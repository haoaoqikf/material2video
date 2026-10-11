from m2v.types.article.article_text import count_characters, extract_body, save_candidate, standard_length_result


def test_standard_boundaries():
    assert standard_length_result("甲" * 129) == {"count": 129, "pass": False}
    assert standard_length_result("甲" * 130) == {"count": 130, "pass": True}
    assert standard_length_result("甲" * 170) == {"count": 170, "pass": True}
    assert standard_length_result("甲" * 171) == {"count": 171, "pass": False}


def test_count_excludes_unicode_punctuation_and_white_space():
    assert count_characters("甲，A1 乙！　") == 4
    assert count_characters('''\'‘’"“”…！？—、。''') == 0


def test_only_first_nonempty_markdown_h1_is_a_title():
    assert extract_body("\n# 标题\n正文内容") == "正文内容"
    assert extract_body("第一行是正文\n第二行") == "第一行是正文\n第二行"
    assert count_characters(extract_body("# 标题\n" + "正文" * 65)) == 130


def test_python_whitespace_matches_unicode_white_space_property():
    assert count_characters("甲\u0085乙\u2007丙") == 3


def test_candidate_is_saved_separately_and_must_meet_standard_length(tmp_path):
    original = tmp_path / "article.md"
    original.write_text("原始内容保持不变", encoding="utf-8")
    candidate = save_candidate(tmp_path, "候" * 140, "a" * 64)
    assert candidate["path"] == "article.candidate.md"
    assert candidate["charCount"] == 140
    assert original.read_text(encoding="utf-8") == "原始内容保持不变"
    try:
        save_candidate(tmp_path, "短" * 129, "a" * 64)
    except ValueError as exc:
        assert "130～170" in str(exc)
    else:
        raise AssertionError("不合规候选稿必须被拒绝")
