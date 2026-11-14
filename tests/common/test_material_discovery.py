"""多源编排独特边界：完整预校验、查询去重、部分失败和元数据持久化。"""
from __future__ import annotations

import json

import pytest

from m2v.materials.contracts import IdentityConstraint, Query, Requirement, RequirementData, SourceData
from m2v.materials.discovery import discover, providers
from m2v.materials.errors import MaterialError
from m2v.materials.source_types import Capability, SearchPage, source, variant
from m2v.materials.store import MaterialStore


class Provider:
    capability = Capability(True, True, True, False, True)

    def __init__(self, name, callback):
        self.name, self.callback, self.calls = name, callback, []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return self.callback(query, **kwargs)


def item(provider='test', identifier='1', width=1920, height=1080):
    return source(provider, identifier, f'https://example.org/{identifier}', title=identifier,
                  variants=[variant('original', 'https://cdn.example.org/x.mp4', kind='video', width=width, height=height)])


def requirement(identifier, *queries, orientation=None):
    return Requirement(id=identifier, data=RequirementData(text='验证真实机械臂抓取', task='process',
        queries=[Query(text=query) for query in queries], minDurationUs=2_000_000,
        identity=IdentityConstraint(entity='Specific Corp', mustMatch=True), preferredOrientation=orientation))


def test_queries_across_requirements_share_requests_but_keep_both_references(tmp_path):
    provider = Provider('test', lambda *args, **kwargs: SearchPage([item()]))
    requirements = [requirement('r1', '机械臂'), requirement('r2', '机械臂', 'robot arm')]
    with MaterialStore(tmp_path / 'work') as store:
        result = discover(selected=[provider], requirements=requirements, store=store)
        document = result.sources[0]
        assert len(provider.calls) == 2 and result.coverage[1]['cacheHit']
        assert {entry.text for entry in document.data.queries} == {'机械臂', 'robot arm'}
        assert store.get('r1').data.identity.mustMatch
        refs = {row[0] for row in store.connection.execute('SELECT target FROM refs WHERE owner=?', (document.id,))}
        assert refs == {'r1', 'r2'}
        again = discover(selected=[provider], requirements=requirements, store=store)
        assert again.sources[0].id == document.id and again.sources[0].createdAt == document.createdAt
        assert result.exit_code == 0 and not result.partial
        assert document.data.policy.usage.status == 'not-checked'


def test_empty_success_and_failure_remain_distinct_and_independent():
    empty = Provider('empty', lambda *args, **kwargs: SearchPage([]))
    def denied(*args, **kwargs):
        raise MaterialError('rate-limited', '有限限流', stage='network', retryable=True)
    failed = Provider('failed', denied)
    good = Provider('good', lambda *args, **kwargs: SearchPage([item('good')]))
    result = discover(selected=[failed, empty, good], queries=[Query(text='robot')])
    assert result.partial and result.exit_code == 1 and len(result.sources) == 1
    assert result.failures[0]['error']['code'] == 'rate-limited'
    assert next(row for row in result.coverage if row['provider'] == 'empty')['returned'] == 0
    assert all('nextStep' in failure for failure in result.failures)
    assert discover(selected=[empty], queries=[Query(text='nothing')]).exit_code == 0
    assert discover(selected=[failed], queries=[Query(text='robot')]).exit_code == 2


def test_empty_candidate_gap_is_actionable_without_changing_zero_success_or_the_script():
    empty = Provider('test', lambda *args, **kwargs: SearchPage([]))
    requirement_doc = requirement('r1', 'robot')
    before = requirement_doc.model_dump(mode='json')
    result = discover(selected=[empty], requirements=[requirement_doc], queries=[Query(text='another')])
    assert result.exit_code == 0 and not result.failures
    assert result.suggestions[0]['requirementId'] == 'r1'
    assert any('Specific Corp' in item for item in result.suggestions[0]['advice'])
    assert result.suggestions[1]['query']['text'] == 'another'
    assert result.to_dict()['suggestions'] == result.suggestions
    assert requirement_doc.model_dump(mode='json') == before
    good = Provider('test', lambda *args, **kwargs: SearchPage([item()]))
    assert not discover(selected=[good], requirements=[requirement_doc]).suggestions


def test_pagination_is_bounded_and_repeated_cursors_stop():
    provider = Provider('test', lambda *args, **kwargs: SearchPage([item()], cursor='20'))
    result = discover(selected=[provider], queries=[Query(text='robot')], max_pages=10)
    assert len(provider.calls) == 2 and result.failures[0]['error']['code'] == 'pagination-loop'
    assert result.exit_code == 1 and len(result.sources) == 1
    provider = Provider('test', lambda *args, **kwargs: SearchPage([item()], cursor='20'))
    result = discover(selected=[provider], queries=[Query(text='robot')], max_pages=1)
    assert len(provider.calls) == 1 and result.coverage[0]['truncated'] and result.exit_code == 0


