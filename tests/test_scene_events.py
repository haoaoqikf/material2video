"""统一事件的边界、声画接线、准备指纹与混音回归。"""
import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core import frames
from m2v.core.project import load_current_prepared
from m2v.types.general import adapter, code_scenes, explainer, scene_events, soundtrack
from _helpers import board, fake_record, fake_tts, project, scene, scene_root, requires_node, prepare_build


@pytest.mark.parametrize('events', [None, {}, [{'id': '', 'frame': 0}],
    [{'id': 'x', 'frame': True}], [{'id': 'x', 'frame': 1.5}],
    [{'id': 'x', 'frame': -1}], [{'id': 'x', 'frame': 100}],
    [{'id': 'x', 'frame': 0}, {'id': 'x', 'frame': 1}],
    [{'id': 'x', 'frame': 0, 'extra': 0}], [{'id': 'x', 'frame': 0}] * 1025])
def test_invalid_events(tmp_path, events):
    with pytest.raises(M2VError):
        explainer.validate(board(scenes=[scene(events=events, durationFrames=100)]), scene_root(tmp_path))


@pytest.mark.parametrize('extra', [{'eventId': 'missing'}, {'eventId': []},
    {'eventId': 'hit', 'segmentId': 'a-line'}, {'eventId': 'hit', 'offsetMs': 0}])
def test_bad_reference(tmp_path, extra):
    data = board(scenes=[scene(events=[{'id': 'hit', 'frame': 0}])],
                 soundtrack={'effects': [{'builtin': 'click', 'sceneId': 'a', **extra}]})
    with pytest.raises(M2VError):
        explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize('fps', [30, 60])
def test_scene_moves_event_and_sound_together(tmp_path, monkeypatch, fps):
    compiled = [{'id': 'a', 'startFrame': 100, 'durationInFrames': 120,
                 'segmentWindows': {}, 'events': [{'id': 'hit', 'frame': 30}]}]
    effects = [{'builtin': 'click', 'sceneId': 'a', 'eventId': 'hit', 'offsetFrames': -2}]
    rows = scene_events.resolve(compiled)
    assert rows[0]['globalFrame'] == 130
    starts = scene_events.effect_starts(effects, compiled, fps, 220)
    assert starts == [128]
    observed = []
    monkeypatch.setattr(soundtrack.audio, 'mix', lambda *args, **kwargs: observed.append(args[5][0].start))
    soundtrack.mix(tmp_path, {'fps': fps, 'soundtrack': {'effects': effects}}, compiled,
                   tmp_path/'raw.wav', tmp_path/'out.wav', [], 220/fps, tmp_path, {}, effect_start_frames=starts)
    assert observed == [128/fps]
    compiled[0]['startFrame'] += 15
    assert scene_events.resolve(compiled)[0]['globalFrame'] == 145
    assert scene_events.effect_starts(effects, compiled, fps, 235) == [143]
    for offset in [-31, 90]:
        with pytest.raises(M2VError, match='所属幕'):
            scene_events.effect_starts([{**effects[0], 'offsetFrames': offset}], compiled, fps, 235)


def test_prepare_rebinds_report_audio_and_scene_cache(tmp_path, monkeypatch):
    data = board(scenes=[scene(events=[{'id': 'hit', 'frame': 15}])],
                 soundtrack={'effects': [{'builtin': 'click', 'sceneId': 'a', 'eventId': 'hit'}]})
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    first = adapter.prepare(root, manifest)
    first_config = code_scenes.scene_config(first['props']['compiledScenes'][0], frames.spec(1920, 1080), {})
    assert first_config['eventFrames'] == {'hit': 15}
    data['scenes'][0]['events'][0]['frame'] += 15
    (root/'storyboard.json').write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(M2VError):
        load_current_prepared(root, manifest)
    second = adapter.prepare(root, manifest)
    assert second['preparedFingerprint'] != first['preparedFingerprint']
    assert second['audio']['segments'][0]['sha256'] != first['audio']['segments'][0]['sha256']
    assert second['props']['effectStartFrames'] == [30]
    assert first['props']['effectStartFrames'] == [15]
    second_config = code_scenes.scene_config(second['props']['compiledScenes'][0], frames.spec(1920, 1080), {})
    assert second_config != first_config
    report = json.loads((root/'outputs/events.json').read_text(encoding='utf-8'))
    assert report['preparedFingerprint'] == second['preparedFingerprint']
    assert report['events'] == [{'sceneId': 'a', 'id': 'hit', 'frame': 30, 'globalFrame': 30}]
    assert report['effects'][0]['globalFrame'] == 30


