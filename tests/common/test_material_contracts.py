"""素材工作材料不参与正式作品 schema，边界严格且时间关系诚实。"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from m2v.materials.contracts import (
    Artifact, Candidate, CandidateData, Index, IndexData, Media, MediaData,
    Observation, Probe, Receipt, ReceiptData, Requirement, RequirementData,
    RetrievalReason, Selection, SelectionData, Source, SourceData, SourceMapping,
    Timeline, TimeRange, fingerprint, parse_document, relative_path,
)
from m2v.materials.errors import MaterialError

SHA = 'a' * 64
ARTIFACT = Artifact(path='objects/aa/file', sha256=SHA, bytes=42)


def documents():
    return [
        Requirement(id='req-1', data=RequirementData(text='连续抓取过程')),
        Source(id='source-1', data=SourceData(provider='local', title='测试媒体')),
        Media(id='media-1', data=MediaData(sourceId='source-1', artifact=ARTIFACT,
              probe=Probe(kind='image', container='png', width=32, height=24), fetchIdentity=SHA)),
        Index(id='index-1', data=IndexData(mediaId='media-1', mediaSha256=SHA, channel='metadata',
              status='complete', configSha256=SHA, timelineMappingSha256=SHA, artifacts=[ARTIFACT])),
        Candidate(id='candidate-1', data=CandidateData(requirementId='req-1', requirementDigest=SHA,
              sourceId='source-1', mediaId='media-1', mediaSha256=SHA, indexIds=['index-1'],
              localRange=None, timelineMappingSha256=SHA,
              retrievalReasons=[RetrievalReason(channel='metadata', rank=1, score=0.5)], fusionScore=0.02)),
        Selection(id='selection-1', data=SelectionData(candidateId='candidate-1', candidateDigest=SHA,
              mediaId='media-1', mediaSha256=SHA, localRange=None, decision='chosen',
              rationale='已看图', purpose='对象识别', operator='assistant')),
        Receipt(id='receipt-1', data=ReceiptData(operationId='op-1', selectionId='selection-1',
              selectionDigest=SHA, sourceId='source-1', inputMediaSha256=SHA, localRange=None,
              timeline=Timeline(), outputArtifactSha256=SHA, manifestSha256=SHA,
              targetProjectId='film', targetAssetId='asset', status='pending')),
    ]


@pytest.mark.parametrize('document', documents())
def test_work_documents_roundtrip_and_reject_unknown_versions_fields(document):
    data = json.loads(document.model_dump_json())
    assert parse_document(data) == document
    for invalid in (2, True, 1.0, '1'):
        with pytest.raises(MaterialError, match='素材工作材料'):
            parse_document({**data, 'schemaVersion': invalid})
    with pytest.raises(MaterialError):
        parse_document({**data, 'extra': '不能吞掉'})
    with pytest.raises(MaterialError):
        parse_document({**data, 'data': {**data['data'], 'extra': '不能吞掉'}})


@pytest.mark.parametrize('start,end', [(1, 1), (2, 1), (-1, 2), (True, 2), (0, False),
                                       (0.0, 2), (0, float('nan')), (0, float('inf'))])
def test_range_is_strict_integer_half_open(start, end):
    with pytest.raises(ValidationError):
        TimeRange(startUs=start, endUs=end)


@pytest.mark.parametrize('path', ['../x', '/x', 'C:/x', 'C:x', 'a\\x', 'a/../x',
                                  './x', 'a//x', 'a/./x', 'a/file:stream', 'a\x00b'])
def test_paths_are_portable_and_do_not_normalize_away_escape(path):
    with pytest.raises(ValueError):
        relative_path(path)


def test_unknown_and_estimated_mapping_do_not_export_fake_source_range():
    interval = TimeRange(startUs=500_000, endUs=1_500_000)
    assert Timeline().source_range(interval) is None
    estimated = Timeline(sourceMapping=SourceMapping(status='estimated', sourceOriginUs=10_000_000))
    assert estimated.source_range(interval) is None
    verified = Timeline(sourceMapping=SourceMapping(status='verified', method='full-input',
                        sourceOriginUs=10_000_000, maxErrorUs=0))
    assert verified.source_range(interval) == TimeRange(startUs=10_500_000, endUs=11_500_000)
    with pytest.raises(ValidationError):
        SourceMapping(status='unknown', sourceOriginUs=1)
    with pytest.raises(ValidationError):
        SourceMapping(status='verified', sourceOriginUs=0)


def test_segment_hash_is_not_full_upstream_and_image_has_no_time():
    data = documents()[2].data.model_dump()
    with pytest.raises(ValidationError):
        MediaData.model_validate({**data, 'coverage': 'section', 'upstreamFullSha256': SHA})
    with pytest.raises(ValidationError):
        MediaData.model_validate({**data, 'requestedRange': {'startUs': 0, 'endUs': 1}})


def test_model_scores_and_selection_do_not_close_observations():
    candidate, selection = documents()[4:6]
    for document in (candidate, selection):
        assert all(item['status'] == 'unknown' for item in document.data.observations.model_dump().values())
    with pytest.raises(ValidationError):
        Observation(status='observed')
    with pytest.raises(ValidationError):
        RetrievalReason(channel='visual', rank=1, score=float('nan'))
    assert Observation(status='observed', basis='实际看了当前窗口', observer='assistant').status == 'observed'


def test_receipt_requires_registered_identity_and_verified_source_mapping():
    value = documents()[-1].data.model_dump()
    with pytest.raises(ValidationError):
        ReceiptData.model_validate({**value, 'status': 'committed'})
    with pytest.raises(ValidationError):
        ReceiptData.model_validate({**value, 'sourceRange': {'startUs': 1, 'endUs': 2}})


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), float('-inf')])
def test_nested_nonfinite_values_are_rejected_at_material_entry(bad):
    for document in (documents()[2], documents()[3], documents()[5]):
        value = document.model_dump(mode='json')
        value['data']['toolchain'] = {'nested': [{'number': bad}]}
        with pytest.raises(MaterialError, match='素材工作材料'):
            parse_document(value)
    value = documents()[3].model_dump(mode='json')
    value['data']['config'] = {'nested': [bad]}
    with pytest.raises(MaterialError):
        parse_document(value)


def test_receipt_verified_mapping_must_match_exact_local_window():
    value = documents()[-1].data.model_dump()
    value.update(timeline=Timeline(sourceMapping=SourceMapping(status='verified', method='full',
                 sourceOriginUs=0, maxErrorUs=0)), localRange=TimeRange(startUs=0, endUs=1_000_000))
    with pytest.raises(ValidationError, match='完全一致'):
        ReceiptData.model_validate({**value, 'sourceRange': TimeRange(startUs=10_000_000, endUs=11_000_000)})
    assert ReceiptData.model_validate({**value, 'sourceRange': value['localRange']}).sourceRange == value['localRange']
    with pytest.raises(ValidationError):
        ReceiptData.model_validate({**value, 'localRange': None, 'sourceRange': value['localRange']})


def test_versioned_collections_are_homogeneous_and_have_unique_ids():
    from m2v.materials.contracts import Collection, parse_collection
    req = documents()[0]
    collection = Collection(id='req-list', kind='material.requirements', data=[req])
    assert parse_collection(json.loads(collection.model_dump_json())) == collection
    for mutation in ({'schemaVersion': 2}, {'kind': 'material.sources'}, {'data': [req, req]}):
        with pytest.raises(MaterialError):
            parse_collection({**collection.model_dump(mode='json'), **mutation})


def test_ids_timestamps_and_fingerprints_are_deterministic_and_timezone_aware():
    assert fingerprint({'b': 1, 'a': 2}) == fingerprint({'a': 2, 'b': 1})
    value = documents()[0].model_dump(mode='json')
    for change in ({'id': '../escape'}, {'createdAt': '2026-11-14T10:00:00'}):
        with pytest.raises(MaterialError):
            parse_document({**value, **change})
