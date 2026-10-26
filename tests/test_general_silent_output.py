"""用真实小候选验证零音轨、有声保留与重复交付。"""
import json
import subprocess

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.types.general import adapter, explainer_render
from _helpers import board, fake_tts, project, scene


@pytest.mark.parametrize('props,expected', [
    ({'compiledScenes': [{'narrationSegments': []}]}, False),
    ({'compiledScenes': [{'narrationSegments': [{'text': '声音'}]}]}, True),
    ({'soundtrack': {'music': {'sourceRef': 'bed.wav'}}}, True),
    ({'soundtrack': {'effects': [{'builtin': 'ding'}]}}, True),
    ({'soundtrack': {'effects': []}}, False),
])
def test_declared_sound_controls_delivery(props, expected):
    assert explainer_render._has_audio({'props': props}) is expected


@pytest.mark.slow
@pytest.mark.parametrize('sound', ['none', 'effect', 'narration'])
def test_real_delivery_streams_and_candidate_reuse(tmp_path, monkeypatch, chromium_ready, sound):
    unit = scene(durationFrames=30, narrationSegments=[])
    data = board(fps=30, targetSeconds=1, scenes=[unit])
    if sound == 'effect':
        data['soundtrack'] = {'effects': [{'builtin': 'ding', 'sceneId': 'a', 'offsetMs': 0}]}
    elif sound == 'narration':
        unit['narrationSegments'] = [{'id': 'a-voice', 'text': '观察结果。'}]
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch, seconds=.4)
    prepared = adapter.prepare(root, manifest)
    output = adapter.render(root, manifest)
    original = output.read_bytes()
    metadata = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-i', str(output)],
                              capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    assert ('Audio:' in metadata) == (sound != 'none')
    assert prepared['durationInFrames'] == 30
    provenance = json.loads(output.with_suffix('.provenance.json').read_text(encoding='utf-8'))
    assert (provenance['audio'].get('mode') == 'none') == (sound == 'none')
    monkeypatch.setattr(explainer_render, '_generate', lambda *_a, **_k: pytest.fail('重复导出不得再生成'))
    assert adapter.render(root, manifest).read_bytes() == original
