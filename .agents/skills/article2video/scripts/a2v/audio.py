"""音频解码与合成。PCM/WAV 用流式文件处理，避免长视频常驻内存。"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .errors import A2VError

SAMPLE_RATE = 24000


def ffmpeg(args: list[str]) -> None:
    try:
        result = subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", *args],
                                capture_output=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise A2VError("音频处理超时（300 秒）") from exc
    if result.returncode:
        raise A2VError("音频处理失败: " + result.stderr.decode("utf-8", "replace")[-1500:])


def decode(source: Path, target: Path) -> float:
    ffmpeg(["-i", str(source), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-c:a", "pcm_s16le", str(target)])
    return wav_duration(target)


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2 or stream.getframerate() != SAMPLE_RATE:
                raise A2VError(f"音轨格式错误: {path}")
            frames = stream.getnframes()
            # 实际读取确认文件没有截断，不能只相信 WAV 头。
            count = 0
            while block := stream.readframes(SAMPLE_RATE):
                count += len(block) // 2
            if frames <= 0 or count != frames:
                raise A2VError(f"音轨为空或不完整: {path}")
            return frames / SAMPLE_RATE
    except (wave.Error, EOFError, OSError) as exc:
        raise A2VError(f"无法读取音轨 {path}: {exc}") from exc


def concatenate(parts: list[tuple[Path | None, int]], fps: int, output: Path) -> None:
    with wave.open(str(output), "wb") as dest:
        dest.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        cursor, written = 0, 0
        for path, frames in parts:
            cursor += frames
            end_sample = round(cursor * SAMPLE_RATE / fps)
            if path:
                with wave.open(str(path), "rb") as source:
                    while block := source.readframes(SAMPLE_RATE):
                        dest.writeframesraw(block)
                        written += len(block) // 2
            if written > end_sample:
                raise A2VError("配音超出场景，拒绝截断")
            while written < end_sample:
                size = min(SAMPLE_RATE, end_sample - written)
                dest.writeframesraw(b"\0\0" * size)
                written += size


def mux(video: Path, audio: Path, output: Path, duration: float) -> None:
    """把无声画面与配音合成为最终成片。

    音频统一转成 44.1kHz 立体声 AAC-LC：配音本身是 24kHz 单声道，但 24kHz 单声道
    AAC 在部分播放器（Windows Media Foundation 实测）里会被直接拒绝打开，
    而 44.1kHz 立体声是兼容性最好、各平台都默认支持的组合。
    画面用 -c:v copy 原样复制，不做二次编码。
    """
    ffmpeg(["-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "128k",
            "-ar", "44100", "-ac", "2",
            "-t", str(duration),
            "-movflags", "+faststart", str(output)])
