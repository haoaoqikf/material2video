"""索引构建、增量复用、向量分片与依赖注入；真实模型推理另见评测记录。"""
from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
import pytest

from m2v.materials import fetch, indexing
from m2v.materials.contracts import (Artifact, EmbeddingSpec, Index, IndexData, Source, SourceData,
                                     TimeRange, fingerprint)
from m2v.materials.errors import MaterialError
from m2v.materials.model_manager import ModelManager
from m2v.materials.store import MaterialStore


def _clip(path: Path, *, seconds=3.0, audio=True):
    arguments = ['-f', 'lavfi', '-i', f'testsrc2=size=96x64:rate=10:duration={seconds}']
    if audio:
        arguments += ['-f', 'lavfi', '-i', f'sine=frequency=440:sample_rate=16000:duration={seconds}']
    arguments += ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
    if audio:
        arguments += ['-c:a', 'aac']
    process = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-nostdin', '-loglevel', 'error',
                              *arguments, str(path)], capture_output=True, timeout=60)
    assert process.returncode == 0, process.stderr.decode('utf-8', 'replace')
    return path


def _setup(tmp_path, *, captions=False):
    store = MaterialStore(tmp_path / 'library')
    source = Source(id='source-local', data=SourceData(provider='local', title='本地素材'))
    store.put(source)
    clip = _clip(tmp_path / 'clip.mp4')
    if captions:
        (tmp_path / 'clip.zh.srt').write_text(
            '1\n00:00:00,000 --> 00:00:01,500\n城市夜景亮起\n\n'
            '2\n00:00:01,500 --> 00:00:03,000\n人群在街道行走\n', encoding='utf-8')
    result = fetch.fetch_local(store, source=source, path=clip)
    return store, source, result.media


def _manager(tmp_path) -> ModelManager:
    return ModelManager(tmp_path / 'models')


def test_tokens_use_chinese_ngrams_and_latin_words():
    values = indexing.tokens('上海 城市夜景 skyline')
    assert '上海' in values and '城市' in values and '夜景' in values and 'skyline' in values


@pytest.mark.media
def test_shots_and_frames_are_bounded_and_reused_without_reinference(tmp_path):
    store, _, media = _setup(tmp_path)
    with store:
        first = indexing.index_shots(store, media, threshold=0.2, max_frames=6)
        assert [item.channel for item in first] == ['shots', 'frames']
        frames = store.records(first[1].document.id)
        assert 1 <= len(frames) <= 6
        for record in frames:
            store.verify_artifact(record.frame)
            assert record.localRange and record.localRange.endUs > record.localRange.startUs
        count = store.connection.execute('SELECT count(*) FROM documents').fetchone()[0]
        second = indexing.index_shots(store, media, threshold=0.2, max_frames=6)
        assert all(item.reused for item in second)
        assert store.connection.execute('SELECT count(*) FROM documents').fetchone()[0] == count


@pytest.mark.media
def test_caption_index_keeps_language_alignment_and_tokens(tmp_path):
    store, _, media = _setup(tmp_path, captions=True)
    with store:
        result = indexing.index_captions(store, media)
        assert result.records == 2
        records = store.records(result.document.id)
        assert records[0].language == 'zh' and records[0].alignment == 'unverified'
        assert records[0].origin == 'captions-local'
        rows = store.connection.execute(
            'SELECT count(*) FROM tokens WHERE index_id=? AND token IN (?,?)',
            (result.document.id, '城市', '夜景')).fetchone()[0]
        assert rows >= 2
        cached = indexing.index_captions(store, media)
        assert cached.reused is True and cached.document.id == result.document.id
        with pytest.raises(MaterialError) as missing:
            indexing.index_chapters(store, media)
        assert missing.value.code == 'not-found'


@pytest.mark.media
def test_asr_backend_is_injected_and_cached(tmp_path, monkeypatch):
    store, _, media = _setup(tmp_path)
    calls = []

    class Word:
        def __init__(self, word, start, end, probability):
            self.word, self.start, self.end, self.probability = word, start, end, probability

    class Segment:
        def __init__(self):
            self.text = '  城市夜景亮起 '
            self.start, self.end, self.avg_logprob = 0.2, 1.8, -0.3
            self.words = [Word('城市', 0.2, 0.9, 0.9), Word('夜景', 0.9, 1.8, 0.8)]

    class WhisperModel:
        def __init__(self, *args, **kwargs):
            calls.append(kwargs)

        def transcribe(self, path, **kwargs):
            return iter([Segment()]), types.SimpleNamespace(language='zh', duration=3.0)

    module = types.ModuleType('faster_whisper')
    module.WhisperModel = WhisperModel
    monkeypatch.setitem(sys.modules, 'faster_whisper', module)
    monkeypatch.setattr(ModelManager, 'path', lambda self, name: tmp_path / 'models' / name)
    with store:
        result = indexing.index_asr(store, media, _manager(tmp_path))
        assert result.records == 1
        record = store.records(result.document.id)[0]
        assert record.text == '城市夜景亮起' and record.language == 'zh'
        assert [word.text for word in record.words] == ['城市', '夜景']
        assert record.alignment == 'unverified'
        assert calls[0]['compute_type'] == 'int8' and calls[0]['device'] == 'cpu'
        again = indexing.index_asr(store, media, _manager(tmp_path))
        assert again.reused is True and len(calls) == 1


