#!/usr/bin/env python
"""生成配音、字幕和派生时间轴，不覆盖源分镜。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2v.cli import main_prepare

if __name__ == "__main__":
    raise SystemExit(main_prepare())
