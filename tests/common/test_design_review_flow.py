"""关键帧和过程独立职责、明确采用、机械派生及纯静态交付边界。"""
from pathlib import Path

import pytest

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.production import issues, ledger, reviews, samples
from m2v.production.storage import read, write
from common.test_media_reviews import work, request, report  # noqa: F401
from common.test_native_samples import native, pair, process_pass  # noqa: F401


def test_old_request_and_mixed_keyframe_process_are_rejected(work):
    root, project = work
    old = request()
    old['version'] = 3
    with pytest.raises(M2VError, match='version=4'):
        reviews.package(root, project, old)
    mixed = request()
    mixed['items'][0].update(path='clip.mp4', dynamic=True)
    with pytest.raises(M2VError, match='关键帧'):
        reviews.package(root, project, mixed)


@pytest.mark.parametrize('where', ['overall', 'item'])
def test_adoption_cannot_hide_insufficient_evidence(work, where):
    root, project = work
    pack = reviews.package(root, project, request())
    path = report(work, pack, verdict='insufficient')
    value = read(path)
    (value if where == 'overall' else value['coverage'][0])['adoption'] = 'adopt'
    write(path, value)
    with pytest.raises(M2VError, match='采用结论'):
        reviews.import_report(root, project, path)


def test_generated_task_has_no_fabricated_call_or_pass(work):
    root, project = work
    pack = reviews.package(root, project, request())
    task = ledger.directory(root) / 'review-tasks' / pack.name
    template = read(task / 'report-template.json')
    invocation = read(task / 'invocation-template.json')
    assert template['adoption'] == 'reject' and template['verdict'] == 'insufficient'
    assert all(item['adoption'] == 'reject' for item in template['coverage'])
    assert not invocation['startedAt'] and not invocation['inputPaths']
    assert not template['reviewerId'] and not template['invocation']['sha256']
    with pytest.raises(M2VError):
        reviews.import_report(root, project, task / 'report-template.json')


def test_same_round_compare_copies_verified_frames_without_rederiving(work, monkeypatch):
    root, project = work
    req = request()
    req.update(references=['trial.png'], conditions=['相同主体品质'])
    blind_pack = reviews.package(root, project, req)
    blind = reviews.import_report(root, project, report(work, blind_pack))
    monkeypatch.setattr(reviews, 'derive_images', lambda *a, **kw: pytest.fail('同轮媒体不应重新取帧派生'))
    comparison = reviews.compare(root, project, blind['id'])
    original = (blind_pack / 'evidence-0000.png').read_bytes()
    assert (comparison / 'evidence-0000.png').read_bytes() == original
    (comparison / 'evidence-0000.png').write_bytes(b'changed copy')
    assert (blind_pack / 'evidence-0000.png').read_bytes() == original


def test_automatic_compare_preserves_sealed_targets_and_rejects_source_drift(work):
    root, project = work
    req = request()
    req.update(references=['trial.png'], conditions=['整体形象与空间品质'])
    blind = reviews.import_report(root, project, report(work, reviews.package(root, project, req)))
    comparison = reviews.compare(root, project, blind['id'])
    pack = read(comparison / 'manifest.json')
    assert pack['blindId'] == blind['id'] and (comparison / 'conditions.json').is_file()
    (root / 'core.tsx').write_text('changed', encoding='utf-8')
    with pytest.raises(M2VError, match='过期'):
        reviews.compare(root, project, blind['id'])


@pytest.mark.parametrize('change', [{'fps': 60}, {'displaySizes': [393]}, {'sampleStep': 2}])
def test_paired_comparison_cannot_change_timing_or_display_evidence(work, change):
    root, project = work
    req = request()
    req.update(references=['trial.png'], conditions=['相同观察条件'])
    blind = reviews.import_report(root, project, report(work, reviews.package(root, project, req)))
    req.update(reviewType='consistency', blindId=blind['id'], **change)
    with pytest.raises(M2VError, match='相同媒体'):
        reviews.package(root, project, req)


def test_final_is_retired_and_process_recheck_preserves_fps(work):
    root, project = work
    req = request()
    req.update(purpose='final')
    with pytest.raises(M2VError, match='keyframe 或 process'):
        reviews.package(root, project, req)
    scope = {'focus': 'comprehensive', 'purpose': 'process', 'reviewMode': 'process',
             'fps': 30, 'displaySizes': [393, 640], 'references': [], 'conditions': [],
             'sources': [], 'sceneIds': [], 'items': [{'id': 'motion', 'window': [0, 90], 'dynamic': True}]}
    assert not issues.covers(scope, {**scope, 'fps': 60})
    assert not reviews.has_visual_target({'references': ['sound.wav', 'music.mp3']})
    assert reviews.has_visual_target({'references': ['sound.wav', 'actual-frame.png']})


def test_process_comparison_is_independent_without_a_blind_report(native):
    root, project, identity = native
    pair(native)
    report_id = process_pass(native)
    result = reviews.current_report(root, project, report_id)
    assert result['reviewType'] == 'process' and result['purpose'] == 'process'
    assert 'blindId' not in result and not result['requiresComparison']
    request_value = read(outputs(root) / f'samples/{identity}/process-request.json')
    with pytest.raises(M2VError, match='实际参考'):
        reviews.package(root, project, request_value)
    request_value.update(reviewType='blind')
    with pytest.raises(M2VError):
        reviews.package(root, project, request_value)


