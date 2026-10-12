"""Unified ``m2v`` command line entry point."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project, load_current_prepared
from m2v.core.output_cleanup import cleanup_after_render
from m2v.types import catalog, registry


def _force_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        configure = getattr(stream, "reconfigure", None)
        if configure:
            try:
                configure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def _register_builtins() -> None:
    if registry.all_types():
        return
    from m2v.types.article.adapter import TYPE as article
    from m2v.types.financial.adapter import TYPE as financial
    from m2v.types.general.adapter import TYPE as general
    for item in (article, financial, general):
        registry.register(item)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m2v", description="专用与通用视频制作工具")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("types", help="列出内置视频类型")
    init = sub.add_parser("init", help="初始化作品目录")
    init.add_argument("--type", required=True)
    init.add_argument("--project", required=True)
    init.add_argument("--content-root")
    for command in ("validate", "prepare", "preview", "review-template", "review", "status", "render"):
        item = sub.add_parser(command)
        item.add_argument("--project", required=True)
        if command == "preview":
            item.add_argument("--limit-frames", type=int)
    migrate = sub.add_parser("migrate", help="显式迁移已有作品并先创建完整备份")
    migrate.add_argument("--project", required=True)
    migrate.add_argument("--from", dest="source_format", required=True, choices=("article-v4", "financial"))
    article = sub.add_parser("article", help="文章类型的语义审查与候选稿操作")
    article.add_argument("workflow", choices=("status", "template", "input-review", "candidate", "adopt-candidate", "keyframes", "samples", "rehearsal"))
    article.add_argument("options", nargs=argparse.REMAINDER)
    financial = sub.add_parser("financial", help="金融类型离线材料编排工具")
    financial.add_argument("workflow", choices=("plan", "migrate-line"))
    financial.add_argument("--project", required=True)
    financial.add_argument("--duration-seconds", type=int, default=60)
    return parser


def _status(root: Path, manifest: dict) -> dict:
    try:
        prepared = load_current_prepared(root, manifest)
        prep = {"status": "current", "fingerprint": prepared["preparedFingerprint"]}
    except M2VError as exc:
        prep = {"status": "stale-or-missing", "detail": str(exc)}
    preview_status, review_status = {"status": "missing"}, {"status": "pending"}
    if prep["status"] == "current":
        try:
            record = json.loads((root / "outputs" / "preview-record.json").read_text(encoding="utf-8"))
            preview_file = (root / record["path"]).resolve()
            if (record.get("preparedFingerprint") != prep["fingerprint"] or not preview_file.is_file()
                    or hashlib.sha256(preview_file.read_bytes()).hexdigest() != record.get("sha256")):
                preview_status = {"status": "stale"}
            else:
                preview_status = {"status": "current", "path": record["path"]}
            review = json.loads((root / "outputs" / "review.json").read_text(encoding="utf-8"))
            prepared = load_current_prepared(root, manifest)
            criteria = _review_criteria(root, manifest, prepared)
            evidence = review.get("evidence")
            complete = (isinstance(evidence, dict) and set(evidence) == set(criteria)
                        and all(isinstance(value, str) and value.strip() for value in evidence.values()))
            if review.get("preparedFingerprint") != prep["fingerprint"] or review.get("criteria") != criteria:
                review_status = {"status": "stale"}
            else:
                review_status = {"status": review.get("status", "pending") if complete else "pending"}
        except (OSError, ValueError, KeyError):
            pass
    return {"id": manifest["id"], "type": manifest["type"], "prepare": prep,
            "preview": preview_status, "review": review_status}


def _review_criteria(root: Path, manifest: dict, prepared: dict) -> dict[str, str]:
    video_type = registry.get(manifest["type"])
    if video_type.review_criteria is not None:
        return video_type.review_criteria(root, manifest, prepared)
    return {"visualQuality": "整片画面质量", "continuity": "内容连续性与节奏", "audio": "音轨和字幕同步"}


def _require_review(root: Path, manifest: dict, prepared: dict) -> None:
    path = root / "outputs" / "review.json"
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise M2VError(f"缺少当前评审记录：{path}；请执行 m2v review-template 并完成评审") from exc
    if (review.get("schemaVersion") != 1 or review.get("status") != "pass"
            or review.get("projectId") != manifest["id"]
            or review.get("preparedFingerprint") != prepared["preparedFingerprint"]):
        raise M2VError("正式评审未通过或已过期；请重新评审当前准备版本")
    criteria = _review_criteria(root, manifest, prepared)
    if review.get("criteria") != criteria:
        raise M2VError("评审项与当前视频类型要求不匹配；请重新生成 review-template")
    evidence = review.get("evidence")
    if (not isinstance(evidence, dict) or set(evidence) != set(criteria)
            or any(not isinstance(value, str) or not value.strip() for value in evidence.values())):
        raise M2VError("评审通过必须为当前类型的每项结论填写非空证据")
    preview = review.get("preview")
    if not isinstance(preview, dict) or preview.get("preparedFingerprint") != prepared["preparedFingerprint"]:
        raise M2VError("评审没有绑定当前完整预演")
    video = (root / str(preview.get("path", ""))).resolve()
    if not video.is_file() or hashlib.sha256(video.read_bytes()).hexdigest() != preview.get("sha256"):
        raise M2VError("已评审的预演文件不存在或已变化")


def _require_type_review(video_type, root: Path, manifest: dict) -> None:
    if video_type.review_gate is not None:
        video_type.review_gate(root, manifest)


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    _register_builtins()
    args = _parser().parse_args(argv)
    try:
        if args.command == "types":
            print(json.dumps([{"type": x.name, "description": registry.describe(x.name)} for x in registry.all_types()], ensure_ascii=False, indent=2))
            return 0
        if args.command == "article":
            from m2v.types.article import workflow_cli as workflow
            return workflow.main([args.workflow, *args.options])
        if args.command == "financial":
            root, manifest = load_project(args.project)
            if manifest["type"] != "financial-timeseries":
                raise M2VError("m2v financial 仅适用于 financial-timeseries 作品")
            from m2v.types.financial.financial import prepare_line_plan, migrate_line
            if args.workflow == "migrate-line":
                backup = migrate_line(root, args.duration_seconds)
                print(f"已升级金融计划到 v8；备份：{backup}。请重新 prepare、preview 和 review。")
                return 0
            plan = prepare_line_plan(root, args.duration_seconds)
            (root / manifest["materials"]["plan"]).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"已生成 {plan['durationSeconds']} 秒金融折线计划")
            return 0
        if args.command == "init":
            item = registry.get(args.type)
            entry = catalog.catalog().get(item.name)
            project_dir = Path(args.project).expanduser()
            content_root = args.content_root or os.environ.get("M2V_CONTENT_ROOT")
            if content_root and not project_dir.is_absolute():
                project_dir = Path(content_root).expanduser() / project_dir
            path = create_project(project_dir, item.name, entry.material_map())
            root = path.parent
            # 材料文件名与初始内容都取自类型目录：这里是写盘，不是第二处事实。
            for material in entry.materials:
                (root / material.file).write_text(
                    json.dumps(material.template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            print(f"已创建 {item.name} 作品：{path}")
            return 0
        if args.command == "migrate":
            from m2v.types.migration import migrate
            migrate(Path(args.project), args.source_format)
            return 0
        root, manifest = load_project(args.project)
        video_type = registry.get(manifest["type"])
        if args.command == "validate":
            video_type.validate(root, manifest)
            print("材料校验通过")
            return 0
        if args.command == "prepare":
            video_type.validate(root, manifest)
            video_type.prepare(root, manifest)
            print(f"已生成准备产物：{root / 'outputs' / 'prepared.json'}")
            return 0
        if args.command == "status":
            print(json.dumps(_status(root, manifest), ensure_ascii=False, indent=2))
            return 0
        if args.command in {"preview", "render"}:
            prepared = load_current_prepared(root, manifest)
            if args.command == "render":
                _require_review(root, manifest, prepared)
                _require_type_review(video_type, root, manifest)
                output = video_type.render(root, manifest)
                try:
                    output_path = Path(output).resolve()
                except (OSError, RuntimeError) as exc:
                    raise M2VError(f"无法解析正式成片路径：{output}: {exc}") from exc
                if not output_path.is_file():
                    raise M2VError(f"正式渲染没有生成成片：{output_path}")
                expected_outputs = (root / "outputs").resolve()
                # Shipped article examples keep their run products under videos/examples.
                if root.parent.name == "examples":
                    example_outputs = (root.parent.parent / "videos" / "examples" / root.name / "outputs").resolve()
                    if output_path.parent == example_outputs:
                        expected_outputs = example_outputs
                failures = cleanup_after_render(expected_outputs, output_path)
                if failures:
                    for failure in failures:
                        print(f"[warning] 旧产物清理未完成：{failure}", file=sys.stderr)
                else:
                    print("旧视频及可再生产物已清理")
            else:
                output = video_type.preview(root, manifest, limit_frames=getattr(args, "limit_frames", None))
                if not output.is_file():
                    raise M2VError(f"预演没有生成视频：{output}")
                if getattr(args, "limit_frames", None) is not None and args.limit_frames < prepared["durationInFrames"]:
                    print(f"限帧调试预览已生成（不会绑定评审）：{output}")
                    return 0
                digest = hashlib.sha256(output.read_bytes()).hexdigest()
                # 预演不一定落在作品根下：仓库自带示例的作品根是 examples/<slug>/，
                # 预演却属于 videos/examples/<slug>/outputs/。记录统一按作品根相对化，
                # 允许 `..`，读回时仍用 `root / path` 解析。
                relative = Path(os.path.relpath(output.resolve(), root)).as_posix()
                record = {"path": relative, "sha256": digest,
                          "frames": prepared["durationInFrames"], "preparedFingerprint": prepared["preparedFingerprint"]}
                (root / "outputs" / "preview-record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"视频输出：{output}")
            return 0
        if args.command == "review-template":
            video_type.validate(root, manifest)
            prepared = load_current_prepared(root, manifest)
            try:
                preview = json.loads((root / "outputs" / "preview-record.json").read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise M2VError("缺少完整预演记录；请先执行 m2v preview") from exc
            if preview.get("preparedFingerprint") != prepared["preparedFingerprint"]:
                raise M2VError("完整预演不匹配当前准备产物；请重新 preview")
            (root / "outputs").mkdir(exist_ok=True)
            criteria = _review_criteria(root, manifest, prepared)
            template = {"schemaVersion": 1, "status": "pending", "criteria": criteria,
                        "evidence": {name: "" for name in criteria},
                        "projectId": manifest["id"], "preparedFingerprint": prepared["preparedFingerprint"],
                        "preview": preview}
            if video_type.review_template is not None:
                video_type.review_template(root, manifest)
            (root / "outputs" / "review.json").write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"待填写评审模板：{root / 'outputs' / 'review.json'}")
            return 0
        if args.command == "review":
            prepared = load_current_prepared(root, manifest)
            _require_review(root, manifest, prepared)
            _require_type_review(video_type, root, manifest)
            print("当前准备版本与完整预演评审通过")
            return 0
        return 0
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1 if args.command not in {"init", "migrate"} else 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[error] 参数或材料错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
