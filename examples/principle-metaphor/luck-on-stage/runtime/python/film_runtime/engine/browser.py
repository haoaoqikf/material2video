"""采集和合成使用本工程Playwright版本恢复的浏览器，禁止导出时隐式下载。"""
from __future__ import annotations

import os
from pathlib import Path

from ..core.errors import VideoError


def configure() -> Path:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)
    if not executable.is_file():
        raise VideoError('缺少本作品匹配的Chromium；运行 pnpm run setup --install-browser 后重试')
    os.environ['VIDEO_BROWSER_EXECUTABLE'] = str(executable)
    return executable
