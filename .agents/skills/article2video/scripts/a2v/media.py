"""媒体清单校验与分镜派生；源分镜始终不被覆盖。"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit, parse_qsl

from . import assets as asset_refs
from .audio import wav_duration
from .errors import A2VError

#: 当前媒体契约为 v4。v1–v3 清单属于旧幕级时间轴，入口一律拒绝并要求重新 prepare。
MANIFEST_VERSION = 4


def fingerprint(source: dict) -> str:
    return hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


#: 按文本处理、需要归一化换行后再哈希的后缀
_TEXT_SUFFIXES = frozenset(
    {".css", ".js", ".mjs", ".cjs", ".json", ".html", ".htm", ".svg", ".txt", ".md"}
)


def file_digest(path: Path) -> str:
    """资产内容摘要。文本类资产**先归一化换行**再哈希。

    实测踩到的坑：git 的换行归一化会在工作区把 LF 静默换成 CRLF，
    于是「内容没变、只差行尾」的文件会让成片被判成「落后」——
    而人怎么重渲都消不掉这个结论（重渲记下 CRLF，下次 checkout 又翻回 LF），
    闸门立刻沦为噪音。二进制资产（字体、图片）按原字节哈希。
    """
    data = path.read_bytes()
    if path.suffix.lower() in _TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def asset_fingerprint(
    page: Path,
    html: str,
    extra: dict | None = None,
    workspace_root: Path | None = None,
    mounts: dict[str, Path] | None = None,
) -> dict:
    """成片溯源用的资产指纹：网页**真正引用**的本地资源，加上页面自身。

    只指纹被引用的文件，不指纹整个 `assets/` 目录：否则改一个用不到的图形
    会让所有成片报「落后」，闸门沦为噪音，人开始忽略它——那等于没有闸门。
    口径与媒体清单一致（同一个 `fingerprint` 的规范化 JSON），
    两处算法不同就会出现「清单说一致、成片说落后」这种没人能判断的状态。

    `workspace_root` 给出「相对哪个根记键」；省略时退回项目标记推导，
    与引入内容根之前的行为一致。经 `/__a2v_web__/` 别名引用的前端工程资产一律记别名键，
    因此页面与资产分处两个根时仍可复核。
    """
    root = (
        Path(workspace_root).resolve()
        if workspace_root is not None
        else (asset_refs.project_root(page.parent) or page.parent)
    )
    files: dict[str, str] = {}
    files[asset_refs.asset_key(page.resolve(), root, mounts)] = file_digest(page.resolve())
    for _reference, candidate in asset_refs.local_assets(page, html, mounts):
        files[asset_refs.asset_key(candidate, root, mounts)] = file_digest(candidate)
    for key, value in (extra or {}).items():
        files[key] = value
    return {"files": files, "digest": fingerprint(files)}


#: 有效分镜的固定文件名：与 media.json 同目录，名字自证「派生自清单」
_EFFECTIVE_STORYBOARD_NAME = "storyboard.effective.json"


@dataclass(frozen=True)
class Media:
    path: Path
    data: dict
    storyboard: V4Storyboard
    audio: Path


@dataclass(frozen=True)
class V4Stage:
    id: str
    start_frame: int
    duration_in_frames: int
    data: dict
    type: str = "world"

    @property
    def end_frame(self) -> int:
        return self.start_frame + self.duration_in_frames


@dataclass(frozen=True)
class V4Storyboard:
    fps: int
    width: int
    height: int
    stages: tuple[V4Stage, ...]
    has_narration: bool = False
    title: str = ""

    @property
    def scenes(self) -> tuple[V4Stage, ...]:
        """Shared inspection consumers call these timeline units scenes."""
        return self.stages

    @property
    def total_frames(self) -> int:
        return self.stages[-1].end_frame if self.stages else 0


def effective_storyboard(media: Media) -> dict:
    """媒体清单派生的有效分镜：源分镜快照 + 每幕实际时长与已解析节拍。

    composition 的时长由 props 推导；props 仍用声明分镜时，画面按声明时长走、
    音轨按派生时长合成——渲染的总帧数交叉校验直接失败，预览与体检的采样帧
    会落进下一幕入场动效前的空窗、被误判成空白帧。`load_media` 已经校验过
    场景数量、ID、「实际时长 ≥ 声明时长」与 `resolvedBeats`，这里只做写回。

    画面、字幕与配音共用同一批 beat 边界，因此有效分镜必须带上
    `resolvedBeats`：少了它，composition 会退回无声等比例估算，
    字幕却按真实词边界走——两者会在同一帧里各说各话。
    """
    effective = copy.deepcopy(media.data["source"])
    if media.data.get("version") == 4:
        effective["mediaTimeline"] = {
            "stages": copy.deepcopy(media.data["stages"]),
            "resolvedBeats": copy.deepcopy(media.data["resolvedBeats"]),
        }
        effective["subtitleCues"] = copy.deepcopy(media.data["cues"])
        return effective
    effective["subtitleCues"] = copy.deepcopy(media.data["cues"])
    for item, scene in zip(effective["scenes"], media.data["scenes"]):
        item["durationInFrames"] = scene["durationInFrames"]
        resolved = scene.get("resolvedBeats")
        if isinstance(resolved, list) and resolved:
            item["resolvedBeats"] = resolved
    return effective


def write_effective_storyboard(media: Media, target_dir: str | Path | None = None) -> Path:
    """把有效分镜落盘，供契约页与 Remotion 作为 props 加载。

    省略 `target_dir` 时写入媒体清单所在目录（`storyboard.effective.json`），
    该目录正是预览与评审的媒体服务根；渲染入口传入渲染输出旁的临时目录，
    文件随临时目录销毁。返回写入路径。
    """
    target = Path(target_dir) if target_dir is not None else media.path.parent
    target.mkdir(parents=True, exist_ok=True)
    path = target / _EFFECTIVE_STORYBOARD_NAME
    path.write_text(
        json.dumps(effective_storyboard(media), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_media(path: str | Path, source_path: str | Path | None = None) -> Media:
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        source = data["source"]
        if isinstance(source, dict) and source.get("version") == 4:
            return _load_media_v4(path, data, source_path)
        # v1–v3 清单属于旧幕级时间轴：入口不读取、不降级，只要求重新 prepare。
        raise ValueError("v4 分镜的媒体清单版本过旧，请按 v4 契约重新 prepare")
    except (OSError, ValueError, KeyError, TypeError, A2VError) as exc:
        raise A2VError(f"媒体清单无效 {path}: {exc}") from exc


def _load_media_v4(path: Path, data: dict, source_path: str | Path | None) -> Media:
    """Validate v4 media against its immutable source and globally resolved stage timeline."""
    from . import storyboard_v4

    source = data["source"]
    if data.get("version") != 4:
        raise ValueError("v4 分镜的媒体清单版本过旧，请重新 prepare")
    if data.get("sourceFingerprint") != fingerprint(source):
        raise ValueError("分镜已修改，请重新 prepare")
    if source_path:
        current = json.loads(Path(source_path).read_text(encoding="utf-8"))
        if fingerprint(current) != data["sourceFingerprint"]:
            raise ValueError("分镜已修改，请重新 prepare")
    report = storyboard_v4.validate(source)
    if not report.ok:
        raise ValueError("清单中的 v4 分镜无效")
    if data.get("soundFingerprint") != fingerprint(sound_configuration(source)):
        raise ValueError("声音配置指纹不一致，请重新 prepare")
    _validate_v4_sound_assets(path, source_path, data)

    raw_stages = data.get("stages")
    if not isinstance(raw_stages, list) or len(raw_stages) != len(source["stages"]):
        raise ValueError("媒体 stages 数量与源分镜不匹配，请重新 prepare")
    cursor = 0
    stages = []
    source_beats = {(stage["id"], beat["id"]): beat for stage in source["stages"] for beat in stage.get("beats", [])}
    seen_beats = set()
    previous_beat_end = 0
    for source_stage, media_stage in zip(source["stages"], raw_stages):
        frames = media_stage.get("durationInFrames")
        if (media_stage.get("id") != source_stage["id"] or type(frames) is not int or frames <= 0):
            raise ValueError("媒体 stage 顺序、ID 或实际时长非法，请重新 prepare")
        stages.append(V4Stage(source_stage["id"], cursor, frames, source_stage.get("data", {})))
        cursor += frames
        audio_ref = media_stage.get("audio")
        if audio_ref is not None:
            candidate = (path.parent / audio_ref).resolve()
            if not candidate.is_relative_to(path.parent) or not candidate.is_file():
                raise ValueError("stage 音频缺失或路径越界")
    beats = data.get("resolvedBeats")
    if not isinstance(beats, list):
        raise ValueError("媒体缺少全局 resolvedBeats，请重新 prepare")
    stage_starts = {stage.id: stage.start_frame for stage in stages}
    stage_ends = {stage.id: stage.end_frame for stage in stages}
    for beat in beats:
        if not isinstance(beat, dict):
            raise ValueError("全局 resolvedBeats 项必须是对象")
        key = (beat.get("stageId"), beat.get("id"))
        source_beat = source_beats.get(key)
        start, end = beat.get("startFrame"), beat.get("endFrame")
        if (source_beat is None or key in seen_beats or type(start) is not int or type(end) is not int
                or start < stage_starts.get(key[0], 0) or end <= start or end > stage_ends.get(key[0], -1)
                or start < previous_beat_end
                or beat.get("action") != source_beat.get("action")
                or beat.get("targets") != source_beat.get("targets")
                or beat.get("meaning") != source_beat.get("meaning")):
            raise ValueError("全局 resolvedBeats 与源声明或累计时间轴不匹配，请重新 prepare")
        seen_beats.add(key)
        previous_beat_end = end
    if seen_beats != set(source_beats):
        raise ValueError("并非所有源 beat 都有全局 resolvedBeats，请重新 prepare")

    standard = data.get("standardCheck")
    seconds = cursor / source["fps"]
    status = "pass" if 35 * source["fps"] <= cursor <= 45 * source["fps"] else "fail"
    if (not isinstance(standard, dict) or standard.get("actualDurationInFrames") != cursor
            or not isinstance(standard.get("actualDurationSeconds"), (int, float))
            or abs(standard["actualDurationSeconds"] - seconds) > 1 / source["fps"]
            or standard.get("durationLimitSeconds") != [35, 45]
            or standard.get("durationStatus") != status):
        raise ValueError("媒体实际时长状态与 stages 不一致")
    if not isinstance(data.get("cues"), list):
        raise ValueError("媒体字幕必须是数组")
    previous_end = 0.0
    for cue in data["cues"]:
        start, end = cue.get("start"), cue.get("end")
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or isinstance(start, bool) or isinstance(end, bool) or start < previous_end
                or end <= start or end > seconds or not isinstance(cue.get("text"), str)
                or not cue["text"].strip() or len(cue["text"]) > 28):
            raise ValueError("字幕时间段非法")
        previous_end = end
    audio_path = _contained_media_file(path, data.get("audio"), "音轨")
    narration_path = _contained_media_file(path, data.get("narration"), "旁白")
    if abs(wav_duration(audio_path) - seconds) > 1 / 24000 or abs(wav_duration(narration_path) - seconds) > 1 / 24000:
        raise ValueError("媒体音轨时长与全局 stages 不一致")
    model = V4Storyboard(source["fps"], source["width"], source["height"], tuple(stages),
                         any(stage.get("narrationSegments") for stage in source["stages"]), source.get("title", ""))
    return Media(path, data, model, audio_path)


def sound_configuration(source: dict) -> dict:
    from . import sound
    return sound.configuration(source)


def _contained_media_file(path: Path, reference: Any, label: str) -> Path:
    if not isinstance(reference, str) or not reference:
        raise ValueError(f"{label}路径缺失")
    candidate = (path.parent / reference).resolve()
    if not candidate.is_relative_to(path.parent) or not candidate.is_file():
        raise ValueError(f"{label}缺失或越界")
    return candidate


def _manifest_asset_file(path: Path, source_path: str | Path | None, reference: Any, label: str) -> Path:
    """声音素材相对**源分镜目录**记录，与分镜里的 `sourceRef` 同一口径。

    素材和媒体清单分处两个目录：素材留在作品目录（`assets/`），清单写在
    `outputs/media/`。按清单目录解析会得到 `../../assets/...` 这种越界路径，
    因此这里改按源分镜目录解析并做越界检查；只有拿不到源分镜时（例如单独
    校验一份清单）才退回按清单目录解析。
    """
    if not isinstance(reference, str) or not reference or Path(reference).is_absolute():
        raise ValueError(f"{label}路径非法")
    if source_path:
        base = Path(source_path).resolve().parent
        candidate = (base / reference).resolve()
        if not candidate.is_relative_to(base):
            raise ValueError(f"{label}缺失或越界")
    else:
        candidate = (path.parent / reference).resolve()
    if not candidate.is_file():
        raise ValueError(f"{label}缺失或越界")
    return candidate


def _validate_v4_sound_assets(path: Path, source_path: str | Path | None, data: dict) -> None:
    from . import sound
    track = data["source"].get("soundtrack", {})
    refs = {item["sourceRef"] for item in ([track["music"]] if track.get("music") else []) + track.get("effects", [])}
    if set(data.get("soundAssets", {})) != refs:
        raise ValueError("声音素材清单不完整")
    for ref, entry in data["soundAssets"].items():
        candidate = _manifest_asset_file(path, source_path, entry.get("path"), "声音素材")
        if sound.asset_digest(candidate) != entry.get("sha256"):
            raise ValueError("声音素材已变化，请重新 prepare")


def media_url(page_url: str, server_url: str, media: Media) -> str:
    parts = urlsplit(page_url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "a2v-media"]
    query.append(("a2v-media", server_url + "/" + quote(media.path.name)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
