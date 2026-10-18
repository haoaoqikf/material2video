"""按实际分段音频编译 v8 时间轴；所有可见时序只在准备阶段解析。

画面由作品的本地代码绘制，准备阶段把每一幕录成标准化无声片段，并把画幅、
字幕几何与媒体映射一起绑进准备指纹。导出只回放这些片段，不运行作品代码。
"""
from __future__ import annotations

from m2v.core.video_config import FPS

import copy
import hashlib
import json
import logging
import math
import tempfile
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, save_prepared
from m2v.core import security
from m2v.engine import audio, frames as frame_engine, remotion, rhythm as rhythm_engine, tts
from . import code_scenes, explainer as contract, explainer_review, reading_pace


logger = logging.getLogger(__name__)


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def implementation_digest() -> str:
    """准备/量测/混音代码也是交付契约，改动后须重新准备和评审。"""
    from m2v.core.fingerprints import fingerprint
    from . import adapter, explainer_render
    from . import soundtrack, media_assets, code_scenes
    modules = (contract, explainer_review, explainer_render, frame_engine, adapter, audio, tts,
               rhythm_engine, soundtrack, media_assets, code_scenes)
    files = [Path(module.__file__) for module in modules] + [Path(__file__)]
    return fingerprint({**{file.name: digest(file) for file in files}, **code_scenes.implementation_inputs()})


