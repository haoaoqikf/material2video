"""从当前正式成片采集开场、关键节点和片尾基准及手机尺寸对照。"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.project import load_project
from m2v.types.general.explainer_render import current

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/visual-review/current"


def resize(source: Path, target: Path, width: int, height: int) -> None:
    result = subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(source),
                             "-vf", f"scale={width}:{height}:flags=lanczos", "-frames:v", "1", str(target)],
                            capture_output=True, timeout=120)
    if result.returncode or not target.is_file():
        raise RuntimeError(f"无法生成复核尺寸 {target.name}: {result.stderr.decode('utf-8', 'replace')[-400:]}")


def main() -> None:
    root, project = load_project(ROOT)
    prepared = current(root, project)
    scenes = prepared["props"]["compiledScenes"]
    by_id = {scene["id"]: scene for scene in scenes}
    frames = {
        "opening": by_id["opening"]["startFrame"],
        "opening-end": by_id["opening"]["startFrame"] + 119,
        "moon": by_id["moon"]["startFrame"] + 90,
        "transistor": by_id["transistor"]["startFrame"] + 60,
        "arpanet": by_id["arpanet"]["startFrame"] + 75,
        "llm": by_id["llm"]["startFrame"] + 135,
        "llm-end": by_id["llm"]["startFrame"] + 269,
        "closing": by_id["closing"]["startFrame"] + 119,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    video = root.parents[1] / "videos" / "examples" / root.name / "outputs" / "video.mp4"
    if not video.is_file():
        raise FileNotFoundError(f"缺少正式成片：{video}")
    records = []
    ffmpeg = get_ffmpeg_exe()
    for name, frame in frames.items():
        target = OUTPUT / f"{name}.png"
        seconds = frame / prepared["fps"]
        result = subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", f"{seconds:.3f}",
                                 "-i", str(video), "-frames:v", "1", "-update", "1", str(target)],
                                capture_output=True, timeout=120)
        if result.returncode or not target.is_file():
            raise RuntimeError(f"无法从正式成片采集 {name}: {result.stderr.decode('utf-8', 'replace')[-400:]}")
        resize(target, OUTPUT / f"{name}-phone.png", 699, 393)
        resize(target, OUTPUT / f"{name}-thumbnail.png", 160, 90)
        records.append({"name": name, "frame": frame, "seconds": round(seconds, 3),
                        "file": target.relative_to(root).as_posix(),
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "phoneFile": f"outputs/visual-review/current/{name}-phone.png",
                        "thumbnailFile": f"outputs/visual-review/current/{name}-thumbnail.png",
                        "nativeSize": [prepared["width"], prepared["height"]],
                        "sourceVideo": video.as_posix(),
                        "phoneImageSize": [699, 393], "thumbnailSize": [160, 90]})
    (OUTPUT / "manifest.json").write_text(json.dumps({"preparedFingerprint": prepared["preparedFingerprint"],
        "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
