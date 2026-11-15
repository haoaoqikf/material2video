"""无字幕来源文字的语义输入、原文出处与缓存绑定。"""
from __future__ import annotations

import numpy as np
import pytest

from m2v.materials import embedding, indexing, retrieval
from m2v.materials.contracts import Media, MediaData, Probe, Source, SourceData, fingerprint
from m2v.materials.contracts import EmbeddingSpec
from m2v.materials.model_manager import ModelManager
from m2v.materials.store import MaterialStore


def test_source_text_index_without_captions_keeps_original_evidence_and_reuses(tmp_path, monkeypatch):
    calls = []
    def encode(manager, texts, *, prefix, batch_size=16):
        calls.append((prefix, texts))
        vectors = np.zeros((len(texts), 384), dtype='float32')
        for row, text in enumerate(texts):
            vectors[row, 0 if 'cooking' in text or '厨房' in text else 1] = 1
        return vectors
    monkeypatch.setattr(embedding, 'embed_texts', encode)
    manager = ModelManager(tmp_path / 'models')
    with MaterialStore(tmp_path / 'work') as store:
        source = Source(id='source-kitchen', data=SourceData(provider='commons',
            title='People cooking food', policy={'description': 'Volunteers preparing meals in a kitchen.'}))
        store.put(source)
        artifact = store.publish_bytes(b'fixture-image-bytes')
        media = Media(id='media-kitchen', data=MediaData(sourceId=source.id, artifact=artifact,
            fetchIdentity='a' * 64, probe=Probe(kind='image', container='png', width=32, height=24)))
        store.put(media)
        result = indexing.index_text(store, media, manager)
        records = store.records(result.document.id)
        assert records[0].text == 'People cooking food\nVolunteers preparing meals in a kitchen.'
        assert records[0].origin == 'e5-small:metadata' and records[0].localRange is None
        assert fingerprint({'sourceId': source.id, 'title': source.data.title,
                            'description': source.data.policy.description}) in result.document.data.inputDigests
        assert indexing.index_text(store, media, manager).reused
        assert len(calls) == 1
        found = retrieval.find(store, query='厨房备餐', channels=('text',), manager=manager)
        assert found.candidates and found.candidates[0].localRange is None
        assert found.candidates[0].retrievalReasons[0].channel == 'metadata'
        assert found.candidates[0].observations.actionComplete.status == 'unknown'


@pytest.mark.parametrize('channel,model,dimensions', [('text', 'e5-small', 384), ('visual', 'siglip2-base', 768)])
def test_background_contrast_rejects_high_scoring_distractor(tmp_path, monkeypatch, channel, model, dimensions):
    manager = ModelManager(tmp_path / 'models')
    def queries(manager, texts, **kwargs):
        vectors = np.zeros((len(texts), dimensions), dtype='float32')
        vectors[0, 0] = 1
        vectors[1:, :2] = [.6, .8]
        return vectors
    monkeypatch.setattr(embedding, 'embed_texts', queries)
    monkeypatch.setattr(embedding, 'embed_visual_text', queries)
    with MaterialStore(tmp_path / 'work') as store:
        source = Source(id='source', data=SourceData(provider='local', title='证据样本'))
        store.put(source)
        media = Media(id='media', data=MediaData(sourceId=source.id, artifact=store.publish_bytes(b'bytes'),
            fetchIdentity='a' * 64, probe=Probe(kind='image', container='png', width=32, height=24)))
        store.put(media)
        artifact, records = indexing._publish_records(store, [
            {'id':'good', 'channel':channel, 'text':'相关内容', 'origin':'test', 'vectorRow':0, 'alignment':'not-applicable'},
            {'id':'distractor', 'channel':channel, 'text':'无关内容', 'origin':'test', 'vectorRow':1, 'alignment':'not-applicable'}])
        matrix = np.zeros((2, dimensions), dtype='float32')
        matrix[0, 0] = 1
        matrix[1, :2] = [.8, .6]
        vector_artifact = indexing._publish_vectors(store, matrix)
        identity = manager.identity(model)
        spec = EmbeddingSpec(model=model, revision=identity['revision'],
            weightsSha256=next(item['sha256'] for item in identity['files'] if item['path']=='model.safetensors'),
            preprocessing=identity['preprocessing'], dimensions=dimensions)
        indexing._store_index(store, media=media, channel=channel, config={}, records=records,
            artifacts=[artifact,vector_artifact], inputs=[], cache_key='semantic', warnings=[], embedding_spec=spec)
        result = retrieval.find(store, query='对象与动作', channels=(channel,), manager=manager)
        assert result.candidates
        assert {reason.recordId for item in result.candidates for reason in item.retrievalReasons} == {'good'}
