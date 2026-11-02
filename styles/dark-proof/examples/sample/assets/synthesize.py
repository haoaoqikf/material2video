"""《样本》原创环境床与事件音；24 kHz PCM16 单声道，CC0-1.0。

所有音色由确定性数学生成，不含第三方采样。环境床前 6 秒轻入，20 秒硬切处
留出短促的低频撞击与半拍留白，43 秒公式段再抬一次，51–58 秒收束。事件音按
角色命名，具体帧位由分镜事件决定，生成器不知道叙事时间。
"""
import math
import struct
import wave
from pathlib import Path

RATE = 24000
DURATIONS = {
    'bed': 58.0,
    'swing': 0.22,
    'impact': 0.9,
    'scratch': 0.45,
    'dissolve': 0.8,
    'regress': 0.9,
    'anchor': 0.5,
    'formula': 1.1,
    'finale': 1.6,
}
PEAK_DB = {
    'bed': -15,
    'swing': -18,
    'impact': -9,
    'scratch': -17,
    'dissolve': -18,
    'regress': -14,
    'anchor': -14,
    'formula': -12,
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


def _lowpass(values: list[float], coefficient: float) -> list[float]:
    out = []
    state = 0.0
    for value in values:
        state = state * coefficient + value * (1 - coefficient)
        out.append(state)
    return out


def _bed(n: int) -> list[float]:
    """低频持续纹理：无节拍、无旋律；动态弧线由包络与和声厚度承担。"""
    raw = [0.0] * n
    for index in range(n):
        t = index / RATE
        # 前 6 秒轻入，20 秒硬切处短暂收窄，43 秒再抬，51–58 秒收束。
        intro = min(1.0, max(0.0, (t - 0.4) / 2.6))
        tail = min(1.0, max(0.0, (58.0 - t) / 4.5))
        dip = 0.35 + 0.65 * min(1.0, abs(t - 20.0) / 0.9)
        lift = 1.0 + 0.22 * min(1.0, max(0.0, (t - 42.0) / 2.0)) * min(1.0, max(0.0, (52.0 - t) / 4.0))
        lfo = 0.5 + 0.5 * math.sin(2 * math.pi * 0.031 * t + 0.4)
        value = (
            0.40 * math.sin(2 * math.pi * 48.0 * t + 0.4 * math.sin(2 * math.pi * 0.031 * t))
            + 0.24 * math.sin(2 * math.pi * 63.7 * t + 0.3 * math.sin(2 * math.pi * 0.023 * t))
            + 0.16 * math.sin(2 * math.pi * 82.1 * t)
            + 0.10 * math.sin(2 * math.pi * 109.3 * t)
            + 0.05 * math.sin(2 * math.pi * 196.0 * t) * lfo
        )
        raw[index] = value * intro * tail * dip * lift
    # 极低通噪声作为空气层；只在 6 秒后加入，避免开场有“嘶”声。
    noise = [0.0] * n
    for index in range(n):
        t = index / RATE
        if t >= 6.0:
            noise[index] = _noise(index) * 0.06 * min(1.0, (t - 6.0) / 2.0)
    smooth = _lowpass(noise, 0.995)
    return [value + smooth[index] for index, value in enumerate(raw)]


def _event(identity: str, n: int) -> list[float]:
    seconds = DURATIONS[identity]
    values = []
    for index in range(n):
        t = index / RATE
        attack = min(1.0, t / .004)
        release = min(1.0, (seconds - t) / .04)
        env = attack * release
        if identity == 'swing':
            value = .55 * math.sin(2 * math.pi * 1180 * t) * math.exp(-t * 46)
            value += .45 * _noise(index + 3) * math.exp(-t * 80)
        elif identity == 'impact':
            value = .78 * math.sin(2 * math.pi * 58 * t) * math.exp(-t * 7.5)
            value += .22 * math.sin(2 * math.pi * 116 * t) * math.exp(-t * 11)
            value += .10 * _noise(index + 7) * math.exp(-t * 18)
        elif identity == 'scratch':
            phase = 2 * math.pi * (900 * t - 420 * t * t)
            value = .42 * math.sin(phase) * math.exp(-t * 5)
            value += .35 * _noise(index + 11) * math.exp(-t * 9)
        elif identity == 'dissolve':
            swell = math.sin(math.pi * min(1.0, t / seconds)) ** 1.6
            value = .62 * _noise(index + 17) * swell
            value += .18 * math.sin(2 * math.pi * 2200 * t) * swell
        elif identity == 'regress':
            value = _bell(t, (660, 990, 1320), 4.0)
        elif identity == 'anchor':
            value = .68 * math.sin(2 * math.pi * 190 * t) * math.exp(-t * 22)
            value += .32 * _noise(index + 23) * math.exp(-t * 40)
        elif identity == 'formula':
            value = _bell(t, (880, 1320, 1760), 3.4)
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
    values = _bed(n) if identity == 'bed' else _event(identity, n)
    peak = max(abs(value) for value in values) or 1
    scale = 10 ** (PEAK_DB[identity] / 20) / peak
    samples = b''.join(struct.pack('<h', round(value * scale * 32767)) for value in values)
    with wave.open(str(target), 'wb') as out:
        out.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        out.writeframes(samples)


def generate_all(directory: Path) -> dict[str, str]:
    """生成全部音效并返回摘要；写盘前先算摘要，避免半套文件。"""
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
