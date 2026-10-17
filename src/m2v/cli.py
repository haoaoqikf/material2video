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
from m2v.core.preview import require_preview
from m2v.core.workspace import CONTENT_ROOT_ENV
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
    from m2v.types.financial.adapter import TYPE as financial
    from m2v.types.general.adapter import TYPE as general
    from m2v.types.housing.adapter import TYPE as housing
    for item in (financial, general, housing):
        registry.register(item)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m2v", description="专用与通用视频制作工具")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("types", help="列出内置视频类型")
    voices = sub.add_parser("voices", help="列出合成可用音色（需要联网）")
    voices.add_argument("--locale", default="zh-CN", help="区域，例如 zh-CN；--locale all 列出全部")
    voices.add_argument("--json", action="store_true", help="输出 JSON")
    init = sub.add_parser("init", help="初始化作品目录")
    init.add_argument("--type", required=True)
    init.add_argument("--project", required=True)
    init.add_argument("--content-root")
    for command in ("validate", "prepare", "preview", "review-template", "review", "status", "render"):
        item = sub.add_parser(command)
        item.add_argument("--project", required=True)
        if command == "preview":
            item.add_argument("--limit-frames", type=int)
        if command == "prepare":
            # 临时试听用：不改作品文件也能换音色或改节奏，省略时跟随 project.json 的 tts。
            item.add_argument("--voice", help="合成音色，例如 zh-CN-YunxiNeural")
            item.add_argument("--rate", help="语速，例如 --rate=-6%%")
            item.add_argument("--profile", choices=("standard", "cinematic"),
                              help="覆盖作品的制作档位；省略时取 project.json 的 productionProfile")
            item.add_argument("--pause-comma", type=float, metavar="SECONDS", help="逗号、顿号处的停顿秒数")
            item.add_argument("--pause-period", type=float, metavar="SECONDS", help="句号、问号处的停顿秒数")
            item.add_argument("--pause-paragraph", type=float, metavar="SECONDS", help="段末停顿秒数")
            item.add_argument("--head-pad", type=float, metavar="SECONDS", help="每段口播开头的静音长度")
    migrate = sub.add_parser("migrate", help="显式迁移已有作品并先创建完整备份")
    migrate.add_argument("--project", required=True)
    migrate.add_argument("--from", dest="source_format", required=True, choices=("financial",))
    relocate = sub.add_parser("relocate", help="将单个作品移动到按视频类型分层的标准目录")
    relocate.add_argument("--project", required=True, help="旧的 videos/<slug> 作品目录")
    relocate.add_argument("--content-root", help=f"工作区根；省略时取 {CONTENT_ROOT_ENV} 或仓库根")
    general = sub.add_parser("general", help="通用类型的语义审查、候选稿与媒体素材操作")
    general.add_argument("workflow", choices=("status", "template", "input-review", "candidate", "adopt-candidate", "keyframes", "samples", "rehearsal", "assets"))
    general.add_argument("options", nargs=argparse.REMAINDER)
    financial = sub.add_parser("financial", help="金融类型离线材料编排工具")
    financial.add_argument("workflow", choices=("plan", "migrate-line"))
    financial.add_argument("--project", required=True)
    financial.add_argument("--duration-seconds", type=int, help="未指定时所有展示跨度均默认 60 秒")
    return parser


def _rhythm_option(args) -> dict:
    """把命令行上的节奏选项收成声明；一个都没给时返回空，表示跟随作品配置。"""
    declared: dict = {}
    pause = {kind: getattr(args, f"pause_{kind}")
             for kind in ("comma", "period", "paragraph")
             if getattr(args, f"pause_{kind}", None) is not None}
    if pause:
        declared["pause"] = pause
    if getattr(args, "head_pad", None) is not None:
        declared["headPad"] = args.head_pad
    return declared


