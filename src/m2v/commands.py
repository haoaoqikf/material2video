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
from m2v.core.output_cleanup import cleanup_after_render
from m2v.core.project import create_project, load_current_prepared, load_project
from m2v.core.workspace import CONTENT_ROOT_ENV
from m2v.types import catalog, registry


def dispatch(args) -> int:
    """按已解析的命令执行；错误交给 `m2v.cli.main` 统一映射为退出码。"""
    if args.command == "styles":
        from m2v.core.styles import list_styles
        items = list_styles()
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            print("\n".join(f"{x['id']} {x['version']} — {x['description']}" for x in items) or "暂无已注册风格")
        return 0
    if args.command in {"gates", "issues", "baseline"} or (args.command == "review" and getattr(args, "action", None) == "import"):
        from m2v.production.cli import dispatch as production_dispatch
        return production_dispatch(args)
    if args.command == "types":
        print(json.dumps([{"type": x.name, "description": registry.describe(x.name)} for x in registry.all_types()], ensure_ascii=False, indent=2))
        return 0
    if args.command == "general":
        from m2v.types.general import explainer_cli as workflow
        return workflow.main([args.workflow, *args.options])
    if args.command == "ref":
        from m2v.reference.cli import main as reference_main
        return reference_main(args)
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
            return lookdev_engine.main(options)
        if args.command == "qa":
            options = ["--project", args.project, "--step", str(args.step)]
            if args.video:
                options += ["--video", args.video]
            return qa_engine.main(options)
        options = ["--project", args.project]
        return assets_audit.main(options)
    if args.command == "init":
        return _init(args)
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
    return _project_command(args)


def _init(args) -> int:
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
    if item.name == 'general':
        from m2v.production.storage import write
        write(root / 'outputs/production/workflow.json', {'version': 1, 'origin': 'new-project'})
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
        prepared = _prepared(root, manifest)
        if args.command == "render":
            _require_type_review(video_type, root, manifest)
            _production_render_event(root, manifest, 'render-request')
            try:
                output = video_type.render(root, manifest)
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
            expected_outputs = (root / "outputs").resolve()
            # Shipped examples keep run products outside their versioned source tree.
            if root.parent.name == "examples":
                expected_outputs = (root.parent.parent / "videos" / "examples" / root.name / "outputs").resolve()
            failures = cleanup_after_render(expected_outputs, output_path,
                preserve_previews=False,
                preserve_visual_evidence=manifest["type"] == "general")
            if failures:
                for failure in failures:
                    print(f"[warning] 旧产物清理未完成：{failure}", file=sys.stderr)
            else:
                print("旧视频及可再生产物已清理")
        else:
            output = video_type.preview(root, manifest, limit_frames=args.limit_frames,
                start_seconds=args.start_seconds, end_seconds=args.end_seconds)
            if not output.is_file():
                raise M2VError(f"片段检查没有生成视频：{output}")
            print("片段检查完成，不作为全片生成的前置条件")
        print(f"视频输出：{output}")
        return 0
    if args.command == "review-template":
        if not video_type.manual_review_available:
            print("当前类型使用候选自动验收，不提供人工评审模板")
            return 0
        video_type.validate(root, manifest)
        prepared = _prepared(root, manifest)
        preview = candidate(root, prepared)
        (root / "outputs").mkdir(exist_ok=True)
        criteria = _review_criteria(root, manifest, prepared)
        template = {"schemaVersion": 1, "status": "pending", "criteria": criteria,
                    "evidence": {name: "" for name in criteria},
                    "projectId": manifest["id"], "preparedFingerprint": prepared["preparedFingerprint"],
                    "candidate": {key: preview[key] for key in ("key", "sha256", "preparedFingerprint")}}
        if video_type.review_template is not None:
            video_type.review_template(root, manifest)
        (root / "outputs" / "review.json").write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"待填写评审模板：{root / 'outputs' / 'review.json'}")
        return 0
    if args.command == "review":
        prepared = _prepared(root, manifest)
        if not video_type.manual_review_available:
            record = candidate(root, prepared)
            if record.get("status") not in {"ready", "delivered"}:
                raise M2VError("当前候选尚未通过自动验收；请执行 m2v render 重试检查")
            _require_type_review(video_type, root, manifest)
            print("当前类型的完整候选自动检查通过；人工评审不适用")
            return 0
        candidate(root, prepared)
        _require_review(root, manifest, prepared)
        _require_type_review(video_type, root, manifest)
        print("当前准备版本与完整候选评审通过")
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
    """制作记录失败只报告诊断，不改变现有导出成功/失败结果。"""
    if manifest['type'] != 'general' or not (root / 'DESIGN.md').exists():
        return
    try:
        from m2v.production import contract, ledger
        from m2v.production.storage import locked
        c = contract.load(root)
        with locked(root):
            ledger.append(root, manifest, kind, upstream={'contract': contract.scope_digest(c)},
                          data={'candidateId': candidate_id, 'reason': '当前渲染绑定缺少可复用候选，需要生成或失败后重试'} if candidate_id else {})
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
    video_type = registry.get(manifest["type"])
    result = {"id": manifest["id"], "type": manifest["type"],
              "review": {"status": "optional" if video_type.manual_review_available else "not-required", "required": False}}
    from m2v.core.styles import selected_style
    style = selected_style(manifest)
    if style:
        result["style"] = {**style["identity"], "guide": style["guide"]}
    from m2v.production import baselines, ledger
    result['production'] = ledger.status(root, manifest, full_history=full_history)
    if manifest['type'] == 'general':
        try:
            result['production']['baselines'] = baselines.summary(root)
        except M2VError as exc:
            result['production'].setdefault('diagnostics', []).append(str(exc))
    if manifest["type"] == "general":
        result["review"]["detail"] = "技术就绪不代表制作完成；助手须复核全片帧序列和自动音频候选并关闭必改项，无需用户确认。"
    try:
        prepared = _prepared(root, manifest)
        result["prepare"] = {"status": "current", "fingerprint": prepared["preparedFingerprint"]}
    except M2VError as exc:
        result.update(prepare={"status": "stale-or-missing", "detail": str(exc)}, stage="unprepared")
        if manifest['type'] == 'general':
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
    review_path = root / "outputs/review.json"
    if video_type.manual_review_available and review_path.exists():
        try:
            _require_review(root, manifest, prepared)
            result["review"]["status"] = "pass"
        except M2VError as exc:
            result["review"].update(status="pending-or-stale", detail=str(exc))
    if manifest['type'] == 'general':
        from m2v.production.readiness import summary
        result['summary'] = summary(result)
    return result


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
    preview = review.get("candidate")
    current_preview = candidate(root, prepared)
    if not isinstance(preview, dict) or any(preview.get(key) != current_preview.get(key) for key in ("key", "sha256", "preparedFingerprint")):
        raise M2VError("评审没有绑定当前完整候选")


def _require_type_review(video_type, root: Path, manifest: dict) -> None:
    if video_type.review_gate is not None:
        video_type.review_gate(root, manifest)


def _validate_project_location(root: Path, manifest: dict) -> None:
    """Reject a project whose declared type disagrees with its canonical path."""
    if root.parent.name not in {"videos", "examples"} and root.parent.parent.name == "videos":
        expected_type = root.parent.name
        if expected_type != manifest["type"]:
            raise M2VError(
                f"作品类型目录不匹配：project.json 声明 {manifest['type']}，"
                f"实际位于 videos/{expected_type}/{root.name}；请执行 m2v relocate"
            )
