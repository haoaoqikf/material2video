"""任务 4.3：所有执行入口只接受 v4，旧分镜与旧媒体被明确拒绝且不写新产物。

入口切换的验收不是「v4 能跑」（那由各能力的用例覆盖），而是「旧契约跑不起来」：
- 每个入口对 v1–v3 分镜给出**单条**可执行诊断并停止；
- 停止发生在写任何作品产物之前（不请求语音、不写媒体、不写 MP4、不写评审报告）；
- 输出归属与内容根隔离规则不变。
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import m2v.types.article.cli as cli
from conftest import approve_input_review, make_project, v4_storyboard

ROOT = Path(__file__).resolve().parents[1]
LEGACY_MESSAGE = "不支持 v4 之前分镜；请按分镜 v4 契约重新编排"


def _legacy_script(version: object) -> dict:
    """一份结构完整但版本不是 4 的分镜：入口必须拒绝而不是尝试兼容。"""
    script = {
        "version": version, "schemaVersion": version, "directingVersion": 1,
        "fps": 30, "width": 1080, "height": 1920, "title": "旧分镜",
        "visual": {"theme": "dark", "preset": "keynote"},
        "visualDirection": {"motif": "路径", "compositionBias": "mixed", "density": "balanced",
                            "rhythm": "steady", "avoid": []},
        "directingBrief": {"thesis": "旧论点", "audienceShift": "旧转变", "emotionalArc": ["疑问", "理解"],
                           "visualMotif": "路径", "stylePack": "editorial", "avoid": []},
        "scenes": [{"id": "opening", "type": "title", "durationInFrames": 1200,
                    "data": {"text": "开场"}, "renderer": {"kind": "tree"},
                    "visualIntent": {"mode": "typography"},
                    "narrationSegments": [{"id": "n1", "text": "旧口播。", "beatId": "b1"}],
                    "beats": [{"id": "b1", "action": "establish", "targets": ["copy"], "meaning": "旧"}],
                    "sceneTree": {"id": "root", "type": "stack",
                                  "children": [{"id": "copy", "type": "text", "contentRef": "data.text"}]}}],
    }
    if version is None:
        script.pop("version")
        script.pop("schemaVersion")
    return script


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _tree(root: Path) -> set[str]:
    return {item.relative_to(root).as_posix() for item in root.rglob("*")} if root.exists() else set()


# ---------------------------------------------------------------------------
# 1. 每个入口都拒绝旧分镜
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", [1, 2, 3, None], ids=["v1", "v2", "v3", "missing"])
def test_validate_rejects_legacy_storyboards_with_a_single_diagnostic(tmp_path, version, capsys):
    path = _write(tmp_path / "storyboard.json", _legacy_script(version))
    assert cli.main_validate([str(path)]) == 2
    errors = [line for line in capsys.readouterr().err.splitlines() if "[error]" in line]
    assert errors == [f"[error] version: {LEGACY_MESSAGE}"]


def test_prepare_rejects_legacy_storyboard_before_requesting_speech(tmp_path, monkeypatch, caplog):
    import m2v.types.article.prepare as prepare_module

    article = make_project(tmp_path, "videos", "demo", None)
    path = _write(article / "storyboard.json", _legacy_script(3))
    approve_input_review(path)
    spoken: list[str] = []
    monkeypatch.setattr(prepare_module, "synthesize", lambda *args, **kwargs: spoken.append("called"))
    cli._force_utf8_output = lambda: None
    assert cli.main_prepare(["--storyboard", str(path), "--content-root", str(tmp_path)]) == 1
    assert spoken == [], "旧分镜不得触发语音合成"
    assert LEGACY_MESSAGE in caplog.text
    assert not (article / "outputs").exists(), "被拒绝的入口不得写出媒体目录"


def test_preview_rejects_legacy_storyboard_without_building_the_page(tmp_path, monkeypatch):
    article = make_project(tmp_path, "videos", "demo", _legacy_script(3))
    monkeypatch.setattr(cli, "_build_contract_for",
                        lambda *_args, **_kwargs: pytest.fail("旧分镜不得触发契约页构建"))
    cli._force_utf8_output = lambda: None
    assert cli.main_preview(["--storyboard", str(article / "storyboard.json"),
                             "--content-root", str(tmp_path), "--no-browser"]) == 2


def test_review_rejects_legacy_storyboard_before_any_review_artifact(tmp_path, monkeypatch, caplog):
    article = make_project(tmp_path, "videos", "demo", _legacy_script(3))
    monkeypatch.setattr(cli, "_build_contract_for",
                        lambda *_args, **_kwargs: pytest.fail("旧分镜不得触发契约页构建"))
    cli._force_utf8_output = lambda: None
    out_dir = article / "outputs" / "inspect"
    assert cli.main_review(["--storyboard", str(article / "storyboard.json"),
                            "--content-root", str(tmp_path), "--out-dir", str(out_dir)]) == 2
    assert LEGACY_MESSAGE in caplog.text
    assert not out_dir.exists(), "被拒绝的评审不得写出报告、联系表或模板"


def test_render_rejects_legacy_storyboard_without_writing_output(tmp_path, monkeypatch):
    article = make_project(tmp_path, "videos", "demo", _legacy_script(3))
    output = tmp_path / "out.mp4"
    monkeypatch.setattr(cli, "render_with_remotion",
                        lambda **_kwargs: pytest.fail("旧分镜不得进入渲染"))
    cli._force_utf8_output = lambda: None
    assert cli.main_render(["--storyboard", str(article / "storyboard.json"),
                            "--content-root", str(tmp_path), "--out", str(output)]) == 2
    assert not output.exists()


def test_production_entry_rejects_legacy_storyboard(tmp_path):
    article = make_project(tmp_path, "videos", "demo", _legacy_script(3))
    completed = subprocess.run(
        [sys.executable, "-m", "m2v.cli", "article", "status", "--storyboard", str(article / "storyboard.json"),
         "--content-root", str(tmp_path)],
        cwd=ROOT, text=True, capture_output=True, check=False, encoding="utf-8", errors="replace",
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 2
    assert LEGACY_MESSAGE in completed.stderr


# ---------------------------------------------------------------------------
# 2. 旧媒体清单同样被拒绝，且不改写任何产物
# ---------------------------------------------------------------------------


def test_legacy_media_manifest_is_rejected_without_touching_the_media_directory(tmp_path, caplog):
    article = make_project(tmp_path, "videos", "demo", v4_storyboard())
    media_dir = article / "outputs" / "media"
    media_dir.mkdir(parents=True)
    manifest = media_dir / "media.json"
    manifest.write_text(json.dumps({
        "version": 3,
        "source": {**_legacy_script(3)},
        "sourceFingerprint": "stale",
        "scenes": [{"id": "opening", "durationInFrames": 1200, "resolvedBeats": []}],
        "cues": [],
        "audio": "old.wav",
        "narration": "old.narration.wav",
        "subtitles": "old.srt",
    }, ensure_ascii=False), encoding="utf-8")
    before = _tree(media_dir)
    cli._force_utf8_output = lambda: None
    assert cli.main_render(["--storyboard", str(article / "storyboard.json"),
                            "--media", str(manifest), "--content-root", str(tmp_path),
                            "--out", str(tmp_path / "out.mp4")]) != 0
    assert _tree(media_dir) == before
    assert not (tmp_path / "out.mp4").exists()
    assert "媒体清单版本过旧" in caplog.text


def test_legacy_media_is_rejected_by_the_validate_entry(tmp_path, capsys):
    article = make_project(tmp_path, "videos", "demo", v4_storyboard())
    media_dir = article / "outputs" / "media"
    media_dir.mkdir(parents=True)
    manifest = media_dir / "media.json"
    manifest.write_text(json.dumps({"version": 2, "source": _legacy_script(2)}), encoding="utf-8")
    assert cli.main_validate([str(article / "storyboard.json"), "--media", str(manifest),
                              "--content-root", str(tmp_path)]) == 2
    assert "媒体清单版本过旧" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 3. 输出归属与内容根隔离不变
# ---------------------------------------------------------------------------


def test_rejected_prepare_does_not_create_outputs_outside_the_repository(tmp_path, monkeypatch):
    """内容根在仓库外时同样成立：被拒绝的入口不创建任何作品目录。"""
    workspace = tmp_path / "content-root"
    article = workspace / "videos" / "demo"
    article.mkdir(parents=True)
    path = _write(article / "storyboard.json", _legacy_script(3))
    approve_input_review(path, workspace)
    cli._force_utf8_output = lambda: None
    assert cli.main_prepare(["--storyboard", str(path), "--content-root", str(workspace)]) == 1
    assert not (workspace / "outputs").exists()
    assert not (tmp_path / "outputs").exists()
    assert (article / "storyboard.json").is_file()
    assert (article / "production.json").is_file()


def test_valid_v4_storyboard_still_reaches_the_render_entry(tmp_path, monkeypatch):
    """反向守卫：切换入口不能把 v4 自己也挡在门外。"""
    article = make_project(tmp_path, "videos", "demo", v4_storyboard())
    captured: list[dict] = []
    monkeypatch.setattr(cli, "render_with_remotion", lambda **kwargs: captured.append(kwargs) or SimpleNamespace(
        summary=lambda: "渲染完成"))
    monkeypatch.setattr(cli, "_aesthetic_render_gate", lambda *_args, **_kwargs: None)
    cli._force_utf8_output = lambda: None
    assert cli.main_render(["--storyboard", str(article / "storyboard.json"),
                            "--content-root", str(tmp_path), "--out", str(tmp_path / "out.mp4"),
                            "--no-probe"]) == 0
    assert captured and captured[0]["output"] == tmp_path / "out.mp4"


def test_legacy_script_copy_is_never_mutated(tmp_path):
    """拒绝是拒绝：入口不得改写源分镜（不迁移、不补齐）。"""
    script = _legacy_script(3)
    path = _write(tmp_path / "storyboard.json", script)
    original = path.read_text(encoding="utf-8")
    cli.main_validate([str(path)])
    assert path.read_text(encoding="utf-8") == original
    assert copy.deepcopy(script) == script
