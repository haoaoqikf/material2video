"""全片节奏评分解析与正式渲染门禁。"""

from __future__ import annotations

import json
from types import SimpleNamespace

import m2v.types.article.cli as cli
import m2v.types.article.rhythm_review as rhythm_review


def test_missing_rhythm_score_is_pending():
    result = rhythm_review.review("- 是否值得发布：通过\n")
    assert result["status"] == "pending"
    assert result["publishable"] is False


def test_rhythm_score_requires_locatable_evidence():
    result = rhythm_review.review("| 节奏 | 4 | 整体节奏流畅 |\n")
    assert result["status"] == "pending"
    assert "定位" in result["detail"]


def test_duplicate_rhythm_rows_remain_pending():
    result = rhythm_review.review(
        "| 节奏 | 4 | 00:12 主要变化 |\n| 节奏 | 5 | 00:28 高潮收束 |\n"
    )
    assert result["status"] == "pending"
    assert "多个节奏评分行" in result["detail"]


def test_rhythm_below_four_fails_even_when_evidence_and_release_conclusion_pass():
    result = rhythm_review.review(
        "- 是否值得发布：通过\n| 节奏 | 3 | 00:12–00:20 核心与前段同速，缺少高潮变化 |\n"
    )
    assert result["status"] == "fail"
    assert result["publishable"] is False


def test_rhythm_four_or_five_pass_with_time_or_stage_evidence():
    for score, evidence in ((4, "00:12 核心提速；00:34 结尾停留"), (5, "阶段：高潮有明显转折")):
        result = rhythm_review.review(f"| 节奏 | {score} | {evidence} |\n")
        assert result["status"] == "pass"
        assert result["publishable"] is True


def test_explicit_rhythm_section_is_supported():
    result = rhythm_review.review("## 全片节奏\n评分：4/5\n依据：00:28 高潮动作加重，00:36 收束。\n")
    assert result["status"] == "pass"


def _render_gate(tmp_path, monkeypatch, valid_script_v4, review_text):
    monkeypatch.setattr(cli, "load_media", lambda *_args, **_kwargs: SimpleNamespace(
        data={"standardCheck": {"durationStatus": "pass"}},
    ))
    storyboard = tmp_path / "storyboard.json"
    storyboard.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding="utf-8")
    inspect_dir = tmp_path / "inspect"
    inspect_dir.mkdir(exist_ok=True)
    (inspect_dir / "report.json").write_text(json.dumps({"aestheticReview": {"findings": []}}), encoding="utf-8")
    (inspect_dir / "review.md").write_text(review_text, encoding="utf-8")
    article = SimpleNamespace(output_dir=tmp_path)
    return cli._aesthetic_render_gate(storyboard, SimpleNamespace(), article, tmp_path / "media.json")


def test_final_render_gate_blocks_missing_rhythm_score(tmp_path, monkeypatch, valid_script_v4):
    result = _render_gate(tmp_path, monkeypatch, valid_script_v4, "- 是否值得发布：通过\n")
    assert "全片节奏评审待完成" in result
    assert "至少 4/5" in result


def test_final_render_gate_blocks_rhythm_three_despite_publish_conclusion(tmp_path, monkeypatch, valid_script_v4):
    result = _render_gate(
        tmp_path, monkeypatch, valid_script_v4,
        "- 是否值得发布：通过\n| 节奏 | 3 | 00:12–00:20 高潮与前段同速 |\n",
    )
    assert "节奏评分 3/5" in result
    assert "重新生成材料并复评" in result


def test_final_render_gate_accepts_rhythm_four_or_five(tmp_path, monkeypatch, valid_script_v4):
    for score in (4, 5):
        result = _render_gate(
            tmp_path, monkeypatch, valid_script_v4,
            f"- 是否值得发布：通过\n| 节奏 | {score} | 00:12 核心转折，00:34 结尾停留 |\n",
        )
        assert result is None


def test_final_render_gate_requires_evidence_even_when_score_passes(tmp_path, monkeypatch, valid_script_v4):
    result = _render_gate(
        tmp_path, monkeypatch, valid_script_v4,
        "- 是否值得发布：通过\n| 节奏 | 4 | 看起来节奏不错 |\n",
    )
    assert "有声预演时间/阶段证据" in result
