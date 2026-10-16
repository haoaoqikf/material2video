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
    # 正式导出验证完整预演，不依赖可选人工评审。
    from m2v.core.preview import require_preview
    require_preview(root, prepared)


TYPE = VideoType("general", validate, prepare, preview, render,
                 review_gate=review_gate, review_criteria=explainer_review.criteria,
                 prepared_check=explainer_render.current)
