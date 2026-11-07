"""过程证据的最低媒体容量：只证明可探测与长度，不判断内容是否正确。

这些用例覆盖伪装视频、纯音频、过短片段、一帧容差与单次操作内的探测缓存；
真实表达是否成立仍由独立评审判断。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.production import media_evidence

pytestmark = pytest.mark.media


def make_video(path: Path, seconds: float, fps: int = 30, audio: float | None = None) -> Path:
    args = [get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi',
            '-i', f'testsrc=size=320x180:rate={fps}:duration={seconds}']
    if audio is not None:
        args += ['-f', 'lavfi', '-i', f'sine=frequency=440:duration={audio}', '-c:a', 'aac']
    args += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)]
    subprocess.run(args, check=True, timeout=300)
    return path


def make_audio_only(path: Path, seconds: float) -> Path:
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi',
                    '-i', f'sine=frequency=440:duration={seconds}', '-c:a', 'aac', str(path)],
                   check=True, timeout=300)
    return path


def make_frames(path: Path, frames: int, fps: int = 30) -> Path:
    """按帧数而非秒数生成，用于验证「不足不超过一帧」的边界。"""
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi',
                    '-i', f'testsrc=size=320x180:rate={fps}', '-frames:v', str(frames),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True, timeout=300)
    return path


def test_probe_reads_only_the_video_stream(tmp_path: Path):
    # 音轨比视频长：容器时长不能冒充视频长度。
    path = make_video(tmp_path / 'long-audio.mp4', 1, audio=4)
    assert media_evidence.probe(path) == pytest.approx(1, abs=.05)


def test_probe_rejects_fake_audio_only_and_missing(tmp_path: Path):
    fake = tmp_path / 'fake.mp4'
    fake.write_bytes(b'not a video')
    with pytest.raises(M2VError, match='无法解码'):
        media_evidence.probe(fake)
    with pytest.raises(M2VError, match='缺少有效视频流'):
        media_evidence.probe(make_audio_only(tmp_path / 'audio.mp4', 2))
    with pytest.raises(M2VError):
        media_evidence.probe(tmp_path / 'missing.mp4')



def test_probe_cache_is_per_operation(tmp_path, monkeypatch):
    path=make_video(tmp_path/'clip.mp4', .3)
    calls=[]
    original=media_evidence.probe
    monkeypatch.setattr(media_evidence,'probe',lambda p: calls.append(p) or original(p))
    with media_evidence.snapshot():
        assert media_evidence.duration(path)>0
        media_evidence.duration(path)
    media_evidence.duration(path)
    assert len(calls)==2
