"""检索通道、RRF 融合、观察未知与过期/不兼容索引排除。"""
from __future__ import annotations

import numpy as np
import pytest

from m2v.materials import indexing, retrieval
from m2v.materials.contracts import (Artifact, EmbeddingSpec, Media, MediaData, Probe, Requirement,
                                     RequirementData, Source, SourceData, TimeBase, TimeRange, fingerprint)
from m2v.materials.errors import MaterialError
from m2v.materials.model_manager import ModelManager
from m2v.materials.store import MaterialStore


def _video_media(store, source, payload=b'video-bytes'):
    import hashlib
    artifact = store.publish_bytes(payload)
    media = Media(id=f'media-{hashlib.sha256(payload).hexdigest()[:12]}', data=MediaData(
        sourceId=source.id, artifact=artifact, fetchIdentity='a' * 64,
        probe=Probe(kind='video', container='mp4', width=64, height=48, durationUs=4_000_000,
                    fps=TimeBase(num=10, den=1), hasAudio=False)))
    return store.put(media)


def _source(store, title='上海城市夜景航拍'):
    source = Source(id='source-1', data=SourceData(provider='local', title=title, author='本地作者'))
    return store.put(source)


def _records_index(store, media, monkeypatch, **kwargs):
    artifact, checked = indexing._publish_records(store, kwargs.pop('records'))
    return indexing._store_index(store, media=media, channel=kwargs.pop('channel'),
                                 config=kwargs.pop('config', {}), records=checked,
                                 artifacts=[artifact], inputs=[], cache_key=kwargs.pop('cache'),
                                 warnings=[])


def _caption_record(start=0, end=2_000_000, text='城市夜景亮起'):
    return {'id': f'captions-{start}', 'channel': 'captions', 'text': text,
            'localRange': {'startUs': start, 'endUs': end}, 'language': 'zh',
            'alignment': 'unverified', 'origin': 'captions-manual'}


