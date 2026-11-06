"""正文提取与非空计数：只覆盖仍被生产路径使用的行为。"""
from pathlib import Path

from m2v.types.scene_film.article_text import active_source, count_characters, extract_body


def test_count_excludes_unicode_punctuation_and_white_space():
    assert count_characters("甲，A1 乙！　") == 4
    assert count_characters('''\'‘’"“”…！？—、。''') == 0


def test_only_first_nonempty_markdown_h1_is_a_title():
    assert extract_body("\n# 标题\n正文内容") == "正文内容"
    assert extract_body("第一行是正文\n第二行") == "第一行是正文\n第二行"
    assert count_characters(extract_body("# 标题\n" + "正文" * 65)) == 130


def test_python_whitespace_matches_unicode_white_space_property():
    assert count_characters("甲\u0085乙\u2007丙") == 3


def test_active_source_prefers_the_adopted_copy(tmp_path: Path):
    original = tmp_path / "article.md"
    original.write_text("原始内容保持不变", encoding="utf-8")
    assert active_source(tmp_path).name == "article.md"
    (tmp_path / "article.accepted.md").write_text("采用稿", encoding="utf-8")
    assert active_source(tmp_path).name == "article.accepted.md"
    assert original.read_text(encoding="utf-8") == "原始内容保持不变"
