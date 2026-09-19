"""声明式页面的完整路径：无专属网页、分镜定位与帧确定性。"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from a2v import cli, paths, storyboard as sb
from a2v.browser import open_animated_page
from a2v.render import _resolve_page_url


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/declarative-number/storyboard.json"


def test_example_has_no_page_and_validates():
    assert not (SOURCE.parent / "index.html").exists()
    model, report = sb.load(SOURCE, declarative=True)
    assert model is not None and report.ok
    assert model.total_frames == 180


def test_paths_do_not_depend_on_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    article = paths.for_storyboard(SOURCE)
    assert cli._storyboard_url(SOURCE, article) == "/examples/declarative-number/storyboard.json"
    assert cli._shared_page(article).is_file()
    assert cli.main_validate([str(SOURCE), "--declarative", "--strict"]) == 0


def test_shared_page_repeats_same_frame(chromium_ready):
    # 共享页面在仓库里、分镜在工作区根下：静态根取工作区根，页面与分镜
    # 因此同源。工作区根在仓库之外时，页面改由 `/__a2v__/` 别名提供
    # （见 test_content_root.py），这里先守住仓库内这条路径。
    article = paths.for_storyboard(SOURCE)
    page = cli._shared_page(article)
    with _resolve_page_url(page, article.workspace_root) as base:
        url = base + "?" + urlencode({"a2v-storyboard": cli._storyboard_url(SOURCE, article)})
        with open_animated_page(url, width=1080, height=1920) as session:
            session.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
            assert session.contract.duration_in_frames == 180
            assert session.evaluate("() => document.querySelectorAll('[data-a2v-scene]').length") == 2
            assert session.evaluate("() => document.documentElement.dataset.a2vTheme") == "light"
            session.seek(50)
            assert session.evaluate("() => document.querySelector('[data-el=value]').textContent") == "73"
            first = session.capture("png")
            session.seek(130)
            session.seek(50)
            assert session.capture("png") == first


def test_short_export_uses_article_output(chromium_ready, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = ROOT / "outputs/examples/declarative-number/previews/silent.mp4"
    assert cli.main_render(["--storyboard", str(SOURCE), "--limit-frames", "3", "--preset", "ultrafast"]) == 0
    assert target.is_file()


def test_render_rejects_unknown_component_before_browser(tmp_path, caplog):
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    data["scenes"][0]["data"]["figure"]["kind"] = "from-internet"
    source = tmp_path / "storyboard.json"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert cli.main_render(["--storyboard", str(source), "--out", str(tmp_path / "out.mp4")]) == 2
    assert "scenes[0].data.figure.kind" in caplog.text
    assert not (tmp_path / "out.mp4").exists()