@pytest.mark.media
def test_ocr_and_visual_use_frames_and_reject_incompatible_index(tmp_path, monkeypatch):
    store, _, media = _setup(tmp_path)
    calls = []

    class Boxes(list):
        pass

    class Output:
        txts = ('烧录字幕', 'EXIT')
        scores = (0.95, 0.6)
        boxes = np.array([[[1, 1], [40, 1], [40, 12], [1, 12]], [[2, 20], [30, 20], [30, 30], [2, 30]]], dtype=float)

    class Engine:
        def __call__(self, path):
            calls.append(path)
            return Output()

    monkeypatch.setattr(indexing, '_ocr_engine', lambda manager: Engine())

    def text_vectors(manager, texts, *, prefix, batch_size=16):
        calls.append(('text', prefix, len(texts)))
        return np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype='float32'), (len(texts), 1))

    def image_vectors(manager, paths, *, batch_size=8):
        calls.append(('image', len(paths)))
        return np.tile(np.array([[0.0, 1.0, 0.0, 0.0]], dtype='float32'), (len(paths), 1))

    monkeypatch.setattr('m2v.materials.embedding.embed_texts', text_vectors)
    monkeypatch.setattr('m2v.materials.embedding.embed_images', image_vectors)
    monkeypatch.setattr('m2v.materials.embedding.dimensions', lambda manager, name: 4)
    with store:
        frames = indexing.index_shots(store, media, max_frames=4)[1].document
        ocr = indexing.index_ocr(store, media, _manager(tmp_path), max_frames=4)
        assert ocr.records == len(store.records(frames.id))
        first = store.records(ocr.document.id)[0]
        assert first.boxes and first.frame and first.confidence > 0
        assert indexing.index_ocr(store, media, _manager(tmp_path), max_frames=4).reused is True

        source = Source(id='source-text', data=SourceData(provider='local', title='素材'))
        store.put(source)
        # 文本索引来自 OCR 记录；第二次复用不再调用编码器。
        text = indexing.index_text(store, media, _manager(tmp_path), sources=('ocr',))
        before = len([item for item in calls if isinstance(item, tuple) and item[0] == 'text'])
        assert text.records == ocr.records
        vectors = indexing.load_vectors(store, text.document)
        assert vectors.shape == (text.records, 4) and np.allclose(np.linalg.norm(vectors, axis=1), 1)
        assert indexing.index_text(store, media, _manager(tmp_path), sources=('ocr',)).reused is True
        assert len([item for item in calls if isinstance(item, tuple) and item[0] == 'text']) == before

        visual = indexing.index_visual(store, media, _manager(tmp_path), max_frames=4)
        assert visual.records == len(store.records(frames.id)) and visual.document.data.embeddingSpec.dimensions == 4
        assert indexing.index_visual(store, media, _manager(tmp_path), max_frames=4).reused is True
        # 模型权重摘要变化后，旧索引不再可查。
        monkeypatch.setattr(ModelManager, 'identity', lambda self, name: {
            'repoId': 'x', 'revision': 'b' * 40, 'license': 'x', 'preprocessing': 'x',
            'files': [{'path': 'model.safetensors', 'sha256': 'c' * 64}]})
        from m2v.materials import retrieval
        found = retrieval.find(store, query='城市夜景', manager=_manager(tmp_path), channels=('visual',),
                               top_k=5)
        assert found.candidates == [] and any('模型身份' in item['note'] for item in found.excluded)


def test_vector_shards_reject_pickle_and_wrong_shape(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        source = Source(id='source-1', data=SourceData(provider='local', title='x'))
        store.put(source)
        from m2v.materials.contracts import CaptionTrack, Media, MediaData, Probe
        media_artifact = store.publish_bytes(b'fake-image-bytes')
        media = Media(id='media-1', data=MediaData(sourceId=source.id, artifact=media_artifact,
            fetchIdentity='a' * 64, probe=Probe(kind='image', container='png', width=4, height=4)))
        store.put(media)
        records_artifact, checked = indexing._publish_records(store, [
            {'id': 'text-abc', 'channel': 'text', 'text': 'x', 'vectorRow': 0,
             'alignment': 'not-applicable', 'origin': 'test'}])
        spec = EmbeddingSpec(model='e5-small', revision='a' * 40, weightsSha256='b' * 64,
                             preprocessing='x', dimensions=4)
        bad = tmp_path / 'pickled.npy'
        np.save(bad, np.array([[1.0]], dtype=object), allow_pickle=True)
        artifact = store.publish_file(bad)
        data = IndexData(mediaId=media.id, mediaSha256=media_artifact.sha256, channel='text',
                         status='complete', config={}, configSha256='c' * 64,
                         toolchain={}, timelineMappingSha256=fingerprint(media.data.probe.timeline),
                         artifacts=[records_artifact, artifact], recordCount=1, embeddingSpec=spec)
        document = store.put(Index(id='index-bad', data=data))
        with pytest.raises(MaterialError):
            indexing.load_vectors(store, document)
