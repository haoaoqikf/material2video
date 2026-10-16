"""设计令牌读取器：解析、单位校验，以及量测接线不许再退回字面量。"""
from __future__ import annotations

import pytest

from m2v.core.errors import M2VError
from m2v.engine import design_tokens
from m2v.types.general import explainer_render

SAMPLE = """
:root { color-scheme: dark; }
@theme static {
  --m2v-width: 1080px;
  --m2v-subtitle-leading: 1.5;
}
"""


def test_只认_theme_static_那一个块():
    """`:root` 里的声明不是令牌，抽进来会让取值取决于文件顺序。"""
    table = design_tokens.theme_block(SAMPLE)
    assert table == {"--m2v-width": "1080px", "--m2v-subtitle-leading": "1.5"}


def test_缺少标记或没有闭合时明确失败():
    with pytest.raises(M2VError, match="找不到"):
        design_tokens.theme_block(":root { --m2v-width: 1080px; }")
    with pytest.raises(M2VError, match="没有闭合"):
        design_tokens.theme_block("@theme static { --m2v-width: 1080px;")


def test_单位不符时失败而不是当数字继续算():
    """`px` 取值写错单位应当在这里报错，而不是被当成无单位数值。"""
    table = design_tokens.tokens()
    assert design_tokens.px("--m2v-subtitle-size") == 40
    assert design_tokens.number("--m2v-subtitle-leading") == 1.5
    with pytest.raises(M2VError, match="应为 px 长度"):
        design_tokens.px("--m2v-subtitle-leading")
    with pytest.raises(M2VError, match="应为无单位数值"):
        design_tokens.number("--m2v-subtitle-size")
    with pytest.raises(M2VError, match="没有"):
        design_tokens.px("--m2v-这个令牌不存在")


def test_量测需要的令牌都在令牌层里():
    """量测读的令牌缺一个就应当在准备/预演之外先失败，而不是画到一半才发现。"""
    table = design_tokens.tokens()
    for name in (
        "--m2v-subtitle-inset-x",
        "--m2v-subtitle-top",
        "--m2v-subtitle-height",
        "--m2v-subtitle-size",
        "--m2v-subtitle-leading",
        "--m2v-measure-left",
        "--m2v-measure-right",
        "--m2v-measure-top",
        "--m2v-measure-content-bottom",
        "--m2v-measure-subtitle-bottom",
    ):
        assert name in table, f"令牌层里缺少 {name}"


def test_量测脚本的边界就是令牌取值():
    """守住接线：边界必须来自令牌，不能再退回脚本里的字面量。"""
    table = design_tokens.tokens()
    script = explainer_render.measure_script()
    bounds = explainer_render.measure_bounds()
    assert set(bounds) == {"left", "right", "top", "contentBottom", "subtitleBottom"}
    assert bounds["left"] == float(table["--m2v-measure-left"][:-2])
    assert bounds["right"] == float(table["--m2v-measure-right"][:-2])
    assert bounds["top"] == float(table["--m2v-measure-top"][:-2])
    assert bounds["contentBottom"] == float(table["--m2v-measure-content-bottom"][:-2])
    assert bounds["subtitleBottom"] == float(table["--m2v-measure-subtitle-bottom"][:-2])
    # 判据只经 `B.` 引用，脚本里不该再出现这几个数字。
    for literal in ("< 106", "> 974", "< 158", "1782 : 1502", "> 1502"):
        assert literal not in script, f"量测脚本里又出现了字面量 {literal}"


def test_字幕盒令牌与量测边界同源():
    """字幕盒左右内缩与量测判据带 2px 容差，两者必须一起动。"""
    inset = design_tokens.px("--m2v-subtitle-inset-x")
    width = design_tokens.px("--m2v-width")
    top = design_tokens.px("--m2v-subtitle-top")
    height = design_tokens.px("--m2v-subtitle-height")
    assert design_tokens.px("--m2v-measure-left") == inset - 2
    assert design_tokens.px("--m2v-measure-right") == width - inset + 2
    assert design_tokens.px("--m2v-measure-subtitle-bottom") == top + height + 2
