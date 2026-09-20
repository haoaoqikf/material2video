#!/usr/bin/env python
from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from a2v.migration import migrate_file

def main() -> int:
    parser = argparse.ArgumentParser(description="把一个旧版分镜显式迁移到 v2 场景树")
    parser.add_argument("source", type=Path); parser.add_argument("output", type=Path); parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try: report = migrate_file(args.source, args.output, force=args.force)
    except (OSError, ValueError, KeyError) as exc: print(f"迁移失败：{exc}", file=sys.stderr); return 2
    print(f"已写出：{args.output}"); print(f"迁移报告：{report}"); print("迁移成功不等于视觉验收通过，请继续运行 a2v.py validate --strict 与 a2v.py review。")
    return 0
if __name__ == "__main__": raise SystemExit(main())
