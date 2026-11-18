"""用户换目标不抹去失败，不扩大或缩小实际复查授权。"""
from copy import deepcopy
from pathlib import Path

import pytest
from PIL import Image

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.production import dependencies, issues, ledger, reviews, samples, targets
from m2v.production.storage import read
from common.test_native_samples import native, pair  # noqa: F401
from common.test_media_reviews import report


def replacement(native, *, request_change=None, isolation='independent-subagent'):
    root, project, _ = native
    pair(native, verdict='fail', isolation=isolation)
    previous = deepcopy(issues.load(root))
    identity = samples.capture(root, project)['id']
    request = read(outputs(root) / f'samples/{identity}/review-request.json')
    Image.new('RGB', (640, 360), 'orange').save(outputs(root) / 'new-target.png')
    request.update(references=['new-target.png'], conditions=['以空间文字和纸层关系为新目标'])
    if request_change:
        request_change(request)
    pack = reviews.package(root, project, request)
    data = dict(version=1, source='user', instruction='可以更换上次的视觉基准，继续研究试制。',
                reportIds=[item['reportId'] for item in previous],
                packPath=(pack / 'manifest.json').relative_to(outputs(root)).as_posix(),
                packSha256=dependencies.digest(pack / 'manifest.json'))
    return identity, request, pack, data, previous


def new_pair(native, request, pack):
    root, project, _ = native
    blind = reviews.import_report(root, project, report((root, project), pack))
    request = {**request, 'reviewType': 'consistency', 'blindId': blind['id']}
    comparison = reviews.import_report(root, project, report((root, project), reviews.package(root, project, request)))
    return dict(blind_id=blind['id'], comparison_id=comparison['id'], basis='新目标下的独立双通过')


def close(root, blind_id):
    for item in issues.load(root):
        item.update(status='closed', cause='design', closureReportId=blind_id)
        issues.update(root, item)


def test_registered_user_retarget_closes_only_after_fresh_pair(native):
    root, project, _ = native
    identity, request, pack, data, previous = replacement(native)
    cycle = ledger.cycle(root)
    result = targets.register(root, project, data)
    assert result['issuesClosed'] is False
    assert issues.load(root) == previous and ledger.cycle(root) == cycle
    with pytest.raises(M2VError, match='不能重开周期'):
        ledger.start(root, project)
    args = new_pair(native, request, pack)
    close(root, args['blind_id'])
    assert all(item['status'] == 'closed' for item in issues.load(root))
    assert [item['scope'] for item in issues.load(root)] == [item['scope'] for item in previous]
    assert samples.deliver(root, project, identity, **args)['sampleId'] == identity


def test_changed_target_without_user_registration_cannot_close(native):
    root, _, _ = native
    _, request, pack, _, _ = replacement(native)
    args = new_pair(native, request, pack)
    with pytest.raises(M2VError, match='对应范围'):
        close(root, args['blind_id'])


@pytest.mark.parametrize('change', [
    lambda data: data.update(source='assistant'),
    lambda data: data.update(instruction=' '),
    lambda data: data.update(version=True),
    lambda data: data.update(reportIds=[]),
    lambda data: data.update(reportIds=['missing']),
    lambda data: data.update(reportIds=data['reportIds'] * 2),
    lambda data: data.update(packPath=123),
    lambda data: data.update(packSha256=None),
])
def test_invalid_retarget_declaration_is_rejected_without_mutation(native, change):
    root, project, _ = native
    _, _, _, data, previous = replacement(native)
    before = ledger.history(root)[0]
    change(data)
    with pytest.raises(M2VError):
        targets.register(root, project, data)
    assert issues.load(root) == previous and ledger.history(root)[0] == before


@pytest.mark.parametrize('change', [
    lambda req: req.update(displaySizes=[393]),
    lambda req: req['items'][0].update(id='other-state'),
    lambda req: req.update(sources=['scenes/other.tsx']),
])
def test_user_retarget_cannot_change_structural_scope(native, change):
    root, project, _ = native
    (root / 'scenes/other.tsx').write_text('export default 2;', encoding='utf-8')
    _, _, _, data, _ = replacement(native, request_change=change)
    with pytest.raises(M2VError, match='不得缩小'):
        targets.register(root, project, data)


def test_pass_before_target_change_cannot_be_reused(native):
    root, project, _ = native
    _, request, pack, data, _ = replacement(native)
    args = new_pair(native, request, pack)
    targets.register(root, project, data)
    with pytest.raises(M2VError, match='晚于'):
        close(root, args['blind_id'])


