"""本地样品须绑定真实来源、窗口、网页与产物，伪造的成功不能写采集事件。"""
import json

from PIL import Image
import pytest

from m2v.core.delivery import digest
from m2v.core.errors import M2VError
from m2v.engine import design_sample
from m2v.standalone import executor
from standalone.test_management_bindings import prepared_work


@pytest.fixture
def packet(tmp_path, monkeypatch):
    project, _ = prepared_work(tmp_path)
    project['output'].update(width=640, height=360)
    (tmp_path / 'project.json').write_text(json.dumps(project), encoding='utf-8')
    scene = tmp_path / 'scenes/main.tsx'
    scene.parent.mkdir()
    scene.write_text('export default () => null;', encoding='utf-8')
    target = tmp_path / 'outputs/samples/private'
    target.mkdir(parents=True)
    Image.new('RGB', (640, 360), 'blue').save(target / 'still-000001.png')
    (target / 'sample.mp4').write_bytes(b'encoded-video')
    for name in ['index.html', 'scene.html', 'capture-clock.js']:
        (target / 'web').mkdir(exist_ok=True)
        (target / 'web' / name).write_text('native viewer', encoding='utf-8')
    value = {'entry': 'scenes/main.tsx', 'props': {}, 'fps': 30, 'width': 640, 'height': 360,
             'durationInFrames': 3, 'stills': [{'frame': 1, 'path': 'still-000001.png'}],
             'video': 'sample.mp4', 'inputs': design_sample.snapshot(tmp_path, [scene, tmp_path / 'project.json']),
             'config': {'media': {}, 'props': {}, 'width': 640, 'height': 360, 'fps': 30, 'durationInFrames': 3},
             'project': {key: project.get(key) for key in ('id', 'type', 'output')}, 'determinism': [],
             'artifacts': {p.relative_to(target).as_posix(): digest(p) for p in target.rglob('*') if p.is_file()}}
    calls = []
    def execute(root, project, action, options):
        calls.append((action, options))
        (target / 'capture.json').write_text(json.dumps(value), encoding='utf-8')
        return {'status': 'captured', 'path': 'outputs/samples/private/capture.json'}
    monkeypatch.setattr(executor, 'execute', execute)
    monkeypatch.setattr(design_sample, 'verify_output', lambda *a, **kw: None)
    return tmp_path, project, target, value, calls


def capture(packet):
    root, project, target, _, _ = packet
    return design_sample.render(root, project, target, entry='scenes/main.tsx', props={},
                                duration_seconds=.1, still_frames=[1])


def test_sample_delegates_local_destination_and_accepts_verified_packet(packet):
    value = capture(packet)
    assert value['entry'] == 'scenes/main.tsx'
    assert 'artifacts' not in value
    action, options = packet[-1][0]
    assert action == 'sample'
    assert options[options.index('--destination') + 1] == 'outputs/samples/private'


@pytest.mark.parametrize('damage', ['entry', 'dimension', 'source', 'artifact', 'frame',
                                   'missing-source', 'missing-web', 'external-scope', 'unknown-field',
                                   'visible-props', 'omitted-import', 'unregistered-media',
                                   'capture-mode', 'time-origin'])
def test_invalid_local_sample_is_rejected(packet, damage):
    root, _, target, value, _ = packet
    if damage == 'entry':
        value['entry'] = 'scenes/other.tsx'
    elif damage == 'dimension':
        value.update(width=320)
        value['config']['width'] = 320
    elif damage == 'source':
        (root / 'scenes/main.tsx').write_text('changed', encoding='utf-8')
    elif damage == 'artifact':
        (target / 'sample.mp4').write_bytes(b'different')
    elif damage == 'frame':
        value['stills'][0]['frame'] = 2
    elif damage == 'missing-source':
        del value['inputs']['work/project.json']
    elif damage == 'missing-web':
        del value['artifacts']['web/scene.html']
    elif damage == 'external-scope':
        value['inputs']['repo/shared.py'] = 'claimed'
    elif damage == 'visible-props':
        value['config']['props'] = {'title': 'different from requested props'}
    elif damage == 'omitted-import':
        helper = root / 'scenes/imported.ts'
        helper.write_text('export const value=1;', encoding='utf-8')
        (root / 'scenes/main.tsx').write_text('import {value} from "./imported"; export default value;', encoding='utf-8')
        value['inputs']['work/scenes/main.tsx'] = digest(root / 'scenes/main.tsx')
    elif damage == 'unregistered-media':
        (root / 'assets/media').mkdir(parents=True)
        (root / 'assets/media/private.mp4').write_bytes(b'unregistered')
        value['config']['media'] = {'private': {'src': '/media/private.mp4', 'kind': 'video'}}
    elif damage == 'capture-mode':
        value['config']['captureMode'] = 'pure-time'
    elif damage == 'time-origin':
        value['config']['timeline'] = {'sceneStartFrame': 900, 'sceneEndFrame': 903, 'durationInFrames': 3}
    else:
        value['id'] = 'cannot-override-ledger-identity'
    with pytest.raises(M2VError):
        capture(packet)


@pytest.mark.parametrize('kind', ['source', 'artifact'])
def test_edit_during_independent_verification_is_rejected(packet, monkeypatch, kind):
    root, _, target, _, _ = packet
    def edit(*args, **kwargs):
        file = root / 'project.json' if kind == 'source' else target / 'sample.mp4'
        file.write_bytes(b'changed-during-check')
    monkeypatch.setattr(design_sample, 'verify_output', edit)
    with pytest.raises(M2VError, match='验证期间'):
        capture(packet)


@pytest.mark.parametrize('kind', ['project', 'props'])
def test_local_process_cannot_rebind_changed_request_inputs_to_old_configuration(packet, monkeypatch, kind):
    root, project, target, value, _ = packet
    props_file = root / 'props.json'
    props_file.write_text('{}', encoding='utf-8')
    value['inputs']['work/props.json'] = digest(props_file)
    original = executor.execute
    def changed(*args, **kwargs):
        if kind == 'project':
            updated = json.loads((root / 'project.json').read_text(encoding='utf-8'))
            updated['output']['width'] = 1280
            (root / 'project.json').write_text(json.dumps(updated), encoding='utf-8')
            value['inputs']['work/project.json'] = digest(root / 'project.json')
        else:
            props_file.write_text('{"title":"edited"}', encoding='utf-8')
            value['inputs']['work/props.json'] = digest(props_file)
        return original(*args, **kwargs)
    monkeypatch.setattr(executor, 'execute', changed)
    with pytest.raises(M2VError, match='来源|参数|描述'):
        design_sample.render(root, project, target, entry='scenes/main.tsx', props={},
                             duration_seconds=.1, still_frames=[1], props_source='props.json')
