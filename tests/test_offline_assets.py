"""资产自足性与预设校验。

分四层：
- 静态层：资产层里不许出现外部 URL，且每处 `url()` 都要指到仓库内真实文件；
- 真实层：限帧导出必须跑得通（资产缺失会在这里暴露）；
- 断网层：拦掉浏览器发出的每一个非本地请求，页面仍要渲染，且两套 webfont
  的 `FontFace.status` 都是 `loaded`（字体静默回退成系统字体在成片里几乎看不出来，
  但会改变字宽与换行）；
- 契约层：分镜的 `visual.preset` 可选，但写了就必须是登记过的预设。

如果哪一天有人把字体或样式改回 CDN，这里会立刻失败，
而不是等到某次离线渲染才发现画面回退成系统字体。
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".agents" / "skills" / "article2video" / "assets"
STORYBOARD = ROOT / "examples" / "keynote-baseline" / "storyboard.json"
RENDER = ROOT / ".agents" / "skills" / "article2video" / "scripts" / "render.py"

sys.path.insert(0, str(ROOT / ".agents" / "skills" / "article2video" / "scripts"))

from a2v import storyboard as sb  # noqa: E402  （路径先于导入，见上）

#: 允许被注释记录、但不允许真正被引用的外部 URL
_URL_IN_USE = re.compile(
    r"""(?:url\(\s*|src\s*=\s*|href\s*=\s*|@import\s+)['"]?(https?://[^'")\s]+)"""
)

#: `url(...)` 里允许出现的写法：相对路径。`#` 开头是 SVG 的片段引用
_URL_LOCAL = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""")


def _asset_files() -> list[pathlib.Path]:
    return [
        path
        for path in sorted(ASSETS.rglob("*"))
        if path.is_file() and path.suffix in (".css", ".js", ".html")
    ]


def _external_references() -> list[str]:
    offenders: list[str] = []
    for path in _asset_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _URL_IN_USE.finditer(text):
            offenders.append(f"{path.relative_to(ROOT)}: {match.group(1)}")
    return offenders


class TestStaticAssets:
    def test_no_external_references(self) -> None:
        offenders = _external_references()
        assert not offenders, f"资产层引用了外部资源，离线渲染会回退：{offenders}"

    def test_every_url_resolves_inside_the_repo(self) -> None:
        """每一处 url() 都要指到仓库里真实存在的文件。

        指向 CDN 会断网回退，指向拼错的本地路径则会静默不生效——
        两种都只有看成片才会发现，所以在这里一次性拦住。
        """
        missing: list[str] = []
        for path in _asset_files():
            if path.suffix == ".js":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for raw in _URL_LOCAL.findall(text):
                target = raw.split("?")[0].split("#")[0].strip()
                if not target or target.startswith(("data:", "http://", "https://")):
                    continue
                if target.startswith("#"):
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.is_file():
                    missing.append(f"{path.relative_to(ROOT)} -> {target}")
        assert not missing, f"url() 指向了不存在的文件：{missing}"

    def test_font_files_are_vendored(self) -> None:
        for name in ("Inter-Variable.ttf", "NotoSansSC-Variable.ttf"):
            size = (ASSETS / "fonts" / name).stat().st_size
            assert size > 100_000, f"{name} 只有 {size} 字节，可能是个占位文件"

    def test_licenses_shipped(self) -> None:
        for name in ("OFL-Inter.txt", "OFL-NotoSansSC.txt"):
            text = (ASSETS / "fonts" / name).read_text(encoding="utf-8", errors="replace")
            assert "SIL OPEN FONT LICENSE" in text.upper()

    def test_font_face_points_at_vendored_files(self) -> None:
        css = (ASSETS / "keynote.css").read_text(encoding="utf-8")
        for name in ("Inter-Variable.ttf", "NotoSansSC-Variable.ttf"):
            assert f"fonts/{name}" in css, f"@font-face 没有引用 {name}"


class TestPresetValidation:
    """分镜里的 `visual.preset`：可选，但写了就必须是登记过的预设。"""

    def _storyboard(self) -> dict:
        return json.loads(STORYBOARD.read_text(encoding="utf-8"))

    def test_keynote_preset_is_accepted(self) -> None:
        report = sb.validate(self._storyboard(), declarative=True)
        assert report.ok, report.errors

    def test_unknown_preset_is_rejected_with_path(self) -> None:
        data = self._storyboard()
        data["visual"]["preset"] = "keynote-x"
        report = sb.validate(data, declarative=True)
        assert report.errors, "未知预设必须报错，否则会安静地按默认主题渲染"
        assert any("visual.preset" in issue.path for issue in report.errors), report.errors

    def test_preset_is_optional(self) -> None:
        data = self._storyboard()
        del data["visual"]["preset"]
        report = sb.validate(data, declarative=True)
        assert report.ok, report.errors

    def test_visual_may_be_absent_entirely(self) -> None:
        data = self._storyboard()
        del data["visual"]
        report = sb.validate(data, declarative=True)
        assert report.ok, report.errors


@pytest.mark.slow
class TestOfflineRender:
    def test_render_succeeds_with_local_assets_only(self, tmp_path: pathlib.Path) -> None:
        """限帧导出一次，并确认它只请求了本地资产。

        这里的网络断言是**静态**的：资产层不许出现外部 URL，且每一处
        `url()` 指向的文件必须真的在仓库里。之所以不在进程里猴补丁 socket，
        是因为 Chromium 走的是自己的网络栈与 Python 的 socket 模块无关，
        那样写出来的「断网」是拦不住浏览器的，只会给人虚假的安全感。
        """
        result = subprocess.run(
            [
                sys.executable,
                str(RENDER),
                "--storyboard",
                str(STORYBOARD),
                "--limit-frames",
                "2",
                "--capture-format",
                "png",
                "--out",
                str(tmp_path / "offline.mp4"),
                "--no-probe",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        assert result.returncode == 0, f"限帧导出失败：{result.stdout}\n{result.stderr}"
        assert (tmp_path / "offline.mp4").stat().st_size > 0

    def test_page_loads_with_every_non_local_request_blocked(self) -> None:
        """真正的断网检查：拦掉浏览器发出的**每一个非本地请求**，页面仍要正常渲染。

        静态扫 URL 只能证明「资产层里没有外链」，证明不了「浏览器真的只用本地
        资产」。这里在 Playwright 层拦截请求：凡是 `127.0.0.1` 之外的一律
        `abort`，然后要求

        1. 没有任何请求被拦下（有的话说明真的有东西在往外要）；
        2. 两套 webfont 的 `FontFace.status` 都是 `loaded`——
           字体回退成系统字体在成片里几乎看不出来，但会悄悄改变字宽与换行；
        3. 字体文件确实是从本地路径取回的。
        """
        playwright = pytest.importorskip("playwright.sync_api")
        import functools
        import http.server
        import socketserver
        import threading
        from urllib.parse import quote

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):  # noqa: D102 - 测试里不需要访问日志
                pass

        with socketserver.ThreadingTCPServer(
            ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
        ) as httpd:
            httpd.daemon_threads = True
            port = httpd.server_address[1]
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            try:
                allowed = f"http://127.0.0.1:{port}/"
                page_url = (
                    f"{allowed}{ASSETS.relative_to(ROOT).as_posix()}/declarative.html"
                    f"?a2v-storyboard={quote('/' + STORYBOARD.relative_to(ROOT).as_posix(), safe='')}"
                )
                with playwright.sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(viewport={"width": 1080, "height": 1920})
                    blocked: list[str] = []
                    requested: list[str] = []

                    def _guard(route, request):
                        url = request.url
                        requested.append(url)
                        if url.startswith(allowed) or url.startswith("data:"):
                            route.continue_()
                        else:
                            blocked.append(url)
                            route.abort()

                    page.route("**/*", _guard)
                    page.goto(page_url)
                    page.wait_for_function(
                        "() => document.querySelectorAll('[data-a2v-scene]').length > 0",
                        timeout=20000,
                    )
                    page.evaluate("() => document.fonts.ready")
                    facts = page.evaluate(
                        """() => {
                          const faces = [];
                          document.fonts.forEach((f) => faces.push({
                            family: f.family, status: f.status, weight: f.weight
                          }));
                          const el = document.querySelector('[data-a2v-preset] [data-a2v-stage]')
                                  || document.querySelector('[data-a2v-stage]');
                          return { faces, stack: getComputedStyle(el).fontFamily };
                        }"""
                    )
                    browser.close()
                    assert not blocked, f"有请求被拦下，说明页面在依赖外部资源：{blocked}"

                    webfonts = {f["family"]: f["status"] for f in facts["faces"]}
                    assert webfonts, "页面没有注册任何 @font-face，字体大概没被引用"
                    for family in ("A2V Inter", "A2V Sans"):
                        assert webfonts.get(family) == "loaded", (
                            f"{family} 未加载（status={webfonts.get(family)}），"
                            "画面会静默回退成系统字体"
                        )
                    assert "A2V Inter" in facts["stack"], facts["stack"]
                    fonts = [url for url in requested if url.endswith(".ttf")]
                    assert len(fonts) >= 2, f"没有从本地取回字体文件：{requested}"
            finally:
                httpd.shutdown()
