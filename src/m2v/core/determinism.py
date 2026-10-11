"""确定性判定：同一帧求值两次，画面必须足够接近。

判据是 **PSNR ≥ 60 dB**，不是逐字节相等。逐字节相等看着更严格，实际会用错：
字体栅格化与图片编码在换机器、换 Chromium 版本时会有末位差异，
于是「换了台机器」会被判成「画面坏了」；而真正的非确定性
（浏览器时钟、随机数、累积状态）在这个量级上根本藏不住，
它们产生的是几十像素的位移，PSNR 会掉到 20~40 dB。

画面比对交给 ffmpeg 的 `psnr` 滤镜：它已经在依赖里，逐像素算法是现成的，
不必为了算一个 MSE 把整帧读进 Python 循环。同帧两次求值完全一致时
ffmpeg 报 `average:inf`，这里按「超过任何阈值」处理。
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError

logger = logging.getLogger(__name__)

#: 判定阈值。取 60 dB：肉眼完全无法分辨，而任何真正的时间驱动差异都远低于它。
DEFAULT_PSNR_DB = 60.0

_AVERAGE_RE = re.compile(r"average:(inf|[\d.]+)")


class DeterminismError(M2VError):
    """画面无法比较（解不出来），而不是「画面不一致」。"""


@dataclass(frozen=True)
class FrameVerdict:
    """某一帧两次求值的判定结果。"""

    frame: int
    psnr: float
    threshold: float

    @property
    def ok(self) -> bool:
        return self.psnr >= self.threshold

    def describe(self) -> str:
        value = "完全一致" if self.psnr == float("inf") else f"{self.psnr:.1f} dB"
        verdict = "通过" if self.ok else "未通过"
        return f"第 {self.frame} 帧 {verdict}（{value}，阈值 {self.threshold:.0f} dB）"


def psnr(first: bytes | Path, second: bytes | Path) -> float:
    """两张图的 PSNR（dB）。完全一致时为 `inf`。"""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        left = _materialize(first, root / "first.png")
        right = _materialize(second, root / "second.png")
        output = subprocess.run(
            [
                get_ffmpeg_exe(),
                "-hide_banner",
                "-i",
                str(left),
                "-i",
                str(right),
                "-lavfi",
                "[0:v][1:v]psnr",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    line = next((item for item in output.stderr.splitlines() if "PSNR" in item), None)
    if line is None:
        tail = "\n".join(output.stderr.splitlines()[-8:])
        raise DeterminismError(f"无法比较两张图（ffmpeg 退出码 {output.returncode}）：\n{tail}")
    match = _AVERAGE_RE.search(line)
    if match is None:
        raise DeterminismError(f"ffmpeg 的 PSNR 输出无法解析：{line}")
    value = match.group(1)
    return float("inf") if value == "inf" else float(value)


def judge_frames(
    produce: Callable[[int], bytes | Path],
    frames: Iterable[int],
    *,
    threshold: float = DEFAULT_PSNR_DB,
) -> list[FrameVerdict]:
    """对每一帧求值两次并判定。

    `produce(frame)` 负责「定位到这一帧并交出画面」；调用方自己决定它是
    一次页面截图、一次 Remotion 渲染，还是别的什么。这里只关心
    「同一次调用两次拿到的画面是否一致」。

    两次求值之间**不做任何清理**：真的非确定性往往来自残留状态，
    清干净反而会把问题掩盖过去。
    """
    verdicts: list[FrameVerdict] = []
    for frame in frames:
        first = produce(frame)
        second = produce(frame)
        verdicts.append(FrameVerdict(frame=frame, psnr=psnr(first, second), threshold=threshold))
    return verdicts


def failures(verdicts: Sequence[FrameVerdict]) -> list[FrameVerdict]:
    """没通过的判定。"""
    return [verdict for verdict in verdicts if not verdict.ok]


def summarize(verdicts: Sequence[FrameVerdict]) -> str:
    """一句话结论，直接进报告。"""
    if not verdicts:
        return "没有可比对的帧：判定未执行（这不是通过）"
    bad = failures(verdicts)
    worst = min(verdicts, key=lambda verdict: verdict.psnr)
    if not bad:
        return (
            f"{len(verdicts)} 帧各求值两次全部通过，"
            f"最低 {_render(worst.psnr)}（第 {worst.frame} 帧）"
        )
    detail = "、".join(f"第 {verdict.frame} 帧 {_render(verdict.psnr)}" for verdict in bad)
    return (
        f"{len(bad)}/{len(verdicts)} 帧两次求值不一致：{detail}。"
        f"画面里存在不由帧号决定的成分（时钟、随机数、累积状态或 CSS 动画）"
    )


def _render(value: float) -> str:
    return "完全一致" if value == float("inf") else f"{value:.1f} dB"


def _materialize(image: bytes | Path, target: Path) -> Path:
    if isinstance(image, Path):
        if not image.is_file():
            raise DeterminismError(f"要比对的图片不存在：{image}")
        return image
    target.write_bytes(image)
    return target
