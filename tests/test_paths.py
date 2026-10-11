"""目录约定与输出路径推导的回归测试。

这些用例守住多篇文章的隔离边界：产物必须落在各自文章目录的 outputs/ 下，
示例产物再独立一层，且推导结果与执行命令时的工作目录无关。

执行入口只接受分镜 v4，因此这里的分镜一律用 `valid_script_v4` 构造；
v1–v3 分镜会被入口直接拒绝，不再覆盖本模块的路径推导行为。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import m2v.types.article.cli as cli
import m2v.types.article.paths as paths
import m2v.types.article.prepare as prep
from m2v.core.errors import M2VError
from m2v.types.article.media import Media
from m2v.types.article.render import RenderResult

from conftest import SKILL_MARKER, approve_input_review, approve_production_record, make_project


def _approve_render_gate(article: Path, media_path: Path | None = None) -> None:
    inspect = article / "outputs" / "inspect"
    inspect.mkdir(parents=True, exist_ok=True)
    (inspect / "report.json").write_text(json.dumps({"aestheticReview": {"findings": []}}), encoding="utf-8")
    # 正式渲染门禁还要求 review.md 的全片节奏单项评分：只写发布结论会被判为待评审。
    (inspect / "review.md").write_text(
        "# 视觉评审\n\n"
        "| 项 | 分 | 依据 |\n| --- | --- | --- |\n"
        "| 节奏 | 4 | 00:00 开场建立；00:01 核心动作推进后停留（渲染路径测试夹具） |\n\n"
        "- 是否值得发布：通过\n",
        encoding="utf-8",
    )
    # 生产记录（含 v4 正式渲染要求的五项全片连续性结论）由 conftest 统一补齐。
    approve_production_record(article / "storyboard.json", media_path)


class TestProjectRoot:
    def test_finds_root_from_nested_file(self, tmp_path, valid_script_v4):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        assert paths.project_root(article / "index.html") == tmp_path

    def test_finds_root_from_directory(self, tmp_path, valid_script_v4):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        assert paths.project_root(article) == tmp_path

    def test_rejects_directory_without_marker(self, tmp_path):
        loose = tmp_path / "somewhere"
        loose.mkdir()
        (loose / "index.html").write_text("<html></html>", encoding="utf-8")
        with pytest.raises(M2VError, match="未找到仓库根目录"):
            paths.project_root(loose / "index.html")

    def test_git_root_alone_is_not_enough(self, tmp_path):
        # 只用 .git 判断会把任意仓库顶层误认为仓库根，进而把产物写到错误位置
        (tmp_path / ".git").mkdir()
        page = tmp_path / "index.html"
        page.write_text("<html></html>", encoding="utf-8")
        with pytest.raises(M2VError, match="未找到仓库根目录"):
            paths.project_root(page)


class TestArticleLocation:
    def test_locates_videos_article(self, tmp_path, valid_script_v4):
        make_project(tmp_path, "videos", "why-rest", valid_script_v4)
        root = tmp_path
        assert paths.locate_article(root, root / "videos" / "why-rest" / "index.html") == (
            "article",
            "why-rest",
        )

    def test_locates_example(self, tmp_path, valid_script_v4):
        make_project(tmp_path, "examples", "why-rest", valid_script_v4)
        root = tmp_path
        assert paths.locate_article(root, root / "examples" / "why-rest") == ("example", "why-rest")

    def test_deep_file_still_belongs_to_its_article(self, tmp_path, valid_script_v4):
        # videos/<slug>/assets/page.html 仍在文章目录内，应归属该文章而不是更深的目录
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        nested = article / "assets"
        nested.mkdir()
        page = nested / "index.html"
        page.write_text("<html></html>", encoding="utf-8")
        assert paths.locate_article(tmp_path, page) == ("article", "demo")

    def test_article_outside_root_is_rejected(self, tmp_path, valid_script_v4):
        other = tmp_path / "elsewhere"
        make_project(other, "videos", "demo", valid_script_v4)
        with pytest.raises(M2VError, match="无法推导文章归属"):
            paths.locate_article(tmp_path, other / "videos" / "demo" / "index.html")


class TestOutputLayout:
    def test_article_outputs_use_slug_directory(self, tmp_path, valid_script_v4):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        found = paths.for_page(article / "index.html")
        assert found.slug == "demo"
        assert found.kind == "article"
        assert found.output_dir == tmp_path / "videos" / "demo" / "outputs"
        assert found.media_dir == tmp_path / "videos" / "demo" / "outputs" / "media"
        assert found.media_manifest == tmp_path / "videos" / "demo" / "outputs" / "media" / "media.json"
        assert found.render_output(voiced=False) == tmp_path / "videos" / "demo" / "outputs" / "silent.mp4"
        assert found.render_output(voiced=True) == tmp_path / "videos" / "demo" / "outputs" / "voiced.mp4"

    def test_example_outputs_get_their_own_layer(self, tmp_path, valid_script_v4):
        # 示例与实际文章可能同名，产物必须分开放，避免互相覆盖
        article = make_project(tmp_path, "examples", "demo", valid_script_v4)
        found = paths.for_page(article / "index.html")
        assert found.output_dir == tmp_path / "videos" / "examples" / "demo" / "outputs"

    def test_preview_output_keeps_final_name(self, tmp_path, valid_script_v4):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        found = paths.for_page(article / "index.html")
        assert found.render_output(voiced=False, preview=True) == (
            tmp_path / "videos" / "demo" / "outputs" / "previews" / "silent.mp4"
        )
        assert found.render_output(voiced=True, preview=True) == (
            tmp_path / "videos" / "demo" / "outputs" / "previews" / "voiced.mp4"
        )

    def test_same_slug_isolated_between_articles(self, tmp_path, valid_script_v4):
        first = make_project(tmp_path, "videos", "alpha", valid_script_v4)
        second = make_project(tmp_path, "videos", "beta", valid_script_v4)
        assert paths.for_page(first / "index.html").output_dir != paths.for_page(
            second / "index.html"
        ).output_dir

    def test_same_slug_isolated_between_article_and_example(self, tmp_path, valid_script_v4):
        real = make_project(tmp_path, "videos", "demo", valid_script_v4)
        sample = make_project(tmp_path, "examples", "demo", valid_script_v4)
        assert paths.for_page(real / "index.html").output_dir != paths.for_page(
            sample / "index.html"
        ).output_dir

    def test_result_is_independent_of_working_directory(self, tmp_path, valid_script_v4, monkeypatch):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        page = article / "index.html"
        expected = paths.for_page(page).output_dir
        monkeypatch.chdir(tmp_path.parent)
        assert paths.for_page(page).output_dir == expected


class TestUnsupportedTargets:
    def test_remote_page_requires_explicit_output(self):
        with pytest.raises(M2VError, match="远程页面"):
            paths.for_page("https://example.com/index.html")

    def test_missing_page_reports_clearly(self, tmp_path):
        with pytest.raises(M2VError, match="页面文件不存在"):
            paths.for_page(tmp_path / "absent.html")

    def test_directory_as_page_is_rejected(self, tmp_path, valid_script_v4):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        with pytest.raises(M2VError, match="需要一个页面文件"):
            paths.for_page(article)

    def test_page_outside_article_directories_is_rejected(self, tmp_path):
        marker = tmp_path / SKILL_MARKER
        marker.parent.mkdir(parents=True)
        marker.write_text("# skill", encoding="utf-8")
        page = tmp_path / "index.html"
        page.write_text("<html></html>", encoding="utf-8")
        with pytest.raises(M2VError, match="无法推导文章归属"):
            paths.for_page(page)

    def test_missing_storyboard_reports_clearly(self, tmp_path):
        with pytest.raises(M2VError, match="分镜脚本不存在"):
            paths.for_storyboard(tmp_path / "absent.json")


class TestNaming:
    def test_media_presence_drives_voiced_name(self):
        # 文件名跟随实际音轨：有声导出用 voiced，无声导出用 silent
        assert paths.use_voiced_name(declares_voice=True, with_media=True) is True
        assert paths.use_voiced_name(declares_voice=False, with_media=True) is True
        assert paths.use_voiced_name(declares_voice=False, with_media=False) is False

    def test_voiced_name_keeps_silent_file_name(self, caplog):
        # 分镜有口播但没给媒体时保持 silent 文件名，同时给出可定位的警告
        assert paths.use_voiced_name(declares_voice=True, with_media=False) is False
        assert "m2v prepare" in caplog.text

    @pytest.mark.parametrize(
        "segments, expected",
        [
            ([], False),
            (None, False),
            ([{"id": "n1", "text": "有口播", "beatId": "beat-open"}], True),
        ],
        ids=["empty-segments", "missing-segments", "declared-narration"],
    )
    def test_declares_narration_reads_v4_has_narration(self, valid_script_v4, segments, expected):
        """v4 只在模型层读口播声明：整片没有或只有空的口播分段都算无声。

        v3 的 `scene.narration` / 逐幕 `narrationSegments` 已无对应产品行为，
        因此改为在 v4 模型上验证同一条判定。
        """
        for stage in valid_script_v4["stages"]:
            if segments is None:
                stage.pop("narrationSegments", None)
            else:
                stage["narrationSegments"] = [dict(item) for item in segments]
        model = cli._v4_model(valid_script_v4)
        assert paths.declares_narration(model) is expected


def _capture_render(monkeypatch) -> list[dict]:
    """替换 CLI 里的 render，避免为了验证路径选择真的启动浏览器。"""
    captured: list[dict] = []

    def fake_render(**kwargs):
        captured.append(kwargs)
        output = Path(kwargs["output"])
        return RenderResult(
            output=output,
            frames=1,
            fps=30,
            width=1080,
            height=1920,
            duration_seconds=1 / 30,
            capture_seconds=0.1,
            total_seconds=0.2,
            size_bytes=1234,
        )

    monkeypatch.setattr(cli, "render_with_remotion", fake_render)
    return captured


class TestVoicedRenderDefaults:
    @pytest.fixture
    def voiced_project(self, tmp_path, valid_script_v4, speech):
        """带口播的项目：v4 分镜自身声明口播，真实 prepare 生成媒体清单，再按推导路径加载。"""
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        return tmp_path, article

    def test_media_renders_to_voiced_name(self, voiced_project, monkeypatch):
        root, article = voiced_project
        media_path = prep.prepare(article / "storyboard.json", root / "videos" / "demo" / "outputs" / "media")
        _approve_render_gate(article, media_path)
        captured = _capture_render(monkeypatch)
        assert cli.main_render(
            [
                "--storyboard", str(article / "storyboard.json"),
                "--media", str(media_path),
                "--no-probe",
            ]
        ) == 0
        assert captured[0]["output"] == root / "videos" / "demo" / "outputs" / "voiced.mp4"

    def test_media_from_another_article_is_rejected(self, voiced_project, monkeypatch):
        root, article = voiced_project
        # other 用同一份分镜内容，确保被拒绝的原因是文章归属而不是指纹不匹配
        (root / "videos" / "other").mkdir(parents=True)
        other = make_project(root, "videos", "other", None)
        (other / "storyboard.json").write_text(
            (article / "storyboard.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        media_path = prep.prepare(article / "storyboard.json", root / "videos" / "demo" / "outputs" / "media")
        _approve_render_gate(other, media_path)
        _capture_render(monkeypatch)
        # 媒体清单属于 demo，却拿 other 的网页来渲染：必须拒绝，避免音画串文章
        assert cli.main_render(
            [
                "--storyboard", str(other / "storyboard.json"),
                "--media", str(media_path),
                "--no-probe",
            ]
        ) == 1


class TestRemotionDefault:
    """默认引擎是 Remotion：只给 --storyboard 的命令走 composition 渲染。"""

    def test_bare_storyboard_routes_to_remotion(self, tmp_path, valid_script_v4, monkeypatch, speech):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        media_path = prep.prepare(article / "storyboard.json", tmp_path / "videos" / "demo" / "outputs" / "media")
        _approve_render_gate(article, media_path)
        captured: list[dict] = []

        def fake_remotion(**kwargs):
            captured.append(kwargs)
            return RenderResult(
                output=Path(kwargs["output"]),
                frames=30,
                fps=30,
                width=1080,
                height=1920,
                duration_seconds=1.0,
                capture_seconds=1.0,
                total_seconds=2.0,
                size_bytes=1234,
            )

        monkeypatch.setattr(cli, "render_with_remotion", fake_remotion)
        code = cli.main_render(
            [
                "--storyboard", str(article / "storyboard.json"),
                "--media", str(media_path),
                "--out", str(tmp_path / "out.mp4"),
                "--no-probe",
            ]
        )
        assert code == 0
        assert captured, "默认引擎应走 render_with_remotion"
        assert captured[0]["output"] == tmp_path / "out.mp4"

class TestCrossArticleMediaGuard:
    """直接验证跨文章合成的拦截逻辑。

    走完整 CLI 时 load_media 的分镜指纹校验会先一步拦下大多数组合，
    因而这里用最小替身单独覆盖归属判断本身。
    """

    def test_same_article_media_is_accepted(self, tmp_path, valid_script_v4):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        media_dir = tmp_path / "videos" / "demo" / "outputs" / "media"
        media_dir.mkdir(parents=True)
        manifest = media_dir / "media.json"
        manifest.write_text("{}", encoding="utf-8")
        model = cli._v4_model(valid_script_v4)
        media = Media(manifest.resolve(), {}, model, media_dir / "audio.wav")

        args = cli._build_render_parser().parse_args(["--storyboard", str(article / "storyboard.json")])
        output = cli._resolve_render_output(args, model, media)
        assert output == tmp_path / "videos" / "demo" / "outputs" / "voiced.mp4"

    def test_storyboard_and_media_of_other_article_is_rejected(self, tmp_path, valid_script_v4):
        # 网页、分镜、媒体三者都属于 other，但网页必须与媒体同源：
        # 这里 other 的一对看似自洽，却与 demo 的媒体目录不一致，应被拦下
        other = make_project(tmp_path, "videos", "other", valid_script_v4)
        media_dir = tmp_path / "videos" / "demo" / "outputs" / "media"
        media_dir.mkdir(parents=True)
        manifest = media_dir / "media.json"
        manifest.write_text("{}", encoding="utf-8")
        model = cli._v4_model(valid_script_v4)

        args = cli._build_render_parser().parse_args(["--storyboard", str(other / "storyboard.json")])
        with pytest.raises(M2VError, match="无法确认它与本篇文章同源"):
            cli._resolve_render_output(
                args, model, Media(manifest.resolve(), {}, model, media_dir / "audio.wav")
            )

    def test_media_outside_slug_media_dir_is_rejected(self, tmp_path, valid_script_v4):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        elsewhere = tmp_path / "scratch"
        elsewhere.mkdir()
        manifest = elsewhere / "media.json"
        manifest.write_text("{}", encoding="utf-8")
        model = cli._v4_model(valid_script_v4)

        args = cli._build_render_parser().parse_args(
            [
                "--storyboard", str(article / "storyboard.json"),
            ]
        )
        with pytest.raises(M2VError, match="无法确认它与本篇文章同源"):
            cli._resolve_render_output(
                args, model, Media(manifest.resolve(), {}, model, elsewhere / "audio.wav")
            )


class TestPrepareCommandDefaults:
    @pytest.mark.parametrize(
        "command",
        [cli.main_render, cli.main_prepare, cli.main_preview, cli.main_validate],
    )
    def test_help_exits_cleanly(self, command, capsys):
        # argparse 的 help 文本会做 % 格式化：文案里的裸 % 会让 --help 直接崩溃
        with pytest.raises(SystemExit) as exit_info:
            command(["--help"])
        assert exit_info.value.code == 0

    def test_out_dir_defaults_to_media_directory(self, tmp_path, valid_script_v4, monkeypatch):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        approve_input_review(article / "storyboard.json")
        calls: list[dict] = []

        def fake_prepare(storyboard, out_dir, voice, rate, force):
            calls.append({"storyboard": storyboard, "out_dir": Path(out_dir)})
            return Path(out_dir) / "media.json"

        monkeypatch.setattr(prep, "prepare", fake_prepare)
        assert cli.main_prepare(["--storyboard", str(article / "storyboard.json")]) == 0
        assert calls[0]["out_dir"] == tmp_path / "videos" / "demo" / "outputs" / "media"

    def test_foreign_outputs_media_dir_is_rejected(self, tmp_path, valid_script_v4, monkeypatch):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        monkeypatch.setattr(prep, "prepare", lambda *a, **k: Path("media.json"))
        # 显式写到另一篇文章的 media/ 属于冲突，必须保留原文件并报错
        assert cli.main_prepare(
            [
                "--storyboard", str(article / "storyboard.json"),
                "--out-dir", str(tmp_path / "outputs" / "someone-else" / "media"),
            ]
        ) == 1

    def test_explicit_out_dir_outside_outputs_is_allowed(self, tmp_path, valid_script_v4, monkeypatch):
        article = make_project(tmp_path, "videos", "demo", valid_script_v4)
        approve_input_review(article / "storyboard.json")
        target = tmp_path / "scratch-media"
        monkeypatch.setattr(prep, "prepare", lambda *a, **k: target / "media.json")
        assert cli.main_prepare(
            ["--storyboard", str(article / "storyboard.json"), "--out-dir", str(target)]
        ) == 0
