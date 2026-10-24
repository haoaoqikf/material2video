"""生成五种选择剪纸版音乐与动作音效；原创合成，无第三方采样，按 CC0 1.0 发布。"""
import math
import struct
import argparse
import tempfile
import wave
from pathlib import Path

RATE = 24000
HERE = Path(__file__).parent


def write(name: str, seconds: float, signal, output_root: Path) -> Path:
    target = output_root / name
    count = round(seconds * RATE)
    with wave.open(str(target), "wb") as out:
        out.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        for start in range(0, count, RATE):
            data = bytearray()
            for index in range(start, min(start + RATE, count)):
                t = index / RATE
                value = max(-1.0, min(1.0, signal(t, index)))
                data.extend(struct.pack("<h", round(value * 32767)))
            out.writeframes(data)
    return target


def music(t: float, _index: int) -> float:
    # 96 BPM, pentatonic plucks and a quiet warm bed; the final second fades cleanly.
    beat = 60 / 96
    notes = (261.63, 329.63, 392.0, 493.88, 392.0, 329.63, 293.66, 392.0)
    step = int(t / (beat / 2))
    local = (t % (beat / 2)) / (beat / 2)
    f = notes[step % len(notes)]
    pluck = math.exp(-local * 5) * math.sin(2 * math.pi * f * t)
    bed = 0.35 * math.sin(2 * math.pi * 130.81 * t) + 0.22 * math.sin(2 * math.pi * 196 * t)
    pulse = 0.12 * math.sin(2 * math.pi * 65.4 * t) * math.exp(-((t % beat) / beat) * 4)
    fade = min(1, t / 0.45, max(0, (30 - t) / 0.8))
    return fade * (0.22 * pluck + 0.10 * bed + pulse)


def chime(t: float, _index: int) -> float:
    env = math.exp(-t * 5) * min(1, t / 0.012)
    return env * (0.46 * math.sin(2 * math.pi * 784 * t) + 0.19 * math.sin(2 * math.pi * 1175 * t))


def join(t: float, _index: int) -> float:
    env = math.exp(-t * 9) * min(1, t / 0.01)
    return env * (0.38 * math.sin(2 * math.pi * (190 - 80 * t) * t) + 0.22 * math.sin(2 * math.pi * 620 * t))


def page(t: float, index: int) -> float:
    # A deterministic soft paper-like noise burst, never random between builds.
    state = (index * 1664525 + 1013904223) & 0xFFFFFFFF
    state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
    noise = (state / 0xFFFFFFFF) * 2 - 1
    env = math.sin(math.pi * min(1, t / 0.8)) ** 2
    return env * (0.15 * noise + 0.22 * math.sin(2 * math.pi * (340 + 300 * t) * t))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="显式替换已存在的音频文件")
    args = parser.parse_args()
    names = ("score.wav", "door.wav", "bridge.wav", "page.wav")
    existing = [HERE / name for name in names if (HERE / name).exists()]
    if existing and not args.force:
        raise FileExistsError(f"素材已存在；为避免覆盖请先备份，或显式传入 --force：{existing}")
    with tempfile.TemporaryDirectory(prefix="five-life-audio-", dir=HERE) as temp:
        staged = Path(temp)
        outputs = (write("score.wav", 30, music, staged),
                   write("door.wav", 0.8, chime, staged),
                   write("bridge.wav", 0.55, join, staged),
                   write("page.wav", 0.8, page, staged))
        for source in outputs:
            destination = HERE / source.name
            source.replace(destination)
            print(destination)
