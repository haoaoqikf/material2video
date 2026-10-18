"""太阳系材质输入：验证实际登记、颜色/数据图设置与可复现生成，不用文件名猜质量。"""
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/solar-system-journey'
spec = importlib.util.spec_from_file_location('solar_material_generator', EXAMPLE / 'assets/materials/generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def test_six_cinematic_targets_have_registered_materials():
    from m2v.types.general.media_assets import resolve
    media = resolve(EXAMPLE)['media']
    record = json.loads((EXAMPLE / 'assets/media-sources.json').read_text(encoding='utf-8'))
    entries = {e['id']: e for e in record['assets']}
    for target in generator.TARGETS:
        assert media[target]['width'] >= 4096
        assert media[target]['license'] != '未知'
        for role in ('normal', 'roughness', 'emissive'):
            e = entries[f'{target}-{role}']
            assert e['target'] == target and e['role'] == role
            assert e['colorSpace'] == ('linear' if role in ('normal', 'roughness') else 'srgb')
    assert media['rings']['width'] >= 4096 and media['rings']['height'] >= 512
    assert media['rings']['alpha']


def test_generated_micro_normals_are_unit_vectors_and_repeatable():
    a = list(generator.material_rows('pluto', 'normal', 32, 16))
    b = list(generator.material_rows('pluto', 'normal', 32, 16))
    assert a == b
    for row in a:
        for i in range(0, len(row), 4):
            length = math.sqrt(sum((v / 127.5 - 1) ** 2 for v in row[i:i+3]))
            assert .99 <= length <= 1.01


def test_ring_profile_retains_cassini_gap():
    row = next(generator.ring_rows(4096, 512))
    def alpha(radius):
        x = int((radius - 1.24) / 1.03 * 4096)
        return row[x * 4 + 3]
    assert alpha(1.98) < 20
    assert alpha(1.8) > 150 and alpha(2.1) > 100


def test_non_emitting_planets_do_not_get_fake_glow():
    row = next(generator.material_rows('saturn', 'emissive', 8, 4))
    assert row == bytes([0, 0, 0, 255]) * 8
