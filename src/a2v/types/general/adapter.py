"""Validate and compile a general video's frame-exact scene schedule."""
from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
import hashlib

from imageio_ffmpeg import get_ffmpeg_exe

from a2v.core.errors import A2VError
from a2v.core.project import file_inputs, load_project, load_current_prepared, save_prepared
from a2v.core import code_gate, code_scenes
from a2v.types.registry import VideoType
from a2v.engine import remotion, contract_page, perf
from a2v.types import registry
from a2v.engine import output_validation
from a2v.core import security

SCENE_TYPES = {"graphic", "financial-timeseries", "article-narrative", "code"}


def _plan(root: Path, project: dict[str, Any]) -> dict[str, Any]:
    file = root / project["materials"].get("plan", "general-plan.json")
    try:
        plan = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise A2VError(f"无法读取通用视频计划：{exc}") from exc
    if not isinstance(plan, dict) or plan.get("schemaVersion") != 1:
        raise A2VError("general-plan.json schemaVersion 必须为 1")
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise A2VError("通用视频至少需要一个场景")
    ids: set[str] = set()
    compiled = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict) or not isinstance(scene.get("id"), str) or not scene["id"].strip():
            raise A2VError(f"scenes[{index}].id 必须是非空字符串")
        if scene["id"] in ids:
            raise A2VError(f"场景 ID 重复：{scene['id']}")
        ids.add(scene["id"])
        kind = scene.get("type")
        if kind not in SCENE_TYPES:
            raise A2VError(f"场景 {scene['id']} 类型无效：{kind!r}")
        embedded = kind in {"financial-timeseries", "article-narrative"}
        if embedded:
            # Embedded works keep their own complete timeline and soundtrack.
            # Accepting parent duration/narration fields here would make authors
            # believe that a forbidden trim or audio overlay had been applied.
            if "duration" in scene:
                raise A2VError(f"嵌入场景 {scene['id']} 保留完整时间轴，不允许声明 duration")
            if "narration" in scene:
                raise A2VError(f"嵌入场景 {scene['id']} 保留自身声音，不允许声明父级 narration")
            ref = scene.get("project")
            if not isinstance(ref, str) or not ref:
                raise A2VError(f"嵌入场景 {scene['id']} 必须声明 project 路径")
            child = (root / ref).resolve()
            if not child.is_dir():
                raise A2VError(f"嵌入作品目录不存在：{child}")
            if child == root.resolve() or root.resolve() not in child.parents:
                raise A2VError(f"嵌入作品 project 必须引用当前作品目录内的子项目：{ref}")
            child_root, child_manifest = load_project(child)
            if child_manifest["type"] != kind:
                raise A2VError(f"嵌入作品类型不匹配：{ref}")
            embedded_prepared = load_current_prepared(child_root, child_manifest)
            frames = embedded_prepared["durationInFrames"]
            scene["embeddedProps"] = embedded_prepared["props"]
            scene["embeddedComposition"] = embedded_prepared["compositionId"]
            scene["embeddedCodeModules"] = []
            if kind == "article-narrative":
                storyboard = child_root / child_manifest["materials"]["storyboard"]
                modules = {}
                for _path, declaration, module in code_scenes.iter_code_scenes(scene["embeddedProps"]):
                    resolved = code_scenes.resolve_module(storyboard.parent, module)
                    if resolved is None:
                        raise A2VError(f"嵌入文章代码场景模块不存在：{module}")
                    alias = "__a2v_embedded_" + hashlib.sha256(
                        f"{scene['id']}:{module}".encode("utf-8")
                    ).hexdigest()[:16]
                    declaration["renderer"]["module"] = alias
                    relative = resolved.resolve().relative_to(root.resolve()).as_posix()
                    modules[alias] = {"path": relative, "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}
                scene["embeddedCodeModules"] = [
                    {"id": alias, **details} for alias, details in sorted(modules.items())
                ]
        else:
            duration = scene.get("duration")
            narration = scene.get("narration")
            if narration is not None:
                valid_narration = (isinstance(narration, str) and bool(narration.strip())) or (
                    isinstance(narration, list) and bool(narration)
                    and all(isinstance(part, str) and part.strip() for part in narration))
                if not valid_narration:
                    raise A2VError(f"场景 {scene['id']} narration 必须是非空文本或文本数组")
            fixed = duration.get("frames") if isinstance(duration, dict) else None
            if fixed is None and narration is None:
                raise A2VError(f"场景 {scene['id']} 必须声明 duration.frames 或 narration")
            if fixed is not None and (type(fixed) is not int or fixed < 1):
                raise A2VError(f"场景 {scene['id']} duration.frames 必须是正整数")
            frames = fixed
            if kind == "code":
                renderer = scene.get("renderer")
                if not isinstance(renderer, dict) or renderer.get("kind") != "code" or not isinstance(renderer.get("module"), str) or not renderer["module"]:
                    raise A2VError(f"代码场景 {scene['id']} 必须声明 renderer.kind=code 和 module")
            if kind == "graphic":
                _validate_graphic_data(scene["id"], scene.get("data", {}))
        transition = scene.get("transition", {"type": "cut"})
        if not isinstance(transition, dict) or transition.get("type", "cut") not in {"cut", "crossfade"}:
            raise A2VError(f"场景 {scene['id']} 转场只支持 cut/crossfade")
        overlap = transition.get("frames", 12 if transition.get("type") == "crossfade" else 0)
        if transition.get("type", "cut") == "cut" and overlap != 0:
            raise A2VError(f"硬切场景 {scene['id']} 不允许重叠帧")
        if type(overlap) is not int or overlap < 0 or (frames is not None and overlap >= frames):
            raise A2VError(f"场景 {scene['id']} 转场帧数无效")
        if index == 0 and overlap:
            raise A2VError("首场景不能声明入场转场帧数")
        if index and compiled[-1].get("durationInFrames") is not None and overlap >= compiled[-1]["durationInFrames"]:
            raise A2VError(f"场景 {scene['id']} 的淡化不能超过前一场景时长")
        compiled.append({**scene, **({"durationInFrames": frames} if frames is not None else {}), "transitionFrames": overlap})
    plan.setdefault("fps", 30)
    plan.setdefault("width", 1080)
    plan.setdefault("height", 1920)
    if (plan["fps"], plan["width"], plan["height"]) != (30, 1080, 1920):
        raise A2VError("通用视频首版只支持 1080×1920、30 fps")
    plan["scenes"] = compiled
    return plan


def _validate_graphic_data(scene_id: str, data: Any) -> None:
    if not isinstance(data, dict):
        raise A2VError(f"图文场景 {scene_id} data 必须是对象")
    lines = data.get("lines", [])
    if not isinstance(lines, list) or len(lines) > 8 or any(not isinstance(line, str) or not line.strip() for line in lines):
        raise A2VError(f"图文场景 {scene_id} lines 必须是最多 8 条的非空文本数组")
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list) or len(nodes) > 6:
        raise A2VError(f"图文场景 {scene_id} nodes 最多包含 6 个关系节点")
    node_ids = set()
    for index, node in enumerate(nodes):
        if (not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"].strip()
                or not isinstance(node.get("label"), str) or not node["label"].strip()):
            raise A2VError(f"图文场景 {scene_id} nodes[{index}] 必须声明非空 id 和 label")
        if node["id"] in node_ids:
            raise A2VError(f"图文场景 {scene_id} 节点 id 重复：{node['id']}")
        node_ids.add(node["id"])
    links = data.get("links", [])
    if not isinstance(links, list) or len(links) > 8:
        raise A2VError(f"图文场景 {scene_id} links 最多包含 8 条关系")
    for index, link in enumerate(links):
        if (not isinstance(link, dict) or not isinstance(link.get("from"), str)
                or not isinstance(link.get("to"), str) or link["from"] not in node_ids or link["to"] not in node_ids):
            raise A2VError(f"图文场景 {scene_id} links[{index}] 必须引用已声明节点")
        if link["from"] == link["to"] or not isinstance(link.get("label"), str) or not link["label"].strip():
            raise A2VError(f"图文场景 {scene_id} links[{index}] 必须是两个不同节点间的非空关系")
    values = data.get("values", [])
    if not isinstance(values, list) or len(values) > 8:
        raise A2VError(f"图文场景 {scene_id} values 最多包含 8 个数值")
    for index, item in enumerate(values):
        value = item.get("value") if isinstance(item, dict) else None
        if (not isinstance(item, dict) or not isinstance(item.get("label"), str) or not item["label"].strip()
                or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise A2VError(f"图文场景 {scene_id} values[{index}] 必须包含非空 label 和有限非负 value")


def validate(root: Path, project: dict) -> None:
    plan = _plan(root, project)
    module_issues = code_scenes.check(plan, root)
    if module_issues:
        raise A2VError("\n".join(f"{path}: {message}" for path, message in module_issues))
    violations = code_gate.check_storyboard(article_dir=root, storyboard_data=plan)
    if violations:
        raise A2VError("\n".join(item.render(root) for item in violations))
    _validate_embedded_reviews(root, plan)


def _validate_embedded_reviews(root: Path, plan: dict[str, Any]) -> None:
    for scene in plan["scenes"]:
        if scene["type"] not in {"financial-timeseries", "article-narrative"}:
            continue
        child_root, child_manifest = load_project((root / scene["project"]).resolve())
        child_type = registry.get(child_manifest["type"])
        child_type.validate(child_root, child_manifest)
        load_current_prepared(child_root, child_manifest)
        if child_type.review_gate is None:
            raise A2VError(f"嵌入类型 {child_manifest['type']} 未公开评审门禁接口")
        child_type.review_gate(child_root, child_manifest)


def prepare(root: Path, project: dict) -> dict:
    plan = _plan(root, project)
    _validate_embedded_reviews(root, plan)
    inputs = file_inputs(root, project)
    dependencies = []
    audio_segments = []
    fps = plan["fps"]
    for scene in plan["scenes"]:
        for module in scene.get("embeddedCodeModules", []):
            inputs[f"embedded-module:{module['id']}"] = module["sha256"]
        if scene["type"] in {"financial-timeseries", "article-narrative"}:
            child_root, child_manifest = load_project((root / scene["project"]).resolve())
            prepared = load_current_prepared(child_root, child_manifest)
            dependencies.append({"path": os.path.relpath(child_root, root),
                                 "preparedFingerprint": prepared["preparedFingerprint"]})
            child_type = registry.get(child_manifest["type"])
            for track in child_type.audio_tracks(child_root, child_manifest, prepared) if child_type.audio_tracks else []:
                audio_segments.append({"sceneId": scene["id"], "path": os.path.relpath(track["path"], root).replace("\\", "/"),
                                       "durationInFrames": track["durationInFrames"], "embedded": True})
        elif scene.get("narration"):
            narration = scene["narration"]
            text = "".join(narration) if isinstance(narration, list) else str(narration)
            cache = root / "outputs" / "audio-cache"
            cache.mkdir(parents=True, exist_ok=True)
            speech = registry.get("article-narrative").prepare_narration
            if speech is None:
                raise A2VError("当前注册的视频类型未提供可复用的口播准备接口")
            wav, cues, _words, seconds, _hit = speech(text, cache)
            fixed = scene.get("duration", {}).get("frames")
            if fixed is not None and (type(fixed) is not int or seconds > fixed / fps):
                raise A2VError(f"场景 {scene['id']} 口播超出固定帧容量")
            scene["durationInFrames"] = fixed if fixed is not None else math.ceil(seconds * fps) + 12
            scene["subtitleCues"] = [{"startFrame": round(cue["start"] * fps),
                                      "endFrame": round(cue["end"] * fps), "text": cue["text"]} for cue in cues]
            audio_segments.append({"sceneId": scene["id"], "path": wav.relative_to(root).as_posix(),
                                   "durationInFrames": math.ceil(seconds * fps)})
    plan = _compile(plan)
    starts = {scene["id"]: scene["startFrame"] for scene in plan["compiledScenes"]}
    for segment in audio_segments:
        segment["startFrame"] = starts[segment["sceneId"]]
        scene = next(item for item in plan["compiledScenes"] if item["id"] == segment["sceneId"])
        segment["durationInFrames"] = min(segment["durationInFrames"], scene["durationInFrames"])
        following = next((item for item in plan["compiledScenes"] if item["startFrame"] == scene["endFrame"] - item["transitionFrames"]), None)
        # Incoming overlap belongs to this scene; outgoing overlap is declared by its successor.
        segment["fadeInFrames"] = min(scene["transitionFrames"], segment["durationInFrames"] // 2)
        segment["fadeOutFrames"] = min((following or {}).get("transitionFrames", 0), segment["durationInFrames"] // 2)
    for scene in plan["compiledScenes"]:
        for cue in scene.get("subtitleCues", []):
            cue["startFrame"] += scene["startFrame"]
            cue["endFrame"] += scene["startFrame"]
    plan["subtitleCues"] = [cue for scene in plan["compiledScenes"] for cue in scene.get("subtitleCues", [])]
    for segment in audio_segments:
        segment["sha256"] = hashlib.sha256((root / segment["path"]).read_bytes()).hexdigest()
        inputs[f"audio:{segment['sceneId']}"] = segment["sha256"]
    render_fingerprint = remotion.build_input_fingerprint(
        storyboard_path=root / project["materials"]["plan"], content_root=root.parent,
        workspace_root=root.parent,
    )["digest"]
    inputs["renderer"] = render_fingerprint
    return save_prepared(root, project=project, composition_id="GeneralVideo", props=plan,
        width=plan["width"], height=plan["height"], fps=plan["fps"],
        duration_in_frames=plan["durationInFrames"], inputs=inputs,
        audio={"segments": audio_segments}, dependencies=dependencies,
        subtitles=[cue for scene in plan["compiledScenes"] for cue in scene.get("subtitleCues", [])])


def _compile(plan: dict[str, Any]) -> dict[str, Any]:
    cursor = 0
    compiled = []
    for index, scene in enumerate(plan["scenes"]):
        frames = scene.get("durationInFrames") or (scene.get("duration") or {}).get("frames")
        if type(frames) is not int or frames < 1:
            raise A2VError(f"场景 {scene['id']} 需要确定时长；带口播场景必须先准备 TTS")
        transition = scene.get("transition", {"type": "cut"})
        overlap = transition.get("frames", 12 if transition.get("type") == "crossfade" else 0)
        if transition.get("type", "cut") == "cut" and overlap != 0:
            raise A2VError(f"硬切场景 {scene['id']} 不允许重叠帧")
        if (type(overlap) is not int or overlap < 0 or overlap >= frames
                or (index == 0 and overlap)
                or (index and overlap >= compiled[-1]["durationInFrames"])):
            raise A2VError(f"场景 {scene['id']} 转场帧数无效")
        if index and overlap + compiled[-1]["transitionFrames"] >= compiled[-1]["durationInFrames"]:
            raise A2VError("相邻交叉淡化导致三个场景同时重叠")
        start = cursor - overlap
        compiled.append({**scene, "durationInFrames": frames, "startFrame": start,
                         "endFrame": start + frames, "transitionFrames": overlap})
        cursor = start + frames
    plan["compiledScenes"] = compiled
    plan["durationInFrames"] = cursor
    plan["audioTimeline"] = []
    return plan


def _embedded_modules(root: Path, scenes: list[dict[str, Any]], inputs: dict[str, str] | None = None) -> list[tuple[str, Path]]:
    """Resolve namespaced article modules and recheck their prepared digests."""
    result = []
    for scene in scenes:
        for module in scene.get("embeddedCodeModules", []):
            path = (root / module["path"]).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError as exc:
                raise A2VError(f"嵌入代码场景模块越界：{path}") from exc
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            if digest != module["sha256"] or (inputs is not None and inputs.get(f"embedded-module:{module['id']}") != digest):
                raise A2VError(f"嵌入代码场景模块已变化；请重新 prepare 并评审：{path}")
            result.append((module["id"], path))
    return result


def preview(root: Path, project: dict, *, limit_frames: int | None = None) -> Path:
    return _render(root, project, preview=True, limit_frames=limit_frames)


def render(root: Path, project: dict) -> Path:
    return _render(root, project, preview=False)


def review_criteria(_root: Path, _project: dict, prepared: dict) -> dict[str, str]:
    scenes = prepared["props"]["compiledScenes"]
    embedded = any(scene["type"] in {"financial-timeseries", "article-narrative"} for scene in scenes)
    audio = bool(prepared.get("audio", {}).get("segments"))
    criteria = {"overallRhythm": "整片节奏、信息密度与开合是否连贯",
                "sceneTransitions": "场景边界、硬切/交叉淡化与视觉衔接",
                "sceneContent": "图文、关系与数据表达是否准确且易读"}
    if embedded:
        criteria["embeddedTypeQuality"] = "每个金融/文章片段均通过其专用门禁且保持完整时间轴"
    if audio:
        criteria["audioSubtitles"] = "口播、音轨淡化和全片字幕边界是否同步"
    if any(scene["type"] == "code" for scene in scenes):
        criteria["codeScene"] = "作品代码场景按帧确定、画面完整且边界符合公开 API"
    return criteria


def _render(root: Path, project: dict, *, preview: bool, limit_frames: int | None = None) -> Path:
    prepared = load_current_prepared(root, project)
    _validate_embedded_reviews(root, _plan(root, project))
    if prepared.get("contractVersion") != 1 or prepared.get("compositionId") != "GeneralVideo":
        raise A2VError("准备记录契约不匹配；请重新 prepare")
    if limit_frames is not None and limit_frames < 1:
        raise A2VError("limit_frames 必须为正整数")
    if not preview and limit_frames is not None:
        raise A2VError("正式导出不支持限帧渲染")
    entry = root / project["materials"]["plan"]
    current_renderer = remotion.build_input_fingerprint(
        storyboard_path=entry, content_root=root.parent, workspace_root=root.parent,
    )["digest"]
    if prepared.get("inputs", {}).get("renderer") != current_renderer:
        raise A2VError("通用视频渲染代码、字体或资源已变化；请重新 prepare 并评审")
    web = contract_page.web_dir()
    destination = root / ("outputs/previews/video.mp4" if preview else "outputs/video.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timings = perf.StageTimings()
    expected_frames = min(prepared["durationInFrames"], limit_frames or prepared["durationInFrames"])
    with tempfile.TemporaryDirectory(prefix="a2v-general-", dir=destination.parent) as temporary:
        temp = Path(temporary)
        props_file = temp / "prepared-props.json"
        props_file.write_text(json.dumps(prepared["props"], ensure_ascii=False), encoding="utf-8")
        raw_video = temp / "video.mp4"
        # Remotion's code-scene manifest consumes the same `scenes` collection
        # used by the public code-scene API. Use this prepared snapshot so code
        # modules are scoped to the current work and stale scenes cannot leak.
        render_plan = dict(prepared["props"])
        render_plan["scenes"] = render_plan["compiledScenes"]
        additional_modules = _embedded_modules(root, render_plan["compiledScenes"], prepared["inputs"])
        # The scene manifest resolves project-relative code modules from the
        # plan's parent directory. Keep this ephemeral snapshot in the project
        # root so `scenes/foo.tsx` has the same meaning as in the source plan.
        fd, plan_name = tempfile.mkstemp(prefix=".a2v-general-render-", suffix=".json", dir=root)
        os.close(fd)
        plan_for_bundle = Path(plan_name)
        try:
            plan_for_bundle.write_text(json.dumps(render_plan, ensure_ascii=False), encoding="utf-8")
            outcome = remotion.bundle(web_dir=web, out_dir=temp / "bundle", storyboard_path=plan_for_bundle,
                content_root=root.parent, workspace_root=root.parent, cache=True,
                additional_modules=additional_modules,
                cache_identity=root / project["materials"]["plan"])
        finally:
            plan_for_bundle.unlink(missing_ok=True)
        timings.record("bundle", outcome.build_seconds)
        timings.record("cache", outcome.cache_seconds)
        def confirm(metadata: remotion.CompositionMetadata) -> dict:
            wanted = (prepared["fps"], prepared["width"], prepared["height"], prepared["durationInFrames"])
            actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
            if actual != wanted:
                raise A2VError(f"GeneralVideo 元数据与准备记录不匹配：期望 {wanted}，实际 {actual}；请重新 prepare")
            count = expected_frames
            return {"out": str(raw_video), "crf": 18, "preset": "medium",
                    "frames": f"0-{count-1}", "scale": 1, "concurrency": 1,
                    "progressTotal": count}
        render_started = time.monotonic()
        session = remotion.render_session(web_dir=web, bundle_dir=outcome.path, props=props_file,
            composition_id="GeneralVideo", on_metadata=confirm, timeout_s=3600)
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(time.monotonic() - render_started - timings.as_dict()["metadata"], 0))
        audio_segments = prepared.get("audio", {}).get("segments", [])
        final_video = raw_video
        if audio_segments:
            final_video = temp / "final.mp4"
            _mux_audio(root, raw_video, final_video, audio_segments, prepared["fps"], expected_frames)
            timings.record("mux", time.monotonic() - render_started - (timings.as_dict()["render"] or 0) - (timings.as_dict()["metadata"] or 0))
        else:
            timings.skip("mux")
        with perf.measure(timings, "probe"):
            output_validation.verify_output(final_video, expected_frames, prepared["width"], prepared["height"], prepared["fps"], expect_audio=bool(audio_segments))
        # Only replace a previously valid export after the new temporary output passes every check.
        staged = temp / destination.name
        try:
            staged.write_bytes(final_video.read_bytes())
            staged.replace(destination)
        except OSError:
            staged.unlink(missing_ok=True)
            raise
        security.grant_inherited_access(destination)
    if not preview:
        inputs = prepared.get("inputs", {})
        provenance = {"schemaVersion": 1, "type": "general", "projectId": project["id"],
                      "preparedFingerprint": prepared["preparedFingerprint"], "inputs": inputs,
                      "durationInFrames": expected_frames, "fps": prepared["fps"],
                      "width": prepared["width"], "height": prepared["height"],
                      "renderer": "remotion", "compositionId": "GeneralVideo"}
        (destination.with_suffix(".provenance.json")).write_text(json.dumps(provenance, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    payload = perf.build_report(entry="preview" if preview else "render", output=destination,
        storyboard=entry, frames=expected_frames, fps=prepared["fps"], width=prepared["width"],
        height=prepared["height"], concurrency=1, timings=timings,
        total_seconds=time.monotonic()-started,
        cache={"status": outcome.cache_status, "key": outcome.cache_key, "detail": outcome.cache_detail},
        extra={"session": {"browsersOpened": session.get("browsersOpened"),
                           "handshakeSeconds": session.get("readySeconds"),
                           "observedPeakMemoryBytes": session.get("peakMemoryBytes"),
                           "memorySamples": session.get("memorySamples")}})
    perf.write_report(perf.report_path_for(destination), payload)
    return destination


def _mux_audio(root: Path, video: Path, output: Path, segments: list[dict], fps: int, frames: int) -> None:
    command = [get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(video)]
    for segment in segments:
        audio = (root / segment["path"]).resolve()
        if not audio.is_file():
            raise A2VError(f"准备音轨缺失或越界：{audio}")
        if hashlib.sha256(audio.read_bytes()).hexdigest() != segment.get("sha256"):
            raise A2VError(f"准备音轨已变化；请重新 prepare：{audio}")
        command.extend(["-i", str(audio)])
    filters = []
    labels = []
    for index, segment in enumerate(segments, start=1):
        delay = round(segment["startFrame"] * 1000 / fps)
        label = f"a{index}"
        duration = segment["durationInFrames"] / fps
        fade_in = segment.get("fadeInFrames", 0) / fps
        fade_out = segment.get("fadeOutFrames", 0) / fps
        chain = f"[{index}:a]" + (f"afade=t=in:st=0:d={fade_in:.6f}," if fade_in else "") + (f"afade=t=out:st={max(0, duration-fade_out):.6f}:d={fade_out:.6f}," if fade_out else "") + f"adelay={delay}|{delay},apad,atrim=duration={frames/fps:.6f}[{label}]"
        filters.append(chain)
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,atrim=duration={frames/fps:.6f}[mixed]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[mixed]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{frames/fps:.6f}", str(output)])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise A2VError(f"通用视频音轨混合失败：{result.stderr[-2000:]}")


TYPE = VideoType("general", "多场景通用视频编排", validate, prepare, preview, render,
                 review_criteria=review_criteria)