def prepare(root: Path, project: dict, *, voice=None, rate=None, rhythm=None, profile=None) -> dict:
    from . import soundtrack, media_assets, cinematic
    actual_profile, profile_source = cinematic.resolve_profile(project, profile)
    source = contract.load(root, project)
    explainer_review.require_input(root, project)
    size = frame_engine.normalize(source.get("width"), source.get("height"))
    frame = frame_engine.spec(*size)
    declared = tts.settings(project).get("speech")
    rhythm = rhythm_engine.configure({**(declared or {}), **(rhythm or {})}) if declared or rhythm else None
    texts = [s["text"] for scene in source["scenes"] for s in scene.get("narrationSegments", [])]
    actual_tts = tts.preparation(project, texts, voice=voice, rate=rate, rhythm=rhythm)
    cache = root / "outputs/audio-cache"
    cache.mkdir(parents=True, exist_ok=True)
    inputs = file_inputs(root, project)
    inputs["tts"] = json.dumps(actual_tts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    inputs["implementation"] = implementation_digest()
    # 档位决定编码、后期与验收口径，因此它和镜头、look 一样属于准备输入。
    inputs["profile"] = json.dumps({"profile": actual_profile, "source": profile_source},
                                   ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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
    measured, durations, overlaps, automatic = [], [], [], []
    hits = 0
    for index, scene in enumerate(scenes):
        overlap = 0 if scene.get("transition", "cut") == "cut" else scene.get("transitionFrames", contract.FADE_FRAMES)
        overlaps.append(overlap)
        segments = []
        for segment in scene.get("narrationSegments", []):
            speech = scene.get("speech")
            scene_rhythm = rhythm_engine.configure({**(rhythm or {}), **(speech or {})}) if speech else rhythm
            wav, cues, _words, seconds, hit = tts.scene_audio(segment["text"], actual_tts["voice"],
                actual_tts["rate"], cache, contract_version=8, rhythm=scene_rhythm)
            if not math.isfinite(seconds) or seconds <= 0: raise M2VError(f"旁白 {segment['id']} 音频时长无效")
            segments.append((segment["id"], wav, cues, math.ceil(seconds * FPS)))
            hits += int(hit)
        measured.append(segments)
        # 冷开场与收尾靠留白声明，阅读停留可以逐幕调整；未声明时与既有行为一致。
        pad = scene.get("leadInFrames", 0) + scene.get("tailFrames", 0)
        hold = scene.get("readingHoldFrames", contract.READING_TAIL)
        minimum = overlap + (pad + sum(s[3] for s in segments) + hold if segments else max(1, pad))
        duration = scene.get("durationFrames")
        if duration is None and segments: duration = minimum
        if duration is None:
            automatic.append(index)
        elif duration < minimum:
            raise M2VError(f"幕 {scene['id']} 固定时长不足以容纳旁白、留白、阅读停留和转场，不得截断口播")
        durations.append(duration)
    if automatic:
        remainder = round(source.get("targetSeconds", 60) * FPS) + sum(overlaps) - sum(d or 0 for d in durations)
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
                     transitionFrames=overlap, segmentWindows={})
        # 前导留白必须真的写进音轨：字幕与镜头按 speech_start 排版，旁白若从 0 帧开始
        # 就会整片提前，出现“字幕在说、声音已走”的错位。
        if leading:
            parts.append((None, leading))
        for identity, wav, local_cues, frames in segments:
            scene["segmentWindows"][identity] = {"startFrame": speech_start, "endFrame": speech_start+frames}
            for cue in local_cues:
                a = max(0, min(frames-1, round(cue["start"]* FPS)))
                b = max(a+1, min(frames, round(cue["end"]* FPS)))
                cues.append({"startFrame": speech_start+a, "endFrame": speech_start+b, "text": cue["text"]})
            parts.append((wav, frames))
            speech_start += frames
        parts.append((None, scene["endFrame"] - speech_start))
        cursor = scene["endFrame"]
        if cursor > contract.MAX_FRAMES:
            raise M2VError(f"全片 {cursor/ FPS:.2f} 秒，超过 600 秒；请调整分镜或旁白，不得截断口播")
        # 镜头时间窗只能在真实分段时长出来之后判定，且必须在录制之前失败。
        shots = (scene.get("content", {}).get("props") or {}).get("shots") or []
        cinematic.validate_shot_windows(scene["id"], shots,
            {key: {"startFrame": window["startFrame"] - start, "endFrame": window["endFrame"] - start}
             for key, window in scene["segmentWindows"].items()}, duration)
        scene["mediaPath"] = code_scenes.record(root, scene, inputs, frame=frame,
                                                media=resolved["media"], media_digest=resolved["digest"],
                                                profile=actual_profile)
        scene["trimStartFrames"] = 0
    props = copy.deepcopy(source)
    props.update(width=size[0], height=size[1], subtitle=frame["subtitle"],
                 compiledScenes=scenes, subtitleCues=cues, durationInFrames=cursor,
                 productionProfile=actual_profile, productionProfileSource=profile_source)
    del props["scenes"]
    media_dir = root / "outputs/media"
    media_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=media_dir) as temporary:
        work = Path(temporary)
        raw, target = work / "raw.wav", work / "audio.wav"
        audio.concatenate(parts, FPS, raw)
        soundtrack.mix(root, source, scenes, raw, target, cues, cursor/ FPS, work, inputs)
        if actual_profile == "cinematic":
            # cinematic 成片响度 −14 LUFS / −1 dBTP；standard 保持既有 −16 口径。
            mastered = work / "mastered.wav"
            audio.master(target, mastered, integrated=-14.0, true_peak=-1.0)
            target = mastered
        sha = digest(target)
        master = media_dir / f"{sha}.wav"
        security.deliver(target, master)
    inputs["file:" + master.relative_to(root).as_posix()] = sha
    inputs["renderer"] = remotion.build_input_fingerprint(workspace_root=root.parent)["digest"]
    logger.info("通用作品准备：%d 幕，%d 帧，%d×%d，TTS 缓存命中 %d", len(scenes), cursor, size[0], size[1], hits)
    prepared = save_prepared(root, project=project, composition_id="ArticleExplainer", props=props,
        width=size[0], height=size[1], fps=FPS, duration_in_frames=cursor, inputs=inputs, subtitles=cues,
        audio={"segments": [{"sceneId": "master", "path": master.relative_to(root).as_posix(),
            "startFrame": 0, "durationInFrames": cursor, "sha256": sha}], "cacheHits": hits})
    # 阅读速度只报告不阻断，因此放在准备产物写盘之后：报告写不成也不该让准备失败。
    reading_pace.write(root, prepared)
    return prepared
