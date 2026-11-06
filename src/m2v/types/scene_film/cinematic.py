"""通用镜头、look 与画面主张的声明校验；镜头分级只用于采集资源分配。"""
from __future__ import annotations

from m2v.core.validate import fail, integer as _integer, number as _number, obj as _obj, text as _text
from m2v.core.video_config import DEFAULT_FPS
from m2v.core.project import subtitle_font_size


TIERS = ("hero", "major", "minor")
EASINGS = ("linear", "easeInCubic", "easeOutCubic", "easeInOutCubic",
           "easeInQuint", "easeOutQuint", "easeInOutQuint",
           "easeInExpo", "easeOutExpo", "easeInOutExpo",
           "easeInOutSine", "backOut")
#: 内置调色档名：`lut` 是**具名档**而不是外部 .cube 文件，录制期不取外网也不读作品目录。
LUTS = ("neutral", "deep-space", "teal-amber", "warm-film")
#: 运动模糊的子帧上限与 SSAA 上限。
MAX_SUBFRAMES = 4
MAX_SHOTS = 120
MAX_CLAIMS = 12
MAX_CLAIM_CHARS = 80
LOOK_NUMBERS = ("grain", "bloom", "dof", "vignette")
POST_NUMBERS = ("bloom", "dof", "grain", "vignette", "chromaticAberration")


def validate_project(project: dict) -> None:
    """旧档位声明一律拒绝，包括显式 null，避免静默改变制作语义。"""
    if "productionProfile" in project:
        fail("productionProfile", "制作档位已移除；请删除 productionProfile 并重新 prepare")
    subtitle_font_size(project)


def validate_claims(part: dict, path: str) -> None:
    """旁白段可选 `claims`：本段旁白声称的画面特征，用于预演时检查可见性。"""
    if "claims" not in part:
        return
    claims = part["claims"]
    if not isinstance(claims, list) or len(claims) > MAX_CLAIMS:
        fail(path + ".claims", f"必须包含 0～{MAX_CLAIMS} 项")
    seen: set[str] = set()
    for index, claim in enumerate(claims):
        item = path + f".claims[{index}]"
        _text(claim, item)
        if len(claim) > MAX_CLAIM_CHARS:
            fail(item, f"不能超过 {MAX_CLAIM_CHARS} 个字符")
        if claim in seen:
            fail(item, f"重复的画面特征：{claim}")
        seen.add(claim)


def validate_look(look, path: str) -> None:
    """作品 `content.props.look`：look bible 的代码化参数。"""
    obj = _obj(look, path, {"profile", "lut", "grain", "bloom", "dof", "vignette", "exposure", "motion"})
    _text(obj.get("profile"), path + ".profile")
    if "lut" in obj and obj["lut"] not in LUTS:
        fail(path + ".lut", f"必须是内置调色档：{'/'.join(LUTS)}")
    for name in LOOK_NUMBERS:
        if name in obj:
            _number(obj[name], 0, 1, f"{path}.{name}")
    if "exposure" in obj:
        _exposure(obj["exposure"], path + ".exposure")
    if "motion" in obj:
        motion = _obj(obj["motion"], path + ".motion", {"subframes", "supersample"})
        if "subframes" in motion:
            _integer(motion["subframes"], 1, MAX_SUBFRAMES, path + ".motion.subframes")
        if "supersample" in motion:
            _integer(motion["supersample"], 1, 2, path + ".motion.supersample")


def _exposure(value, path: str) -> None:
    obj = _obj(value, path, {"ev", "mode"})
    if "ev" in obj:
        _number(obj["ev"], -5, 5, path + ".ev")
    if "mode" in obj and obj["mode"] not in ("look", "shot"):
        fail(path + ".mode", "必须是 look/shot")


def _position(value, path: str) -> None:
    if not isinstance(value, list) or len(value) != 3:
        fail(path, "必须是 [x, y, z] 三元数组")
    for index, item in enumerate(value):
        _number(item, -1e6, 1e6, f"{path}[{index}]")


def _camera(value, path: str, fps: int) -> None:
    obj = _obj(value, path, {"path", "fov", "roll", "easing", "keyframes"})
    if "path" in obj:
        points = obj["path"]
        if not isinstance(points, list) or not 2 <= len(points) <= 64:
            fail(path + ".path", "必须包含 2～64 个路径点")
        for index, point in enumerate(points):
            _position(point, f"{path}.path[{index}]")
    if "fov" in obj:
        _number(obj["fov"], 1, 179, path + ".fov")
    if "roll" in obj:
        _number(obj["roll"], -180, 180, path + ".roll")
    if "easing" in obj and obj["easing"] not in EASINGS:
        fail(path + ".easing", f"必须是 {'/'.join(EASINGS)}")
    if "keyframes" in obj:
        keys = obj["keyframes"]
        if not isinstance(keys, list) or not 2 <= len(keys) <= 64:
            fail(path + ".keyframes", "必须包含 2～64 个关键帧")
        for index, key in enumerate(keys):
            item = _obj(key, f"{path}.keyframes[{index}]", {"frame", "position"})
            _integer(item.get("frame"), 0, 600 * fps, f"{path}.keyframes[{index}].frame")
            _position(item.get("position"), f"{path}.keyframes[{index}].position")


