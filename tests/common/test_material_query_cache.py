"""每次请求每种模型只编码一次，并先排除不兼容空间。"""
from __future__ import annotations

import numpy as np

from m2v.materials import embedding, indexing, retrieval
from m2v.materials.contracts import EmbeddingSpec, Media, MediaData, Probe, Source, SourceData
from m2v.materials.model_manager import ModelManager
from m2v.materials.store import MaterialStore


def test_query_encoding_is_per_request_channel_not_per_media(tmp_path, monkeypatch):
    calls = {'text':0, 'visual':0}
    def encode(channel, dimensions, texts):
        calls[channel] += 1
        vectors = np.zeros((len(texts), dimensions), dtype='float32')
        vectors[0,0] = 1
        vectors[1:,1] = 1
        return vectors
    monkeypatch.setattr(embedding, 'embed_texts', lambda manager,texts,**kwargs:encode('text',384,texts))
    monkeypatch.setattr(embedding, 'embed_visual_text', lambda manager,texts:encode('visual',768,texts))
    manager = ModelManager(tmp_path/'models')
    with MaterialStore(tmp_path/'work') as store:
        source = Source(id='source', data=SourceData(provider='local',title='样本'))
        store.put(source)
        for number in range(3):
            media = store.put(Media(id=f'media-{number}', data=MediaData(sourceId=source.id,
                artifact=store.publish_bytes(str(number).encode()), fetchIdentity='a'*64,
                probe=Probe(kind='image',container='png',width=32,height=24))))
            for channel,model,dimensions in [('text','e5-small',384),('visual','siglip2-base',768)]:
                artifact,records = indexing._publish_records(store,[{'id':'record','channel':channel,'text':'相关内容',
                    'vectorRow':0,'origin':'test','alignment':'not-applicable'}])
                matrix = np.zeros((1,dimensions),dtype='float32')
                matrix[0,0] = 1
                identity = manager.identity(model)
                spec = EmbeddingSpec(model=model,revision=identity['revision'],
                    weightsSha256=next(item['sha256'] for item in identity['files'] if item['path']=='model.safetensors'),
                    preprocessing=identity['preprocessing'],dimensions=dimensions)
                indexing._store_index(store,media=media,channel=channel,config={},records=records,
                    artifacts=[artifact,indexing._publish_vectors(store,matrix)],inputs=[],cache_key=f'{channel}-{number}',
                    warnings=[],embedding_spec=spec)
        result = retrieval.find(store,query='第一条查询',channels=('text','visual'),manager=manager)
        assert len(result.candidates) == len({candidate.mediaId for candidate in result.candidates}) == 3
        assert all({reason.channel for reason in item.retrievalReasons} == {'text','visual'} for item in result.candidates)
        assert calls == result.stats['queryEncodingBatches'] == {'text':1,'visual':1}
        retrieval.find(store,query='第二条查询',channels=('text','visual'),manager=manager)
        assert calls == {'text':2,'visual':2}
        original = manager.identity
        def incompatible(name):
            value = original(name)
            value['preprocessing'] = 'incompatible'
            return value
        monkeypatch.setattr(manager,'identity',incompatible)
        result = retrieval.find(store,query='无效模型查询',channels=('text','visual'),manager=manager)
        assert not result.candidates and result.excluded
        assert calls == {'text':2,'visual':2} and not result.stats['queryEncodingBatches']
