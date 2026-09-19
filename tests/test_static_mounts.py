"""静态服务器的挂载：内容根在仓库之外时，共享资产靠别名取到。

别名（`/__a2v__/`）是「内容根可以放在任何地方」的前提：页面在内容根里、
共享资产在仓库里，两者不在一棵树，只能由服务器按声明的前缀把请求接过去。
因此这里守三件事：**命中的取得到、没声明的不放行、越界的必须挡住**。

越界那一侧尤其要紧：别名一旦能被 `..` 穿透，等于把仓库目录挂到了页面上，
而这条路径是渲染时自动开启的。
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

import pytest

from a2v.errors import A2VError
from a2v.static_server import LocalServer

MOUNT = "/__a2v__"


def _fixture_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """内容根（页面与分镜）与仓库侧资产目录，互不同树。"""
    content = tmp_path / "content"
    page_dir = content / "videos" / "demo"
    page_dir.mkdir(parents=True)
    (page_dir / "index.html").write_text("<html>内容根里的页面</html>", encoding="utf-8")
    (page_dir / "storyboard.json").write_text("{}", encoding="utf-8")

    repo = tmp_path / "repo"
    assets = repo / "assets"
    (assets / "nested").mkdir(parents=True)
    (assets / "base.css").write_text(":root{--a:1}", encoding="utf-8")
    (assets / "nested" / "deep.js").write_text("var a = 1;", encoding="utf-8")
    # 挂在资产目录之外：别名不得穿到这里
    (repo / "secret.txt").write_text("不该被读到", encoding="utf-8")
    return content, assets


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, ""


class TestMountResolvesInsideTheMountedDirectory:
    def test_serves_a_mounted_asset(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            status, body = _get(f"{server.base_url}{MOUNT}/base.css")
        assert status == 200
        assert body == ":root{--a:1}"

    def test_serves_nested_paths(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            status, body = _get(f"{server.base_url}{MOUNT}/nested/deep.js")
        assert status == 200
        assert body == "var a = 1;"

    def test_static_root_still_serves_the_page_and_its_storyboard(self, tmp_path):
        """挂载不能挤掉静态根：页面与同目录的分镜仍按相对路径取。"""
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            page = _get(f"{server.base_url}/videos/demo/index.html")
            storyboard = _get(f"{server.base_url}/videos/demo/storyboard.json")
        assert page[0] == 200 and "内容根里的页面" in page[1]
        assert storyboard == (200, "{}")


class TestMountDoesNotWidenTheStaticRoot:
    def test_unknown_prefix_is_not_mapped(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            status, body = _get(f"{server.base_url}/assets/base.css")
        assert status == 404, "没有声明的别名不该映射到任何目录"
        assert body == ""

    def test_traversal_out_of_the_mount_is_refused(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            for attempt in (f"{MOUNT}/../secret.txt", f"{MOUNT}/%2e%2e/secret.txt"):
                status, body = _get(f"{server.base_url}{attempt}")
                assert status == 404, attempt
                assert "不该被读到" not in body

    def test_assets_directory_itself_is_not_listed(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            status, _ = _get(f"{server.base_url}{MOUNT}/")
        assert status == 404, "别名目录不提供目录列表"

    def test_missing_mount_directory_fails_loudly(self, tmp_path):
        """挂载目录不存在时当场报错，而不是让资产安静地 404。"""
        content, _ = _fixture_dirs(tmp_path)
        with pytest.raises(NotADirectoryError):
            LocalServer(content, mounts={MOUNT: tmp_path / "absent"})

    def test_prefix_must_be_absolute(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        with pytest.raises(ValueError):
            LocalServer(content, mounts={"__a2v__": assets})


class TestUrlFor:
    def test_url_for_a_file_inside_the_static_root(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            url = server.url_for(content / "videos" / "demo" / "index.html")
        assert url.endswith("/videos/demo/index.html")
        assert MOUNT not in url

    def test_url_for_a_file_inside_a_mount(self, tmp_path):
        """共享页面在仓库里、静态根在内容根里：页面只能通过别名起 URL。"""
        content, assets = _fixture_dirs(tmp_path)
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            url = server.url_for(assets / "base.css")
        assert url.endswith(f"{MOUNT}/base.css")

    def test_url_for_an_unreachable_file_raises(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        outside = tmp_path / "elsewhere.html"
        outside.write_text("<html></html>", encoding="utf-8")
        with LocalServer(content, mounts={MOUNT: assets}) as server:
            with pytest.raises(A2VError, match="既不在静态根"):
                server.url_for(outside)

    def test_url_for_before_start_raises(self, tmp_path):
        content, assets = _fixture_dirs(tmp_path)
        server = LocalServer(content, mounts={MOUNT: assets})
        with pytest.raises(RuntimeError):
            server.url_for(content / "videos" / "demo" / "index.html")
