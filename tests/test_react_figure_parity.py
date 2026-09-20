"""新旧两条渲染路径的**画面等价性**：同一个分镜、同一个帧号，抽帧比 PSNR。

这一份是组件迁移的判据。迁移不是「看起来差不多」：几何、字体、描边、强调色、
底纹层次里任何一处差一点，在成片里都会变成可见的差异，而所有静态检查照常通过。
因此这里把两条路径的同一帧截图逐像素比对，阈值沿用既有的确定性判据
（PSNR ≥ 60 dB，见 `a2v/determinism.py`）。

- 旧路径：共享页面 `assets/declarative.html`（skill bundle 里的受控组件库）；
- 新路径：契约页（`web/dist/contract/contract.html`，挂 `@remotion/player`）。

两个页面都加上 `a2v-rendering` 类：那是渲染脚本会做的事（取消预览缩放、
隐藏预览控件），不加就是拿预览态和渲染态比，白差一堆像素。

会话策略：本模块**只用函数级会话**，两个页面先后各开一次。Playwright 的同步 API
不许一个进程里同时存在两个会话，因此这里不能和持有模块级会话的模块混在一起跑。
"""

from __future__ import annotations

import pathlib
from urllib.parse import urlencode

import pytest

from a2v import browser, contract_page, determinism, paths, render

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".agents" / "skills" / "article2video" / "assets"

#: 判据：确定性判定用的就是这条线，跨实现等价沿用同一个数
PSNR_THRESHOLD = 60.0

#: 分镜：示例 → 要对照的帧号。帧号取自各幕的**中后段**（入场已收敛、
#: 常驻微动仍在），既不落在入场中途（那里的差异会被判定成动效差异而不是几何差异），
#: 也不取第 0 帧（`ready()` 承诺首帧可用，但入场刚起步，画面信息量最低）。
#:
#: **为什么没有 `examples/why-effort-fails`**：那一路的旧渲染用的是它**自己写的页面**
#: （`examples/why-effort-fails/index.html`：自定义 `:root` 令牌、`.stage-bg` 层叠、
#: 每幕的挂载样式），而新路径的画面**只由分镜与受控组件决定**，没有「页面自带 CSS」
#: 这个出口。两者不是同一个输入，逐像素比对没有意义。它的页面改写是后续阶段的事
#: （把页面里的令牌与版式收进分镜的 `visual` 与组件参数），改完再把它加回这里。
CASES: dict[str, tuple[int, ...]] = {
    "examples/declarative-number/storyboard.json": (60, 120, 150, 200, 250, 320),
    "examples/keynote-baseline/storyboard.json": (30, 120, 300, 500, 760, 1100, 1500, 1900),
}


def _skip_if_unbuilt() -> None:
    page = contract_page.contract_page_path()
    if not page.is_file():
        pytest.skip(f"契约页尚未构建：{page}（先执行 cd web && pnpm install && pnpm build）")


def _legacy_url(storyboard: pathlib.Path) -> tuple[str, object]:
    """旧路径的页面 URL 与它需要的静态服务器上下文。

    页面在 skill bundle 里、分镜在工作区根下，两者靠静态服务器的别名接起来，
    因此必须把上下文管理器交回调用方，在整个截图期间保持打开。
    """
    article = paths.for_storyboard(storyboard)
    manager = render._resolve_page_url(
        ASSETS / "declarative.html", article.workspace_root
    )
    base = manager.__enter__()
    url = base + "?" + urlencode(
        {"a2v-storyboard": contract_page.storyboard_url(storyboard, article.workspace_root)}
    )
    return url, manager


def _shots(url: str, frames: tuple[int, ...]) -> dict[int, bytes]:
    with browser.open_animated_page(url, width=1080, height=1920) as page:
        page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
        shots: dict[int, bytes] = {}
        for frame in frames:
            page.seek(frame)
            shots[frame] = page.capture("png")
        return shots


@pytest.mark.parametrize("storyboard_path", sorted(CASES))
def test_both_paths_draw_the_same_frames(chromium_ready, storyboard_path):
    """同一帧在两条路径上必须达到 PSNR ≥ 60 dB。"""
    _skip_if_unbuilt()
    storyboard = ROOT / storyboard_path
    frames = CASES[storyboard_path]

    legacy_url, manager = _legacy_url(storyboard)
    try:
        legacy = _shots(legacy_url, frames)
    finally:
        manager.__exit__(None, None, None)
    with contract_page.serve_contract_page(storyboard, ROOT) as react_url:
        react = _shots(react_url, frames)

    verdicts = [
        (frame, determinism.psnr(legacy[frame], react[frame])) for frame in frames
    ]
    worst = min(verdicts, key=lambda item: item[1])
    detail = "；".join(f"第 {frame} 帧 {value:.1f} dB" for frame, value in verdicts)
    assert worst[1] >= PSNR_THRESHOLD, (
        f"{storyboard_path}：最差一帧（第 {worst[0]} 帧）只有 {worst[1]:.1f} dB，"
        f"低于 {PSNR_THRESHOLD} dB。逐帧：{detail}"
    )
