"""生成原创 CC0 演示视频片段；无第三方素材。

用仓库依赖里已有的 ffmpeg（imageio-ffmpeg）合成 1080×1920、30 fps 的短视频，
画面是一个沿水平方向往返的圆点，用来演示 v6 视频模板的裁剪入点与显示适配。
生成后按 `m2v article assets import` 导入作品，文件以内容摘要命名并写入来源记录。
"""
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

FILTER = (
    "color=c=0x101820:s=1080x1920:r=30:d=4,"
    "drawbox=x='540-90+360*sin(2*PI*t/4)':y='960-90':w=180:h=180:"
    "color=0x4fa3ff@0.9:t=fill,"
    "drawbox=x='140':y='1700':w=800:h=6:color=0x2a3a4d@1:t=fill"
)


def write(name: str, seconds: int = 4) -> Path:
    path = Path(__file__).parent / name
    subprocess.run([
        get_ffmpeg_exe(), "-y", "-v", "error",
        "-f", "lavfi", "-i", FILTER,
        "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
    ], check=True)
    return path


if __name__ == "__main__":
    print(write("clip.mp4"))
