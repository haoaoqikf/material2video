"""关键帧和过程独立职责、明确采用、机械派生及纯静态交付边界。"""
from pathlib import Path
from shutil import copyfile

import pytest

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.production import issues, ledger, reviews, samples
from m2v.production.storage import read, write
from common.test_media_reviews import work, request, report  # noqa: F401
from common.test_native_samples import native, pair  # noqa: F401


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


@pytest.mark.parametrize('legacy_blind', [False, True], ids=['native-path', 'legacy-copy'])
def test_same_round_compare_copies_verified_frames_without_rederiving(work, monkeypatch, legacy_blind):
    root, project = work
    req = request()
    req.update(references=['trial.png'], conditions=['相同主体品质'])
    native = 'evidence-0000.png'
    duplicate = 'evidence-0000-640.png'
    phone = 'evidence-0000-393.png'
    derive_images = reviews.derive_images

    def legacy_derivation(source, widths):
        paths = derive_images(source, widths)
        legacy_path = source.with_name(duplicate)
        copyfile(source, legacy_path)
        return [legacy_path if path == source else path for path in paths]

    with monkeypatch.context() as scope:
        if legacy_blind:
            scope.setattr(reviews, 'derive_images', legacy_derivation)
        blind_pack = reviews.package(root, project, req)
    blind_manifest = read(blind_pack / 'manifest.json')
    blind_frame = blind_manifest['items'][0]['sequence'][0]
    assert blind_frame['displayPaths'] == [duplicate if legacy_blind else native, phone]
    assert (blind_pack / duplicate).is_file() == legacy_blind
    blind = reviews.import_report(root, project, report(work, blind_pack))
    monkeypatch.setattr(reviews, 'derive_images', lambda *a, **kw: pytest.fail('同轮媒体不应重新取帧派生'))
    comparison = reviews.compare(root, project, blind['id'])
    comparison_manifest = read(comparison / 'manifest.json')
    frame = comparison_manifest['items'][0]['sequence'][0]
    assert frame['path'] == native and frame['displayPaths'] == [native, phone]
    sealed_paths = [record['path'] for record in comparison_manifest['files']]
    assert sealed_paths.count(native) == 1 and duplicate not in sealed_paths
    assert not (comparison / duplicate).exists()
    assert (comparison / phone).read_bytes() == (blind_pack / phone).read_bytes()
    original = (blind_pack / native).read_bytes()
    assert (comparison / native).read_bytes() == original
    assert ledger.evidence_valid_at(comparison, comparison_manifest['files'])
    (comparison / native).write_bytes(b'changed copy')
    assert not ledger.evidence_valid_at(comparison, comparison_manifest['files'])
    assert read(blind_pack / 'manifest.json') == blind_manifest
    assert ledger.evidence_valid_at(blind_pack, blind_manifest['files'])


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


def test_first_style_binding_preserves_original_observed_reference():
    previous = {'focus': 'comprehensive', 'purpose': 'process', 'reviewMode': 'process',
                'fps': 30, 'displaySizes': [393, 1080], 'references': [{'path': 'refs/target.mp4', 'sha256': 'a' * 64}],
                'conditions': ['保持同一交易日'], 'sources': [], 'sceneIds': [], 'film': True,
                'items': [{'id': 'handoff', 'window': [10, 50], 'dynamic': True}]}
    current = {**previous, 'styleDigest': 'b' * 64, 'styleTargets': {'handoff': {'scene': ['evidence']}}}
    assert issues.covers(previous, current)
    assert not issues.covers(current, previous)
    assert not issues.covers(current, {**current, 'styleDigest': 'c' * 64})
    assert not issues.covers(previous, {**current, 'references': []})
    assert not issues.covers(previous, {**current, 'conditions': []})
    assert not issues.covers({**previous, 'references': []}, {**current, 'references': []})


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


def test_static_capture_delivers_images_without_a_video_or_process_claim(native):
    root, project, _ = native
    identity = samples.capture(root, project, kind='static')['id']
    args = pair((root, project, identity))
    value, directory = samples.load(root, project, identity)
    assert value['video'] is None and not list(directory.glob('*.mp4'))
    result = samples.deliver(root, project, identity, **args)
    assert list(Path(result['path']).glob('*.png')) and not list(Path(result['path']).glob('*.mp4'))


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
