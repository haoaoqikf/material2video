"""成片溯源的资产指纹。

只覆盖不依赖浏览器的那一半：指纹口径本身。渲染成功后落溯源、
以及「这个成片是不是旧资产渲的」的判定，接在 `render.py` 与验收流程上，
由 OpenSpec 变更 `render-provenance` 落地。

这一层要守住的三件事：

  * **口径一致**：与媒体清单用同一个 `fingerprint`（规范化 JSON 的 sha256），
    否则会出现「清单说一致、成片说落后」这种没人能判断该信哪个的状态；
  * **只指纹被引用的文件**：改一个用不到的图形不得触发「落后」——
    闸门一旦开始报无意义的落后，人就会开始忽略它；
  * **产物里不写绝对路径**：溯源文件跟着成片走，机器换了也应当能读懂。
"""

from __future__ import annotations

from pathlib import Path

from a2v import media as media_mod


def _page(tmp_path: Path, html: str = "") -> Path:
    page = tmp_path / "videos" / "demo" / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html or "<html></html>", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return page


def _asset(tmp_path: Path, relative: str, text: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestFingerprintCoversTheRightFiles:
    def test_page_itself_is_always_included(self, tmp_path):
        page = _page(tmp_path, "<html>甲</html>")
        result = media_mod.asset_fingerprint(page, page.read_text(encoding="utf-8"))
        assert [key for key in result["files"]] == ["videos/demo/index.html"]
        assert result["digest"]

    def test_referenced_local_assets_are_included(self, tmp_path):
        _asset(tmp_path, "assets/theme.css", ":root{--a:1}")
        _asset(tmp_path, "assets/timeline.js", "var a = 1;")
        html = (
            '<link rel="stylesheet" href="../../assets/theme.css">'
            '<script src="../../assets/timeline.js"></script>'
        )
        page = _page(tmp_path, html)
        keys = sorted(media_mod.asset_fingerprint(page, html)["files"])
        assert keys == ["assets/theme.css", "assets/timeline.js", "videos/demo/index.html"]

    def test_unreferenced_files_stay_out(self, tmp_path):
        """未被引用的文件不进指纹——否则改它会让所有成片报落后。"""
        _asset(tmp_path, "assets/theme.css", ":root{--a:1}")
        _asset(tmp_path, "assets/unused-figure.js", "var unused = 1;")
        html = '<link rel="stylesheet" href="../../assets/theme.css">'
        page = _page(tmp_path, html)
        keys = media_mod.asset_fingerprint(page, html)["files"]
        assert "assets/unused-figure.js" not in keys

    def test_remote_references_are_ignored(self, tmp_path):
        html = '<script src="https://cdn.example.com/lib.js"></script>'
        page = _page(tmp_path, html)
        assert list(media_mod.asset_fingerprint(page, html)["files"]) == ["videos/demo/index.html"]

    def test_extra_entries_are_merged_in(self, tmp_path):
        """有声导出的媒体清单指纹走 extra，不另开字段。"""
        page = _page(tmp_path)
        result = media_mod.asset_fingerprint(
            page, "", {"media.json": "abc", "storyboard.json": "def"}
        )
        assert result["files"]["media.json"] == "abc"
        assert result["files"]["storyboard.json"] == "def"

    def test_no_absolute_paths_leak_into_the_payload(self, tmp_path):
        page = _page(tmp_path)
        payload = str(media_mod.asset_fingerprint(page, page.read_text(encoding="utf-8")))
        assert str(tmp_path) not in payload


class TestFingerprintChangesWithContent:
    def test_content_change_moves_the_digest(self, tmp_path):
        _asset(tmp_path, "assets/theme.css", ":root{--a:1}")
        html = '<link rel="stylesheet" href="../../assets/theme.css">'
        page = _page(tmp_path, html)
        before = media_mod.asset_fingerprint(page, html)["digest"]
        _asset(tmp_path, "assets/theme.css", ":root{--a:2}")
        after = media_mod.asset_fingerprint(page, html)["digest"]
        assert before != after, "改了被引用的资产，指纹必须变——否则陈旧判定永远发现不了"

    def test_one_byte_change_is_enough(self, tmp_path):
        target = _asset(tmp_path, "assets/theme.css", ":root{--a:1}")
        page = _page(tmp_path, '<link rel="stylesheet" href="../../assets/theme.css">')
        before = media_mod.asset_fingerprint(page, page.read_text(encoding="utf-8"))["digest"]
        target.write_text(":root{--a:3}", encoding="utf-8")  # 只改一个字节
        after = media_mod.asset_fingerprint(page, page.read_text(encoding="utf-8"))["digest"]
        assert before != after

    def test_unreferenced_change_does_not_move_the_digest(self, tmp_path):
        """这是噪音那一侧的反例：未被引用的文件变了，成片不该被判为落后。"""
        _asset(tmp_path, "assets/theme.css", ":root{--a:1}")
        unused = _asset(tmp_path, "assets/unused.js", "var unused = 1;")
        html = '<link rel="stylesheet" href="../../assets/theme.css">'
        page = _page(tmp_path, html)
        before = media_mod.asset_fingerprint(page, html)["digest"]
        unused.write_text("var unused = 2;", encoding="utf-8")
        after = media_mod.asset_fingerprint(page, html)["digest"]
        assert before == after

    def test_digest_is_stable_across_calls(self, tmp_path):
        page = _page(tmp_path)
        first = media_mod.asset_fingerprint(page, "")["digest"]
        second = media_mod.asset_fingerprint(page, "")["digest"]
        assert first == second

    def test_digest_uses_the_media_manifest_canonical_form(self, tmp_path):
        """口径一致：同一份 files 交给 fingerprint 必须得到同一个 digest。"""
        page = _page(tmp_path)
        result = media_mod.asset_fingerprint(page, "")
        assert result["digest"] == media_mod.fingerprint(result["files"])
