"""设计令牌在新画面工程里的**作用域**：在浏览器里量计算值。

为什么不能只读样式表文本：两层令牌是否按预期生效，取决于三件静态解析看不到的事——
选择器能不能命中、Tailwind 的 `@theme` 把变量输出到哪一层、自定义属性沿 DOM 树怎么继承。

实测踩过的坑正是这一条：预设层一度被写进 `@theme`（它只能输出到 `:root`），
于是**未启用预设**的画面也换上了预设的字体、安全区与底色，而全部静态检查照常通过。
这里问的是浏览器算出来的值，所以那类错误跑不掉。

会话策略：本模块只用**函数级**会话，在同一页面里依次读取深色并切换到浅色。
Playwright 的同步 API 不许一个进程里同时存在两个会话，因此这条检查不能和
持有模块级会话的模块放在一起（那正是它先前失败的原因）。
"""

from __future__ import annotations

import json
import pathlib

import pytest

import m2v.engine.browser as browser
import m2v.engine.contract_page as contract_page
from conftest import v4_storyboard

ROOT = pathlib.Path(__file__).resolve().parents[1]
def _preset_storyboard(tmp_path: pathlib.Path) -> pathlib.Path:
    article = tmp_path / "examples" / "preset-check"
    article.mkdir(parents=True)
    data = v4_storyboard()
    target = article / "storyboard.json"
    target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return target

#: 分两类看：既看两层**不同**的取值（字体、安全区、底色、字阶），
#: 也看只由默认层给出的令牌（`--m2v-surface` 这类）在预设下依然可用。
TOKENS = (
    "--m2v-bg-0",
    "--m2v-text-1",
    "--m2v-accent",
    "--m2v-safe-top",
    "--m2v-size-body",
    "--m2v-font",
    "--m2v-surface",
    "--m2v-width",
)


def _skip_if_unbuilt() -> None:
    page = contract_page.contract_page_path()
    if not page.is_file():
        pytest.skip(f"契约页尚未构建：{page}（先执行 cd web && pnpm install && pnpm build）")


def _tokens(url: str, chromium_ready, flips: tuple[str, ...] = ()) -> list[dict]:
    """打开页面读计算值；`flips` 里的主题会依次改写根元素属性后再读一次。

    改属性而不是另开一个页面：浅色主题的选择器要匹配的正是「预设与主题都挂在
    根元素上、舞台只管画面」这种形状；示例分镜声明深色预设，再在浏览器中切换浅色。

    属性挂在哪里是**契约的一部分**：React 路径与旧页面 `assets/declarative.js`
    一样，把 `data-m2v-preset` / `data-m2v-theme` / 尺寸变量写到
    `document.documentElement` 上（见 `M2VCompositionV4` 里的 `useLayoutEffect`），
    自定义属性沿 DOM 继承到舞台，因此这里读与改都落在根元素上。
    """
    with browser.open_animated_page(url, width=1080, height=1920, expected_version=4) as page:
        page.seek(0)
        reads = [
            page.evaluate(
                "() => {"
                f"const names = {list(TOKENS)!r};"
                "const root = getComputedStyle(document.documentElement);"
                "const stage = document.querySelector('.m2v-stage');"
                "const body = stage ? getComputedStyle(stage) : root;"
                "const out = {};"
                "for (const name of names) {"
                "out[name] = (body.getPropertyValue(name) || root.getPropertyValue(name) || '').trim();"
                "}"
                "return {tokens: out, preset: !!document.querySelector('[data-m2v-preset]'),"
                "theme: document.documentElement.getAttribute('data-m2v-theme')};"
                "}"
            )
        ]
        for theme in flips:
            page.evaluate(
                "(theme) => document.documentElement.setAttribute('data-m2v-theme', theme)",
                theme,
            )
            reads.append(
                page.evaluate(
                    "() => {"
                    f"const names = {list(TOKENS)!r};"
                    "const stage = document.querySelector('.m2v-stage');"
                    "const css = getComputedStyle(stage || document.documentElement);"
                    "const out = {};"
                    "for (const name of names) out[name] = (css.getPropertyValue(name) || '').trim();"
                    "return {tokens: out,"
                    "theme: document.documentElement.getAttribute('data-m2v-theme')};"
                    "}"
                )
            )
        return reads


def test_v4_preset_tokens_apply_to_dark_and_light_themes(chromium_ready, tmp_path):
    _skip_if_unbuilt()
    storyboard = _preset_storyboard(tmp_path)
    with contract_page.serve_contract_page(storyboard, tmp_path, repo_root=ROOT) as preset_url:
        dark, light = _tokens(preset_url, chromium_ready, flips=("light",))

    assert dark["preset"] is True, "启用预设的 V4 分镜必须在画面上挂出预设属性"
    assert dark["theme"] == "dark", dark
    assert dark["tokens"]["--m2v-safe-top"] == "240px", dark["tokens"]
    assert dark["tokens"]["--m2v-bg-0"].lower() == "#08090c", dark["tokens"]
    assert dark["tokens"]["--m2v-size-body"] == "40px", dark["tokens"]
    assert "M2V Inter" in dark["tokens"]["--m2v-font"], dark["tokens"]

    # 同一个页面上切成浅色：配色必须整体换掉，字阶与几何不动
    assert light["theme"] == "light"
    assert light["tokens"]["--m2v-bg-0"].lower() == "#eff1f4", light["tokens"]
    assert light["tokens"]["--m2v-accent"].lower() == "#0a6ad9", light["tokens"]
    assert light["tokens"]["--m2v-size-body"] == "40px", light["tokens"]
    assert light["tokens"]["--m2v-safe-top"] == "240px", light["tokens"]

    assert dark["tokens"]["--m2v-surface"].startswith("linear-gradient"), dark
    assert dark["tokens"]["--m2v-width"] == "1080px"
