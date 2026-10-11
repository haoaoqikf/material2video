from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from a2v.types.article import adapter


def test_prepare_bridge_passes_storyboard_option(monkeypatch, tmp_path: Path) -> None:
    storyboard = tmp_path / "storyboard.json"
    storyboard.write_text("{}", encoding="utf-8")
    calls: list[list[str]] = []

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

    result = adapter.prepare(tmp_path, {"materials": {"storyboard": "storyboard.json"}})

    assert calls[0][:2] == ["--storyboard", str(storyboard.resolve())]
    assert result["composition_id"] == "A2V"
    assert result["duration_in_frames"] == 90


def test_canonical_article_project_supplies_its_own_workspace_root(tmp_path: Path) -> None:
    article = tmp_path / "content" / "videos" / "embedded"
    assert adapter._content_root(article) == article.parent.parent
    assert adapter._content_args(article) == ["--content-root", str(article.parent.parent)]
