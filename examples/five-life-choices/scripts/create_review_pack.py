"""从候选视频生成可复核的匿名帧包、手机尺寸样张与 SHA-256 清单。"""
from __future__ import annotations

import argparse
import hashlib
import math
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe


def run(args: list[str]) -> None:
    subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def create(video: Path, output: Path, review_id: str, seconds: float, interval: float,
           start_seconds: float = 0) -> int:
    video = video.resolve(strict=True)
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"评审目录非空，拒绝覆盖：{output}")
    if start_seconds < 0 or seconds <= 0 or interval <= 0 or interval > seconds:
        raise ValueError("start-seconds 不得为负；seconds 和 interval 必须为正数，且 interval 不得大于 seconds")
    count = math.ceil(seconds / interval)
    output.mkdir(parents=True, exist_ok=True)
    full = output / "full"
    medium = output / "852"
    mobile = output / "393"
    for directory in (full, medium, mobile):
        directory.mkdir()
    pattern = str(full / "frame-%03d.png")
    run(["-ss", f"{start_seconds:.6f}", "-i", str(video), "-vf",
         f"fps=1/{interval:.6f}", "-frames:v", str(count), pattern])

    actual = len(list(full.glob("frame-*.png")))
    for width, target in ((852, medium), (393, mobile)):
        run(["-i", pattern, "-frames:v", str(actual), "-vf", f"scale={width}:-2",
             str(target / "frame-%03d.png")])
    columns = min(4, actual)
    rows = math.ceil(actual / columns)
    for name, directory, width in (("contact-sheet.png", full, 480),
                                   ("mobile-contact.png", mobile, 393)):
        sequence = str(directory / "frame-%03d.png")
        run(["-i", sequence, "-frames:v", "1", "-vf",
             f"scale={width}:-2,tile={columns}x{rows}", str(output / name)])

    lines = [f"{review_id} anonymous visual review",
             f"Source video SHA-256: {digest(video)}",
             f"{actual} frames sampled from {start_seconds:g}s every {interval:g} seconds; per-frame versions at 1920, 852, and 393px.",
             "Review only what is visible. Do not infer intended meaning.", "", "Frame timestamps:"]
    for index, frame in enumerate(sorted(full.glob("frame-*.png"))):
        timestamp = start_seconds + index * interval
        lines.append(f"- {frame.name}: {timestamp:.3f}s")
    lines.extend(("", "Review prompts:",
                  "1. Describe the visible event and whether it reads at a glance.",
                  "2. Note discontinuity, overlap, contact ambiguity, floating, or timing gaps with timestamps.",
                  "3. Assess pacing, the result hold, and phone-size readability.",
                  "4. Separate must-fix issues from preferences."))
    (output / "review-brief.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = []
    for path in sorted(p for p in output.rglob("*") if p.is_file() and p.name != "sha256.txt"):
        manifest.append(f"{digest(path)}  {path.relative_to(output).as_posix()}")
    (output / "sha256.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--id", required=True, help="不含设计语义的评审包编号")
    parser.add_argument("--seconds", required=True, type=float, help="候选片段检查时长")
    parser.add_argument("--start-seconds", type=float, default=0, help="候选片段在源视频中的起始秒数")
    parser.add_argument("--interval", type=float, default=0.5, help="抽帧间隔，秒")
    args = parser.parse_args()
    print(f"生成 {create(args.video, args.output, args.id, args.seconds, args.interval, args.start_seconds)} 帧：{args.output}")


if __name__ == "__main__":
    main()
