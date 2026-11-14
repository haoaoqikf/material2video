"""工作库的不可变发布、事务与恢复；无需真实下载或模型。"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from m2v.materials.contracts import Media, MediaData, Probe, Requirement, RequirementData, Source, SourceData
from m2v.materials.errors import MaterialError
from m2v.materials.store import MaterialStore, no_links, workspace_root


def source(name='source-1'):
    return Source(id=name, data=SourceData(provider='local', title='原始素材'))


def test_workspace_requires_explicit_context_and_does_not_touch_project_schema(tmp_path):
    with pytest.raises(MaterialError, match='workspace'):
        workspace_root()
    assert workspace_root(project=tmp_path) == tmp_path / 'outputs/materials'
    assert workspace_root(project=tmp_path, workspace=tmp_path / 'explicit') == tmp_path / 'explicit'


def test_file_dedup_does_not_merge_different_sources(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        artifact = store.publish_bytes(b'same bytes')
        assert store.publish_bytes(b'same bytes') == artifact
        for name in ('source-1', 'source-2'):
            store.put(source(name))
            media = Media(id=name.replace('source', 'media'), data=MediaData(
                sourceId=name, artifact=artifact, fetchIdentity='a' * 64,
                probe=Probe(kind='image', container='test', width=1, height=1)))
            store.put(media)
        assert len(store.documents('material.source')) == 2
        assert len(store.documents('material.media')) == 2
        assert store.connection.execute('SELECT count(*) FROM artifacts').fetchone()[0] == 1
        assert store.connection.execute('SELECT count(*) FROM document_artifacts').fetchone()[0] == 2


def test_document_immutability_cache_and_snapshot_recovery(tmp_path, monkeypatch):
    with MaterialStore(tmp_path) as store:
        record = Requirement(id='req-1', data=RequirementData(text='对象动作'))
        store.put(record, cache_key='request-key')
        assert store.cached('request-key') == record
        assert store.cached('missing') is None
        assert store.put(record) == record
        changed = record.model_copy(update={'data': RequirementData(text='另一个对象')})
        with pytest.raises(MaterialError, match='不同内容'):
            store.put(changed)
        path = store.export(record.id)
        path.unlink()
        assert json.loads(store.export(record.id).read_text(encoding='utf-8'))['id'] == record.id
        monkeypatch.setattr('m2v.materials.store.atomic_text', lambda *_: (_ for _ in ()).throw(OSError('disk')))
        second = Requirement(id='req-2', data=RequirementData(text='记录已提交，快照可补'))
        store.put(second)
        assert store.get('req-2') == second


def test_object_hash_drift_does_not_get_overwritten(tmp_path):
    with MaterialStore(tmp_path) as store:
        artifact = store.publish_bytes(b'original')
        path = store.verify_artifact(artifact)
        path.write_bytes(b'changed!')
        with pytest.raises(MaterialError, match='摘要'):
            store.verify_artifact(artifact)
        with pytest.raises(MaterialError, match='损坏'):
            store.publish_bytes(b'original')
        assert path.read_bytes() == b'changed!'


def test_missing_references_and_transaction_abort_leave_no_document(tmp_path):
    with MaterialStore(tmp_path) as store:
        record = source()
        with pytest.raises(MaterialError, match='关系缺失'):
            store.put(record, references=['nonexistent'])
        assert store.documents('material.source') == []
        with pytest.raises(RuntimeError):
            with store.transaction() as db:
                db.execute('INSERT INTO operations VALUES(?,?,?,?)', ('op', 'pending', '{}', 'time'))
                raise RuntimeError('crash')
        assert store.operation('op') is None


def test_crash_after_file_publish_leaves_only_recoverable_unreferenced_object(tmp_path, monkeypatch):
    with MaterialStore(tmp_path) as store:
        artifact = store.publish_bytes(b'complete before document commit')
        assert store.verify_artifact(artifact).is_file()
        assert not store.documents('material.media')
        assert store.connection.execute('SELECT count(*) FROM document_artifacts').fetchone()[0] == 0
        store.operation('op-1', status='pending', payload={'sha256': artifact.sha256})
    with MaterialStore(tmp_path) as recovered:
        assert recovered.operation('op-1')['status'] == 'pending'
        assert recovered.verify_artifact(artifact).is_file()
        recovered.operation('op-1', status='committed', payload={'sha256': artifact.sha256})
        assert recovered.operation('op-1')['status'] == 'committed'


def test_invalid_version_corruption_and_storage_escape(tmp_path):
    with MaterialStore(tmp_path) as store:
        record = source()
        store.put(record)
        for reference in ('../x', '/outside', 'C:/outside', 'a/../x', 'x:stream'):
            with pytest.raises(MaterialError, match='路径'):
                store.path(reference)
        with pytest.raises(MaterialError, match='种类'):
            store.get(record.id, kind='material.media')
        store.connection.execute("UPDATE documents SET payload='{}' WHERE id=?", (record.id,))
        with pytest.raises(MaterialError, match='损坏'):
            store.get(record.id)
        store.connection.execute('PRAGMA user_version=2')
    with pytest.raises(MaterialError, match='版本'):
        MaterialStore(tmp_path)


def test_publish_budget_and_failed_delivery_preserve_existing(tmp_path, monkeypatch):
    with MaterialStore(tmp_path) as store:
        old = store.publish_bytes(b'old')
        with pytest.raises(MaterialError, match='预算'):
            store.publish_bytes(b'too large', max_bytes=3)
        monkeypatch.setattr('m2v.materials.store.deliver', lambda *_: (_ for _ in ()).throw(OSError('crash')))
        with pytest.raises(OSError):
            store.publish_bytes(b'new unpublished bytes')
        assert store.verify_artifact(old).read_bytes() == b'old'
        assert not list((tmp_path / 'staging').iterdir())
        assert store.connection.execute('SELECT count(*) FROM artifacts').fetchone()[0] == 1


def _indexed_video(store):
    from m2v.materials.contracts import Index, IndexData, IndexRecord, TimeRange, canonical, fingerprint
    store.put(source())
    artifact = store.publish_bytes(b'video fixture bytes')
    media = Media(id='media-1', data=MediaData(sourceId='source-1', artifact=artifact,
                  fetchIdentity='b' * 64, probe=Probe(kind='video', container='test', width=10, height=10, durationUs=2_000_000)))
    store.put(media)
    record = IndexRecord(id='record-1', channel='captions', text='实际动作',
                         localRange=TimeRange(startUs=0, endUs=1_000_000), origin='manual')
    records = store.publish_bytes(canonical([record.model_dump(mode='json')]).encode('utf-8'))
    index = Index(id='index-1', data=IndexData(mediaId=media.id, mediaSha256=artifact.sha256,
                  channel='captions', status='complete', configSha256='c' * 64,
                  timelineMappingSha256=fingerprint(media.data.probe.timeline), artifacts=[records], recordCount=1))
    store.put(index)
    return media, index, record


def test_completed_index_records_bind_exact_immutable_artifact_set(tmp_path):
    from m2v.materials.contracts import IndexRecord
    with MaterialStore(tmp_path) as store:
        _, index, record = _indexed_video(store)
        with pytest.raises(MaterialError, match='未完整发布'):
            store.records(index.id)
        store.add_records(index.id, [record], tokenize=lambda text: [text])
        store.add_records(index.id, [record], tokenize=lambda text: [text])
        assert store.records(index.id) == [record]
        for mutated in ([record.model_copy(update={'id': 'record-2'})],
                        [record.model_copy(update={'text': '不同内容'})]):
            with pytest.raises(MaterialError, match='不可变产物集合'):
                store.add_records(index.id, mutated)
        with pytest.raises(MaterialError, match='条目数'):
            store.add_records(index.id, [record, record])
        with pytest.raises(MaterialError, match='跨通道'):
            store.add_records(index.id, [record.model_copy(update={'channel': 'visual'})])
        assert len(store.records(index.id)) == 1


def test_idempotent_put_does_not_silently_drop_new_refs_or_cache_key(tmp_path):
    with MaterialStore(tmp_path) as store:
        store.put(source('source-a'))
        store.put(source('source-b'))
        req = Requirement(id='request', data=RequirementData(text='镜头'))
        store.put(req, references=['source-a'])
        with pytest.raises(MaterialError, match='引用或缓存'):
            store.put(req, references=['source-b'], cache_key='new-key')
        with pytest.raises(MaterialError, match='引用或缓存'):
            store.put(req, references=['source-a'], cache_key='new-key')
        assert store.cached('new-key') is None
        assert store.put(req, references=['source-a']) == req


def test_reference_kind_digest_range_and_mapping_bindings(tmp_path):
    from m2v.materials.contracts import Candidate, CandidateData, RetrievalReason, TimeRange, fingerprint
    with MaterialStore(tmp_path) as store:
        req = Requirement(id='request', data=RequirementData(text='镜头'))
        store.put(req)
        artifact = store.publish_bytes(b'bytes')
        bad = Media(id='wrong-source', data=MediaData(sourceId=req.id, artifact=artifact, fetchIdentity='a' * 64,
                    probe=Probe(kind='image', container='test', width=1, height=1)))
        with pytest.raises(MaterialError, match='种类'):
            store.put(bad)
        media, index, _ = _indexed_video(store)
        data = CandidateData(requirementId=req.id, requirementDigest=fingerprint(req), sourceId='source-1',
               mediaId=media.id, mediaSha256=media.data.artifact.sha256, indexIds=[index.id],
               localRange=TimeRange(startUs=0, endUs=1_000_000), timelineMappingSha256=fingerprint(media.data.probe.timeline),
               retrievalReasons=[RetrievalReason(channel='captions', rank=1, score=1.0)], fusionScore=0.01)
        for update in ({'mediaSha256': '0' * 64}, {'requirementDigest': '0' * 64},
                       {'localRange': TimeRange(startUs=0, endUs=3_000_000)},
                       {'sourceRange': TimeRange(startUs=0, endUs=1_000_000)},
                       {'timelineMappingSha256': '0' * 64}):
            with pytest.raises(MaterialError):
                store.put(Candidate(id='bad-candidate', data=data.model_copy(update=update)))
        assert store.documents('material.candidate') == []
        store.put(Candidate(id='good-candidate', data=data))


def test_receipt_cannot_change_selection_source_or_output_identity(tmp_path):
    from m2v.materials.contracts import (Candidate, CandidateData, Receipt, ReceiptData, RetrievalReason,
                                       Selection, SelectionData, TimeRange, fingerprint)
    with MaterialStore(tmp_path) as store:
        media, index, _ = _indexed_video(store)
        req = Requirement(id='request', data=RequirementData(text='动作'))
        store.put(req)
        window = TimeRange(startUs=0, endUs=1_000_000)
        candidate = Candidate(id='candidate', data=CandidateData(requirementId=req.id, requirementDigest=fingerprint(req),
            sourceId='source-1', mediaId=media.id, mediaSha256=media.data.artifact.sha256, indexIds=[index.id],
            localRange=window, timelineMappingSha256=fingerprint(media.data.probe.timeline),
            retrievalReasons=[RetrievalReason(channel='captions', rank=1, score=1.0)], fusionScore=0.01))
        store.put(candidate)
        output = store.publish_bytes(b'clip bytes')
        selection = Selection(id='selection', data=SelectionData(candidateId=candidate.id,
            candidateDigest=fingerprint(candidate), mediaId=media.id, mediaSha256=media.data.artifact.sha256,
            localRange=window, decision='chosen', rationale='已查看', purpose='过程', operator='assistant',
            outputArtifact=output))
        store.put(selection)
        data = ReceiptData(operationId='op', selectionId=selection.id, selectionDigest=fingerprint(selection),
            sourceId='source-1', inputMediaSha256=media.data.artifact.sha256, localRange=window,
            timeline=media.data.probe.timeline, outputArtifactSha256=output.sha256,
            manifestSha256='a' * 64, targetProjectId='film', targetAssetId='clip', status='pending')
        for update in ({'sourceUrl': 'https://example.org/forged'}, {'outputArtifactSha256': '0' * 64},
                       {'upstreamFullSha256': '0' * 64}, {'selectionDigest': '0' * 64}):
            with pytest.raises(MaterialError, match='未绑定'):
                store.put(Receipt(id='bad-receipt', data=data.model_copy(update=update)))
        store.put(Receipt(id='good-receipt', data=data))


def test_symlink_in_any_root_or_child_ancestor_is_rejected(tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip('宿主未开放符号链接创建权限')
    with pytest.raises(MaterialError, match='链接'):
        MaterialStore(link / 'nested')
    with MaterialStore(real) as store:
        child = real / 'linked'
        child.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(MaterialError, match='路径'):
            store.path('linked/outside')


@pytest.mark.skipif(os.name != 'nt', reason='Windows junction 边界')
def test_windows_junction_root_is_not_resolved_away(tmp_path):
    real = tmp_path / 'target'
    real.mkdir()
    junction = tmp_path / 'junction'
    completed = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(real)], capture_output=True)
    if completed.returncode:
        pytest.skip('宿主不允许创建 junction')
    try:
        with pytest.raises(MaterialError, match='目录联接'):
            no_links(junction / 'new')
    finally:
        # rmdir 只移除已核对路径的 junction 本身，不删除其指向目录。
        assert junction.parent == tmp_path and junction.is_junction()
        junction.rmdir()
        assert real.is_dir()
