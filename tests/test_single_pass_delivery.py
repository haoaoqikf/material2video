"""验证调用次数，而非仅断言生成成功。"""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from m2v.core import delivery
from m2v.core.errors import M2VError
from m2v.core.preview import window


def test_default_and_explicit_preview_ranges():
    assert window(3600, 60) == (0, 600)
    assert window(240, 60) == (0, 239)
    assert window(3600, 60, start_seconds=20, end_seconds=22) == (1200, 1320)
    for kwargs in ({"end_seconds": 60}, {"limit_frames": 3600}, {"end_seconds": float("nan")},
                   {"start_seconds": -1}, {"limit_frames": 0}, {"end_seconds": 70}):
        with pytest.raises(M2VError):
            window(3600, 60, **kwargs)


def test_one_generation_retry_validation_delivery_and_damage(tmp_path, monkeypatch):
    target = tmp_path / "video.mp4"
    target.write_bytes(b"old")
    state = {"preparedFingerprint": "v1"}
    counts = {"generate": 0, "verify": 0}
    reject = [True]
    def generate(path):
        counts["generate"] += 1
        path.write_bytes(b"new")
        path.with_suffix(".provenance.json").write_text("{}")
    def verify(path):
        counts["verify"] += 1
        if reject[0]:
            raise M2VError("bad check")
    def run():
        return delivery.export_once(target, dict(state), generate, verify, lambda: dict(state))
    with pytest.raises(M2VError):
        run()
    assert target.read_bytes() == b"old"
    assert counts["generate"] == 1
    assert delivery.read_record(tmp_path)["status"] == "validation-failed"
    reject[0] = False
    original = delivery.security.deliver
    def fail_copy(source, dest):
        if dest == target:
            raise OSError("copy failed")
        return original(source, dest)
    monkeypatch.setattr(delivery.security, "deliver", fail_copy)
    with pytest.raises(OSError):
        run()
    assert target.read_bytes() == b"old"
    assert counts["generate"] == 1
    monkeypatch.setattr(delivery.security, "deliver", original)
    run(); run()
    assert target.read_bytes() == b"new" and target.with_suffix(".provenance.json").is_file()
    assert counts["generate"] == 1
    Path(delivery.read_record(tmp_path)["path"]).write_bytes(b"damage")
    run()
    assert counts["generate"] == 1, "有效交付仍在，应恢复候选而非重渲染"
    Path(delivery.read_record(tmp_path)["path"]).write_bytes(b"damage")
    target.write_bytes(b"damage")
    run()
    assert counts["generate"] == 2
    state["preparedFingerprint"] = "v2"
    run()
    assert counts["generate"] == 3


def test_concurrent_export_rejected_and_input_change_discards(tmp_path):
    target = tmp_path / "video.mp4"
    binding = {"preparedFingerprint": "v1"}
    with delivery._lock(tmp_path):
        with pytest.raises(M2VError, match="拒绝重复"):
            delivery.export_once(target, binding, lambda _: None, lambda _: None, lambda: binding)
    def generate(path):
        path.write_bytes(b"changed")
    with pytest.raises(M2VError, match="输入变化"):
        delivery.export_once(target, binding, generate, lambda _: None, lambda: {"preparedFingerprint": "v2"})
    assert not target.exists()
    assert not list((tmp_path / "candidates").glob("*.mp4"))


