"""候选选择与本地精确精裁；不把请求起点冒充实测起点。

精裁使用解码后重编码，显式声明输出帧率与像素格式；起点按真实 PTS 测量，
起点/终点/时长误差与有声偏移超过目标输出一帧（有声 50ms）时明确失败。
"""
from __future__ import annotations

import json
import logging
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .contracts import (Candidate, CandidateData, Observations, Probe, Selection,
                        SelectionData, TimeRange, Transform, fingerprint)
from .errors import MaterialError
from .media import LOCAL_INPUT_OPTIONS, ffprobe_exe, probe, seconds_us, toolchain
from .store import MaterialStore

logger = logging.getLogger(__name__)


@dataclass
class CutResult:
    selection: Selection
    measured: dict


def persist_candidate(store: MaterialStore, candidate: CandidateData,
                      candidate_id: str | None = None) -> Candidate:
    document_id = candidate_id or f'candidate-{fingerprint(candidate.model_dump(mode="json"))[:32]}'
    try:
        previous = store.get(document_id, kind='material.candidate')
    except MaterialError as exc:
        if exc.code != 'not-found':
            raise
    else:
        if previous.data != candidate:
            raise MaterialError('conflict', '候选 ID 已对应不同内容', stage='selection')
        return previous
    return store.put(Candidate(id=document_id, data=candidate))


def _actual_start(source: Path, requested_us: int, *, video_start_us: int | None) -> int:
    """读取真实帧 PTS，返回请求起点之后第一帧的媒体本地时间。"""
    command = [ffprobe_exe(), '-v', 'error', '-select_streams', 'v:0',
               '-read_intervals', f'{requested_us / 1_000_000:.6f}%+#60',
               '-show_frames', '-show_entries', 'frame=best_effort_timestamp,pts_time',
               '-of', 'json', str(source)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '精裁起点测量超时', stage='selection') from exc
    if result.returncode:
        raise MaterialError('timeline-unverified', '无法测量真实视频帧，未执行精裁', stage='selection')
    try:
        frames = json.loads(result.stdout).get('frames') or []
    except ValueError as exc:
        raise MaterialError('timeline-unverified', '帧探测结果无效', stage='selection') from exc
    values = []
    for frame in frames:
        value = frame.get('pts_time')
        if value is None:
            continue
        try:
            values.append(seconds_us(value))
        except MaterialError:
            continue
    origin = video_start_us or 0
    candidates = sorted(value - origin for value in values if value - origin >= requested_us - 1)
    if not candidates:
        raise MaterialError('timeline-unverified', '请求窗口内没有可测量的真实帧', stage='selection')
    return candidates[0]


def _cut(source: Path, target: Path, interval: TimeRange, transform: Transform,
         *, image: bool, length_us: int | None = None) -> None:
    if image:
        shutil.copyfile(source, target)
        return
    fps = transform.fps
    length_us = length_us or (interval.endUs - interval.startUs)
    command = [get_ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(source), *LOCAL_INPUT_OPTIONS,
               '-ss', f'{interval.startUs / 1_000_000:.6f}', '-t', f'{length_us / 1_000_000:.6f}',
               '-map', '0:v:0']
    if transform.audio == 'preserve':
        command += ['-map', '0:a:0?']
    command += ['-vf', f'scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={fps.num}/{fps.den}',
                '-c:v', transform.codec, '-crf', str(transform.crf), '-preset', 'medium',
                '-pix_fmt', 'yuv420p']
    command += (['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2'] if transform.audio == 'preserve' else ['-an'])
    command += ['-movflags', '+faststart', '-y', str(target)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=3600)
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '精裁超时', stage='selection') from exc
    if result.returncode or not target.is_file() or not target.stat().st_size:
        raise MaterialError('decode-failed', '精裁失败，未发布输出', stage='selection')


def _verify(probe_result: Probe, interval: TimeRange, transform: Transform,
            actual_start: int, *, source_has_audio: bool) -> dict:
    frame_us = math.ceil(transform.fps.den * 1_000_000 / transform.fps.num)
    length = interval.endUs - interval.startUs
    duration_error = (probe_result.durationUs or 0) - length
    end_error = actual_start + (probe_result.durationUs or 0) - interval.endUs
    audio_offset = None
    if transform.audio == 'preserve' and source_has_audio and probe_result.hasAudio:
        audio_offset = (probe_result.audioStartUs or 0)
    measured = {'startErrorUs': actual_start - interval.startUs, 'endErrorUs': end_error,
                'durationErrorUs': duration_error, 'frameUs': frame_us,
                'audioOffsetUs': audio_offset}
    if abs(measured['startErrorUs']) > frame_us:
        raise MaterialError('timeline-unverified', '精裁实际起点误差超过目标输出一帧', stage='selection')
    if abs(duration_error) > frame_us:
        raise MaterialError('timeline-unverified', '精裁输出时长误差超过目标输出一帧', stage='selection')
    if abs(end_error) > frame_us:
        raise MaterialError('timeline-unverified', '精裁实际终点误差超过目标输出一帧', stage='selection')
    if audio_offset is not None and abs(audio_offset) > 50_000:
        raise MaterialError('timeline-unverified', '精裁音轨偏移超过 50ms', stage='selection')
    return measured


