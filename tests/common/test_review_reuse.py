"""视觉结论复用边界；复用不产生新的观察，不替代当前采集或独立失败闭环。"""
import copy
from argparse import Namespace

import pytest
from PIL import Image

from m2v.core.delivery import outputs, digest
from m2v.core.errors import M2VError
from m2v.production import cli, dependencies, issues, ledger, reviews, reuse, samples, storage
from m2v.production.storage import read, write
from common.test_media_reviews import work, report, request
from common.test_native_samples import native, pair


def generic_pair(work, *, verdict='pass', who='first'):
    root, project = work
    req = request()
    Image.new('RGB', (640, 360), 'red').save(outputs(root) / 'target.png')
    req.update(references=['target.png'], conditions=['主体轮廓与空间关系'])
    pack = reviews.package(root, project, req)
    blind = reviews.import_report(root, project, report(work, pack, verdict=verdict, who=who))
    req.update(reviewType='consistency', blindId=blind['id'])
    pack = reviews.package(root, project, req)
    comparison = reviews.import_report(root, project, report(work, pack, verdict=verdict, who=who))
    return req, blind['id'], comparison['id']


def reuse_request(root, project, req, blind, comparison):
    req = copy.deepcopy(req)
    req.pop('blindId', None)
    req.pop('reviewType', None)
    pack = reviews.package(root, project, req)
    return dict(version=1, blindId=blind, comparisonId=comparison,
                packPath=(pack / 'manifest.json').relative_to(outputs(root)).as_posix(),
                packSha256=digest(pack / 'manifest.json'))


def test_source_change_can_reuse_visuals_without_rewriting_old_report(work):
    root, project = work
    req, blind, comparison = generic_pair(work)
    original = reviews.current_report(root, project, blind)
    (root / 'core.tsx').write_text('new implementation, same pixels', encoding='utf-8')
    with pytest.raises(M2VError, match='过期'):
        reviews.current_report(root, project, blind)
    registration = reuse.register(root, project, reuse_request(root, project, req, blind, comparison))
    assert registration['newObservation'] is False
    assert reviews.current_report(root, project, blind) == original
    with pytest.raises(M2VError, match='过期'):
        reviews.load_package(root, project, original['packPath'], original['packSha256'])
    status = ledger.status(root, project)
    assert {r['status'] for r in status['trial']} == {'pass'}
    assert all(r['visualReuse'] == registration['receipt'] for r in status['trial'])


@pytest.mark.parametrize('mutation', ['media', 'window', 'fps', 'display', 'conditions', 'reference', 'sources'])
def test_any_media_or_observation_change_rejects_reuse(work, mutation):
    root, project = work
    req, blind, comparison = generic_pair(work)
    if mutation == 'media':
        # 同像素不同文件字节也拒绝，不使用近似图片比较放宽规则。
        (outputs(root) / 'different.png').write_bytes((outputs(root) / 'trial.png').read_bytes() + b'other-container-data')
        req['items'][0]['path'] = 'different.png'
    elif mutation == 'window':
        req['items'][0]['window'] = [0, 2]
    elif mutation == 'fps':
        req['fps'] = 24
    elif mutation == 'display':
        req['displaySizes'].append(1280)
    elif mutation == 'conditions':
        req['conditions'] = ['改变目标']
    elif mutation == 'reference':
        Image.new('RGB', (640, 360), 'green').save(outputs(root) / 'another.png')
        req['references'] = ['another.png']
    else:
        req['sources'].append('unrelated.tsx')
    with pytest.raises(M2VError, match='不同'):
        reuse.register(root, project, reuse_request(root, project, req, blind, comparison))


@pytest.mark.parametrize('damage', ['report', 'call', 'private', 'pack', 'media', 'receipt'])
def test_reuse_revalidates_sealed_history_and_current_evidence(work, damage):
    root, project = work
    req, blind, comparison = generic_pair(work)
    original = reviews.current_report(root, project, blind)
    (root / 'core.tsx').write_text('changed', encoding='utf-8')
    result = reuse.register(root, project, reuse_request(root, project, req, blind, comparison))
    if damage == 'report':
        target = ledger.directory(root) / 'reports' / f'{blind}.json'
    elif damage == 'call':
        target = outputs(root) / original['invocation']['path']
    elif damage == 'private':
        target = ledger.directory(root) / 'packages' / f"{read(outputs(root) / original['packPath'])['reviewId']}.json"
    elif damage == 'pack':
        target = outputs(root) / original['packPath']
    elif damage == 'media':
        target = outputs(root) / 'trial.png'
    else:
        target = outputs(root) / result['receipt']['path']
    target.write_bytes(b'damaged')
    with pytest.raises(M2VError):
        reviews.current_report(root, project, blind)


