"""文章 v6 统一讲解与素材制作的类型适配器。"""
from pathlib import Path
from m2v.types.registry import VideoType
from . import explainer, explainer_prepare, explainer_render, explainer_review


def validate(root: Path, project: dict) -> None:
    source = explainer.load(root, project)
    if not explainer.topic_input(source):
        explainer.source_file(root, project)


def prepare(root: Path, project: dict, **options) -> dict:
    return explainer_prepare.prepare(root, project, **options)


def preview(root: Path, project: dict, *, limit_frames=None) -> Path:
    return explainer_render.render(root, project, preview=True, limit_frames=limit_frames)


def render(root: Path, project: dict) -> Path:
    return explainer_render.render(root, project)


def review_gate(root: Path, project: dict) -> None:
    validate(root, project)
    explainer_review.require_input(root, project)
    prepared = explainer_render.current(root, project)
    # 独立导出与嵌入均验证完整预演，不依赖可选人工评审。
    from m2v.core.preview import require_preview
    require_preview(root, prepared)


def audio_tracks(root: Path, project: dict, prepared: dict) -> list[dict]:
    current = explainer_render.current(root, project)
    return [{"path": root / segment["path"], "durationInFrames": segment["durationInFrames"]}
            for segment in current["audio"]["segments"]]


def prepare_narration(text: str, cache: Path, *, voice=None, rate=None, rhythm=None):
    # general 仍复用共享口播缓存契约，避免文章升级使通用语音缓存失效。
    # contract_version=3 是通用与素材类型的缓存键，改动会让已缓存语音全部失效。
    from m2v.engine import tts
    cache.mkdir(parents=True, exist_ok=True)
    voice, rate = tts.resolve({}, voice=voice, rate=rate)
    return tts.scene_audio(text, voice, rate, cache, contract_version=3, rhythm=rhythm)


TYPE = VideoType("article-narrative", validate, prepare, preview, render,
                 review_gate=review_gate, review_criteria=explainer_review.criteria,
                 audio_tracks=audio_tracks, prepare_narration=prepare_narration,
                 prepared_check=explainer_render.current)
