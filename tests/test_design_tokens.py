"""设计令牌读取器：解析、单位校验，以及字幕几何不许再退回第二处真源。"""
from __future__ import annotations

import math

import pytest

from m2v.core.errors import M2VError
from m2v.core import frames
from m2v.engine import design_tokens
from m2v.types.general import explainer_render

SAMPLE = """
:root { color-scheme: dark; }
@theme static {
  --m2v-width: 1080px;
  --m2v-grid-columns: 12;
}
"""


def test_只认_theme_static_那一个块():
    """`:root` 里的声明不是令牌，抽进来会让取值取决于文件顺序。"""
    table = design_tokens.theme_block(SAMPLE)
    assert table == {"--m2v-width": "1080px", "--m2v-grid-columns": "12"}


def test_缺少标记或没有闭合时明确失败():
    with pytest.raises(M2VError, match="找不到"):
        design_tokens.theme_block(":root { --m2v-width: 1080px; }")
    with pytest.raises(M2VError, match="没有闭合"):
        design_tokens.theme_block("@theme static { --m2v-width: 1080px;")


def test_单位不符时失败而不是当数字继续算():
    """`px` 取值写错单位应当在这里报错，而不是被当成无单位数值。"""
    table = design_tokens.tokens()
    assert design_tokens.px("--m2v-size-body") == 40
    assert design_tokens.number("--m2v-grid-columns") == 12
    with pytest.raises(M2VError, match="应为 px 长度"):
        design_tokens.px("--m2v-grid-columns")
    with pytest.raises(M2VError, match="应为无单位数值"):
        design_tokens.number("--m2v-size-body")
    with pytest.raises(M2VError, match="没有"):
        design_tokens.px("--m2v-这个令牌不存在")


def test_字幕几何不再写在令牌层里():
    """字幕盒按画幅集中在画幅清单：令牌层里再留一份就是第二处真源。"""
    table = design_tokens.tokens()
    stale = sorted(name for name in table if name.startswith(("--m2v-subtitle-", "--m2v-measure-")))
    assert stale == [], f"令牌层里还有已被画幅清单接管的名字：{stale}"


def test_画幅清单是字幕几何的唯一真源():
    """SDK、合成层与量测消费的准备产物都从同一份清单派生。"""
    portrait, landscape = frames.spec(1080, 1920), frames.spec(1920, 1080)
    assert set(portrait["subtitle"]) == {"safeArea", "fontSize", "lineHeight", "textColor", "plateColor"}
    # 盒几何保留画幅缩放；手机观看时横竖屏字幕均40px，避免横屏字号随高度缩小。
    ratio = 1080 / 1920
    # 四舍五入（half-up）而不是 Python 的银行家舍入：22.5 取 23。
    scale = lambda value: math.floor(value * ratio + 0.5)  # noqa: E731 - 量算式写在一处更好读
    assert landscape["subtitle"]["fontSize"] == portrait["subtitle"]["fontSize"] == 40
    assert landscape["subtitle"]["safeArea"]["height"] == scale(portrait["subtitle"]["safeArea"]["height"])
    portrait_gap = portrait["height"] - (portrait["subtitle"]["safeArea"]["y"] + portrait["subtitle"]["safeArea"]["height"])
    landscape_gap = landscape["height"] - (landscape["subtitle"]["safeArea"]["y"] + landscape["subtitle"]["safeArea"]["height"])
    assert landscape_gap == scale(portrait_gap)
    for spec in (portrait, landscape):
        area = spec["subtitle"]["safeArea"]
        assert area["x"] == round(spec["width"] * portrait["subtitle"]["safeArea"]["x"] / portrait["width"])
        assert area["width"] == spec["width"] - 2 * area["x"], "字幕盒左右内缩必须对称"
    # 字幕样式独立于作品配色：白字配不透明深色底板。
    assert portrait["subtitle"]["textColor"] == landscape["subtitle"]["textColor"] == "#ffffff"
    assert portrait["subtitle"]["plateColor"] == landscape["subtitle"]["plateColor"]


def test_量测脚本的安全区就是画幅清单取值():
    """守住接线：安全区必须来自画幅清单，不能再退回脚本里的字面量。"""
    for size in frames.sizes():
        script = explainer_render.measure_script(size=size)
        safe = frames.spec(*size)["subtitle"]["safeArea"]
        for name, value in safe.items():
            assert f'"{name}": {value}' in script, f"{size} 的 {name} 没有进量测脚本"
        # 判据只经 `B.` 引用，脚本里不该再出现这些数字。
        for value in safe.values():
            assert f"< {value}" not in script and f"> {value}" not in script


def test_未支持画幅明确失败():
    with pytest.raises(M2VError, match="仅支持"):
        frames.normalize(1080, 1080)
    with pytest.raises(M2VError, match="画幅清单里没有"):
        frames.spec(1080, 1080)