def _focus(value, path: str) -> None:
    obj = _obj(value, path, {"target", "distance", "from", "to", "aperture"})
    if "target" in obj:
        _text(obj["target"], path + ".target")
    for name in ("distance", "from", "to"):
        if name in obj:
            _number(obj[name], 0.01, 1e6, f"{path}.{name}")
    if ("from" in obj) != ("to" in obj):
        fail(path, "焦点拉移必须同时声明 from 与 to")
    if "aperture" in obj:
        _number(obj["aperture"], 0.7, 32, path + ".aperture")


def _post(value, path: str) -> None:
    obj = _obj(value, path, set(POST_NUMBERS) | {"lut"})
    for name in POST_NUMBERS:
        if name in obj:
            _number(obj[name], 0, 1, f"{path}.{name}")
    if "lut" in obj and obj["lut"] not in LUTS:
        fail(path + ".lut", f"必须是内置调色档：{'/'.join(LUTS)}")


def validate_shots(props: dict, path: str, *, fps: int = DEFAULT_FPS) -> list[dict]:
    """校验 `content.props.shots`，返回镜头列表；未声明时返回空列表。"""
    if "shots" not in props:
        return []
    shots = props["shots"]
    if not isinstance(shots, list) or not 1 <= len(shots) <= MAX_SHOTS:
        fail(path + ".shots", f"必须包含 1～{MAX_SHOTS} 项")
    seen: set[str] = set()
    for index, shot in enumerate(shots):
        item = path + f".shots[{index}]"
        obj = _obj(shot, item, {"id", "target", "tier", "segment", "startFrame", "endFrame",
                                "camera", "focus", "exposure", "post", "note", "cut"})
        identity = _text(obj.get("id"), item + ".id")
        if identity in seen:
            fail(item, f"重复镜头 ID：{identity}")
        seen.add(identity)
        _text(obj.get("target"), item + ".target")
        if obj.get("tier") not in TIERS:
            fail(item + ".tier", f"必须是 {'/'.join(TIERS)}")
        if "segment" in obj:
            _text(obj["segment"], item + ".segment")
        if "cut" in obj and type(obj["cut"]) is not bool:
            fail(item + ".cut", "必须是布尔值")
        start = _integer(obj.get("startFrame"), 0, 600 * fps, item + ".startFrame")
        end = _integer(obj.get("endFrame"), 1, 600 * fps, item + ".endFrame")
        if end <= start:
            fail(item, f"endFrame 必须大于 startFrame（{identity}）")
        if "camera" in obj:
            _camera(obj["camera"], item + ".camera", fps)
        if "focus" in obj:
            _focus(obj["focus"], item + ".focus")
        if "exposure" in obj:
            _exposure(obj["exposure"], item + ".exposure")
        if "post" in obj:
            _post(obj["post"], item + ".post")
        if "note" in obj:
            _text(obj["note"], item + ".note")
    return shots


def validate_shot_windows(scene_id: str, shots: list[dict], windows: dict[str, dict],
                          duration: int) -> None:
    """准备阶段：镜头时间窗必须落在它声明的位置上。

    镜头**声明** `segment` 时，它必须完整覆盖该旁白段的窗口——这是作者对「这个镜头
    讲的就是这段旁白」的承诺，也是本模块唯一能判定的对齐关系。没有声明的镜头只要求
    落在幕时长内：hero 镜头通常要跨过留白与相邻旁白，不要求镜头长度服从固定配额。

    真实分段时长来自 TTS，因此这条判定只能在准备阶段做，且必须在录制之前失败。
    """
    if not shots:
        return
    for shot in shots:
        where = f"scenes[{scene_id}].content.props.shots[{shot['id']}]"
        start, end = shot["startFrame"], shot["endFrame"]
        if end > duration:
            fail(where, f"时间窗 {start}～{end} 超出幕时长 {duration}")
        if "segment" not in shot:
            continue
        window = windows.get(shot["segment"])
        if window is None:
            fail(where, f"引用了本幕不存在的旁白段：{shot['segment']}")
        if start > window["startFrame"] or end < window["endFrame"]:
            fail(where, f"时间窗 {start}～{end} 没有覆盖声明的旁白段 {shot['segment']}"
                        f"（{window['startFrame']}～{window['endFrame']}）")