def test_reuse_cannot_choose_old_pass_over_new_failure_or_refresh_time(work):
    root, project = work
    req, blind, comparison = generic_pair(work)
    generic_pair(work, verdict='fail', who='failed')
    registration = reuse_request(root, project, req, blind, comparison)
    with pytest.raises(M2VError, match='未解决'):
        reuse.register(root, project, registration)
    for problem in issues.load(root):
        problem.update(status='closed', cause='design', closureReportId=blind)
        with pytest.raises(M2VError, match='晚于'):
            issues.update(root, problem)


def test_legal_new_review_closes_conflict_but_stale_closure_blocks_again(work):
    root, project = work
    req, blind, comparison = generic_pair(work)
    generic_pair(work, verdict='fail', who='failed')
    _, fresh, _ = generic_pair(work, who='dispute-new')
    for problem in issues.load(root):
        problem.update(status='closed', cause='design', closureReportId=fresh)
        issues.update(root, problem)
    reuse.register(root, project, reuse_request(root, project, req, blind, comparison))
    (root / 'core.tsx').write_text('changed after dispute closure', encoding='utf-8')
    with pytest.raises(M2VError):
        reviews.current_report(root, project, blind)


@pytest.mark.parametrize('cycle_length', [1, 2])
def test_issue_query_rejects_cyclic_reuse_closures_and_recovers_after_repair(work, cycle_length):
    """真实封存/复用链不能用自循环或双报告循环关闭失败；查询退出后可重新核验。"""
    root, project = work
    Image.new('RGB', (640, 360), 'red').save(outputs(root) / 'target.png')
    requests = []
    for index in range(cycle_length):
        media = f'cycle-{index}.png'
        Image.new('RGB', (640, 360), ('blue', 'green')[index]).save(outputs(root) / media)
        req = request()
        req['items'][0]['path'] = media
        req.update(references=['target.png'], conditions=['主体轮廓与空间关系'])
        requests.append(req)

    def make_pair(req, who, verdict='pass'):
        pack = reviews.package(root, project, req)
        blind = reviews.import_report(root, project, report(work, pack, who=who, verdict=verdict))
        comparison_request = dict(req, reviewType='consistency', blindId=blind['id'])
        pack = reviews.package(root, project, comparison_request)
        comparison = reviews.import_report(root, project, report(work, pack, who=who, verdict=verdict))
        return blind['id'], comparison['id']

    original = [make_pair(req, f'original-{index}') for index, req in enumerate(requests)]
    failed = [make_pair(req, f'failure-{index}', 'fail') for index, req in enumerate(requests)]
    fresh, _ = make_pair(requests[0], 'fresh-observation')
    for problem in issues.load(root):
        problem.update(status='closed', cause='design', closureReportId=fresh)
        issues.update(root, problem)
    repaired = issues.load(root)
    for req, (blind, comparison) in zip(requests, original, strict=True):
        reuse.register(root, project, reuse_request(root, project, req, blind, comparison))

    # 模拟问题表被外部改写；原报告、包和复用收据仍须走真实校验，不能mock resolve。
    cyclic = copy.deepcopy(repaired)
    for problem in cyclic:
        index = next(i for i, pair in enumerate(failed) if problem['reportId'] in pair)
        problem['closureReportId'] = original[(index + 1) % cycle_length][0]
    issues.save(root, cyclic)
    with ledger.query():
        with pytest.raises(M2VError, match='循环依赖'):
            reviews.current_report(root, project, original[0][0])
        assert {item['status'] for item in issues.load(root)} == {'open'}
    assert not reuse._resolving.get()

    # 失败缓存不能跨独立读取；恢复真实fresh闭环后应重新通过，而非永久缓存失败。
    issues.save(root, repaired)
    assert {item['status'] for item in issues.load(root)} == {'closed'}
    assert reviews.current_report(root, project, original[0][0])['verdict'] == 'pass'
    assert not ledger.query_active()


@pytest.mark.parametrize('source_changed', [True, False])
def test_current_native_capture_can_deliver_with_same_full_media(native, source_changed):
    root, project, old = native
    args = pair(native)
    before = reviews.current_report(root, project, args['blind_id'])
    if source_changed:
        (root / 'scenes/main.tsx').write_text('new implementation', encoding='utf-8')
    fresh = samples.capture(root, project)['id']
    req = read(outputs(root) / f'samples/{fresh}/review-request.json')
    req.update(references=['target.png'], conditions=['整体品质参考：主体轮廓与空间关系'])
    reuse.register(root, project, reuse_request(root, project, req, args['blind_id'], args['comparison_id']))
    delivered = samples.deliver(root, project, fresh, **args)
    assert delivered['sampleId'] == fresh and delivered['visualReuse']['path']
    assert reviews.current_report(root, project, args['blind_id']) == before
    assert samples.deliver(root, project, fresh, **args)['reused']
    (root / 'scenes/main.tsx').write_text('changed again', encoding='utf-8')
    with pytest.raises(M2VError, match='来源'):
        samples.deliver(root, project, fresh, **args)