def _list_voices(locale: str, as_json: bool) -> int:
    """列出合成可用音色，避免把音色名写错才发现。

    只读诊断：结果不参与渲染，也不写文件。
    """
    import asyncio
    from m2v.engine import tts

    try:
        grouped = asyncio.run(tts.list_voices())
    except Exception as exc:
        raise M2VError(f"无法获取音色列表（需要联网）：{exc}") from exc
    selected = grouped if locale == "all" else {locale: grouped.get(locale, [])}
    if locale != "all" and not selected[locale]:
        available = "、".join(sorted(item for item in grouped if item.startswith("zh")) or sorted(grouped))
        raise M2VError(f"区域 {locale} 没有可用音色；可尝试 --locale all，或这些中文区域：{available}")
    if as_json:
        print(json.dumps({
            key: [{"voice": v["ShortName"], "gender": v.get("Gender"),
                   "categories": (v.get("VoiceTag") or {}).get("ContentCategories"),
                   "personalities": (v.get("VoiceTag") or {}).get("VoicePersonalities")}
                  for v in values]
            for key, values in selected.items()}, ensure_ascii=False, indent=2))
        return 0
    for key in sorted(selected):
        print(f"{key}（{len(selected[key])} 个）")
        for voice in sorted(selected[key], key=lambda item: item["ShortName"]):
            tag = voice.get("VoiceTag") or {}
            traits = "、".join(filter(None, (
                "、".join(tag.get("ContentCategories") or []),
                "、".join(tag.get("VoicePersonalities") or []))))
            print(f"  {voice['ShortName']:<38} {voice.get('Gender', ''):<7} {traits}")
    return 0


def _report_reading_pace(root: Path) -> None:
    """阅读速度只提示不阻断：超限时打印一行，制作照常继续。"""
    path = root / "outputs/reading-pace.json"
    if not path.is_file():
        return
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[warning] 阅读速度报告无法读取：{exc}", file=sys.stderr)
        return
    over = report.get("overLimit") or []
    if not over:
        return
    fastest = max(over, key=lambda cue: cue["charactersPerSecond"])
    print(
        f"[warning] {len(over)} 条字幕超过 {report.get('limitPerSecond')} 字/秒的阅读上限"
        f"（最快 {fastest['charactersPerSecond']} 字/秒，第 {fastest['startFrame']} 帧）；"
        f"详见 {path}",
        file=sys.stderr,
    )


def _prepared(root: Path, manifest: dict) -> dict:
    check = registry.get(manifest["type"]).prepared_check
    return check(root, manifest) if check else load_current_prepared(root, manifest)


def _status(root: Path, manifest: dict) -> dict:
    video_type = registry.get(manifest["type"])
    review_status = {"status": "optional" if video_type.manual_review_available else "not-required",
                     "required": False}
    preview_status = {"status": "missing"}
    try:
        prepared = _prepared(root, manifest)
        prep = {"status": "current", "fingerprint": prepared["preparedFingerprint"]}
    except M2VError as exc:
        return {"id": manifest["id"], "type": manifest["type"],
                "prepare": {"status": "stale-or-missing", "detail": str(exc)},
                "preview": preview_status, "review": review_status}
    record_path = root / "outputs/preview-record.json"
    if manifest["type"] == "financial-timeseries":
        record_path = root / "outputs/previews/preview-record.json"
    if record_path.exists():
        try:
            if manifest["type"] == "financial-timeseries":
                _require_type_review(video_type, root, manifest)
                record = json.loads(record_path.read_text(encoding="utf-8"))
                video = (root / record["path"]).resolve()
                if (not record.get("materialsAndAssetsSha256") or not video.is_file()
                        or hashlib.sha256(video.read_bytes()).hexdigest() != record.get("sha256")):
                    raise M2VError("金融预演文件或绑定已变化")
            else:
                record = require_preview(root, prepared, verify_media=False)
            preview_status = {"status": "current", "path": record["path"]}
        except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
            preview_status = {"status": "stale", "detail": str(exc)}
    review_path = root / "outputs/review.json"
    if video_type.manual_review_available and review_path.exists():
        try:
            review = json.loads(review_path.read_text(encoding="utf-8"))
            criteria = _review_criteria(root, manifest, prepared)
            if (not isinstance(review, dict) or review.get("schemaVersion") != 1
                    or review.get("projectId") != manifest["id"]
                    or review.get("preparedFingerprint") != prep["fingerprint"]
                    or review.get("criteria") != criteria or preview_status["status"] != "current"
                    or review.get("preview") != record):
                review_status["status"] = "stale"
            else:
                evidence = review.get("evidence")
                complete = (isinstance(evidence, dict) and set(evidence) == set(criteria)
                            and all(isinstance(v, str) and v.strip() for v in evidence.values()))
                review_status["status"] = review.get("status", "pending") if complete else "pending"
        except (OSError, ValueError, KeyError, TypeError):
            review_status["status"] = "stale"
    return {"id": manifest["id"], "type": manifest["type"], "prepare": prep,
            "preview": preview_status, "review": review_status}


