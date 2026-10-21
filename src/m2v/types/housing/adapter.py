"""住宅年度均价适配器：材料校验 + 无声类型生命周期。"""
from __future__ import annotations

from pathlib import Path

from m2v.types.housing import housing, housing_render
from m2v.types.silent_type import SilentTypeSpec, build_silent_type


def _load(root: Path, project: dict) -> dict:
    return housing.load_project(root, project)


def _review_criteria(_root: Path, _project: dict, _prepared: dict) -> dict[str, str]:
    return {"visualQuality": "画面层级、手机可读性与曲线呈现",
            "dataContinuity": "年份、均价、计算口径和 2005 年断点标记准确",
            "silentOutput": "画面无字幕轨、旁白和音频流"}


TYPE = build_silent_type(SilentTypeSpec(
    name="housing-timeseries",
    composition_id="HousingTimeSeries",
    width=housing.WIDTH,
    height=housing.HEIGHT,
    fps=housing.FPS,
    load=_load,
    build_props=housing.build_render_props,
    duration_frames=lambda _docs, props: props["durationInFrames"],
    render=housing_render.render,
    review_criteria=_review_criteria,
    manual_review_available=True,
))

#: 生命周期入口同时以模块级名字暴露：测试与手工排查直接调用它们。
validate, prepare, preview, render = TYPE.validate, TYPE.prepare, TYPE.preview, TYPE.render
review_criteria = TYPE.review_criteria
