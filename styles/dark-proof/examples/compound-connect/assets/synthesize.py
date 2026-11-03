"""《接》原创程序化配乐与事件音；24 kHz PCM16 单声道，CC0-1.0。

所有音色由确定性数学生成，不含第三方采样。112 BPM 配乐按八拍分段：
前轻、中抬、尾收；事件音只按角色命名，具体帧位由分镜事件决定。
"""
import math
import struct
import wave
from pathlib import Path

RATE = 24000
DURATIONS = {
    'bed': 60.0,
    'origin': 0.5,
    'spiral': 0.35,
    'fold': 0.25,
    'moon': 1.1,
    'board': 0.5,
    'grain': 0.12,
    'network': 1.2,
    'return': 0.9,
    'curve': 1.0,
    'finale': 1.6,
}
PEAK_DB = {
    'bed': -8.5,
    'origin': -16,
    'spiral': -18,
    'fold': -17,
    'moon': -11,
    'board': -16,
    'grain': -20,
    'network': -12,
    'return': -14,
    'curve': -13,
    'finale': -10,
}


def _noise(seed: int) -> float:
    """确定性伪随机，返回 [-1, 1)。"""
    x = math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return (x - math.floor(x)) * 2 - 1


def _bell(t: float, freqs: tuple[float, ...], decay: float, attack: float = .006) -> float:
    envelope = min(1, t / attack) * math.exp(-t * decay)
    return sum(weight * math.sin(2 * math.pi * freq * t)
               for freq, weight in zip(freqs, (0.62, 0.26, 0.12))) * envelope


BPM = 112
BEAT = 60 / BPM


def _add(buffer: list[float], start: float, values: list[float], gain: float = 1.0) -> None:
    begin = max(0, round(start * RATE))
    for offset, value in enumerate(values):
        index = begin + offset
        if index >= len(buffer):
            break
        buffer[index] += value * gain


def _kick(seconds: float = 0.24) -> list[float]:
    count = round(RATE * seconds)
    out = []
    for index in range(count):
        t = index / RATE
        envelope = math.exp(-t * 13)
        frequency = 50 + 22 * math.exp(-t * 32)
        out.append((0.82 * math.sin(2 * math.pi * frequency * t)
                    + 0.12 * _noise(index + 101) * math.exp(-t * 70)) * envelope)
    return out


def _tick(seconds: float = 0.08) -> list[float]:
    count = round(RATE * seconds)
    out = []
    for index in range(count):
        t = index / RATE
        envelope = math.exp(-t * 72)
        out.append((0.5 * _noise(index + 211)
                    + 0.24 * math.sin(2 * math.pi * 1760 * t) * math.exp(-t * 48)) * envelope)
    return out


def _hat(seconds: float = 0.06) -> list[float]:
    count = round(RATE * seconds)
    return [_noise(index + 307) * math.exp(-index / RATE * 110) * 0.24
            for index in range(count)]


def _riser(seconds: float = 1.6) -> list[float]:
    count = round(RATE * seconds)
    out = []
    for index in range(count):
        t = index / RATE
        phase = min(1.0, t / seconds)
        frequency = 180 + 1500 * phase * phase
        envelope = phase ** 2
        out.append((0.55 * _noise(index + 401) * envelope
                    + 0.2 * math.sin(2 * math.pi * frequency * t) * envelope))
    return out


def _motif(seconds: float, freqs: tuple[float, ...]) -> list[float]:
    count = round(RATE * seconds)
    return [_bell(index / RATE, freqs, 2.6) for index in range(count)]


def _score_impact(seconds: float = 0.7) -> list[float]:
    count = round(RATE * seconds)
    out = []
    for index in range(count):
        t = index / RATE
        envelope = math.exp(-t * 9)
        out.append((0.8 * math.sin(2 * math.pi * 48 * t)
                    + 0.22 * math.sin(2 * math.pi * 72 * t)
                    + 0.12 * _noise(index + 503) * math.exp(-t * 24)) * envelope)
    return out


def _section_energy(t: float) -> float:
    if t < 6:
        return 0.24 + 0.3 * min(1.0, t / 6)
    if t < 14:
        return 0.62
    if t < 20:
        return 0.72
    if t < 24:
        return 0.56
    if t < 30:
        return 0.84
    if t < 36:
        return 0.9
    if t < 41:
        return 0.92
    if t < 47:
        return 0.46
    if t < 52:
        return 0.7
    if t < 56:
        return 0.95
    if t < 58:
        return 1.0
    return max(0.0, 1.0 - (t - 58) / 2.0)


CHORDS = [
    (0.0, 6.0, (110.0, 130.81, 164.81)),
    (6.0, 14.0, (87.31, 110.0, 130.81)),
    (14.0, 20.0, (130.81, 164.81, 196.0)),
    (20.0, 24.0, (98.0, 123.47, 146.83)),
    (24.0, 30.0, (110.0, 130.81, 164.81)),
    (30.0, 36.0, (98.0, 123.47, 146.83)),
    (36.0, 41.0, (110.0, 130.81, 164.81)),
    (41.0, 47.0, (87.31, 110.0, 130.81)),
    (47.0, 52.0, (98.0, 123.47, 146.83)),
    (52.0, 60.0, (130.81, 164.81, 196.0)),
]