@pytest.mark.parametrize("kind", ["general", "financial", "housing"])
def test_renderer_repeated_full_export_calls_generate_once(tmp_path, monkeypatch, kind):
    from m2v.core import project as project_module
    from m2v.engine import output_validation, render_pipeline
    from m2v.types.general import explainer_render
    from m2v.types.financial import financial, financial_render
    from m2v.types.housing import housing_render
    module = {"general": explainer_render, "financial": financial_render, "housing": housing_render}[kind]
    project = {"id": "test", "type": kind}
    prepared = {"preparedFingerprint": "current", "durationInFrames": 1200, "width": 1920, "height": 1080}
    monkeypatch.setattr(project_module, "load_project", lambda _: (tmp_path, project))
    monkeypatch.setattr(project_module, "load_current_prepared", lambda *_: prepared)
    monkeypatch.setattr(delivery, "binding", lambda root, prep, params: {"preparedFingerprint": prep["preparedFingerprint"], "parameters": params})
    monkeypatch.setattr(output_validation, "verify_output", lambda *a, **k: None)
    calls = []
    def generate(root, data, *args, **kwargs):
        calls.append(kwargs)
        kwargs["output"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["output"].write_bytes(b"full")
        return kwargs["output"]
    if kind == "general":
        monkeypatch.setattr(module, "_generate", generate)
        monkeypatch.setattr(module, "current", lambda *_: prepared)
        monkeypatch.setattr(module, "layout_check", lambda *_: {})
        material = project
    else:
        # 无声类型共用 `render_pipeline`：替身必须打在管线上，而不是类型模块上。
        monkeypatch.setattr(render_pipeline, "generate", generate)
        monkeypatch.setattr(render_pipeline, "assert_no_audio", lambda _: None)
        if kind == "financial":
            monkeypatch.setattr(financial, "render_inputs_digest", lambda _: "inputs")
            material = {"plan": {"durationSeconds": 20}}
        else:
            monkeypatch.setattr(module, "_inputs_digest", lambda _: "inputs")
            material = {"durationSeconds": 20}
    module.render(tmp_path, material)
    module.render(tmp_path, material)
    assert len(calls) == 1
    assert calls[0]["defer_validation"] is True


def test_general_materializes_only_intersecting_scenes_and_offsets(tmp_path, monkeypatch):
    from m2v.types.general import code_scenes, media_assets
    monkeypatch.setattr(media_assets, "resolve", lambda _: {"media": {}, "digest": "m"})
    calls = []
    def record(root, scene, inputs, **kwargs):
        calls.append((scene["id"], kwargs["capture_range"]))
        return "outputs/code-cache/test.mp4"
    monkeypatch.setattr(code_scenes.capture, "record", record)
    scenes = [{"id": name, "startFrame": start, "endFrame": end} for name, start, end in
              [("a", 0, 100), ("b", 80, 200), ("c", 200, 300)]]
    prepared = {"width": 1920, "height": 1080, "props": {"compiledScenes": scenes}}
    result = code_scenes.materialize(tmp_path, prepared, 90, 120)
    assert calls == [("a", (90, 100)), ("b", (10, 40))]
    assert [s["mediaStartFrame"] for s in result["props"]["compiledScenes"]] == [90, 10]
    assert "mediaPath" not in prepared["props"]["compiledScenes"][0]


def test_sidecar_failure_restores_previous_delivery(tmp_path, monkeypatch):
    target = tmp_path / "video.mp4"
    target.write_bytes(b"old")
    sidecar = target.with_suffix(".provenance.json")
    sidecar.write_text("old provenance")
    state = {"preparedFingerprint": "v1"}
    count = []
    def generate(path):
        count.append(path)
        path.write_bytes(b"new")
        path.with_suffix(".provenance.json").write_text("new provenance")
        path.with_suffix(".performance.json").write_text("new perf")
    original = delivery.security.deliver
    def reject(source, destination):
        if destination == target.with_suffix(".performance.json"):
            raise OSError("sidecar failure")
        return original(source, destination)
    monkeypatch.setattr(delivery.security, "deliver", reject)
    with pytest.raises(OSError):
        delivery.export_once(target, state, generate, lambda _: None, lambda: state)
    assert target.read_bytes() == b"old"
    assert sidecar.read_text() == "old provenance"
    monkeypatch.setattr(delivery.security, "deliver", original)
    delivery.export_once(target, state, generate, lambda _: None, lambda: state)
    assert len(count) == 1 and target.read_bytes() == b"new"


def test_post_generation_report_error_keeps_candidate_for_retry(tmp_path):
    target = tmp_path / "video.mp4"
    state = {"preparedFingerprint": "v1"}
    calls = []
    def generate(path):
        calls.append(path)
        path.write_bytes(b"complete candidate")
        raise OSError("report write failed after video completed")
    with pytest.raises(OSError):
        delivery.export_once(target, state, generate, lambda _: None, lambda: state)
    delivery.export_once(target, state, generate, lambda _: None, lambda: state)
    assert len(calls) == 1 and target.read_bytes() == b"complete candidate"


def test_cleanup_preserves_current_candidate_and_removes_old_video(tmp_path):
    from m2v.core.output_cleanup import cleanup_after_render
    outputs = tmp_path / "outputs"
    cache = outputs / "candidates"
    cache.mkdir(parents=True)
    final = outputs / "video.mp4"
    final.write_bytes(b"current")
    candidate = cache / "current.mp4"
    candidate.write_bytes(b"current")
    candidate.with_suffix(".provenance.json").write_text("{}")
    old = cache / "old.mp4"
    old.write_bytes(b"old")
    (outputs / "delivery.json").write_text(json.dumps({"path": str(candidate)}), encoding="utf-8")
    assert cleanup_after_render(outputs, final) == []
    assert candidate.is_file() and candidate.with_suffix(".provenance.json").is_file()
    assert not old.exists()
