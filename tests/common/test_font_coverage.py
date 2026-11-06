"""缺字机检：渲染用字必须在随仓库分发的字体里有字形。

缺字是唯一一种**静默失败**——浏览器不报错、不警告，直接用系统字体顶上，
字宽字重基线全变，而所有现有门禁照过。所以这条要真的量到字形，
两向都要验：全覆盖时不能报，缺字时必须报。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import m2v.core.fonts as fonts
from helpers.examples import STORYBOARD_PATHS

ASSETS = Path(__file__).resolve().parents[2] / "fonts/files"
NOTO = ASSETS / "NotoSansSC-Variable.ttf"
INTER = ASSETS / "Inter-Variable.ttf"

pytestmark = pytest.mark.skipif(
    not NOTO.is_file(), reason="字体未恢复；先运行 uv run python fonts/fetch.py")


class TestTheReaderItself:
    def test_reads_a_large_coverage_from_the_shipped_font(self):
        coverage = fonts.codepoint_coverage(NOTO)
        assert len(coverage) > 20_000, "Noto Sans SC 应当覆盖两万多个码位"
        assert ord("永") in coverage and ord("A") in coverage

    def test_inter_has_latin_but_no_cjk(self):
        coverage = fonts.codepoint_coverage(INTER)
        assert ord("A") in coverage
        assert ord("永") not in coverage, "Inter 不该有汉字——反例的立足点"

    def test_rejects_a_non_font(self, tmp_path):
        junk = tmp_path / "not-a-font.ttf"
        junk.write_bytes(b"this is not a font at all")
        with pytest.raises(ValueError):
            fonts.codepoint_coverage(junk)

    def test_emoji_and_unassigned_codepoints_are_missing(self):
        """字体里没有的码位要报出来，不能因为「区段看着像中文」就放过。"""
        text = "正常\U0001F600"  # 笑脸 emoji
        assert "\U0001F600" in fonts.missing_glyphs(NOTO, text)

    def test_missing_glyphs_keeps_first_seen_order_and_dedupes(self):
        missing = fonts.missing_glyphs(INTER, "甲乙甲")
        assert missing == ["甲", "乙"]

    def test_whitespace_is_not_a_missing_glyph(self):
        assert fonts.missing_glyphs(INTER, "A\n\t B") == []


class TestShippedWorksAreCovered:
    """三支真实作品的文本必须被随仓库分发的字体全覆盖。"""

    ROOT = Path(__file__).resolve().parents[2]

    def _texts(self, storyboard: Path) -> str:
        import json

        def walk(node, out):
            if isinstance(node, dict):
                for key, value in node.items():
                    if isinstance(value, str):
                        out.append(value)
                    else:
                        walk(value, out)
            elif isinstance(node, list):
                for item in node:
                    walk(item, out)

        out: list[str] = []
        walk(json.loads(storyboard.read_text(encoding="utf-8")), out)
        return "".join(out)

    @pytest.mark.parametrize("storyboard", STORYBOARD_PATHS)
    def test_every_rendered_character_has_a_glyph(self, storyboard):
        coverage = fonts.codepoint_coverage(NOTO)
        missing = fonts.missing_glyphs(NOTO, self._texts(self.ROOT / storyboard), coverage)
        assert missing == [], f"{storyboard} 缺字：{''.join(missing)}"


class TestAuditTellsYouWhereItHurts:
    """光说「缺字」没用，要说是哪一段缺——否则这条结论不可修。"""

    ROOT = Path(__file__).resolve().parents[2]
    BASELINE = ROOT / "examples/spatial-3d/solar-system-journey/storyboard.json"

    def _storyboard(self) -> dict:
        import json

        return json.loads(self.BASELINE.read_text(encoding="utf-8"))

    def test_a_clean_work_reports_nothing(self):
        assert fonts.audit_fonts([NOTO, INTER], self._storyboard()) == [], "全覆盖时必须一声不吭"

    def test_missing_glyph_is_reported_with_its_scene_and_field(self):
        data = self._storyboard()
        data["scenes"][0]["content"]["title"] = "正常\U0001F600"
        findings = fonts.audit_fonts([NOTO, INTER], data)
        assert findings, "插入了字体没有的字符，必须报出来"
        assert "\U0001F600" in findings[0]["missing"]
        assert f"{data['scenes'][0]['id']}.content.title" in findings[0]["where"], "结论要指到具体的讲解文字字段"

    def test_spoken_segments_are_not_scanned_as_visual_text(self):
        """口播段只供配音和字幕使用，不作为画面可见文字扫描。"""
        data = self._storyboard()
        stage = data["scenes"][0]
        stage["narrationSegments"] = [{"id": "n1", "text": "\U0001F600\U0001F601"}]
        assert fonts.audit_fonts([NOTO, INTER], data) == []
