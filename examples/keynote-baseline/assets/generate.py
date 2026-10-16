"""生成原创 CC0 演示视频片段；无第三方素材。

用仓库依赖里已有的 ffmpeg（imageio-ffmpeg）合成 1080×1920、30 fps 的短视频，
画面是一个沿水平方向往返的圆点，用来演示 v6 视频模板的裁剪入点与显示适配。
生成后按 `m2v general assets import` 导入作品，文件以内容摘要命名并写入来源记录。
"""
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

# 往返移动必须由 overlay 的 x 表达式驱动：本仓库的 ffmpeg（v7.1）只在配置阶段
# 求值一次 drawbox 的 x，用 drawbox 画会动的方块只会得到一张静止画面。
FILTER = (
    "color=c=0x101820:s=1080x1920:r=30:d=4[bg];"
    "color=c=0x4fa3ff:s=180x180:r=30:d=4,format=rgba,"
    "geq=r='79':g='163':b='255':a='if(lte(hypot(X-90,Y-90),90),230,0)'[dot];"
    "[bg][dot]overlay=x='540-90+360*sin(2*PI*t/4)':y='960-90':format=auto[stage];"
    "[stage]drawbox=x=140:y=1700:w=800:h=6:color=0x2a3a4d@1:t=fill"
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
