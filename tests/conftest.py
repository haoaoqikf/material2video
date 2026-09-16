"""测试夹具：把 skill 内的 a2v 包加入导入路径。

a2v 包位于 skill bundle 内部（scripts/a2v），不随项目安装为可导入包，
因此测试需要显式注入路径，与四个入口脚本的做法保持一致。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "article2video" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "why-effort-fails"

# 项目根标记的相对路径，与 a2v.paths.PROJECT_MARKER 保持一致
SKILL_MARKER = Path(".agents/skills/article2video/SKILL.md")


def make_project(tmp_path: Path, kind: str, slug: str, script: dict | None = None) -> Path:
    """在 tmp_path 下搭一个最小的规范项目，返回文章目录。

    kind 取 "videos" 或 "examples"；script 提供时写入 storyboard.json。
    路径规则依赖项目根标记，因此每个用例都必须先有标记文件。
    """
    marker = tmp_path / SKILL_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("# article2video skill", encoding="utf-8")

    article = tmp_path / kind / slug
    article.mkdir(parents=True, exist_ok=True)
    (article / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")
    if script is not None:
        (article / "storyboard.json").write_text(
            json.dumps(script, ensure_ascii=False), encoding="utf-8"
        )
    return article


@pytest.fixture(scope="session")
def chromium_ready():
    """浏览器不可用时跳过，而不是让整个测试套件失败。"""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            playwright.chromium.launch(headless=True).close()
    except Exception as exc:  # noqa: BLE001 - 任何启动失败都应降级为跳过
        pytest.skip(f"未安装可用的 Playwright Chromium: {exc}")


def write_tone(path: Path, duration: float = 1.0) -> None:
    """写一段可解码的 440Hz WAV，作为 TTS 替身的音频。"""
    import math
    import struct
    import wave

    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        frames = (
            struct.pack("<h", int(2000 * math.sin(2 * math.pi * 440 * n / 24000)))
            for n in range(round(duration * 24000))
        )
        stream.writeframes(b"".join(frames))


@pytest.fixture
def speech(monkeypatch):
    """替换 edge-tts，让需要真实媒体清单的用例不访问网络。"""
    import re

    from a2v import prepare as prep

    async def fake(text, voice, rate, output):
        tokens = re.findall(r"[\w\u4e00-\u9fff]", text)
        # 音轨长度按字数放大，并让字词时间戳严格落在音轨内且单调递增：
        # 字幕校验会同时检查这两点，示例口播比单元测试长得多。
        write_tone(output, 0.2 + len(tokens) * 0.15)
        return [
            {"text": token, "start": 0.1 + i * 0.15, "end": 0.2 + i * 0.15}
            for i, token in enumerate(tokens)
        ]

    monkeypatch.setattr(prep, "synthesize", fake)


@pytest.fixture
def valid_script() -> dict:
    """一份结构完整的最小分镜脚本，测试中按需局部改动。"""
    return {
        "version": 1,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "title": "测试视频",
        "scenes": [
            {
                "id": "opening",
                "type": "title",
                "durationInFrames": 30,
                "data": {"text": "开场"},
            },
            {
                "id": "closing",
                "type": "conclusion",
                "durationInFrames": 60,
                "data": {"text": "结论"},
            },
        ],
    }
