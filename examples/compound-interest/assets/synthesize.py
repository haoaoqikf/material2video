"""本例原创音效与环境床；24kHz PCM16 单声道，CC0-1.0，无随机采样。

颜色/事件对应：落片、第一笔金片、回吸与熔合、分屏左右、30 年金属流、回扣、结尾。
bed 的前 8 秒是数字静音，8.0 秒才淡入，29–30 秒淡出；这样既有 music 字段不需要起始偏移。
"""
import math
import struct
import wave
from pathlib import Path

RATE = 24000
DURATIONS = {
    'bed': 30.0,
    'drop1': .18, 'drop2': .18, 'drop3': .18,
    'slide': .35, 'float': .8, 'ding': .9,
    'suction': .7, 'fusion': .6,
    'tingLow': .9, 'tingHigh': .6,
    'thump': .4, 'tick': .2,
    'stream': 6.0, 'resonance': 1.2, 'chime': 1.4,
}
PEAK_DB = {
    'bed': -12,
    'drop1': -6, 'drop2': -6, 'drop3': -6,
    'slide': -8, 'float': -6, 'ding': -6,
    'suction': -8, 'fusion': -8,
    'tingLow': -6, 'tingHigh': -6,
    'thump': -8, 'tick': -8,
    'stream': -10, 'resonance': -8, 'chime': -10,
}


def _noise(seed: int) -> float:
    """确定性伪随机，返回 [-1, 1)。"""
    x = math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return (x - math.floor(x)) * 2 - 1


def _bell(t: float, freqs: tuple[float, ...], decay: float, attack: float = .006) -> float:
    envelope = min(1, t / attack) * math.exp(-t * decay)
    return sum(w * math.sin(2 * math.pi * f * t) for f, w in zip(freqs, (0.62, 0.26, 0.12))) * envelope


def _bed(n: int) -> list[float]:
    """低频持续纹理：几个非整数比低音 + 低通噪声 + 少量空气层，无节拍、无旋律。"""
    values = [0.0] * n
    low = 0.0
    for i in range(n):
        t = i / RATE
        if t < 8 or t >= 30:
            continue
        fade_in = min(1, (t - 8) / .8)
        fade_out = min(1, (30 - t) / 1.0)
        low = low * .90 + _noise(i) * .10
        value = (.35 * math.sin(2 * math.pi * 48 * t + .4 * math.sin(2 * math.pi * .031 * t))
                 + .22 * math.sin(2 * math.pi * 63.7 * t + .3 * math.sin(2 * math.pi * .023 * t))
                 + .14 * math.sin(2 * math.pi * 82.1 * t)
                 + .08 * math.sin(2 * math.pi * 109.3 * t)
                 + .16 * low
                 + .012 * math.sin(2 * math.pi * 3200 * t) * (.5 + .5 * math.sin(2 * math.pi * .017 * t)))
        values[i] = value * fade_in * fade_out
    return values


def _stream(n: int) -> list[float]:
    """颗粒化金属流：密度随时间上升，不逐枚发声。"""
    values = [0.0] * n
    for i in range(n):
        t = i / RATE
        density = .35 + t / DURATIONS['stream']
        low = .05 * math.sin(2 * math.pi * 140 * t) * (1 - t / DURATIONS['stream'])
        values[i] = low
        for k in range(14):
            start = ((k * 173 + (k * k * 29) % 97) % 1000) / 1000 * (DURATIONS['stream'] - .1)
            if start <= t < start + .06 and _noise(k * 7 + 1) * .5 + .5 < density:
                freq = 2100 + ((k * 313) % 2600)
                values[i] += .10 * math.sin(2 * math.pi * freq * (t - start)) * math.exp(-(t - start) * 55)
    return values


def _event(identity: str, n: int) -> list[float]:
    seconds = DURATIONS[identity]
    values = []
    for i in range(n):
        t = i / RATE
        attack = min(1, t / .008)
        release = min(1, (seconds - t) / .05)
        env = attack * release
        if identity == 'drop1':
            value = .75 * math.sin(2 * math.pi * 185 * t) * math.exp(-t * 26)
            value += .25 * _noise(i) * math.exp(-t * 70)
        elif identity == 'drop2':
            value = .75 * math.sin(2 * math.pi * 228 * t) * math.exp(-t * 30)
            value += .25 * _noise(i + 5) * math.exp(-t * 70)
        elif identity == 'drop3':
            value = .75 * math.sin(2 * math.pi * 268 * t) * math.exp(-t * 34)
            value += .25 * _noise(i + 9) * math.exp(-t * 70)
        elif identity == 'slide':
            phase = 2 * math.pi * (420 * t - 165 * t * t)
            value = .55 * math.sin(phase) * math.exp(-t * 4) + .25 * _noise(i + 3) * math.exp(-t * 12)
        elif identity == 'float':
            phase = 2 * math.pi * (300 * t + 125 * t * t)
            value = .6 * math.sin(phase) * math.sin(math.pi * min(1, t / seconds)) ** 1.4
        elif identity == 'ding':
            value = _bell(t, (880, 1320, 1760), 4.5)
        elif identity == 'suction':
            phase = 2 * math.pi * (650 * t - 390 * t * t)
            value = .55 * math.sin(phase) * math.exp(-t * 3) + .3 * _noise(i + 7) * math.exp(-t * 8)
        elif identity == 'fusion':
            value = .5 * math.sin(2 * math.pi * 110 * t) * math.exp(-t * 4)
            value += .3 * math.sin(2 * math.pi * 165 * t) * math.exp(-t * 5)
        elif identity == 'tingLow':
            value = _bell(t, (440, 660, 990), 3.5)
        elif identity == 'tingHigh':
            value = _bell(t, (880, 1320, 1980), 5)
        elif identity == 'thump':
            value = .8 * math.sin(2 * math.pi * 85 * t) * math.exp(-t * 9)
            value += .2 * math.sin(2 * math.pi * 170 * t) * math.exp(-t * 12)
        elif identity == 'tick':
            value = .6 * math.sin(2 * math.pi * 1200 * t) * math.exp(-t * 50)
            value += .4 * _noise(i + 11) * math.exp(-t * 90)
        elif identity == 'resonance':
            value = .6 * math.sin(2 * math.pi * 70 * t) * math.exp(-t * 2.5)
            value += .3 * math.sin(2 * math.pi * 105 * t) * math.exp(-t * 3)
        elif identity == 'chime':
            value = _bell(t, (1046.5, 1568, 2093), 3.2)
        else:
            raise KeyError(identity)
        values.append(value * env)
    return values


def generate(identity: str, target: Path) -> None:
    seconds = DURATIONS[identity]
    n = round(RATE * seconds)
    values = _bed(n) if identity == 'bed' else _stream(n) if identity == 'stream' else _event(identity, n)
    peak = max(abs(value) for value in values) or 1
    scale = 10 ** (PEAK_DB[identity] / 20) / peak
    samples = b''.join(struct.pack('<h', round(value * scale * 32767)) for value in values)
    with wave.open(str(target), 'wb') as out:
        out.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        out.writeframes(samples)
