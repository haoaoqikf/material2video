"""Playwright 浏览器会话封装。

职责只有一件事：打开提供画面的页面，等待它就绪，然后按帧号驱动画面并截取图片。
所有与「确定性渲染契约」相关的检查（`__A2V__` 接口存在、版本正确、字段类型正确）
都在这里落地。

画面有两个提供者，本模块不区分：

* **契约页**（React + Remotion Player）：`web/dist/contract/contract.html`，
  当前版本 3。它按 `a2v-storyboard` 查询参数加载任意作品的分镜；
* 旧动画网页：不再受支持，版本检查会明确拒绝它。

资源生命周期：Playwright 驱动进程与事件循环由本模块负责启动与关闭。
``sync_playwright()`` 的驱动循环会一直运行到 ``stop()`` 被调用为止，
即使浏览器已关闭也不会自行退出；漏掉 stop 会让同进程内的后续渲染失败。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Browser, Error as PlaywrightError, Route
from playwright.sync_api import Page, Playwright, sync_playwright

from a2v.engine.contract_page import CONTRACT_VERSION
from a2v.core.errors import A2VError

logger = logging.getLogger(__name__)


class BrowserError(A2VError):
    """页面加载或契约检查失败。"""


def is_local_url(url: str) -> bool:
    """URL 是否指向本机或非网络资源；与运行期 offline guard 同一口径。

    允许：相对路径、``data:``/``blob:``/``about:``、本机环回（localhost、
    127.0.0.1、::1）。其余一律视为非本地——预览、评审与渲染都必须离线可跑。
    """
    if url.startswith(("data:", "blob:", "about:")):
        return True
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        host = (parsed.hostname or "").lower()
        return host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")
    return parsed.scheme in ("", "file")


@dataclass
class PageContract:
    """从网页读取到的 __A2V__ 契约字段。"""

    fps: int
    duration_in_frames: int
    width: int
    height: int
    version: int = CONTRACT_VERSION


class AnimatedPage:
    """一个已就绪的契约页。上下文管理器负责释放浏览器资源。"""

    def __init__(
        self,
        page: Page,
        contract: PageContract,
        browser: Browser,
        playwright: Playwright,
        violations: list[str] | None = None,
    ) -> None:
        self._page = page
        self._browser = browser
        self._playwright = playwright
        self._closed = False
        self.contract = contract
        #: 运行期隔离违规（被阻断请求、页面异常、控制台 error、未处理 Promise）。
        self.violations = violations if violations is not None else []

    def drain_violations(self) -> list[str]:
        """取走已记录的运行期违规；调用方把它们并入失败而非警告。

        静默跳过等于把「画面在乱来」当成「画面正常」；违规一律计为错误。
        """
        found, self.violations = self.violations, []
        try:
            unhandled = self._page.evaluate("() => window.__A2V_UNHANDLED__ || []")
        except Exception:  # noqa: BLE001 - 页面已关闭时不阻塞清理
            unhandled = []
        for reason in unhandled or []:
            found.append(f"未处理的 Promise: {reason}")
        return found

    def __enter__(self) -> "AnimatedPage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def seek(self, frame: int) -> None:
        """驱动网页渲染到指定帧。

        契约要求 seekToFrame 返回 Promise，Playwright 会自动等待它
        resolve，从而保证截图时画面已完成更新。
        """
        self._page.evaluate("(frame) => window.__A2V__.seekToFrame(frame)", frame)

    def capture(self, image_format: str = "jpeg", quality: int = 98) -> bytes:
        """截取当前画面。

        JPEG 的编码开销显著低于 PNG（1080×1920 实测约 66ms vs 225ms），
        而 q98 对文字画面几乎无可感损失，因此默认使用 JPEG；需要逐像素
        比对时再切换到 PNG。
        """
        if image_format == "png":
            return self._page.screenshot(type="png")
        return self._page.screenshot(type="jpeg", quality=quality)

    def evaluate(self, expression: str, arg: Any = None) -> Any:
        """在页面上下文中求值，供渲染前的布局体检与动效量测使用。"""
        if arg is None:
            return self._page.evaluate(expression)
        return self._page.evaluate(expression, arg)

    def close(self) -> None:
        """按页面 → 浏览器 → 驱动的顺序释放。

        释放发生在 finally 语义下，此时可能已有原始异常在传播，因此这里
        吞掉所有清理错误，只记日志，避免掩盖真正的失败原因。
        """
        if self._closed:
            return
        self._closed = True
        for label, action in (
            ("页面", self._page.context.close),
            ("浏览器", self._browser.close),
            ("Playwright 驱动", self._playwright.stop),
        ):
            try:
                action()
            except Exception as exc:  # noqa: BLE001 - 清理失败不应中断主流程
                logger.warning("关闭%s失败: %s", label, exc)


def open_animated_page(
    url: str,
    timeout_ms: int = 30000,
    width: int | None = None,
    height: int | None = None,
    expected_version: int = CONTRACT_VERSION,
) -> AnimatedPage:
    """启动 Chromium 打开提供画面的页面并验证 __A2V__ 契约。

    width/height 显式传入时以渲染脚本的视口为准，避免网页尺寸与脚本
    声明不一致导致画面被裁切或留黑边。

    `expected_version` 是**这条路径要求的契约版本**。分镜渲染只接受 v3 契约；
    旧页面路径不再绕过版本检查。
    """
    playwright = sync_playwright().start()
    browser: Browser | None = None
    try:
        browser = playwright.chromium.launch(headless=True)
        viewport = {"width": width, "height": height} if width and height else None
        page = browser.new_page(viewport=viewport, device_scale_factor=1)

        # 运行期隔离（任务 3.3）：阻断非本地请求 + 收集失败信号。
        # 四类信号都算违规：被阻断的请求、页面异常、未处理 Promise、控制台 error。
        violations: list[str] = []

        def _on_route(route: Route) -> None:
            url = route.request.url
            if is_local_url(url):
                route.continue_()
                return
            violations.append(f"被阻断的非本地请求: {url}")
            route.abort()

        def _on_page_error(error: Exception) -> None:
            violations.append(f"页面异常: {error}")

        def _on_console(message: Any) -> None:
            if message.type == "error":
                violations.append(f"控制台 error: {message.text}")

        page.route("**/*", _on_route)
        page.on("pageerror", _on_page_error)
        page.on("console", _on_console)
        page.add_init_script(
            "window.addEventListener('unhandledrejection', (event) => {"
            "  window.__A2V_UNHANDLED__ = window.__A2V_UNHANDLED__ || [];"
            "  window.__A2V_UNHANDLED__.push(String(event.reason));"
            "});"
        )

        # 收集页面侧报错，契约未就绪时把它一并抛出，避免只看到「未定义」
        diagnostics: list[str] = []
        page.on("pageerror", lambda error: diagnostics.append(f"页面异常: {error}"))
        page.on(
            "console",
            lambda message: (
                diagnostics.append(f"控制台 {message.type}: {message.text}")
                if message.type == "error"
                else None
            ),
        )

        logger.info("打开页面: %s", url)
        page.goto(url, wait_until="load", timeout=timeout_ms)

        # __A2V__ 由页面异步挂载（通常要等分镜 JSON 加载完），
        # load 事件早于它出现，因此必须显式等待而不是立即读取。
        try:
            page.wait_for_function("() => !!window.__A2V__", timeout=timeout_ms)
        except PlaywrightError as exc:
            detail = "\n".join(diagnostics[-5:]) or "页面未输出错误信息"
            expected = (
                f"__A2V__ version {expected_version} 契约"
                if expected_version is not None
                else "__A2V__ 契约"
            )
            raise BrowserError(
                f"{url}: 等待 window.__A2V__ 定义超时。请确认页面暴露了{expected}。\n{detail}"
            ) from exc

        raw: dict[str, Any] = page.evaluate(
            "() => ({"
            "version: window.__A2V__.version ?? null, "
            "fps: window.__A2V__.fps, "
            "durationInFrames: window.__A2V__.durationInFrames, "
            "width: window.__A2V__.width, "
            "height: window.__A2V__.height, "
            "ready: typeof window.__A2V__.ready, "
            "seek: typeof window.__A2V__.seekToFrame})"
        )
        _validate_contract(raw, url, expected_version)
        contract = PageContract(
            fps=raw["fps"],
            duration_in_frames=raw["durationInFrames"],
            width=raw["width"],
            height=raw["height"],
            version=raw["version"],
        )
        logger.info(
            "契约就绪: %d fps, %d 帧, %dx%d",
            contract.fps,
            contract.duration_in_frames,
            contract.width,
            contract.height,
        )

        # 等待字体与首帧绘制完成；契约要求 ready() 在画面可用后 resolve。
        page.evaluate("() => window.__A2V__.ready()")
        return AnimatedPage(page, contract, browser, playwright, violations)
    except PlaywrightError as exc:
        _teardown(browser, playwright)
        raise BrowserError(f"浏览器加载页面失败: {exc}") from exc
    except Exception:
        _teardown(browser, playwright)
        raise


def _teardown(browser: Browser | None, playwright: Playwright) -> None:
    """失败路径上的资源回收：即使浏览器未启动也要停掉驱动循环。

    同样吞掉清理错误，让调用方拿到原始的失败原因。
    """
    if browser is not None:
        try:
            browser.close()
        except Exception as exc:  # noqa: BLE001 - 清理失败不应掩盖原始错误
            logger.warning("关闭浏览器失败: %s", exc)
    try:
        playwright.stop()
    except Exception as exc:  # noqa: BLE001 - 同上
        logger.warning("停止 Playwright 驱动失败: %s", exc)


def _validate_contract(
    raw: dict[str, Any], url: str, expected_version: int = CONTRACT_VERSION
) -> None:
    """契约字段缺失或类型不对时给出可定位的错误信息。"""
    if raw["ready"] != "function":
        raise BrowserError(f"{url}: window.__A2V__.ready 不是函数")
    if raw["seek"] != "function":
        raise BrowserError(f"{url}: window.__A2V__.seekToFrame 不是函数")

    # 版本先判：两个版本的 `ready` 与 `seekToFrame` 签名相同，差别在语义
    # （version 1 不保证 Player 已挂载），因此版本不符时接下来会在首帧截图上
    # 出现「画面还是空的」这类难以反推的现象。
    version = raw["version"]
    if version is None:
        raise BrowserError(
            f"{url}: window.__A2V__ 缺少 version 字段。"
            f"本渲染入口的契约版本是 {CONTRACT_VERSION}。"
        )
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise BrowserError(f"{url}: window.__A2V__.version 必须是正整数，实际为 {version!r}")
    if version != expected_version:
        raise BrowserError(
            f"{url}: 渲染契约版本为 {version}，这条渲染路径要求的是 {expected_version}"
        )

    for key in ("fps", "durationInFrames", "width", "height"):
        value = raw[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise BrowserError(f"{url}: window.__A2V__.{key} 必须是正整数，实际为 {value!r}")
