"""工作媒体的实测时基与本地解码边界；只对相关节点运行 FFmpeg。"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image
import pytest
from pydantic import ValidationError

from m2v.materials import media
from m2v.materials.contracts import Artifact, MediaData, TimeBase, TimeRange
from m2v.materials.errors import MaterialError


def test_integer_microseconds_preserve_pts_without_fps_approximation():
    assert media.seconds_us('1.000001') == 1_000_001
    assert media.seconds_us('-0.000001') == -1
    assert media.pts_us(10_000, TimeBase(num=1, den=30_000)) == 333_333
    assert media.pts_us(-1, TimeBase(num=1001, den=30_000)) == -33_367
    for invalid in (True, 'NaN', 'Infinity', 'not-a-time'):
        with pytest.raises(MaterialError):
            media.seconds_us(invalid)
    with pytest.raises(MaterialError):
        media.pts_us(True, TimeBase(num=1, den=1000))


def test_image_has_no_time_window_and_unknown_mapping(tmp_path):
    path = tmp_path / 'image-without-extension'
    Image.new('RGB', (96, 64), color='navy').save(path, format='PNG')
    result = media.probe(path, full_source=True)
    assert (result.kind, result.width, result.height) == ('image', 96, 64)
    assert result.durationUs is None and result.timeline.source_range(None) is None
    with pytest.raises(MaterialError, match='像素预算'):
        media.probe(path, max_pixels=10)


def _video(path: Path, *, offset=False, vfr=False, audio=True):
    arguments = ['-f', 'lavfi', '-i', 'testsrc2=size=96x64:rate=12:duration=2']
    if audio:
        arguments += ['-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=2']
    if vfr:
        # 前 6 帧间隔 1/12s，其后 18 帧间隔 1/6s；名义帧率不能推回 PTS。
        arguments += ['-vf', r'setpts=if(lt(N\,6)\,N/(12*TB)\,(0.5+(N-6)/6)/TB)']
    elif offset:
        arguments += ['-vf', 'setpts=PTS+2/TB']
        if audio:
            arguments += ['-af', 'asetpts=PTS+2/TB']
    arguments += ['-fps_mode', 'passthrough', '-c:v', 'ffv1']
    if audio:
        arguments += ['-c:a', 'pcm_s16le']
    process = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-nostdin', '-loglevel', 'error',
                              *arguments, str(path)], capture_output=True, timeout=30)
    assert process.returncode == 0, process.stderr.decode('utf-8', 'replace')
    return path


@pytest.mark.media
def test_toolchain_records_both_real_tools_without_mutable_cache_poisoning():
    identity = media.toolchain()
    assert identity['ffmpeg'].startswith('ffmpeg version') and identity['ffprobe'].startswith('ffprobe version')
    identity['ffmpeg'] = 'forged'
    assert media.toolchain()['ffmpeg'] != 'forged'


@pytest.mark.media
def test_nonzero_video_pts_and_full_source_mapping_are_distinct(tmp_path):
    path = _video(tmp_path / 'nonzero.mkv', offset=True)
    result = media.probe(path, full_source=True)
    assert result.videoStartUs == 2_000_000
    assert result.audioStartUs == 2_000_000 and result.hasAudio
    assert result.durationUs == 2_000_000
    assert result.timeline.localOriginPts is not None
    assert media.pts_us(result.timeline.localOriginPts, result.timeline.timeBase) == 2_000_000
    local = TimeRange(startUs=250_000, endUs=1_500_000)
    assert result.timeline.source_range(local) == local
    assert result.timeline.sourceMapping.status == 'verified'


@pytest.mark.media
def test_vfr_keeps_real_time_base_and_does_not_invent_source_mapping(tmp_path):
    path = _video(tmp_path / 'vfr.mkv', vfr=True, audio=False)
    result = media.probe(path)
    assert not result.hasAudio and result.durationUs > 3_000_000
    truth = subprocess.run([media.ffprobe_exe(), '-v', 'error', '-select_streams', 'v:0',
                            '-show_frames', '-show_entries', 'frame=best_effort_timestamp',
                            '-of', 'json', str(path)], capture_output=True, timeout=30, check=True)
    pts = [int(item['best_effort_timestamp']) for item in json.loads(truth.stdout)['frames']]
    times = [media.pts_us(value, result.timeline.timeBase) for value in pts]
    assert len({round((right-left) / 1000) for left, right in zip(times, times[1:])}) >= 2
    nominal_us = round(23 * 1_000_000 * result.fps.den / result.fps.num)
    assert times[-1] - times[0] > nominal_us
    assert result.timeline.source_range(TimeRange(startUs=0, endUs=500_000)) is None
    assert result.timeline.sourceMapping.status == 'unknown'

    actual_sha = sha256(path.read_bytes()).hexdigest()
    data = dict(sourceId='source', artifact=Artifact(path='objects/fragment', sha256=actual_sha, bytes=path.stat().st_size),
                probe=result, coverage='section', fetchIdentity='a' * 64)
    assert MediaData(**data).upstreamFullSha256 is None
    with pytest.raises(ValidationError, match='未取得整片'):
        MediaData(**data, upstreamFullSha256=actual_sha)


@pytest.mark.media
def test_audio_only_and_dangerous_playlist_are_not_confused(tmp_path):
    audio = tmp_path / 'audio.wav'
    process = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-nostdin', '-loglevel', 'error',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=0.5', str(audio)],
        capture_output=True, timeout=30)
    assert process.returncode == 0, process.stderr.decode('utf-8', 'replace')
    result = media.probe(audio)
    assert result.kind == 'audio' and result.width is None and result.durationUs == 500_000
    assert result.hasAudio and result.sampleRate == 48_000

    playlist = tmp_path / 'hidden-playlist'
    playlist.write_text('#EXTM3U\n#EXTINF:10,\nhttp://127.0.0.1/private\n', encoding='utf-8')
    with pytest.raises(MaterialError) as error:
        media.probe(playlist)
    assert error.value.code == 'media-invalid'
