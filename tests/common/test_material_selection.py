"""预览、选择精裁、作品导入与凭据恢复；真实 FFmpeg 节点单独选择。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from conftest import create_typed_project
import pytest

from m2v.materials import fetch, import_work, preview, selection
from m2v.materials.contracts import (CandidateData, Requirement, RequirementData, Source, SourceData,
                                     RetrievalReason, TimeRange, Transform, fingerprint)
from m2v.materials.errors import MaterialError
from m2v.materials.store import MaterialStore


def _clip(path: Path, *, seconds=3.0, audio=True):
    arguments = ['-f', 'lavfi', '-i', f'testsrc2=size=128x72:rate=25:duration={seconds}']
    if audio:
        arguments += ['-f', 'lavfi', '-i', f'sine=frequency=440:sample_rate=48000:duration={seconds}']
    arguments += ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
    if audio:
        arguments += ['-c:a', 'aac']
    process = subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-nostdin', '-loglevel', 'error',
                              *arguments, str(path)], capture_output=True, timeout=60)
    assert process.returncode == 0, process.stderr.decode('utf-8', 'replace')
    return path


def _setup(tmp_path):
    store = MaterialStore(tmp_path / 'library')
    source = Source(id='source-local', data=SourceData(provider='local', title='本地素材',
                                                       author='作者', license='CC0'))
    store.put(source)
    media = fetch.fetch_local(store, source=source, path=_clip(tmp_path / 'clip.mp4')).media
    requirement = Requirement(id='req-1', data=RequirementData(text='城市夜景过程'))
    store.put(requirement)
    interval = TimeRange(startUs=400_000, endUs=1_800_000)
    candidate = CandidateData(requirementId=requirement.id, requirementDigest=fingerprint(requirement),
        sourceId=source.id, mediaId=media.id, mediaSha256=media.data.artifact.sha256, indexIds=[],
        localRange=interval, sourceRange=media.data.probe.timeline.source_range(interval),
        timelineMappingSha256=fingerprint(media.data.probe.timeline), fusionScore=0.5,
        retrievalReasons=[RetrievalReason(channel='captions', rank=1, score=0.5,
                                          excerpt='测试 <script>alert(1)</script> 摘录')],
        limitations=['字幕命中不等于画面已观察'])
    return store, media, candidate


@pytest.mark.media
def test_preview_builds_sheet_preview_and_safe_html(tmp_path):
    store, media, candidate = _setup(tmp_path)
    with store:
        result = preview.preview_candidates(store, [candidate], out=tmp_path / 'preview',
                                            columns=2, tile_width=240, preview_seconds=2)
        assert result.sheet.is_file() and result.html.is_file()
        page = result.html.read_text(encoding='utf-8')
        assert '<script>alert(1)</script>' not in page
        assert '&lt;script&gt;' in page
        assert 'Content-Security-Policy' in page and 'https://' not in page.split('</style>')[0]
        entry = result.candidates[0]
        assert Path(result.directory / entry['preview']).is_file()
        assert entry['previewRange']['durationUs'] <= 2_000_000
        index = json.loads((result.directory / 'index.json').read_text(encoding='utf-8'))
        assert index['selectionTemplate'][0]['mediaId'] == media.id
        assert index['selectionTemplate'][0]['sourceRange']


@pytest.mark.media
def test_select_measures_frame_accurate_window_and_refuses_rejected_output(tmp_path):
    store, media, candidate = _setup(tmp_path)
    with store:
        document = selection.persist_candidate(store, candidate)
        transform = Transform(fps={'num': 10, 'den': 1}, audio='preserve', crf=20)
        cut = selection.select(store, document, decision='chosen', rationale='画面与台词一致',
                               purpose='纪录片片段', operator='主代理', output_dir=tmp_path / 'out',
                               transform=transform)
        assert abs(cut.measured['startErrorUs']) <= cut.measured['frameUs']
        assert abs(cut.measured['durationErrorUs']) <= cut.measured['frameUs']
        assert abs(cut.measured['audioOffsetUs'] or 0) <= 50_000
        artifact = cut.selection.data.outputArtifact
        assert artifact and artifact.bytes > 0
        store.verify_artifact(artifact)
        again = selection.select(store, document, decision='chosen', rationale='画面与台词一致',
                                 purpose='纪录片片段', operator='主代理', output_dir=tmp_path / 'out',
                                 transform=transform)
        assert again.selection.data.outputArtifact.sha256 == artifact.sha256
        rejected = selection.select(store, document, decision='rejected', rationale='窗口不完整',
                                    purpose='排除', operator='主代理', output_dir=tmp_path / 'out')
        assert rejected.selection.data.outputArtifact is None
        with pytest.raises(MaterialError):
            selection.select(store, document, decision='chosen', rationale=' ', purpose='x',
                             operator='y', output_dir=tmp_path / 'out')


@pytest.mark.media
@pytest.mark.parametrize('source_origin_us', [0, 5_000_000])
def test_actual_start_crosses_long_gop_and_keeps_local_time(tmp_path, source_origin_us):
    # 默认 x264 GOP 长于请求位置；从前一个关键帧只读 60 包无法到达 2.86 秒。
    source = _clip(tmp_path / 'long-gop.mp4', seconds=6, audio=False)
    if source_origin_us:
        shifted = tmp_path / 'shifted.mp4'
        result = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-nostdin',
            '-itsoffset', str(source_origin_us / 1_000_000), '-i', str(source),
            '-map', '0:v:0', '-c', 'copy', str(shifted)], capture_output=True, timeout=60)
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        source = shifted
    actual = selection._actual_start(source, 2_860_000, video_start_us=source_origin_us)
    assert actual == 2_880_000
    with pytest.raises(MaterialError) as missing:
        selection._actual_start(source, 7_000_000, video_start_us=source_origin_us)
    assert missing.value.code == 'timeline-unverified'


@pytest.mark.media
def test_import_registers_media_receipt_and_is_idempotent(tmp_path):
    store, media, candidate = _setup(tmp_path)
    project = create_typed_project(tmp_path / 'project', 'text-motion').parent
    with store:
        document = selection.persist_candidate(store, candidate)
        cut = selection.select(store, document, decision='chosen', rationale='可用',
                               purpose='作品片段', operator='主代理', output_dir=tmp_path / 'out',
                               transform=Transform(fps={'num': 10, 'den': 1}))
        from m2v.core.errors import M2VError
        from m2v.core.style_binding import BINDING
        binding = project / BINDING
        original = binding.read_bytes()
        binding.unlink()
        with pytest.raises(M2VError, match='风格绑定'):
            import_work.import_selection(store, project_root=project, selection_id=cut.selection.id,
                                         asset_id='clip-one', role='color')
        assert not (project / 'assets/materials').exists()
        assert not store.connection.execute('SELECT 1 FROM operations').fetchone()
        binding.write_bytes(original)
        imported = import_work.import_selection(store, project_root=project, selection_id=cut.selection.id,
                                                asset_id='clip-one', role='color')
        assert imported.receipt.data.status == 'committed'
        entry = imported.entry
        assert entry['id'] == 'clip-one' and entry['sha256'] == cut.selection.data.outputArtifact.sha256
        assert (project / entry['path']).is_file()
        receipt_path = project / 'assets/materials/receipts' / f'{imported.receipt.data.operationId}.json'
        assert receipt_path.is_file()
        assert imported.receipt.data.targetAssetPath == entry['path']
        assert not (project / 'assets/materials/staging' / imported.receipt.data.operationId).exists()
        verified = import_work.verify_project_media(project)
        assert verified['usable'] and verified['verified'] == 1
        resumed = import_work.import_selection(store, project_root=project, selection_id=cut.selection.id,
                                               asset_id='clip-one')
        assert resumed.resumed is True and resumed.receipt.id == imported.receipt.id
        with pytest.raises(MaterialError) as conflict:
            other = CandidateData.model_validate({**candidate.model_dump(mode='json'),
                'localRange': {'startUs': 0, 'endUs': 900_000},
                'sourceRange': {'startUs': 0, 'endUs': 900_000}})
            second = selection.persist_candidate(store, other, candidate_id='candidate-other')
            changed = selection.select(store, second, decision='chosen', rationale='另一个窗口',
                                       purpose='替换', operator='主代理', output_dir=tmp_path / 'out2',
                                       transform=Transform(fps={'num': 10, 'den': 1}))
            import_work.import_selection(store, project_root=project, selection_id=changed.selection.id,
                                         asset_id='clip-one')
        assert conflict.value.code == 'conflict'


@pytest.mark.media
def test_import_receipt_failure_is_recoverable_without_claiming_success(tmp_path, monkeypatch):
    store, media, candidate = _setup(tmp_path)
    project = create_typed_project(tmp_path / 'project', 'text-motion').parent
    original = import_work._write_receipt

    def flaky(root, receipt):
        raise OSError('disk full')

    with store:
        document = selection.persist_candidate(store, candidate)
        cut = selection.select(store, document, decision='chosen', rationale='可用',
                               purpose='作品片段', operator='主代理', output_dir=tmp_path / 'out',
                               transform=Transform(fps={'num': 10, 'den': 1}))
        monkeypatch.setattr(import_work, '_write_receipt', flaky)
        with pytest.raises(OSError):
            import_work.import_selection(store, project_root=project, selection_id=cut.selection.id,
                                         asset_id='clip-one')
        rows = store.connection.execute('SELECT status FROM operations').fetchall()
        assert [row[0] for row in rows] == ['pending']
        monkeypatch.setattr(import_work, '_write_receipt', original)
        recovered = import_work.import_selection(store, project_root=project, selection_id=cut.selection.id,
                                                 asset_id='clip-one')
        assert recovered.receipt.data.status == 'committed'
        assert recovered.receipt.data.registeredEntryDigest
        assert import_work.verify_project_media(project)['usable']
        assert store.connection.execute('SELECT status FROM operations').fetchone()[0] == 'committed'

