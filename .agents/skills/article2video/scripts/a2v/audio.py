"""音频解码与合成。PCM/WAV 用流式文件处理，避免长视频常驻内存。"""
from __future__ import annotations

import subprocess
import json
import math
import shutil
import struct
import wave
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .errors import A2VError

SAMPLE_RATE = 24000


def concatenate_samples(parts: list[tuple[Path | None, int]], output: Path) -> None:
    """按精确样本数拼接，不把毫秒停顿取整为视频帧。"""
    with wave.open(str(output), "wb") as dest:
        dest.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        for path, samples in parts:
            written = 0
            if path:
                with wave.open(str(path), "rb") as source:
                    while block := source.readframes(SAMPLE_RATE):
                        dest.writeframesraw(block); written += len(block) // 2
            if written > samples: raise A2VError("段音频超出样本预算")
            while written < samples:
                size = min(SAMPLE_RATE, samples - written)
                dest.writeframesraw(b"\0\0" * size); written += size


def loudness(path: Path) -> dict:
    try:
        result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path), "-af",
            "loudnorm=I=-16:TP=-1:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise A2VError("音频响度量测超时（300 秒）") from exc
    if result.returncode: raise A2VError("无法量测音频响度")
    text = result.stderr.decode("utf-8", "replace")
    try: return json.loads(text[text.rfind("{"):text.rfind("}") + 1])
    except ValueError as exc: raise A2VError("响度量测未返回有效数据") from exc


def normalize(source: Path, target: Path) -> None:
    stats = loudness(source)
    if not math.isfinite(float(stats["input_i"])):
        shutil.copyfile(source, target); return
    options = ":".join(f"{key}={stats[value]}" for key, value in {
        "measured_I": "input_i", "measured_TP": "input_tp", "measured_LRA": "input_lra",
        "measured_thresh": "input_thresh", "offset": "target_offset"}.items())
    ffmpeg(["-i", str(source), "-af", f"loudnorm=I=-16:TP=-1:LRA=11:{options}:linear=true",
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(target)])


def duck_envelope(cues: list[dict], duration: float, target: Path) -> None:
    """包络由字幕讲话区间生成。重叠攻击/释放合并，整片 PCM 不驻内存。"""
    spans = []
    for cue in cues:
        start, end = max(0., cue["start"] - .08), cue["end"] + .25
        if spans and start <= spans[-1][1]: spans[-1] = (spans[-1][0], max(end, spans[-1][1]))
        else: spans.append((start, end))
    index = 0; low = 10 ** (-10 / 20)
    with wave.open(str(target), "wb") as dest:
        dest.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        count = round(duration * SAMPLE_RATE)
        for offset in range(0, count, SAMPLE_RATE):
            block = bytearray()
            for sample in range(offset, min(count, offset + SAMPLE_RATE)):
                t = sample / SAMPLE_RATE
                while index < len(spans) and t >= spans[index][1]: index += 1
                gain = 1.
                if index < len(spans):
                    a, b = spans[index]
                    if a <= t < b:
                        attack = min(1., (t - a) / .08); release = min(1., (b - t) / .25)
                        gain = 1 - (1 - low) * min(attack, release)
                block.extend(struct.pack("<h", round(gain * 32767)))
            dest.writeframesraw(block)


def mix(narration: Path, target: Path, duration: float, cues: list[dict],
        music: tuple[Path, dict] | None, effects: list[tuple[Path, float, float]], work: Path) -> None:
    normalize(narration, work / "normalized.wav")
    args = ["-i", str(work / "normalized.wav")]; filters = []; labels = ["[0:a]"]; index = 1
    if music:
        path, settings = music
        if settings.get("loop", False): args += ["-stream_loop", "-1"]
        args += ["-i", str(path)]; music_index = index; index += 1
        duck_envelope(cues, duration, work / "duck.wav")
        args += ["-i", str(work / "duck.wav")]; envelope_index = index; index += 1
        fade_in = min(duration, settings.get("fadeInMs", 500) / 1000)
        fade_out = min(duration, settings.get("fadeOutMs", 500) / 1000)
        effect = f"aresample={SAMPLE_RATE},aformat=channel_layouts=mono,atrim=duration={duration},apad=whole_dur={duration},volume={settings.get('gainDb', -24)}dB"
        if fade_in: effect += f",afade=t=in:d={fade_in}"
        if fade_out: effect += f",afade=t=out:st={duration-fade_out}:d={fade_out}"
        filters += [f"[{music_index}:a]{effect}[music]", f"[music][{envelope_index}:a]amultiply[bed]"]
        labels.append("[bed]")
    for path, start, gain in effects:
        args += ["-i", str(path)]
        filters.append(f"[{index}:a]aresample={SAMPLE_RATE},aformat=channel_layouts=mono,volume={gain}dB,adelay={round(start * SAMPLE_RATE)}S:all=1[fx{index}]")
        labels.append(f"[fx{index}]"); index += 1
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,alimiter=limit=0.794328:level=false:latency=true,atrim=duration={duration},apad=whole_dur={duration}[out]")
    ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(target)])


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


def mux(video: Path, audio: Path, output: Path, duration: float, start: float = 0) -> None:
    """把无声画面与配音合成为最终成片。

    音频统一转成 44.1kHz 立体声 AAC-LC：配音本身是 24kHz 单声道，但 24kHz 单声道
    AAC 在部分播放器（Windows Media Foundation 实测）里会被直接拒绝打开，
    而 44.1kHz 立体声是兼容性最好、各平台都默认支持的组合。
    画面用 -c:v copy 原样复制，不做二次编码。
    """
    gain = 0.
    for attempt in range(3):
        ffmpeg(["-i", str(video), "-ss", str(start), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "128k",
                "-ar", "44100", "-ac", "2", "-af", f"volume={gain}dB",
                "-t", str(duration), "-movflags", "+faststart", str(output)])
        peak = float(loudness(output)["input_tp"])
        if peak <= -1: return
        gain -= peak + 1.2
    raise A2VError("AAC 真峰值仍高于 −1 dBTP，拒绝交付")
