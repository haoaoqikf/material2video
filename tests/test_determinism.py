"""确定性判定的单元与集成测试。

判据是 PSNR ≥ 60 dB。这里同时验证它的**两个方向**：

- 帧驱动的画面：同一帧两次求值必须通过；
- 时钟驱动的画面（CSS 动画）：同一帧两次求值必须**失败**。

只验前者的话，一个「永远返回通过」的实现也能过——那正是这套机检最怕的东西。
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

from a2v import determinism

from conftest import EXAMPLES_DIR

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = EXAMPLES_DIR / "index.html"


def _png(tmp_path: pathlib.Path, name: str, color: str) -> pathlib.Path:
    from imageio_ffmpeg import get_ffmpeg_exe

    target = tmp_path / name
    completed = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=64x64",
            "-frames:v",
            "1",
            str(target),
        ],
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    return target


def test_identical_images_report_infinite_psnr(tmp_path):
    first = _png(tmp_path, "a.png", "black")
    assert determinism.psnr(first, first) == float("inf")


def test_a_visually_large_difference_falls_far_below_the_threshold(tmp_path):
    first = _png(tmp_path, "a.png", "black")
    second = _png(tmp_path, "b.png", "white")
    value = determinism.psnr(first, second)
    assert value < 10, f"黑白两帧的 PSNR 竟然有 {value}"


def test_a_tiny_difference_scores_high_but_finite(tmp_path):
    first = _png(tmp_path, "a.png", "black")
    second = _png(tmp_path, "b.png", "0x010101")
    value = determinism.psnr(first, second)
    assert 40 < value < 60, f"差一个色阶应该落在 40~60 dB，实际 {value}"


def test_bytes_and_paths_are_both_accepted(tmp_path):
    first = _png(tmp_path, "a.png", "black")
    assert determinism.psnr(first.read_bytes(), first) == float("inf")


def test_unreadable_input_is_reported_as_such(tmp_path):
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"this is not a png")
    with pytest.raises(determinism.DeterminismError) as excinfo:
        determinism.psnr(broken, broken)
    assert "无法比较" in str(excinfo.value)


def test_missing_file_is_reported_as_such(tmp_path):
    with pytest.raises(determinism.DeterminismError):
        determinism.psnr(tmp_path / "nope.png", tmp_path / "nope.png")


def test_verdict_threshold_and_describe(tmp_path):
    same = determinism.FrameVerdict(frame=42, psnr=float("inf"), threshold=60.0)
    assert same.ok and "完全一致" in same.describe()
    bad = determinism.FrameVerdict(frame=7, psnr=21.5, threshold=60.0)
    assert not bad.ok
    assert "未通过" in bad.describe() and "21.5" in bad.describe()


def test_summary_of_no_frames_is_not_a_pass():
    """空报告必须说「没执行」，不能长得像通过。"""
    assert "不是通过" in determinism.summarize([])


def test_summary_names_the_worst_frame():
    verdicts = [
        determinism.FrameVerdict(frame=0, psnr=72.0, threshold=60.0),
        determinism.FrameVerdict(frame=30, psnr=61.0, threshold=60.0),
    ]
    text = determinism.summarize(verdicts)
    assert "全部通过" in text and "61.0" in text and "第 30 帧" in text


def test_summary_of_a_failure_says_what_to_look_for():
    text = determinism.summarize(
        [determinism.FrameVerdict(frame=12, psnr=18.0, threshold=60.0)]
    )
    assert "第 12 帧" in text
    assert "CSS 动画" in text


# ------------------------------------------------------------------ 真画面


def _producer(page):
    """`produce(frame)`：定位到该帧并交出 PNG。"""

    def produce(frame: int) -> bytes:
        page.seek(frame)
        return page.capture("png")

    return produce


@pytest.fixture
def frame_driven_page():
    """示例网页：画面只由帧号决定。

    作用域是**单个用例**而不是整个模块：Playwright 的同步 API 在同一进程里
    不允许两个会话并存，模块级夹具会把浏览器一直握着，
    后面那个负例用例就打不开自己的页面了。
    """
    from a2v.browser import open_animated_page
    from a2v.render import _resolve_page_url

    with _resolve_page_url(PAGE, None) as url:
        with open_animated_page(url, width=1080, height=1920) as page:
            page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
            yield page


def test_frame_driven_page_passes_every_sampled_frame(chromium_ready, frame_driven_page):
    """抽三帧，每帧求值两次，全部要通过。"""
    verdicts = determinism.judge_frames(_producer(frame_driven_page), [0, 45, 700])
    assert determinism.failures(verdicts) == [], determinism.summarize(verdicts)
    assert all(verdict.psnr == float("inf") for verdict in verdicts), determinism.summarize(
        verdicts
    )


TIME_DRIVEN_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  @keyframes slide { from { transform: translateX(0) } to { transform: translateX(900px) } }
  #box { width: 180px; height: 180px; background: #f4f7fb; animation: slide 2s linear infinite; }
  body { margin: 0; background: #07090f; }
</style></head>
<body>
  <div data-a2v-stage style="width:1080px;height:1920px">
    <div id="box"></div>
  </div>
  <script>
    // 契约字段齐全、seekToFrame 也不报错——但画面由**时钟**决定，
    // 这正是要被抓出来的那类画面：它看起来完全正常，只是同一帧每次都不一样
    window.__A2V__ = {
      version: 1,
      fps: 30,
      width: 1080,
      height: 1920,
      durationInFrames: 60,
      ready: async () => {},
      seekToFrame: async () => { await new Promise((r) => setTimeout(r, 120)); },
    };
  </script>
</body></html>
"""


def test_time_driven_page_fails_the_judgement(chromium_ready, tmp_path):
    """负例：CSS 动画驱动的画面必须被判失败，并指名是哪一帧。"""
    from a2v.browser import open_animated_page
    from a2v.render import _resolve_page_url

    page_file = tmp_path / "time-driven.html"
    page_file.write_text(TIME_DRIVEN_PAGE, encoding="utf-8")

    with _resolve_page_url(page_file, tmp_path) as url:
        with open_animated_page(url, width=1080, height=1920) as page:
            verdicts = determinism.judge_frames(_producer(page), [30])

    bad = determinism.failures(verdicts)
    assert bad, "时钟驱动的画面竟然通过了确定性判定"
    assert bad[0].frame == 30
    assert bad[0].psnr < determinism.DEFAULT_PSNR_DB
    assert "第 30 帧" in determinism.summarize(verdicts)