def test_prepare_rejects_event_beyond_automatic_duration(tmp_path, monkeypatch):
    root, manifest = project(tmp_path, board(scenes=[scene(events=[{'id': 'late', 'frame': 1000}])]))
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    with pytest.raises(M2VError, match='超出本幕时长'):
        adapter.prepare(root, manifest)


@requires_node
@pytest.mark.slow
def test_real_compound_event_shift_and_local_capture(tmp_path, chromium_ready):
    """真实示例：落点和声音移动15帧；局部取帧与较长窗口同帧像素一致。"""
    from playwright.sync_api import sync_playwright
    root = Path(__file__).resolve().parents[1] / 'styles/examples/count-ledger/compound-interest'
    source = json.loads((root/'storyboard.json').read_text(encoding='utf-8'))
    target = source['scenes'][0]
    target.update(startFrame=0, durationInFrames=870, segmentWindows={})
    target['content']['props']['hideText'] = True
    scene_events.resolve([target])
    work = tmp_path/'build'
    work.mkdir()
    code_scenes.build_scene(root, target, work)
    geometry = {'width': 384, 'height': 216, 'subtitle': {'safeArea': {'x': 0, 'y': 180, 'width': 384, 'height': 36}}}
    snapshots = []
    with sync_playwright() as pw:
        for name, selected, shift in [('window', [29, 30, 44, 45], 0), ('local', [30], 0), ('shift', [44, 45], 15)]:
            folder = tmp_path/name
            folder.mkdir()
            (folder/'scene.js').write_bytes((work/'scene.js').read_bytes())
            target['events'][0]['frame'] = 30 + shift
            scene_events.resolve([target])
            config = code_scenes.scene_config(target, geometry, {}, fps=30)
            observed = {}
            code_scenes._capture(pw, root, folder, config, selected_frames=selected,
                observe=lambda page, frame: observed.update({frame: float(page.locator('[data-m2v-role="disc"]').first.get_attribute('cy'))}))
            starts = scene_events.effect_starts(source['soundtrack']['effects'], [target], 30, 870)
            assert starts[0] == 30 + shift
            snapshots.append(observed)
    assert snapshots[0][29] < 900
    assert snapshots[0][30] == pytest.approx(900)
    assert snapshots[2][44] < 900
    assert snapshots[2][45] == pytest.approx(900)
    assert snapshots[0][30] == snapshots[1][30]
    assert (tmp_path/'window/frame-000030.png').read_bytes() == (tmp_path/'local/frame-000030.png').read_bytes()


