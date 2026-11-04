"""时序证据范围、复用依赖与失效后的独立闭环。"""
import json

from PIL import Image
import pytest

from helpers.production import project as production_project
from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.production import checks, contract, issues, ledger, timing
from m2v.production.storage import read, receipt, write


@pytest.fixture
def project(tmp_path):
    root, manifest, c = production_project(tmp_path)
    shot = c['scenes'][0]['shots'][0]
    shot['timeStructure'] = {'result': {'window': [0, 30], 'audience': '结果', 'visible': '主体',
        'attention': '主体', 'toleranceFrames': 1, 'failure': '结果不可辨'}}
    c['reviewPlan']['risks'] = [{'id': 'timing', 'kind': 'structure-timing', 'scope': {'checkpointIds': ['one-cp']},
        'reason': '变化与结果时点', 'requiredEvidence': ['完整过程']}]
    (root / 'DESIGN.md').write_text('```m2v-checkpoints\n' + json.dumps(c) + '\n```\n', encoding='utf-8')
    return root, manifest, c


def capture_report(root, c, *, seconds=1):
    base = outputs(root)
    directory = base / 'production/checkpoints/one-cp'
    directory.mkdir(parents=True, exist_ok=True)
    clip = directory / 'window.mp4'
    checks.ffmpeg(['-f', 'lavfi', '-i', f'color=c=blue:s=64x64:r=30:d={seconds}',
                   '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(clip)])
    measurement = directory / 'measurements.json'
    write(measurement, {'window': [0, 30], 'capture': 'browser-selected-frames',
        'cacheSource': {'path': 'code-cache/current.mp4', 'startFrame': 0, 'endFrame': 30}})
    return checks.save_report(root, c, 'G4', [{'name': '量测', 'status': 'unverified', 'detail': '只复用过程'}],
        scene_id='one', checkpoint_id='one-cp', evidence=[receipt(base, clip), receipt(base, measurement)])


@pytest.mark.media
def test_reuse_binds_actual_sources_and_expires_after_source_edit(project, monkeypatch):
    root, manifest, c = project
    path = capture_report(root, c)
    references = [path.relative_to(outputs(root)).as_posix()]
    monkeypatch.setattr(checks, 'make_animatic', lambda *_: pytest.fail('不应重复生成 animatic'))
    report_path = checks.run(root, manifest, 'G3', timing_reports=references)[0]
    report = read(report_path)
    assert report['status'] == 'pass' and report['upstream']['timingReports'] == references
    assert not (outputs(root) / 'production/animatic').exists()
    event = ledger.register(root, manifest, report_path)
    assert event['upstream'] == ledger.event_upstream(root, c, event)
    assert read(path)['status'] == 'unverified'  # 不继承 G4 通过
    assert ledger.status(root, manifest)['gates'][3]['evidenceStatus'] == '待评审'
    (root / 'scenes/one.tsx').write_text('export default 2;', encoding='utf-8')
    assert ledger.status(root, manifest)['gates'][3]['evidenceStatus'] == '过期'
    with pytest.raises(M2VError, match='过期'):
        ledger.register(root, manifest, report_path)


@pytest.mark.media
@pytest.mark.parametrize('mutation', ['short', 'window', 'hash', 'coverage', 'malformed'])
def test_reuse_rejects_insufficient_or_stale_capture(project, mutation):
    root, manifest, c = project
    path = capture_report(root, c, seconds=.2 if mutation == 'short' else 1)
    references = [path.relative_to(outputs(root)).as_posix()]
    if mutation == 'window':
        data = read(path)
        measurement = outputs(root) / 'production/checkpoints/one-cp/measurements.json'
        value = read(measurement); value['window'] = [1, 30]; write(measurement, value)
        data['evidence'] = [receipt(outputs(root), outputs(root) / e['path']) for e in data['evidence']]
        write(path, data)
    elif mutation == 'hash':
        (outputs(root) / 'production/checkpoints/one-cp/window.mp4').write_bytes(b'changed')
    elif mutation == 'coverage':
        references = []
    elif mutation == 'malformed':
        write(path, [])
    with pytest.raises(M2VError):
        checks.run(root, manifest, 'G3', timing_reports=references)


@pytest.mark.media
def test_animatic_limits_scope_and_maps_original_windows(project):
    root, manifest, c = project
    import copy
    for index in range(3, 7):
        scene = copy.deepcopy(c['scenes'][1])
        scene['id'] = f's{index}'
        scene['shots'][0]['id'] = f'q{index}'
        scene['checkpoints'][0].update(id=f'cp{index}', shotId=f'q{index}')
        c['scenes'].append(scene)
    image = outputs(root) / 'frame.png'
    Image.new('RGB', (192, 108), 'blue').save(image)
    write(outputs(root) / 'production/design-frames.json', {'frames': [
        {'checkpointId': cp['id'], 'width': 1920, 'path': 'frame.png', 'phase': 'result'}
        for _, _, cp in contract.checkpoints(c)]})
    clip = timing.make_animatic(root, c)
    coverage = read(clip.with_name('manifest.json'))['coverage']
    assert {item['sceneId'] for item in coverage} == {'one', 'two'}
    assert coverage[0]['window'] == [0, 30] and coverage[0]['outputWindow'] == [0, 30]
    assert coverage[1]['outputWindow'] == [30, 60] and coverage[1]['contextOnly']
    from imageio_ffmpeg import count_frames_and_secs
    frames, seconds = count_frames_and_secs(str(clip))
    assert frames == 60 and abs(seconds - 2.0) < .05
    assert read(clip.with_name('manifest.json'))['nonDelivery']


def test_expired_historical_recheck_does_not_hide_new_valid_recheck(project, monkeypatch):
    root, _, c = project
    original = {'type': 'review', 'gate': 'G3', 'sceneId': None, 'checkpointId': None, 'time': '1',
        'data': {'verdict': 'fail', 'roundId': 'first', 'reviewerId': 'R1', 'reviewType': 'blind',
                 'coverage': [{'checkpointId': 'one-cp'}]}}
    good = {'type': 'review', 'gate': 'G3', 'sceneId': None, 'checkpointId': None, 'time': '3',
        'upstream': {'current': True}, 'evidence': [{'path': 'good.json', 'sha256': 'pass'}],
        'data': {'verdict': 'pass', 'round': 'core', 'isolation': 'independent-subagent', 'reviewType': 'blind',
                 'reportId': 'pass', 'coverage': [{'checkpointId': 'one-cp', 'status': 'pass', 'assessment': {
                     name: {'status': 'pass', 'observations': '当前观察'}
                     for name in ('understanding', 'presentation', 'representativeness')}}]}}
    stale = {**good, 'time': '2'}
    def upstream(root, c, event):
        if event is stale:
            raise M2VError('历史时序来源已过期')
        return {'current': True}
    monkeypatch.setattr(ledger, 'event_upstream', upstream)
    monkeypatch.setattr(ledger, 'evidence_valid', lambda *_: True)
    item = {'id': 'REVIEW-first-R1', 'gate': 'G3', 'sceneId': None,
            'evidence': [{'path': 'good.json', 'sha256': 'pass', 'gate': 'G3'}]}
    issues._require_independent_recheck(root, item, ([original, stale, good], c, []))


def test_malformed_report_upstream_is_a_contract_error(project):
    root, manifest, c = project
    path = checks.save_report(root, c, 'G1', [{'name': '声明', 'status': 'pass', 'detail': 'fixture'}])
    report = read(path)
    report['upstream'] = []
    write(path, report)
    with pytest.raises(M2VError, match='上游必须为对象'):
        ledger.register(root, manifest, path)
