"""渲染前置检查：CSS 动画与时间/随机源的静态扫描。

扫描只做提示，不阻断渲染；但它必须在开渲前就把「预览正常、导出闪烁」
这类问题指出来，因此这里锁定三类行为：能命中、不误报、连共享资产一起扫。
"""

from __future__ import annotations

import logging

from a2v.render import _warn_on_time_driven_motion

CLEAN_PAGE = """<!doctype html>
<html><head><style>
  .card { transform: translateY(20px); opacity: .4; }
  .card:hover { border-color: rgba(255,255,255,.2); }
</style></head><body><script>requestAnimationFrame(function () {});</script></body></html>
"""

COUNT_UP_PAGE = """<!doctype html>
<html><head><style>
  .value { animation: count 1s linear; }
  @keyframes count { from { opacity: 0; } }
</style></head><body></body></html>
"""


def _warnings(caplog, page_text: str, tmp_path) -> list[str]:
    page = tmp_path / "index.html"
    page.write_text(page_text, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        _warn_on_time_driven_motion(page)
    return [record.getMessage() for record in caplog.records]


def test_clean_page_produces_no_warning(caplog, tmp_path):
    assert _warnings(caplog, CLEAN_PAGE, tmp_path) == []


def test_detects_animation_and_keyframes(caplog, tmp_path):
    messages = _warnings(caplog, COUNT_UP_PAGE, tmp_path)
    assert any("@keyframes" in message for message in messages)
    assert any("animation" in message for message in messages)


def test_detects_transition_in_linked_stylesheet(caplog, tmp_path):
    (tmp_path / "style.css").write_text(".a { transition: opacity .3s ease; }", encoding="utf-8")
    page = '<!doctype html><html><head><link rel="stylesheet" href="style.css"></head></html>'
    messages = _warnings(caplog, page, tmp_path)
    assert any("style.css" in message and "transition" in message for message in messages)


def test_ignores_remote_stylesheets(caplog, tmp_path):
    page = '<!doctype html><html><head><link rel="stylesheet" href="https://cdn.example.com/a.css"></head></html>'
    assert _warnings(caplog, page, tmp_path) == []


def test_missing_page_is_silent(caplog, tmp_path):
    with caplog.at_level(logging.WARNING):
        _warn_on_time_driven_motion(tmp_path / "absent.html")
    assert caplog.records == []


class TestSharedAssets:
    """共享资产（skill 的 assets/）在网页目录之外。

    只按网页目录判断范围会让动效悄悄绕过检查：把 animation 写进组件库照样
    会在成片里闪烁，所以扫描必须跟着 <link>/<script> 走到项目内。
    """

    @staticmethod
    def _project(tmp_path, html: str, asset_text: str, name: str):
        (tmp_path / ".git").mkdir()
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / name).write_text(asset_text, encoding="utf-8")
        page_dir = tmp_path / "videos" / "demo"
        page_dir.mkdir(parents=True)
        page = page_dir / "index.html"
        page.write_text(html, encoding="utf-8")
        return page

    def test_detects_animation_in_shared_stylesheet(self, caplog, tmp_path):
        page = self._project(
            tmp_path,
            '<!doctype html><html><head><link rel="stylesheet" href="../../assets/figures.css"></head></html>',
            ".fig { transition: transform .2s ease; }",
            "figures.css",
        )
        with caplog.at_level(logging.WARNING):
            _warn_on_time_driven_motion(page)
        assert any("figures.css" in record.getMessage() for record in caplog.records)

    def test_detects_time_source_in_shared_script(self, caplog, tmp_path):
        page = self._project(
            tmp_path,
            '<!doctype html><html><body><script src="../../assets/figures.js"></script></body></html>',
            "function f() { return Math.random() * Date.now(); }",
            "figures.js",
        )
        with caplog.at_level(logging.WARNING):
            _warn_on_time_driven_motion(page)
        messages = [record.getMessage() for record in caplog.records]
        assert any("Math.random()" in message for message in messages)
        assert any("Date.now()" in message for message in messages)

    def test_ignores_assets_outside_the_project(self, caplog, tmp_path):
        # 项目标记之外的路径不读，避免顺着相对路径读到仓库外的任意文件
        page = self._project(
            tmp_path,
            '<!doctype html><html><head><link rel="stylesheet" href="../../../../outside.css"></head></html>',
            "",
            "figures.css",
        )
        outside = tmp_path.parent / "outside.css"
        outside.write_text(".a { animation: x 1s; }", encoding="utf-8")
        try:
            with caplog.at_level(logging.WARNING):
                _warn_on_time_driven_motion(page)
            assert caplog.records == []
        finally:
            outside.unlink()

    def test_script_scan_does_not_flag_allowed_primitives(self, caplog, tmp_path):
        # 脚本只查时间与随机源：requestAnimationFrame 与按帧写 transform 是允许的
        page = self._project(
            tmp_path,
            '<!doctype html><html><body><script src="../../assets/figures.js"></script></body></html>',
            "requestAnimationFrame(tick); node.style.transform = 'scale(' + p + ')';",
            "figures.js",
        )
        with caplog.at_level(logging.WARNING):
            _warn_on_time_driven_motion(page)
        assert caplog.records == []
