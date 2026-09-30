#!/usr/bin/env python
"""视觉评审入口：抽帧量测 + 契约探针 + 观感闸门。

用法示例::

    uv run python .agents/skills/article2video/scripts/review.py \
        --storyboard videos/never-fear-interviews/storyboard.json \
        --media videos/never-fear-interviews/outputs/media/media.json

产出一张联系表、逐幕抽帧与 report.json，并在终端给出需要人工评审的清单。
它只负责把该看的摆出来，不代替人做审美判断。

脚本名不叫 inspect.py：入口脚本所在目录会被加入 sys.path，
与标准库的 inspect 同名会顶掉它（dataclasses 会因此导入失败）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v.cli import main_review  # noqa: E402  (路径注入后才能导入)

if __name__ == "__main__":
    raise SystemExit(main_review())
