"""五类统一 v9 全画布代码场景与素材制作的类型适配器。"""
from pathlib import Path
from m2v.type_system.registry import VideoType
from . import cinematic, explainer, explainer_prepare, explainer_render, explainer_review


def validate(root: Path, project: dict) -> None:
    cinematic.validate_project(project)
    source = explainer.load(root, project)
    if not explainer.topic_input(source):
        explainer.source_file(root, project)


def prepare(root: Path, project: dict, **options) -> dict:
    return explainer_prepare.prepare(root, project, **options)


def preview(root: Path, project: dict, *, limit_frames=None, start_seconds=0, end_seconds=None,
            jobs: int = 1) -> Path:
    return explainer_render.render(root, project, preview=True, limit_frames=limit_frames,
                                   start_seconds=start_seconds, end_seconds=end_seconds, jobs=jobs)


def render(root: Path, project: dict, *, jobs: int = 1) -> Path:
    return explainer_render.render(root, project, jobs=jobs)


def pre_render_check(root: Path, project: dict) -> None:
    validate(root, project)
    explainer_review.require_input(root, project)
    explainer_render.current(root, project)


def make_type(name: str) -> VideoType:
    return VideoType(name, validate, prepare, preview, render,
                     pre_render_check=pre_render_check,
                     prepared_check=explainer_render.current, supports_render_jobs=True)
