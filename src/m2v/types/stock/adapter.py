"""在线素材剪辑类型的行为适配器：校验、准备、预演、渲染与评审项。

准备阶段把「检索结果」变成可渲染的时间轴：口播幕由真实语音定时长，其余幕按
目标时长自动分配；音轨要么是覆盖全片的单条母版轨（有口播或音床时），要么完全
没有音轨。素材文件按内容摘要登记为 ``file:`` 输入，因此素材、许可记录或 brief
任一变化都会让准备与评审过期。
"""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, load_current_prepared, save_prepared
from m2v.engine import audio as audio_engine
from m2v.engine import remotion
from m2v.engine import rhythm as rhythm_engine
from m2v.engine import sound as sound_contract
from m2v.engine import tts as tts_engine
from m2v.types import registry
from m2v.types.registry import VideoType
from m2v.types.stock import brief as brief_module
from m2v.types.stock import search as search_module
from m2v.types.stock import stock_render, timeline

MATERIAL = brief_module.MATERIAL
SEARCH_RECORD = brief_module.SEARCH_RECORD


def _load(root: Path, project: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    brief = brief_module.load(root, project)
    record = search_module.load_record(root, project, brief)
    return brief, record


def _overlaps(brief: dict[str, Any]) -> list[int]:
    return timeline.overlaps(brief)


def _assets(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [entry["asset"] for entry in record["scenes"]]


def _check_declared_capacity(brief: dict[str, Any], assets: list[dict[str, Any]]) -> None:
    """声明固定帧数的幕必须能被素材覆盖；提前失败，避免准备到一半才发现。"""
    fps = brief["fps"]
    for index, scene in enumerate(brief["scenes"]):
        fixed = scene.get("durationFrames")
        if fixed is None:
            continue
        available = fixed - _overlaps(brief)[index]
        capacity = timeline.asset_capacity(assets[index], timeline.trim_start_frames(scene, fps), fps)
        if capacity is not None and capacity < available:
            raise M2VError(
                f"幕 {scene['id']} 需要 {available / fps:.2f} 秒可用素材，"
                f"但 {assets[index]['path']} 只有 {capacity / fps:.2f} 秒；请降低 durationFrames 或换更长的素材")


def validate(root: Path, project: dict[str, Any]) -> None:
    brief, record = _load(root, project)
    _check_declared_capacity(brief, _assets(record))


def _render_props(brief: dict[str, Any], record: dict[str, Any], frames: list[int],
                  compiled: list[dict[str, Any]], subtitles: list[dict[str, Any]],
                  total_frames: int) -> dict[str, Any]:
    fps = brief["fps"]
    provider_name = record["provider"]["name"]
    assets = _assets(record)
    scenes = []
    for index, scene in enumerate(brief["scenes"]):
        asset = assets[index]
        entry = {
            "id": scene["id"],
            "startFrame": compiled[index]["startFrame"],
            "endFrame": compiled[index]["endFrame"],
            "durationInFrames": compiled[index]["durationInFrames"],
            "transitionFrames": compiled[index]["transitionFrames"],
            "providerName": provider_name,
            "asset": {
                "kind": asset["kind"],
                "path": asset["path"],
                "trimStartFrames": timeline.trim_start_frames(scene, fps),
                "author": asset["author"],
                "sourceUrl": asset["sourceUrl"],
                "license": asset["license"],
                "width": asset["width"],
                "height": asset["height"],
            },
            "motion": timeline.motion_for(index, brief["motion"]["photoZoom"]) if asset["kind"] == "photo" else None,
        }
        scenes.append(entry)
    return {"schemaVersion": 1, "topic": brief["topic"], "fps": fps, "width": brief["width"],
            "height": brief["height"], "durationInFrames": total_frames,
            "theme": brief["visual"]["theme"], "attribution": brief["visual"]["attribution"],
            "mediaBase": "", "compiledScenes": scenes, "subtitleCues": subtitles}


def prepare(root: Path, project: dict[str, Any], *, voice: str | None = None, rate: str | None = None,
            rhythm: dict | None = None) -> dict[str, Any]:
    brief, record = _load(root, project)
    assets = _assets(record)
    fps = brief["fps"]
    overlaps = _overlaps(brief)
    trims = [timeline.trim_start_frames(scene, fps) for scene in brief["scenes"]]
    _check_declared_capacity(brief, assets)

    inputs = file_inputs(root, project)
    record_file = search_module.record_path(root)
    inputs["file:" + SEARCH_RECORD] = hashlib.sha256(record_file.read_bytes()).hexdigest()
    for asset in assets:
        inputs["file:" + asset["path"]] = asset["sha256"]

    voice, rate = tts_engine.resolve(project, voice=voice, rate=rate)
    configured_tts = tts_engine.settings(project)
    rhythm = rhythm_engine.configure({**configured_tts.get("speech", {}), **(rhythm or {})}) \
        if (configured_tts.get("speech") or rhythm) else None
    if configured_tts or rhythm:
        inputs["tts"] = json.dumps({**configured_tts, **({"speech": rhythm} if rhythm else {})},
                                   ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    cache = root / "outputs" / "audio-cache"
    cache.mkdir(parents=True, exist_ok=True)
    resolved: list[int | None] = []
    speech_frames: list[int | None] = []
    scene_cues: list[list[dict[str, Any]]] = []
    scene_wavs: list[Path | None] = []
    for index, scene in enumerate(brief["scenes"]):
        narration = scene.get("narration")
        if not narration:
            resolved.append(scene.get("durationFrames"))
            speech_frames.append(None)
            scene_cues.append([])
            scene_wavs.append(None)
            continue
        speech = scene.get("speech") or {}
        scene_rate = speech.get("rate") or rate
        scene_rhythm = rhythm_engine.configure(speech) if speech else rhythm
        if speech:
            inputs[f"speech:{scene['id']}"] = rhythm_engine.fingerprint_of(
                {"speech": speech, "rate": scene_rate})
        speak = registry.get("article-narrative").prepare_narration
        if speak is None:
            raise M2VError("当前注册的视频类型未提供可复用的口播准备接口")
        wav, cues, _words, seconds, _hit = speak(narration, cache, voice=voice, rate=scene_rate,
                                                 rhythm=scene_rhythm)
        frames = math.ceil(seconds * fps)
        fixed = scene.get("durationFrames")
        available = (fixed - overlaps[index]) if fixed is not None else None
        if available is not None and frames > available:
            raise M2VError(
                f"幕 {scene['id']} 口播 {frames} 帧超出固定帧数可容纳的 {available} 帧；"
                f"请提高 durationFrames 或缩短口播")
        resolved.append(fixed if fixed is not None else frames + brief_module.READING_TAIL_FRAMES)
        speech_frames.append(frames)
        scene_cues.append(cues)
        scene_wavs.append(wav)

    frames = timeline.allocate(brief, assets, trims, resolved)
    compiled, total_frames = timeline.compile_scenes(brief, frames)
    timeline.check_total(brief, total_frames)

    # 音轨按编译后的帧边界排布：第 i 幕的音频从上一幕结束处开始，因此可用长度
    # 是「本幕时长 − 入场重叠」。这样整片旁白时间轴与画面时间轴逐帧对齐。
    part_lengths = [frames[index] - overlaps[index] for index in range(len(frames))]
    part_starts: list[int] = []
    cursor = 0
    for length in part_lengths:
        part_starts.append(cursor)
        cursor += length
    subtitles: list[dict[str, Any]] = []
    parts: list[tuple[Path | None, int]] = []
    speech_cues: list[dict[str, Any]] = []
    for index, scene in enumerate(brief["scenes"]):
        spoken = speech_frames[index]
        if spoken is None:
            parts.append((None, part_lengths[index]))
            continue
        # 口播 wav 是内容寻址的缓存文件，按准备接口返回的路径引用，不按幕名猜。
        parts.append((scene_wavs[index], spoken))
        parts.append((None, part_lengths[index] - spoken))
        for cue in scene_cues[index]:
            start = part_starts[index] + round(cue["start"] * fps)
            end = part_starts[index] + max(round(cue["start"] * fps) + 1, round(cue["end"] * fps))
            subtitles.append({"startFrame": start, "endFrame": end, "text": cue["text"]})
            speech_cues.append({"start": start / fps, "end": end / fps})
    # 拼接按帧推进：长度为零的段直接去掉，避免空段影响边界。
    parts = [(path, length) for path, length in parts if length > 0]

    assets_map = sound_contract.sound_assets(brief, brief_module.brief_path(root, project))
    audio_segments: list[dict[str, Any]] = []
    if any(path is not None for path in scene_wavs) or assets_map:
        duration = total_frames / fps
        narration_file = root / "outputs" / "audio.wav"
        with tempfile.TemporaryDirectory(prefix="m2v-stock-audio-", dir=root / "outputs") as audio_temporary:
            work = Path(audio_temporary)
            audio_engine.concatenate(parts, fps, work / "narration.wav")
            music = (brief.get("soundtrack") or {}).get("music")
            if music:
                audio_engine.mix(work / "narration.wav", narration_file, duration, speech_cues,
                                 (assets_map[music["sourceRef"]], music), [], work)
            else:
                audio_engine.normalize(work / "narration.wav", narration_file)
        digest = hashlib.sha256(narration_file.read_bytes()).hexdigest()
        audio_segments = [{"sceneId": "master", "path": "outputs/audio.wav", "startFrame": 0,
                           "durationInFrames": total_frames, "sha256": digest}]
        inputs["file:outputs/audio.wav"] = digest
        inputs["sound"] = json.dumps(
            {"soundtrack": brief.get("soundtrack"),
             "speech": [scene.get("speech") for scene in brief["scenes"]]},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    props = _render_props(brief, record, frames, compiled, subtitles, total_frames)
    entry = brief_module.brief_path(root, project)
    inputs["renderer"] = remotion.build_input_fingerprint(
        storyboard_path=entry, content_root=root.parent, workspace_root=root.parent)["digest"]
    return save_prepared(root, project=project, composition_id=stock_render.COMPOSITION_ID, props=props,
        width=brief["width"], height=brief["height"], fps=fps, duration_in_frames=total_frames,
        inputs=inputs, audio={"segments": audio_segments}, subtitles=subtitles)


def preview(root: Path, project: dict[str, Any], *, limit_frames: int | None = None) -> Path:
    return stock_render.render(root, project, load_current_prepared(root, project),
                               preview=True, limit_frames=limit_frames)


def render(root: Path, project: dict[str, Any]) -> Path:
    return stock_render.render(root, project, load_current_prepared(root, project), preview=False)


def review_criteria(_root: Path, _project: dict, prepared: dict) -> dict[str, str]:
    criteria = {
        "visualQuality": "素材清晰度、构图与竖屏可读性，无拉伸变形或重复素材",
        "editRhythm": "逐幕时长分配、静图推拉平移与幕间转场是否连贯",
        "sourceCompliance": "每幕来源、作者与许可留证与实际画面一致且可核验",
    }
    if prepared.get("audio", {}).get("segments"):
        criteria["audioSubtitles"] = "口播、音床响度与全片字幕边界是否同步"
    return criteria


TYPE = VideoType("stock-montage", validate, prepare, preview, render,
                 review_criteria=review_criteria, manual_review_required=True)
