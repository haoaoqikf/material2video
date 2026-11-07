"""``m2v`` 各子命令的实现。

解析与错误映射留在 :mod:`m2v.cli`，这里只负责「拿到已解析的参数，把命令做掉」：
每个分支自己加载作品、取类型适配器并打印结果。分开的理由不是分层好看，而是
`main()` 过去有 173 行、把分发与十来个命令的实现混在一起，改一个命令要读完所有命令。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from m2v.core.delivery import candidate, outputs as delivery_outputs, read_record
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_current_prepared, load_project
from m2v.core.workspace import CONTENT_ROOT_ENV
from m2v.type_system import catalog, registry


def dispatch(args) -> int:
    """按已解析的命令执行；错误交给 `m2v.cli.main` 统一映射为退出码。"""
    if args.command == "sample":
        from m2v.production.sample_cli import dispatch as sample_dispatch
        return sample_dispatch(args)
    if args.command in {"review", "issues", "baseline"}:
        from m2v.production.cli import dispatch as production_dispatch
        return production_dispatch(args)
    if args.command == "types":
        listing = []
        for item in registry.all_types():
            listing.append({
                "type": item.name,
                "description": registry.describe(item.name),
            })
        print(json.dumps(listing, ensure_ascii=False, indent=2))
        return 0
    if args.command == "author":
        from m2v.types.scene_film import explainer_cli as workflow
        return workflow.main([args.workflow, *args.options])
    if args.command == "ref":
        from m2v.reference.cli import main as reference_main
        return reference_main(args)
    if args.command == "data":
        root, manifest = load_project(args.project)
        if manifest["type"] != "data-evolution":
            raise M2VError("m2v data financial-plan 仅适用于数据演化作品")
        from m2v.types.scene_film.sources import validate as validate_sources
        storyboard = json.loads((root / manifest["materials"]["storyboard"]).read_text(encoding="utf-8-sig"))
        if storyboard.get("version") != 9 or storyboard.get("schemaVersion") != 9:
            raise M2VError("financial-plan 只接受 v9 分镜")
        sources = validate_sources(root, storyboard, manifest["type"], allow_missing_financial_plan=True)
        financial = [item["files"] for item in sources.values() if item["kind"] == "financial-series"]
        if len(financial) != 1:
            raise M2VError("financial-plan 需要分镜中恰好一个 financial-series 来源")
        from m2v.types.financial.financial import prepare_line_plan
        files = financial[0]
        plan = prepare_line_plan(root, args.duration_seconds, files=files)
        (root / files["plan"]).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已生成 {plan['durationSeconds']} 秒金融折线计划")
        return 0
    if args.command in {"lookdev", "qa", "assets"}:
        # 三个检查入口各自解析自己的参数；这里只做统一分发。
        from m2v.engine import assets_audit, lookdev as lookdev_engine, qa as qa_engine
        if args.command == "lookdev":
            options = ["--project", args.project, "--sample-seconds", str(args.sample_seconds),
                       "--still-scale", str(args.still_scale)]
            # 取点模式与代表静帧互斥：只在真的声明了张数时才转发，保留"未声明"语义。
            if args.stills is not None:
                options += ["--stills", str(args.stills)]
            if args.sheet:
                options += ["--sheet", *[str(item) for item in args.sheet]]
            if args.motion:
                options += ["--motion", *[str(item) for item in args.motion]]
            if args.det:
                options.append("--det")
            if args.event:
                for event in args.event:
                    options += ["--event", event]
                if args.before is not None:
                    options += ["--before", str(args.before)]
                if args.after is not None:
                    options += ["--after", str(args.after)]
                if args.hold:
                    options += ["--hold", str(args.hold)]
            return lookdev_engine.main(options)
        if args.command == "qa":
            options = ["--project", args.project, "--step", str(args.step)]
            if args.video:
                options += ["--video", args.video]
            return qa_engine.main(options)
        from m2v.engine import assets_tools
        if args.workflow == "audit":
            if not args.project:
                raise M2VError("assets audit 需要 --project")
            return assets_audit.main(["--project", args.project])
        if args.workflow == "report":
            if not args.project:
                raise M2VError("assets report 需要 --project")
            return assets_tools.report_main(project=args.project, sources=args.sources,
                                            as_json=args.json)
        return assets_tools.contact_main(
            project=args.project, inputs=args.inputs or [], times=args.times,
            samples=args.samples, columns=args.columns, tile_width=args.tile_width,
            out=args.out, as_json=args.json)
    if args.command == "init":
        return _init(args)
    if args.command == "voices":
        return _list_voices(args.locale, args.json)
    return _project_command(args)


def _init(args) -> int:
    item = registry.get(args.type)
    entry = catalog.catalog().get(item.name)
    project_dir = Path(args.project).expanduser()
    content_root = args.content_root or os.environ.get(CONTENT_ROOT_ENV)
    workspace = Path(content_root).expanduser().resolve() if content_root else Path(__file__).resolve().parents[2]
    standard = entry.workspace_parts()
    standard_hint = "videos/" + "/".join((*standard, "<slug>"))
    if not project_dir.is_absolute():
        if len(project_dir.parts) == 1:
            project_dir = workspace / "videos" / Path(*standard) / project_dir
        elif project_dir.parts[0] == "videos":
            expected = ("videos", *standard, project_dir.parts[-1])
            if project_dir.parts != expected:
                raise M2VError(
                    f"作品路径与类型类别不一致：{item.name} 的标准位置为 {standard_hint}，"
                    f"实际为 {project_dir.as_posix()}"
                )
            project_dir = workspace / project_dir
        else:
            project_dir = workspace / project_dir
    # 绝对路径同样按类别校验；在写盘前失败，避免留下位置错误的作品。
    _validate_project_location(project_dir, {"type": item.name})
    path = create_project(project_dir, item.name, entry.material_map(), output=entry.initial_dimensions())
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


def _project_command(args) -> int:
    """作品级命令：validate / prepare / status / preview / render / review*。"""
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
                           rhythm=_rhythm_option(args))
        print(f"已生成准备产物：{root / 'outputs' / 'prepared.json'}")
        _report_reading_pace(root)
        return 0
    if args.command == "status":
        print(json.dumps(_status(root, manifest, full_history=args.history), ensure_ascii=False, indent=2))
        return 0
    if args.command in {"preview", "render"}:
        _prepared(root, manifest)
        jobs = getattr(args, "jobs", 1)
        if type(jobs) is not int or not 1 <= jobs <= 4:
            raise M2VError("--jobs 必须为 1～4 的整数")
        if jobs > 1 and not video_type.supports_render_jobs:
            raise M2VError(f"当前类型 {manifest['type']} 不支持 --jobs > 1")
        render_options = {"jobs": jobs} if jobs > 1 and video_type.supports_render_jobs else {}
        if args.command == "render":
            _require_render_input(video_type, root, manifest)
            _production_render_event(root, manifest, 'render-request')
            try:
                output = video_type.render(root, manifest, **render_options)
            except Exception:
                _production_render_event(root, manifest, 'render-failed')
                raise
            _production_render_event(root, manifest, 'render-returned')
            try:
                output_path = Path(output).resolve()
            except (OSError, RuntimeError) as exc:
                raise M2VError(f"无法解析正式成片路径：{output}: {exc}") from exc
            if not output_path.is_file():
                raise M2VError(f"正式渲染没有生成成片：{output_path}")
            from m2v.production.cleanup import cleanup_render_outputs
            failures = cleanup_render_outputs(root, output_path)
            if failures:
                for failure in failures:
                    print(f"[warning] 旧产物清理未完成：{failure}", file=sys.stderr)
            else:
                print("旧视频及可再生产物已清理")
        else:
            output = video_type.preview(root, manifest, limit_frames=args.limit_frames,
                start_seconds=args.start_seconds, end_seconds=args.end_seconds, **render_options)
            if not output.is_file():
                raise M2VError(f"片段检查没有生成视频：{output}")
            print("片段检查完成，不作为全片生成的前置条件")
        print(f"视频输出：{output}")
        return 0
    return 0


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


def _production_render_event(root: Path, manifest: dict, kind: str, *, candidate_id=None) -> None:
    """记录不阻断候选生成；未显式启动周期时不创建制作状态。"""
    if not (delivery_outputs(root) / 'production/workflow.json').exists():
        return
    try:
        from m2v.production import ledger
        from m2v.production.storage import locked
        with locked(root):
            ledger.append(root, manifest, kind, data={'candidateId': candidate_id})
    except (M2VError, OSError, ValueError) as exc:
        print(f'[warning] 制作渲染记录失败：{exc}', file=sys.stderr)


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


def _status(root: Path, manifest: dict, *, full_history=False) -> dict:
    registry.get(manifest["type"])
    result = {"id": manifest["id"], "type": manifest["type"]}
    from m2v.production import baselines, ledger
    result['production'] = ledger.status(root, manifest, full_history=full_history)
    try:
        result['production']['baselines'] = baselines.summary(root)
    except M2VError as exc:
        result['production'].setdefault('diagnostics', []).append(str(exc))
    try:
        prepared = _prepared(root, manifest)
        result["prepare"] = {"status": "current", "fingerprint": prepared["preparedFingerprint"]}
    except M2VError as exc:
        result.update(prepare={"status": "stale-or-missing", "detail": str(exc)}, stage="unprepared")
        from m2v.production.readiness import summary
        result['summary'] = summary(result)
        return result
    result["stage"] = "prepared"
    record = read_record(delivery_outputs(root))
    if record:
        try:
            record = candidate(root, prepared)
            result["candidate"] = record
            result["stage"] = record["status"]
        except M2VError as exc:
            result["candidate"] = {"status": "stale", "detail": str(exc)}
    from m2v.production.readiness import summary
    result['summary'] = summary(result)
    return result


def _require_render_input(video_type, root: Path, manifest: dict) -> None:
    if video_type.pre_render_check is not None:
        video_type.pre_render_check(root, manifest)


def _validate_project_location(root: Path, manifest: dict) -> None:
    """Reject a project whose path disagrees with its type's canonical workspace location.

    Canonical location is ``videos/<type>/<slug>``. Repository examples live at
    ``examples/<type>/<slug>/`` and keep their own project manifests.
    """
    try:
        index = max(position for position, part in enumerate(root.parts) if part == "videos")
    except ValueError:
        return
    actual_parts = root.parts[index + 1:]
    if len(actual_parts) != 2:
        raise M2VError("作品位置必须为 videos/<type>/<slug>；旧目录不自动迁移")
    entry = catalog.catalog().get(manifest["type"])
    expected_parts = (*entry.workspace_parts(), root.name)
    if actual_parts == expected_parts:
        return
    actual = Path("videos", *actual_parts).as_posix()
    standard = Path("videos", *entry.workspace_parts(), "<slug>").as_posix()
    raise M2VError(
        f"作品位置与类型不匹配：project.json 声明 {manifest['type']}，"
        f"实际位于 {actual}，标准位置为 {standard}"
    )
