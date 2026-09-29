"""媒体清单校验与分镜派生；源分镜始终不被覆盖。"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit, parse_qsl

from . import assets as asset_refs
from . import beats as beat_mod
from . import storyboard as sb
from .audio import wav_duration
from .errors import A2VError

#: 当前媒体清单版本。版本 2 起逐幕携带 `resolvedBeats`（分段口播的真实词边界
#: 解析结果）；版本 1 的旧清单继续可读，但含分段口播的分镜必须重新 prepare。
MANIFEST_VERSION = 3


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
    与引入内容根之前的行为一致。经 `/__a2v__/` 别名引用的共享资产一律记别名键，
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
    storyboard: sb.Storyboard
    audio: Path


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


def _scene_resolved_beats(
    item: dict, scene: dict, frames: int, *, version: int
) -> list[dict]:
    """校验并返回一幕的 `resolvedBeats`；旧清单返回空表。

    读取器同时支持旧清单和新版 beat 清单：版本 1 的清单只要不含分段口播就
    照常可用，含分段口播则必须重新 prepare（旧缓存给不出词边界）。
    版本 2 起逐幕要求该字段，并核对顺序、重叠、越界与源声明一致性。
    """
    segments = item.get("narrationSegments")
    has_segments = isinstance(segments, list) and bool(segments)
    raw = scene.get("resolvedBeats")
    if version < 2:
        if has_segments:
            raise ValueError("清单版本过旧（没有分段口播的节拍解析结果），请重新 prepare")
        return []
    if not isinstance(raw, list):
        raise ValueError("场景缺少 resolvedBeats 数组")
    if not has_segments:
        if raw:
            raise ValueError("字符串口播的场景不应携带 resolvedBeats")
        return []
    timeline = beat_mod.BeatTimeline.from_json(raw, estimated=False)
    issues = beat_mod.validate_timeline(timeline.beats, frames)
    if issues:
        raise ValueError("；".join(issues))
    declared = {
        str(beat.get("id")): beat
        for beat in (item.get("beats") or [])
        if isinstance(beat, dict)
    }
    if not timeline.beats:
        raise ValueError("分段口播的场景必须有已解析的节拍区间")
    if [beat.id for beat in timeline.beats] != [
        beat_id for beat_id in declared if beat_id in {item.id for item in timeline.beats}
    ]:
        raise ValueError("resolvedBeats 的顺序与源分镜的 beat 声明不一致")
    for beat in timeline.beats:
        source = declared.get(beat.id)
        if source is None:
            raise ValueError(f"resolvedBeats 的 {beat.id} 在源分镜里不存在")
        if (
            source.get("action") != beat.action
            or [str(target) for target in source.get("targets") or []] != list(beat.targets)
            or source.get("meaning") != beat.meaning
        ):
            raise ValueError(f"resolvedBeats 的 {beat.id} 与源分镜声明不一致")
    if set(declared) != {beat.id for beat in timeline.beats}:
        raise ValueError("源分镜里有 beat 没有解析出帧区间")
    return raw


def load_media(path: str | Path, source_path: str | Path | None = None) -> Media:
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        source = data["source"]
        if (
            type(data["version"]) is not int
            or data["version"] not in (1, 2, MANIFEST_VERSION)
            or data["sourceFingerprint"] != fingerprint(source)
        ):
            raise ValueError("版本或分镜指纹非法")
        if source_path and fingerprint(json.loads(Path(source_path).read_text(encoding="utf-8"))) != data["sourceFingerprint"]:
            raise ValueError("分镜已修改，请重新 prepare")
        report = sb.validate(source)
        if not report.ok:
            raise ValueError("清单中的源分镜无效")
        from . import sound
        if data["version"] < 3 and ("soundtrack" in source or any("speech" in seg for scene in source["scenes"] for seg in scene.get("narrationSegments", []))):
            raise ValueError("新声音参数需要 version 3 清单，请重新 prepare")
        if data["version"] == 3:
            if data.get("soundFingerprint") != fingerprint(sound.configuration(source)):
                raise ValueError("声音配置指纹不一致，请重新 prepare")
            expected_refs = {item["sourceRef"] for item in ([source["soundtrack"]["music"]] if source.get("soundtrack", {}).get("music") else []) + source.get("soundtrack", {}).get("effects", [])}
            if set(data.get("soundAssets", {})) != expected_refs: raise ValueError("声音素材清单不完整")
            for ref, entry in data["soundAssets"].items():
                candidate = (path.parent / entry["path"]).resolve()
                if source_path and candidate != (Path(source_path).resolve().parent / ref).resolve(): raise ValueError("声音素材路径不一致")
                if not candidate.is_file() or sound.asset_digest(candidate) != entry["sha256"]:
                    raise ValueError("声音素材已变化，请重新 prepare")
            narration = (path.parent / data["narration"]).resolve()
            if not narration.is_relative_to(path.parent): raise ValueError("旁白必须位于清单目录内")
        effective = copy.deepcopy(source)
        if len(data["scenes"]) != len(source["scenes"]):
            raise ValueError("场景数量不匹配")
        for item, scene in zip(effective["scenes"], data["scenes"]):
            frames = scene["durationInFrames"]
            if (scene["id"] != item["id"] or type(frames) is not int
                    or frames < item["durationInFrames"]):
                raise ValueError("场景 ID 或时长非法")
            item["durationInFrames"] = frames
            resolved = _scene_resolved_beats(item, scene, frames, version=data["version"])
            if resolved:
                item["resolvedBeats"] = resolved
        model = sb._build(effective, report)
        previous_end = 0
        if not isinstance(data["cues"], list):
            raise ValueError("字幕必须是列表")
        for cue in data["cues"]:
            start, end = cue["start"], cue["end"]
            if (any(type(t) not in (int, float) or not math.isfinite(t) for t in (start, end))
                    or start < previous_end or end <= start or end > model.total_frames / model.fps
                    or not isinstance(cue["text"], str) or not cue["text"].strip() or len(cue["text"]) > 28):
                raise ValueError("字幕时间段非法")
            previous_end = end
        audio = (path.parent / data["audio"]).resolve()
        if not audio.is_relative_to(path.parent):
            raise ValueError("音轨必须位于清单目录内")
        if abs(wav_duration(audio) - model.total_frames / model.fps) > 1 / 24000:
            raise ValueError("音轨时长与时间轴不一致")
        if data["version"] == 3 and abs(wav_duration(narration) - model.total_frames / model.fps) > 1 / 24000:
            raise ValueError("旁白时长与时间轴不一致")
        return Media(path, data, model, audio)
    except (OSError, ValueError, KeyError, TypeError, A2VError) as exc:
        raise A2VError(f"媒体清单无效 {path}: {exc}") from exc


def media_url(page_url: str, server_url: str, media: Media) -> str:
    parts = urlsplit(page_url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "a2v-media"]
    query.append(("a2v-media", server_url + "/" + quote(media.path.name)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