@requires_node
@pytest.mark.slow
def test_browser_event_state_and_special_ids(tmp_path, chromium_ready):
    """配置传输保留特殊字典键；实际DOM的动作、计数和强调共同移动。"""
    from playwright.sync_api import sync_playwright
    root, work, built = prepare_build(tmp_path, '''
import {useEffect, useMemo} from 'react';
import {createSceneEvents, useSceneContext} from 'm2v/code-scene';
export default function Demo(config) {
  const clock = useSceneContext();
  useEffect(() => {clock.ready();}, []);
  const events = useMemo(() => createSceneEvents(config.eventFrames), [config.eventFrames]);
  const frame = clock.elapsedSeconds * config.fps;
  const hit = events.frame('__proto__');
  const p = events.progress('__proto__', frame, 6, -6);
  const active = frame >= hit;
  return <div id="state" data-x={p} data-count={Number(active)}
    data-emphasis={active ? 1 - events.progress('__proto__', frame, 6) : 0}
    data-special={events.frame('</script>')} style={{width:160,height:90,background:'#000'}}>
    <div style={{width:10,height:10,background:active?'#ff0':'#fff',transform:`translateX(${p*100}px)`}}/>
  </div>;
}''')
    assert built.returncode == 0, built.stderr
    target = {'id': 'a', 'startFrame': 0, 'durationInFrames': 30, 'segmentWindows': {},
              'content': {'props': {}}, 'events': []}
    geometry = {'width': 160, 'height': 90, 'subtitle': {'safeArea': {'x': 0, 'y': 70, 'width': 160, 'height': 20}}}
    snapshots = []
    with sync_playwright() as pw:
        for shift in [0, 15]:
            target['events'] = [{'id': '__proto__', 'frame': 9 + shift}, {'id': '</script>', 'frame': 0}]
            scene_events.resolve([target])
            folder = tmp_path/f'special-{shift}'
            folder.mkdir()
            (folder/'scene.js').write_bytes((work/'scene.js').read_bytes())
            observed = {}
            code_scenes._capture(pw, root, folder, code_scenes.scene_config(target, geometry, {}, fps=30),
                selected_frames=[8 + shift, 9 + shift, 10 + shift],
                observe=lambda page, frame: observed.update({frame - shift: page.locator('#state').evaluate(
                    '(el) => [el.dataset.x,el.dataset.count,el.dataset.emphasis,el.dataset.special]')}))
            assert scene_events.effect_starts([{'sceneId': 'a', 'eventId': '__proto__'}], [target], 30, 30) == [9 + shift]
            snapshots.append(observed)
    for frame in [8, 9, 10]:
        assert list(map(float, snapshots[0][frame])) == pytest.approx(list(map(float, snapshots[1][frame])))
    assert list(map(float, snapshots[0][9])) == [1, 1, 1, 0]


def test_event_coverage_reports_actual_spacing_and_missed_frames():
    """采样步长与事件密度分开报告；诊断不进入 checks 状态。"""
    from m2v.production.checks import event_coverage

    prepared = {'props': {'resolvedEvents': [
        {'sceneId': 'compound', 'id': 'drop-1', 'frame': 30, 'globalFrame': 30},
        {'sceneId': 'compound', 'id': 'drop-2', 'frame': 33, 'globalFrame': 33},
        {'sceneId': 'compound', 'id': 'drop-3', 'frame': 35, 'globalFrame': 35}]}}
    scene = {'id': 'compound'}
    checkpoint = {'window': [0, 105], 'sampleStep': 15}
    coverage = event_coverage(prepared, scene, checkpoint, [0, 15, 30, 45, 60, 75, 90, 100, 104])
    assert coverage['eventFrames'] == [30, 33, 35]
    assert coverage['sampledFrames'] == [30]
    assert coverage['missedFrames'] == [33, 35]
    assert coverage['minSpacing'] == 2
    assert coverage['sampleStep'] == 15
    assert coverage['warning'] is True
    assert event_coverage({'props': {}}, scene, checkpoint, []) is None


def test_event_coverage_is_quiet_when_every_event_is_sampled():
    from m2v.production.checks import event_coverage

    prepared = {'props': {'resolvedEvents': [
        {'sceneId': 'a', 'id': 'hit', 'frame': 10, 'globalFrame': 10}]}}
    coverage = event_coverage(prepared, {'id': 'a'}, {'window': [0, 20], 'sampleStep': 1}, [10])
    assert coverage['warning'] is False
    assert coverage['missedFrames'] == []
