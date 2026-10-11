"""分段语音与混音契约：离线替身仅用于测试，不充作真实样片评审。"""
import copy
import json
import math
import re
import struct
import wave
import subprocess
from pathlib import Path

import pytest
import m2v.engine.audio as audio
import m2v.types.article.prepare as prepare
import m2v.types.article.production as production
import m2v.types.article.storyboard as storyboard
import m2v.engine.sound as sound
from m2v.core.errors import M2VError
from m2v.types.article.media import load_media
from test_production_workflow import _ready_record

def tone(path, duration=.5):
    with wave.open(str(path), 'wb') as out:
        out.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        out.writeframes(b''.join(struct.pack('<h', round(6000 * math.sin(2 * math.pi * 400 * n / 24000))) for n in range(round(duration * 24000))))

def stage_speech(calls=None, char_seconds=.25):
    """v4 逐 stage 合成的离线替身：每个字 0.25 秒，且词边界覆盖完整口播。

    v4 的 ``prepare`` 只按 stage 的**拼接后文本**合成一次，再按真实词边界派生
    时长与节拍；替身必须返回文本里全部文字、时间单调且落在音轨内。
    """
    async def fake(text, voice, rate, output):
        if calls is not None:
            calls.append((text, voice, rate))
        tokens = re.findall(r"[\w\u4e00-\u9fff]", text)
        tone(output, .3 + len(tokens) * char_seconds)
        return [{"text": token, "start": .1 + index * char_seconds, "end": .2 + index * char_seconds}
                for index, token in enumerate(tokens)]
    return fake

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

def test_stage_speech_cache_and_legacy_manifest(tmp_path, valid_script_v4, monkeypatch):
    """v4 以 stage 为单位合成：缓存键覆盖 stage 文本，旧清单必须被拒绝并要求重做。

    v4 已删除逐段 ``speech``（rate/pauseBeforeMs/pauseAfterMs）：整段 stage 文本
    一次合成，逐段停顿与语速不再参与时间轴，因此这里断言「同一 stage 文本命中
    缓存、只有被改写的 stage 重新合成」，取代旧的逐段停顿偏移断言。
    """
    calls = []
    monkeypatch.setattr(prepare, 'synthesize', stage_speech(calls))
    texts = [''.join(segment['text'] for segment in stage['narrationSegments']) for stage in valid_script_v4['stages']]
    source = tmp_path / 'storyboard.json'; source.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding='utf-8')
    manifest = prepare.prepare(source, tmp_path / 'media')
    media = load_media(manifest, source)
    # 每条 stage 一次合成：缓存键就是该 stage 的完整口播文本。
    assert [text for text, _, _ in calls] == texts
    # 字幕起于真实词边界；画面 beat 与字幕共用同一批边界（容一帧取整）。
    assert media.data['cues'][0]['start'] == pytest.approx(.1)
    assert media.data['resolvedBeats'][0]['startFrame'] == pytest.approx(media.data['cues'][0]['start'] * media.storyboard.fps, abs=1)
    # 口播文本未变：重新 prepare 全部命中缓存，不重复请求配音。
    valid_script_v4['stages'][0]['beats'][1]['meaning'] = '把注意力移向落点与靶心'
    source.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding='utf-8')
    prepare.prepare(source, manifest.parent)
    assert [text for text, _, _ in calls] == texts
    # 只有被改写的 stage 重新合成，其余 stage 仍命中缓存。
    valid_script_v4['stages'][0]['narrationSegments'][0]['text'] = '先看一次成本极高的投掷，落点马上就能看见。'
    changed = ''.join(segment['text'] for segment in valid_script_v4['stages'][0]['narrationSegments'])
    source.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding='utf-8')
    prepare.prepare(source, manifest.parent)
    assert [text for text, _, _ in calls] == texts + [changed]
    # v1–v3 旧媒体清单一律拒绝：入口不读取、不降级，只要求重新 prepare。
    old = json.loads(manifest.read_text(encoding='utf-8')); old['version'] = 2
    manifest.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(M2VError, match='v4 分镜的媒体清单版本过旧，请重新 prepare'):
        load_media(manifest, source)
    # v1–v3 分镜同样不被接受：只回一条可执行的诊断。
    legacy = copy.deepcopy(valid_script_v4); legacy['version'] = legacy['schemaVersion'] = 3
    source.write_text(json.dumps(legacy, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(M2VError, match='不支持 v4 之前分镜；请按分镜 v4 契约重新编排'):
        prepare.prepare(source, manifest.parent)

def test_mix_loop_duck_and_failure_preserves_manifest(tmp_path, valid_script_v4, monkeypatch):
    monkeypatch.setattr(prepare, 'synthesize', stage_speech())
    tone(tmp_path / 'bed.wav', .2)
    valid_script_v4['soundtrack'] = {'music': {'sourceRef': 'bed.wav', 'loop': True, 'fadeInMs': 0, 'fadeOutMs': 0}}
    source = tmp_path / 'storyboard.json'; source.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding='utf-8')
    manifest = prepare.prepare(source, tmp_path); before = manifest.read_bytes()
    media = load_media(manifest, source)
    assert audio.wav_duration(media.audio) == media.storyboard.total_frames / media.storyboard.fps
    stats = audio.loudness(media.audio); assert float(stats['input_tp']) <= -1
    (tmp_path / 'bed.wav').write_bytes(b'broken')
    with pytest.raises(M2VError, match='声音素材已变化'): load_media(manifest, source)
    with pytest.raises(M2VError): prepare.prepare(source, manifest.parent)
    assert manifest.read_bytes() == before

def test_sound_assets_resolve_outside_the_media_directory(tmp_path, valid_script_v4, monkeypatch):
    """作品目录里的素材 + `outputs/media/` 里的清单：素材按分镜目录解析。

    真实布局下素材留在作品目录（`assets/`），媒体写在 `outputs/media/`；
    若按清单目录解析，记录下来的 `../../assets/...` 会被判成越界，
    任何带声音的作品都读不回清单。
    """
    article = tmp_path / 'videos' / 'demo'
    (article / 'assets').mkdir(parents=True)
    monkeypatch.setattr(prepare, 'synthesize', stage_speech())
    tone(article / 'assets' / 'bed.wav', .2)
    valid_script_v4['soundtrack'] = {'music': {'sourceRef': 'assets/bed.wav', 'loop': True}}
    source = article / 'storyboard.json'
    source.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding='utf-8')
    manifest = prepare.prepare(source, article / 'outputs' / 'media')
    assert json.loads(manifest.read_text(encoding='utf-8'))['soundAssets']['assets/bed.wav']['path'] \
        == 'assets/bed.wav'
    media = load_media(manifest, source)
    assert media.audio.is_file()

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
    with pytest.raises(M2VError, match='响度量测超时'): audio.loudness(tmp_path / 'voice.wav')
