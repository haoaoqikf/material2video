"""同轮实际参考、逐场范围与失效边界。"""
from copy import deepcopy

import pytest

from m2v.core import style_binding as style
from m2v.core.delivery import digest, outputs
from m2v.core.errors import M2VError
from m2v.production import reviews, style_review
from m2v.production.storage import read, write
from common.test_media_reviews import report, request, work  # noqa: F401


@pytest.mark.parametrize('omission', ['reference', 'candidate'])
def test_same_round_uses_pinned_media_and_requires_observed_targets(work, omission):
    root, project = work
    req = {**request(), 'conditions': ['手机尺寸看清主句'], 'referenceUses': {'window-1': []}}
    blind = reviews.package(root, project, req)
    assert not list(blind.glob('style-*'))
    first = reviews.import_report(root, project, report(work, blind))
    compare = reviews.compare(root, project, first['id'])
    index = read(compare/'style-references.json')
    only, = index['references'].values()
    assert only['role'] == 'overall' and digest(compare/only['file']) == only['sha256']
    data = report(work, compare)
    result = read(data)
    record = outputs(root)/result['invocation']['path']
    invocation = read(record)
    skipped = only['file'] if omission == 'reference' else read(compare/'manifest.json')['items'][0]['sequence'][0]['displayPaths'][-1]
    invocation['inputPaths'] = [p for p in invocation['inputPaths'] if not p.endswith(skipped)]
    write(record, invocation)
    result['invocation']['sha256'] = digest(record)
    write(data, result)
    with pytest.raises(M2VError, match='insufficient'):
        reviews.import_report(root, project, data)
    accepted = reviews.import_report(root, project, report(work, compare))
    assert accepted['verdict'] == 'pass'
    path = root/style.BINDING
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(M2VError, match='过期'):
        reviews.current_report(root, project, accepted['id'])


def test_partial_override_preserves_other_scenes_and_roles(work):
    root, project = work
    data = style.load_binding(root, project)
    refs = data['visualStyle']['references']
    target = deepcopy(data['visualStyle'])
    target.update(id='authorized-grid', references=[refs[1]])
    target['snapshot'] = {refs[1]['id']: target['snapshot'][refs[1]['id']]}
    (root/'instruction.txt').write_text('第一幕采用此网格', encoding='utf-8')
    write(root/'storyboard.json', {'scenes': [{'id': 'one'}, {'id': 'two'}]})
    data['overrides'] = [{'target': target, 'referenceDigest': style.fingerprint(target),
                          'scope': {'scenes': ['one'], 'uses': [refs[1]['id']]},
                          'authorization': {'quote': '第一幕采用此网格', 'at': '2026-11-28T09:00:00+08:00',
                                            'source': 'instruction.txt'}}]
    write(root/style.BINDING, data)
    req = {**request(), 'sceneIds': ['one', 'two']}
    view = style_review.selection(root, project, req)
    window = view['items']['window-1']
    assert set(window['one']) - set(window['two']) == {'authorized-grid@1/'+refs[1]['id']}
    assert len(set(window['two']) - set(window['one'])) == 1
    with pytest.raises(M2VError, match='当前范围外'):
        style_review.selection(root, project, {**req, 'referenceUses': {'window-1': ['unknown']}})


def test_missing_reference_or_conditions_cannot_authorize_pass(work, monkeypatch):
    root, project = work
    def unavailable(*_):
        raise M2VError('来源不可达且没有有效快照')
    monkeypatch.setattr(style_review, '_obtain', unavailable)
    blind = reviews.package(root, project, request())
    first = reviews.import_report(root, project, report(work, blind))
    compare = reviews.compare(root, project, first['id'])
    index = read(compare/'style-references.json')
    assert not index['conditionsAvailable'] and all('missing' in r for r in index['references'].values())
    with pytest.raises(M2VError, match='insufficient'):
        reviews.import_report(root, project, report(work, compare))
    assert reviews.import_report(root, project, report(work, compare, verdict='insufficient'))['adoption'] == 'reject'

def test_retarget_requires_authorization_for_every_changed_scene(work):
    from m2v.production import targets

    root, project = work
    write(root/'storyboard.json', {'scenes': [{'id': name, 'content': {'entry': 'core.tsx'}}
                                              for name in ('one', 'two')]})
    req = {**request(), 'sceneIds': ['one', 'two'], 'conditions': ['两场核对图表焦点']}
    original = reviews.package(root, project, req)
    failed = reviews.import_report(root, project, report(work, original, verdict='fail'))
    binding = style.load_binding(root, project)
    visual = binding['visualStyle']
    quotes = ['第一场采用新版网格', '第二场采用新版网格']
    (root/'authorization.txt').write_text('\n'.join(quotes), encoding='utf-8')
    for scene, quote in zip(req['sceneIds'], quotes, strict=True):
        target = {**visual, 'id': 'new-grid'}
        binding['overrides'].append({
            'target': target, 'referenceDigest': style.fingerprint(target),
            'scope': {'scenes': [scene], 'uses': 'all'},
            'authorization': {'quote': quote, 'at': '2026-11-28T09:00:00+08:00',
                              'source': 'authorization.txt'},
        })
    write(root/style.BINDING, binding)

    def replacement(instruction):
        pack = reviews.package(root, project, req)
        return dict(version=1, source='user', instruction=instruction, reportIds=[failed['id']],
                    packPath=(pack/'manifest.json').relative_to(outputs(root)).as_posix(),
                    packSha256=digest(pack/'manifest.json'))

    with pytest.raises(M2VError, match='全部受影响场景'):
        targets.register(root, project, replacement(quotes[0]))
    quote = '两个场景都采用新版网格'
    (root/'authorization.txt').write_text(quote, encoding='utf-8')
    for override in binding['overrides']:
        override['authorization']['quote'] = quote
    write(root/style.BINDING, binding)
    assert targets.register(root, project, replacement(quote))['issuesClosed'] is False


@pytest.mark.parametrize('swap_reference', [False, True])
def test_first_default_allows_user_condition_change_only_with_original_reference(work, monkeypatch, swap_reference):
    from m2v.production import targets

    root, project = work
    original = {**request(), 'references': ['one.png'], 'conditions': ['底部显示单位']}
    # 用真实画面作为旧资料，保留历史凭据缺少默认绑定这一处版本差异。
    base = outputs(root)
    image = base / request()['items'][0]['path']
    (base / 'one.png').write_bytes(image.read_bytes())
    (base / 'two.png').write_bytes(image.read_bytes())
    original_pack = reviews.package(root, project, original)
    failed = reviews.import_report(root, project, report(work, original_pack, verdict='fail'))
    effective = targets.effective_scope

    def legacy_scope(root, item):
        scope, index = effective(root, item)
        for key in ('styleTargets', 'styleDigest'):
            scope.pop(key, None)
        return scope, index

    monkeypatch.setattr(targets, 'effective_scope', legacy_scope)
    new = {**original, 'conditions': ['单位紧邻日期'],
           'references': ['two.png'] if swap_reference else original['references']}
    pack = reviews.package(root, project, new)
    change = dict(version=1, source='user', instruction='单位移到日期旁', reportIds=[failed['id']],
                  packPath=(pack/'manifest.json').relative_to(base).as_posix(), packSha256=digest(pack/'manifest.json'))
    if swap_reference:
        with pytest.raises(M2VError, match='已登记用户授权'):
            targets.register(root, project, change)
    else:
        assert targets.register(root, project, change)['issuesClosed'] is False
