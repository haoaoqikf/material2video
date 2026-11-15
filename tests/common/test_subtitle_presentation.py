"""双行字幕的翻译切分与自适应柔光辅助。"""
from __future__ import annotations

import pytest
from PIL import Image

from m2v.core.errors import M2VError
from film_runtime.engine import subtitle_backing
from m2v.engine.subtitles import split_translation


def test_translation_splits_on_matching_punctuation() -> None:
    assert split_translation(
        "Why care about opinions, the more exhausting life becomes?", 2, "hook"
    ) == ["Why care about opinions,", "the more exhausting life becomes?"]
    assert split_translation(
        "Consider: they are not watching you.", 2, "turn"
    ) == ["Consider:", "they are not watching you."]
    assert split_translation(
        "Do it boldly; say no when needed.", 2, "action"
    ) == ["Do it boldly;", "say no when needed."]


def test_translation_count_mismatch_fails() -> None:
    with pytest.raises(M2VError, match="英文翻译有 1 段"):
        split_translation("Only one sentence.", 2, "hook")
    with pytest.raises(M2VError, match="英文翻译为空"):
        split_translation("   ", 1, "hook")


@pytest.mark.parametrize("width,height", [(1080, 1920), (1920, 1080)])
def test_sample_uses_actual_subtitle_region_and_switches_ink(tmp_path, width, height):
    from m2v.core import frames

    subtitle = frames.spec(width, height)["subtitle"]
    area = subtitle["safeArea"]
    path = tmp_path / "background.png"
    # 同一幕的主体处于深色背景，字幕正下方是浅色文书。
    with Image.new("RGB", (width, height), "#090e18") as canvas:
        background = subtitle_backing.region_color(_save(canvas, path), area, width, height)
        assert subtitle_backing.appearance(background, subtitle)["textColor"] == "#ffffff"
        canvas.paste("#f4efe3", (area["x"], area["y"], area["x"] + area["width"], area["y"] + area["height"]))
        background = subtitle_backing.region_color(_save(canvas, path), area, width, height)
        assert background == "#f4efe3"
        assert subtitle_backing.appearance(background, subtitle)["textColor"] == "#101219"


def _save(canvas, path):
    canvas.save(path)
    return path
