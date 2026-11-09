"""统一事件的边界、声画接线、准备指纹与混音回归。"""
import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core import frames
from m2v.core.project import load_current_prepared
from m2v.types.scene_film import adapter, code_scenes, explainer, scene_events, soundtrack
from helpers.scene_film import board, fake_record, fake_tts, project, scene, scene_root, requires_node, prepare_build

pytestmark = pytest.mark.media


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


@pytest.mark.slow
def test_real_compound_event_shift_and_local_capture(tmp_path):
    """独立工程真实Canvas：事件声画一起移动，局部/窗口采集像素一致。"""
    import os
    import textwrap
    from m2v.standalone.process import run

    root = Path(__file__).resolve().parents[3] / 'examples/data-evolution/compound-interest'
    python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file() or not (root/'node_modules/esbuild').exists():
        pytest.skip('需要先恢复compound-interest独立工程的本地Python/Node环境')
    # 使用作品自己的host/React上下文及字体，不把v3入口塞进旧共享SDK构建器。
    script = textwrap.dedent('''
        import json, sys
        from pathlib import Path
        from PIL import Image, ImageChops
        from playwright.sync_api import sync_playwright
        from film_runtime.engine.browser import configure
        from film_runtime.types.scene_film import code_scenes, scene_events
        from film_runtime.types.scene_film.code_scenes.config import copy_build_outputs

        configure()
        root, temporary = Path.cwd(), Path(sys.argv[1])
        source = json.loads((root/'storyboard.json').read_text(encoding='utf-8'))
        target = source['scenes'][0]
        duration, fps = target['durationFrames'], source['fps']
        target.update(startFrame=0, endFrame=duration, durationInFrames=duration, segmentWindows={})
        target['content']['props']['hideText'] = True
        first = next(event for event in target['events'] if event['id'] == 'drop-1')
        base, delay = first['frame'], 15
        events = {event['id']: event['frame'] for event in target['events']}
        scene_events.resolve([target])
        build = temporary/'build'
        build.mkdir()
        code_scenes.build_scene(root, target, build)
        geometry = {'width': 384, 'height': 216,
            'subtitle': {'safeArea': {'x': 0, 'y': 180, 'width': 384, 'height': 36}}}
        starts = {}
        with sync_playwright() as pw:
            for name, selected, shift in [('window', [base-1, base, base+delay], 0),
                                          ('local', [base], 0),
                                          ('shift', [base, base+delay-1, base+delay], delay)]:
                folder = temporary/name
                folder.mkdir()
                copy_build_outputs(build, folder)
                for event in target['events']:
                    event['frame'] = events[event['id']] + (shift if event['id'].startswith('drop-') else 3*shift)
                    if event['id'] == 'first-start':
                        # 只控制测试副本的微推相机：30/90 == 45/135。
                        # 比较落定相位时视角完全相同，不能让微推掩盖事件错帧。
                        event['frame'] = 3*(base+shift)
                target['events'].sort(key=lambda event: event['frame'])
                scene_events.resolve([target])
                config = code_scenes.scene_config(target, geometry, {}, fps=fps)
                code_scenes._capture(pw, root, folder, config, selected_frames=selected, verify_frames=2)
                starts[name] = scene_events.effect_starts(source['soundtrack']['effects'],
                    [target], fps, duration)[0]
        def pixels(name, frame=base):
            with Image.open(temporary/name/f'frame-{frame:06d}.png') as picture:
                return picture.convert('RGB')
        original = pixels('window')
        local_equal = ImageChops.difference(original, pixels('local')).getbbox() is None
        changed = ImageChops.difference(original, pixels('shift')).convert('L').histogram()
        landed_equal = ImageChops.difference(original, pixels('shift', base+delay)).getbbox() is None
        before_differs = all(ImageChops.difference(pixels(name, at-1), pixels(name, at)).getbbox()
            is not None for name, at in [('window', base), ('shift', base+delay)])
        print(json.dumps({'base': base, 'delay': delay, 'starts': starts,
            'localEqual': local_equal, 'landedEqual': landed_equal,
            'beforeDiffers': before_differs, 'changedPixels': sum(changed[3:])}))
    ''')
    lines = []
    result = run([str(python), '-c', script, str(tmp_path)], root, timeout=120, on_line=lines.append)
    assert result == 0, '\n'.join(lines)
    evidence = json.loads(lines[-1])
    assert evidence['localEqual']
    assert evidence['landedEqual']
    assert evidence['beforeDiffers']
    assert evidence['changedPixels'] > 20  # 排除少量GPU抗锯齿噪声，确认事件实际改变画面。
    assert evidence['starts'] == {'window': evidence['base'], 'local': evidence['base'],
                                  'shift': evidence['base'] + evidence['delay']}


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
