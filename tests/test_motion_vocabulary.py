# -*- coding: utf-8 -*-
"""动效语汇的护栏：缓动只能引用常量，手挑时长的去重数量不许再涨。

第 22 轮实测：49 处 `api.progress` 调用里，时长参数用了 **20 个不同取值**，
而且**混用两种单位**（帧数 12/14/…/40 与场景占比 0.05…0.36）；缓动有 3 条常量
外加 1 处裸字符串 `'linear'`。设计层本来就有时长阶梯
（`--a2v-dur-fast/base/slow` = 7/11/17 帧），但零消费者——动效时长是各组件手挑的。

这两条判据不假装统一已经做完，只做两件此刻就能成立的事：
把裸字符串堵掉；把"再发明一个取值"变成需要解释的失败。
"""
from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIGURES_JS = ROOT / ".agents/skills/article2video/assets/figures.js"
KEYNOTE_CSS = ROOT / ".agents/skills/article2video/assets/keynote.css"

#: 实测于第 22 轮。它是一道上限，不是目标：目标是让时长落回设计层的阶梯
#: （`--a2v-dur-fast/base/slow` = 7/11/17 帧），那一步会让这个数降下来。
DISTINCT_DURATION_CEILING = 20

#: 设计层给出的时长阶梯（帧）。它是"接上阶梯"那一步的靶子，所以不能被删掉。
LADDER_TOKENS = ("--a2v-dur-fast", "--a2v-dur-base", "--a2v-dur-slow")


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _calls(text: str, name: str) -> list[str]:
    """取出所有 `name(...)` 的实参文本（括号配平，不能靠正则硬凑）。"""
    out = []
    for match in re.finditer(re.escape(name) + r"\(", text):
        depth, index = 1, match.end()
        while index < len(text) and depth:
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
            index += 1
        out.append(text[match.end():index - 1])
    return out


def _split_args(args: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in args:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


@pytest.fixture(scope="module")
def progress_calls() -> list[list[str]]:
    source = _strip_comments(FIGURES_JS.read_text(encoding="utf-8"))
    calls = [_split_args(raw) for raw in _calls(source, "api.progress")]
    assert len(calls) > 40, f"只解析出 {len(calls)} 处调用，解析器大概失效了"
    return calls


class TestMotionVocabulary:
    """动效的语汇有上限——不然每加一个组件就多一档手感。"""

    def test_easing_is_a_named_constant(self, progress_calls: list[list[str]]) -> None:
        """缓动必须是常量，不许写裸字符串。

        组件文件自己定义了 `EASE_OUT` / `EASE_SOFT` / `EASE_SYMMETRIC` /
        `EASE_LINEAR`，就是为了让每一处都读得出"这是哪一档手感"。
        第 22 轮实测有 1 处写的是裸字符串 `'linear'`。
        """
        raw = []
        for args in progress_calls:
            if len(args) >= 4:
                easing = args[3]
                if easing.startswith(("'", '"')):
                    raw.append(easing)
        assert not raw, (
            f"{len(raw)} 处缓动写的是裸字符串：{raw[:3]}——"
            "改用 EASE_* 常量，否则没人能从调用点看出这是哪一档"
        )

    def test_hand_picked_durations_do_not_multiply(
        self, progress_calls: list[list[str]]
    ) -> None:
        """手挑时长的去重数量是一道上限。

        新组件要动效时，先复用已有的取值；确实需要新的一档，就把这个数字
        连同理由一起改——那正是"该把它接回设计层阶梯"的信号。
        """
        values = {args[2] for args in progress_calls if len(args) >= 3}
        assert len(values) <= DISTINCT_DURATION_CEILING, (
            f"手挑时长已经有 {len(values)} 个不同取值"
            f"（上限 {DISTINCT_DURATION_CEILING}）："
            f"{sorted(values)[:6]} …——先复用，或者接回 "
            f"{' / '.join(LADDER_TOKENS)} 那条阶梯"
        )

    def test_the_ladder_is_still_there(self) -> None:
        """阶梯是"接回去"那一步的靶子，删掉它等于把目标删掉。"""
        css = KEYNOTE_CSS.read_text(encoding="utf-8")
        missing = [token for token in LADDER_TOKENS if f"{token}:" not in css]
        assert not missing, f"设计层里少了时长阶梯：{missing}"
