"""音频解码与合成。PCM/WAV 用流式文件处理，避免长视频常驻内存。"""
from __future__ import annotations

import subprocess
import json
import math
import shutil
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError

SAMPLE_RATE = 24000


@dataclass(frozen=True)
class Effect:
    path: Path
    start: float
    gain_db: float
    trim_start: float
    duration: float
    loop: bool = False
    fade_in: float = 0.
    fade_out: float = 0.
    pan: float | None = None


def loudness(path: Path) -> dict:
    try:
        result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path), "-af",
            "loudnorm=I=-16:TP=-1:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise M2VError("音频响度量测超时（300 秒）") from exc
    if result.returncode: raise M2VError("无法量测音频响度")
    text = result.stderr.decode("utf-8", "replace")
    try: return json.loads(text[text.rfind("{"):text.rfind("}") + 1])
    except ValueError as exc: raise M2VError("响度量测未返回有效数据") from exc


def normalize(source: Path, target: Path, integrated: float = -16.0,
              true_peak: float = -1.0) -> None:
    """两遍 loudnorm；旁白默认 −16 LUFS，统一成片母版用 −14 LUFS。"""
    stats = loudness(source)
    if not math.isfinite(float(stats["input_i"])):
        shutil.copyfile(source, target); return
    options = ":".join(f"{key}={stats[value]}" for key, value in {
        "measured_I": "input_i", "measured_TP": "input_tp", "measured_LRA": "input_lra",
        "measured_thresh": "input_thresh", "offset": "target_offset"}.items())
    ffmpeg(["-i", str(source), "-af",
            f"loudnorm=I={integrated}:TP={true_peak}:LRA=11:{options}:linear=true",
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(target)])


def master(source: Path, target: Path, integrated: float = -14.0, true_peak: float = -1.0) -> None:
    """成片响度归一：动态 loudnorm 同时控制响度与真峰值。

    只做线性增益时，峰值余量不足会把目标响度顶住（实测 −15.2 而不是 −14）；
    动态模式用同一组参数做温和压缩，才能同时满足响度与真峰值上限。
    """
    # 温和压缩先收峰值，再让 loudnorm 有增益余量；只靠 loudnorm 实测停在 −15.3。
    ffmpeg(["-i", str(source), "-af",
            f"acompressor=threshold=-20dB:ratio=2:attack=5:release=150,"
            f"loudnorm=I={integrated}:TP={true_peak}:LRA=9",
            "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", str(target)])


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
        music: tuple[Path, dict] | None, effects: list[Effect], work: Path) -> None:
    normalize(narration, work / "normalized.wav")
    args = ["-i", str(work / "normalized.wav")]
    filters = ["[0:a]aformat=channel_layouts=stereo[voice]"]
    labels = ["[voice]"]; index = 1
    if music:
        path, settings = music
        if settings.get("loop", False): args += ["-stream_loop", "-1"]
        args += ["-i", str(path)]; music_index = index; index += 1
        duck_envelope(cues, duration, work / "duck.wav")
        args += ["-i", str(work / "duck.wav")]; envelope_index = index; index += 1
        fade_in = min(duration, settings.get("fadeInMs", 500) / 1000)
        fade_out = min(duration, settings.get("fadeOutMs", 500) / 1000)
        effect = f"aresample={SAMPLE_RATE},aformat=channel_layouts=stereo,atrim=duration={duration},apad=whole_dur={duration},volume={settings.get('gainDb', -24)}dB"
        if fade_in: effect += f",afade=t=in:d={fade_in}"
        if fade_out: effect += f",afade=t=out:st={duration-fade_out}:d={fade_out}"
        filters += [f"[{music_index}:a]{effect}[music]",
                    f"[{envelope_index}:a]pan=stereo|c0=c0|c1=c0[duck]", "[music][duck]amultiply[bed]"]
        labels.append("[bed]")
    for effect in effects:
        args += ["-i", str(effect.path)]
        chain = [f"aresample={SAMPLE_RATE}", f"atrim=start={effect.trim_start}", "asetpts=PTS-STARTPTS"]
        if effect.loop:
            # 重复已裁掉入点的素材；size 按实际剩余样本数计算，避免回到原文件起点。
            with wave.open(str(effect.path), "rb") as stream:
                size = stream.getnframes() - round(effect.trim_start*SAMPLE_RATE)
            chain.append(f"aloop=loop=-1:size={size}")
        chain += [f"atrim=duration={effect.duration}", "asetpts=PTS-STARTPTS"]
        if effect.pan is None:
            chain.append("aformat=channel_layouts=stereo")
        else:
            angle = (effect.pan + 1) * math.pi / 4
            chain += ["aformat=channel_layouts=mono",
                      f"pan=stereo|c0={math.cos(angle):.9f}*c0|c1={math.sin(angle):.9f}*c0"]
        if effect.fade_in:
            chain.append(f"afade=t=in:d={effect.fade_in}")
        if effect.fade_out:
            chain.append(f"afade=t=out:st={effect.duration-effect.fade_out}:d={effect.fade_out}")
        chain += [f"volume={effect.gain_db}dB", f"adelay={round(effect.start*SAMPLE_RATE)}S:all=1"]
        filters.append(f"[{index}:a]" + ",".join(chain) + f"[fx{index}]")
        labels.append(f"[fx{index}]"); index += 1
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,alimiter=limit=0.794328:level=false:latency=true,atrim=duration={duration},apad=whole_dur={duration}[out]")
    ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", str(target)])


