"""按作品切字体子集。

fontTools 是运行时依赖；这里测的是“切出来的东西对不对”。要守住的三件事：
源文件不被改、子集真的更小、**切完必须过缺字机检**——最后一条是这条能力
能安全存在的前提：漏字的子集会静默回退到系统字体。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import m2v.core.fonts as fonts

from helpers.examples import STORYBOARD_PATHS

ROOT = Path(__file__).resolve().parents[2]
NOTO = ROOT / "fonts/files/NotoSansSC-Variable.ttf"
STORYBOARDS = STORYBOARD_PATHS

pytestmark = pytest.mark.skipif(
    not NOTO.is_file(), reason="字体未恢复；先运行 uv run python fonts/fetch.py")


def _storyboard(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class TestCharsetMatchesWhatTheCheckLooksAt:
    def test_charset_is_the_rendered_text_deduplicated(self):
        charset = fonts.charset_for({"scenes": [{"id": "a", "text": "甲乙甲", "title": "乙"}]})
        assert set(charset) == {"甲", "乙"}, "重复的字只出现一次"

    def test_narration_is_not_in_the_charset(self):
        """切子集与体检必须同一口径：口播段只用于音频，不作为可见文字。"""
        charset = fonts.charset_for({"scenes": [{"id": "a", "text": "甲", "narrationSegments": [{"id": "n1", "text": "乙丙", "beatId": "b1"}]}]})
        assert charset == "甲"


class TestSubsetting:
    def test_source_font_is_left_alone(self, tmp_path):
        before = NOTO.read_bytes()
        storyboard = _storyboard(STORYBOARDS[0])
        target = tmp_path / "subset.ttf"
        fonts.subset_font(NOTO, fonts.charset_for(storyboard), target)
        assert target.is_file()
        assert NOTO.read_bytes() == before, "共享字体是只读的：只能读它、不能改它"

    def test_subset_is_much_smaller_and_still_covers_the_work(self, tmp_path):
        storyboard = _storyboard(STORYBOARDS[0])
        target = tmp_path / "subset.ttf"
        fonts.subset_font(NOTO, fonts.charset_for(storyboard), target)
        assert target.stat().st_size < NOTO.stat().st_size / 10, "子集应当显著更小"
        missing = fonts.audit(storyboard, target)
        assert missing == [], f"子集漏字会让浏览器静默回退：{missing}"

    def test_all_three_works_can_be_subset_without_missing_glyphs(self, tmp_path):
        for index, relative in enumerate(STORYBOARDS):
            storyboard = _storyboard(relative)
            target = tmp_path / f"subset-{index}.ttf"
            fonts.subset_font(NOTO, fonts.charset_for(storyboard), target)
            assert fonts.audit(storyboard, target) == [], relative

    def test_dropping_a_character_is_caught_by_the_check(self, tmp_path):
        """反例：故意少切一个会被渲染的字，缺字机检必须报出来。"""
        storyboard = _storyboard(STORYBOARDS[0])
        charset = fonts.charset_for(storyboard)
        victim = next(char for char in charset if "\u4e00" <= char <= "\u9fff")
        target = tmp_path / "subset-missing.ttf"
        fonts.subset_font(NOTO, charset.replace(victim, ""), target)
        missing = fonts.audit(storyboard, target)
        assert missing, "漏字的子集必须被抓住"
        assert victim in "".join("".join(f["missing"]) for f in missing)
        assert missing[0]["where"], "结论要指到具体的幕与字段"
