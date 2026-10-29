# -*- coding: utf-8 -*-
"""分镜文案的机械规则：标点、空白、占位符。

第 26 轮先量了一遍：3 份分镜、178 条字符串、8 条规则**零命中**——文案本身是干净的。
所以这份判据的价值不在"修"，而在"防"：文案是作者写的，机器只能守住机械部分，
而机械部分一旦破功（`AI,时代`、`。。`、留个 TODO 就出片）就是废片。

规则的适用范围有意收窄：**含汉字**的字符串才查中文标点类问题，
纯英文串（`"layout": "center"` 这类配置值）不适用——判据不该对
它看不懂的语种下判断。
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u4e00-\u9fff]")

#: 任何语言都不成立的规则
ALWAYS = {
    "重复标点": re.compile(r"[，。！？；：、,.!?;:]{2,}"),
    "首尾空白": re.compile(r"^\s|\s$"),
    "连续空格": re.compile(r" {2,}"),
    "占位残留": re.compile(r"\b(TODO|TBD|XXX|FIXME)\b|待填|待补|占位"),
}

#: 只对含汉字的字符串成立
CJK_ONLY = {
    "中英标点混排": re.compile(r"[，。！？；：、][,.;:!?]|[,.;:!?][，。！？；：、]"),
    # 只查 ,;:!? 而不查句点：句点在版本号与小数里是正常的（v1.2 / 3.5），
    # 中文里的半角句点另有一条规则，要求它紧跟汉字
    "半角标点出现在中文里": re.compile(r"[,;:!?]"),
    "半角句号紧跟汉字": re.compile(r"[\u4e00-\u9fff]\."),
    "三点省略": re.compile(r"\.\.\."),
}


def problems(text: str) -> list[str]:
    """返回这条文案踩到的规则名。"""
    found = [name for name, pattern in ALWAYS.items() if pattern.search(text)]
    if CJK.search(text):
        found += [name for name, pattern in CJK_ONLY.items() if pattern.search(text)]
    return found


def strings(node, path: str = ""):
    """深度优先取出所有字符串值（键不取）。"""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from strings(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def storyboards() -> list[pathlib.Path]:
    return sorted(ROOT.glob("styles/*/examples/*/storyboard.json"))


class TestCopyRules:
    """规则自己得先站得住：这些是"反向验证"写在用例里的形式。"""

    @pytest.mark.parametrize(
        "text,rule",
        [
            ("选项越多，决定越慢", None),
            ("多一个选项，并不是多一份自由", None),
            ("01 / 08", None),
            ("AI 时代的注意力", None),
            ("选项越多，，决定越慢", "重复标点"),
            ("多一个选项 ", "首尾空白"),
            ("选  项", "连续空格"),
            ("TODO: 填标题", "占位残留"),
            ("AI,时代", "半角标点出现在中文里"),
            ("这是个,逗号", "半角标点出现在中文里"),
            ("终于结束了.", "半角句号紧跟汉字"),
            ("还在想...", "三点省略"),
        ],
    )
    def test_rule_engine(self, text: str, rule: str | None) -> None:
        found = problems(text)
        if rule is None:
            assert not found, f"{text!r} 不该被判为有问题，却命中 {found}"
        else:
            assert rule in found, f"{text!r} 应该命中 {rule}，实际 {found}"

    def test_english_only_strings_are_not_judged(self) -> None:
        """配置值这类纯英文串不该被中文标点规则误伤。"""
        assert problems("center") == []
        assert problems("linear-gradient(180deg, red, blue)") == []


class TestEveryStoryboardCopy:
    """仓库里每一份分镜的文案都得过。"""

    def test_no_mechanical_problem(self) -> None:
        boards = storyboards()
        assert boards, "一份分镜都没找到，判据大概失效了"
        scanned = 0
        bad: list[str] = []
        for board in boards:
            data = json.loads(board.read_text(encoding="utf-8"))
            for path, text in strings(data):
                scanned += 1
                found = problems(text)
                if found:
                    bad.append(f"{board.parent.name}{path} {text[:30]!r} → {'/'.join(found)}")
        assert scanned > 100, f"只扫到 {scanned} 条字符串，解析大概失效了"
        assert not bad, "分镜文案踩到机械规则：\n  " + "\n  ".join(bad)
