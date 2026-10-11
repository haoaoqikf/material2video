"""体检生成的 `review.md` 模板必须真的能被机检读回来。

这份模板是 AI/评审人唯一会被引导填写的表格。模板标签与解析器对不上时，
按模板逐格填写的人会一直看到「待评审」，而**错误信息不会提这件事**——
发布闸门只会说「未填写」，于是同一份材料被反复重看。
所以这里测的不是正则，而是「照模板填完就算通过」这条闭环。
"""

from __future__ import annotations

import re

import a2v.types.article.animation_review as ar
import a2v.types.article.bespoke_review as br
import a2v.types.article.cli as cli
import a2v.types.article.rhythm_review as rhythm_review
import a2v.types.article.visual_narrative as vn

SCENES = ["opening", "smooth"]


def _fill_scores(text: str, *, graphics: int, motion: int) -> str:
    """像评审人那样把模板里的分数格填上。"""
    text = re.sub(r"^(\|\s*图形论证\s*\|)\s*\|", rf"\1 {graphics} |", text, flags=re.MULTILINE)
    text = re.sub(r"^(\|\s*动效服务\s*\|)\s*\|", rf"\1 {motion} |", text, flags=re.MULTILINE)
    text = re.sub(r"^(\|\s*节奏\s*\|)\s*\|", r"\1 4 | 00:12 核心阶段明显加速，00:34 结尾停留 |", text, flags=re.MULTILINE)
    return text.replace("- 是否值得发布：待评审", "- 是否值得发布：通过")


def _fill_bespoke(text: str, scores: dict[str, int]) -> str:
    text = text.replace("状态：待评审", "状态：启用")
    for scene_id, score in scores.items():
        row = f"| {scene_id} |" + f" {score} |" * 5 + " 00:00 实测依据 |"
        text = re.sub(rf"^\|\s*{scene_id}\s*\|[^\n]*$", row, text, flags=re.MULTILINE)
    return text


def test_模板标签与解析器一致(tmp_path):
    cli._ensure_aesthetic_review_template(tmp_path, SCENES)
    text = (tmp_path / "review.md").read_text(encoding="utf-8")
    for label in ("图形论证", "动效服务", "节奏"):
        assert re.search(rf"^\|\s*{label}\s*\|", text, re.MULTILINE), f"模板缺少「{label}」行"


def test_照模板填完就能发布(tmp_path):
    cli._ensure_aesthetic_review_template(tmp_path, SCENES)
    path = tmp_path / "review.md"
    path.write_text(
        _fill_bespoke(
            _fill_scores(path.read_text(encoding="utf-8"), graphics=5, motion=4),
            {scene: 4 for scene in SCENES},
        ),
        encoding="utf-8",
    )

    v6 = vn.review_v6(path, [])
    assert v6["score"] == 5 and v6["status"] == "通过" and v6["publishable"] is True

    a6 = ar.review_a6(path, {"scenes": []})
    assert a6["score"] == 4 and a6["status"] == "通过" and a6["publishable"] is True
    assert rhythm_review.review(path.read_text(encoding="utf-8"))["status"] == "pass"

    bespoke = br.review(
        path,
        {"scenes": [{"id": scene, "renderer": {"kind": "code"}} for scene in SCENES]},
    )
    assert bespoke["status"] == "通过" and bespoke["publishable"] is True


def test_模板分数不能靠说明文字误判(tmp_path):
    """没填分数时必须留在「待评审」，不能因为正文里出现「评分」就通过。"""
    cli._ensure_aesthetic_review_template(tmp_path, SCENES)
    path = tmp_path / "review.md"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n<!-- 评审人还需按量表给出评分 -->\n",
        encoding="utf-8",
    )
    assert vn.review_v6(path, [])["status"] == "待评审"
    assert ar.review_a6(path, {"scenes": []})["status"] == "待评审"


def test_早期模板标签仍然可读(tmp_path):
    """旧记录用的是「图形承担论证」「动效服务理解」，不能因为改词就失效。"""
    path = tmp_path / "review.md"
    path.write_text(
        "| 维度 | 评分（1-5） | 依据 |\n|---|---:|---|\n"
        "| 图形承担论证 | 4 | 旧记录 |\n| 动效服务理解 | 4 | 旧记录 |\n",
        encoding="utf-8",
    )
    assert vn.review_v6(path, [])["status"] == "通过"
    assert ar.review_a6(path, {"scenes": []})["status"] == "通过"