def _decide(candidate: Candidate, *, decision: str, rationale: str, purpose: str, operator: str,
            transform: Transform, observations: Observations | None) -> None:
    if decision not in {'chosen', 'rejected'}:
        raise MaterialError('invalid-request', '选择决定必须是 chosen 或 rejected', stage='selection')
    for value, label in ((rationale, '理由'), (purpose, '用途'), (operator, '操作者')):
        if not isinstance(value, str) or not value.strip():
            raise MaterialError('invalid-request', f'选择必须写明{label}', stage='selection')


def select(store: MaterialStore, candidate: Candidate, *, decision: str, rationale: str,
           purpose: str, operator: str, output_dir: Path, transform: Transform | None = None,
           observations: Observations | None = None, image: bool | None = None) -> CutResult:
    transform = transform or Transform()
    _decide(candidate, decision=decision, rationale=rationale, purpose=purpose,
            operator=operator, transform=transform, observations=observations)
    media = store.get(candidate.data.mediaId, kind='material.media')
    if media.data.artifact.sha256 != candidate.data.mediaSha256:
        raise MaterialError('hash-mismatch', '候选媒体摘要已变化，请重新查找', stage='selection')
    source = store.verify_artifact(media.data.artifact)
    is_image = media.data.probe.kind == 'image'
    if image is not None and image != is_image:
        raise MaterialError('invalid-request', '图片/视频选择类型与媒体实测不符', stage='selection')
    interval = candidate.data.localRange
    output_artifact = None
    output_probe = None
    measured: dict = {}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = (f'{fingerprint({"candidate": candidate.id, "decision": decision, "transform": transform.model_dump(mode="json"), "window": interval.model_dump(mode="json") if interval else None})[:16]}.mp4')
    if decision == 'chosen':
        if not is_image and interval is None:
            raise MaterialError('invalid-request', '视频选择必须声明本地窗口', stage='selection')
        with tempfile.TemporaryDirectory(prefix='select-', dir=output_dir) as temporary:
            target = Path(temporary) / filename
            if is_image:
                suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}.get(
                    (media.data.probe.container or '').upper(), '.png')
                target = target.with_suffix(suffix)
                _cut(source, target, TimeRange(startUs=0, endUs=1), transform, image=True)
                output_probe = probe(target, timeout_s=120)
            else:
                actual_start = _actual_start(source, interval.startUs,
                                             video_start_us=media.data.probe.videoStartUs)
                # 以真实起点为锚，长度裁剪到请求终点，避免起点取整把终点推过一帧。
                length = max(1, interval.endUs - actual_start)
                _cut(source, target, interval, transform, image=False, length_us=length)
                output_probe = probe(target, timeout_s=120)
                measured = _verify(output_probe, interval, transform, actual_start,
                                   source_has_audio=media.data.probe.hasAudio)
            output_artifact = store.publish_file(target, max_bytes=256 * 1024 * 1024)
    data = SelectionData(candidateId=candidate.id, candidateDigest=fingerprint(candidate),
                         mediaId=candidate.data.mediaId, mediaSha256=candidate.data.mediaSha256,
                         localRange=interval, sourceRange=candidate.data.sourceRange,
                         decision=decision, rationale=rationale, purpose=purpose, operator=operator,
                         observations=observations or candidate.data.observations,
                         transform=transform, outputArtifact=output_artifact, outputProbe=output_probe,
                         toolchain={**toolchain(), 'policy': 'decode-reencode-frame-accurate-v1',
                                    'measured': measured})
    document_id = f'selection-{fingerprint(data.model_dump(mode="json"))[:32]}'
    try:
        previous = store.get(document_id, kind='material.selection')
    except MaterialError as exc:
        if exc.code != 'not-found':
            raise
    else:
        if previous.data != data:
            raise MaterialError('conflict', '同一选择身份对应不同输出', stage='selection')
        return CutResult(previous, measured)
    document = store.put(Selection(id=document_id, data=data))
    return CutResult(document, measured)


