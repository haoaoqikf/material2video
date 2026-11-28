"""候选生成与技术验收不依赖可选人工评审或旧预演。"""
import json
import pytest
from m2v.cli import main
from m2v.commands import _status
from m2v.core import delivery
from m2v.types.scene_film import adapter


@pytest.mark.parametrize("kind", ["text-motion", "data-evolution", "spatial-3d"])
@pytest.mark.parametrize("review_state", [None, "pending", "fail", "stale"])
def test_types_export_without_preview_or_manual_review(tmp_path, monkeypatch, kind, review_state):
    root = tmp_path / kind
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    manifest = {"id": "demo", "type": kind}
    if review_state:
        (outputs / "review.json").write_text(json.dumps({"status": review_state}), encoding="utf-8")
    final = outputs / "final.mp4"
    def render(*_, **__):
        final.write_bytes(b"final")
        return final
    monkeypatch.setattr(adapter, "render", render)
    monkeypatch.setattr("m2v.commands.load_project", lambda *_: (root, manifest))
    assert main(["render", "--project", str(root)]) == 0
    assert final.read_bytes() == b"final"


def test_status_reports_candidate_failure_and_review_independently(tmp_path, monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'templates/standalone/runtime/python'))
    from standalone.test_management_bindings import prepared_work
    from m2v.core.fingerprints import fingerprint
    manifest, prepared = prepared_work(tmp_path)
    monkeypatch.setattr("m2v.commands._prepared", lambda *_: prepared)
    assert _status(tmp_path, manifest)["stage"] == "prepared"
    video = tmp_path / "outputs/candidates/test.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"candidate")
    binding = delivery.binding(tmp_path, prepared, {'crf': 18})
    record = {**binding, 'key': fingerprint(binding), "path": 'outputs/candidates/test.mp4',
              "sha256": delivery.digest(video), "status": "validation-failed", "error": "probe failed"}
    (tmp_path / "outputs/delivery.json").write_text(json.dumps(record), encoding="utf-8")
    result = _status(tmp_path, manifest)
    assert result["stage"] == "validation-failed"
    assert result["candidate"]["error"] == "probe failed"
    assert result["production"]["complete"] is False
    video.write_bytes(b"damaged")
    assert _status(tmp_path, manifest)["candidate"]["status"] == "stale"


def test_status_does_not_create_the_local_environment(tmp_path):
    root = tmp_path / 'work'
    (root / 'outputs').mkdir(parents=True)
    manifest = {'schemaVersion': 3, 'id': 'status-readonly', 'type': 'text-motion',
                'materials': {'storyboard': 'storyboard.json'}, 'output': {'fps': 30}}
    (root / 'project.json').write_text(json.dumps(manifest), encoding='utf-8')
    (root / 'storyboard.json').write_text('{"version": 9, "schemaVersion": 9, "scenes": []}',
                                          encoding='utf-8')
    result = _status(root, manifest)
    assert result['prepare']['status'] == 'stale-or-missing'
    assert not (root / '.venv').exists()


def test_lookdev_rejects_sample_from_another_preparation(tmp_path, monkeypatch):
    from m2v.engine import lookdev
    from m2v.standalone import executor

    root = tmp_path / 'work'
    root.mkdir()
    sample = root / 'outputs/lookdev/sample.mp4'
    sample.parent.mkdir(parents=True)
    sample.write_bytes(b'sample')
    still = sample.parent / 'still.png'
    still.write_bytes(b'png')
    prepared = {'preparedFingerprint': 'CURRENT', 'fps': 30, 'width': 1920, 'height': 1080,
                'durationInFrames': 90, 'props': {'compiledScenes': []}}
    monkeypatch.setattr(lookdev, '_render_stills', lambda *args, **kwargs: [still])
    monkeypatch.setattr(lookdev, 'contact_sheet', lambda *args, **kwargs: still)
    monkeypatch.setattr(lookdev, 'sample_audio', lambda *args, **kwargs: (False, None))
    monkeypatch.setattr(lookdev, 'still_frames', lambda *args, **kwargs: [0])
    monkeypatch.setattr(lookdev, 'sample_window', lambda *args, **kwargs: (0, 10))
    monkeypatch.setattr(executor, 'execute', lambda *args, **kwargs: {
        'path': 'outputs/lookdev/sample.mp4', 'preparedFingerprint': 'OTHER'})
    monkeypatch.setattr(executor, 'local_artifact', lambda _root, _path: sample)
    monkeypatch.setattr(executor, 'read_json', lambda _path: {'preparedFingerprint': 'OTHER'})
    with pytest.raises(Exception, match='准备身份'):
        lookdev.run(root, {'materials': {'storyboard': 'storyboard.json'}}, prepared,
                    stills=1, sample_seconds=1)
