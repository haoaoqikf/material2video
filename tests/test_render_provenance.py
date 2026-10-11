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
import os
from pathlib import Path

import pytest

import m2v.types.article.render as render_mod


def _digest(path: Path) -> str:
    import m2v.types.article.media as media_mod

    return media_mod.file_digest(path)


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
    import m2v.types.article.media as media_mod

    html = page.read_text(encoding="utf-8")
    workspace = tmp_path
    payload = {
        "version": 3,
        "workspace": os.path.relpath(workspace, video.parent).replace(os.sep, "/"),
        "page": page.relative_to(workspace).as_posix(),
        "storyboard": "",
        "frames": 12,
        "fps": 30,
        "captureFormat": "jpeg",
        "assets": media_mod.asset_fingerprint(page, html, extra, workspace_root=workspace),
    }
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"fake mp4")
    video.with_suffix(".provenance.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return payload


class TestProvenanceAcrossRoots:
    """文章与产物在仓库之外时，溯源仍要能判定。

    v3 用相对引用定位（产物目录 → 工作区根 + 工作区根相对路径），因此不要求
    产物上级有仓库标记；共享资产经 `/__m2v__/` 引用时记别名键，不因为它在
    另一个根里就被漏掉——漏掉的话，改了组件库而没重渲的成片会显示「对得上」。
    """

    @staticmethod
    def _workspace(tmp_path: Path) -> tuple[Path, Path]:
        content = tmp_path / "content"
        page = content / "videos" / "demo" / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text(
            '<!doctype html><html><head>'
            '<link rel="stylesheet" href="/__m2v__/figures.css"></head></html>',
            encoding="utf-8",
        )
        return content, page

    @staticmethod
    def _render(tmp_path: Path, content: Path, page: Path) -> Path:
        import m2v.types.article.media as media_mod

        video = content / "videos" / "demo" / "outputs" / "silent.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"fake mp4")
        payload = {
            "version": 3,
            "workspace": os.path.relpath(content, video.parent).replace(os.sep, "/"),
            "page": "videos/demo/index.html",
            "storyboard": "",
            "frames": 12,
            "fps": 30,
            "captureFormat": "jpeg",
            "assets": media_mod.asset_fingerprint(
                page, page.read_text(encoding="utf-8"), workspace_root=content
            ),
        }
        video.with_suffix(".provenance.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return video

    @pytest.fixture
    def mounted_assets(self, tmp_path, monkeypatch) -> Path:
        """把 `/__m2v__/` 指到测试自己的资产目录，模拟仓库那一侧。"""
        import m2v.core.assets as assets_mod

        fake = tmp_path / "skill-assets"
        fake.mkdir()
        (fake / "figures.css").write_text(".fig{opacity:1}", encoding="utf-8")
        monkeypatch.setattr(
            assets_mod, "default_mounts", lambda: {assets_mod.SKILL_MOUNT: fake}
        )
        return fake

    def test_external_workspace_round_trip(self, tmp_path, mounted_assets):
        content, page = self._workspace(tmp_path)
        video = self._render(tmp_path, content, page)
        payload = json.loads(video.with_suffix(".provenance.json").read_text(encoding="utf-8"))
        assert payload["workspace"] == "../../.."
        assert payload["page"] == "videos/demo/index.html"
        assert sorted(payload["assets"]["files"]) == ["__m2v__/figures.css", "videos/demo/index.html"]
        assert render_mod.provenance_status(video)["status"] == "current"

    def test_shared_asset_change_names_the_alias_key(self, tmp_path, mounted_assets):
        content, page = self._workspace(tmp_path)
        video = self._render(tmp_path, content, page)
        (mounted_assets / "figures.css").write_text(".fig{opacity:.5}", encoding="utf-8")
        result = render_mod.provenance_status(video)
        assert result["status"] == "stale"
        assert result["changed"] == ["__m2v__/figures.css"]

    def test_removed_shared_asset_is_reported_as_missing(self, tmp_path, mounted_assets):
        content, page = self._workspace(tmp_path)
        video = self._render(tmp_path, content, page)
        (mounted_assets / "figures.css").unlink()
        result = render_mod.provenance_status(video)
        assert result["status"] == "stale"
        assert result["missing"] == ["__m2v__/figures.css"]

    def test_alias_key_cannot_point_outside_the_mount(self, tmp_path, mounted_assets):
        """被人改过的溯源键不得让判定去读挂载目录之外的文件。"""
        content, page = self._workspace(tmp_path)
        video = self._render(tmp_path, content, page)
        sidecar = video.with_suffix(".provenance.json")
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        (tmp_path / "outside.css").write_text(".a{opacity:1}", encoding="utf-8")
        payload["assets"]["files"]["__m2v__/../outside.css"] = _digest(
            tmp_path / "outside.css"
        )
        sidecar.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result = render_mod.provenance_status(video)
        assert result["status"] == "stale"
        assert result["missing"] == ["__m2v__/../outside.css"]

    def test_missing_workspace_reference_is_unknown_not_guessed(self, tmp_path, mounted_assets):
        content, page = self._workspace(tmp_path)
        video = self._render(tmp_path, content, page)
        sidecar = video.with_suffix(".provenance.json")
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        payload.pop("workspace")
        sidecar.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result = render_mod.provenance_status(video)
        assert result["status"] == "unknown"
        assert "工作区引用" in result["detail"]


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


class TestLineEndingsDoNotFakeStaleness:
    """git 的换行归一化会在工作区静默翻转行尾：只差行尾不得判落后。"""

    def test_crlf_round_trip_stays_current(self, tmp_path):
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        theme = tmp_path / "assets" / "theme.css"
        theme.write_bytes(theme.read_bytes().replace(b"\n", b"\r\n"))
        result = render_mod.provenance_status(video)
        assert result["status"] == "current", result["detail"]

    def test_binary_assets_are_hashed_raw(self, tmp_path):
        """字体、图片不归一化：二进制里出现 0x0D0A 也不能被改写。"""
        import m2v.types.article.media as media_mod

        blob = tmp_path / "assets" / "font.ttf"
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(b"\x00\r\n\x01")
        assert media_mod.file_digest(blob) == __import__("hashlib").sha256(b"\x00\r\n\x01").hexdigest()

    def test_old_version_sidecar_is_unknown_not_stale(self, tmp_path):
        """旧口径写的溯源不能判成落后——那是格式变了，不是资产变了。"""
        page = _work(tmp_path)
        video = tmp_path / "outputs" / "demo" / "silent.mp4"
        _provenance(tmp_path, page, video)
        sidecar = video.with_suffix(".provenance.json")
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        data["version"] = 2  # 上一版口径：没有 workspace 字段，页面按仓库标记定位
        data.pop("workspace", None)
        sidecar.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        result = render_mod.provenance_status(video)
        assert result["status"] == "unknown"
        assert "旧格式" in result["detail"]


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
