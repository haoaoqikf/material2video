"""讲解主题规格（颜色、排版、动效）的读取入口。

数据在 `web/src/themes.json`：前端 `palette.ts` 与这里读**同一份**。准备阶段要用主题的
动效帧数编译时间轴（转场时长与阅读停留都进 `minimum` 判据），Python 侧若另存一份，
「改主题」只会改到画面那一半，判据那一半留在常量里不跟着动。

这里只暴露编排需要的部分（主题名单、默认主题、动效帧数）。颜色与排版由前端直接读，
不经过 Python——把它们搬进准备产物会让「调一个色值」也要重新准备。
"""
from __future__ import annotations

import json
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.engine.contract_page import web_dir

#: 主题清单在 `web/` 下的相对位置。
MANIFEST_RELATIVE = Path("src/themes.json")

#: 动效帧数的字段定义：名 → 是否允许缺省。缺省表示不覆盖，沿用分镜或契约常量。
_MOTION_FIELDS = ("entranceFrames", "holdFrames", "transitionFrames")


def manifest_path(repo_root: Path | None = None) -> Path:
    return web_dir(repo_root) / MANIFEST_RELATIVE


def manifest(repo_root: Path | None = None) -> dict:
    """主题清单原文。字段缺失或结构不对时明确失败，不猜。"""
    path = manifest_path(repo_root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise M2VError(f"无法读取主题清单 {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise M2VError(f"主题清单 {path} 不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("themes"), dict) or not data["themes"]:
        raise M2VError(f"主题清单 {path} 缺少非空的 themes 对象")
    if data.get("default") not in data["themes"]:
        raise M2VError(f"主题清单 {path} 的 default 不在 themes 里：{data.get('default')!r}")
    return data


def names(repo_root: Path | None = None) -> tuple[str, ...]:
    """全部主题名，按清单顺序。"""
    return tuple(manifest(repo_root)["themes"])


def default(repo_root: Path | None = None) -> str:
    """未声明 `visual.theme` 时使用的主题。"""
    return manifest(repo_root)["default"]


def motion(theme: str, repo_root: Path | None = None) -> dict[str, int]:
    """主题的动效帧数。

    `transitionFrames` 可以缺省：缺省表示**不覆盖**分镜里每幕声明的转场时长，
    这样只有显式声明该字段的主题才接管转场。
    """
    data = manifest(repo_root)
    spec = data["themes"].get(theme)
    if spec is None:
        raise M2VError(f"未知主题 {theme!r}；可选：{'、'.join(data['themes'])}")
    values = spec.get("motion")
    if not isinstance(values, dict):
        raise M2VError(f"主题 {theme} 缺少 motion 对象")
    unknown = sorted(set(values) - set(_MOTION_FIELDS))
    if unknown:
        raise M2VError(f"主题 {theme} 的 motion 含未知字段：{'、'.join(unknown)}")
    for field in ("entranceFrames", "holdFrames"):
        if field not in values:
            raise M2VError(f"主题 {theme} 的 motion 缺少 {field}")
    for field, value in values.items():
        if type(value) is not int or value < 1:
            raise M2VError(f"主题 {theme} 的 motion.{field} 必须为正整数，实际是 {value!r}")
    return dict(values)
