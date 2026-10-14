"""按实际分段音频编译 v5；所有可见时序只在准备阶段解析。"""
from __future__ import annotations

import copy
import hashlib
import logging
import math
import tempfile
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, save_prepared
from m2v.engine import audio, remotion, rhythm as rhythm_engine, tts
from . import explainer as contract, explainer_review

logger = logging.getLogger(__name__)


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def implementation_digest() -> str:
    """准备/量测/混音代码也是交付契约，改动后须重新准备和评审。"""
    from m2v.core.fingerprints import fingerprint
    from . import adapter, explainer_render
    modules = (contract, explainer_review, explainer_render, adapter, audio, tts, rhythm_engine)
    files = [Path(module.__file__) for module in modules] + [Path(__file__)]
    return fingerprint({file.name: digest(file) for file in files})


def prepare(root: Path, project: dict, *, voice=None, rate=None, rhythm=None) -> dict:
    source = contract.load(root, project)
    explainer_review.require_input(root, project)
    voice, rate = tts.resolve(project, voice=voice, rate=rate)
    declared = tts.settings(project).get("speech")
    rhythm = rhythm_engine.configure({**(declared or {}), **(rhythm or {})}) if declared or rhythm else None
    cache = root / "outputs/audio-cache"
    cache.mkdir(parents=True, exist_ok=True)
    props = copy.deepcopy(source)
    props["visual"] = {"theme": source.get("visual", {}).get("theme", "dark")}
    cursor = hits = 0
    parts, cues, compiled = [], [], []
    inputs = file_inputs(root, project)
    inputs["implementation"] = implementation_digest()
    article = contract.source_file(root, project)
    inputs["file:" + article.relative_to(root).as_posix()] = digest(article)
    inputs["file:outputs/input-review.json"] = digest(root / "outputs/input-review.json")
    for scene in props["scenes"]:
        fade = contract.FADE_FRAMES if scene.get("transition") == "fade" else 0
        # 先保留前幕完整 12 帧阅读尾段，再淡化；下一幕声音延迟至淡化结束。
        start = cursor
        speech_start = start + fade
        if fade:
            compiled[-1]["endFrame"] += fade
            compiled[-1]["durationInFrames"] += fade
            parts.append((None, fade))
        scene["startFrame"], scene["transitionFrames"] = start, fade
        windows = {}
        for segment in scene["narrationSegments"]:
            wav, local_cues, _words, seconds, hit = tts.scene_audio(
                segment["text"], voice, rate, cache, contract_version=5, rhythm=rhythm)
            if not math.isfinite(seconds) or seconds <= 0:
                raise M2VError(f"旁白 {segment['id']} 音频时长无效")
            frames = math.ceil(seconds * contract.FPS)
            windows[segment["id"]] = {"startFrame": speech_start, "endFrame": speech_start + frames}
            for cue in local_cues:
                cs = max(0, min(frames - 1, round(cue["start"] * contract.FPS)))
                ce = max(cs + 1, min(frames, round(cue["end"] * contract.FPS)))
                cues.append({"startFrame": speech_start + cs, "endFrame": speech_start + ce, "text": cue["text"]})
            parts.append((wav, frames))
            speech_start += frames
            hits += int(hit)
        scene["segmentWindows"] = windows
        scene["endFrame"] = speech_start + contract.READING_TAIL
        scene["durationInFrames"] = scene["endFrame"] - start
        parts.append((None, contract.READING_TAIL))
        cursor = scene["endFrame"]
        if cursor > contract.MAX_FRAMES:
            logger.warning("讲解准备超限：%d 帧，场景 %s", cursor, scene["id"])
            raise M2VError(f"讲解全片 {cursor / contract.FPS:.2f} 秒，超过 60 秒；请调整文本或正常语速，不得截断口播")
        if scene["template"] == "cause":
            scene["levels"] = contract.graph_levels(scene["content"])
        if scene["template"] == "image":
            image = contract.local_file(root, scene["content"]["src"], "image.src")
            inputs["file:" + image.relative_to(root).as_posix()] = digest(image)
            # 内嵌与离线契约页均无需依赖作品路径或服务器挂载。
            import base64
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[image.suffix.lower()]
            scene["imageSource"] = f"data:{mime};base64," + base64.b64encode(image.read_bytes()).decode("ascii")
        compiled.append(scene)
    props["compiledScenes"], props["subtitleCues"], props["durationInFrames"] = compiled, cues, cursor
    del props["scenes"]
    media_dir = root / "outputs/media"
    media_dir.mkdir(parents=True, exist_ok=True)
    # 使用内容摘要媒体名，准备失败不会覆盖旧准备所引用的音轨。
    with tempfile.TemporaryDirectory(dir=media_dir) as temporary:
        target = Path(temporary) / "audio.wav"
        raw = Path(temporary) / "raw.wav"
        audio.concatenate(parts, contract.FPS, raw)
        audio.normalize(raw, target)
        sha = digest(target)
        master = media_dir / f"{sha}.wav"
        target.replace(master)
    inputs["file:" + master.relative_to(root).as_posix()] = sha
    entry = root / project["materials"]["storyboard"]
    inputs["renderer"] = remotion.build_input_fingerprint(storyboard_path=entry,
        content_root=root.parent, workspace_root=root.parent)["digest"]
    logger.info("讲解准备：%d 幕，%d 帧，TTS 缓存命中 %d", len(compiled), cursor, hits)
    return save_prepared(root, project=project, composition_id="ArticleExplainer", props=props,
        width=contract.WIDTH, height=contract.HEIGHT, fps=contract.FPS, duration_in_frames=cursor,
        inputs=inputs, subtitles=cues,
        audio={"segments": [{"sceneId": "master", "path": master.relative_to(root).as_posix(),
            "startFrame": 0, "durationInFrames": cursor, "sha256": sha}], "cacheHits": hits})
