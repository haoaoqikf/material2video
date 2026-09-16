"""Playwright 浏览器会话封装。

职责只有一件事：打开动画网页，等待它就绪，然后按帧号驱动画面并截取图片。
所有与「确定性渲染契约」相关的检查（__A2V__ 接口存在、字段类型正确）都在
这里落地。

资源生命周期：Playwright 驱动进程与事件循环由本模块负责启动与关闭。
``sync_playwright()`` 的驱动循环会一直运行到 ``stop()`` 被调用为止，
即使浏览器已关闭也不会自行退出；漏掉 stop 会让同进程内的后续渲染失败。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Browser, Error as PlaywrightError
from playwright.sync_api import Page, Playwright, sync_playwright

from .errors import A2VError

logger = logging.getLogger(__name__)


class BrowserError(A2VError):
    """页面加载或契约检查失败。"""


@dataclass
class PageContract:
    """从网页读取到的 __A2V__ 契约字段。"""

    fps: int
    duration_in_frames: int
    width: int
    height: int


class AnimatedPage:
    """一个已就绪的动画网页。上下文管理器负责释放浏览器资源。"""

    def __init__(
        self,
        page: Page,
        contract: PageContract,
        browser: Browser,
        playwright: Playwright,
    ) -> None:
        self._page = page
        self._browser = browser
        self._playwright = playwright
        self._closed = False
        self.contract = contract

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

    def evaluate(self, expression: str) -> Any:
        """在页面上下文中求值，供渲染前的布局体检使用。"""
        return self._page.evaluate(expression)

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
) -> AnimatedPage:
    """启动 Chromium 打开动画网页并验证 __A2V__ 契约。

    width/height 显式传入时以渲染脚本的视口为准，避免网页尺寸与脚本
    声明不一致导致画面被裁切或留黑边。
    """
    playwright = sync_playwright().start()
    browser: Browser | None = None
    try:
        browser = playwright.chromium.launch(headless=True)
        viewport = {"width": width, "height": height} if width and height else None
        page = browser.new_page(viewport=viewport, device_scale_factor=1)

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

        # __A2V__ 由网页异步挂载（通常要等分镜 JSON 加载完），
        # load 事件早于它出现，因此必须显式等待而不是立即读取。
        try:
            page.wait_for_function("() => !!window.__A2V__", timeout=timeout_ms)
        except PlaywrightError as exc:
            detail = "\n".join(diagnostics[-5:]) or "页面未输出错误信息"
            raise BrowserError(
                f"{url}: 等待 window.__A2V__ 定义超时。"
                f"请确认网页引入了 timeline.js，且 A2V.mount() 已成功执行。\n{detail}"
            ) from exc

        raw: dict[str, Any] = page.evaluate(
            "() => ({"
            "fps: window.__A2V__.fps, "
            "durationInFrames: window.__A2V__.durationInFrames, "
            "width: window.__A2V__.width, "
            "height: window.__A2V__.height, "
            "ready: typeof window.__A2V__.ready, "
            "seek: typeof window.__A2V__.seekToFrame})"
        )
        _validate_contract(raw, url)
        contract = PageContract(
            fps=raw["fps"],
            duration_in_frames=raw["durationInFrames"],
            width=raw["width"],
            height=raw["height"],
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
        return AnimatedPage(page, contract, browser, playwright)
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


def _validate_contract(raw: dict[str, Any], url: str) -> None:
    """契约字段缺失或类型不对时给出可定位的错误信息。"""
    if raw["ready"] != "function":
        raise BrowserError(f"{url}: window.__A2V__.ready 不是函数")
    if raw["seek"] != "function":
        raise BrowserError(f"{url}: window.__A2V__.seekToFrame 不是函数")
    for key in ("fps", "durationInFrames", "width", "height"):
        value = raw[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise BrowserError(f"{url}: window.__A2V__.{key} 必须是正整数，实际为 {value!r}")
