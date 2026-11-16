"""恢复固定媒体；已登记且摘要一致的本地文件直接复用。"""
import logging
import subprocess
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from film_runtime.core.example_media import digest, download, restore


def recover_lunar_excerpt(recipe: dict, output: Path) -> None:
    """以固定编码器从 NASA 16mm 扫描中恢复已审核的无声窗口。"""
    if recipe["id"] != "moon-walk":
        raise ValueError(f"没有对应的恢复转换：{recipe['id']}")
    encoder = get_ffmpeg_exe()
    version = subprocess.check_output([encoder, "-version"], text=True).splitlines()[0]
    if not version.startswith("ffmpeg version 7.1-essentials_build-www.gyan.dev "):
        raise RuntimeError("恢复登月档案窗口需要固定的 FFmpeg 7.1 Windows 构建")
    with tempfile.TemporaryDirectory(prefix="m2v-apollo-") as directory:
        source = Path(directory) / "apollo11-mag-k.mov"
        download(recipe["sourceMediaUrl"], source)
        if digest(source) != recipe["sourceSha256"]:
            raise RuntimeError("NASA 1092-K 胶卷扫描文件摘要变化")
        subprocess.run([
            encoder, "-y", "-v", "error", "-xerror", "-ss", str(recipe["startSeconds"]),
            "-i", str(source), "-t", str(recipe["durationSeconds"]), "-map", "0:v:0", "-an",
            "-map_metadata", "-1", "-vf", recipe["videoFilter"],
            "-c:v", "libx264", "-crf", "16", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-threads", "1", str(output),
        ], check=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    restore(Path(__file__).resolve().parents[1], generate=recover_lunar_excerpt)