def test_native_process_blind_reason_packages_a_blind_review_then_compares(native):
    root, project, identity = native
    value, _ = samples.load(root, project, identity)
    targets = {'references': [f"samples/{identity}/{value['stills'][0]['path']}"],
               'conditions': ['完整动作与对象的连续性']}
    blind_pack = samples.review(root, project, identity, purpose='process', targets=targets,
                                blind_reason='需要在提示前独立辨认发生连续变化的对象')
    assert read(blind_pack / 'manifest.json')['reviewType'] == 'blind'
    assert not (blind_pack / 'conditions.json').exists()
    accepted = reviews.import_report(root, project, report((root, project), blind_pack))
    comparison = reviews.compare(root, project, accepted['id'])
    manifest = read(comparison / 'manifest.json')
    assert manifest['reviewType'] == 'consistency' and manifest['purpose'] == 'process'
    assert (comparison / 'conditions.json').is_file()


def test_cli_builds_sample_task_and_derives_comparison_without_request_copy(native, capsys):
    import json
    from m2v import cli
    root, project, identity = native
    value, directory = samples.load(root, project, identity)
    targets = outputs(root) / 'targets.json'
    write(targets, {'references': [f"samples/{identity}/{value['stills'][0]['path']}"],
                    'conditions': ['仅测试真实目标与来源的机械绑定，不证明审美']})
    assert cli.main(['sample', 'review', '--project', str(root), '--id', identity,
                     '--purpose', 'keyframe', '--targets', str(targets)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert Path(result['reportTemplate']).is_file() and Path(result['task']).is_file()
    assert read(Path(result['reportTemplate']))['adoption'] == 'reject'
    pack = Path(result['path'])
    path = report((root, project), pack)
    assert cli.main(['review', 'import', '--project', str(root), '--file', str(path)]) == 0
    accepted = json.loads(capsys.readouterr().out)
    assert cli.main(['review', 'compare', '--project', str(root), '--blind-id', accepted['id']]) == 0
    comparison = json.loads(capsys.readouterr().out)
    assert read(Path(comparison['path']) / 'manifest.json')['blindId'] == accepted['id']
    assert Path(comparison['invocationTemplate']).is_file()


def test_process_failure_closes_only_with_current_matching_process(native):
    root, project, identity = native
    pair(native)
    targets = {'references': ['target.png'], 'conditions': ['完整状态与因果关系']}
    pack = samples.review(root, project, identity, purpose='process', targets=targets)
    reviews.import_report(root, project, report((root, project), pack, verdict='fail'))
    fresh = samples.capture(root, project)['id']
    accepted = reviews.import_report(root, project, report((root, project),
        samples.review(root, project, fresh, purpose='process', targets=targets)))
    problem = issues.load(root)[0]
    problem.update(status='closed', cause='implementation', closureReportId=accepted['id'])
    issues.update(root, problem)
    assert issues.load(root)[0]['status'] == 'closed'


def test_static_capture_delivers_images_without_a_video_or_process_claim(native):
    root, project, _ = native
    identity = samples.capture(root, project, kind='static')['id']
    args = pair((root, project, identity))
    value, directory = samples.load(root, project, identity)
    assert value['video'] is None and not list(directory.glob('*.mp4'))
    with pytest.raises(M2VError, match='静态采集'):
        samples.review(root, project, identity, purpose='process',
                       targets={'references': ['target.png'], 'conditions': ['未采集的过程']})
    result = samples.deliver(root, project, identity, **args)
    assert list(Path(result['path']).glob('*.png')) and not list(Path(result['path']).glob('*.mp4'))
    with pytest.raises(M2VError, match='静态样品'):
        samples.deliver(root, project, identity, **{**args, 'process_id': args['blind_id']})


@pytest.mark.parametrize('version', [3, ledger.VERSION + 1])
def test_version_downgrade_cannot_erase_current_native_failure(native, version):
    root, project, _ = native
    pair(native, verdict='fail')
    workflow = outputs(root) / 'production/workflow.json'
    original = read(workflow)
    write(workflow, {**original, 'version': version})
    with pytest.raises(M2VError, match='不能借版本升级'):
        ledger.start(root, project)
    assert read(workflow)['cycleId'] == original['cycleId']
    write(workflow, original)
    assert all(item['status'] == 'open' for item in issues.load(root))


def test_generic_keyframe_failure_cannot_be_erased_by_a_new_cycle(work):
    root, project = work
    reviews.import_report(root, project, report(work, reviews.package(root, project, request()), verdict='fail'))
    before = ledger.cycle(root)
    with pytest.raises(M2VError, match='不能重开周期'):
        ledger.start(root, project)
    assert ledger.cycle(root) == before and issues.load(root)[0]['status'] == 'open'


def test_review_task_directory_link_cannot_write_outside_project(work, tmp_path):
    root, project = work
    outside = tmp_path / 'outside'
    outside.mkdir()
    tasks = ledger.directory(root) / 'review-tasks'
    try:
        tasks.symlink_to(outside, target_is_directory=True)
    except OSError:
        import os
        if os.name != 'nt':
            pytest.skip('当前环境不能创建目录链接')
        import _winapi
        _winapi.CreateJunction(str(outside), str(tasks))
    with pytest.raises(M2VError, match='链接|越界'):
        reviews.package(root, project, request())
    assert not list(outside.iterdir())
