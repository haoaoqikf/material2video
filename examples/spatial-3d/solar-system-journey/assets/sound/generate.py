"""生成太阳系示例的音乐床与音效；全部原创合成，无第三方采样，按 CC0 1.0 分发。

无缝循环的做法（与 article-media-and-sound.md 的声床判据一致）：所有频率都取循环长度的整数分之一，
任何漂移都用相位调制而不是改变频率；因此末采样到首采样的步进不会超过素材内部的
最大相邻步进，循环点与信号内部同样平滑。
"""
import argparse
import hashlib
import json
import math
import struct
import wave
import sys
import tempfile
from pathlib import Path

RATE = 24000
BEAT_SECONDS = 1.0  # 60 BPM
LOOP_SECONDS = 16.0  # 16 拍，整数个周期
HERE = Path(__file__).parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--storyboard', type=Path, default=HERE.parents[1] / 'storyboard.json')
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--restore', action='store_true', help='按固定配方恢复缺失音轨，不覆盖摘要不符的已有文件')
mode.add_argument('--check', action='store_true', help='只核验固定配方与现有音轨')
args = parser.parse_args()
BOARD = json.loads(args.storyboard.read_text(encoding='utf-8'))
SCORE_SECONDS = BOARD['scenes'][0]['durationFrames'] / BOARD['fps']
SHOTS = {shot['id']: shot for shot in BOARD['scenes'][0]['content']['props']['shots']}
SCHEDULE = {key: [shot['startFrame'] / BOARD['fps'], shot['endFrame'] / BOARD['fps']]
            for key, shot in SHOTS.items() if shot.get('segment') or key == 'oort-tail'}


def source_inputs() -> dict:
    # Git的autocrlf不改变生成逻辑；用无BOM、统一换行的源码摘要支持跨平台恢复。
    source = Path(__file__).read_text(encoding='utf-8-sig').encode('utf-8')
    return {'generatorSha256': hashlib.sha256(source).hexdigest(),
            'durationSeconds': SCORE_SECONDS, 'schedule': SCHEDULE}


def seeded(seed: int):
    """确定性伪随机：同一种子在任何机器上都给出同一串数。"""
    state = seed & 0xFFFFFFFF

    def value() -> float:
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 0xFFFFFFFF * 2 - 1

    return value


def write(name: str, seconds: float, signal, directory: Path = HERE) -> Path:
    path = directory / name
    total = int(round(seconds * RATE))
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        for offset in range(0, total, RATE):
            block = bytearray()
            for index in range(offset, min(total, offset + RATE)):
                value = max(-1.0, min(1.0, signal(index / RATE)))
                block.extend(struct.pack("<h", round(value * 32767)))
            out.writeframes(bytes(block))
    return path


def bed(t: float) -> float:
    """60 BPM 环境底：低频 drone + 缓慢起伏的 pad + 每拍一次的柔和脉冲。"""
    phase = 2 * math.pi * t
    drone = 0.16 * math.sin(phase * 55) + 0.09 * math.sin(phase * 82.5) + 0.06 * math.sin(phase * 110)
    # 相位调制：调制周期取循环长度的整数分之一，循环点因此严格连续。
    drift = 0.05 * math.sin(phase * 0.25) + 0.03 * math.sin(phase * 0.125)
    pad = (0.07 + drift) * math.sin(phase * 220 + 1.6 * math.sin(phase * 0.25))
    beat = (t % BEAT_SECONDS) / BEAT_SECONDS
    pulse = 0.05 * math.exp(-beat * 6.0) * math.sin(phase * 330)
    swell = 0.75 + 0.25 * math.cos(phase / LOOP_SECONDS)
    return (drone + pad + pulse) * swell


def whoosh(t: float, duration: float = 1.4) -> float:
    """飞近 whoosh：带通噪声的包络扫过，配一条下行的低频。"""
    noise = seeded(20261017)
    envelope = math.sin(math.pi * min(1.0, t / duration)) ** 2
    body = 0.0
    # 用固定抽头近似带通：多档延迟相加再相乘，等价于共振但不引入随机相位。
    for tap in range(1, 5):
        body += noise() * math.sin(2 * math.pi * (900 - 620 * t / duration) * t + tap)
    return 0.22 * envelope * body / 4 + 0.12 * envelope * math.sin(2 * math.pi * (70 + 40 * t) * t)


def shimmer(t: float, duration: float = 1.8) -> float:
    """环 shimmer：高频泛音簇缓慢衰减，模拟冰晶颗粒的细碎反光。"""
    envelope = math.exp(-t * 2.2)
    partials = (1046.5, 1568.0, 2093.0, 2637.0, 3136.0)
    value = 0.0
    for index, frequency in enumerate(partials):
        value += math.sin(2 * math.pi * frequency * t) / (index + 2)
    tremolo = 0.6 + 0.4 * math.sin(2 * math.pi * 5.5 * t)
    return 0.16 * envelope * tremolo * value / 2.2


