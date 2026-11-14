"""获取编排：本地/直链/平台分轨的发布、时间映射与失败边界。"""
from __future__ import annotations

import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
import pytest

from m2v.materials import fetch
from m2v.materials.contracts import Source, SourceData, TimeRange
from m2v.materials.errors import MaterialError
from m2v.materials.store import MaterialStore


def _source(provider='local', title='候选'):
    return Source(id=f'source-{provider}', data=SourceData(provider=provider, title=title))


def _clip(path: Path, *, seconds=2.0, audio=True, container='mkv'):
    arguments = ['-f', 'lavfi', '-i', f'testsrc2=size=96x64:rate=12:duration={seconds}']
    if audio:
        arguments += ['-f', 'lavfi', '-i', f'sine=frequency=440:sample_rate=48000:duration={seconds}']
    arguments += ['-c:v', 'ffv1']
    if audio:
        arguments += ['-c:a', 'pcm_s16le']
    process = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-nostdin', '-loglevel', 'error',
                              *arguments, str(path)], capture_output=True, timeout=60)
    assert process.returncode == 0, process.stderr.decode('utf-8', 'replace')
    return path


def _image(path: Path):
    from PIL import Image
    Image.new('RGB', (64, 48), color='navy').save(path, format='PNG')
    return path


@pytest.mark.media
def test_local_full_fetch_publishes_verified_mapping_and_sidecar_captions(tmp_path):
    media_file = _clip(tmp_path / 'clip.mkv')
    (tmp_path / 'clip.zh.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\n素材字幕\n', encoding='utf-8')
    with MaterialStore(tmp_path / 'library') as store:
        source = _source()
        store.put(source)
        result = fetch.fetch_local(store, source=source, path=media_file)
        data = result.media.data
        assert data.coverage == 'full'
        assert data.upstreamFullSha256 == data.artifact.sha256
        assert data.probe.timeline.sourceMapping.status == 'verified'
        assert data.probe.timeline.sourceMapping.sourceOriginUs == 0
        assert [track.origin for track in data.captions] == ['local']
        assert data.captions[0].format == 'srt' and data.captions[0].alignment == 'unverified'
        assert result.media.id.startswith('media-')
        # 相同获取意图重复执行返回同一记录，不因 createdAt 变化而冲突。
        again = fetch.fetch_local(store, source=source, path=media_file)
        assert again.media == result.media


@pytest.mark.media
def test_local_section_fetch_trims_locally_and_maps_verified_origin(tmp_path):
    media_file = _clip(tmp_path / 'clip.mkv', seconds=2.0)
    with MaterialStore(tmp_path / 'library') as store:
        source = _source()
        store.put(source)
        interval = TimeRange(startUs=400_000, endUs=1_400_000)
        result = fetch.fetch_local(store, source=source, path=media_file, requested_range=interval)
        data = result.media.data
        assert data.coverage == 'section' and data.upstreamFullSha256 is None
        assert data.requestedRange == interval and data.observedRange == interval
        assert abs(data.probe.durationUs - 1_000_000) <= 100_000
        mapping = data.probe.timeline.sourceMapping
        assert mapping.status == 'verified' and mapping.sourceOriginUs == 400_000
        assert mapping.maxErrorUs and mapping.maxErrorUs > 0


@pytest.mark.media
def test_local_image_fetch_keeps_image_without_time_window(tmp_path):
    image_file = _image(tmp_path / 'picture.png')
    with MaterialStore(tmp_path / 'library') as store:
        source = _source()
        store.put(source)
        result = fetch.fetch_local(store, source=source, path=image_file)
        data = result.media.data
        assert data.probe.kind == 'image' and data.probe.durationUs is None
        assert data.coverage == 'full' and data.requestedRange is None
        with pytest.raises(MaterialError):
            fetch.fetch_local(store, source=source, path=image_file,
                              requested_range=TimeRange(startUs=0, endUs=1_000))


class _HTTP:
    def __init__(self, payload: bytes | Exception):
        self.payload = payload
        self.calls = 0

    def download(self, url, destination, *, max_bytes=None):
        self.calls += 1
        if isinstance(self.payload, Exception):
            raise self.payload
        destination.write_bytes(self.payload)
        from hashlib import sha256
        return {'path': str(destination), 'bytes': len(self.payload), 'sha256': sha256(self.payload).hexdigest(),
                'sourceUrl': url, 'resumedBytes': 0, 'transferredBytes': len(self.payload),
                'requests': 1, 'elapsedSeconds': 0.1}


