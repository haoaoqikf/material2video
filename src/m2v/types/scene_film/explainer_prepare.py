"""按实际分段音频编译 v9 时间轴；所有可见时序只在准备阶段解析。

画面由作品的本地代码绘制，准备阶段只编译时间轴和源码输入，并把画幅、
字幕几何与媒体映射一起绑进准备指纹。检查和正式生成按需录制片段后合成。
"""
from __future__ import annotations

from m2v.core.video_config import READING_TAIL_SECONDS

import copy
import hashlib
import json
import logging
import math
import tempfile
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, save_prepared, subtitle_font_size
from m2v.core import security
from m2v.core import frames as frame_engine
from m2v.engine import audio, kokoro_tts, qwen3_tts, remotion, rhythm as rhythm_engine, subtitle_backing, subtitles, tts
from . import code_scenes, explainer as contract, explainer_review, reading_pace


logger = logging.getLogger(__name__)


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def implementation_digest() -> str:
    """准备/量测/混音代码也是交付契约，改动后须重新准备和评审。

    键用仓库内相对路径而不是文件名：拆包后两个包都会出现 `__init__.py`，按文件名
    做键会互相覆盖，漏掉其中一个包的实现。
    """
    from m2v.core.assets import REPOSITORY_ROOT
    from m2v.core.fingerprints import fingerprint, module_files
    from m2v.core import media_policy
    from m2v.engine import render_pipeline
    from . import adapter, explainer_render
    from . import soundtrack, media_assets, code_scenes, scene_events, sources
    from m2v.types.financial import materials as financial_materials, plan as financial_plan, valuation as financial_valuation
    from m2v.types.building_construction import materials as building_materials, components as building_components
    from m2v.types.vehicle_showcase import materials as vehicle_materials
    modules = (contract, explainer_review, explainer_render, render_pipeline, frame_engine, adapter, audio, tts,
               kokoro_tts, qwen3_tts, subtitle_backing, subtitles, rhythm_engine, soundtrack, media_assets, media_policy, code_scenes, scene_events, sources, remotion,
               financial_materials, financial_plan, financial_valuation, building_materials, building_components,
               vehicle_materials)
    files = [file for module in modules for file in module_files(module)] + [Path(__file__)]
    keys = {file.relative_to(REPOSITORY_ROOT).as_posix(): digest(file) for file in files}
    return fingerprint({**keys, **code_scenes.implementation_inputs()})


