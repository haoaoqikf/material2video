"""方案C原创柔质触感声；无采样、无旋律，24kHz PCM16，CC0-1.0。

旧synthesize配方保持原样，新资产用mint-身份防止覆盖历史摘要。
"""
import math
from pathlib import Path
import struct
import wave

RATE = 24000
DURATIONS = {'mint-bed': 29.0, 'mint-contact': .16, 'mint-grow': .34,
             'mint-return': .28, 'mint-reveal': .6, 'mint-close': .38}


def _noise(index: int) -> float:
    value = (index * 747796405 + 2891336453) & 0xFFFFFFFF
    value = (((value >> ((value >> 28) + 4)) ^ value) * 277803737) & 0xFFFFFFFF
    value = (value >> 22) ^ value
    return value / 2147483648 - 1


def generate(identity: str, target: Path) -> None:
    seconds = DURATIONS[identity]
    count = round(seconds * RATE)
    values = []
    low = 0.0
    for index in range(count):
        t = index / RATE
        noise = _noise(index + 71)
        low = low * .92 + noise * .08
        if identity == 'mint-bed':
            envelope = min(1, max(0, (t - 8) / .8)) * min(1, max(0, 29 - t))
            value = (.88 * low + .03 * math.sin(2 * math.pi * 47.3 * t)) * envelope if t >= 8 else 0.0
        else:
            attack = min(1, t / .004)
            release = min(1, max(0, (seconds - t) / .04))
            if identity == 'mint-contact':
                value = (.52 * math.sin(2 * math.pi * 143 * t) * math.exp(-t * 35)
                         + .35 * low * math.exp(-t * 45) + .13 * noise * math.exp(-t * 90))
            elif identity == 'mint-grow':
                value = (low * .9 + .1 * noise) * math.sin(math.pi * t / seconds) ** 2
            elif identity == 'mint-return':
                value = low * math.sin(math.pi * t / seconds) ** 2 * (1 - t / seconds)
            elif identity == 'mint-reveal':
                value = (.8 * low + .2 * math.sin(2 * math.pi * 71.3 * t)) * math.exp(-t * 8)
            else:
                value = (.65 * low + .35 * math.sin(2 * math.pi * 117.7 * t)) * math.exp(-t * 12)
            value *= attack * release
        values.append(value)
    peak = max(map(abs, values)) or 1
    level = -19 if identity == 'mint-bed' else -10
    scale = 10 ** (level / 20) / peak
    with wave.open(str(target), 'wb') as out:
        out.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        out.writeframes(b''.join(struct.pack('<h', round(value * scale * 32767)) for value in values))
