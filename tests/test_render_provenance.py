"""成片的陈旧判定：这个成片是不是旧资产渲的。

要守住的三件事，缺一条这个闸门就不可信：

  * **改了被引用的资产必须报出来**，并指出是哪个文件——否则它救不了第 8 轮
    那种「旧弹跳静默躺在 outputs 里」的情况；
  * **没变的不能乱报**（改一个没被引用的文件不得触发落后）——闸门一旦开始
    报无意义的落后，人就会开始忽略它，等于没有闸门；
  * **没有溯源要如实说「无法判断」**：不默认放行（安静通过和真的通过长得一样），
    也不判失败（成片可能只是别人给的）。
"""

from __future__ import annotations

import json
from pathlib import Path

from a2v import render as render_mod


def _work(tmp_path: Path) -> Path:
    """一个最小工程：网页 + 一个被引用资产 + 一个成片与它的溯源。"""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    page = tmp_path / "videos" / "demo" / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text('<link rel="stylesheet" href="../../assets/theme.css">', encoding="utf-8")
    theme = tmp_path / "assets" / "theme.css"
    theme.parent.mkdir(parents=True, exist_ok=True)
    theme.write_text(":root{--a:1}", encoding="utf-8")
    return page


def _provenance(tmp_path: Path, page: Path, video: Path, extra: dict | None = None) -> dict:
    from a2v import media as media_mod

    html = page.read_text(encoding="utf-8")
    payload = {
        "version": 1,
        "page": page.relative_to(tmp_path).as_posix(),
        "storyboard": "",
        "frames": 12,
        "fps": 30,
        "captureFormat": "jpeg",
        "assets": media_mod.asset_fingerprint(page, html, extra),
    }
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"fake mp4")
    video.with_suffix(".provenance.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return payload


class TestStalenessVerdicts:
    def test_fresh_render_is_current(self, tmp_path):
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        result = render_mod.provenance_status(video)
        assert result["status"] == "current", result["detail"]

    def test_referenced_asset_change_is_reported_with_the_file(self, tmp_path):
        """第 8 轮那个场景：动效资产改过而没重渲，必须报出来并指名。"""
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        (tmp_path / "assets" / "theme.css").write_text(":root{--a:2}", encoding="utf-8")
        result = render_mod.provenance_status(video)
        assert result["status"] == "stale"
        assert result["changed"] == ["assets/theme.css"]
        assert "assets/theme.css" in result["detail"]

    def test_newly_referenced_asset_makes_it_stale(self, tmp_path):
        """新增一个 script 标签也算变：那时渲的片子没有它。"""
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        (tmp_path / "assets" / "motion.js").write_text("var a = 1;", encoding="utf-8")
        page.write_text(
            '<link rel="stylesheet" href="../../assets/theme.css">'
            '<script src="../../assets/motion.js"></script>',
            encoding="utf-8",
        )
        result = render_mod.provenance_status(video)
        assert result["status"] == "stale"
        assert result["changed"] == ["assets/motion.js"] or "assets/motion.js" in result["detail"]

    def test_unreferenced_change_stays_current(self, tmp_path):
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        unused = tmp_path / "assets" / "unused.js"
        unused.write_text("var unused = 1;", encoding="utf-8")
        assert render_mod.provenance_status(video)["status"] == "current"

    def test_missing_referenced_file_is_stale(self, tmp_path):
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        (tmp_path / "assets" / "theme.css").unlink()
        result = render_mod.provenance_status(video)
        assert result["status"] == "stale"
        assert result["missing"] == ["assets/theme.css"]

    def test_non_file_entries_are_not_failures(self, tmp_path):
        """媒体清单指纹不是文件，复核不了就得说复核不了，不能算落后。"""
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "voiced.mp4"
        _provenance(tmp_path, page, video, {"media.sourceFingerprint": "abc123"})
        result = render_mod.provenance_status(video)
        assert result["status"] == "current"
        assert result["unverifiable"] == ["media.sourceFingerprint"]
        assert "无法复核" in result["detail"]


class TestUnknownIsNotAPass:
    def test_missing_provenance_is_unknown(self, tmp_path):
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"fake mp4")
        result = render_mod.provenance_status(video)
        assert result["status"] == "unknown", "没有溯源不得默认放行"
        assert "无法判断" in result["detail"]

    def test_unreadable_provenance_is_unknown(self, tmp_path):
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"fake mp4")
        video.with_suffix(".provenance.json").write_text("{ 不是 JSON", encoding="utf-8")
        assert render_mod.provenance_status(video)["status"] == "unknown"

    def test_page_gone_is_unknown(self, tmp_path):
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        page.unlink()
        result = render_mod.provenance_status(video)
        assert result["status"] == "unknown"
        assert "找不到了" in result["detail"]

    def test_unknown_is_neither_current_nor_stale(self, tmp_path):
        """三种结论互斥：unknown 不得被调用方当成通过。"""
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"fake mp4")
        assert render_mod.provenance_status(video)["status"] not in {"current", "stale"}
