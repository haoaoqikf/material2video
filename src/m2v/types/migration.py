"""Explicit, backup-first migration for existing article and financial projects."""
from __future__ import annotations

from m2v.core.video_config import FPS

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.project import PROJECT_FILE, PROJECT_VERSION
from m2v.types import catalog


def migrate(root: Path, source_format: str) -> Path:
    root = root.resolve()
    if (root / PROJECT_FILE).exists():
        raise M2VError(f"作品已有 project.json，拒绝重复迁移：{root / PROJECT_FILE}")
    if not root.is_dir():
        raise M2VError(f"作品目录不存在：{root}")
    financial_upgrade = False
    if source_format == "financial":
        from m2v.types.financial import financial
        raw_plan = json.loads((root / "animation-plan.json").read_text(encoding="utf-8"))
        raw_request = json.loads((root / "request.json").read_text(encoding="utf-8"))
        raw_prices = json.loads((root / "prices.json").read_text(encoding="utf-8"))
        financial_upgrade = raw_plan.get("schemaVersion") not in {7, 8}
        if financial_upgrade:
            if raw_request.get("schemaVersion") != 1 or raw_plan.get("schemaVersion") not in {1, 2, 3, 4, 5, 6} or raw_prices.get("schemaVersion") not in {1, 2, 3}:
                raise M2VError("金融迁移仅支持当前 request v1 与历史价格 v1-v3、计划 v1-v6")
        else:
            financial.load_project(root)
        entry = catalog.catalog().get("financial-timeseries")
        video_type = entry.name
        # 材料入口取自类型目录：迁移产物必须与该类型的当前材料契约一致。
        materials = entry.material_map()
    else:
        raise M2VError(f"不支持的迁移来源：{source_format}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = root.with_name(f"{root.name}.m2v-backup-{stamp}")
    if backup.exists():
        raise M2VError(f"备份目标已存在，拒绝覆盖：{backup}")
    shutil.copytree(root, backup, copy_function=shutil.copy2)
    slug = re.sub(r"[^a-z0-9-]+", "-", root.name.lower()).strip("-") or "video"
    project_id = f"{slug[:50].rstrip('-') or 'video'}-{uuid.uuid4().hex[:8]}"
    manifest = {"schemaVersion": PROJECT_VERSION, "id": project_id, "type": video_type,
                "materials": materials,
                "output": {"width": 1080, "height": 1920, "fps": FPS, "audio": "optional"}}
    target = root / PROJECT_FILE
    temporary = target.with_suffix(".json.tmp")
    try:
        if financial_upgrade:
            from m2v.types.financial.financial import migrate_line
            migrate_line(root)
        historical = [
            Path("production.json"),
            Path("outputs/prepared.json"), Path("outputs/review.json"), Path("outputs/preview-record.json"),
            Path("outputs/media/media.json"), Path("outputs/legibility-review.json"),
            Path("outputs/previews/preview-record.json"),
            Path("outputs/inspect/report.json"), Path("outputs/inspect/review.md"),
        ]
        archived = []
        history_root = root / "outputs" / "history" / f"migration-{stamp}"
        for relative in historical:
            source = root / relative
            if not source.is_file():
                continue
            target_history = history_root / relative
            target_history.parent.mkdir(parents=True, exist_ok=True)
            source.replace(target_history)
            archived.append(relative.as_posix())
        if archived:
            history_root.mkdir(parents=True, exist_ok=True)
            (history_root / "migration.json").write_text(json.dumps({
                "status": "historical", "reason": "作品迁入统一 project 契约后，旧准备与评审不再绑定当前执行契约",
                "sourceFormat": source_format, "archivedFiles": archived,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        # Restore the complete pre-migration tree if a legacy financial upgrade or
        # manifest write fails. The backup itself remains available for inspection.
        backed_up = {item.relative_to(backup) for item in backup.rglob("*") if item.is_file()}
        for item in root.rglob("*"):
            if item.is_file() and item.relative_to(root) not in backed_up:
                item.unlink(missing_ok=True)
        for item in backup.rglob("*"):
            if item.is_file():
                relative = item.relative_to(backup)
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)
        target.unlink(missing_ok=True)
        raise
    print(f"已备份原作品：{backup}\n已创建统一作品描述：{target}。请重新 prepare、预演和评审。")
    return target
