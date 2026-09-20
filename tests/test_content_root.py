"""内容根：文章与产物可以不在仓库里。

守三件事：

* **不设内容根时两层根重合**，既有调用方式与产物位置逐帧不变；
* **设了内容根**，仓库外文章的归属、产物与媒体目录都跟着工作区根走，
  且 `--content-root` 优先于 `A2V_CONTENT_ROOT`；
* **推不出来时报错并说明两条设置方式**，而不是猜一个位置——猜错的后果是
  把成片写到别处，而人直到打开目录才发现。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2v import cli, paths, storyboard as sb
from a2v.errors import A2VError

from conftest import SKILL_MARKER, make_project


def make_repo(tmp_path: Path) -> Path:
    """仓库侧：只有 skill 标记，没有内容。"""
    repo = tmp_path / "repo"
    marker = repo / SKILL_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("# article2video skill", encoding="utf-8")
    return repo


def make_content_root(tmp_path: Path, slug: str = "demo", script: dict | None = None) -> Path:
    """内容根侧：与仓库同构的 `videos/<slug>/`。"""
    content = tmp_path / "content"
    article = content / "videos" / slug
    article.mkdir(parents=True, exist_ok=True)
    (article / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")
    if script is not None:
        (article / "storyboard.json").write_text(
            json.dumps(script, ensure_ascii=False), encoding="utf-8"
        )
    return content


class TestContentRootResolution:
    def test_external_article_needs_a_content_root(self, tmp_path):
        """既不设参数也不设环境变量时，报错并点名两条设置方式。"""
        make_repo(tmp_path)
        content = make_content_root(tmp_path)
        page = content / "videos" / "demo" / "index.html"
        with pytest.raises(A2VError) as excinfo:
            paths.for_page(page)
        message = str(excinfo.value)
        assert "--content-root" in message and paths.CONTENT_ROOT_ENV in message

    def test_explicit_content_root_resolves_the_article(self, tmp_path):
        repo = make_repo(tmp_path)
        content = make_content_root(tmp_path, script={"version": 1})
        found = paths.for_page(content / "videos" / "demo" / "index.html", content)
        # 页面在仓库之外，向上找不到标记：仓库根回退到正在运行的 bundle 所在处，
        # 因为被挂载的共享资产就是那一份。
        assert found.repo_root != repo
        assert (found.repo_root / SKILL_MARKER).is_file()
        assert (found.repo_root / "pyproject.toml").is_file()
        assert found.workspace_root == content.resolve()
        assert found.kind == "article"
        assert found.slug == "demo"
        assert found.source_dir == content / "videos" / "demo"
        assert found.output_dir == content / "outputs" / "demo"
        assert found.media_dir == content / "outputs" / "demo" / "media"
        assert found.render_output(voiced=True) == content / "outputs" / "demo" / "voiced.mp4"

    def test_environment_variable_is_honoured(self, tmp_path, monkeypatch):
        make_repo(tmp_path)
        content = make_content_root(tmp_path)
        monkeypatch.setenv(paths.CONTENT_ROOT_ENV, str(content))
        found = paths.for_page(content / "videos" / "demo" / "index.html")
        assert found.workspace_root == content.resolve()
        assert found.output_dir == content / "outputs" / "demo"

    def test_explicit_argument_beats_environment(self, tmp_path, monkeypatch):
        make_repo(tmp_path)
        content = make_content_root(tmp_path)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.setenv(paths.CONTENT_ROOT_ENV, str(elsewhere))
        found = paths.for_page(content / "videos" / "demo" / "index.html", content)
        assert found.workspace_root == content.resolve()

    def test_repo_internal_example_wins_over_content_root(self, tmp_path, monkeypatch):
        """仓库自带的示例不随内容根漂移：仍按仓库根归属。"""
        repo = make_repo(tmp_path)
        sample = make_project(repo, "examples", "demo", None)
        content = make_content_root(tmp_path)
        monkeypatch.setenv(paths.CONTENT_ROOT_ENV, str(content))
        found = paths.for_page(sample / "index.html")
        assert found.workspace_root == repo.resolve()
        assert found.output_dir == repo / "outputs" / "examples" / "demo"

    def test_storyboard_in_content_root_resolves_the_same_article(self, tmp_path, valid_script):
        make_repo(tmp_path)
        content = make_content_root(tmp_path, script=valid_script)
        source = content / "videos" / "demo" / "storyboard.json"
        assert paths.for_storyboard(source, content).output_dir == content / "outputs" / "demo"
        assert paths.for_page(
            content / "videos" / "demo" / "index.html", content
        ).source_dir == paths.for_storyboard(source, content).source_dir

    def test_article_outside_both_roots_is_rejected(self, tmp_path):
        make_repo(tmp_path)
        content = make_content_root(tmp_path)
        loose = tmp_path / "loose" / "demo"
        loose.mkdir(parents=True)
        page = loose / "index.html"
        page.write_text("<html></html>", encoding="utf-8")
        with pytest.raises(A2VError, match="无法推导文章归属"):
            paths.for_page(page, content)


class TestContentRootReachesTheEntryPoints:
    def _render_args(self, content: Path, *extra: str):
        return cli._build_render_parser().parse_args(
            ["--storyboard", str(content / "videos" / "demo" / "storyboard.json"), *extra]
        )

    def test_cli_argument_selects_the_content_root(self, tmp_path, valid_script):
        make_repo(tmp_path)
        content = make_content_root(tmp_path, script=valid_script)
        args = self._render_args(content, "--content-root", str(content))
        article = cli._article_for(args, required=True)
        model, report = sb.load(args.storyboard)
        assert report.ok and model is not None
        output = cli._resolve_render_output(args, model, None, article)
        assert output == content / "outputs" / "demo" / "silent.mp4"

    def test_environment_variable_reaches_the_entry_point(self, tmp_path, valid_script, monkeypatch):
        make_repo(tmp_path)
        content = make_content_root(tmp_path, script=valid_script)
        monkeypatch.setenv(paths.CONTENT_ROOT_ENV, str(content))
        args = self._render_args(content)
        article = cli._article_for(args, required=True)
        assert article.output_dir == content / "outputs" / "demo"

    def test_cli_argument_beats_environment(self, tmp_path, valid_script, monkeypatch):
        make_repo(tmp_path)
        content = make_content_root(tmp_path, script=valid_script)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.setenv(paths.CONTENT_ROOT_ENV, str(elsewhere))
        args = self._render_args(content, "--content-root", str(content))
        assert cli._article_for(args, required=True).workspace_root == (
            content.resolve()
        )

    def test_missing_content_root_is_reported_not_guessed(self, tmp_path, valid_script, caplog):
        """声明式路径少了内容根：报错说明怎么设，不落到猜测的路径上。"""
        make_repo(tmp_path)
        content = make_content_root(tmp_path, script=valid_script)
        assert cli.main_render(["--storyboard", str(content / "videos" / "demo" / "storyboard.json")]) == 1
        assert paths.CONTENT_ROOT_ENV in caplog.text
        assert not (content / "outputs").exists()
        assert not (tmp_path / "repo" / "outputs").exists()

    def test_declarative_serve_root_follows_the_workspace(self, tmp_path, valid_script):
        """共享页面在仓库里、分镜在内容根里：静态根必须是内容根。"""
        from a2v.render import _default_serve_root

        make_repo(tmp_path)
        content = make_content_root(tmp_path, script=valid_script)
        page = content / "videos" / "demo" / "index.html"
        assert _default_serve_root(page, content) == paths.for_page(page, content).workspace_root
        assert _default_serve_root(page, content) == content.resolve()
        # 不告诉它内容根时推不出来，只能退回网页所在目录——这也是为什么
        # 四个入口都要把 --content-root 一路透传下去。
        assert _default_serve_root(page) == page.parent
