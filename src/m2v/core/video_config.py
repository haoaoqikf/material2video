"""跨语言帧率配置：专用类型固定帧率，通用类型按作品选择30/60。"""
import json
from pathlib import Path
from m2v.core.assets import REPOSITORY_ROOT

from m2v.core.errors import M2VError

_CONFIG = json.loads((REPOSITORY_ROOT / "web/src/video-config.json").read_text(encoding="utf-8"))
FPS: int = _CONFIG["fps"]
DRIVING_ROUTE_FPS: int = _CONFIG["drivingRoute"]["defaultFps"]
BUILDING_FPS: int = _CONFIG["buildingConstruction"]["defaultFps"]
VEHICLE_SHOWCASE_FPS: int = _CONFIG["vehicleShowcase"]["defaultFps"]
ROAD_TRIP_FPS: int = _CONFIG["roadTrip"]["defaultFps"]
GENERAL_DEFAULT_FPS: int = _CONFIG["general"]["defaultFps"]
GENERAL_ALLOWED_FPS: tuple[int, ...] = tuple(_CONFIG["general"]["allowedFps"])


def validate_general_fps(value: object, field: str = "fps") -> int:
    if type(value) is not int or value not in GENERAL_ALLOWED_FPS:
        allowed = "或".join(str(fps) for fps in GENERAL_ALLOWED_FPS)
        raise M2VError(f"{field} 必须为整数{allowed}")
    return value


def general_fps(project: dict, storyboard: dict) -> int:
    """仅解析显式值，不把缺省值误当成与另一处声明冲突。"""
    output = project.get("output", {})
    declarations = [("output.fps", output["fps"])] if "fps" in output else []
    if "fps" in storyboard:
        declarations.append(("storyboard.fps", storyboard["fps"]))
    for field, value in declarations:
        validate_general_fps(value, field)
    if len({value for _, value in declarations}) > 1:
        raise M2VError("output.fps 与 storyboard.fps 必须一致")
    return declarations[0][1] if declarations else GENERAL_DEFAULT_FPS


def default_fps(video_type: str) -> int:
    if video_type == "general":
        return GENERAL_DEFAULT_FPS
    if video_type == "driving-route":
        return DRIVING_ROUTE_FPS
    if video_type == "building-construction":
        return BUILDING_FPS
    if video_type == "vehicle-showcase":
        return VEHICLE_SHOWCASE_FPS
    if video_type == "road-trip":
        return ROAD_TRIP_FPS
    return FPS


def project_fps(root: Path, project: dict, *, allow_missing_storyboard: bool = False) -> int:
    """在没有已加载分镜的入口核对实际帧率，不依赖业务类型层。"""
    if project["type"] != "general":
        return default_fps(project["type"])
    try:
        storyboard = json.loads((root / project["materials"]["storyboard"]).read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        if allow_missing_storyboard:
            return general_fps(project, {})
        raise M2VError("缺少分镜，无法核对帧率") from exc
    except (OSError, ValueError, KeyError) as exc:
        raise M2VError("无法读取分镜帧率；请检查 storyboard 材料") from exc
    if not isinstance(storyboard, dict):
        raise M2VError("分镜必须为对象")
    return general_fps(project, storyboard)
#: 未声明阅读停留时，通用 v8 在每个末段后保留的默认时长（秒）。
READING_TAIL_SECONDS: float = 0.4