def test_lexical_hits_keep_unknown_observations_and_identity_limit(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        source = _source(store)
        media = _video_media(store, source)
        _records_index(store, media, None, records=[_caption_record()], channel='captions', cache='cap')
        requirement = Requirement(id='req-1', data=RequirementData(
            text='找到上海城市夜景，必须是该城市实拍', identity={'entity': '上海', 'mustMatch': True}))
        result = retrieval.find(store, requirement=requirement, channels=('lexical',), top_k=5)
        assert len(result.candidates) == 1
        candidate = result.candidates[0]
        assert candidate.observations.factualIdentityMatch.status == 'unknown'
        assert candidate.localRange == TimeRange(startUs=0, endUs=2_000_000)
        assert candidate.sourceRange is None  # 未验证映射不导出精确源区间
        assert any('身份' in note for note in candidate.limitations)
        assert candidate.retrievalReasons[0].channel == 'captions'
        assert result.channels['lexical'] >= 1


def test_metadata_and_lexical_rrf_fuse_without_raw_score_mixing(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        source = _source(store)
        media = _video_media(store, source)
        _records_index(store, media, None, records=[_caption_record()], channel='captions', cache='cap')
        single = retrieval.find(store, query='城市夜景', channels=('lexical',), top_k=5)
        both = retrieval.find(store, query='城市夜景', channels=('lexical', 'metadata'), top_k=5)
        assert single.candidates and both.candidates
        assert both.candidates[0].fusionScore > single.candidates[0].fusionScore
        channels = {(reason.channel) for reason in both.candidates[0].retrievalReasons}
        assert {'captions', 'metadata'} <= channels


def test_semantic_text_and_visual_require_matching_model_and_are_separable(tmp_path, monkeypatch):
    manager = ModelManager(tmp_path / 'models')
    with MaterialStore(tmp_path / 'library') as store:
        source = _source(store)
        media = _video_media(store, source)
        text_identity = manager.identity('e5-small')
        visual_identity = manager.identity('siglip2-base')
        media_artifact = media.data.artifact

        def semantic_index(channel, model, identity, dimension):
            records = [
                {'id': f'{channel}-0', 'channel': channel, 'text': '城市夜景亮起',
                 'localRange': {'startUs': 0, 'endUs': 900_000}, 'vectorRow': 0,
                 'alignment': 'not-applicable', 'origin': channel},
                {'id': f'{channel}-1', 'channel': channel, 'text': '高山湖泊',
                 'localRange': {'startUs': 1_000_000, 'endUs': 1_900_000}, 'vectorRow': 1,
                 'alignment': 'not-applicable', 'origin': channel},
            ]
            artifact, checked = indexing._publish_records(store, records)
            matrix = np.zeros((2, dimension), dtype='float32')
            matrix[0, 0] = 1.0
            matrix[1, 1] = 1.0
            vectors = indexing._publish_vectors(store, matrix)
            spec = EmbeddingSpec(model=model, revision=identity['revision'],
                                 weightsSha256=next(item['sha256'] for item in identity['files']
                                                    if item['path'] == 'model.safetensors'),
                                 preprocessing=identity['preprocessing'], dimensions=dimension)
            data = indexing.IndexData(mediaId=media.id, mediaSha256=media_artifact.sha256,
                channel=channel, status='complete', config={}, configSha256='b' * 64,
                toolchain={}, timelineMappingSha256=fingerprint(media.data.probe.timeline),
                artifacts=[artifact, vectors], recordCount=2, embeddingSpec=spec)
            document = store.put(indexing.Index(id=f'index-{channel}', data=data))
            store.add_records(document.id, checked, tokenize=indexing.tokens)
            return document

        semantic_index('text', 'e5-small', text_identity, 384)
        semantic_index('visual', 'siglip2-base', visual_identity, 768)

        def query_texts(manager, texts, *, prefix, batch_size=16):
            return np.tile(np.array([[1.0] + [0.0] * 383], dtype='float32'), (len(texts), 1))

        monkeypatch.setattr('m2v.materials.embedding.embed_texts', query_texts)
        monkeypatch.setattr('m2v.materials.embedding.embed_visual_text',
                            lambda manager, texts: np.tile(np.array([[1.0] + [0.0] * 767], dtype='float32'), (len(texts), 1)))
        found = retrieval.find(store, query='城市夜景', manager=manager,
                               channels=('text', 'visual'), top_k=5)
        assert found.candidates
        reasons = [reason for candidate in found.candidates for reason in candidate.retrievalReasons]
        assert {reason.channel for reason in reasons} == {'text', 'visual'}
        assert reasons[0].modelIdentity and '@' in reasons[0].modelIdentity

        # 模型身份不匹配时视觉索引被明确排除，而不是混查。
        original = ModelManager.identity

        def different(self, name):
            value = original(self, name)
            value['revision'] = 'f' * 40
            return value

        monkeypatch.setattr(ModelManager, 'identity', different)
        excluded = retrieval.find(store, query='城市夜景', manager=manager, channels=('visual',), top_k=5)
        assert excluded.candidates == []
        assert any('模型身份' in item['note'] for item in excluded.excluded)


def test_expired_media_and_url_queries_are_reported_not_faked(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        source = _source(store)
        media = _video_media(store, source)
        _records_index(store, media, None, records=[_caption_record()], channel='captions', cache='cap')
        other = _video_media(store, source, payload=b'other-video-bytes')
        result = retrieval.find(store, query='城市夜景', channels=('lexical',), media_ids=[other.id], top_k=5)
        assert result.candidates == []  # 另一个媒体的有效索引不会冒充
        (store.path(media.data.artifact.path, exists=True)).unlink()
        broken = retrieval.find(store, query='城市夜景', channels=('lexical',), media_ids=[media.id], top_k=5)
        assert broken.candidates == []
        assert broken.excluded and broken.excluded[0]['reason'] in {'not-found', 'security-blocked'}
        with pytest.raises(Exception):
            retrieval.find(store, query='https://example.com/x', channels=('lexical',))


def test_metadata_filters_limit_media_without_touching_indexes(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        source = _source(store)
        media = _video_media(store, source)
        _records_index(store, media, None, records=[_caption_record()], channel='captions', cache='cap')
        kept = retrieval.find(store, query='城市夜景', channels=('lexical',), orientation='landscape',
                              min_duration_us=1_000_000, provider='local', top_k=5)
        assert kept.candidates
        for kwargs in ({'orientation': 'portrait'}, {'min_duration_us': 5_000_000},
                       {'provider': 'commons'}):
            filtered = retrieval.find(store, query='城市夜景', channels=('lexical',), top_k=5, **kwargs)
            assert filtered.candidates == []
            assert any(item['reason'] == 'metadata-filter' for item in filtered.excluded)
        with pytest.raises(MaterialError):
            retrieval.find(store, query='城市夜景', channels=('lexical',), orientation='diagonal')


def test_find_reuses_ad_hoc_requirement_and_does_not_build_indexes(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        source = _source(store)
        media = _video_media(store, source)
        before = len(store.documents('material.index'))
        empty = retrieval.find(store, query='城市夜景', channels=('lexical',), top_k=5)
        assert empty.candidates == [] and empty.channels['lexical'] == 0
        assert len(store.documents('material.index')) == before
        again = retrieval.find(store, query='城市夜景', channels=('lexical',), top_k=5)
        assert again.requirement.id == empty.requirement.id
        assert len(store.documents('material.requirement')) == 1
