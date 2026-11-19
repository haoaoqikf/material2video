"""五类作品共享的跨语言帧率配置。"""
import json
from pathlib import Path
from film_runtime.core.assets import REPOSITORY_ROOT

from film_runtime.core.errors import VideoError

_CONFIG = json.loads((REPOSITORY_ROOT / "src/video-config.json").read_text(encoding="utf-8"))
FPS: int = _CONFIG["fps"]
DEFAULT_FPS: int = _CONFIG["sceneFilm"]["defaultFps"]
ALLOWED_FPS: tuple[int, ...] = tuple(_CONFIG["sceneFilm"]["allowedFps"])


def validate_fps(value: object, field: str = "fps") -> int:
    if type(value) is not int or value not in ALLOWED_FPS:
        allowed = "或".join(str(fps) for fps in ALLOWED_FPS)
        raise VideoError(f"{field} 必须为整数{allowed}")
    return value


def storyboard_fps(project: dict, storyboard: dict) -> int:
    """仅解析显式值，不把缺省值误当成与另一处声明冲突。"""
    output = project.get("output", {})
    declarations = [("output.fps", output["fps"])] if "fps" in output else []
    if "fps" in storyboard:
        declarations.append(("storyboard.fps", storyboard["fps"]))
    for field, value in declarations:
        validate_fps(value, field)
    if len({value for _, value in declarations}) > 1:
        raise VideoError("output.fps 与 storyboard.fps 必须一致")
    return declarations[0][1] if declarations else DEFAULT_FPS


def default_fps(video_type: str) -> int:
    return DEFAULT_FPS


def project_fps(root: Path, project: dict, *, allow_missing_storyboard: bool = False) -> int:
    """在没有已加载分镜的入口核对实际帧率，不依赖业务类型层。"""
    try:
        storyboard = json.loads((root / project["materials"]["storyboard"]).read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        if allow_missing_storyboard:
            return storyboard_fps(project, {})
        raise VideoError("缺少分镜，无法核对帧率") from exc
    except (OSError, ValueError, KeyError) as exc:
        raise VideoError("无法读取分镜帧率；请检查 storyboard 材料") from exc
    if not isinstance(storyboard, dict):
        raise VideoError("分镜必须为对象")
    return storyboard_fps(project, storyboard)
#: 未声明阅读停留时，统一 v9 在每个末段后保留的默认时长（秒）。
READING_TAIL_SECONDS: float = 0.4