def _review_criteria(root: Path, manifest: dict, prepared: dict) -> dict[str, str]:
    video_type = registry.get(manifest["type"])
    if video_type.review_criteria is not None:
        return video_type.review_criteria(root, manifest, prepared)
    return {"visualQuality": "整片画面质量", "continuity": "内容连续性与节奏", "audio": "音轨和字幕同步"}


def _require_review(root: Path, manifest: dict, prepared: dict) -> None:
    if not registry.get(manifest["type"]).manual_review_available:
        return
    path = root / "outputs" / "review.json"
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise M2VError(f"缺少可选评审记录：{path}；请执行 m2v review-template 并完成评审") from exc
    if (not isinstance(review, dict) or review.get("schemaVersion") != 1 or review.get("status") != "pass"
            or review.get("projectId") != manifest["id"]
            or review.get("preparedFingerprint") != prepared["preparedFingerprint"]):
        raise M2VError("可选评审未通过或已过期；请重新评审当前准备版本")
    criteria = _review_criteria(root, manifest, prepared)
    if review.get("criteria") != criteria:
        raise M2VError("评审项与当前视频类型要求不匹配；请重新生成 review-template")
    evidence = review.get("evidence")
    if (not isinstance(evidence, dict) or set(evidence) != set(criteria)
            or any(not isinstance(value, str) or not value.strip() for value in evidence.values())):
        raise M2VError("评审通过必须为当前类型的每项结论填写非空证据")
    preview = review.get("preview")
    current_preview = require_preview(root, prepared, verify_media=False)
    if not isinstance(preview, dict) or preview != current_preview:
        raise M2VError("评审没有绑定当前完整预演")


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
        if args.command == "general":
            from m2v.types.general import explainer_cli as workflow
            return workflow.main([args.workflow, *args.options])
        if args.command == "financial":
            root, manifest = load_project(args.project)
            if manifest["type"] != "financial-timeseries":
                raise M2VError("m2v financial 仅适用于 financial-timeseries 作品")
            from m2v.types.financial.financial import prepare_line_plan, migrate_line
            if args.workflow == "migrate-line":
                backup = migrate_line(root, args.duration_seconds if args.duration_seconds is not None else 60)
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
            content_root = args.content_root or os.environ.get(CONTENT_ROOT_ENV)
            workspace = Path(content_root).expanduser().resolve() if content_root else Path(__file__).resolve().parents[2]
            if not project_dir.is_absolute():
                if len(project_dir.parts) == 1:
                    project_dir = workspace / "videos" / item.name / project_dir
                elif len(project_dir.parts) == 2 and project_dir.parts[0] == "videos":
                    raise M2VError(f"作品路径缺少类型目录：请使用 <slug> 或 videos/{item.name}/<slug>")
                elif len(project_dir.parts) == 3 and project_dir.parts[0] == "videos":
                    if project_dir.parts[1] != item.name:
                        raise M2VError(f"作品路径类型目录与 --type 不一致：应为 videos/{item.name}/<slug>")
                    project_dir = workspace / project_dir
                else:
                    project_dir = workspace / project_dir
            path = create_project(project_dir, item.name, entry.material_map())
            root = path.parent
            # 材料文件名与初始内容都取自类型目录：这里是写盘，不是第二处事实。
            for material in entry.materials:
                (root / material.file).write_text(
                    json.dumps(material.template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            # 起步文件（本地代码场景入口）同样按目录声明复制，之后由作者改写。
            for relative in entry.starters:
                source = catalog.starters_dir(item.name) / relative
                if not source.is_file():
                    raise M2VError(f"类型目录声明的起步文件不存在：{source}")
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"已创建 {item.name} 作品：{path}")
            return 0
        if args.command == "migrate":
            from m2v.types.migration import migrate
            migrate(Path(args.project), args.source_format)
            return 0
        if args.command == "relocate":
            from m2v.types.relocation import relocate
            result = relocate(Path(args.project), content_root=args.content_root)
            print(result.message)
            return 0
        if args.command == "voices":
            return _list_voices(args.locale, args.json)
        root, manifest = load_project(args.project)
        video_type = registry.get(manifest["type"])
        _validate_project_location(root, manifest)
        if args.command == "validate":
            video_type.validate(root, manifest)
            print("材料校验通过")
            return 0
        if args.command == "prepare":
            video_type.validate(root, manifest)
            video_type.prepare(root, manifest, voice=args.voice, rate=args.rate,
                               rhythm=_rhythm_option(args), profile=args.profile)
            print(f"已生成准备产物：{root / 'outputs' / 'prepared.json'}")
            _report_reading_pace(root)
            return 0
        if args.command == "status":
            print(json.dumps(_status(root, manifest), ensure_ascii=False, indent=2))
            return 0
        if args.command in {"preview", "render"}:
            prepared = _prepared(root, manifest)
            if args.command == "render":
                if manifest["type"] != "financial-timeseries":
                    require_preview(root, prepared)
                _require_type_review(video_type, root, manifest)
                output = video_type.render(root, manifest)
                try:
                    output_path = Path(output).resolve()
                except (OSError, RuntimeError) as exc:
                    raise M2VError(f"无法解析正式成片路径：{output}: {exc}") from exc
                if not output_path.is_file():
                    raise M2VError(f"正式渲染没有生成成片：{output_path}")
                expected_outputs = (root / "outputs").resolve()
                # Shipped examples keep run products outside their versioned source tree.
                if root.parent.name == "examples":
                    expected_outputs = (root.parent.parent / "videos" / "examples" / root.name / "outputs").resolve()
                failures = cleanup_after_render(expected_outputs, output_path,
                    preserve_previews=manifest["type"] == "financial-timeseries")
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
                # 档位随预演一起留证：同一指纹下档位不会变，但记录要能自证。
                # 按准备记录里是否声明档位判断，不按类型名分发。
                profile = prepared.get("props", {}).get("productionProfile")
                if profile is not None:
                    record["productionProfile"] = profile
                (root / "outputs" / "preview-record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"视频输出：{output}")
            return 0
        if args.command == "review-template":
            if not video_type.manual_review_available:
                print("当前类型使用完整预演自动验收，不提供人工评审模板")
                return 0
            video_type.validate(root, manifest)
            prepared = _prepared(root, manifest)
            preview = require_preview(root, prepared, verify_media=False)
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
            prepared = _prepared(root, manifest)
            if not video_type.manual_review_available:
                if manifest["type"] != "financial-timeseries":
                    require_preview(root, prepared)
                _require_type_review(video_type, root, manifest)
                print("当前类型的完整预演自动验收通过；人工评审不适用")
                return 0
            require_preview(root, prepared)
            _require_review(root, manifest, prepared)
            _require_type_review(video_type, root, manifest)
            print("当前准备版本与完整预演评审通过")
            return 0
        return 0
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1 if args.command not in {"init", "migrate", "relocate"} else 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[error] 参数或材料错误：{exc}", file=sys.stderr)
        return 2


def _validate_project_location(root: Path, manifest: dict) -> None:
    """Reject a project whose declared type disagrees with its canonical path."""
    if root.parent.name not in {"videos", "examples"} and root.parent.parent.name == "videos":
        expected_type = root.parent.name
        if expected_type != manifest["type"]:
            raise M2VError(
                f"作品类型目录不匹配：project.json 声明 {manifest['type']}，"
                f"实际位于 videos/{expected_type}/{root.name}；请执行 m2v relocate"
            )


if __name__ == "__main__":
    raise SystemExit(main())
