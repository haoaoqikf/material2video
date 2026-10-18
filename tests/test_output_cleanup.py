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


def test_financial_cleanup_can_preserve_bound_preview(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    current = outputs / "final.mp4"
    current.write_bytes(b"final")
    preview = outputs / "previews" / "preview.mp4"
    preview.parent.mkdir()
    preview.write_bytes(b"preview")
    record = preview.parent / "preview-record.json"
    record.write_text("{}", encoding="utf-8")

    failures = output_cleanup.cleanup_after_render(outputs, current, preserve_previews=True)

    assert failures == []
    assert preview.is_file()
    assert record.is_file()


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


def test_general_cleanup_preserves_only_explicit_local_visual_evidence(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    current = outputs / "video.mp4"
    current.write_bytes(b"final")
    # 既覆盖整目录清理，也覆盖逐文件清理与带空格/编码路径。
    for name in ("qa/keep.png", "qa/old.png", "debug-review/before.mp4",
                 "lookdev/after frame.jpg", "lookdev/old.mp4", "old.mp4"):
        path = outputs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"evidence")
    notes = outputs / "visual-notes.md"
    notes.write_text("[帧](qa/keep.png) [之前](debug-review/before.mp4) "
                     "[之后](<lookdev/after%20frame.jpg>) [外部](../outside.png) "
                     "[目录](lookdev/) [网页](https://example.com/photo.png)", encoding="utf-8")
    external = tmp_path / "outside.png"
    external.write_bytes(b"external")

    assert output_cleanup.cleanup_after_render(outputs, current, preserve_visual_evidence=True) == []

    assert notes.is_file() and current.is_file() and external.is_file()
    assert (outputs / "qa/keep.png").is_file()
    assert (outputs / "debug-review/before.mp4").is_file()
    assert (outputs / "lookdev/after frame.jpg").is_file()
    assert not (outputs / "qa/old.png").exists()
    assert not (outputs / "lookdev/old.mp4").exists()
    assert not (outputs / "old.mp4").exists()


def test_unreadable_visual_record_skips_cleanup_without_losing_current(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    current = outputs / "video.mp4"
    current.write_bytes(b"final")
    old = outputs / "old.mp4"
    old.write_bytes(b"old")
    (outputs / "visual-notes.md").write_bytes(b"\xff")

    failures = output_cleanup.cleanup_after_render(outputs, current, preserve_visual_evidence=True)

    assert len(failures) == 1 and "无法读取视觉证据记录" in failures[0]
    assert old.is_file() and current.is_file()