def ice(t: float, duration: float = 0.9) -> float:
    """冰裂：短促的噪声爆裂加几条固定共振。"""
    noise = seeded(773311)
    envelope = math.exp(-t * 9.0)
    crack = noise() * envelope * 0.35
    ring = 0.0
    for frequency in (420.0, 780.0, 1330.0):
        ring += math.sin(2 * math.pi * frequency * t) * math.exp(-t * (7.0 + frequency / 400))
    return crack + 0.12 * ring / 3



def score(t: float) -> float:
    """按当前分镜时长生成的同主题配乐：温暖探索→巨行星高潮→外层留韵；纯合成艺术声音。"""
    # Smooth phrase envelopes put useful energy above bass for small speakers.
    notes = (261.6256, 329.6276, 391.9954, 493.8833, 391.9954, 329.6276, 293.6648, 391.9954)
    phrase = t / 2.5
    index = int(phrase) % len(notes)
    local = phrase % 1
    note = notes[index]
    envelope = math.sin(math.pi * local) ** 2
    melody = envelope * (0.20 * math.sin(2 * math.pi * note * t)
                         + 0.055 * math.sin(2 * math.pi * note * 2 * t))
    chord = sum(math.sin(2 * math.pi * f * t) for f in (130.8128, 195.9977, 261.6256)) * 0.045
    earth = sum(SCHEDULE['earth-hero']) / 2
    saturn = sum(SCHEDULE['saturn-hero']) / 2
    # 乐句力度跟随实际镜头，不再假定土星永远位于片长57%的位置。
    warmth = math.exp(-((t - earth) / 4.5) ** 2)
    climax = math.exp(-((t - saturn) / 5.5) ** 2)
    outer_start = SCHEDULE['neptune-station'][0]
    sparse = max(0.0, min(1.0, (t - outer_start) / 10))
    opening = min(1.0, t / 4)
    ending = min(1.0, max(0.0, (SCORE_SECONDS - t) / 8))
    return (melody * (0.65 + warmth * 0.18 + climax * 0.5) * (1 - sparse * 0.35)
            + chord * (1 - sparse * 0.20) + bed(t) * (0.18 + climax * 0.06)) * opening * ending

def generate(directory: Path) -> None:
    write("bed.wav", LOOP_SECONDS, bed, directory)
    raw = write("score-raw.wav", SCORE_SECONDS, score, directory)
    # Normalize the independent music stem before authored gain and speech ducking.
    from film_runtime.engine.audio import normalize
    normalize(raw, directory / "score.wav", integrated=-18.0, true_peak=-3.0)
    raw.unlink()
    write("whoosh.wav", 1.4, whoosh, directory)
    write("shimmer.wav", 1.8, shimmer, directory)
    write("ice.wav", 0.9, ice, directory)


NAMES = ('bed.wav', 'score.wav', 'whoosh.wav', 'shimmer.wav', 'ice.wav')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    recipe = HERE / 'recipe.json'
    if args.restore or args.check:
        record = json.loads(recipe.read_text(encoding='utf-8'))
        if record.get('version') != 1 or record.get('inputs') != source_inputs() or set(record.get('files', {})) != set(NAMES):
            raise RuntimeError('声音配方与当前生成器/镜头预算不符；请由制作过程重新生成并登记，不得静默接受摘要漂移')
        missing = []
        for name in NAMES:
            path = HERE / name
            if not path.is_file():
                missing.append(name)
            elif digest(path) != record['files'][name]['sha256']:
                raise RuntimeError(f'已有声音摘要不符，不覆盖：{path}')
        if missing and args.check:
            raise RuntimeError(f'缺少声音：{missing}；运行 assets/fetch.py 恢复')
        if missing:
            with tempfile.TemporaryDirectory(prefix='.restore-', dir=HERE) as temporary:
                stage = Path(temporary)
                generate(stage)
                for name in NAMES:
                    if digest(stage / name) != record['files'][name]['sha256']:
                        raise RuntimeError(f'声音恢复摘要不符：{name}；保留已有文件，不改写配方')
                for name in missing:
                    with (HERE / name).open('xb') as target:
                        target.write((stage / name).read_bytes())
        print('声音配方与5项素材核验通过')
        return
    generate(HERE)
    files = {}
    for name in NAMES:
        with wave.open(str(HERE / name)) as wav:
            seconds = wav.getnframes() / wav.getframerate()
        files[name] = {'sha256': digest(HERE / name), 'durationSeconds': seconds}
    recipe.write_text(json.dumps({'version': 1, 'inputs': source_inputs(), 'files': files},
                                 ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'已生成{SCORE_SECONDS:.3f}秒配乐及固定恢复配方')


if __name__ == '__main__':
    main()
