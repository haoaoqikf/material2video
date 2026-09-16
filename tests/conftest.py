"""测试夹具：把 skill 内的 a2v 包加入导入路径。

a2v 包位于 skill bundle 内部（scripts/a2v），不随项目安装为可导入包，
因此测试需要显式注入路径，与三个入口脚本的做法保持一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "article2video" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "why-effort-fails"


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
