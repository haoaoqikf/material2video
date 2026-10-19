"""太阳系示例的声音素材：无缝循环、不削顶、可解码，且分镜声明与实际文件一致。

素材按项目约定**不入库**（`.gitignore` 忽略 `*.wav`），因此测试先运行版本控制里的
生成器把它产出来——这也正是全新克隆后准备作品前的必要步骤。
"""
from __future__ import annotations

import json
import shutil
import struct
import sys
import subprocess
import wave
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/solar-system-journey"
SOUND = EXAMPLE / "assets/sound"
NAMES = ("bed.wav", "whoosh.wav", "shimmer.wav", "ice.wav", "score.wav")


@pytest.fixture(scope="module")
def sound_assets() -> Path:
    subprocess.run([sys.executable, str(SOUND / "generate.py")], check=True, capture_output=True, timeout=600)
    return SOUND


def samples(path: Path) -> tuple[int, ...]:
    with wave.open(str(path), "rb") as stream:
        assert stream.getframerate() == 24000 and stream.getnchannels() == 1
        raw = stream.readframes(stream.getnframes())
    return struct.unpack(f"<{len(raw) // 2}h", raw)


def test_bed_loops_without_a_seam(sound_assets):
    """判据不是「首尾采样接近」，而是末采样到首采样的步进不超过素材内部的最大相邻步进。"""
    values = samples(sound_assets / "bed.wav")
    steps = [abs(second - first) for first, second in zip(values, values[1:])]
    seam = abs(values[0] - values[-1])
    assert seam <= max(steps), f"循环点有接缝：{seam} > {max(steps)}"
    assert abs(values[0]) < 200, "循环点不应停在非零相位上"


def test_sound_assets_are_audible_and_not_clipped(sound_assets):
    for name in NAMES:
        values = samples(sound_assets / name)
        peak = max(abs(value) for value in values)
        assert 0.05 * 32767 < peak < 32000, f"{name} 的峰值不合理：{peak}"


def test_effects_decode_with_ffmpeg(sound_assets):
    for name in ("whoosh.wav", "shimmer.wav", "ice.wav"):
        result = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(sound_assets / name),
                                 "-f", "null", "-"], capture_output=True, timeout=60)
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")[-400:]


def test_storyboard_soundtrack_points_at_real_files(sound_assets):
    data = json.loads((EXAMPLE / "storyboard.json").read_text(encoding="utf-8"))
    track = data["soundtrack"]
    music = track["music"]
    assert music["loop"] is False and music["sourceRef"].endswith("score.wav")
    assert -6 <= music["gainDb"] <= 0
    with wave.open(str(EXAMPLE / music["sourceRef"]), "rb") as stream:
        assert stream.getnframes() / stream.getframerate() == data["scenes"][0]["durationFrames"] / data["fps"]
    assert (EXAMPLE / music["sourceRef"]).is_file()
    local = [effect for effect in track["effects"] if "sourceRef" in effect]
    assert len(local) == 2, "少量重要节点使用音效，避免每站重复"
    for effect in local:
        assert (EXAMPLE / effect["sourceRef"]).is_file()
        assert -60 <= effect["gainDb"] <= 0
        assert -60000 <= effect["offsetMs"] <= 60000



def test_generator_is_deterministic(sound_assets, tmp_path):
    """生成器是确定性的：换一个目录重跑应得到逐字节相同的素材。"""
    target = tmp_path / "sound"
    shutil.copytree(SOUND, target)
    for name in NAMES:
        (target / name).unlink()
    subprocess.run([sys.executable, str(target / "generate.py"), "--storyboard", str(EXAMPLE / "storyboard.json")], check=True, capture_output=True, timeout=600)
    for name in NAMES:
        assert (target / name).read_bytes() == (sound_assets / name).read_bytes(), f"{name} 不可复现"
