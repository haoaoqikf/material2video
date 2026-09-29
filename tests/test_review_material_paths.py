"""联系表文件名必须跟着抽帧时间轴走。

静态材料 `contact-sheet.png` 只按分镜声明的时间轴生成（见视觉评审量表），
`production.json` 登记的就是它的摘要。带 `--media` 的体检按配音派生的时长抽帧，
画的是另一批帧，如果还写同一个文件名，就会覆盖登记过的材料，让门禁报
「材料已缺失或摘要已变化」——而画面一个字都没变。
"""
from __future__ import annotations

from a2v import cli, inspect


def test_sheet_name_follows_sampling_timeline() -> None:
    assert cli._contact_sheet_name("storyboard") == "contact-sheet.png"
    assert cli._contact_sheet_name("media") == "contact-sheet-media.png"
    # 没有 source 字段（旧报告）按静态材料处理，不要悄悄改名
    assert cli._contact_sheet_name(None) == "contact-sheet.png"


def test_review_summary_prints_the_sheet_it_wrote(tmp_path) -> None:
    payload = {"frameCount": 18, "summary": {"errors": 0, "warnings": 0}, "source": "media"}
    assert "contact-sheet-media.png" in cli._review_summary(payload, tmp_path)
    payload["source"] = "storyboard"
    assert "contact-sheet.png" in cli._review_summary(payload, tmp_path)
    assert "contact-sheet-media.png" not in cli._review_summary(payload, tmp_path)


def test_run_inspect_accepts_an_explicit_sheet_name() -> None:
    """文件名是参数而不是写死的常量：否则两条时间轴必然互相覆盖。"""
    import inspect as inspect_lib

    signature = inspect_lib.signature(inspect.run_inspect)
    assert signature.parameters["sheet_name"].default == "contact-sheet.png"
