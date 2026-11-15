"""五类统一 v9 代码场景的材料校验：入口与录制声明。

采集、构建与渲染由作品本地运行时执行；主项目只负责分镜阶段的声明校验。
"""
from __future__ import annotations

import json

from m2v.core.errors import M2VError

CAPTURE_FIELDS = {"mode", "timebase", "jobs", "blockFrames", "verifyFrames"}


def validate_entry(root, entry: object, props: object) -> None:
    """校验作品内 TSX 入口与 props；路径解析与存在性由分镜所在作品界定。"""
    if not isinstance(entry, str) or "\\" in entry:
        raise M2VError("code.entry 必须为 scenes/ 下的相对 TSX 路径")
    file = (root / entry).resolve()
    if (not entry.startswith("scenes/") or not file.is_relative_to((root / "scenes").resolve())
            or not file.is_relative_to(root.resolve()) or file.suffix != ".tsx" or not file.is_file()):
        raise M2VError("code.entry 必须引用作品 scenes/ 下存在的 TSX 文件")
    if not isinstance(props, dict):
        raise M2VError("code.props 必须为 JSON 对象")
    try:
        json.dumps(props, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise M2VError("code.props 必须为有限 JSON 值") from exc


def capture_settings(props: object) -> dict:
    """校验并返回 `content.props.capture` 的录制声明。

    `capture` 是作品 props 里的保留键，只控制作品本地录制，不参与画面数据。
    主项目校验字段与取值范围，实际采集由作品运行时执行。
    """
    if props is None:
        props = {}
    if not isinstance(props, dict):
        raise M2VError("content.props 必须为 JSON 对象")
    capture = props.get("capture", {})
    if not isinstance(capture, dict):
        raise M2VError("content.props.capture 必须为 JSON 对象")
    unknown = sorted(set(capture) - CAPTURE_FIELDS)
    if unknown:
        raise M2VError(f"content.props.capture 含未知字段：{'、'.join(unknown)}")
    mode = capture.get("mode", "sequential")
    if mode not in ("sequential", "pure-time"):
        raise M2VError("content.props.capture.mode 必须为 sequential 或 pure-time")
    timebase = capture.get("timebase", "global" if mode == "pure-time" else "local")
    if timebase not in ("local", "global"):
        raise M2VError("content.props.capture.timebase 必须为 local 或 global")
    if mode == "pure-time" and timebase != "global":
        raise M2VError("pure-time 场景必须使用全局时间；请移除 timebase: local")
    jobs = capture.get("jobs", 1)
    if type(jobs) is not int or not 1 <= jobs <= 4:
        raise M2VError("content.props.capture.jobs 必须为 1～4 的整数")
    block_frames = capture.get("blockFrames")
    if block_frames is not None and (type(block_frames) is not int or not 1 <= block_frames <= 36000):
        raise M2VError("content.props.capture.blockFrames 必须为 1～36000 的整数")
    verify_frames = capture.get("verifyFrames", 4)
    if type(verify_frames) is not int or not 2 <= verify_frames <= 4:
        raise M2VError("content.props.capture.verifyFrames 必须为 2～4 的整数")
    return {"mode": mode, "timebase": timebase, "jobs": jobs,
            "blockFrames": block_frames, "verifyFrames": verify_frames}


def validate_capture(props: object) -> None:
    """材料校验入口：非法录制声明在 validate/prepare 阶段就失败。"""
    capture_settings(props)
