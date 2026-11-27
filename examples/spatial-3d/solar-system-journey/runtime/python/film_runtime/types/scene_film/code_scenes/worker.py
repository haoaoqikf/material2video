"""pure-time 采集子进程入口：只读取 JSON 任务，不依赖父进程状态。

父进程已经构建好 `scene.js` 并把块首、区间与输出路径写进任务；这里启动自己的
Chromium 采集该块，编码并写 receipt。失败以非零退出码返回，父进程汇总报错。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from film_runtime.core.errors import VideoError
from .capture import PURE_CONTRACT, _capture, _clip_receipt, _encode
from .config import copy_build_outputs
from .workspace import register_worker


def run_job(job: dict) -> None:
    root = Path(job["root"]).resolve()
    work = Path(job["work"]).resolve()
    output = Path(job["output"]).resolve()
    first, last = int(job["first"]), int(job["last"])
    register_worker(work.parent)
    work.mkdir(parents=True, exist_ok=True)
    copy_build_outputs(Path(job['sceneJs']).parent, work)
    config = job["config"]
    with sync_playwright() as playwright:
        probe = _capture(playwright, root, work, config, selected_frames=list(range(first, last)),
                         pure=True, verify_frames=int(job.get("verifyFrames", 4)), capture_start=first,
                         witness_frames=[int(frame) for frame in job.get("witnessFrames", [])])
    _encode(work, output, last - first, config["width"], config["height"],
            start_frame=first, fps=int(job["fps"]),
            supersample=int((config.get("motion") or {}).get("supersample", 1)))
    extra = {"contract": PURE_CONTRACT, "verified": True, **(probe or {})}
    _clip_receipt(output, first, last, extra=extra)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("用法：python -m film_runtime.types.scene_film.code_scenes.worker <job.json>", file=sys.stderr)
        return 2
    try:
        job = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        run_job(job)
        return 0
    except (VideoError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"pure-time 采集块失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