def test_corrupt_target_change_reopens_and_blocks_delivery(native):
    root, project, _ = native
    identity, request, pack, data, _ = replacement(native)
    change = targets.register(root, project, data)
    args = new_pair(native, request, pack)
    close(root, args['blind_id'])
    Path(change['path']).write_text('{}', encoding='utf-8')
    assert all(item['status'] == 'open' for item in issues.load(root))
    with pytest.raises(M2VError, match='必改'):
        samples.deliver(root, project, identity, **args)


def test_retarget_rejects_stale_package(native):
    root, project, _ = native
    _, _, _, data, _ = replacement(native)
    (root / 'scenes/main.tsx').write_text('changed', encoding='utf-8')
    with pytest.raises(M2VError, match='变化|过期'):
        targets.register(root, project, data)


def test_retarget_cannot_select_a_self_review_failure(native):
    root, project, _ = native
    _, _, _, data, _ = replacement(native, isolation='self-review')
    with pytest.raises(M2VError, match='独立必改失败'):
        targets.register(root, project, data)


def test_unchanged_target_is_not_a_user_retarget(native):
    root, project, _ = native
    _, _, _, data, _ = replacement(native, request_change=lambda req: req.update(
        references=['target.png'], conditions=['整体品质参考：主体轮廓与空间关系']))
    with pytest.raises(M2VError, match='目标未改变'):
        targets.register(root, project, data)


def test_retarget_does_not_authorize_an_unlisted_failure(native):
    root, project, _ = native
    _, request, pack, data, previous = replacement(native)
    data['reportIds'] = data['reportIds'][:1]
    targets.register(root, project, data)
    args = new_pair(native, request, pack)
    listed, unlisted = previous
    listed.update(status='closed', cause='design', closureReportId=args['blind_id'])
    issues.update(root, listed)
    unlisted.update(status='closed', cause='design', closureReportId=args['blind_id'])
    with pytest.raises(M2VError, match='对应范围'):
        issues.update(root, unlisted)


def test_latest_user_target_in_a_chain_requires_a_new_pair(native):
    root, project, _ = native
    _, request, pack, data, previous = replacement(native)
    targets.register(root, project, data)
    prior = new_pair(native, request, pack)
    Image.new('RGB', (640, 360), 'purple').save(outputs(root) / 'third-target.png')
    request = {**request, 'references': ['third-target.png'], 'conditions': ['第三个用户目标']}
    third_pack = reviews.package(root, project, request)
    data.update(packPath=(third_pack / 'manifest.json').relative_to(outputs(root)).as_posix(),
                packSha256=dependencies.digest(third_pack / 'manifest.json'))
    targets.register(root, project, data)
    with pytest.raises(M2VError, match='对应范围'):
        close(root, prior['blind_id'])
    latest = new_pair(native, request, third_pack)
    close(root, latest['blind_id'])
    assert [item['scope'] for item in issues.load(root)] == [item['scope'] for item in previous]


def test_observation_before_registration_cannot_be_imported_later_as_fresh(native, monkeypatch):
    from datetime import datetime, timedelta

    root, project, _ = native
    _, request, pack, data, _ = replacement(native)
    old_observation = report((root, project), pack)
    call = read(outputs(root) / read(old_observation)['invocation']['path'])
    later = (datetime.fromisoformat(call['completedAt']) + timedelta(seconds=1)).isoformat()
    with monkeypatch.context() as patch:
        patch.setattr(ledger, 'now', lambda: later)
        targets.register(root, project, data)
    blind = reviews.import_report(root, project, old_observation)
    comparison_request = {**request, 'reviewType': 'consistency', 'blindId': blind['id']}
    comparison_pack = reviews.package(root, project, comparison_request)
    reviews.import_report(root, project, report((root, project), comparison_pack))
    with pytest.raises(M2VError, match='重新开始'):
        close(root, blind['id'])


@pytest.mark.parametrize('change', [
    lambda scope: scope.update(sources=['other-source']),
    lambda scope: scope.update(sceneIds=['other-scene']),
    lambda scope: scope['items'][0].update(id='other-window'),
    lambda scope: scope['items'][0].update(window=[0, 8]),
])
def test_final_target_registration_also_preserves_structure(change):
    original = dict(focus='comprehensive', fps=30, purpose='final', reviewMode='blind', displaySizes=[393, 1920], references=['old'], conditions=['old'],
                    sources=['video.mp4'], sceneIds=['opening'], items=[dict(id='full', window=[0, 10], dynamic=True)])
    current = deepcopy(original)
    current.update(references=['new'], conditions=['new'])
    change(current)
    assert not targets._structural_cover(original, current)