def test_missing_or_cross_cycle_or_final_reuse_is_rejected(work):
    root, project = work
    req, blind, comparison = generic_pair(work)
    registration = reuse_request(root, project, req, blind, comparison)
    missing = dict(registration, blindId='missing')
    with pytest.raises(M2VError):
        reuse.register(root, project, missing)
    req['round'] = 'final'
    # final 身份在 signature 入口拒绝，不能经 trial 收据改变阶段。
    original = read(outputs(root) / registration['packPath'])
    original['round'] = 'final'
    write(outputs(root) / registration['packPath'], original)
    with pytest.raises(M2VError):
        reuse.register(root, project, registration)
    ledger.start(root, project)
    with pytest.raises(M2VError):
        reuse.register(root, project, registration)


def test_repackaging_stale_native_capture_cannot_create_current_visual_evidence(native):
    root, project, identity = native
    args = pair(native)
    req = read(outputs(root) / f'samples/{identity}/review-request.json')
    req.update(references=['target.png'], conditions=['整体品质参考：主体轮廓与空间关系'])
    (root / 'scenes/main.tsx').write_text('changed source but no new capture', encoding='utf-8')
    with pytest.raises(M2VError, match='来源已变化'):
        reuse.register(root, project, reuse_request(root, project, req, args['blind_id'], args['comparison_id']))


@pytest.mark.parametrize('alternate_case', [False, True])
def test_indirect_capture_input_change_invalidates_normal_report_as_well_as_reuse(native, monkeypatch, alternate_case):
    root, project, _ = native
    dependency = root / 'indirect.ts'
    dependency.write_text('original', encoding='utf-8')
    render = samples.design_sample.render
    def with_dependency(*args, **kwargs):
        result = render(*args, **kwargs)
        result['inputs']['work/indirect.ts'] = digest(dependency)
        return result
    monkeypatch.setattr(samples.design_sample, 'render', with_dependency)
    identity = samples.capture(root, project)['id']
    if alternate_case:
        import os
        if os.name != 'nt':
            pytest.skip('Windows路径大小写等价边界')
        req_path = outputs(root) / f'samples/{identity}/review-request.json'
        req = read(req_path)
        req['sources'][0] = req['sources'][0].replace('outputs/', 'Outputs/').replace('/capture.json', '/CAPTURE.JSON')
        write(req_path, req)
    accepted = pair((root, project, identity))
    assert reviews.current_report(root, project, accepted['blind_id'])['verdict'] == 'pass'
    dependency.write_text('changed but entry and capture json unchanged', encoding='utf-8')
    with pytest.raises(M2VError, match='来源已变化'):
        reviews.current_report(root, project, accepted['blind_id'])


def test_independent_fail_cannot_be_downgraded_to_advice(work):
    root, _ = work
    generic_pair(work, verdict='fail')
    problem = issues.load(root)[0]
    problem['required'] = False
    with pytest.raises(M2VError, match='必改性质'):
        issues.update(root, problem)


def test_late_import_cannot_refresh_an_observation_made_before_failure(work):
    root, project = work
    req, _, _ = generic_pair(work)
    req.pop('blindId')
    req.pop('reviewType')
    pack = reviews.package(root, project, req)
    path = report(work, pack, who='observed-before-failure')
    old = read(path)
    call = outputs(root) / old['invocation']['path']
    invocation = read(call)
    invocation.update(startedAt=read(pack / 'manifest.json')['createdAt'],
                      completedAt=read(pack / 'manifest.json')['createdAt'])
    write(call, invocation)
    from m2v.production.storage import receipt
    old['invocation'] = receipt(outputs(root), call)
    saved = root / 'old-observation.json'
    write(saved, old)
    generic_pair(work, verdict='fail', who='later-failure')
    imported = reviews.import_report(root, project, saved)
    comparison_request = dict(req, reviewType='consistency', blindId=imported['id'])
    comparison_pack = reviews.package(root, project, comparison_request)
    reviews.import_report(root, project, report(work, comparison_pack, who='observed-before-failure'))
    for problem in issues.load(root):
        problem.update(status='closed', cause='design', closureReportId=imported['id'])
        with pytest.raises(M2VError, match='重新开始'):
            issues.update(root, problem)


def test_cli_reuse_streams_each_media_only_for_binding_and_snapshot(work, monkeypatch, capsys):
    root, project = work
    req, blind, comparison = generic_pair(work)
    registration = reuse_request(root, project, req, blind, comparison)
    path = root / 'reuse.json'
    write(path, registration)
    source = (outputs(root) / 'trial.png').resolve()
    actual, reads = storage.digest, []
    def counted(path):
        if path.resolve() == source:
            reads.append(path)
        return actual(path)
    monkeypatch.setattr(storage, 'digest', counted)
    monkeypatch.setattr(dependencies, 'file_digest', counted)
    assert cli.dispatch(Namespace(command='review', action='reuse', project=str(root), file=str(path))) == 0
    assert 'newObservation' in capsys.readouterr().out
    # 一次直接当前来源绑定 + 一次操作内依赖快照；不随历史报告重复读取全片。
    assert len(reads) <= 2
