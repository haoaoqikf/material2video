"""在作品写锁内保留当前周期隔离包的源媒体，再调用通用输出清理。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.core.output_cleanup import cleanup_after_render
from . import ledger
from .model import VERSION, fields
from .storage import local, locked, read


def retained_media(root: Path) -> set[Path]:
    """包内净化副本不能替代源媒体：来源绑定仍核验源文件摘要。"""
    base = outputs(root)
    if not (base / "production/workflow.json").exists():
        return set()
    events, errors = ledger.history(root)
    if errors:
        raise M2VError("; ".join(errors))
    protected: set[Path] = set()
    for event in events:
        if event["type"] != "package":
            continue
        sealed = event["data"]["receipt"]
        if not ledger.evidence_valid(root, [sealed]):
            raise M2VError("评审源媒体引用记录损坏，未执行清理")
        private = read(local(base, sealed["path"]))
        fields(private, {"version", "request", "binding", "manifest"})
        if private["version"] != VERSION:
            raise M2VError("评审源媒体引用版本未知，未执行清理")
        binding = private["binding"]
        fields(binding, {"conditions", "sources", "media", "references"}, {"final"})
        for key in ("media", "references"):
            if not isinstance(binding[key], list):
                raise M2VError("评审源媒体引用无效，未执行清理")
            for entry in binding[key]:
                fields(entry, {"path", "sha256"})
                # 已失效/未导入的包也保留其明确引用，不把内容过期误作可删除。
                protected.add(local(base, entry["path"], exists=False))
    return protected


def cleanup_render_outputs(root: Path, current_video: Path) -> list[str]:
    """清理失败只报告，不影响已生成候选；与 pack/import 共用锁避免引用竞态。"""
    try:
        with locked(root):
            protected = retained_media(root)
            return cleanup_after_render(
                outputs(root), current_video,
                preserve_visual_evidence=True, protected_files=protected,
            )
    except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
        return [f"无法确认评审源媒体引用，未执行清理：{exc}"]
