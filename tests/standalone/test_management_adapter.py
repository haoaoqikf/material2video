"""媒体成功须绑定当前准备、候选、窗口与实际待检视频。"""
import json
import shutil

import pytest

from m2v import cli, commands
from m2v.core import delivery
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.standalone import executor
from m2v.types.scene_film import adapter
from standalone.test_management_bindings import prepared_work


@pytest.fixture
def media(tmp_path, monkeypatch):
    project, prepared = prepared_work(tmp_path)
    video = tmp_path / 'outputs/video.mp4'
    video.write_bytes(b'already-encoded')
    result = {'status': 'candidate', 'path': 'outputs/video.mp4', 'sha256': delivery.digest(video),
              'preparedFingerprint': prepared['preparedFingerprint']}
    provenance = {'preparedFingerprint': prepared['preparedFingerprint'], 'startFrame': 0,
                  'durationInFrames': 90, 'fps': 30, 'width': 1920, 'height': 1080,
                  'delivery': {'sha256': result['sha256']}}
    video.with_suffix('.provenance.json').write_text(json.dumps(provenance), encoding='utf-8')
    target = tmp_path / 'outputs/candidates/current.mp4'
    target.parent.mkdir()
    shutil.copyfile(video, target)
    binding = delivery.binding(tmp_path, prepared, {'crf': 18})
    record = {**binding, 'key': fingerprint(binding), 'sha256': result['sha256'],
              'path': 'outputs/candidates/current.mp4', 'destination': 'outputs/video.mp4', 'status': 'delivered'}
    (tmp_path / 'outputs/delivery.json').write_text(json.dumps(record), encoding='utf-8')
    monkeypatch.setattr(executor, 'execute', lambda *a, **kw: result)
    monkeypatch.setattr(adapter, 'verify_output', lambda *a, **kw: None)
    return tmp_path, project, prepared, result, provenance


def test_render_accepts_current_bound_and_delivered_candidate(media):
    root, project, _, _, _ = media
    assert adapter.render(root, project) == root / 'outputs/video.mp4'


@pytest.mark.parametrize('damage', ['receipt-missing', 'receipt-stale', 'result-stale', 'provenance-stale'])
def test_same_shape_old_video_cannot_be_reported_as_current_success(media, damage):
    root, project, _, result, provenance = media
    if damage == 'receipt-missing':
        (root / 'outputs/delivery.json').unlink()
    elif damage == 'receipt-stale':
        record = delivery.read_record(root / 'outputs')
        record['preparedFingerprint'] = 'old'
        (root / 'outputs/delivery.json').write_text(json.dumps(record), encoding='utf-8')
    elif damage == 'result-stale':
        result['preparedFingerprint'] = 'old'
    else:
        provenance['preparedFingerprint'] = 'old'
        (root / 'outputs/video.provenance.json').write_text(json.dumps(provenance), encoding='utf-8')
    with pytest.raises(M2VError):
        adapter.render(root, project)


def test_preview_requires_actual_requested_window(media):
    root, project, _, _, provenance = media
    with pytest.raises(M2VError, match='窗口'):
        adapter.preview(root, project, start_seconds=1, limit_frames=3)
    provenance.update(startFrame=30, durationInFrames=3)
    (root / 'outputs/video.provenance.json').write_text(json.dumps(provenance), encoding='utf-8')
    assert adapter.preview(root, project, start_seconds=1, limit_frames=3) == root / 'outputs/video.mp4'


def test_manifest_change_during_technical_verification_invalidates_success(media, monkeypatch):
    root, project, _, _, _ = media
    def change_during_check(*args, **kwargs):
        updated = json.loads((root / 'project.json').read_text(encoding='utf-8'))
        updated['output']['subtitle'] = {'fontSize': 40}
        (root / 'project.json').write_text(json.dumps(updated), encoding='utf-8')
    monkeypatch.setattr(adapter, 'verify_output', change_during_check)
    with pytest.raises(M2VError, match='磁盘作品描述'):
        adapter.render(root, project)


@pytest.mark.parametrize('fails', [False, True])
def test_management_render_preserves_event_order_and_skips_cleanup_on_failure(media, monkeypatch, fails):
    root, _, _, _, _ = media
    events, cleanups = [], []
    monkeypatch.setattr(commands, '_production_render_event', lambda root, manifest, kind: events.append(kind))
    import m2v.production.cleanup as cleanup
    monkeypatch.setattr(cleanup, 'cleanup_render_outputs', lambda *a: cleanups.append(a) or [])
    if fails:
        def failed(*args, **kwargs):
            raise M2VError('local render failed')
        monkeypatch.setattr(executor, 'execute', failed)
    assert cli.main(['render', '--project', str(root)]) == (1 if fails else 0)
    assert events == ['render-request', 'render-failed' if fails else 'render-returned']
    assert len(cleanups) == (0 if fails else 1)


@pytest.mark.parametrize('damage', [None, 'sha', 'different-video', 'status', 'prepared'])
def test_qa_rechecks_actual_target_media_and_current_prepared(media, monkeypatch, damage):
    root, _, prepared, _, _ = media
    video = root / 'outputs/video.mp4'
    report = {'status': 'pass', 'preparedFingerprint': prepared['preparedFingerprint'],
              'video': 'outputs/video.mp4', 'videoSha256': delivery.digest(video), 'scope': 'technical-only'}
    if damage == 'sha':
        report['videoSha256'] = 'stale'
    elif damage == 'different-video':
        other = root / 'outputs/other.mp4'
        other.write_bytes(video.read_bytes())
        report['video'] = 'outputs/other.mp4'
    elif damage == 'status':
        report['status'] = 'fail'
    elif damage == 'prepared':
        report['preparedFingerprint'] = 'stale'
    (root / 'outputs/qa.json').write_text(json.dumps(report), encoding='utf-8')
    monkeypatch.setattr(executor, 'execute', lambda *a, **kw: {'status': 'pass', 'path': 'outputs/qa.json'})
    args = cli._parser().parse_args(['qa', '--project', str(root), '--video', str(video)])
    if damage is None:
        assert commands.dispatch(args) == 0
    else:
        with pytest.raises(M2VError, match='QA报告'):
            commands.dispatch(args)
