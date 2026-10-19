"""Housing annual time-series adapter for the shared project lifecycle."""
from __future__ import annotations

from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, save_prepared
from m2v.types.housing import housing, housing_render
from m2v.types.registry import VideoType


def _load(root: Path, project: dict) -> dict:
    return housing.load_project(root, project)


def validate(root: Path, project: dict) -> None:
    _load(root, project)


def prepare(root: Path, project: dict, *, voice: str | None = None, rate: str | None = None,
            rhythm: dict | None = None, profile: str | None = None) -> dict:
    # 房价成片契约要求无音轨，因此不接受音色、语速与韵律；参数只为统一类型接口。
    # 制作档位目前只由通用类型提供：显式拒绝，而不是静默按 standard 处理。
    if profile is not None:
        raise M2VError("住宅成片不支持制作档位；--profile 仅适用于 general 作品")
    series = _load(root, project)
    props = housing.build_render_props(series)
    return save_prepared(root, project=project, composition_id="HousingTimeSeries", props=props,
        width=housing.WIDTH, height=housing.HEIGHT, fps=housing.FPS,
        duration_in_frames=props["durationInFrames"], inputs=file_inputs(root, project))


def preview(root: Path, project: dict, *, limit_frames: int | None = None, start_seconds=0, end_seconds=None) -> Path:
    series = _load(root, project)
    return housing_render.render(root, series, preview=True, limit_frames=limit_frames, start_seconds=start_seconds, end_seconds=end_seconds)


def render(root: Path, project: dict) -> Path:
    series = _load(root, project)
    return housing_render.render(root, series)


def review_criteria(_root: Path, _project: dict, _prepared: dict) -> dict[str, str]:
    return {"visualQuality": "画面层级、手机可读性与曲线呈现",
            "dataContinuity": "年份、均价、计算口径和 2005 年断点标记准确",
            "silentOutput": "画面无字幕轨、旁白和音频流"}


TYPE = VideoType("housing-timeseries", validate, prepare, preview, render,
                 review_criteria=review_criteria, manual_review_available=True)
