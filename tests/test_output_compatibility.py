"""成片码流兼容性测试。

背景：JPEG 中间帧带的是全范围色彩，直接进 libx264 会产出 yuvj420p(pc) 的流。
ffmpeg 自己解码完全正常，但 Windows 的 Media Foundation 会以 0xc00d36c4
拒绝打开整个文件——也就是「渲染成功、验收通过，用户却打不开」。
因此这里锁定住两条对外契约：

1. 画面必须是 yuv420p(tv, bt709)，不能是全范围；
2. 配音必须是 44.1kHz 立体声 AAC-LC。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from a2v import audio
from a2v.encoder import VideoEncoder
from a2v.render import RenderError, _verify_output, _verify_playback_compatibility
from conftest import make_jpeg, write_tone


def stream_info(path: Path) -> str:
    """返回 ffmpeg 打印的输入信息，用作断言依据。"""
    completed = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stderr


def test_encoded_video_uses_tv_range_bt709(tmp_path: Path) -> None:
    """编码器必须把 JPEG 帧转成 yuv420p(tv, bt709)，而不是 yuvj420p(pc)。"""
    jpeg = make_jpeg()
    output = tmp_path / "video.mp4"
    with VideoEncoder(output, fps=30) as encoder:
        for _ in range(6):
            encoder.write(jpeg)

    info = stream_info(output)
    assert "yuv420p(tv, bt709" in info
    assert "yuvj420p" not in info
    assert "(pc," not in info
    _verify_playback_compatibility(output)


def test_playback_compatibility_rejects_full_range(tmp_path: Path) -> None:
    """全范围像素格式必须在验收阶段被拦下，而不是留给用户去发现。"""
    jpeg = make_jpeg()
    source = tmp_path / "source.mp4"
    with VideoEncoder(source, fps=30) as encoder:
        for _ in range(3):
            encoder.write(jpeg)

    # 再编码一遍并故意去掉色彩转换，复现出全范围码流
    legacy = tmp_path / "legacy.mp4"
    subprocess.run(
        [
            get_ffmpeg_exe(), "-y", "-v", "error",
            "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", "30", "-i", "-",
            "-c:v", "libx264", "-pix_fmt", "yuvj420p", "-crf", "18", str(legacy),
        ],
        input=jpeg * 3,
        check=True,
    )
    assert "yuvj420p" in stream_info(legacy)
    try:
        _verify_playback_compatibility(legacy)
    except RenderError as exc:
        assert "全范围" in str(exc)
    else:  # pragma: no cover - 只有 libx264 不再接受 yuvj420p 时才会走到
        raise AssertionError("全范围码流没有被拦下")


def test_muxed_audio_is_stereo_44k_aac(tmp_path: Path) -> None:
    """合成后的配音必须是 44.1kHz 立体声 AAC-LC，这是各平台兼容性最好的组合。"""
    jpeg = make_jpeg()
    video = tmp_path / "video.mp4"
    with VideoEncoder(video, fps=30) as encoder:
        for _ in range(30):
            encoder.write(jpeg)

    tone = tmp_path / "tone.wav"
    write_tone(tone, 1.0)
    output = tmp_path / "voiced.mp4"
    audio.mux(video, tone, output, 1.0)

    info = stream_info(output)
    assert "aac (LC)" in info
    assert "44100 Hz, stereo" in info
    assert "24000 Hz, mono" not in info
    _verify_output(output, 30, 64, 96, 30, expect_audio=True)