@pytest.mark.parametrize('options', [{'page_size': True}, {'max_results': 0}, {'max_pages': 21}, {'max_queries': False}])
def test_invalid_budgets_fail_before_requests(options):
    provider = Provider('test', lambda *args, **kwargs: SearchPage([]))
    with pytest.raises(MaterialError):
        discover(selected=[provider], queries=[Query(text='robot')], **options)
    assert provider.calls == []


def test_unknown_version_and_duplicate_requirement_id_have_no_store_side_effects(tmp_path):
    provider = Provider('test', lambda *args, **kwargs: SearchPage([]))
    valid = requirement('r', 'robot')
    bad = valid.model_dump(mode='json')
    bad['schemaVersion'] = 999
    with MaterialStore(tmp_path / 'work') as store:
        for values in ([valid, bad], [valid, valid]):
            with pytest.raises(MaterialError):
                discover(selected=[provider], requirements=values, store=store)
        assert store.documents('material.requirement') == [] and provider.calls == []


def test_direction_only_sorts_and_source_constraints_are_not_auto_satisfied():
    provider = Provider('test', lambda *args, **kwargs: SearchPage([item(identifier='wide'), item(identifier='tall', width=720, height=1280)]))
    result = discover(selected=[provider], requirements=[requirement('r', 'robot', orientation='portrait')])
    assert [entry.data.externalId for entry in result.sources] == ['tall', 'wide']
    assert len(result.sources) == 2 and all('observations' not in value.data.model_dump() for value in result.sources)


def test_result_budget_reports_unqueried_sources_without_calling_them():
    first = Provider('first', lambda *args, **kwargs: SearchPage([item('first')]))
    second = Provider('second', lambda *args, **kwargs: SearchPage([item('second')]))
    result = discover(selected=[first, second], queries=[Query(text='robot')], max_results=1)
    assert result.partial and result.exit_code == 1 and not second.calls
    assert result.skipped[0]['provider'] == 'second' and result.skipped[0]['reason'] == 'result-budget'


def test_cancellation_retains_completed_page_in_store(tmp_path):
    provider = Provider('test', lambda *args, **kwargs: SearchPage([item()], cursor='20'))
    with MaterialStore(tmp_path / 'work') as store:
        result = discover(selected=[provider], queries=[Query(text='robot')], store=store,
                          cancelled=lambda: bool(provider.calls))
        assert result.exit_code == 130 and result.sources and len(provider.calls) == 1
        assert store.get(result.sources[0].id).kind == 'material.source'


def test_malformed_page_is_atomic_and_does_not_block_next_source():
    bad = Provider('bad', lambda *args, **kwargs: SearchPage([item('bad'), 'PRIVATE_PAYLOAD']))
    good = Provider('good', lambda *args, **kwargs: SearchPage([item('good')]))
    result = discover(selected=[bad, good], queries=[Query(text='robot')])
    assert [document.data.provider for document in result.sources] == ['good']
    assert result.partial and 'PRIVATE_PAYLOAD' not in json.dumps(result.to_dict())


def test_unidentifiable_source_response_fails_once_without_false_deduplication():
    bad = Provider('bad', lambda *args, **kwargs: SearchPage([SourceData(provider='bad', title='only a title')]))
    result = discover(selected=[bad], requirements=[requirement('r1', 'robot'), requirement('r2', 'robot')])
    assert not result.sources and len(bad.calls) == 1 and len(result.failures) == 2
    assert result.coverage[1]['cacheHit'] and result.exit_code == 2


def test_any_kind_expands_only_supported_native_media_types():
    provider = Provider('test', lambda query, **kwargs: SearchPage([item(identifier=kwargs['kind'])]))
    provider.capability = Capability(True, True, True, False, True, kinds=('image', 'video'))
    result = discover(selected=[provider], queries=[Query(text='robot', language='en')], kind='any')
    assert {row['kind'] for row in result.coverage} == {'image', 'video'} and len(provider.calls) == 2
    assert {query.language for document in result.sources for query in document.data.queries} == {'en'}


def test_pexels_api_cannot_be_enabled_by_environment_key(monkeypatch):
    monkeypatch.setenv('M2V_PEXELS_API_KEY', 'PRIVATE_KEY')
    selected = providers(None)['pexels']
    result = discover(selected=[selected], queries=[Query(text='robot')])
    assert result.exit_code == 2 and result.failures[0]['error']['code'] == 'api-disabled'
    assert not result.capabilities['pexels']['search'] and 'PRIVATE_KEY' not in json.dumps(result.to_dict())


def test_link_with_session_is_not_saved_as_keyword_query():
    provider = Provider('test', lambda *args, **kwargs: SearchPage([]))
    with pytest.raises(MaterialError, match='显式来源'):
        discover(selected=[provider], queries=[Query(text='https://example.org/share?token=SECRET')])
    assert not provider.calls
