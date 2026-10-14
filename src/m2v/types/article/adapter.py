"""Bridge the established article workflow into the project type protocol."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, save_prepared
from m2v.types.article import cli, media
from m2v.types.article.cli import _v4_model
from m2v.types.article.timeline_v4 import resolve_v4
from m2v.types.article import paths, production

from m2v.types.registry import VideoType


def _storyboard(root: Path, project: dict) -> Path:
    path = (root / project["materials"]["storyboard"]).resolve()
    if not path.is_file():
        raise M2VError(f"分镜不存在：{path}")
    return path


def _content_root(root: Path) -> Path | None:
    """Resolve the legacy article workspace from a canonical project location."""
    if root.parent.parent.name == "videos":
        return root.parent.parent.parent.resolve()
    if root.parent.name in {"videos", "examples"}:
        return root.parent.parent.resolve()
    return paths.content_root()


def _content_args(root: Path) -> list[str]:
    workspace = _content_root(root)
    return ["--content-root", str(workspace)] if workspace is not None else []


def _article(root: Path, project: dict) -> paths.ArticlePaths:
    """Resolve where this project's outputs belong.

    The canonical location is not always `<root>/outputs`: a project living in
    the shipped `examples/<slug>/` writes to `videos/examples/<slug>/outputs/`
    so that run records never land inside the versioned example directory.
    """
    return paths.for_storyboard(_storyboard(root, project), _content_root(root))


def validate(root: Path, project: dict) -> None:
    path = _storyboard(root, project)
    if cli.main_validate([str(path), "--strict", *_content_args(root)]):
        raise M2VError(f"文章 v4 分镜未通过校验：{path}")


def prepare(root: Path, project: dict, *, voice: str | None = None, rate: str | None = None,
            rhythm: dict | None = None) -> dict:
    path = _storyboard(root, project)
    validate(root, project)
    article = _article(root, project)
    media_path = article.media_manifest
    from m2v.engine import rhythm as rhythm_engine
    from m2v.engine import tts as shared_tts
    # 「命令行 > 作品配置 > 默认值」的优先级只在引擎里实现一次。
    voice, rate = shared_tts.resolve(project, voice=voice, rate=rate)
    args = ["--storyboard", str(path), "--out-dir", str(article.media_dir),
            "--voice", voice, "--rate", rate, *_content_args(root)]
    declared = shared_tts.settings(project).get("speech")
    if declared or rhythm:
        merged = rhythm_engine.configure({**(declared or {}), **(rhythm or {})})
        args.extend(["--rhythm", json.dumps(merged, ensure_ascii=False)])
    if cli.main_prepare(args):
        raise M2VError("文章媒体准备失败")
    loaded = media.load_media(media_path, path)
    effective = media.effective_storyboard(loaded)
    model = _v4_model(effective)
    timeline = resolve_v4(effective, loaded.data)
    props = {**effective, "mediaTimeline": loaded.data}
    inputs = file_inputs(root, project)
    inputs["media"] = hashlib.sha256(media_path.read_bytes()).hexdigest()
    return save_prepared(root, project=project, composition_id="M2V", props=props,
        width=model.width, height=model.height, fps=model.fps,
        duration_in_frames=timeline.total_frames, inputs=inputs,
        audio={"enabled": bool(loaded.data.get("audio"))})


def preview(root: Path, project: dict, *, limit_frames: int | None = None) -> Path:
    path = _storyboard(root, project)
    article = _article(root, project)
    output = article.preview_dir / "video.mp4"
    media_path = article.media_manifest
    args = ["--storyboard", str(path), "--purpose", "review", "--out", str(output), *_content_args(root)]
    if media_path.is_file():
        args += ["--media", str(media_path)]
    if limit_frames:
        args += ["--limit-frames", str(limit_frames)]
    if cli.main_render(args):
        raise M2VError("文章预演失败")
    return output


def render(root: Path, project: dict) -> Path:
    path = _storyboard(root, project)
    article = _article(root, project)
    if cli.main_render(["--storyboard", str(path), *_content_args(root)]):
        raise M2VError("文章正式渲染失败")
    return article.output_dir / "silent.mp4"


def review_gate(root: Path, project: dict) -> None:
    storyboard = _storyboard(root, project)
    article = _article(root, project)
    raw = json.loads(storyboard.read_text(encoding="utf-8"))
    media_path = article.media_manifest
    current = production.current_fingerprints(
        storyboard, media_path if media_path.is_file() else None, article
    )
    reason = production.gate(production.record_path(article), raw, current)
    if reason:
        raise M2VError(reason)
    reason = cli._aesthetic_render_gate(
        str(storyboard), _v4_model(raw), article, str(media_path) if media_path.is_file() else None
    )
    if reason:
        raise M2VError(reason)


def review_template(root: Path, project: dict) -> None:
    """Create the established article-specific production review record."""
    from m2v.types.article import workflow_cli

    storyboard = _storyboard(root, project)
    workspace = _content_root(root)
    args = ["template", "--storyboard", str(storyboard)]
    if workspace is not None:
        args += ["--content-root", str(workspace)]
    code = workflow_cli.main(args)
    if code:
        raise M2VError("文章类型评审模板生成失败")


def review_criteria(_root: Path, _project: dict, _prepared: dict) -> dict[str, str]:
    return {"visualQuality": "画面层级、手机可读性与图形论证",
            "narrativeContinuity": "文章阶段、对象状态和镜头连续性",
            "narrationAudio": "口播、字幕同步与声音完整性"}
    reason = cli._aesthetic_render_gate(str(storyboard), _v4_model(raw), article, None)
    if reason:
        raise M2VError(reason)


def audio_tracks(root: Path, project: dict, prepared: dict) -> list[dict]:
    if not prepared.get("audio", {}).get("enabled"):
        return []
    media_path = _article(root, project).media_manifest
    media_file = media.load_media(media_path, _storyboard(root, project))
    return [{"path": media_file.audio, "durationInFrames": prepared["durationInFrames"]}]


def prepare_narration(text: str, cache: Path, *, voice: str | None = None,
                      rate: str | None = None,
                      rhythm: dict | None = None) -> tuple[Path, list[dict], list[dict], float, bool]:
    """通用类型复用的口播准备入口；音色、语速与韵律由调用方按作品配置解析后传入。"""
    from m2v.engine import tts as shared_tts
    from m2v.types.article.prepare import _scene_audio
    cache.mkdir(parents=True, exist_ok=True)
    return _scene_audio(text, voice or shared_tts.DEFAULT_VOICE, rate or shared_tts.DEFAULT_RATE,
                        cache, False, rhythm=rhythm)


TYPE = VideoType("article-narrative", validate, prepare, preview, render,
                 review_gate=review_gate, review_criteria=review_criteria, review_template=review_template,
                 audio_tracks=audio_tracks, prepare_narration=prepare_narration)
