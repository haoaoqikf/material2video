"""正式合成窗口和整片复核。原生试制仍由 samples 管理。"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
import wave
from pathlib import Path

from m2v.core.audio_policy import declared_audio
from m2v.core.delivery import candidate, outputs
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from . import dependencies, ledger
from .model import fields, identifier, text, window
from .storage import local, read, receipt

logger = logging.getLogger(__name__)
SAMPLE_THRESHOLD_SECONDS = 30


def prepared(root, project):
    from m2v.commands import _prepared

    return ledger.query_value(("prepared", root), lambda: _prepared(root, project))


def sample_required(data):
    return data["durationInFrames"] > SAMPLE_THRESHOLD_SECONDS * data["fps"]


def _overlaps(start, end, item):
    return item["startFrame"] < end and item["endFrame"] > start


def _cues(data, frame_window):
    cues = data["props"]["subtitleCues"]
    return [cue for cue in cues if _overlaps(*frame_window, cue)]


def _audio_window(root, data, start, end):
    segment, = data["audio"]["segments"]
    path = local(root, segment["path"])
    try:
        with wave.open(str(path), "rb") as audio:
            rate = audio.getframerate()
            first = start * rate // data["fps"]
            last = end * rate // data["fps"]
            # Include the stream format so equal bytes under different playback formats differ.
            audio.setpos(first)
            chunk = audio.readframes(last - first)
            frame_size = audio.getsampwidth() * audio.getnchannels()
            if len(chunk) != (last - first) * frame_size:
                raise M2VError("音频母版没有覆盖正式评审窗口")
            return [rate, audio.getnchannels(), audio.getsampwidth(), hashlib.sha256(chunk).hexdigest()]
    except (OSError, EOFError, wave.Error) as exc:
        raise M2VError(f"无法核对正式评审窗口的音频母版：{exc}") from exc


def _window_signature(root, data, frame_window, dynamic):
    start, end = frame_window
    props = data["props"]
    scenes = [scene for scene in props["compiledScenes"] if _overlaps(start, end, scene)]
    if not scenes:
        raise M2VError("正式评审窗口缺少实际场景")
    cues = _cues(data, frame_window)
    return fingerprint({
        "fps": data["fps"], "width": data["width"], "height": data["height"],
        "implementation": data["inputs"]["implementation"], "renderer": data["inputs"]["renderer"],
        "scenes": [(scene, dependencies.scene_sources(root, scene)) for scene in scenes],
        "subtitles": {"style": props["subtitle"], "cues": cues} if cues else None,
        "audio": _audio_window(root, data, start, end) if dynamic and declared_audio(data) else None,
    })


def _source(root, project, data, media):
    base = outputs(root)
    source = local(base, media["path"])
    path = source.with_suffix(".provenance.json")
    proof = receipt(base, path)
    value = read(path)
    if (value.get("schemaVersion") != 1 or value.get("compositionId") != "SceneFilm"
            or value.get("projectId") != project["id"] or value.get("type") != project["type"]
            or any(value.get(key) != data[key] for key in ("width", "height", "fps"))
            or value.get("delivery", {}).get("sha256") != media["sha256"]):
        raise M2VError("正式评审须使用当前作品实际合成的视频和对应溯源")
    offset, size = value.get("startFrame"), value.get("durationInFrames")
    if type(offset) is not int or offset < 0 or type(size) is not int or size < 1:
        raise M2VError("正式评审视频旁车缺少有效时间窗")
    return value, proof


def _copy_pinned(source, target, digest):
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".review-source-", dir=target.parent)
        os.close(fd)
        temporary = Path(name)
        try:
            shutil.copyfile(source, temporary)
            # Bypass the query cache for a copy that has just been written.
            from m2v.core.delivery import digest as file_digest
            if file_digest(temporary) != digest:
                raise M2VError("合成证据在封存期间变化")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    if dependencies.digest(target) != digest:
        raise M2VError("已封存的正式评审证据摘要失配")


def pin_sources(root, project, request):
    """预演的固定文件名可被下一次覆盖，正式候选则已有按版本保存的路径。"""
    base = outputs(root)
    data = prepared(root, project)
    paths = {}
    for name in dict.fromkeys(item["path"] for item in request["items"]):
        source = local(base, name)
        source_media = receipt(base, source)
        value, proof = _source(root, project, data, source_media)
        if value.get("preparedFingerprint") != data["preparedFingerprint"]:
            raise M2VError("新正式评审须从当前准备版本的预演或候选取证")
        declared = local(base, proof["path"])
        if source == base / "video.mp4":
            record = candidate(root, data)
            if record["sha256"] != source_media["sha256"]:
                raise M2VError("交付文件与当前候选摘要不符")
            source = local(base, Path(record["path"]).relative_to(base).as_posix())
            candidate_value, candidate_proof = _source(root, project, data, receipt(base, source))
            if candidate_proof["sha256"] != proof["sha256"]:
                # 技术 QA 在候选封存后补写交付旁车；该注记不属于合成时间映射。
                delivery_mapping = {key: field for key, field in value.items() if key != "qa"}
                candidate_mapping = {key: field for key, field in candidate_value.items() if key != "qa"}
                if ("qa" not in value and "qa" not in candidate_value) or delivery_mapping != candidate_mapping:
                    raise M2VError("交付文件与当前候选的时间映射不一致")
        if source.parent != base / "candidates":
            name_key = fingerprint([source_media["sha256"], proof["sha256"]])
            pinned = local(base, f"review-sources/{name_key}{source.suffix}", exists=False)
            _copy_pinned(source, pinned, source_media["sha256"])
            target = local(base, pinned.with_suffix(".provenance.json").relative_to(base).as_posix(), exists=False)
            _copy_pinned(declared, target, proof["sha256"])
            source = pinned
        paths[name] = source.relative_to(base).as_posix()
    return {**request, "items": [{**item, "path": paths[item["path"]]} for item in request["items"]]}


def composition_binding(root, project, request, media, sealed=None):
    data = prepared(root, project)
    if request["fps"] != data["fps"]:
        raise M2VError("正式证据须与成片帧率相同")
    process = request["purpose"] == "process"
    if process and sealed is None and not sample_required(data):
        raise M2VError("成片不超过 30 秒，无需创建正式关键样片评审")
    result, sources = {}, {}
    for item, entry in zip(request["items"], media, strict=True):
        path = entry["path"]
        if path not in sources:
            sources[path] = _source(root, project, data, entry)
        value, proof = sources[path]
        # 已封存窗口用实际局部依赖重验。创建时必须从当前版本取证。
        if sealed is None and value.get("preparedFingerprint") != data["preparedFingerprint"]:
            raise M2VError("正式评审源视频与当前准备身份不符")
        offset = value["startFrame"]
        start, end = item["window"]
        frame_window = [offset + start, offset + end]
        if end > value["durationInFrames"] or frame_window[1] > data["durationInFrames"]:
            raise M2VError("正式证据超出实际合成或当前成片窗口")
        if process and frame_window == [0, data["durationInFrames"]]:
            raise M2VError("关键样片须选择成片中的局部过程")
        result[item["id"]] = {
            "window": frame_window, "provenance": proof,
            "hasSubtitles": bool(_cues(data, frame_window)),
            "signature": ledger.query_value(
                ("film-window", root, tuple(frame_window), item["dynamic"]),
                lambda: _window_signature(root, data, frame_window, item["dynamic"]),
            ),
        }
    return result


def _latest(events, event_type):
    return next((event["data"] for event in reversed(events) if event["type"] == event_type), None)


def _validate_windows(request, data):
    fields(request, {"windows"})
    if not isinstance(request["windows"], list) or not request["windows"]:
        raise M2VError("请登记至少一个能回答具体问题的必审窗口")
    seen = set()
    total = data["durationInFrames"]
    for item in request["windows"]:
        fields(item, {"id", "window", "goal"})
        identity = identifier(item["id"])
        start, end = window(item["window"])
        text(item["goal"])
        if identity in seen or end - start < 2 or end > total or (start == 0 and end == total):
            raise M2VError("必审窗口须使用唯一 ID、至少两帧并位于成片内的局部范围")
        seen.add(identity)


def register_windows(root, project, request):
    data = prepared(root, project)
    if not sample_required(data):
        raise M2VError("成片不超过 30 秒，无需登记必审样片窗口")
    _validate_windows(request, data)
    if data["props"]["subtitleCues"] and not any(_cues(data, item["window"]) for item in request["windows"]):
        raise M2VError("有字幕的成片须登记至少一个观察实际字幕的必审窗口")
    record = {**request, "fps": data["fps"]}
    ledger.append(root, project, "sample-windows", data=record)
    logger.info("登记了 %d 个关键样片必审窗口", len(request["windows"]))
    return record


def sample_state(data, events, approved):
    if data is None:
        return {"status": "undetermined"}
    if not sample_required(data):
        return {"status": "exempt", "windows": []}
    record = _latest(events, "sample-windows")
    if record is None:
        return {"status": "required", "windows": [], "detail": "缺少必审窗口登记"}
    try:
        if record["fps"] != data["fps"]:
            raise M2VError("帧率变化，须重新登记必审窗口")
        _validate_windows({"windows": record["windows"]}, data)
    except (M2VError, KeyError, TypeError) as exc:
        return {"status": "required", "windows": [], "detail": str(exc)}
    windows = []
    subtitles_covered = False
    for item in record["windows"]:
        evidence = [
            film[item["id"]] for film, conditions in approved
            if item["id"] in film and film[item["id"]]["window"] == item["window"]
            and item["goal"] in conditions
        ]
        subtitles_covered |= any(binding["hasSubtitles"] for binding in evidence)
        windows.append({**item, "status": "pass" if evidence else "missing"})
    complete = all(item["status"] == "pass" for item in windows)
    if data["props"]["subtitleCues"] and not subtitles_covered:
        return {"status": "required", "windows": windows, "detail": "缺少实际字幕过程的有效覆盖"}
    return {"status": "pass" if complete else "required", "windows": windows}


def current_candidate(root, data):
    return ledger.query_value(("candidate", root), lambda: candidate(root, data))


def qa_binding(root, project):
    def verify():
        data = prepared(root, project)
        record = current_candidate(root, data)
        if record.get("status") not in ("ready", "delivered"):
            raise M2VError("当前完整候选技术验收尚未通过")
        base = outputs(root)
        if record["status"] == "delivered":
            from m2v.standalone.executor import local_artifact
            delivered = local_artifact(root, record.get("destination"))
            if dependencies.digest(local(base, delivered.relative_to(base).as_posix())) != record["sha256"]:
                raise M2VError("交付文件与当前候选摘要不符")
        path = local(base, "qa.json")
        payload = path.read_bytes()
        qa = json.loads(payload)
        if (qa.get("status") != "pass" or qa.get("scope") != "technical-only"
                or qa.get("videoSha256") != record["sha256"]
                or qa.get("preparedFingerprint") != data["preparedFingerprint"]
                or qa.get("durationInFrames") != data["durationInFrames"] or qa.get("fps") != data["fps"]):
            raise M2VError("需要当前完整候选的有效技术 QA")
        return {"candidateSha256": record["sha256"], "preparedFingerprint": data["preparedFingerprint"],
                "durationFrames": data["durationInFrames"], "fps": data["fps"],
                "qa": {"path": "qa.json", "sha256": hashlib.sha256(payload).hexdigest()}}

    return ledger.query_value(("technical-qa", root), verify)


def confirm_playback(root, project, request):
    fields(request, {"candidateSha256", "observations"})
    text(request["observations"])
    binding = qa_binding(root, project)
    if request["candidateSha256"] != binding["candidateSha256"]:
        raise M2VError("实际看听的文件摘要与当前候选不符")
    record = {**binding, "observations": request["observations"]}
    ledger.append(root, project, "playback-confirmed", data=record)
    logger.info("已登记当前完整候选的整片复核 %s", binding["candidateSha256"])
    return record


def playback_state(events, qa):
    record = _latest(events, "playback-confirmed")
    if record is None:
        return {"status": "missing"}
    if qa["status"] != "pass" or {key: value for key, value in qa.items() if key != "status"} != {
        key: value for key, value in record.items() if key != "observations"
    }:
        return {"status": "stale", "detail": "当前候选或技术绑定已变化"}
    return {"status": "pass", **record}
