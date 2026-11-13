"""双行字幕的翻译切分与自适应柔光辅助。"""
from __future__ import annotations

import pytest

from m2v.core.errors import M2VError
from m2v.engine import subtitle_backing
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


def test_fallback_backing_is_neutral_and_bounded() -> None:
    value = subtitle_backing.fallback(0.3)
    assert value["color"] == "#070a0e"
    assert value["background"] == "#070a0e"
    assert 0 <= value["opacity"] <= 0.3


@pytest.mark.media
def test_sample_reads_a_real_frame(tmp_path) -> None:
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe
    clip = tmp_path / "white.mp4"
    subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=white:s=108x192:d=1",
                    "-pix_fmt", "yuv420p", "-y", str(clip)], check=True)
    value = subtitle_backing.sample(clip, 0.3, 0.3)
    assert value["background"] == "#ffffff"
    assert 0.10 <= value["opacity"] <= 0.30
    assert value["color"].startswith("#")
