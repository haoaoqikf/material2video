# -*- coding: utf-8 -*-
"""K10 主次分明的成对测试。

一条新判据要两头发力：**正向**要能抓住"两块一样大、看不出主次"的画面，
**反向**不能把"本来就主次分明"的画面拦下来。缺任何一头，这条判据都不算立住。
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import a2v.types.article.keynote as keynote


def _text(role, left, right, top, bottom, size, alpha=1.0):
    return {
        "role": role,
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "fontSize": size,
        "alpha": alpha,
    }


def test_flags_two_equally_sized_blocks():
    """正向：两块等大的可见文本 → 看不出主次，必须报出来。"""
    gate = keynote.gate_hierarchy("probe", [
        _text("a", 0, 400, 0, 200, 60),
        _text("b", 0, 400, 300, 500, 60),
    ])
    assert gate.status in ("warn", "fail"), gate
    assert gate.value < keynote._HIERARCHY_MIN_RATIO


def test_flags_a_near_tie():
    """正向（更隐蔽的一种）：第一名只比第二名大一点点。"""
    gate = keynote.gate_hierarchy("probe", [
        _text("big", 0, 410, 0, 200, 60),
        _text("small", 0, 400, 300, 500, 60),
    ])
    assert gate.status in ("warn", "fail"), gate


def test_does_not_flag_a_clear_hierarchy():
    """反向：主次分明（实测里最小的 opening 是 3.12 倍）→ 不得拦。"""
    gate = keynote.gate_hierarchy("probe", [
        _text("headline", 0, 1200, 0, 400, 120),
        _text("body", 0, 400, 500, 560, 40),
    ])
    assert gate.status == "pass", gate
    assert gate.value >= keynote._HIERARCHY_MIN_RATIO


def test_skips_when_there_is_only_one_visible_block():
    """样本不足 → 跳过并写明原因，不硬判。"""
    gate = keynote.gate_hierarchy("probe", [_text("only", 0, 400, 0, 200, 60)])
    assert gate.status == "skipped", gate
    assert gate.detail


def test_invisible_text_never_takes_first_place():
    """渐变标题的 alpha 是 0（它"看不见"），不能让它当第一名把真实层级压掉。"""
    gate = keynote.gate_hierarchy("probe", [
        _text("ghost", 0, 2000, 0, 900, 200, alpha=0.0),
        _text("headline", 0, 1200, 0, 400, 120),
        _text("body", 0, 400, 500, 560, 40),
    ])
    assert gate.status == "pass", gate
    assert "headline" in gate.detail