def prepare(root: Path, project: dict, *, voice=None, rate=None, rhythm=None, backend=None) -> dict:
    from . import soundtrack, media_assets, cinematic
    cinematic.validate_project(project)
    source = contract.load(root, project)
    fps = source["fps"]
    explainer_review.require_input(root, project)
    size = frame_engine.normalize(source.get("width"), source.get("height"))
    frame = frame_engine.spec(*size)
    font_size = subtitle_font_size(project)
    if font_size is not None:
        frame["subtitle"]["fontSize"] = font_size
    declared = tts.settings(project).get("speech")
    rhythm = rhythm_engine.configure({**(declared or {}), **(rhythm or {})}) if declared or rhythm else None
    texts = [s["text"] for scene in source["scenes"] for s in scene.get("narrationSegments", [])]
    actual_tts = tts.preparation(project, texts, voice=voice, rate=rate, rhythm=rhythm, backend=backend)
    tts.ensure_backend(actual_tts, root)
    cache = root / "outputs/audio-cache"
    cache.mkdir(parents=True, exist_ok=True)
    inputs = file_inputs(root, project)
    from . import sources as structured_sources
    prepared_sources, source_inputs = structured_sources.prepare(root, source, project["type"])
    inputs.update(source_inputs)
    inputs["tts"] = json.dumps(actual_tts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    inputs["implementation"] = implementation_digest()
    inputs["productionContract"] = "five-types-v2"
    if not contract.topic_input(source):
        article = contract.source_file(root, project)
        inputs["file:" + article.relative_to(root).as_posix()] = digest(article)
        inputs["file:outputs/input-review.json"] = digest(root / "outputs/input-review.json")
    record = root / media_assets.RECORD
    if record.exists(): inputs["file:" + media_assets.RECORD] = digest(record)
    # 登记素材在录制之前全部复核：片段要绑定媒体映射，映射必须先是可信的。
    # 每个素材文件也逐个进 `file:` 输入，替换任何一个都会让旧准备失效。
    resolved = media_assets.resolve(root)
    inputs["codeMedia"] = resolved["digest"]
    for entry in media_assets.load_record(root)["assets"]:
        relative = entry["path"]
        inputs["file:" + relative] = digest(root / relative)
    inputs["frame"] = f"{size[0]}x{size[1]}"
    inputs["subtitle"] = json.dumps(frame["subtitle"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    # 先量测所有旁白，再分配无旁白镜头的剩余时间，绝不靠截断口播凑时长。
    scenes = copy.deepcopy(source["scenes"])
    for scene in scenes:
        scene["content"]["preparedSources"] = {
            identity: prepared_sources[identity] for identity in scene["content"].get("sourceIds", [])
        }
    measured, durations, overlaps, automatic = [], [], [], []
    hold_lists: list[list[int]] = []
    hits = 0
    media_map = {entry["id"]: root / entry["path"]
                 for entry in media_assets.load_record(root)["assets"]}
    backing_style = frame["subtitle"].get("backing")
    for index, scene in enumerate(scenes):
        overlap = 0 if scene.get("transition", "cut") == "cut" else scene.get("transitionFrames", round(8 / 30 * fps))
        overlaps.append(overlap)
        segments = []
        holds = []
        for segment in scene.get("narrationSegments", []):
            speech = scene.get("speech")
            scene_rhythm = rhythm_engine.configure({**(rhythm or {}), **(speech or {})}) if speech else rhythm
            wav, cues, _words, seconds, hit = tts.scene_audio(segment["text"], actual_tts["voice"],
                actual_tts["rate"], cache, contract_version=9, rhythm=scene_rhythm,
                backend=actual_tts["backend"], models_dir=root / "models")
            if not math.isfinite(seconds) or seconds <= 0: raise M2VError(f"旁白 {segment['id']} 音频时长无效")
            translation = segment.get("translation")
            english = (subtitles.split_translation(translation, len(cues), f"{scene['id']}/{segment['id']}")
                       if translation else None)
            segments.append((segment["id"], wav, cues, math.ceil(seconds * fps), english))
            holds.append(segment.get("holdFrames", 0))
            hits += int(hit)
        measured.append(segments)
        hold_lists.append(holds)
        # 冷开场与收尾靠留白声明，阅读停留可以逐幕调整；未声明时与既有行为一致。
        # 段间留白只发生在相邻旁白之间，最后一段由 tailFrames 收尾。
        pad = scene.get("leadInFrames", 0) + scene.get("tailFrames", 0)
        hold = scene.get("readingHoldFrames", round(READING_TAIL_SECONDS * fps))
        inter_hold = sum(holds[:-1])
        minimum = overlap + (pad + sum(s[3] for s in segments) + inter_hold + hold
                             if segments else max(1, pad))
        duration = scene.get("durationFrames")
        if duration is None and segments: duration = minimum
        if duration is None:
            automatic.append(index)
        elif duration < minimum:
            raise M2VError(f"幕 {scene['id']} 固定时长不足以容纳旁白、留白、阅读停留和转场，不得截断口播")
        durations.append(duration)
    if automatic:
        remainder = round(source.get("targetSeconds", 60) * fps) + sum(overlaps) - sum(d or 0 for d in durations)
        share, extra = divmod(remainder, len(automatic))
        for position, index in enumerate(automatic):
            durations[index] = share + (position < extra)
            if durations[index] <= overlaps[index]:
                raise M2VError("目标时长不足以分配无旁白镜头，请增加 targetSeconds")
    cursor = 0
    parts, cues = [], []
    for index, (scene, segments, duration, overlap) in enumerate(zip(scenes, measured, durations, overlaps)):
        if index and (overlap >= durations[index-1] or (index > 1 and overlap + overlaps[index-1] >= durations[index-1])):
            raise M2VError(f"幕 {scene['id']} 转场过长或造成三幕重叠")
        start = cursor - overlap
        # 留白属于本幕：旁白在 leadInFrames 之后才开始，收尾留白同样计入幕长。
        leading = scene.get("leadInFrames", 0)
        speech_start = cursor + leading
        scene.update(startFrame=start, endFrame=start+duration, durationInFrames=duration,
                     transitionFrames=overlap, transition=scene.get("transition", "cut"), segmentWindows={})
        for identity, item in scene["content"]["preparedSources"].items():
            payload = item["data"]
            if (payload["fps"], payload["width"], payload["height"], payload["durationInFrames"]) != (
                    fps, size[0], size[1], duration):
                raise M2VError(f"幕 {scene['id']} 的来源 {identity} 帧率、画幅或时长与分镜不一致")
        # 前导留白必须真的写进音轨：字幕与镜头按 speech_start 排版，旁白若从 0 帧开始
        # 就会整片提前，出现“字幕在说、声音已走”的错位。
        if leading:
            parts.append((None, leading))
        scene_props = scene.get("content", {}).get("props") or {}
        for segment_index, (identity, wav, local_cues, frames, english) in enumerate(segments):
            scene["segmentWindows"][identity] = {"startFrame": speech_start, "endFrame": speech_start+frames}
            for cue_index, cue in enumerate(local_cues):
                a = max(0, min(frames-1, round(cue["start"]* fps)))
                b = max(a+1, min(frames, round(cue["end"]* fps)))
                item = {"startFrame": speech_start+a, "endFrame": speech_start+b, "text": cue["text"]}
                if english:
                    item["secondary"] = english[cue_index]
                if backing_style and backing_style.get("mode") == "adaptiveHalo":
                    asset_id = scene_props.get("asset")
                    asset_path = media_map.get(asset_id) if isinstance(asset_id, str) else None
                    if asset_id and asset_path is None:
                        raise M2VError(f"幕 {scene['id']} 的素材 {asset_id} 未登记，无法采样字幕背景")
                    if asset_path:
                        start_seconds = scene_props.get("startSeconds", 0)
                        seconds_in_scene = (speech_start + a - scene["startFrame"]) / fps
                        midpoint = seconds_in_scene + (b - a) / (2 * fps)
                        item["backing"] = subtitle_backing.sample(
                            asset_path, float(start_seconds) + midpoint, backing_style["maxOpacity"])
                    else:
                        item["backing"] = subtitle_backing.fallback(backing_style["maxOpacity"])
                cues.append(item)
            parts.append((wav, frames))
            speech_start += frames
            # 段间静默写在发声段之后，下一段的窗口与字幕因此整体后移；末段不插入。
            if segment_index < len(segments) - 1:
                gap = hold_lists[index][segment_index]
                if gap:
                    parts.append((None, gap))
                    speech_start += gap
        parts.append((None, scene["endFrame"] - speech_start))
        cursor = scene["endFrame"]
        if cursor > 600 * fps:
            raise M2VError(f"全片 {cursor/ fps:.2f} 秒，超过 600 秒；请调整分镜或旁白，不得截断口播")
        # 镜头时间窗只能在真实分段时长出来之后判定，且必须在录制之前失败。
        shots = (scene.get("content", {}).get("props") or {}).get("shots") or []
        cinematic.validate_shot_windows(scene["id"], shots,
            {key: {"startFrame": window["startFrame"] - start, "endFrame": window["endFrame"] - start}
             for key, window in scene["segmentWindows"].items()}, duration)
        # 准备只验证/构建源码以收集可达依赖；录制推迟到检查窗口或正式生成。
        with tempfile.TemporaryDirectory(prefix="scene-inputs-") as temporary:
            scene_inputs = code_scenes.build_scene(root, scene, Path(temporary))
            inputs.update(scene_inputs)
    from . import scene_events
    resolved_events = scene_events.resolve(scenes)
    effect_start_frames = scene_events.effect_starts(source.get("soundtrack", {}).get("effects", []), scenes, fps, cursor)
    props = copy.deepcopy(source)
    props.update(width=size[0], height=size[1], subtitle=frame["subtitle"],
                 compiledScenes=scenes, subtitleCues=cues, durationInFrames=cursor,
                 resolvedEvents=resolved_events, effectStartFrames=effect_start_frames)
    del props["scenes"]
    props.pop("sources", None)
    media_dir = root / "outputs/media"
    media_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=media_dir) as temporary:
        work = Path(temporary)
        raw, target = work / "raw.wav", work / "audio.wav"
        audio.concatenate(parts, fps, raw)
        soundtrack.mix(root, source, scenes, raw, target, cues, cursor/ fps, work, inputs,
                       effect_start_frames=effect_start_frames)
        mastered = work / "mastered.wav"
        audio.master(target, mastered, integrated=-14.0, true_peak=-1.0)
        target = mastered
        sha = digest(target)
        master = media_dir / f"{sha}.wav"
        security.deliver(target, master)
    inputs["file:" + master.relative_to(root).as_posix()] = sha
    inputs["renderer"] = remotion.build_input_fingerprint(workspace_root=root.parent)["digest"]
    logger.info("通用作品准备：%d 幕，%d 帧，%d×%d，TTS 缓存命中 %d", len(scenes), cursor, size[0], size[1], hits)
    prepared = save_prepared(root, project=project, composition_id="SceneFilm", props=props,
        width=size[0], height=size[1], fps=fps, duration_in_frames=cursor, inputs=inputs, subtitles=cues,
        audio={"segments": [{"sceneId": "master", "path": master.relative_to(root).as_posix(),
            "startFrame": 0, "durationInFrames": cursor, "sha256": sha}], "cacheHits": hits})
    # 阅读速度只报告不阻断，因此放在准备产物写盘之后：报告写不成也不该让准备失败。
    reading_pace.write(root, prepared)
    from m2v.core.project import _write_json
    _write_json(root / "outputs/events.json", {"schemaVersion": 1, "fps": fps,
        "preparedFingerprint": prepared["preparedFingerprint"], "events": resolved_events,
        "effects": [{"index": index, "sceneId": effect["sceneId"],
                     **({"eventId": effect["eventId"]} if "eventId" in effect else {}), "globalFrame": start}
                    for index, (effect, start) in enumerate(zip(source.get("soundtrack", {}).get("effects", []), effect_start_frames))]})
    return prepared
