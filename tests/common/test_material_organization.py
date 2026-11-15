"""长期组织、多库浏览隔离、只读访问与相似分组的行为边界。"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sqlite3

import numpy as np
from PIL import Image
import pytest

from m2v.materials import cli, indexing, library_view, organization, similarity
from m2v.materials.contracts import EmbeddingSpec, Media, MediaData, Probe, Source, SourceData
from m2v.materials.errors import MaterialError
from m2v.materials.store import MaterialStore


def _media(store, tmp_path, name='shared', color='navy', title='厨房备餐'):
    image = tmp_path / f'{name}.png'
    Image.new('RGB', (32, 24), color).save(image)
    source = Source(id='source-' + name, data=SourceData(provider='local', title=title))
    store.put(source)
    return store.put(Media(id='media-' + name, data=MediaData(sourceId=source.id,
        artifact=store.publish_file(image), fetchIdentity='a' * 64,
        probe=Probe(kind='image', container='png', width=32, height=24))))


def test_annotations_survive_reopen_filter_remove_and_keep_identity(tmp_path):
    root = tmp_path / 'work'
    with MaterialStore(root) as store:
        media = _media(store, tmp_path)
        original = store.get(media.id).model_dump(mode='json')
        result = organization.annotate(store, media.id, tags=['厨房', 'FOOD'], collections=['日常'], favorite=True)
        assert result['tags'] == ['food', '厨房']
        assert store.get(media.id).model_dump(mode='json') == original
    with MaterialStore(root, readonly=True) as store:
        found = organization.list_media(store, tags=['FOOD'], collection='日常', favorites=True, query='厨房')
        assert [row['mediaId'] for row in found['items']] == [media.id]
        with pytest.raises(sqlite3.OperationalError):
            store.connection.execute('DELETE FROM documents')
        before = set(store.root.rglob('*'))
        with pytest.raises(MaterialError) as blocked:
            store.publish_bytes(b'forbidden')
        assert blocked.value.code == 'read-only' and set(store.root.rglob('*')) == before
    with MaterialStore(root) as store:
        organization.annotate(store, media.id, remove_tags=['food'], remove_collections=['日常'], favorite=False)
        assert not organization.list_media(store, favorites=True)['items']
        assert organization.annotation(store, media.id)['tags'] == ['厨房']
        before = organization.annotation(store, media.id)
        for kwargs in ({'tags':['bad\x00tag']}, {'favorite':'true'}, {'tags':['same'],'remove_tags':['SAME']}):
            with pytest.raises(MaterialError):
                organization.annotate(store, media.id, **kwargs)
        assert organization.annotation(store, media.id) == before
        with pytest.raises(MaterialError):
            organization.annotate(store, 'missing', tags=['x'])


def test_multi_library_browse_preserves_duplicate_ids_and_escapes_text(tmp_path):
    roots = [tmp_path / 'one', tmp_path / 'two']
    for index, root in enumerate(roots):
        with MaterialStore(root) as store:
            media = _media(store, tmp_path, color=['navy','red'][index], title='<script>alert("x")</script> 厨房')
            if index == 0:
                organization.annotate(store, media.id, tags=['备餐'], favorite=True)
    before = [hashlib.sha256((root/'catalog.sqlite3').read_bytes()).hexdigest() for root in roots]
    result = library_view.browse(roots, tmp_path / 'view')
    assert len(result['items']) == 2 and len({item['libraryId'] for item in result['items']}) == 2
    assert len({item['mediaId'] for item in result['items']}) == 1
    assert all((tmp_path/'view'/item['thumbnail']).is_file() for item in result['items'])
    page = Path(result['html']).read_text(encoding='utf-8')
    assert '<script>alert(' not in page and '&lt;script&gt;' in page
    assert "script-src 'sha256-" in page and "connect-src 'none'" in page
    assert page.count('<script>') == 1
    assert before == [hashlib.sha256((root/'catalog.sqlite3').read_bytes()).hexdigest() for root in roots]
    with pytest.raises(MaterialError):
        library_view.browse([tmp_path/'missing'], tmp_path/'bad-view')
    assert not (tmp_path/'missing').exists()


def _visual(store, media, angle, revision='a' * 40):
    artifact, records = indexing._publish_records(store, [{'id':'frame', 'channel':'visual',
        'frame':media.data.artifact.model_dump(mode='json'), 'vectorRow':0,
        'origin':'test', 'alignment':'not-applicable'}])
    vector = np.array([[math.cos(angle), math.sin(angle)]], dtype='float32')
    vectors = indexing._publish_vectors(store, vector)
    spec = EmbeddingSpec(model='test-visual', revision=revision, weightsSha256='a' * 64,
                         preprocessing='test', dimensions=2)
    return indexing._store_index(store, media=media, channel='visual', config={}, records=records,
        artifacts=[artifact,vectors], inputs=[], cache_key=media.id, warnings=[], embedding_spec=spec)


def test_similar_groups_require_direct_representative_and_separate_models(tmp_path):
    with MaterialStore(tmp_path/'work') as store:
        for name, angle, revision in [('a',0,'a'*40),('b',math.pi/6,'a'*40),('c',math.pi/3,'a'*40),('d',0,'b'*40)]:
            _visual(store, _media(store,tmp_path,name), angle, revision)
        original = len(store.documents('material.media'))
        result = similarity.similar(store, threshold=.8)
        assert len(result['groups']) == 1
        assert {item['mediaId'] for item in result['groups'][0]['members']} == {'media-a','media-b'}
        assert result['modelSpaces'] == 2 and len(store.documents('material.media')) == original
        assert similarity.similar(store, threshold=.8, max_items=2)['truncated']
        with pytest.raises(MaterialError):
            similarity.similar(store, threshold=float('nan'))


def test_organization_cli_annotates_lists_and_browses(tmp_path, capsys):
    root = tmp_path/'work'
    with MaterialStore(root) as store:
        media = _media(store,tmp_path)
    common = ['--workspace',str(root),'--json']
    assert cli.main(['library','annotate',*common,'--media',media.id,'--tag','厨房','--favorite','yes']) == 0
    capsys.readouterr()
    assert cli.main(['library','list',*common,'--tag','厨房','--favorites']) == 0
    assert len(json.loads(capsys.readouterr().out)['items']) == 1
    assert cli.main(['library','browse',*common,'--out',str(tmp_path/'view')]) == 0
    assert Path(json.loads(capsys.readouterr().out)['html']).is_file()
