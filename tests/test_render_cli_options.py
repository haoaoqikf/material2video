"""正式 render CLI 的并发与缓存开关。

对应 openspec 变更 `optimize-final-video-render` 的任务 3.1：
`--concurrency` 必须是正整数、默认 1，非法取值在**打包之前**失败；
`--no-bundle-cache` 只影响本次是否复用缓存，不改变输出参数。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import m2v.types.article.cli as cli
import m2v.types.article.prepare as prep
from m2v.types.article.render import RenderResult
from conftest import make_project

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_paths import _approve_render_gate  # noqa: E402


def _capture(monkeypatch) -> list[dict]:
    captured: list[dict] = []

    def fake(**kwargs):
        captured.append(kwargs)
        return RenderResult(
            output=Path(kwargs["output"]),
            frames=1,
            fps=30,
            width=1080,
            height=1920,
            duration_seconds=1 / 30,
            capture_seconds=0.1,
            total_seconds=0.2,
            size_bytes=1234,
        )

    monkeypatch.setattr(cli, "render_with_remotion", fake)
    return captured


@pytest.fixture
def project(tmp_path, valid_script_v4, speech):
    article = make_project(tmp_path, "videos", "demo", valid_script_v4)
    media = prep.prepare(
        article / "storyboard.json", tmp_path / "videos" / "demo" / "outputs" / "media"
    )
    _approve_render_gate(article, media)
    return tmp_path, article, media


def _argv(article, media, *extra):
    return [
        "--storyboard", str(article / "storyboard.json"),
        "--media", str(media),
        "--no-probe",
        *extra,
    ]


def test_default_concurrency_is_one_and_the_cache_is_enabled(project, monkeypatch):
    _root, article, media = project
    captured = _capture(monkeypatch)
    assert cli.main_render(_argv(article, media)) == 0
    assert captured[0]["concurrency"] == 1
    assert captured[0]["bundle_cache"] is True


def test_explicit_concurrency_reaches_the_renderer(project, monkeypatch):
    _root, article, media = project
    captured = _capture(monkeypatch)
    assert cli.main_render(_argv(article, media, "--concurrency", "3")) == 0
    assert captured[0]["concurrency"] == 3


def test_no_bundle_cache_only_disables_the_cache(project, monkeypatch):
    _root, article, media = project
    captured = _capture(monkeypatch)
    assert cli.main_render(_argv(article, media, "--no-bundle-cache")) == 0
    assert captured[0]["bundle_cache"] is False
    assert captured[0]["concurrency"] == 1


@pytest.mark.parametrize("value", ["0", "-2", "abc", "1.5", ""])
def test_invalid_concurrency_fails_before_anything_is_packed(project, monkeypatch, capsys, value):
    _root, article, media = project
    captured = _capture(monkeypatch)
    with pytest.raises(SystemExit) as excinfo:
        cli.main_render(_argv(article, media, "--concurrency", value))
    assert excinfo.value.code == 2
    assert captured == [], "参数非法时不得进入渲染（更不得打包）"
    assert "--concurrency" in capsys.readouterr().err


def test_formal_gate_still_blocks_before_the_renderer_is_entered(
    tmp_path, valid_script_v4, speech, monkeypatch
):
    """缓存与并发都不改变「先过门禁」：缺评审记录时连渲染器都不进。"""
    article = make_project(tmp_path, "videos", "demo", valid_script_v4)
    media = prep.prepare(
        article / "storyboard.json", tmp_path / "videos" / "demo" / "outputs" / "media"
    )
    captured = _capture(monkeypatch)
    assert cli.main_render(_argv(article, media)) != 0
    assert captured == [], "门禁未通过时不得进入渲染"