def ffmpeg(args: list[str]) -> None:
    try:
        result = subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", *args],
                                capture_output=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise M2VError("音频处理超时（300 秒）") from exc
    if result.returncode:
        raise M2VError("音频处理失败: " + result.stderr.decode("utf-8", "replace")[-1500:])


def decode(source: Path, target: Path) -> float:
    ffmpeg(["-i", str(source), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-c:a", "pcm_s16le", str(target)])
    return wav_duration(target)


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2 or stream.getframerate() != SAMPLE_RATE:
                raise M2VError(f"音轨格式错误: {path}")
            frames = stream.getnframes()
            # 实际读取确认文件没有截断，不能只相信 WAV 头。
            count = 0
            while block := stream.readframes(SAMPLE_RATE):
                count += len(block) // 2
            if frames <= 0 or count != frames:
                raise M2VError(f"音轨为空或不完整: {path}")
            return frames / SAMPLE_RATE
    except (wave.Error, EOFError, OSError) as exc:
        raise M2VError(f"无法读取音轨 {path}: {exc}") from exc


def concatenate(parts: list[tuple[Path | None, int]], fps: int, output: Path,
                fades: list[tuple[int, int]] | None = None) -> None:
    """按帧边界把逐段配音拼成一条轨；`fades` 给出每段首尾共享画面淡化进度的帧数。

    不给 `fades` 时整段原样写入（逐幕音轨的既有行为）。
    给了就按段内的槽位位置线性淡入淡出：单条母版轨没有逐场景音轨可以 afade，
    淡化只能在拼接时施加，否则交叉淡化处的声音会硬切。
    """
    with wave.open(str(output), "wb") as dest:
        dest.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        cursor, written = 0, 0
        for index, (path, frames) in enumerate(parts):
            cursor += frames
            end_sample = round(cursor * SAMPLE_RATE / fps)
            slot_start, slot_end = written, end_sample
            fade_in_frames, fade_out_frames = (fades[index] if fades else (0, 0))
            slot_frames = max(end_sample - slot_start, 0)
            fade_in = min(round(fade_in_frames * SAMPLE_RATE / fps), slot_frames)
            fade_out = min(round(fade_out_frames * SAMPLE_RATE / fps), slot_frames - fade_in)
            if path:
                with wave.open(str(path), "rb") as source:
                    while block := source.readframes(SAMPLE_RATE):
                        if fade_in or fade_out:
                            block = _fade_block(block, written, fade_in, fade_out, slot_start, slot_end)
                        dest.writeframesraw(block)
                        written += len(block) // 2
            if written > end_sample:
                raise M2VError("配音超出场景，拒绝截断")
            while written < end_sample:
                size = min(SAMPLE_RATE, end_sample - written)
                dest.writeframesraw(b"\0\0" * size)
                written += size


def _fade_block(block: bytes, first_sample: int, fade_in: int, fade_out: int,
                slot_start: int, slot_end: int) -> bytes:
    """按槽位内的采样位置给一块 PCM 施加线性淡入淡出。"""
    samples = list(struct.unpack(f"<{len(block) // 2}h", block))
    for offset, value in enumerate(samples):
        position = first_sample + offset
        gain = 1.0
        if fade_in:
            gain = min(gain, (position - slot_start) / fade_in)
        if fade_out:
            gain = min(gain, (slot_end - position) / fade_out)
        if gain < 1.0:
            samples[offset] = round(value * max(gain, 0.0))
    return struct.pack(f"<{len(samples)}h", *samples)


def mux(video: Path, audio: Path, output: Path, duration: float, start: float = 0) -> None:
    """把无声画面与配音合成为最终成片。

    音频统一转成 44.1kHz 立体声 AAC-LC：旁白输入是单声道，声音设计母版保留立体声；24kHz 单声道
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
    raise M2VError("AAC 真峰值仍高于 −1 dBTP，拒绝交付")
