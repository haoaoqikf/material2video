"""设计宪法的机检部分。

宪法文档里每一条都标了「能不能机检」，这里的用例负责保证
**标了机检的确实查得出来，没标机检的不会被假装查出来**。
误报和漏报一样有害：误报会让人学会忽略警告。
"""

from __future__ import annotations

from pathlib import Path

from a2v import constitution

PAGE = """<!doctype html>
<html><head>
<link rel="stylesheet" href="theme.css">
</head><body>
<div data-a2v-stage>
  <div class="stage-bg" aria-hidden="true"></div>
  <section data-a2v-scene data-scene-id="one">
    <div class="a2v-safe" data-a2v-figure></div>
  </section>
</div>
<script src="timeline.js"></script>
</body></html>
"""

THEME = ":root { --a2v-safe-top: 220px; --a2v-safe-bottom: 320px; }"
SCRIPT = "api.progress(f, 0, 30, 'outQuint'); api.progress(f, 0, 30, 'inOutCubic');"


def _project(tmp_path: Path, page: str = PAGE, theme: str = THEME, script: str = SCRIPT) -> Path:
    (tmp_path / "theme.css").write_text(theme, encoding="utf-8")
    (tmp_path / "timeline.js").write_text(script, encoding="utf-8")
    target = tmp_path / "index.html"
    target.write_text(page, encoding="utf-8")
    return target


def _paths(report) -> list[str]:
    return [issue.path for issue in report.issues]


def test_clean_page_passes(tmp_path):
    report = constitution.check_page(_project(tmp_path))
    assert report.errors == []
    assert report.warnings == []


def test_requires_stage(tmp_path):
    page = PAGE.replace(" data-a2v-stage", "")
    assert any("#C1" in path for path in _paths(constitution.check_page(_project(tmp_path, page))))


def test_warns_without_background_layer(tmp_path):
    page = PAGE.replace('<div class="stage-bg" aria-hidden="true"></div>', "")
    report = constitution.check_page(_project(tmp_path, page))
    assert "index.html#C1" in _paths(report)
    assert report.ok


def test_mount_count_ignores_css_selectors(tmp_path):
    """选择器里也会出现属性名，数标签而不是数字符串。

    页面的 <style> 里几乎必然有 `[data-a2v-scene] { … }`，
    按字符串计数会把场景数多算一个，从而误报挂载点不足。
    """
    page = PAGE.replace(
        "</head>",
        "<style>[data-a2v-scene] { z-index: 1; } [data-a2v-figure] { display: block; }</style></head>",
    )
    report = constitution.check_page(_project(tmp_path, page))
    assert "#C4" not in " ".join(_paths(report))


def test_flags_missing_mount(tmp_path):
    """一个挂载点都没有：只提醒（网页可能自己画图形），不判失败。"""
    page = PAGE.replace(" data-a2v-figure", "")
    report = constitution.check_page(_project(tmp_path, page))
    assert "index.html#C4" in _paths(report)
    assert report.ok


def test_partial_mounting_is_an_error(tmp_path):
    """部分挂载才是真错误：没接组件的场景在成片里是空白。"""
    page = PAGE.replace(
        "</div>\n<script",
        "</div>\n<section data-a2v-scene data-scene-id=\"two\"></section>\n</div>\n<script",
    )
    report = constitution.check_page(_project(tmp_path, page))
    assert "index.html#C4" in _paths(report)
    assert not report.ok


def test_flags_extra_curve(tmp_path):
    script = "api.progress(f, 0, 30, 'outBack');"
    report = constitution.check_page(_project(tmp_path, script=script))
    assert any("#C2" in path for path in _paths(report))


def test_curve_check_ignores_identifiers(tmp_path):
    """`'input'` 这类普通字符串不是曲线名，不能报。"""
    script = "node.tagName === 'input'; el.type = 'output'; var x = 'linear';"
    report = constitution.check_page(_project(tmp_path, script=script))
    assert "#C2" not in " ".join(_paths(report))


def test_curve_check_ignores_comments(tmp_path):
    script = "// 以前用过 'outBack'，现在统一走三条曲线\napi.progress(f, 0, 30, 'outQuint');"
    report = constitution.check_page(_project(tmp_path, script=script))
    assert "#C2" not in " ".join(_paths(report))


def test_flags_blur(tmp_path):
    report = constitution.check_page(_project(tmp_path, theme=THEME + "\n.glow { filter: blur(24px); }"))
    assert any("#C3" in path for path in _paths(report))


def test_flags_blur_in_shared_stylesheet(tmp_path):
    """共享资产也要查：把模糊写进组件库是最容易漏的一处。"""
    asset = tmp_path / "assets"
    asset.mkdir()
    (asset / "figures.css").write_text(".halo { backdrop-filter: blur(8px); }", encoding="utf-8")
    page = PAGE.replace("</head>", '<link rel="stylesheet" href="assets/figures.css"></head>')
    report = constitution.check_page(_project(tmp_path, page))
    assert any("#C3" in path for path in _paths(report))


def test_warns_without_safe_area_tokens(tmp_path):
    report = constitution.check_page(_project(tmp_path, theme=":root { --x: 1; }"))
    assert "index.html#C6" in _paths(report)


class TestSingleSource:
    """C12：文案只写在分镜里。"""

    @staticmethod
    def _scenes(data: dict) -> list[dict]:
        return [{"id": "one", "type": "title", "durationInFrames": 30, "data": data}]

    def test_flags_storyboard_sentence_copied_into_page(self, tmp_path):
        sentence = "最坏的结果不过就是这家公司不要你"
        page = PAGE.replace("</body>", f"<p>{sentence}</p></body>")
        scenes = self._scenes({"text": sentence})
        report = constitution.check_page(_project(tmp_path, page), constitution.storyboard_texts(scenes))
        assert "index.html#C5" in _paths(report)

    def test_ignores_short_labels(self, tmp_path):
        # 短标签（角标、图形上的短词）与网页上的固定词组重合是正常的
        page = PAGE.replace("</body>", "<span>开场命题</span></body>")
        scenes = self._scenes({"text": "开场命题"})
        report = constitution.check_page(_project(tmp_path, page), constitution.storyboard_texts(scenes))
        assert report.errors == []

    def test_ignores_copy_inside_comments(self, tmp_path):
        sentence = "最坏的结果不过就是这家公司不要你"
        page = PAGE.replace("</body>", f"<!-- {sentence} --></body>")
        scenes = self._scenes({"text": sentence})
        report = constitution.check_page(_project(tmp_path, page), constitution.storyboard_texts(scenes))
        assert report.errors == []

    def test_compares_line_by_line(self, tmp_path):
        """分镜用 \n 手动折行，网页里按行出现同样要判为抄写。"""
        page = PAGE.replace("</body>", "<p>不过就是这家公司不要你。</p></body>")
        scenes = self._scenes({"text": "最坏的结果，\n不过就是这家公司不要你。"})
        report = constitution.check_page(_project(tmp_path, page), constitution.storyboard_texts(scenes))
        assert "index.html#C5" in _paths(report)

    def test_ignores_labels_under_figure(self, tmp_path):
        """figure.labels 是画在图上的标注，不参与「正文真源」比对。"""
        texts = constitution.storyboard_texts(
            self._scenes({"text": "短文案", "figure": {"kind": "gap", "labels": {"assumption": "假设已经拥有"}}})
        )
        assert "假设已经拥有" not in texts

    def test_missing_page_is_an_error(self, tmp_path):
        report = constitution.check_page(tmp_path / "absent.html")
        assert not report.ok
