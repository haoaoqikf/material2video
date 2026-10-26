"""复利例的制作契约与可恢复声音；数学计算另由TS测试验证。"""
import hashlib
import importlib.util
import json
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/compound-interest'
BED = {'sourceRef': 'assets/media/bed.wav', 'gainDb': 0, 'loop': False,
       'fadeInMs': 0, 'fadeOutMs': 0}
DROPS = [17, 19, 22, 25, 27, 30, 33, 35, 38, 41]


def test_film_is_870_frames_with_ambient_bed_and_events():
    board = json.loads((EXAMPLE / 'storyboard.json').read_text(encoding='utf-8'))
    assert (board['width'], board['height'], board['fps'], board['targetSeconds']) == (1920, 1080, 30, 29)
    assert len(board['scenes']) == 1
    scene = board['scenes'][0]
    assert scene['durationFrames'] == 870 and scene['narrationSegments'] == []
    assert board['soundtrack']['music'] == BED
    effects = board['soundtrack']['effects']
    assert len(effects) == 25
    offsets = [effect['offsetFrames'] for effect in effects]
    assert offsets == sorted(offsets)
    assert offsets[:10] == DROPS and offsets[-1] == 810
    assert all(effect['gainDb'] <= 0 for effect in effects)
    assert 'tts' not in json.loads((EXAMPLE / 'project.json').read_text(encoding='utf-8'))


def load_fetch():
    # 脚本平时由assets目录执行，测试隔离装载而不改变生产导入路径。
    def load(name):
        spec = importlib.util.spec_from_file_location('compound_' + name, EXAMPLE / f'assets/{name}.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    synth = load('synthesize')
    old = sys.modules.get('synthesize')
    sys.modules['synthesize'] = synth
    try:
        return load('fetch')
    finally:
        if old is None:
            sys.modules.pop('synthesize', None)
        else:
            sys.modules['synthesize'] = old


def test_audio_recipe_reproduces_exact_hash_and_format(tmp_path):
    fetch = load_fetch()
    recipe = json.loads((EXAMPLE / 'assets/recipe.json').read_text(encoding='utf-8'))
    for item in recipe['assets']:
        target = tmp_path / (item['id'] + '.wav')
        fetch.generate(item['id'], target)
        fetch.validate(target, item)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == item['expectedSha256']
        with wave.open(str(target)) as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 24000)
            assert abs(wav.getnframes() / 24000 - item['durationSeconds']) <= 1 / 24000


def test_bed_is_silent_until_eight_seconds_and_fades_out(tmp_path):
    """music 没有起始偏移：8 秒进入必须烘焙在 bed.wav 里。"""
    spec = importlib.util.spec_from_file_location('compound_synth_bed', EXAMPLE / 'assets/synthesize.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path / 'bed.wav'
    module.generate('bed', target)
    with wave.open(str(target)) as wav:
        assert wav.getframerate() == 24000 and wav.getnchannels() == 1
        assert wav.getnframes() / 24000 == 29.0
        samples = wav.readframes(wav.getnframes())
    values = [abs(int.from_bytes(samples[i:i + 2], 'little', signed=True))
              for i in range(0, len(samples), 2)]
    lead = 8 * 24000
    assert max(values[:lead]) == 0, '前8秒必须是数字静音'
    first = next(i for i, value in enumerate(values) if value)
    assert abs(first / 24000 - 8.0) <= .002, '环境床应在8.0秒进入'
    assert max(values) > 500, '环境床必须可闻'
    assert max(values[-2400:]) < max(values) * .2, '28.9–29.0秒应淡出'


def test_restore_refuses_drift_without_overwriting_any_input(tmp_path, monkeypatch):
    fetch = load_fetch()
    assets = tmp_path / 'assets'
    assets.mkdir()
    recipe = json.loads((EXAMPLE / 'assets/recipe.json').read_text(encoding='utf-8'))
    (assets / 'recipe.json').write_text(json.dumps(recipe), encoding='utf-8')
    media = assets / 'media'
    media.mkdir()
    existing = media / 'drop1.wav'
    existing.write_bytes(b'previous-content')
    monkeypatch.setattr(fetch, 'HERE', assets)
    with pytest.raises(ValueError, match='摘要'):
        fetch.restore()
    assert existing.read_bytes() == b'previous-content'
    assert len(list(media.iterdir())) == 1


def test_review_pack_samples_first_frame_instead_of_bucket_midpoint(tmp_path):
    """时间码必须与实际帧对应，避免25帧/秒滤镜采到半个采样周期后。"""
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe
    spec = importlib.util.spec_from_file_location('review_pack', EXAMPLE / 'scripts/create_review_pack.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / 'v.mp4'
    subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=192x108:r=30:d=0.1',
                    '-f', 'lavfi', '-i', 'color=blue:s=192x108:r=30:d=0.9', '-filter_complex',
                    '[0:v][1:v]concat=n=2:v=1:a=0', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
    output = tmp_path / 'pack'
    assert module.create(source, output, 'T', 1, .5) == 2
    result = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-i', str(output / 'full/frame-001.png'),
                             '-vf', 'scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    assert result[0] > 200 and result[2] < 50


def test_review_pack_handles_non_zero_start(tmp_path):
    """微距评审从 8 秒开始：起点与时间码都要落在实际片段上。"""
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe
    spec = importlib.util.spec_from_file_location('review_pack_start', EXAMPLE / 'scripts/create_review_pack.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / 'v.mp4'
    subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=192x108:r=30:d=0.1',
                    '-f', 'lavfi', '-i', 'color=blue:s=192x108:r=30:d=0.9', '-filter_complex',
                    '[0:v][1:v]concat=n=2:v=1:a=0', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
    output = tmp_path / 'pack'
    assert module.create(source, output, 'T2', .4, .2, start_seconds=.2) == 2
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['timecodes'][0] == pytest.approx(.2)
    result = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-i', str(output / 'full/frame-001.png'),
                             '-vf', 'scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    assert result[2] > 200 and result[0] < 50
