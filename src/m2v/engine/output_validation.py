"""Shared MP4 decoding, stream, and output-shape validation."""
from __future__ import annotations

import subprocess
import tempfile
import re
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe, read_frames

from m2v.core.errors import M2VError


def _decoded_frame_count(progress: str) -> int | None:
    matches = re.findall(r"(?m)^frame=(\d+)$", progress)
    return int(matches[-1]) if matches else None


def verify_output(output: Path, expected_frames: int, width: int, height: int, fps: int,
                  expect_audio: bool = False, *, require_delivery_format: bool = True) -> None:
    if not output.is_file() or not output.stat().st_size:
        raise M2VError("ffmpeg 没有生成有效输出文件")
    decoded = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(output), "-map", "0:v:0",
                              "-f", "null", "-", "-progress", "pipe:1", "-nostats"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace")
    if decoded.returncode:
        raise M2VError(f"成片解码失败：{decoded.stderr[-1500:]}")
    actual_frames = _decoded_frame_count(decoded.stdout)
    if actual_frames != expected_frames:
        actual = actual_frames if actual_frames is not None else "不可用"
        raise M2VError(f"成片帧数不匹配：期望 {expected_frames}，实际 {actual}")
    reader = read_frames(str(output))
    try:
        metadata = next(reader)
    finally:
        reader.close()
    if tuple(metadata["size"]) != (width, height) or abs(metadata["fps"] - fps) > .01:
        raise M2VError("成片尺寸或帧率不匹配")
    if abs(metadata["duration"] - expected_frames / fps) > max(.1, 1 / fps):
        raise M2VError("成片时长不匹配")
    info = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(output)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    line = next((item for item in info.stderr.splitlines() if "Video:" in item and "Stream #" in item), "")
    if require_delivery_format and line and ("yuvj420p" in line or "(pc," in line or "yuv420p(" not in line):
        raise M2VError("成片像素格式不兼容常用播放器")
    if expect_audio:
        with tempfile.TemporaryFile() as pcm:
            result = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(output), "-map", "0:a:0",
                                     "-ac", "1", "-ar", "24000", "-f", "s16le", "-"],
                                    stdout=pcm, stderr=subprocess.PIPE, timeout=300)
            if result.returncode or abs(pcm.tell() / 48000 - expected_frames / fps) > .1:
                raise M2VError("成片音轨缺失、不可解码或音画时长不一致")
