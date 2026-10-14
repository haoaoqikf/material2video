"""在线素材剪辑类型的作品材料：``brief.json`` 的读取、默认值与严格校验。

这是本类型唯一的人手材料。校验在这里一次做完：字段形状、取值区间、逐幕关键词、
可选口播与音床；检索与准备都只读这份已归一化的结果，避免同一份规则在两处各写
一遍而慢慢走偏。
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError
from m2v.engine import sound as sound_contract
from m2v.types.article.storyboard import Report

MATERIAL = "brief.json"
SEARCH_RECORD = "outputs/footage-search.json"
ASSET_DIR = "assets/stock"

FPS = 30
WIDTH = 1080
HEIGHT = 1920

#: 口播幕末尾的阅读停留：与文章、通用类型一致，避免字幕刚消失画面就切走。
READING_TAIL_FRAMES = 12

#: 可选逐幕口播的韵律字段：与共享声音契约的 speech 字段保持同一套。
SPEECH_FIELDS = {"rate", "pauseBeforeMs", "pauseAfterMs"}

ORIENTATIONS = {"portrait", "landscape", "square", "any"}
MEDIA_KINDS = ("video", "photo")
TRANSITIONS = {"cut", "crossfade"}

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULTS: dict[str, Any] = {
    "durationToleranceSeconds": 2,
    "provider": {
        "name": "pexels",
        "apiBase": "https://api.pexels.com",
        "apiKeyEnv": "M2V_PEXELS_API_KEY",
        "orientation": "portrait",
        "perPage": 15,
        "media": ["video", "photo"],
        "minClipSeconds": 2.5,
        "maxClipSeconds": 8,
        "allowReuse": False,
    },
    "visual": {"theme": "dark"},
    "motion": {"photoZoom": 1.12},
}


def _merged(raw: Any, defaults: dict[str, Any], where: str) -> dict[str, Any]:
    """按默认值补全对象字段；未知字段留给校验报错，不静默丢弃。"""
    if not isinstance(raw, dict):
        raise M2VError(f"{where} 必须是对象")
    return {**defaults, **raw}


def _require_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise M2VError(f"{where} 必须是非空字符串")
    return value


def _require_number(value: Any, where: str, *, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise M2VError(f"{where} 必须是有限数值")
    if not low <= float(value) <= high:
        raise M2VError(f"{where} 必须处于 {low} 至 {high} 之间：{value}")
    return float(value)


def _require_int(value: Any, where: str, *, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise M2VError(f"{where} 必须是 {low} 至 {high} 之间的整数：{value!r}")
    return value


def _validate_speech(raw: Any, where: str) -> None:
    if not isinstance(raw, dict):
        raise M2VError(f"{where} 必须是对象")
    unknown = set(raw) - SPEECH_FIELDS
    if unknown:
        raise M2VError(f"{where} 含未知字段：{'、'.join(sorted(unknown))}")
    if "rate" in raw and not sound_contract.valid_rate(raw["rate"]):
        raise M2VError(f"{where}.rate 必须是 −50% 至 +50% 的有符号百分比")
    for key in ("pauseBeforeMs", "pauseAfterMs"):
        if key in raw:
            _require_int(raw[key], f"{where}.{key}", low=0, high=2000)


def _validate_scene(raw: Any, index: int, seen: set[str]) -> dict[str, Any]:
    where = f"scenes[{index}]"
    if not isinstance(raw, dict):
        raise M2VError(f"{where} 必须是对象")
    allowed = {"id", "keywords", "narration", "durationFrames", "speech", "transition", "assetId",
               "trimStartSeconds", "media"}
    unknown = set(raw) - allowed
    if unknown:
        raise M2VError(f"{where} 含未知字段：{'、'.join(sorted(unknown))}")
    scene_id = _require_text(raw.get("id"), f"{where}.id")
    if scene_id in seen:
        raise M2VError(f"幕 ID 重复：{scene_id}")
    seen.add(scene_id)
    keywords = raw.get("keywords")
    if (not isinstance(keywords, list) or not keywords
            or any(not isinstance(word, str) or not word.strip() for word in keywords)):
        raise M2VError(f"{where}.keywords 必须是非空字符串数组")
    if "narration" in raw:
        _require_text(raw["narration"], f"{where}.narration")
    if "durationFrames" in raw:
        _require_int(raw["durationFrames"], f"{where}.durationFrames", low=1, high=FPS * 600)
    if "speech" in raw:
        if "narration" not in raw:
            raise M2VError(f"{where}.speech 只对声明了口播的幕有意义")
        _validate_speech(raw["speech"], f"{where}.speech")
    if "media" in raw and raw["media"] not in MEDIA_KINDS:
        raise M2VError(f"{where}.media 只支持 {'、'.join(MEDIA_KINDS)}")
    if "assetId" in raw and not (isinstance(raw["assetId"], (str, int)) and not isinstance(raw["assetId"], bool)):
        raise M2VError(f"{where}.assetId 必须是字符串或整数来源 ID")
    if "trimStartSeconds" in raw:
        _require_number(raw["trimStartSeconds"], f"{where}.trimStartSeconds", low=0, high=600)
        if "media" in raw and raw["media"] != "video":
            raise M2VError(f"{where}.trimStartSeconds 只对视频素材有意义")
    transition = raw.get("transition")
    if transition is not None:
        if not isinstance(transition, dict) or set(transition) - {"type", "frames"}:
            raise M2VError(f"{where}.transition 只支持 type 与 frames")
        kind = transition.get("type", "cut")
        if kind not in TRANSITIONS:
            raise M2VError(f"{where}.transition.type 只支持 cut/crossfade")
        frames = transition.get("frames", 12 if kind == "crossfade" else 0)
        if type(frames) is not int or frames < 0 or frames > FPS * 5:
            raise M2VError(f"{where}.transition.frames 必须是 0 至 {FPS * 5} 的整数")
        if kind == "cut" and frames != 0:
            raise M2VError(f"{where} 硬切不允许重叠帧")
        if index == 0 and frames:
            raise M2VError("首幕不能声明入场转场（没有前一幕可以重叠）")
    return raw


def normalize(raw: Any) -> dict[str, Any]:
    """校验并补全一份 brief；任何字段问题都在这里失败。"""
    if not isinstance(raw, dict):
        raise M2VError(f"{MATERIAL} 顶层必须是对象")
    if raw.get("schemaVersion") != 1:
        raise M2VError(f"{MATERIAL} schemaVersion 必须为 1")
    allowed = {"schemaVersion", "topic", "targetSeconds", "fps", "width", "height",
               "durationToleranceSeconds", "provider", "visual", "motion", "scenes", "soundtrack"}
    unknown = set(raw) - allowed
    if unknown:
        raise M2VError(f"{MATERIAL} 含未知字段：{'、'.join(sorted(unknown))}")
    brief = dict(raw)
    brief["topic"] = _require_text(raw.get("topic"), "topic")
    brief["targetSeconds"] = _require_number(raw.get("targetSeconds"), "targetSeconds", low=1, high=600)
    for field, expected in (("fps", FPS), ("width", WIDTH), ("height", HEIGHT)):
        value = raw.get(field, expected)
        if type(value) is not int or value != expected:
            raise M2VError(f"{field} 必须为 {expected}（本类型固定 1080×1920、30 fps）")
        brief[field] = expected
    brief["durationToleranceSeconds"] = _require_number(
        raw.get("durationToleranceSeconds", DEFAULTS["durationToleranceSeconds"]),
        "durationToleranceSeconds", low=0, high=30)

    provider = _merged(raw.get("provider", {}), DEFAULTS["provider"], "provider")
    provider_allowed = set(DEFAULTS["provider"])
    if set(provider) - provider_allowed:
        raise M2VError(f"provider 含未知字段：{'、'.join(sorted(set(provider) - provider_allowed))}")
    provider["name"] = _require_text(provider.get("name"), "provider.name")
    api_base = _require_text(provider.get("apiBase"), "provider.apiBase").rstrip("/")
    if not api_base.startswith(("http://", "https://")):
        raise M2VError("provider.apiBase 必须是 http(s) 地址")
    provider["apiBase"] = api_base
    key_env = _require_text(provider.get("apiKeyEnv"), "provider.apiKeyEnv")
    if not _ENV_NAME.match(key_env):
        raise M2VError("provider.apiKeyEnv 必须是环境变量名")
    provider["apiKeyEnv"] = key_env
    if provider.get("orientation") not in ORIENTATIONS:
        raise M2VError(f"provider.orientation 只支持 {'、'.join(sorted(ORIENTATIONS))}")
    provider["perPage"] = _require_int(provider.get("perPage"), "provider.perPage", low=1, high=80)
    media = provider.get("media")
    if (not isinstance(media, list) or not media
            or any(item not in MEDIA_KINDS for item in media) or len(set(media)) != len(media)):
        raise M2VError(f"provider.media 必须是 {'、'.join(MEDIA_KINDS)} 的非空无重复子集")
    provider["media"] = list(media)
    provider["minClipSeconds"] = _require_number(provider.get("minClipSeconds"), "provider.minClipSeconds", low=0.5, high=30)
    provider["maxClipSeconds"] = _require_number(provider.get("maxClipSeconds"), "provider.maxClipSeconds", low=0.5, high=30)
    if provider["maxClipSeconds"] < provider["minClipSeconds"]:
        raise M2VError("provider.maxClipSeconds 不能小于 minClipSeconds")
    if type(provider.get("allowReuse")) is not bool:
        raise M2VError("provider.allowReuse 必须是布尔值")
    brief["provider"] = provider

    visual = _merged(raw.get("visual", {}), DEFAULTS["visual"], "visual")
    if set(visual) - {"theme", "attribution"}:
        raise M2VError(f"visual 含未知字段：{'、'.join(sorted(set(visual) - {'theme', 'attribution'}))}")
    if visual.get("theme") not in {"dark", "light"}:
        raise M2VError("visual.theme 只支持 dark/light")
    # 来源署名不是可选装饰：没有它就无法满足「保留可核验来源」的交付要求。
    visual["attribution"] = _require_text(visual.get("attribution"), "visual.attribution")
    brief["visual"] = visual

    motion = _merged(raw.get("motion", {}), DEFAULTS["motion"], "motion")
    if set(motion) - {"photoZoom"}:
        raise M2VError(f"motion 含未知字段：{'、'.join(sorted(set(motion) - {'photoZoom'}))}")
    motion["photoZoom"] = _require_number(motion.get("photoZoom"), "motion.photoZoom", low=1.0, high=1.5)
    brief["motion"] = motion

    scenes = raw.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise M2VError("scenes 必须是非空数组")
    seen: set[str] = set()
    brief["scenes"] = [_validate_scene(scene, index, seen) for index, scene in enumerate(scenes)]
    _require_reachable_target(brief)

    if "soundtrack" in raw:
        report = Report()
        # 逐幕只有单一 narration 文本，没有 beat 轴，因此只接受音床。
        sound_contract.validate_sound(brief, report, effects=False)
        if not report.ok:
            raise M2VError("\n".join(issue.format() for issue in report.errors))
    return brief


def _require_reachable_target(brief: dict[str, Any]) -> None:
    """幕数与逐幕上限必须够长：结构上达不到目标时长时，在联网检索之前就失败。

    每一幕最长不超过 ``provider.maxClipSeconds``（声明 ``durationFrames`` 的幕按声明
    值），幕间重叠还会让成片更短。有口播的幕时长由真实语音决定，无法在这里估算，
    因此只要存在这类幕就跳过本项检查。
    """
    if any(scene.get("narration") for scene in brief["scenes"]):
        return
    fps = brief["fps"]
    maximum = int(round(brief["provider"]["maxClipSeconds"] * fps))
    reachable = sum(int(scene.get("durationFrames", maximum)) for scene in brief["scenes"])
    reachable -= sum(_overlap_frames(scene) for scene in brief["scenes"])
    target = int(round(brief["targetSeconds"] * fps))
    tolerance = int(round(brief["durationToleranceSeconds"] * fps))
    if reachable + tolerance < target:
        raise M2VError(
            f"按 {len(brief['scenes'])} 幕、每幕最多 {brief['provider']['maxClipSeconds']} 秒计算，"
            f"最长只能剪出 {reachable / fps:.2f} 秒，达不到 targetSeconds={brief['targetSeconds']} 秒；"
            f"请增加幕数或调高 provider.maxClipSeconds")


def _overlap_frames(scene: dict[str, Any]) -> int:
    transition = scene.get("transition") or {"type": "cut"}
    kind = transition.get("type", "cut")
    return int(transition.get("frames", 12 if kind == "crossfade" else 0))


def load(root: Path, project: dict[str, Any]) -> dict[str, Any]:
    """读取并归一化作品的 brief；材料入口取自作品契约。"""
    path = root / project["materials"].get("brief", MATERIAL)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"无法读取 {path.name}：{exc}") from exc
    return normalize(raw)


def brief_path(root: Path, project: dict[str, Any]) -> Path:
    return root / project["materials"].get("brief", MATERIAL)
