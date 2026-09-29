"""分段语音与混音契约：离线替身仅用于测试，不充作真实样片评审。"""
import copy
import json
import math
import struct
import wave
import subprocess
from pathlib import Path

import pytest
from a2v import audio, prepare, production, storyboard, sound
from a2v.errors import A2VError
from a2v.media import load_media
from test_production_workflow import _ready_record

def tone(path, duration=.5):
    with wave.open(str(path), 'wb') as out:
        out.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        out.writeframes(b''.join(struct.pack('<h', round(6000 * math.sin(2 * math.pi * 400 * n / 24000))) for n in range(round(duration * 24000))))

def test_speech_and_sound_contract(valid_script):
    segment = valid_script['scenes'][0]['narrationSegments'][0]
    segment['speech'] = {'rate': '-50%', 'pauseBeforeMs': 2000, 'pauseAfterMs': 0}
    assert storyboard.validate(valid_script).ok
    for speech in ({'rate': '+51%'}, {'rate': '10%'}, {'pauseAfterMs': True}, {'pauseBeforeMs': 2001}, {'extra': 0}):
        segment['speech'] = speech
        assert not storyboard.validate(valid_script).ok
    segment.pop('speech')
    for ref in ('../secret.wav', 'https://example.com/a.wav', '/tmp/a.wav', 'a\\b.wav'):
        valid_script['soundtrack'] = {'music': {'sourceRef': ref}}
        assert not storyboard.validate(valid_script).ok
    valid_script['soundtrack'] = {'effects': [{'sourceRef': 'assets/drop.wav', 'sceneId': 'missing', 'beatId': 'b1'}]}
    assert not storyboard.validate(valid_script).ok

def test_segment_pause_cache_and_legacy(tmp_path, valid_script, monkeypatch):
    calls = []
    async def fake(text, voice, rate, output):
        calls.append((text, rate)); tone(output)
        return [{'text': text.strip('，。'), 'start': .1, 'end': .4}]
    monkeypatch.setattr(prepare, 'synthesize', fake)
    for scene in valid_script['scenes']:
        scene['narrationSegments'] = [{'id': 'n1', 'text': '重复，', 'beatId': 'b1', 'speech': {'pauseBeforeMs': 100, 'pauseAfterMs': 200}}, {'id': 'n2', 'text': '重复。', 'beatId': 'b2', 'speech': {'rate': '+10%'}}]
    source = tmp_path / 'storyboard.json'; source.write_text(json.dumps(valid_script), encoding='utf-8')
    manifest = prepare.prepare(source, tmp_path / 'media')
    media = load_media(manifest, source)
    assert len(calls) == 2
    assert media.data['cues'][0]['start'] == pytest.approx(.2)
    assert media.data['cues'][1]['start'] == pytest.approx(.9)
    assert media.data['scenes'][0]['resolvedBeats'][0]['startFrame'] == 0
    assert media.data['scenes'][0]['resolvedBeats'][0]['endFrame'] == 24
    valid_script['scenes'][0]['narrationSegments'][0]['speech']['pauseAfterMs'] = 300
    source.write_text(json.dumps(valid_script), encoding='utf-8')
    prepare.prepare(source, manifest.parent); assert len(calls) == 2
    old = json.loads(manifest.read_text(encoding='utf-8')); old['version'] = 2
    manifest.write_text(json.dumps(old), encoding='utf-8')
    with pytest.raises(A2VError, match='重新 prepare'): load_media(manifest, source)

def test_mix_loop_duck_and_failure_preserves_manifest(tmp_path, valid_script, monkeypatch):
    async def fake(text, voice, rate, output):
        tone(output); return [{'text': text.strip('，。'), 'start': .1, 'end': .4}]
    monkeypatch.setattr(prepare, 'synthesize', fake)
    for scene in valid_script['scenes']:
        scene['narrationSegments'] = [{'id': 'n1', 'text': '一，', 'beatId': 'b1'}, {'id': 'n2', 'text': '二。', 'beatId': 'b2'}]
    # 单词事件必须覆盖完整文本，替身按真实顺序提供。
    async def two(text, voice, rate, output):
        tone(output); return [{'text':'一', 'start':.05, 'end':.2}, {'text':'二', 'start':.25, 'end':.4}]
    monkeypatch.setattr(prepare, 'synthesize', two)
    tone(tmp_path / 'bed.wav', .2)
    valid_script['soundtrack'] = {'music': {'sourceRef': 'bed.wav', 'loop': True, 'fadeInMs': 0, 'fadeOutMs': 0}}
    source = tmp_path / 'storyboard.json'; source.write_text(json.dumps(valid_script), encoding='utf-8')
    manifest = prepare.prepare(source, tmp_path / 'media'); before = manifest.read_bytes()
    media = load_media(manifest, source)
    assert audio.wav_duration(media.audio) == media.storyboard.total_frames / media.storyboard.fps
    stats = audio.loudness(media.audio); assert float(stats['input_tp']) <= -1
    (tmp_path / 'bed.wav').write_bytes(b'broken')
    with pytest.raises(A2VError, match='声音素材已变化'): load_media(manifest, source)
    with pytest.raises(A2VError): prepare.prepare(source, manifest.parent)
    assert manifest.read_bytes() == before

def test_duck_envelope_and_short_music(tmp_path):
    envelope = tmp_path / 'envelope.wav'
    audio.duck_envelope([{'start': .2, 'end': .5}], 1, envelope)
    with wave.open(str(envelope), 'rb') as stream:
        def sample(t):
            stream.setpos(round(t * 24000)); return struct.unpack('<h', stream.readframes(1))[0] / 32767
        assert sample(0) == 1
        assert sample(.3) == pytest.approx(10 ** (-10/20), abs=.0001)
        assert sample(.6) < sample(.7) < sample(.9)
    tone(tmp_path / 'voice.wav', 1); tone(tmp_path / 'bed.wav', .2)
    audio.mix(tmp_path / 'voice.wav', tmp_path / 'mix.wav', 1, [], (tmp_path / 'bed.wav', {'loop': False}), [(tmp_path / 'bed.wav', .9, -12)], tmp_path)
    assert audio.wav_duration(tmp_path / 'mix.wav') == 1

def test_content_missing_low_score_stale_and_rework():
    record = _ready_record(); source = {'scenes': [{'id': s} for s in ('open','core','close')]}; current = record['fingerprints']
    assert production.gate_for_status(record, source, current) is None
    content = record['reviews']['full'].pop('content')
    assert '口播内容' in production.gate_for_status(record, source, current)
    record['reviews']['full']['content'] = content
    content['dimensions']['boundary_accuracy']['score'] = 3
    assert '至少 4/5' in production.gate_for_status(record, source, current)
    content['dimensions']['boundary_accuracy']['score'] = 4
    record['materials']['rehearsal']['fingerprints'] = {**current, 'media':'old'}
    assert '过期' in production.gate_for_status(record, source, current)


def test_loudness_timeout_is_actionable(tmp_path, monkeypatch):
    def timeout(*args, **kwargs): raise subprocess.TimeoutExpired('ffmpeg', 300)
    monkeypatch.setattr(audio.subprocess, 'run', timeout)
    with pytest.raises(A2VError, match='响度量测超时'): audio.loudness(tmp_path / 'voice.wav')