def _score(n: int) -> list[float]:
    """60 秒、112 BPM 的原创程序化配乐；无采样、无第三方音乐。"""
    buffer = [0.0] * n
    for begin, end, freqs in CHORDS:
        first = max(0, round(begin * RATE))
        last = min(n, round(end * RATE))
        for index in range(first, last):
            t = index / RATE
            edge = min(1.0, (t - begin) / 0.4, (end - t) / 0.4)
            tremolo = 0.82 + 0.18 * math.sin(2 * math.pi * 0.17 * t + begin)
            value = (
                0.052 * math.sin(2 * math.pi * freqs[0] * t)
                + 0.032 * math.sin(2 * math.pi * freqs[1] * t)
                + 0.02 * math.sin(2 * math.pi * freqs[2] * t)
            )
            buffer[index] += value * max(0.0, edge) * tremolo
    step = 0
    while step * BEAT < 60:
        t = step * BEAT
        energy = _section_energy(t)
        if energy > 0.05:
            _add(buffer, t, _kick(), 0.58 * energy)
            if 6 <= t < 58:
                _add(buffer, t + BEAT * 0.5, _tick(), 0.18 * energy)
        step += 1
    for begin, end in ((24, 29.5), (30, 35.5), (36, 40.5), (47, 51.5), (52, 55.5)):
        for tick in [begin + index * BEAT / 2 for index in range(int((end - begin) / (BEAT / 2)))]:
            _add(buffer, tick, _hat(), 0.7 * _section_energy(tick))
    for begin, _, freqs in CHORDS:
        _add(buffer, begin + 0.02, _motif(1.6, (freqs[1] * 2, freqs[2] * 2, freqs[1] * 3)),
             0.1 if begin else 0.06)
    for end, riser, impact in ((5.8, 0.22, 0.34), (13.8, 0.26, 0.36), (19.8, 0.28, 0.38),
                               (23.8, 0.24, 0.32), (29.8, 0.3, 0.4), (35.8, 0.3, 0.4),
                               (40.9, 0.5, 0.55), (46.8, 0.24, 0.3),
                               (51.8, 0.28, 0.36), (55.7, 0.5, 0.55), (58.0, 0.2, 0.3)):
        _add(buffer, max(0.0, end - 1.4), _riser(1.4), riser)
        _add(buffer, end, _score_impact(), impact)
    for index in range(n):
        t = index / RATE
        if 40.9 <= t < 41.3:
            buffer[index] *= 0.18
        if t > 58.4:
            buffer[index] *= max(0.0, (60.0 - t) / 1.6)
    return buffer


def _event(identity: str, n: int) -> list[float]:
    seconds = DURATIONS[identity]
    values = []
    for index in range(n):
        t = index / RATE
        attack = min(1.0, t / .004)
        release = min(1.0, (seconds - t) / .04)
        env = attack * release
        if identity == 'origin':
            value = _bell(t, (660, 990, 1320), 3.6)
        elif identity == 'spiral':
            value = .55 * math.sin(2 * math.pi * 1180 * t) * math.exp(-t * 34)
            value += .35 * _noise(index + 3) * math.exp(-t * 60)
        elif identity == 'fold':
            value = .5 * _noise(index + 5) * math.exp(-t * 26)
            value += .4 * math.sin(2 * math.pi * (140 + 90 * t) * t) * math.exp(-t * 18)
        elif identity == 'moon':
            swell = math.sin(math.pi * min(1.0, t / seconds)) ** 1.2
            value = .5 * _bell(t, (440, 660, 990), 1.6) * swell
            value += .35 * _noise(index + 7) * swell * math.exp(-t * 1.4)
        elif identity == 'board':
            value = .6 * math.sin(2 * math.pi * 96 * t) * math.exp(-t * 16)
            value += .3 * _noise(index + 9) * math.exp(-t * 30)
        elif identity == 'grain':
            value = .55 * _noise(index + 11) * math.exp(-t * 95)
            value += .25 * math.sin(2 * math.pi * 2400 * t) * math.exp(-t * 55)
        elif identity == 'network':
            value = _bell(t, (880, 1320, 1760), 3.0)
            value += .18 * _noise(index + 13) * math.exp(-t * 3) * 0.4
        elif identity == 'return':
            value = .52 * math.sin(2 * math.pi * 110 * t) * math.exp(-t * 2.4)
            value += .28 * _bell(t, (330, 495, 660), 2.2)
        elif identity == 'curve':
            phase = min(1.0, t / seconds)
            value = .35 * _noise(index + 17) * phase ** 2
            value += .3 * math.sin(2 * math.pi * (180 + 900 * phase ** 2) * t) * phase
        elif identity == 'finale':
            attack_slow = min(1.0, t / .08)
            release_slow = min(1.0, (seconds - t) / .5)
            value = (
                .46 * math.sin(2 * math.pi * 55 * t)
                + .30 * math.sin(2 * math.pi * 82.5 * t)
                + .18 * math.sin(2 * math.pi * 110 * t)
                + .08 * _noise(index + 29) * math.exp(-t * 2)
            ) * (0.55 + 0.45 * math.sin(math.pi * min(1.0, t / seconds))) * attack_slow * release_slow
        else:
            raise KeyError(identity)
        values.append(value * env)
    return values


def generate(identity: str, target: Path) -> None:
    seconds = DURATIONS[identity]
    n = round(RATE * seconds)
    values = _score(n) if identity == 'bed' else _event(identity, n)
    peak = max(abs(value) for value in values) or 1
    scale = 10 ** (PEAK_DB[identity] / 20) / peak
    samples = b''.join(struct.pack('<h', round(value * scale * 32767)) for value in values)
    with wave.open(str(target), 'wb') as out:
        out.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        out.writeframes(samples)


def generate_all(directory: Path) -> dict[str, str]:
    import hashlib
    directory.mkdir(parents=True, exist_ok=True)
    digests = {}
    for identity in DURATIONS:
        target = directory / f'{identity}.wav'
        generate(identity, target)
        digests[identity] = hashlib.sha256(target.read_bytes()).hexdigest()
    return digests


if __name__ == '__main__':
    import json
    target = Path(__file__).resolve().parent / 'media'
    print(json.dumps(generate_all(target), ensure_ascii=False, indent=2))
