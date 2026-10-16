"""通用作品画幅与字幕几何的读取入口。

数据在 `web/src/frames.json`：Python 准备、浏览器量测、前端 SDK 与合成层读**同一份**。
过去字幕盒写在 `tokens.css`，量测边界又各写一份常量，「改一个值」只会改到画面那一半，
判据那一半留在原处不动——两边静默漂移，没有任何一处报错。

画幅只支持两种：1920×1080 横屏与 1080×1920 竖屏，未声明时取横屏。字幕几何按画幅给出，
横屏取值是竖屏数值乘 1080/1920 的结果，比例关系由测试守着，避免只改一边。
"""
from __future__ import annotations

import json
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.engine.contract_page import web_dir

#: 画幅清单在 `web/` 下的相对位置。
MANIFEST_RELATIVE = Path("src/frames.json")

#: 字幕必须齐全的字段。取值级校验在这里做，因为消费方有三个（SDK、合成、量测）。
_SUBTITLE_INTEGERS = ("x", "y", "width", "height", "fontSize")
_SUBTITLE_COLORS = ("textColor", "plateColor")

#: 画幅的两个整数边长。
_FRAME_FIELDS = ("width", "height")


def manifest_path(repo_root: Path | None = None) -> Path:
    return web_dir(repo_root) / MANIFEST_RELATIVE


def manifest(repo_root: Path | None = None) -> dict:
    """画幅清单原文。结构不对时明确失败，不猜。"""
    path = manifest_path(repo_root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise M2VError(f"无法读取画幅清单 {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise M2VError(f"画幅清单 {path} 不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise M2VError(f"画幅清单 {path} 的 schemaVersion 必须为 1")
    frames = data.get("frames")
    if not isinstance(frames, list) or not frames:
        raise M2VError(f"画幅清单 {path} 缺少非空的 frames 数组")
    sizes = []
    for index, frame in enumerate(frames):
        _entry(frame, f"{path} 的 frames[{index}]")
        sizes.append(_key(_size(frame)))
    if len(set(sizes)) != len(sizes):
        raise M2VError(f"画幅清单 {path} 存在重复画幅")
    if data.get("default") not in sizes:
        raise M2VError(f"画幅清单 {path} 的 default 不在 frames 里：{data.get('default')!r}")
    return data


def _size(frame: dict) -> tuple[int, int]:
    return frame["width"], frame["height"]


def _key(size: tuple[int, int]) -> str:
    return f"{size[0]}x{size[1]}"


def _entry(frame: object, where: str) -> None:
    if not isinstance(frame, dict):
        raise M2VError(f"{where} 不是对象")
    for field in _FRAME_FIELDS:
        value = frame.get(field)
        if type(value) is not int or value <= 0:
            raise M2VError(f"{where} 的 {field} 必须是正整数")
    subtitle = frame.get("subtitle")
    if not isinstance(subtitle, dict):
        raise M2VError(f"{where} 缺少 subtitle 对象")
    unknown = sorted(set(subtitle) - set(_SUBTITLE_INTEGERS) - set(_SUBTITLE_COLORS) - {"lineHeight"})
    if unknown:
        raise M2VError(f"{where} 的 subtitle 含未知字段：{'、'.join(unknown)}")
    for field in _SUBTITLE_INTEGERS:
        value = subtitle.get(field)
        if type(value) is not int or value < 0:
            raise M2VError(f"{where} 的 subtitle.{field} 必须是非负整数")
    leading = subtitle.get("lineHeight")
    if isinstance(leading, bool) or not isinstance(leading, (int, float)) or leading <= 0:
        raise M2VError(f"{where} 的 subtitle.lineHeight 必须是正数")
    for field in _SUBTITLE_COLORS:
        value = subtitle.get(field)
        if not isinstance(value, str) or not value.startswith("#") or len(value) != 7:
            raise M2VError(f"{where} 的 subtitle.{field} 必须是 #RRGGBB 颜色")
    if subtitle["x"] + subtitle["width"] > frame["width"] or subtitle["y"] + subtitle["height"] > frame["height"]:
        raise M2VError(f"{where} 的字幕安全区超出画布")


def sizes(repo_root: Path | None = None) -> tuple[tuple[int, int], ...]:
    """全部受支持画幅，按清单顺序。"""
    return tuple(_size(frame) for frame in manifest(repo_root)["frames"])


def default(repo_root: Path | None = None) -> tuple[int, int]:
    """尺寸均省略时使用的画幅。"""
    for frame in manifest(repo_root)["frames"]:
        if _key(_size(frame)) == manifest(repo_root)["default"]:
            return _size(frame)
    raise M2VError("画幅清单的 default 无法解析")  # pragma: no cover - manifest() 已保证可达


def normalize(width: object, height: object, repo_root: Path | None = None) -> tuple[int, int]:
    """把分镜声明的尺寸规范化为受支持画幅。

    两边都省略取默认横屏；只写一边、类型不对或组合不受支持都明确失败——
    静默补一半会让作品尺寸变成「作者没写、系统猜的」。
    """
    if width is None and height is None:
        return default(repo_root)
    if width is None or height is None:
        raise M2VError("width/height 必须同时省略或同时提供整数")
    for name, value in (("width", width), ("height", height)):
        if type(value) is not int:
            raise M2VError(f"{name} 必须是整数")
    supported = sizes(repo_root)
    if (width, height) not in supported:
        allowed = "、".join(_key(item) for item in supported)
        raise M2VError(f"width/height 仅支持 {allowed}")
    return width, height


def spec(width: int, height: int, repo_root: Path | None = None) -> dict:
    """某个画幅的完整取值：边长加字幕安全区与字幕样式。"""
    for frame in manifest(repo_root)["frames"]:
        if _size(frame) == (width, height):
            subtitle = dict(frame["subtitle"])
            return {"width": width, "height": height,
                    "subtitle": {"safeArea": {key: subtitle[key] for key in ("x", "y", "width", "height")},
                                 "fontSize": subtitle["fontSize"], "lineHeight": subtitle["lineHeight"],
                                 "textColor": subtitle["textColor"], "plateColor": subtitle["plateColor"]}}
    raise M2VError(f"画幅清单里没有 {_key((width, height))}")
