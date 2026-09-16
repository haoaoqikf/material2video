"""渲染前置检查：CSS 动画静态扫描。

扫描只做提示，不阻断渲染；但它必须在开渲前就把「预览正常、导出闪烁」
这类问题指出来，因此这里锁定两类行为：能命中、且不误报。
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
    assert any("CSS animation" in message for message in messages)


def test_detects_transition_in_linked_stylesheet(caplog, tmp_path):
    (tmp_path / "style.css").write_text(".a { transition: opacity .3s ease; }", encoding="utf-8")
    page = '<!doctype html><html><head><link rel="stylesheet" href="style.css"></head></html>'
    messages = _warnings(caplog, page, tmp_path)
    assert any("style.css" in message and "CSS transition" in message for message in messages)


def test_ignores_remote_stylesheets(caplog, tmp_path):
    page = '<!doctype html><html><head><link rel="stylesheet" href="https://cdn.example.com/a.css"></head></html>'
    assert _warnings(caplog, page, tmp_path) == []


def test_missing_page_is_silent(caplog, tmp_path):
    with caplog.at_level(logging.WARNING):
        _warn_on_time_driven_motion(tmp_path / "absent.html")
    assert caplog.records == []
