"""字幕、章节、转录、镜头、OCR、文本与视觉索引的本地构建与增量复用。

每个索引绑定媒体摘要、时间映射、输入摘要、工具/模型身份与参数；键不变时
直接复用，键变化只重建受影响通道。推理与解码都在数据库写事务之外。
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import subprocess
import tempfile
import types
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

from . import embedding
from .captions import chapters_to_records, cue_records, parse_captions
from .contracts import Artifact, EmbeddingSpec, Index, IndexData, IndexRecord, fingerprint
from .errors import MaterialError
from .media import LOCAL_INPUT_OPTIONS, seconds_us, toolchain
from .model_manager import ModelManager
from .store import MaterialStore

logger = logging.getLogger(__name__)

CHANNELS = ('captions', 'chapters', 'shots', 'frames', 'asr', 'ocr', 'text', 'visual')
DEFAULT_OPS = {'asr': (), 'ocr': ('frames',), 'text': ('captions', 'asr', 'ocr', 'chapters'),
               'visual': ('frames',), 'shots': (), 'frames': ()}
MAX_RECORDS = 50_000
MAX_FRAMES = 240


@dataclass
class IndexResult:
    document: Index
    channel: str
    reused: bool = False
    warnings: list[str] = field(default_factory=list)
    records: int = 0

    def to_dict(self) -> dict:
        return {'channel': self.channel, 'indexId': self.document.id,
                'status': self.document.data.status, 'recordCount': self.document.data.recordCount,
                'reused': self.reused, 'warnings': self.warnings}


def _mapping_digest(media) -> str:
    return fingerprint(media.data.probe.timeline)


def tokens(text: str) -> list[str]:
    """中文按字符 n-gram，拉丁按词；不依赖外部分词器，避免漏召回。"""
    value = (text or '').lower()
    result: set[str] = set()
    for run in re.findall(r'[㐀-䶿一-鿿]+|[a-z0-9]+', value):
        if '一' <= run[0] <= '鿿' or '㐀' <= run[0] <= '䶿':
            if len(run) == 1:
                result.add(run)
            else:
                result.update(run[index:index + 2] for index in range(len(run) - 1))
                result.add(run)
        else:
            result.add(run)
    return sorted(result)


def _publish_records(store: MaterialStore, records: list[dict]) -> tuple[Artifact, list[IndexRecord]]:
    if len(records) > MAX_RECORDS:
        raise MaterialError('resource-limit', '索引条目超过单次预算，请缩小范围', stage='index')
    checked = [IndexRecord.model_validate(item) for item in records]
    if len({item.id for item in checked}) != len(checked):
        raise MaterialError('invalid-request', '索引条目 ID 重复', stage='index')
    payload = [item.model_dump(mode='json') for item in checked]
    payload.sort(key=lambda item: item['id'])
    artifact = store.publish_bytes(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8'))
    return artifact, checked


def _publish_vectors(store: MaterialStore, matrix: np.ndarray) -> Artifact:
    if matrix.dtype != np.float32 or matrix.ndim != 2 or not matrix.size:
        raise MaterialError('invalid-request', '向量分片必须是二维非空 float32', stage='index')
    if not np.all(np.isfinite(matrix)):
        raise MaterialError('media-invalid', '向量含非有限值，未发布索引', stage='index')
    staging = Path(tempfile.mkdtemp(prefix='vectors-', dir=store.path('staging', exists=True, directory=True)))
    try:
        path = staging / 'vectors.npy'
        np.save(path, np.ascontiguousarray(matrix, dtype='float32'), allow_pickle=False)
        return store.publish_file(path)
    finally:
        for item in staging.iterdir():
            item.unlink(missing_ok=True)
        staging.rmdir()


def _store_index(store: MaterialStore, *, media, channel: str, config: dict, records: list[IndexRecord],
                 artifacts: list[Artifact], inputs: list[str], cache_key: str,
                 embedding_spec: EmbeddingSpec | None = None, tool: dict | None = None,
                 warnings: list[str]) -> IndexResult:
    data = IndexData(mediaId=media.id, mediaSha256=media.data.artifact.sha256, channel=channel,
                     status='complete', config=config,
                     configSha256=fingerprint({'channel': channel, 'config': config,
                                               'embedding': embedding_spec.model_dump(mode='json') if embedding_spec else None}),
                     inputDigests=sorted(set(inputs)), toolchain=tool or toolchain(),
                     timelineMappingSha256=_mapping_digest(media), artifacts=artifacts,
                     recordCount=len(records), embeddingSpec=embedding_spec)
    cached = store.cached(cache_key)
    if cached is not None:
        if cached.kind != 'material.index' or cached.data != data:
            raise MaterialError('conflict', '索引缓存身份已对应不同内容', stage='index')
        return IndexResult(cached, channel, reused=True, warnings=warnings, records=data.recordCount)
    document_id = f'index-{fingerprint(data.model_dump(mode="json"))[:32]}'
    try:
        previous = store.get(document_id, kind='material.index')
    except MaterialError as exc:
        if exc.code != 'not-found':
            raise
    else:
        if previous.data != data:
            raise MaterialError('conflict', '同一索引身份对应不同参数或输出', stage='index')
        store.add_records(previous.id, records, tokenize=tokens)
        return IndexResult(previous, channel, reused=True, warnings=warnings, records=data.recordCount)
    document = store.put(Index(id=document_id, data=data), cache_key=cache_key)
    store.add_records(document.id, records, tokenize=tokens)
    return IndexResult(document, channel, reused=False, warnings=warnings, records=data.recordCount)


def _cache_key(media, channel: str, config: dict, *, inputs: list[str] = (), model: dict | None = None) -> str:
    return 'index:' + fingerprint({'media': media.data.artifact.sha256, 'channel': channel,
                                   'mapping': _mapping_digest(media), 'config': config,
                                   'inputs': sorted(set(inputs)), 'model': model,
                                   'toolchain': {key: toolchain()[key] for key in ('ffmpeg', 'ffprobe')}})


def _track_config(media) -> list[dict]:
    return [{'sha256': item.artifact.sha256, 'origin': item.origin, 'language': item.language,
             'format': item.format} for item in media.data.captions]


def index_captions(store: MaterialStore, media) -> IndexResult:
    tracks = media.data.captions
    if not tracks:
        raise MaterialError('not-found', '媒体没有平台/本地字幕；可显式使用 asr 通道', stage='index')
    config = {'tracks': _track_config(media), 'timePolicy': 'local-us-half-open-v1'}
    cache = _cache_key(media, 'captions', config)
    cached = store.cached(cache)
    if cached is not None:
        return IndexResult(cached, 'captions', reused=True, records=cached.data.recordCount)
    records, inputs, warnings = [], [], []
    for track in tracks:
        path = store.verify_artifact(track.artifact)
        parsed = parse_captions(path, duration_us=media.data.probe.durationUs)
        inputs.append(track.artifact.sha256)
        warnings.extend(parsed.limitations)
        language = track.language or (parsed.language if parsed.language != 'mixed' else None)
        records.extend(cue_records(parsed.cues, language=language,
                                   origin=f'captions-{track.origin}',
                                   source_key=track.artifact.sha256))
    artifact, checked = _publish_records(store, records)
    return _store_index(store, media=media, channel='captions', config=config, records=checked,
                        artifacts=[artifact], inputs=inputs, cache_key=cache, warnings=warnings)


def index_chapters(store: MaterialStore, media) -> IndexResult:
    if not media.data.chapters:
        raise MaterialError('not-found', '媒体没有来源章节声明', stage='index')
    config = {'chapters': [{'title': item.title, 'start': item.localRange.startUs,
                            'end': item.localRange.endUs} for item in media.data.chapters]}
    cache = _cache_key(media, 'chapters', config)
    records = chapters_to_records(media.data.chapters)
    artifact, checked = _publish_records(store, records)
    return _store_index(store, media=media, channel='chapters', config=config, records=checked,
                        artifacts=[artifact], inputs=[media.data.artifact.sha256], cache_key=cache,
                        warnings=['章节来自平台声明；边界未与画面切镜独立核对'])


def _scene_times(path: Path, *, threshold: float, adaptive: bool) -> tuple[list[float], list[str], dict]:
    warnings, tool = [], {'detector': 'ffmpeg-scene', 'threshold': threshold}
    if adaptive:
        try:
            from scenedetect import AdaptiveDetector, detect
            scenes = detect(str(path), AdaptiveDetector())
            tool['detector'] = 'scenedetect-adaptive'
            return [start.get_seconds() for start, _ in scenes[1:]], warnings, tool
        except ImportError:
            warnings.append('未安装可选 adaptive 切镜后端；已回退 FFmpeg 场景分数')
    executable = get_ffmpeg_exe()
    command = [executable, '-v', 'info', '-nostdin', '-i', str(path), *LOCAL_INPUT_OPTIONS,
               '-filter:v', f'select=gt(scene\\,{threshold}),showinfo',
               '-an', '-f', 'null', '-']
    try:
        result = subprocess.run(command, capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '切镜检测超时', stage='index') from exc
    text = result.stderr.decode('utf-8', 'replace')
    times = [float(value) for value in re.findall(r'Parsed_showinfo[^\n]*pts_time:([0-9.]+)', text)]
    black = re.findall(r'black_start:([0-9.]+)', text)
    freeze = re.findall(r'freeze_start:([0-9.]+)', text)
    tool.update(blackStarts=len(black), freezeStarts=len(freeze))
    return times, warnings, tool


def _usable_frame(path: Path) -> bool:
    """黑场、纯色或极低对比度帧不作为视觉证据；保留“质量信号”而非猜测内容。"""
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as picture:
            small = picture.convert('L').resize((64, 64))
            stats = ImageStat.Stat(small)
            mean = stats.mean[0]
            deviation = stats.stddev[0]
    except (OSError, ValueError):
        return False
    return mean >= 8 and deviation >= 6


def _extract_frames(store: MaterialStore, media, staging: Path, shots: list[tuple[int, int]],
                    *, long_shot_us: int, max_frames: int) -> tuple[list[dict], list[str]]:
    frame_us = 33_334
    fps = media.data.probe.fps
    if fps:
        frame_us = max(1, round(fps.den * 1_000_000 / fps.num))
    duration = media.data.probe.durationUs or 0
    times: list[int] = []
    for start, end in shots:
        length = end - start
        points = [start + min(length // 10, 500_000), start + length // 2, max(start, end - min(length // 10, 500_000))]
        if length > long_shot_us:
            points.extend(start + offset for offset in range(long_shot_us, length, long_shot_us))
        times.extend(max(0, min(point, duration - 1)) for point in points)
    unique = sorted({int(value) for value in times})
    warnings = []
    if len(unique) > max_frames:
        warnings.append(f'采样帧 {len(unique)} 超过本次 {max_frames} 帧预算，按时间顺序截断')
        unique = unique[:max_frames]
    source = store.verify_artifact(media.data.artifact)
    extracted: list[tuple[int, Path]] = []
    for spot in unique:
        target = staging / f'frame-{spot:012d}.png'
        command = [get_ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(source), *LOCAL_INPUT_OPTIONS,
                   '-ss', f'{spot / 1_000_000:.6f}', '-frames:v', '1', '-y', str(target)]
        try:
            result = subprocess.run(command, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise MaterialError('resource-limit', '关键帧提取超时', stage='index') from exc
        if result.returncode or not target.is_file() or not target.stat().st_size:
            raise MaterialError('decode-failed', '关键帧无法解码，未发布帧索引', stage='index')
        extracted.append((spot, target))
    records = []
    low_quality = 0
    for spot, target in extracted:
        if not _usable_frame(target):
            low_quality += 1
            continue
        records.append(_frame_record(store, spot, target, frame_us, duration))
    if low_quality:
        warnings.append(f'{low_quality} 个采样帧为黑场、纯色或低对比度，未作为视觉证据')
    if not records and extracted:
        spot, target = extracted[0]
        records.append(_frame_record(store, spot, target, frame_us, duration))
        warnings.append('所有采样帧对比度偏低；保留首个采样帧并标注为质量受限')
    return records, warnings


def _frame_record(store: MaterialStore, spot: int, target: Path, frame_us: int, duration: int) -> dict:
    artifact = store.publish_file(target, max_bytes=64 * 1024 * 1024)
    end = min(spot + frame_us, duration) if duration else spot + frame_us
    if end <= spot:
        end = spot + 1
    identifier = hashlib.sha256(f'{spot}:{artifact.sha256}'.encode()).hexdigest()[:24]
    return {'id': f'frames-{identifier}', 'channel': 'frames', 'text': '',
            'localRange': {'startUs': spot, 'endUs': end}, 'frame': artifact.model_dump(mode='json'),
            'alignment': 'not-applicable', 'origin': 'ffmpeg-keyframe'}


def index_shots(store: MaterialStore, media, *, threshold: float = 0.3, adaptive: bool = False,
                long_shot_s: float = 10.0, max_frames: int = 48) -> list[IndexResult]:
    if media.data.probe.kind != 'video':
        raise MaterialError('invalid-request', '镜头索引只适用于视频', stage='index')
    if not 0 < threshold < 1 or not 0 < long_shot_s <= 600 or type(max_frames) is not int or not 1 <= max_frames <= MAX_FRAMES:
        raise MaterialError('invalid-request', '切镜阈值、长镜头间隔或帧预算无效', stage='index')
    config = {'threshold': threshold, 'adaptive': bool(adaptive), 'longShotUs': int(long_shot_s * 1_000_000),
              'maxFrames': max_frames, 'frameQuality': 'luma-contrast-v1'}
    cache = _cache_key(media, 'shots', config)
    cached = store.cached(cache)
    if cached is not None:
        result = IndexResult(cached, 'shots', reused=True, records=cached.data.recordCount)
        shots = [(record.localRange.startUs, record.localRange.endUs)
                 for record in store.records(cached.id) if record.localRange]
        shots_digest = cached.data.artifacts[0].sha256
        warnings = []
    else:
        source = store.verify_artifact(media.data.artifact)
        duration = media.data.probe.durationUs
        times, warnings, tool = _scene_times(source, threshold=threshold, adaptive=adaptive)
        boundaries = sorted({0, duration, *(seconds_us(value) for value in times if 0 < value < duration / 1_000_000)})
        shots = list(zip(boundaries, boundaries[1:]))
        if len(shots) > 2000:
            raise MaterialError('resource-limit', '候选切镜超过 2000 段预算', stage='index')
        records = []
        for index, (start, end) in enumerate(shots):
            identifier = hashlib.sha256(f'{start}:{end}'.encode()).hexdigest()[:24]
            records.append({'id': f'shots-{identifier}', 'channel': 'shots', 'text': '',
                            'localRange': {'startUs': start, 'endUs': end},
                            'alignment': 'not-applicable', 'origin': tool['detector']})
        artifact, checked = _publish_records(store, records)
        warnings.append('切镜是候选边界；快速运镜、闪光、淡变与字幕变化可能误切，不代表动作起止')
        result = _store_index(store, media=media, channel='shots', config=config, records=checked,
                              artifacts=[artifact], inputs=[media.data.artifact.sha256], cache_key=cache,
                              tool={**toolchain(), **tool}, warnings=warnings)
        shots_digest = artifact.sha256
    frame_config = {**config, 'shotsDigest': shots_digest}
    frame_cache = _cache_key(media, 'frames', frame_config, inputs=[shots_digest])
    frame_cached = store.cached(frame_cache)
    if frame_cached is not None:
        return [result, IndexResult(frame_cached, 'frames', reused=True, records=frame_cached.data.recordCount)]
    staging = Path(tempfile.mkdtemp(prefix='frames-', dir=store.path('staging', exists=True, directory=True)))
    try:
        frame_records, frame_warnings = _extract_frames(
            store, media, staging, shots, long_shot_us=int(long_shot_s * 1_000_000), max_frames=max_frames)
    finally:
        for item in staging.iterdir():
            item.unlink(missing_ok=True)
        staging.rmdir()
    frame_artifact, frame_checked = _publish_records(store, frame_records)
    frame_result = _store_index(store, media=media, channel='frames', config=frame_config,
                                records=frame_checked, artifacts=[frame_artifact],
                                inputs=[media.data.artifact.sha256, shots_digest],
                                cache_key=frame_cache, warnings=[*warnings, *frame_warnings])
    return [result, frame_result]


def _find_index(store: MaterialStore, media, channel: str) -> Index | None:
    # 同一媒体可有多种参数的旧索引；默认使用最近建立且与当前媒体/映射一致的一份。
    matches = [document for document in store.documents('material.index')
               if (document.data.mediaId == media.id and document.data.channel == channel
                   and document.data.status == 'complete'
                   and document.data.mediaSha256 == media.data.artifact.sha256
                   and document.data.timelineMappingSha256 == _mapping_digest(media))]
    return max(matches, key=lambda item: (item.createdAt, item.id)) if matches else None


def _require_frames(store: MaterialStore, media, options: dict) -> Index:
    existing = _find_index(store, media, 'frames')
    if existing is not None and not options.get('rebuild_frames'):
        return existing
    return index_shots(store, media, **(options.get('shots') or {}))[1].document


def index_asr(store: MaterialStore, media, manager: ModelManager, *, language: str | None = None,
              vad: bool = True, beam_size: int = 5, max_segments: int = 20_000,
              device: str = 'cpu') -> IndexResult:
    from .diagnostics import require_dependency
    require_dependency('faster_whisper', extra='asr', purpose='语音转录')
    if media.data.probe.kind == 'image' or not media.data.probe.hasAudio:
        raise MaterialError('media-invalid', '媒体没有音轨，无法转录', stage='index')
    if language is not None and (not isinstance(language, str) or not re.fullmatch(r'[a-zA-Z-]{2,16}', language)):
        raise MaterialError('invalid-request', '转录语言必须是明确的短语言代码或省略', stage='index')
    if device not in {'cpu', 'cuda'}:
        raise MaterialError('invalid-request', '转录设备只支持 cpu 或 cuda', stage='index')
    compute_type = 'int8' if device == 'cpu' else 'float16'
    identity = embedding.model_identity(manager, 'whisper-small')
    config = {'language': language, 'vad': bool(vad), 'beamSize': beam_size,
              'computeType': compute_type, 'device': device, 'wordTimestamps': True}
    cache = _cache_key(media, 'asr', config, inputs=[media.data.artifact.sha256], model=identity)
    cached = store.cached(cache)
    if cached is not None:
        return IndexResult(cached, 'asr', reused=True, records=cached.data.recordCount)
    source = store.verify_artifact(media.data.artifact)
    staging = Path(tempfile.mkdtemp(prefix='asr-', dir=store.path('staging', exists=True, directory=True)))
    try:
        audio = staging / 'audio.wav'
        process = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(source),
                                  *LOCAL_INPUT_OPTIONS, '-map', '0:a:0', '-ac', '1', '-ar', '16000',
                                  '-c:a', 'pcm_s16le', '-y', str(audio)], capture_output=True, timeout=900)
        if process.returncode or not audio.is_file():
            raise MaterialError('decode-failed', '音轨提取失败，未发布转录索引', stage='index')
        from faster_whisper import WhisperModel
        model = WhisperModel(str(manager.path('whisper-small')), device=device, compute_type=compute_type,
                             cpu_threads=0, num_workers=1)
        segments, info = model.transcribe(str(audio), language=language, beam_size=beam_size,
                                          vad_filter=bool(vad), word_timestamps=True,
                                          condition_on_previous_text=False)
        records, warnings = [], []
        for index, segment in enumerate(segments):
            if index >= max_segments:
                warnings.append(f'转录分段超过 {max_segments} 条预算，已截断')
                break
            text = (segment.text or '').strip()
            if not text:
                continue
            start, end = seconds_us(segment.start), seconds_us(segment.end)
            if end <= start or end > (media.data.probe.durationUs or end) + 1_000_000:
                continue
            confidence = None
            if isinstance(segment.avg_logprob, (int, float)) and math.isfinite(segment.avg_logprob):
                confidence = min(1.0, max(0.0, math.exp(segment.avg_logprob)))
            words = []
            for word in (segment.words or [])[:128]:
                word_start, word_end = seconds_us(word.start), seconds_us(word.end)
                if word_end <= word_start or word_start < start or word_end > end:
                    continue
                words.append({'text': (word.word or '').strip() or '∅',
                              'localRange': {'startUs': word_start, 'endUs': word_end},
                              'confidence': min(1.0, max(0.0, float(word.probability)))})
            identifier = hashlib.sha256(f'{start}:{end}:{text}'.encode()).hexdigest()[:24]
            records.append({'id': f'asr-{identifier}', 'channel': 'asr', 'text': text,
                            'localRange': {'startUs': start, 'endUs': end}, 'language': info.language,
                            'confidence': confidence, 'words': words,
                            'alignment': 'unverified', 'origin': 'faster-whisper-small'})
    finally:
        for item in staging.iterdir():
            item.unlink(missing_ok=True)
        staging.rmdir()
    if not records:
        warnings.append('未识别到有效语音；空语音、纯音乐或背景噪声不冒充已转录内容')
    warnings.append('转录时间码与文字为模型输出，可能与专名、口音和背景音乐存在偏差')
    artifact, checked = _publish_records(store, records)
    return _store_index(store, media=media, channel='asr', config=config, records=checked,
                        artifacts=[artifact], inputs=[media.data.artifact.sha256], cache_key=cache,
                        tool={**toolchain(), 'model': identity}, warnings=warnings)


_OCR = None


def _ocr_engine(manager: ModelManager):
    global _OCR
    key = str(manager.root)
    if _OCR is not None and _OCR[0] == key:
        return _OCR[1]
    from .diagnostics import require_dependency
    require_dependency('rapidocr', extra='ocr', purpose='画面文字识别')
    from rapidocr import ModelType, OCRVersion, RapidOCR
    root = manager.path('rapidocr')
    params = {
        'Det.model_path': str(root / 'PP-OCRv4/ch_PP-OCRv4_det_infer.onnx'),
        'Det.ocr_version': OCRVersion.PPOCRV4, 'Det.model_type': ModelType.MOBILE,
        'Rec.model_path': str(root / 'PP-OCRv4/ch_PP-OCRv4_rec_infer.onnx'),
        'Rec.ocr_version': OCRVersion.PPOCRV4, 'Rec.model_type': ModelType.MOBILE,
        'Cls.model_path': str(root / 'PP-OCRv3/ch_ppocr_mobile_v2.0_cls_train.onnx'),
        'Cls.ocr_version': OCRVersion.PPOCRV4, 'Cls.model_type': ModelType.MOBILE,
        'Global.log_level': 'error',
    }
    engine = RapidOCR(params=params)
    _OCR = (key, engine)
    return engine


def index_ocr(store: MaterialStore, media, manager: ModelManager, *, max_frames: int = 24,
              options: dict | None = None) -> IndexResult:
    options = options or {}
    if type(max_frames) is not int or not 1 <= max_frames <= MAX_FRAMES:
        raise MaterialError('invalid-request', 'OCR 帧预算无效', stage='index')
    image = media.data.probe.kind == 'image'
    frames = None if image else _require_frames(store, media, options)
    identity = embedding.model_identity(manager, 'rapidocr')
    config = {'maxFrames': max_frames if not image else 1, 'detector': 'PP-OCRv4-mobile',
              'image': image,
              'framesIndex': frames.id if frames else None,
              'framesDigest': frames.data.artifacts[0].sha256 if frames else None}
    inputs = [frames.data.artifacts[0].sha256] if frames else [media.data.artifact.sha256]
    cache = _cache_key(media, 'ocr', config, inputs=inputs, model=identity)
    cached = store.cached(cache)
    if cached is not None:
        return IndexResult(cached, 'ocr', reused=True, records=cached.data.recordCount)
    engine = _ocr_engine(manager)
    if image:
        frame_records = [types.SimpleNamespace(frame=media.data.artifact, localRange=None)]
    else:
        frame_records = [item for item in store.records(frames.id) if item.frame and item.localRange][:max_frames]
    records, warnings = [], []
    for item in frame_records:
        path = store.verify_artifact(item.frame)
        try:
            output = engine(str(path))
        except Exception as exc:  # noqa: BLE001 - 识别器内部异常不能泄露绝对路径
            raise MaterialError('decode-failed', '画面文字识别失败，未发布 OCR 索引', stage='index') from None
        texts = [str(value).strip() for value in (output.txts or ()) if str(value).strip()]
        if not texts:
            continue
        boxes = []
        scores = list(output.scores or ())
        for index, text_value in enumerate(texts[:200]):
            polygon = output.boxes[index] if output.boxes is not None and index < len(output.boxes) else None
            if polygon is None or len(polygon) != 4:
                continue
            points = [[float(point[0]), float(point[1])] for point in polygon]
            if not all(math.isfinite(value) for point in points for value in point):
                continue
            score = scores[index] if index < len(scores) else None
            boxes.append({'text': text_value[:500], 'polygon': points,
                          'confidence': min(1.0, max(0.0, float(score))) if isinstance(score, (int, float)) else 0.0})
        if not boxes:
            continue
        window = item.localRange.model_dump(mode='json') if item.localRange else None
        identifier = hashlib.sha256(f'{window}:{item.frame.sha256}'.encode()).hexdigest()[:24]
        records.append({'id': f'ocr-{identifier}', 'channel': 'ocr',
                        'text': ' '.join(box['text'] for box in boxes)[:4_000],
                        'localRange': window, 'frame': item.frame.model_dump(mode='json'),
                        'language': None, 'confidence': round(sum(box['confidence'] for box in boxes) / len(boxes), 6),
                        'boxes': boxes, 'alignment': 'unverified', 'origin': 'rapidocr-ppocrv4'})
    if not records:
        warnings.append('采样帧未识别到文字；无烧录字、文字过小或框预算不足都可能为空')
    warnings.append('OCR 是识别结果而非原始字幕轨；可能误识别，不能作为产品身份或事实已核实证据')
    artifact, checked = _publish_records(store, records)
    return _store_index(store, media=media, channel='ocr', config=config, records=checked,
                        artifacts=[artifact], inputs=inputs, cache_key=cache,
                        tool={**toolchain(), 'model': identity}, warnings=warnings)


def _source_records(store: MaterialStore, media, channel: str) -> Index | None:
    index = _find_index(store, media, channel)
    return index


def index_text(store: MaterialStore, media, manager: ModelManager, *,
               sources=('captions', 'asr', 'ocr', 'chapters'), batch_size: int = 16) -> IndexResult:
    allowed = {'captions', 'asr', 'ocr', 'chapters'}
    if not sources or set(sources) - allowed:
        raise MaterialError('invalid-request', '文本索引来源必须来自 captions/asr/ocr/chapters', stage='index')
    inputs, pools = [], []
    for channel in sources:
        index = _source_records(store, media, channel)
        if index is None:
            continue
        inputs.append(index.data.artifacts[0].sha256)
        pools.append((channel, store.records(index.id)))
    if not pools:
        raise MaterialError('not-found', '没有可用于文本语义索引的字幕/转录/OCR 记录', stage='index')
    items = []
    for channel, records in pools:
        for record in records:
            if record.text.strip():
                items.append((channel, record))
    if not items:
        raise MaterialError('not-found', '已有索引没有任何文字内容', stage='index')
    warnings = []
    if len(items) > MAX_RECORDS:
        warnings.append(f'文字条目超过 {MAX_RECORDS} 条预算，已按来源顺序截断')
        items = items[:MAX_RECORDS]
    identity = embedding.model_identity(manager, 'e5-small')
    config = {'sources': list(sources), 'batchSize': batch_size, 'prefix': 'passage',
              'maxChars': embedding.MAX_TEXT_CHARS}
    cache = _cache_key(media, 'text', config, inputs=inputs, model=identity)
    cached = store.cached(cache)
    if cached is not None:
        return IndexResult(cached, 'text', reused=True, records=cached.data.recordCount)
    vectors = embedding.embed_texts(manager, [record.text for _, record in items],
                                    prefix='passage', batch_size=batch_size)
    vector_artifact = _publish_vectors(store, vectors)
    records = []
    for row, (channel, record) in enumerate(items):
        identifier = hashlib.sha256(f'{channel}:{record.id}'.encode()).hexdigest()[:24]
        records.append({'id': f'text-{identifier}', 'channel': 'text', 'text': record.text,
                        'localRange': record.localRange.model_dump(mode='json') if record.localRange else None,
                        'language': record.language, 'vectorRow': row,
                        'alignment': 'not-applicable', 'origin': f'e5-small:{channel}'})
    artifact, checked = _publish_records(store, records)
    spec = EmbeddingSpec(model='e5-small', revision=identity['revision'],
                         weightsSha256=next(item['sha256'] for item in identity['files']
                                            if item['path'] == 'model.safetensors'),
                         preprocessing=identity['preprocessing'], dimensions=embedding.dimensions(manager, 'e5-small'),
                         normalized=True, device='cpu', precision='float32')
    return _store_index(store, media=media, channel='text', config=config, records=checked,
                        artifacts=[artifact, vector_artifact], inputs=inputs, cache_key=cache,
                        embedding_spec=spec, tool={**toolchain(), 'model': identity}, warnings=warnings)


def index_visual(store: MaterialStore, media, manager: ModelManager, *, max_frames: int = 48,
                 options: dict | None = None) -> IndexResult:
    options = options or {}
    if type(max_frames) is not int or not 1 <= max_frames <= MAX_FRAMES:
        raise MaterialError('invalid-request', '视觉索引帧预算无效', stage='index')
    image = media.data.probe.kind == 'image'
    frames = None if image else _require_frames(store, media, options)
    identity = embedding.model_identity(manager, 'siglip2-base')
    config = {'maxFrames': max_frames if not image else 1, 'image': image,
              'framesIndex': frames.id if frames else None,
              'framesDigest': frames.data.artifacts[0].sha256 if frames else None}
    inputs = [frames.data.artifacts[0].sha256] if frames else [media.data.artifact.sha256]
    cache = _cache_key(media, 'visual', config, inputs=inputs, model=identity)
    cached = store.cached(cache)
    if cached is not None:
        return IndexResult(cached, 'visual', reused=True, records=cached.data.recordCount)
    if image:
        frame_records = [types.SimpleNamespace(frame=media.data.artifact, localRange=None)]
    else:
        frame_records = [item for item in store.records(frames.id) if item.frame and item.localRange][:max_frames]
    if not frame_records:
        raise MaterialError('not-found', '没有可用关键帧，无法建立视觉索引', stage='index')
    paths = [store.verify_artifact(item.frame) for item in frame_records]
    vectors = embedding.embed_images(manager, paths)
    vector_artifact = _publish_vectors(store, vectors)
    records = []
    for row, item in enumerate(frame_records):
        window = item.localRange.model_dump(mode='json') if item.localRange else None
        identifier = hashlib.sha256(f'{window}:{item.frame.sha256}'.encode()).hexdigest()[:24]
        records.append({'id': f'visual-{identifier}', 'channel': 'visual', 'text': '',
                        'localRange': window,
                        'frame': item.frame.model_dump(mode='json'), 'vectorRow': row,
                        'alignment': 'not-applicable', 'origin': 'siglip2-base'})
    artifact, checked = _publish_records(store, records)
    spec = EmbeddingSpec(model='siglip2-base', revision=identity['revision'],
                         weightsSha256=next(item['sha256'] for item in identity['files']
                                            if item['path'] == 'model.safetensors'),
                         preprocessing=identity['preprocessing'], dimensions=embedding.dimensions(manager, 'siglip2-base'),
                         normalized=True, device='cpu', precision='float32')
    warnings = ['视觉召回只表示帧级图文相似；不证明动作完整、先后因果、人物身份或真实事件']
    if len(frame_records) < 3:
        warnings.append('采样帧过少，单帧相似不能代表整段画面')
    return _store_index(store, media=media, channel='visual', config=config, records=checked,
                        artifacts=[artifact, vector_artifact], inputs=inputs,
                        cache_key=cache, embedding_spec=spec,
                        tool={**toolchain(), 'model': identity}, warnings=warnings)


def index_media(store: MaterialStore, media, manager: ModelManager, channels,
                *, options: dict | None = None) -> list[IndexResult]:
    """按通道顺序执行；依赖帧的通道会先建立/复用帧索引。"""
    if not channels or set(channels) - set(CHANNELS):
        raise MaterialError('invalid-request', '索引通道必须来自已知集合', stage='index')
    options = options or {}
    results: list[IndexResult] = []
    requested = list(dict.fromkeys(channels))
    if {'shots', 'frames'} & set(requested):
        pair = index_shots(store, media, **(options.get('shots') or {}))
        if 'shots' in requested:
            results.append(pair[0])
        if 'frames' in requested:
            results.append(pair[1])
        requested = [item for item in requested if item not in {'shots', 'frames'}]
    for channel in [item for item in ('captions', 'chapters', 'asr', 'ocr', 'text', 'visual')
                    if item in requested]:
        if channel == 'captions':
            results.append(index_captions(store, media))
        elif channel == 'chapters':
            results.append(index_chapters(store, media))
        elif channel == 'asr':
            results.append(index_asr(store, media, manager, **(options.get('asr') or {})))
        elif channel == 'ocr':
            results.append(index_ocr(store, media, manager,
                                     max_frames=(options.get('ocr') or {}).get('max_frames', 24),
                                     options=options))
        elif channel == 'text':
            results.append(index_text(store, media, manager, **(options.get('text') or {})))
        elif channel == 'visual':
            results.append(index_visual(store, media, manager,
                                        max_frames=(options.get('visual') or {}).get('max_frames', 48),
                                        options=options))
    return results


def load_vectors(store: MaterialStore, index: Index) -> np.ndarray:
    """只接受 .npy float32 分片；拒绝 pickle，并核对维数与记录数。"""
    if index.data.embeddingSpec is None or len(index.data.artifacts) < 2:
        raise MaterialError('invalid-request', '索引没有向量分片', stage='find')
    path = store.verify_artifact(index.data.artifacts[1])
    try:
        matrix = np.load(path, allow_pickle=False)
    except (ValueError, OSError) as exc:
        raise MaterialError('media-invalid', '向量分片无法安全读取', stage='find') from exc
    spec = index.data.embeddingSpec
    if (matrix.dtype != np.float32 or matrix.ndim != 2 or matrix.shape[1] != spec.dimensions
            or matrix.shape[0] != index.data.recordCount or not np.all(np.isfinite(matrix))):
        raise MaterialError('hash-mismatch', '向量分片与索引身份不一致', stage='find')
    return matrix
