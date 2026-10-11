from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from conftest import make_project
from m2v.types.article import adapter


def _stub_media_pipeline(monkeypatch, calls: list[list[str]]) -> None:
    """把配音与指纹相关的重活换掉，只观察传给底层 CLI 的参数。"""

    def prepare_media(args: list[str]) -> int:
        calls.append(args)
        output_dir = Path(args[args.index("--out-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "media.json").write_text("{}", encoding="utf-8")
        return 0

    monkeypatch.setattr(adapter, "validate", lambda *_: None)
    monkeypatch.setattr(adapter.cli, "main_prepare", prepare_media)
    monkeypatch.setattr(adapter.media, "load_media", lambda *_: SimpleNamespace(data={}, audio=None))
    monkeypatch.setattr(adapter.media, "effective_storyboard", lambda *_: {})
    monkeypatch.setattr(adapter, "_v4_model", lambda *_: SimpleNamespace(width=1080, height=1920, fps=30))
    monkeypatch.setattr(adapter, "resolve_v4", lambda *_: SimpleNamespace(total_frames=90))
    monkeypatch.setattr(adapter, "file_inputs", lambda *_: {})
    monkeypatch.setattr(adapter, "save_prepared", lambda *_args, **kwargs: kwargs)


def test_prepare_bridge_passes_storyboard_option(monkeypatch, tmp_path: Path) -> None:
    root = make_project(tmp_path, "videos", "demo", {})
    calls: list[list[str]] = []
    _stub_media_pipeline(monkeypatch, calls)

    result = adapter.prepare(root, {"materials": {"storyboard": "storyboard.json"}})

    assert calls[0][:2] == ["--storyboard", str((root / "storyboard.json").resolve())]
    assert Path(calls[0][calls[0].index("--out-dir") + 1]) == root / "outputs" / "media"
    assert result["composition_id"] == "M2V"
    assert result["duration_in_frames"] == 90


def test_canonical_article_project_supplies_its_own_workspace_root(tmp_path: Path) -> None:
    article = tmp_path / "content" / "videos" / "embedded"
    assert adapter._content_root(article) == article.parent.parent
    assert adapter._content_args(article) == ["--content-root", str(article.parent.parent)]


def test_shipped_example_writes_beside_videos_not_inside_the_versioned_source(
    monkeypatch, tmp_path: Path
) -> None:
    """示例的产物属于 `videos/examples/<slug>/outputs/`，不是 `examples/<slug>/outputs/`。

    写错位置会把运行记录、音轨和成片落进受版本控制的示例目录里。
    """
    root = make_project(tmp_path, "examples", "demo", {})
    calls: list[list[str]] = []
    _stub_media_pipeline(monkeypatch, calls)

    project = {"materials": {"storyboard": "storyboard.json"}}
    expected_outputs = tmp_path / "videos" / "examples" / "demo" / "outputs"

    article = adapter._article(root, project)
    assert article.output_dir == expected_outputs
    assert not (root / "outputs").exists()

    adapter.prepare(root, project)
    assert Path(calls[0][calls[0].index("--out-dir") + 1]) == expected_outputs / "media"

    preview_args: list[list[str]] = []
    monkeypatch.setattr(adapter.cli, "main_render", lambda args: preview_args.append(args) or 0)
    preview = adapter.preview(root, project, limit_frames=12)
    assert preview == expected_outputs / "previews" / "video.mp4"
    assert Path(preview_args[0][preview_args[0].index("--out") + 1]) == preview

    monkeypatch.setattr(adapter.cli, "main_render", lambda _args: 0)
    assert adapter.render(root, project) == expected_outputs / "silent.mp4"
    assert not (root / "outputs").exists()
