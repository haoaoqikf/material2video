"""获取编排：本地文件、公开直链、平台 worker 与网页声明媒体。

所有网络下载先落到工作库的私有暂存目录，完成大小、摘要、探测与首段解码后
才按内容寻址发布。区间请求不放宽远端 Range 语义：先取得受预算约束的完整
文件，再在本地按真实解码位置精裁；无法证明上游源原点时保持映射未知。
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .contracts import (Artifact, CaptionTrack, Chapter, Media, MediaData, Probe, SourceMapping,
                        TimeRange, Timeline, fingerprint)
from .errors import MaterialError
from .media import LOCAL_FORMATS, LOCAL_INPUT_OPTIONS, probe, seconds_us, toolchain
from .network import NetworkBudget, SafeHTTP, public_url, validate_url
from .paths import no_links
from .registration import register_local
from .store import MaterialStore
from .webpage import WebpageProvider

logger = logging.getLogger(__name__)

MEDIA_SUFFIXES = {'.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi', '.ts', '.flv', '.mp3', '.m4a',
                  '.aac', '.wav', '.flac', '.ogg', '.opus', '.png', '.jpg', '.jpeg', '.webp'}
SUBTITLE_SUFFIXES = {'.srt', '.vtt', '.ass'}
SUBTITLE_FORMAT = {'.srt': 'srt', '.vtt': 'vtt', '.ass': 'ass'}
MAX_FILE_BYTES = 4 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class FetchBudget:
    max_bytes: int = 1024 * 1024 * 1024
    total_bytes: int = 3 * 1024 * 1024 * 1024
    max_duration_us: int = 6 * 3600 * 1_000_000
    min_free_bytes: int = 2 * 1024 * 1024 * 1024
    timeout_s: float = 300.0
    decode_seconds: float = 5.0
    retries: int = 2

    def __post_init__(self):
        for value, label, upper in ((self.max_bytes, '单件字节', MAX_FILE_BYTES),
                                    (self.total_bytes, '总字节', MAX_FILE_BYTES * 4),
                                    (self.max_duration_us, '时长', 24 * 3600 * 1_000_000)):
            if type(value) is not int or not 0 < value <= upper:
                raise MaterialError('invalid-request', f'获取{label}预算无效', stage='fetch')
        if not isinstance(self.timeout_s, (int, float)) or isinstance(self.timeout_s, bool) or not 0 < self.timeout_s <= 3600:
            raise MaterialError('invalid-request', '获取时限预算无效', stage='fetch')


@dataclass
class FetchResult:
    media: Media
    warnings: list[str]
    stats: dict | None = None


def _decode_check(path: Path, kind: str, *, seconds: float) -> None:
    """只解码开头一小段，确认容器与首帧/首音可见性；完整解码在精裁输出上另做。"""
    if kind == 'image':
        return
    executable = get_ffmpeg_exe()
    selection = ['-map', '0:v:0'] if kind == 'video' else ['-map', '0:a:0']
    try:
        result = subprocess.run([executable, '-v', 'error', '-xerror', '-nostdin', '-i', str(path),
                                 *LOCAL_INPUT_OPTIONS, *selection, '-t', f'{seconds:.3f}', '-f', 'null', '-'],
                                capture_output=True, timeout=max(30.0, seconds * 20))
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '媒体首段解码超时', stage='fetch') from exc
    if result.returncode:
        raise MaterialError('decode-failed', '媒体首段无法解码，未发布', stage='fetch')


def _measure(path: Path, budget: FetchBudget) -> Probe:
    result = probe(path, timeout_s=max(30.0, min(budget.timeout_s, 600)))
    if result.durationUs is not None and result.durationUs > budget.max_duration_us:
        raise MaterialError('resource-limit', '媒体时长超过本次获取预算', stage='fetch')
    _decode_check(path, result.kind, seconds=budget.decode_seconds)
    return result


def _frame_us(result: Probe) -> int:
    fps = result.fps
    return max(1, round(fps.den * 1_000_000 / fps.num)) if fps else 33_334


def _trim(source: Path, destination: Path, interval: TimeRange | None) -> None:
    if interval is None:
        shutil.copyfile(source, destination)
        return
    start_s = interval.startUs / 1_000_000
    length_s = (interval.endUs - interval.startUs) / 1_000_000
    executable = get_ffmpeg_exe()
    try:
        # -ss 作为输出选项做精确解码定位；-t 用请求长度，不依赖 -to 的相对时间语义。
        result = subprocess.run([executable, '-v', 'error', '-nostdin', '-i', str(source),
                                 *LOCAL_INPUT_OPTIONS, '-ss', f'{start_s:.6f}', '-t', f'{length_s:.6f}',
                                 '-map', '0:v:0?', '-map', '0:a:0?', '-c:v', 'libx264', '-preset', 'veryfast',
                                 '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                                 '-movflags', '+faststart', str(destination)],
                                capture_output=True, timeout=3600)
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '本地精裁超时', stage='fetch') from exc
    if result.returncode or not destination.is_file() or not destination.stat().st_size:
        raise MaterialError('decode-failed', '本地精裁失败，未发布片段', stage='fetch')


def _merge(tracks: list[Path], destination: Path) -> None:
    video = next((item for item in tracks if _stream_kind(item) == 'video'), None)
    audio = next((item for item in tracks if _stream_kind(item) == 'audio'), None)
    if video is None:
        raise MaterialError('media-invalid', '平台未返回可用的视频轨', stage='fetch')
    executable = get_ffmpeg_exe()
    command = [executable, '-v', 'error', '-nostdin', '-i', str(video)]
    if audio is not None:
        command += ['-i', str(audio), '-map', '0:v:0', '-map', '1:a:0']
    else:
        command += ['-map', '0:v:0']
    command += ['-c', 'copy', str(destination)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '本地分轨合并超时', stage='fetch') from exc
    if result.returncode or not destination.is_file() or not destination.stat().st_size:
        raise MaterialError('decode-failed', '本地分轨合并失败，未发布媒体', stage='fetch')


def _stream_kind(path: Path) -> str | None:
    try:
        return probe(path, timeout_s=60).kind
    except MaterialError:
        return None


def _range(value, duration_us: int | None, *, allow_image: bool) -> TimeRange | None:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            value = TimeRange.model_validate(value)
        except Exception as exc:  # noqa: BLE001 - 统一映射为契约错误
            raise MaterialError('invalid-request', '请求区间必须是微秒半开区间', stage='fetch') from exc
    if not isinstance(value, TimeRange):
        raise MaterialError('invalid-request', '请求区间必须是微秒半开区间', stage='fetch')
    if duration_us is not None and value.endUs > duration_us:
        raise MaterialError('invalid-request', '请求区间越过实际媒体时长', stage='fetch')
    if not allow_image:
        raise MaterialError('invalid-request', '图片不能声明时间区间', stage='fetch')
    return value


def _fetch_identity(source_id: str, location: str, variant: str, interval: TimeRange | None,
                    tool: str, extra: dict | None = None) -> str:
    return fingerprint({'sourceId': source_id, 'location': location, 'variant': variant,
                        'requestedRange': interval.model_dump(mode='json') if interval else None,
                        'tool': tool, **(extra or {})})


def _publish_subtitles(store: MaterialStore, files: list[Path], *, budget: FetchBudget,
                       manual_languages: set[str] | None = None,
                       default_origin: str = 'local') -> list[CaptionTrack]:
    """字幕来源分人工/自动/本地三类；任何一类都不表示与实际画面对齐已验证。"""
    tracks: list[CaptionTrack] = []
    manual = {item.lower() for item in (manual_languages or ())}
    for path in sorted(files):
        if path.suffix.lower() not in SUBTITLE_SUFFIXES or not path.is_file():
            continue
        if not 0 < path.stat().st_size <= min(budget.max_bytes, 32 * 1024 * 1024):
            raise MaterialError('resource-limit', '字幕文件为空或超过预算', stage='fetch')
        language = _language_from_name(path.name)
        if default_origin == 'platform':
            automatic = '.auto.' in path.name.lower() or (language or '').lower() not in manual
            origin = 'automatic' if automatic else 'manual'
        else:
            origin = default_origin
        tracks.append(CaptionTrack(artifact=store.publish_file(path, max_bytes=min(budget.max_bytes, 32 * 1024 * 1024)),
                                   language=language, origin=origin, alignment='unverified',
                                   format=SUBTITLE_FORMAT[path.suffix.lower()]))
    return tracks


def _language_from_name(name: str) -> str | None:
    match = re.search(r'[._-]([a-z]{2,3}(?:-[A-Za-z]{2,4})?)[._-]?(?:auto)?\.(?:srt|vtt|ass)$', name)
    return match.group(1) if match else None


def _chapters(values: list[dict], duration_us: int | None, *, source: str) -> list[Chapter]:
    result: list[Chapter] = []
    for item in values[:512]:
        start, end = item.get('startSeconds'), item.get('endSeconds')
        title = item.get('title')
        if not isinstance(title, str) or not title.strip():
            continue
        try:
            start_us, end_us = seconds_us(start), seconds_us(end)
        except MaterialError:
            continue
        if end_us <= start_us:
            continue
        if duration_us is not None and end_us > duration_us:
            # 平台声明的章节超出实测媒体时按实测边界截断，并保留来源说明。
            end_us = duration_us
            if end_us <= start_us:
                continue
        result.append(Chapter(title=title.strip()[:500],
                              localRange=TimeRange(startUs=start_us, endUs=end_us)))
    if len(result) > 1 and result[0].localRange.startUs > 0:
        result[0] = Chapter(title=result[0].title,
                            localRange=TimeRange(startUs=0, endUs=result[0].localRange.endUs))
    return result


def _probe_without_mapping(result: Probe) -> Probe:
    return result.model_copy(deep=True, update={'timeline': Timeline(
        localOriginPts=result.timeline.localOriginPts, timeBase=result.timeline.timeBase,
        sourceMapping=SourceMapping())})


def _verified(result: Probe, origin_us: int, max_error_us: int) -> Probe:
    return result.model_copy(deep=True, update={'timeline': Timeline(
        localOriginPts=result.timeline.localOriginPts, timeBase=result.timeline.timeBase,
        sourceMapping=SourceMapping(status='verified', method='full-input' if origin_us == 0 else 'local-trim',
                                    sourceOriginUs=origin_us, maxErrorUs=max_error_us))})


def _media(store: MaterialStore, *, source_id: str, artifact: Artifact, result: Probe,
           fetch_identity: str, coverage: str, upstream: str | None, interval: TimeRange | None,
           observed: TimeRange | None, captions: list[CaptionTrack], chapters: list[Chapter],
           toolchain_extra: dict, limitations: list[str]) -> Media:
    data = MediaData(sourceId=source_id, artifact=artifact, probe=result, variant='original',
                     coverage=coverage, requestedRange=interval, observedRange=observed,
                     upstreamFullSha256=upstream, fetchIdentity=fetch_identity,
                     toolchain={**toolchain(), **toolchain_extra}, captions=captions, chapters=chapters)
    # 重复相同获取意图返回同一记录；createdAt 不参与身份，否则每次重试都会与新快照冲突。
    document_id = f'media-{fingerprint(data.model_dump(mode="json"))[:32]}'
    try:
        previous = store.get(document_id, kind='material.media')
    except MaterialError as exc:
        if exc.code != 'not-found':
            raise
    else:
        if previous.data != data:
            raise MaterialError('conflict', '同一媒体身份对应不同实测内容', stage='fetch')
        return previous
    return store.put(Media(id=document_id, data=data))


def fetch_local(store: MaterialStore, *, source, path: Path, budget: FetchBudget | None = None,
                requested_range: TimeRange | None = None, title: str | None = None) -> FetchResult:
    """获取显式本地普通文件；文件本身即完整来源，不伪造上游摘要。"""
    budget = budget or FetchBudget()
    from .registration import local_file
    path = local_file(path)
    if path.suffix.lower() not in MEDIA_SUFFIXES:
        raise MaterialError('unsupported-source', '本地获取只接受已知媒体扩展名', stage='fetch')
    if path.stat().st_size > budget.max_bytes:
        raise MaterialError('resource-limit', '本地文件超过本次单件预算，未复制', stage='fetch')
    if shutil.disk_usage(store.root).free < path.stat().st_size + budget.min_free_bytes:
        raise MaterialError('resource-limit', '素材库磁盘余量不足，未复制', stage='fetch')
    identity = _fetch_identity(source.id, f'local:{path.name}', 'original', requested_range, 'local-copy')
    staging = Path(tempfile.mkdtemp(prefix='fetch-', dir=store.path('staging', exists=True, directory=True)))
    warnings: list[str] = []
    try:
        working = staging / f'input{path.suffix.lower()}'
        shutil.copyfile(path, working)
        full = _measure(working, budget)
        interval = _range(requested_range, full.durationUs, allow_image=full.kind != 'image')
        if full.kind == 'image':
            final = staging / f'final{path.suffix.lower()}'
            shutil.copyfile(working, final)
            result = full
            coverage, interval, observed, upstream = 'full', None, None, None
        else:
            final = staging / 'final.mp4'
            _trim(working, final, interval)
            result = _measure(final, budget)
            if interval is None:
                result = _verified(result, 0, 0)
                coverage, observed, upstream = 'full', None, None
            else:
                result = _verified(result, interval.startUs, _frame_us(full))
                coverage, observed, upstream = 'section', interval, None
        artifact = store.publish_file(final, max_bytes=budget.max_bytes, min_free_bytes=budget.min_free_bytes)
        if coverage == 'full':
            upstream = artifact.sha256
        subtitles = _publish_subtitles(store, [item for item in path.parent.iterdir()
                                               if item.is_file() and item.suffix.lower() in SUBTITLE_SUFFIXES
                                               and (item.stem == path.stem
                                                    or item.name.startswith(path.stem + '.'))], budget=budget)
        media = _media(store, source_id=source.id, artifact=artifact, result=result,
                       fetch_identity=identity, coverage=coverage, upstream=upstream,
                       interval=interval, observed=observed, captions=subtitles, chapters=[],
                       toolchain_extra={'method': 'local-copy'}, limitations=warnings)
        return FetchResult(media=media, warnings=warnings)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _network_budget(budget: FetchBudget) -> NetworkBudget:
    return NetworkBudget(max_bytes=budget.max_bytes, total_bytes=budget.total_bytes,
                         max_requests=64, timeout_s=min(budget.timeout_s, 120.0),
                         deadline_s=budget.timeout_s, retries=budget.retries,
                         min_free_bytes=budget.min_free_bytes)


def _download(http: SafeHTTP, url: str, destination: Path, *, budget: FetchBudget) -> dict:
    return http.download(url, destination, max_bytes=budget.max_bytes)


def _subtitle_files(directory: Path) -> list[Path]:
    return [item for item in directory.iterdir() if item.is_file()
            and item.suffix.lower() in SUBTITLE_SUFFIXES]


def fetch_public_file(store: MaterialStore, *, source, url: str, budget: FetchBudget | None = None,
                      requested_range: TimeRange | None = None, http: SafeHTTP | None = None) -> FetchResult:
    """受控直链获取；默认完整下载后本地精裁，不把远端 Range 响应当可信时间证明。"""
    budget = budget or FetchBudget()
    validate_url(url)
    identity = _fetch_identity(source.id, public_url(url), 'original', requested_range, 'safe-http')
    http = http or SafeHTTP(_network_budget(budget))
    staging = Path(tempfile.mkdtemp(prefix='fetch-', dir=store.path('staging', exists=True, directory=True)))
    warnings: list[str] = []
    try:
        raw = staging / 'download'
        stats = _download(http, url, raw, budget=budget)
        kind = _sniff_suffix(raw)
        working = staging / f'input{kind}'
        raw.replace(working)
        full = _measure(working, budget)
        interval = _range(requested_range, full.durationUs, allow_image=full.kind != 'image')
        if full.kind == 'image':
            final = staging / f'final{working.suffix.lower()}'
            shutil.copyfile(working, final)
            result = full
            coverage, observed, upstream = 'full', None, stats['sha256']
        else:
            final = staging / 'final.mp4'
            _trim(working, final, interval)
            result = _measure(final, budget)
            if interval is None:
                result = _verified(result, 0, 0)
                coverage, observed, upstream = 'full', None, stats['sha256']
            else:
                result = _verified(result, interval.startUs, _frame_us(full))
                coverage, observed, upstream = 'section', interval, None
        artifact = store.publish_file(final, max_bytes=budget.max_bytes, min_free_bytes=budget.min_free_bytes)
        media = _media(store, source_id=source.id, artifact=artifact, result=result,
                       fetch_identity=identity, coverage=coverage, upstream=upstream,
                       interval=interval, observed=observed, captions=[], chapters=[],
                       toolchain_extra={'method': 'safe-http', 'sourceBytes': stats['bytes'],
                                         'requests': stats['requests']}, limitations=warnings)
        return FetchResult(media=media, warnings=warnings,
                           stats={key: stats[key] for key in ('bytes', 'requests', 'elapsedSeconds')})
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _sniff_suffix(path: Path) -> str:
    try:
        probe(path, timeout_s=60)
        return '.mp4'
    except MaterialError:
        pass
    with path.open('rb') as stream:
        head = stream.read(64)
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if head.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return '.webp'
    if head.startswith(b'ID3') or head[:2] in {b'\xff\xfb', b'\xff\xf3'}:
        return '.mp3'
    raise MaterialError('media-invalid', '远端文件无法识别为受支持的本地媒体', stage='fetch')


def fetch_platform(store: MaterialStore, *, source, url: str, budget: FetchBudget | None = None,
                   format_id: str = 'best', subtitles: bool = True, cookies: str | None = None,
                   requested_range: TimeRange | None = None, worker=None) -> FetchResult:
    """平台获取：worker 只下载分轨与字幕，父层本地合并、探测和发布。"""
    from .ytdlp_worker import run_ytdlp
    budget = budget or FetchBudget()
    validate_url(url)
    worker = worker or run_ytdlp
    identity = _fetch_identity(source.id, public_url(url), format_id, requested_range, 'yt-dlp',
                               {'subtitles': bool(subtitles)})
    staging = Path(tempfile.mkdtemp(prefix='platform-', dir=store.path('staging', exists=True, directory=True)))
    warnings: list[str] = []
    try:
        request = {'schemaVersion': 1, 'mode': 'download', 'url': url, 'directory': str(staging),
                   'format_id': format_id, 'subtitles': bool(subtitles),
                   'budget': _worker_budget(budget)}
        if cookies is not None:
            request['cookies'] = str(cookies)
        try:
            data = worker(request, timeout_s=budget.timeout_s)
        except MaterialError as exc:
            raise MaterialError(exc.code, str(exc), stage=exc.stage, retryable=exc.retryable,
                                source_id=source.id) from None
        media_files = [staging / item['path'] for item in data.get('files', []) if item['kind'] == 'media']
        if not media_files or len(media_files) > 3:
            raise MaterialError('media-invalid', '平台未返回可合并的媒体轨', stage='fetch')
        for item in media_files:
            info = item.lstat()
            if not item.is_file() or info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise MaterialError('security-blocked', '平台输出必须是独立普通文件', stage='fetch')
            if item.stat().st_size > budget.max_bytes:
                raise MaterialError('resource-limit', '平台单轨文件超过获取预算', stage='fetch')
        metadata = data.get('metadata') or {}
        if metadata.get('has_drm'):
            raise MaterialError('unsupported-source', '平台声明 DRM，未发布媒体', stage='fetch')
        if metadata.get('live_status') in {'is_live', 'is_upcoming'}:
            raise MaterialError('unsupported-source', '直播媒体不在自动获取范围', stage='fetch')
        merged = staging / 'merged.mkv'
        if len(media_files) > 1:
            _merge(media_files, merged)
            base_mapping = 'unknown'
        else:
            shutil.copyfile(media_files[0], merged)
            base_mapping = 'verified'
        full = _measure(merged, budget)
        interval = _range(requested_range, full.durationUs, allow_image=full.kind != 'image')
        final = staging / 'final.mp4'
        _trim(merged, final, interval)
        result = _measure(final, budget)
        if interval is None and base_mapping == 'verified':
            result = _verified(result, 0, 0)
            coverage, observed, upstream = 'full', None, None
        elif interval is None:
            result = _probe_without_mapping(result)
            coverage, observed, upstream = 'unknown', None, None
        else:
            if base_mapping == 'verified':
                result = _verified(result, interval.startUs, _frame_us(full))
            else:
                result = _probe_without_mapping(result)
            coverage, observed, upstream = 'section', interval, None
        artifact = store.publish_file(final, max_bytes=budget.max_bytes, min_free_bytes=budget.min_free_bytes)
        manual = {str(item).lower() for item in (metadata.get('subtitles') or {}).get('manual', [])}
        captions = _publish_subtitles(store, _subtitle_files(staging), budget=budget,
                                      manual_languages=manual, default_origin='platform')
        chapters = _chapters(metadata.get('chapters') or [], result.durationUs, source='platform')
        if coverage == 'unknown' and base_mapping == 'unknown':
            warnings.append('平台返回分轨，合并后无法证明上游字节身份；源时间映射保持 unknown')
        media = _media(store, source_id=source.id, artifact=artifact, result=result,
                       fetch_identity=identity, coverage=coverage, upstream=upstream,
                       interval=interval, observed=observed, captions=captions, chapters=chapters,
                       toolchain_extra={'method': 'yt-dlp', 'tracks': len(media_files),
                                         'formatId': format_id},
                       limitations=warnings)
        return FetchResult(media=media, warnings=warnings, stats=data.get('stats'))
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _worker_budget(budget: FetchBudget) -> dict:
    return {'max_bytes': budget.max_bytes, 'total_bytes': budget.total_bytes, 'max_requests': 64,
            'timeout_s': min(budget.timeout_s, 120.0), 'deadline_s': budget.timeout_s,
            'retries': budget.retries, 'min_free_bytes': budget.min_free_bytes}


def _choose_locator(http: SafeHTTP, resolved, budget: FetchBudget) -> str:
    """多资产来源按预算选最大可用项；不默认抓取 5 GB 原始母带。"""
    pairs = [(item.kind, resolved.locators.get(item.id), item.bytes)
             for item in resolved.source.variants if resolved.locators.get(item.id)]
    if not pairs:
        raise MaterialError('media-invalid', '来源没有可直接获取的文件', stage='fetch')
    for kinds in ({'video'}, {'audio'}, {'image'}):
        pool = [entry for entry in pairs if entry[0] in kinds]
        if not pool:
            continue
        if len(pool) == 1:
            return pool[0][1]
        sized = []
        for kind, locator, declared in pool[:16]:
            if declared is not None:
                sized.append((declared, locator))
                continue
            try:
                response = http.open(locator, method='HEAD', max_bytes=1)
                try:
                    length = response.headers.get('Content-Length')
                finally:
                    response.close()
                if length and length.isdigit():
                    sized.append((int(length), locator))
            except MaterialError as exc:
                if exc.code == 'cancelled':
                    raise
        under = [entry for entry in sized if entry[0] <= budget.max_bytes]
        if under:
            return max(under)[1]
        if sized:
            smallest = min(sized)
            raise MaterialError('resource-limit',
                                f'来源最小可用文件约 {smallest[0] // (1024 * 1024)} MiB，超过当前单件预算；'
                                '可提高 --max-mb 或改用较小版本', stage='fetch')
        return pool[0][1]
    raise MaterialError('media-invalid', '来源没有可用的图像/视频/音频资产', stage='fetch')


def fetch_page(store: MaterialStore, *, source, url: str, budget: FetchBudget | None = None,
               http: SafeHTTP | None = None, requested_range: TimeRange | None = None) -> FetchResult:
    """解析显式页面声明的媒体；选取声明规格最大的一项，不执行脚本。"""
    budget = budget or FetchBudget()
    http = http or SafeHTTP(_network_budget(budget))
    resolved = WebpageProvider(http).resolve(source.data, locator=url)
    # locator 只在内存里；它可能是带签名参数的临时地址，不能从脱敏后的 variant 反推。
    candidates = [((item.width or 0) * (item.height or 0), item.kind, resolved.locators.get(item.id))
                  for item in resolved.source.variants]
    candidates = [entry for entry in candidates if entry[2]]
    if not candidates:
        raise MaterialError('media-invalid', '页面没有可直接获取的媒体声明；请显式提供文件或直链', stage='fetch')
    videos = [entry for entry in candidates if entry[1] == 'video']
    _, _, locator = max(videos or candidates)
    logger.info('页面媒体获取 source=%s declared=%d', source.id, len(candidates))
    return fetch_public_file(store, source=source, url=locator, budget=budget,
                             requested_range=requested_range, http=http)


def fetch_source(store: MaterialStore, *, source, locator: str | None = None,
                 budget: FetchBudget | None = None, format_id: str = 'best', subtitles: bool = True,
                 cookies: str | None = None, requested_range: TimeRange | None = None,
                 http: SafeHTTP | None = None, worker=None) -> FetchResult:
    """按来源种类分派；未验证的站点链接尽力走平台 worker，不宣称稳定支持。"""
    budget = budget or FetchBudget()
    http = http or SafeHTTP(_network_budget(budget))
    provider = source.data.provider
    if provider == 'local':
        if locator is None or not Path(locator).is_file():
            raise MaterialError('invalid-request', '本地来源重新获取时必须显式提供原文件', stage='fetch')
        return fetch_local(store, source=source, path=Path(locator), budget=budget,
                           requested_range=requested_range)
    if locator is None:
        if source.data.sourceUrl is None:
            raise MaterialError('locator-required', '来源地址已脱敏，请显式重新提供原链接', stage='fetch')
        locator = source.data.sourceUrl
    if provider in {'webpage', 'url'}:
        return fetch_page(store, source=source, url=locator, budget=budget, http=http,
                          requested_range=requested_range)
    if provider in {'http-file'}:
        return fetch_public_file(store, source=source, url=locator, budget=budget, http=http,
                                 requested_range=requested_range)
    if provider in {'commons', 'archive', 'nasa', 'pixabay'}:
        from .discovery import providers
        adapter = providers(http).get(provider)
        if adapter is None:
            raise MaterialError('unsupported-source', '来源适配器不可用', stage='fetch')
        resolved = adapter.resolve(source.data)
        if not resolved.locators:
            raise MaterialError('media-invalid', '来源没有可直接获取的文件', stage='fetch')
        best = _choose_locator(http, resolved, budget)
        return fetch_public_file(store, source=source, url=best, budget=budget, http=http,
                                 requested_range=requested_range)
    if provider in {'youtube', 'bilibili', 'douyin', 'xiaohongshu', 'weibo', 'xigua', 'platform', 'url-platform'}:
        return fetch_platform(store, source=source, url=locator, budget=budget, format_id=format_id,
                              subtitles=subtitles, cookies=cookies, requested_range=requested_range,
                              worker=worker)
    raise MaterialError('unsupported-source', '来源种类不在受控获取范围', stage='fetch')
