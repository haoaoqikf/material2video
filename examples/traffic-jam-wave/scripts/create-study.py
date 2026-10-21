"""低成本创意试制：推进原生60fps时钟、每6帧采图，以10fps生成草稿。

只供选案和整片结构复核，不能代替最终60fps成片。所有媒体留在忽略的交付输出。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from playwright.sync_api import sync_playwright

from m2v.core.project import load_project, _write_json
from m2v.engine import audio
from m2v.types.general import code_scenes, media_assets
from m2v.types.general.explainer_render import current


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", help="省略时制作整片粗预演")
    args = parser.parse_args()
    root, project = load_project(Path(__file__).resolve().parents[1])
    prepared = current(root, project)
    scenes = [s for s in prepared["props"]["compiledScenes"] if not args.scene or s["id"] == args.scene]
    if not scenes:
        parser.error("未知场景")
    output = root.parents[1] / "videos/examples" / root.name / "outputs/visual-review/studies"
    output.mkdir(parents=True, exist_ok=True)
    frame = {"width": prepared["width"], "height": prepared["height"], "subtitle": prepared["props"]["subtitle"]}
    media = media_assets.resolve(root)["media"]
    with tempfile.TemporaryDirectory(prefix="study-") as temp, sync_playwright() as pw:
        work = Path(temp)
        clips, captured_count = [], 0
        for index, source in enumerate(scenes):
            scene = json.loads(json.dumps(source))
            scene["content"]["props"]["draft"] = True
            directory = work / f"scene-{index}"
            directory.mkdir()
            code_scenes.build_scene(root, scene, directory)
            selected = list(range(0, scene["durationInFrames"], 6))
            code_scenes._capture(pw, root, directory, code_scenes.scene_config(scene, frame, media), selected_frames=selected)
            sequence = directory / "sequence"
            sequence.mkdir()
            for number, native in enumerate(selected):
                shutil.copyfile(directory / f"frame-{native:06d}.png", sequence / f"{number:06d}.png")
            clip = work / f"clip-{index}.mp4"
            subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-framerate", "10", "-i",
                            str(sequence / "%06d.png"), "-c:v", "libx264", "-preset", "fast",
                            "-crf", "23", "-pix_fmt", "yuv420p", str(clip)], check=True)
            clips.append(clip)
            captured_count += len(selected)
        listing = work / "clips.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
        silent = work / "silent.mp4"
        subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i",
                        str(listing), "-c", "copy", str(silent)], check=True)
        start = scenes[0]["startFrame"] / 60
        duration = sum(s["durationInFrames"] for s in scenes) / 60
        target = output / f"{args.scene or 'full-rough'}.mp4"
        audio.mux(silent, root / prepared["audio"]["segments"][0]["path"], target, duration, start=start)
    _write_json(target.with_suffix(".json"), {"kind": "creative-study-not-delivery", "preparedFingerprint": prepared["preparedFingerprint"],
                "sourceCadence": 60, "captureEveryFrames": 6, "outputFps": 10, "capturedFrames": captured_count,
                "scenes": [s["id"] for s in scenes], "subtitleCoverage": "not-composited; verify-final-separately"})
    print(target)


if __name__ == "__main__":
    main()
