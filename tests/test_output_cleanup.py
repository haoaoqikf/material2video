from __future__ import annotations

from pathlib import Path

from m2v.core import output_cleanup


def test_cleanup_removes_old_outputs_but_preserves_current_and_reusable_inputs(tmp_path: Path) -> None:
    outputs = tmp_path / "project" / "outputs"
    outputs.mkdir(parents=True)
    current = outputs / "final.mp4"
    current.write_bytes(b"new")
    current.with_suffix(".provenance.json").write_text("{}", encoding="utf-8")
    current.with_suffix(".performance.json").write_text("{}", encoding="utf-8")
    current.with_suffix(".srt").write_text("subtitle", encoding="utf-8")
    old = outputs / "old.mp4"
    old.write_bytes(b"old")
    old.with_suffix(".provenance.json").write_text("{}", encoding="utf-8")
    old.with_suffix(".performance.json").write_text("{}", encoding="utf-8")
    old.with_suffix(".srt").write_text("old subtitle", encoding="utf-8")
    preview = outputs / "previews" / "review" / "nested" / "full.mp4"
    preview.parent.mkdir(parents=True)
    preview.write_bytes(b"preview")
    (preview.parent / "frame.png").write_bytes(b"frame")
    (outputs / "preview-record.json").write_text("{}", encoding="utf-8")
    (outputs / "qa").mkdir()
    (outputs / "qa" / "check.png").write_bytes(b"check")
    (outputs / "debug-financial-render").mkdir()
    (outputs / "debug-financial-render" / "bundle.js").write_text("cache", encoding="utf-8")
    media = outputs / "media"
    media.mkdir()
    (media / "audio.wav").write_bytes(b"prepared audio")
    (media / "embedded.mp4").write_bytes(b"prepared clip")
    for name in ("prepared.json", "review.json", "legibility-review.json"):
        (outputs / name).write_text("{}", encoding="utf-8")
    (outputs / "notes.txt").write_text("unclassified", encoding="utf-8")

    failures = output_cleanup.cleanup_after_render(outputs, current)

    assert failures == []
    assert current.read_bytes() == b"new"
    assert all(current.with_suffix(suffix).is_file() for suffix in (".srt", ".provenance.json", ".performance.json"))
    assert not old.exists()
    assert not old.with_suffix(".provenance.json").exists()
    assert not preview.parent.exists()
    assert not (outputs / "qa").exists()
    assert not (outputs / "debug-financial-render").exists()
    assert not (outputs / "preview-record.json").exists()
    assert (media / "audio.wav").is_file()
    assert (media / "embedded.mp4").is_file()
    assert all((outputs / name).is_file() for name in ("prepared.json", "review.json", "legibility-review.json", "notes.txt"))


def test_cleanup_refuses_to_run_when_current_video_is_outside_outputs(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    old = outputs / "old.mp4"
    old.write_bytes(b"old")
    external = tmp_path / "external.mp4"
    external.write_bytes(b"new")

    failures = output_cleanup.cleanup_after_render(outputs, external)

    assert failures and "不是作品 outputs 的直接文件" in failures[0]
    assert old.is_file()
    assert external.read_bytes() == b"new"


def test_cleanup_reports_locked_old_file_and_keeps_new_video(tmp_path: Path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    current = outputs / "new.mp4"
    current.write_bytes(b"new")
    old = outputs / "old.mp4"
    old.write_bytes(b"old")
    unlink = output_cleanup._unlink

    def fail_old(path: Path, failures: list[str]) -> None:
        if path == old:
            failures.append(f"{old}: locked")
        else:
            unlink(path, failures)

    monkeypatch.setattr(output_cleanup, "_unlink", fail_old)

    failures = output_cleanup.cleanup_after_render(outputs, current)

    assert failures == [f"{old}: locked"]
    assert current.read_bytes() == b"new"
    assert old.read_bytes() == b"old"