@pytest.mark.media
def test_public_file_fetch_reports_source_bytes_and_rejects_bad_media(tmp_path):
    payload = _clip(tmp_path / 'remote.mkv').read_bytes()
    with MaterialStore(tmp_path / 'library') as store:
        source = _source('http-file')
        store.put(source)
        http = _HTTP(payload)
        result = fetch.fetch_public_file(store, source=source, url='https://example.com/video.mkv', http=http)
        assert http.calls == 1
        assert result.media.data.coverage == 'full'
        assert result.media.data.toolchain['method'] == 'safe-http'
        assert result.stats['bytes'] == len(payload)
        with pytest.raises(MaterialError, match='无法识别'):
            fetch.fetch_public_file(store, source=source, url='https://example.com/x.bin',
                                    http=_HTTP(b'not a media file'))
        with pytest.raises(MaterialError, match='预算') as failure:
            fetch.fetch_public_file(store, source=source, url='https://example.com/video.mkv',
                                    http=_HTTP(MaterialError('resource-limit', '源文件超过下载预算', stage='fetch')))
        assert failure.value.code == 'resource-limit'
        assert not store.documents('material.media')[1:]  # 失败不发布第二个媒体


class _Worker:
    def __init__(self, directory_writer, metadata=None, files=None):
        self.writer = directory_writer
        self.metadata = metadata or {}
        self.files = files or []

    def __call__(self, request, *, timeout_s):
        directory = Path(request['directory'])
        self.writer(directory)
        return {'mode': 'download', 'metadata': self.metadata,
                'files': [{'path': item.name, 'bytes': item.stat().st_size, 'kind': 'media' if item.suffix != '.vtt' else 'subtitle'}
                          for item in sorted(directory.iterdir())],
                'warnings': [], 'stats': {'bytes': 1, 'requests': 1}, 'toolchain': {}}


@pytest.mark.media
def test_platform_split_tracks_merge_but_never_invent_source_range(tmp_path):
    video, audio = tmp_path / 'v.mkv', tmp_path / 'a.mka'
    _clip(video, audio=False)
    subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-nostdin', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', 'sine=frequency=440:sample_rate=48000:duration=2', '-c:a', 'pcm_s16le', str(audio)],
                   check=True, capture_output=True, timeout=30)
    payload = {'video': video.read_bytes(), 'audio': audio.read_bytes(),
               'subs': 'WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n平台字幕\n'.encode('utf-8')}

    def writer(directory):
        (directory / 'media-000001.mkv').write_bytes(payload['video'])
        (directory / 'media-000002.mka').write_bytes(payload['audio'])
        (directory / 'media-000003.zh-Hans.vtt').write_bytes(payload['subs'])

    worker = _Worker(writer, metadata={'title': '平台条目', 'duration': 2,
                                       'chapters': [{'startSeconds': 0, 'endSeconds': 2, 'title': '第一章'}],
                                       'subtitles': {'manual': ['zh-Hans'], 'automatic': []}})
    with MaterialStore(tmp_path / 'library') as store:
        source = _source('youtube')
        store.put(source)
        result = fetch.fetch_platform(store, source=source, url='https://www.youtube.com/watch?v=abc12345678',
                                      worker=worker)
        data = result.media.data
        assert data.coverage == 'unknown' and data.upstreamFullSha256 is None
        assert data.probe.timeline.sourceMapping.status == 'unknown'
        assert data.probe.timeline.source_range(TimeRange(startUs=0, endUs=500_000)) is None
        assert data.probe.hasAudio and data.probe.kind == 'video'
        assert [chapter.title for chapter in data.chapters] == ['第一章']
        assert [(track.origin, track.language) for track in data.captions] == [('manual', 'zh-Hans')]
        assert any('unknown' in note for note in result.warnings)


@pytest.mark.media
def test_platform_rejects_drm_live_and_unverified_outputs(tmp_path):
    video = _clip(tmp_path / 'v.mkv', audio=False)
    payload = video.read_bytes()

    def writer(directory):
        (directory / 'media-000001.mkv').write_bytes(payload)

    with MaterialStore(tmp_path / 'library') as store:
        source = _source('bilibili')
        store.put(source)
        for metadata in ({'has_drm': True}, {'live_status': 'is_live'}):
            with pytest.raises(MaterialError) as failure:
                fetch.fetch_platform(store, source=source, url='https://www.bilibili.com/video/BV1xx411c7mD',
                                     worker=_Worker(writer, metadata))
            assert failure.value.code == 'unsupported-source'
        assert store.documents('material.media') == []


def test_fetch_budget_and_section_contract_are_strict():
    for values in ({'max_bytes': 0}, {'max_bytes': True}, {'max_duration_us': -1}, {'total_bytes': 10 ** 18}):
        with pytest.raises(MaterialError):
            fetch.FetchBudget(**values)
    with pytest.raises(MaterialError):
        fetch._range({'startUs': 5, 'endUs': 1}, None, allow_image=True)
    with pytest.raises(MaterialError):
        fetch._range(TimeRange(startUs=0, endUs=10), None, allow_image=False)


def test_local_source_requires_explicit_file_and_platform_unknown_source_is_rejected(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        source = _source()
        store.put(source)
        with pytest.raises(MaterialError, match='显式提供原文件'):
            fetch.fetch_source(store, source=source, locator=str(tmp_path / 'missing.mkv'))
        unknown = Source(id='source-x', data=SourceData(provider='unknown-provider', title='未知'))
        store.put(unknown)
        with pytest.raises(MaterialError) as failure:
            fetch.fetch_source(store, source=unknown, locator='https://example.com/x')
        assert failure.value.code == 'unsupported-source'
