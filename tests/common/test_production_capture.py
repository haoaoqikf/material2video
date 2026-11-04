"""真实浏览器覆盖稀疏采样、短事件与图片派生的集成路径。"""
import json

import pytest

from helpers.general import STARTER, requires_node
from helpers.production import project as production_project
from m2v.core import frames
from m2v.core.delivery import outputs
from m2v.production import checks
from m2v.production.storage import read


@requires_node
@pytest.mark.slow
def test_real_capture_keeps_event_neighbors_and_native_phone_frames(tmp_path, monkeypatch, chromium_ready):
    root, manifest, c = production_project(tmp_path)
    c['scenes'] = c['scenes'][:1]
    cp = c['scenes'][0]['checkpoints'][0]
    cp['expected'] = [{'role': 'disc', 'count': 1}]
    (root / 'DESIGN.md').write_text('```m2v-checkpoints\n' + json.dumps(c) + '\n```\n', encoding='utf-8')
    source = STARTER.read_text(encoding='utf-8').replace('<div style={{width, height,', '<div data-m2v-role="disc" style={{width, height,')
    (root / 'scenes/one.tsx').write_text(source, encoding='utf-8')
    clip = outputs(root) / 'cached.mp4'
    checks.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=1920x1080:r=30:d=1',
                   '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(clip)])
    scene = {'id': 'one', 'startFrame': 0, 'endFrame': 30, 'durationInFrames': 30, 'segmentWindows': {},
             'content': {'entry': 'scenes/one.tsx', 'props': {}}, 'mediaPath': 'outputs/cached.mp4'}
    prepared = {'props': {'compiledScenes': [scene], 'subtitle': frames.spec(1920, 1080)['subtitle'],
                          'resolvedEvents': [{'id': 'pulse', 'sceneId': 'one', 'frame': 7, 'globalFrame': 7}]}}
    monkeypatch.setattr('m2v.core.project.load_project', lambda *_: (root, manifest))
    monkeypatch.setattr('m2v.commands._prepared', lambda *_: prepared)
    monkeypatch.setattr('m2v.types.general.media_assets.resolve', lambda *_: {'media': {}})
    monkeypatch.setattr('m2v.types.general.code_scenes.materialize', lambda *_: prepared)
    monkeypatch.setattr(checks, 'ffmpeg', lambda *_: pytest.fail('图片派生不应启动 ffmpeg'))
    report = read(checks.capture(root, c, None)[0])
    assert all(item['status'] != 'fail' for item in report['checks'])
    assert any(item['name'] == '对象状态:disc' and item['status'] == 'pass' for item in report['checks'])
    # 只声明对象计数，没有声明文字预算；不能把采集成功写成全部通过。
    assert report['status'] == 'unverified'
    directory = outputs(root) / 'production/checkpoints/one-cp'
    measurement = read(directory / 'measurements.json')
    assert set(map(int, measurement['frames'])) == {0, 6, 7, 8, 15, 29}
    assert measurement['eventCoverage']['sampleStep'] == 15
    assert not measurement['eventCoverage']['missedFrames']
    assert len(list(directory.glob('*-1920.png'))) == 6
    assert len(list(directory.glob('*-393.png'))) == 6
    assert not list(directory.glob('*-852.png'))
    assert (directory / 'window.mp4').read_bytes() == clip.read_bytes()
