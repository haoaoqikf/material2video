#!/usr/bin/env python
"""独立的导演层审美预检入口，复用 review.py 的同源 composition 抽帧流程。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v.cli import main_review  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main_review())
