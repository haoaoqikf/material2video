"""端到端验证「默认输出链路」。

单元测试用替身检查路径选择，这里真的跑一遍渲染：确认默认推导出的
outputs/<slug>/ 目录会被创建、成片与字幕落在正确位置，且限帧试渲染
写进 previews/ 而不是覆盖正式成片。
"""

from __future__ import annotations

import shutil

import pytest

from a2v import cli
from conftest import EXAMPLES_DIR, SCRIPTS_DIR, SKILL_MARKER, make_project

ASSETS_DIR = SCRIPTS_DIR.parent / "assets"


@pytest.fixture
def example_project(tmp_path):
    """把示例源文件复制进一个临时项目，避免碰到仓库里已有的产物。

    网页通过相对路径引用共享 skill 资产（base.css / timeline.js），因此临时
    项目也要带上同样的目录层级，默认静态根才解析得到这些资源。
    """
    make_project(tmp_path, "examples", "why-effort-fails", None)
    shutil.copytree(ASSETS_DIR, tmp_path / SKILL_MARKER.parent / "assets")

    article = tmp_path / "examples" / "why-effort-fails"
    for name in ("index.html", "storyboard.json", "article.md"):
        if (EXAMPLES_DIR / name).is_file():
            shutil.copy2(EXAMPLES_DIR / name, article / name)
    return tmp_path, article


def _render_args(article, *extra):
    return [
        "--page", str(article / "index.html"),
        "--storyboard", str(article / "storyboard.json"),
        *extra,
    ]


class TestDefaultRenderPipeline:
    def test_limit_frames_writes_preview_and_keeps_final_free(
        self, chromium_ready, example_project
    ):
        root, article = example_project
        preview = root / "outputs" / "examples" / "why-effort-fails" / "previews" / "silent.mp4"
        final = root / "outputs" / "examples" / "why-effort-fails" / "silent.mp4"

        assert cli.main_render(_render_args(article, "--limit-frames", "3")) == 0
        assert preview.is_file()
        assert not final.exists(), "限帧试渲染不能创建正式成片"

        assert cli.main_render(_render_args(article)) == 0
        assert final.is_file()
        assert preview.is_file(), "正式渲染不应删除已有的试渲染文件"

    def test_voiced_render_writes_mp4_and_srt(self, chromium_ready, example_project, speech):
        root, article = example_project
        assert cli.main_prepare(["--storyboard", str(article / "storyboard.json")]) == 0
        media = root / "outputs" / "examples" / "why-effort-fails" / "media" / "media.json"
        assert media.is_file()

        assert cli.main_render(
            _render_args(article, "--media", str(media), "--limit-frames", "3")
        ) == 0
        voiced = root / "outputs" / "examples" / "why-effort-fails" / "previews" / "voiced.mp4"
        assert voiced.is_file()
        assert voiced.with_suffix(".srt").is_file()
        # 有声导出不应污染无声成片的文件名
        assert not (voiced.parent / "silent.mp4").exists()

    def test_explicit_out_still_supported(self, chromium_ready, example_project):
        # 旧调用方式必须继续可用：显式 --out 时不改写文件名
        root, article = example_project
        explicit = root / "legacy" / "custom.mp4"
        assert cli.main_render(
            _render_args(article, "--out", str(explicit), "--limit-frames", "3")
        ) == 0
        assert explicit.is_file()
