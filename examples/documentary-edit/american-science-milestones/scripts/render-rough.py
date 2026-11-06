"""按当前分镜时长生成设计阶段粗预演：6 fps 采样、60 fps 容器。

只用于检查逐项节奏、构图与档案可辨度；帧数为采样后的近似值，不授权正式导出。
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from m2v.engine import audio, frames
from m2v.types.scene_film import code_scenes, media_assets

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FPS = 6
CAPTURE_SIZE = (1920, 1080)
OUTPUT_SIZE = (960, 540)


def main() -> None:
    prepared = json.loads((ROOT / "outputs/prepared.json").read_text(encoding="utf-8"))
    frame = frames.spec(*CAPTURE_SIZE)
    media = media_assets.resolve(ROOT)
    output = ROOT / "outputs/rough"
    output.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="rough-", dir=output) as temporary, sync_playwright() as pw:
        work_root = Path(temporary)
        for scene in prepared["props"]["compiledScenes"]:
            seconds = scene["durationInFrames"] / prepared["fps"]
            compiled = {**scene, "startFrame": 0, "segmentWindows": {},
                        "durationInFrames": round(seconds * SAMPLE_FPS)}
            config = code_scenes.scene_config(compiled, frame, media["media"], profile="standard")
            config["fps"] = SAMPLE_FPS
            work = work_root / scene["id"]
            work.mkdir()
            code_scenes.build_scene(ROOT, compiled, work)
            code_scenes._capture(pw, ROOT, work, config)
            clip = output / f"{scene['id']}.mp4"
            audio.ffmpeg(["-framerate", str(SAMPLE_FPS), "-i", str(work / "frame-%06d.png"),
                          "-vf", f"scale={OUTPUT_SIZE[0]}:{OUTPUT_SIZE[1]}:flags=lanczos",
                          "-r", str(prepared["fps"]), "-an", "-c:v", "libx264",
                          "-pix_fmt", "yuv420p", "-crf", "23", str(clip)])
            clips.append(clip)
    listing = output / "clips.txt"
    listing.write_text("".join(f"file '{path.as_posix()}'\n" for path in clips), encoding="utf-8")
    rough = output / "rough.mp4"
    audio.ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(rough)])
    receipt = {
        "preparedFingerprint": prepared["preparedFingerprint"],
        "storyboardSha256": hashlib.sha256((ROOT / "storyboard.json").read_bytes()).hexdigest(),
        "sourceSamplingFps": SAMPLE_FPS,
        "outputFps": prepared["fps"],
        "size": list(OUTPUT_SIZE),
        "captureSize": list(CAPTURE_SIZE),
        "seconds": prepared["durationInFrames"] / prepared["fps"],
        "videoSha256": hashlib.sha256(rough.read_bytes()).hexdigest(),
    }
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(rough)


if __name__ == "__main__":
    main()
