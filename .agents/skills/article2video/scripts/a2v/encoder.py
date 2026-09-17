"""ffmpeg 视频编码管道。

渲染脚本逐帧产生 PNG 字节，本模块通过 stdin 把它们喂给 ffmpeg 的
image2pipe demuxer，避免把上千帧 PNG 落盘到磁盘。ffmpeg 二进制由
imageio-ffmpeg 提供，无需单独安装。
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .errors import A2VError

logger = logging.getLogger(__name__)

# 每帧一次 write，缓冲太小会放大系统调用开销；4MB 够容纳一帧大图。
_STDIN_BUFFER_SIZE = 4 * 1024 * 1024


class EncoderError(A2VError):
    """编码启动或写入失败，消息中附带 ffmpeg 的 stderr 便于定位。"""


class VideoEncoder:
    """管理一个 ffmpeg 子进程，逐帧写入图片并在退出时合成 MP4。

    用法::

        with VideoEncoder("out.mp4", fps=30) as enc:
            for frame_bytes in frames:
                enc.write(frame_bytes)

    input_codec 必须与写入的图片格式一致：JPEG 对应 ``mjpeg``，PNG 对应 ``png``。
    """

    def __init__(
        self,
        output: str | Path,
        fps: int,
        crf: int = 18,
        preset: str = "medium",
        input_codec: str = "mjpeg",
    ) -> None:
        self.output = Path(output)
        self.fps = fps
        self.crf = crf
        self.preset = preset
        self.input_codec = input_codec
        self._process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> "VideoEncoder":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.finish()
        else:
            self.abort()

    def start(self) -> None:
        """启动 ffmpeg 子进程。输出目录不存在时先创建。"""
        self.output.parent.mkdir(parents=True, exist_ok=True)
        command = [
            get_ffmpeg_exe(),
            # -y 覆盖已有输出；-loglevel error 减少管道读取量
            "-y",
            "-loglevel",
            "error",
            # 图片帧从 stdin 进入，帧率与分镜脚本保持一致
            "-f",
            "image2pipe",
            "-c:v",
            self.input_codec,
            "-framerate",
            str(self.fps),
            "-i",
            "-",
            # JPEG 帧带的是全范围（full range）色彩，直接被 libx264 编码会得到
            # yuvj420p(pc) 的流；部分播放器（例如 Windows 的 Media Foundation）
            # 会因此拒绝打开文件。这里统一转换成电视范围 + BT.709 的标准 4:2:0，
            # 并把色彩元数据显式写进码流，保证在手机、剪辑软件与各平台都能播。
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
            "-pix_fmt",
            "yuv420p",
            "-color_range",
            "tv",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            self.preset,
            "-crf",
            str(self.crf),
            "-movflags",
            "+faststart",
            str(self.output),
        ]
        logger.info("启动 ffmpeg: %s", " ".join(command))
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=_STDIN_BUFFER_SIZE,
            )
        except OSError as exc:
            raise EncoderError(f"无法启动 ffmpeg: {exc}") from exc

    def write(self, frame_bytes: bytes) -> None:
        """写入一帧图片。进程意外退出时抛出带 stderr 的错误。"""
        process = self._require_process()
        try:
            process.stdin.write(frame_bytes)
        except OSError as exc:
            # Windows 上写已终止进程的 stdin 报 Errno 22 而不是 BrokenPipeError，
            # 这里统一按管道失败处理，附上 ffmpeg 的 stderr 便于定位。
            raise EncoderError(self._stderr_text("写入帧时管道中断")) from exc
        if process.poll() is not None:
            raise EncoderError(self._stderr_text("ffmpeg 提前退出"))

    def finish(self) -> None:
        """关闭 stdin 并等待 ffmpeg 完成。编码失败时抛出错误。"""
        process = self._require_process()
        try:
            process.stdin.close()
        except OSError:
            pass  # stdin 已被 ffmpeg 侧关闭，稍后在返回码里报错
        process.wait()
        if process.returncode != 0:
            raise EncoderError(self._stderr_text(f"ffmpeg 编码失败（退出码 {process.returncode}）"))
        self._process = None
        logger.info("编码完成: %s", self.output)

    def abort(self) -> None:
        """异常路径下终止子进程，避免遗留僵尸进程。"""
        process = self._process
        if process is None:
            return
        self._process = None
        if process.poll() is None:
            process.kill()
            process.wait()
        logger.warning("已终止 ffmpeg 编码进程")

    def _require_process(self) -> subprocess.Popen[bytes]:
        if self._process is None:
            raise EncoderError("编码进程尚未启动或已经结束")
        return self._process

    def _stderr_text(self, prefix: str) -> str:
        process = self._process
        detail = ""
        if process is not None and process.stderr is not None:
            try:
                detail = process.stderr.read().decode("utf-8", errors="replace").strip()
            except OSError:
                detail = ""
        message = f"{prefix}"
        if detail:
            message = f"{prefix}\nffmpeg stderr:\n{detail[-2000:]}"
        return message
