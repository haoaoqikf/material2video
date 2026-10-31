"""确定性的程序化音床：30 秒无缝循环，频率取循环长度的整数分之一。

音床不依赖外部曲目授权；生成器版本、种子、循环长度与许可写入准备记录。
所有分量在 30 秒内完成整数周期，循环点不存在相位跳变，因此不会出现爆音。
"""
from __future__ import annotations

import hashlib
import math
import struct
import wave
from pathlib import Path

from m2v.engine import audio

GENERATOR = "m2v.road-trip-ambient"
VERSION = 1
DEFAULT_SEED = 318
LOOP_SECONDS = 30.0
LICENSE = "CC0-1.0（程序化生成，无外部素材）"
#: 基准频率与整数周期数；循环长度固定 30 秒，频率 = cycles / 30。
_TONES = (
    (72.0, 0.42, 1),   # 低频铺底
    (144.0, 0.20, 2),  # 八度
    (216.0, 0.10, 3),  # 五度泛音
    (0.10, 0.30, 1),   # 极慢呼吸
)


def _cycles(frequency: float) -> int:
    return max(1, round(frequency * LOOP_SECONDS))


def synthesize(target: Path, *, seed: int = DEFAULT_SEED) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    count = round(LOOP_SECONDS * audio.SAMPLE_RATE)
    phases = []
    for index, (frequency, _gain, _harmonic) in enumerate(_TONES):
        cycles = _cycles(frequency)
        phases.append((cycles, 2 * math.pi * ((seed * (index + 3)) % 97) / 97))
    samples = bytearray()
    for index in range(count):
        phase = 2 * math.pi * index / count
        value = 0.0
        for (frequency, gain, _harmonic), (cycles, offset) in zip(_TONES, phases):
            value += gain * math.sin(cycles * phase + offset)
        # 极慢的幅度呼吸同样整周期，避免循环点音量跳变。
        breath = 0.82 + 0.18 * math.sin(phases[-1][0] * phase)
        samples.extend(struct.pack("<h", round(max(-1.0, min(1.0, value * breath * 0.22)) * 32767)))
    with wave.open(str(target), "wb") as stream:
        stream.setparams((1, 2, audio.SAMPLE_RATE, 0, "NONE", "not compressed"))
        stream.writeframes(bytes(samples))
    return record(target, seed=seed)


def record(target: Path, *, seed: int = DEFAULT_SEED) -> dict:
    return {
        "generator": GENERATOR,
        "version": VERSION,
        "seed": seed,
        "loopSeconds": LOOP_SECONDS,
        "license": LICENSE,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }


def verify(path: Path) -> dict:
    duration = audio.wav_duration(path)
    if abs(duration - LOOP_SECONDS) > 1 / audio.SAMPLE_RATE:
        raise ValueError(f"音床长度 {duration:.3f} 秒，应为 {LOOP_SECONDS:.0f} 秒")
    return record(path)
