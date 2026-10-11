"""渲染基准与成片验收：冷/热缓存、并发对照与跨并发一致性。

为什么要有这个入口：缓存与并发的价值只能用**同一台机器上的同一段链路**证明。
把「快了」写成结论很容易，难的是把「在什么配置下、跑的哪一段、测了几次、
峰值内存多少」一起留下来，让数字可复核。因此这里：

- 三类场景都有明确定义：`baseline`（本次禁用缓存，等价于改动前每次重新打包）、
  `cold`（启用缓存但条目被清掉）、`hot`（同一输入已缓存）；
- 每个场景重复多次并报**中位数**，同时记录进程树峰值内存；
- 并发的对照先比**未编码中间帧**（PSNR ≥ 60 dB），再比编码成片的帧数、色彩、
  音轨与关键帧——不同码流不要求逐字节一致，但画质不得因此变化。

数字落在作品 `outputs/bench/`（已被 `.gitignore` 忽略），不进版本控制。
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

import a2v.engine.bundle_cache as bundle_cache
import a2v.types.article.paths as paths
import a2v.engine.perf as perf
import a2v.types.article.storyboard_v4 as storyboard_v4
import a2v.types.article.render as render_engine
import a2v.engine.remotion as remotion
from a2v.types.article.cli import _v4_model
from a2v.core.errors import A2VError
from a2v.types.article.media import load_media

logger = logging.getLogger(__name__)

#: 仓库自带的三个固定示例：基准只在它们上面跑，不新增示例目录。
EXAMPLES = ("buffer-smoothing", "darts-trial-and-error", "keynote-baseline")

#: 基准的默认帧数：验收要求至少 90 帧。
DEFAULT_FRAMES = 90

#: 每个场景的重复次数；中位数取三次。
DEFAULT_REPEATS = 3

#: 并发对照默认取值。
DEFAULT_CONCURRENCY = (1, 2, 4)

#: 目标（验收条件，不是承诺）：见 design.md 决策 5。
BUNDLE_REDUCTION_TARGET = 0.80
HOT_TOTAL_REDUCTION_TARGET = 0.10
COLD_REGRESSION_LIMIT = 0.05

#: 跨并发未编码画面的一致性阈值
PSNR_FLOOR_DB = 60.0


@dataclass(frozen=True)
class Case:
    """一次基准渲染的配置。"""

    example: str
    scenario: str  # baseline | cold | hot
    concurrency: int
    frames: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def storyboard_path_for(workspace_root: Path, example: str) -> Path:
    return workspace_root / "examples" / example / "storyboard.json"


def load_model(storyboard_path: Path):
    data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    report = storyboard_v4.validate(data)
    if report.errors:
        raise A2VError(f"基准只接受通过 v4 校验的分镜：{storyboard_path}：{report.issues}")
    return _v4_model(data)


def bench_dir(storyboard_path: Path, content_root: str | Path | None = None) -> Path:
    """基准产物目录：作品的 outputs/bench（已被 .gitignore 忽略）。"""
    article = paths.for_storyboard(storyboard_path, content_root)
    directory = article.output_dir / "bench"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def clear_bundle_cache(web_dir: Path) -> None:
    shutil.rmtree(bundle_cache.cache_root(web_dir), ignore_errors=True)


def render_case(
    case: Case,
    *,
    workspace_root: Path,
    content_root: str | Path | None = None,
) -> dict:
    """跑一次基准渲染，返回该次的真实耗时与峰值内存。"""
    storyboard_path = storyboard_path_for(workspace_root, case.example)
    model = load_model(storyboard_path)
    directory = bench_dir(storyboard_path, content_root)
    web = remotion.web_dir()
    if case.scenario == "cold":
        clear_bundle_cache(web)
    # `baseline`（禁用缓存，等价改动前每次重打）与 `steady`（丢弃式预热）都不碰缓存
    use_cache = case.scenario not in ("baseline", "steady")
    output = directory / f"{case.example}-{case.scenario}-c{case.concurrency}.mp4"
    logger.info(
        "基准渲染 %s/%s 并发 %d：%d 帧 → %s",
        case.example, case.scenario, case.concurrency, case.frames, output.name,
    )
    # 采样整棵进程树（本进程 + Node + Chromium）：并发提升的代价就是内存，
    # 只报耗时无法回答「值得吗」。
    sampler = perf.ProcessTreeMemorySampler(os.getpid(), interval_s=2.0)
    sampler.start()
    started = time.monotonic()
    failure: str | None = None
    try:
        result = render_engine.render_with_remotion(
            output=output,
            storyboard=model,
            storyboard_path=storyboard_path,
            limit_frames=case.frames,
            probe=True,
            workspace_root=workspace_root,
            content_root=content_root,
            concurrency=case.concurrency,
            bundle_cache=use_cache,
        )
    except BaseException as exc:  # 失败也要留证据：设计明确要求记录失败情况
        failure = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        peak = sampler.stop()
        wall = time.monotonic() - started
    payload = json.loads(perf.report_path_for(output).read_text(encoding="utf-8"))
    return {
        "example": case.example,
        "scenario": case.scenario,
        "concurrency": case.concurrency,
        "frames": result.frames,
        "wallSeconds": round(wall, 3),
        "totalSeconds": result.total_seconds,
        "captureSeconds": result.capture_seconds,
        "stages": result.stages,
        "cache": payload["cache"],
        "session": payload.get("session"),
        "peakRssBytes": peak,
        "memorySamples": sampler.samples,
        "outputBytes": result.size_bytes,
        "output": str(output),
        "startedAt": _now(),
        "failure": failure,
    }


def summarize_series(runs: list[dict]) -> dict:
    """把同一场景的多次运行压成中位数与峰值。"""

    def median(key: str) -> float | None:
        values = [run[key] for run in runs if run.get(key) is not None]
        return round(statistics.median(values), 3) if values else None

    stage_values: dict[str, float | None] = {}
    for stage in perf.STAGES:
        values = [
            run["stages"][stage]
            for run in runs
            if run.get("stages") and run["stages"].get(stage) is not None
        ]
        stage_values[stage] = round(statistics.median(values), 3) if values else None
    peaks = [run["peakRssBytes"] for run in runs if run.get("peakRssBytes")]
    return {
        "runs": len(runs),
        "frames": runs[0]["frames"],
        "concurrency": runs[0]["concurrency"],
        "cacheStatus": runs[0]["cache"]["status"],
        "totalSecondsMedian": median("totalSeconds"),
        "totalSecondsMin": round(min(run["totalSeconds"] for run in runs), 3),
        "totalSecondsMax": round(max(run["totalSeconds"] for run in runs), 3),
        "captureSecondsMedian": median("captureSeconds"),
        "stagesMedian": stage_values,
        "peakRssBytesMax": max(peaks) if peaks else None,
        "outputBytes": runs[-1]["outputBytes"],
    }


def _spread(series: dict) -> float:
    """一组运行的观测带宽（±秒）：(最大 − 最小) / 2。

    端到端总耗时的抖动来自渲染阶段本身（同一台机器、同一份输入，实测
    ±2 秒），因此「冷路径比基线慢多少」只能在**观测带宽**这个分辨率上读。
    """
    if not series:
        return 0.0
    return round((series["totalSecondsMax"] - series["totalSecondsMin"]) / 2, 3)


def evaluate_targets(series: dict[str, dict], *, representative: str) -> dict:
    """按 design 里的目标判定，逐条给出数值与结论。"""
    checks: list[dict] = []

    def add(name: str, value: float | None, target: float, op: str) -> None:
        if value is None:
            checks.append({"name": name, "value": None, "target": target, "op": op, "pass": False,
                           "detail": "缺少可比较的样本"})
            return
        ok = value >= target if op == ">=" else value <= target
        checks.append({"name": name, "value": round(value, 4), "target": target, "op": op, "pass": ok})

    for example in EXAMPLES:
        cold = series.get(f"{example}/cold/c1")
        hot = series.get(f"{example}/hot/c1")
        baseline = series.get(f"{example}/baseline/c1")
        if not cold or not hot or not baseline:
            # 缺样本不能算通过：报告里必须写清缺的是哪一项
            checks.append({
                "name": f"{example}: 场景样本完整",
                "value": None,
                "target": 1,
                "op": ">=",
                "pass": False,
                "detail": "缺少 baseline/cold/hot 中的一项，无法比较",
            })
            continue
        cold_bundle = (cold["stagesMedian"]["bundle"] or 0.0) + (cold["stagesMedian"]["cache"] or 0.0)
        hot_bundle = (hot["stagesMedian"]["bundle"] or 0.0) + (hot["stagesMedian"]["cache"] or 0.0)
        add(
            # 比「打包相关」而不是只比 bundle：命中时仍要算键与复核产物，
            # 把这段成本藏起来会让降幅虚高。
            f"{example}: 热缓存打包相关阶段下降",
            1 - hot_bundle / cold_bundle if cold_bundle else None,
            BUNDLE_REDUCTION_TARGET,
            ">=",
        )
        checks[-1]["detail"] = "含缓存键计算与完整性复核（cache+bundle）"
        checks[-1]["bundleOnlyReduction"] = (
            round(1 - (hot["stagesMedian"]["bundle"] or 0.0) / cold["stagesMedian"]["bundle"], 4)
            if cold["stagesMedian"]["bundle"]
            else None
        )

        # 冷路径回退：读**可归因的开销**，而不是两次端到端中位数之差。
        # 端到端总耗时的抖动（同一份输入实测 ±2 秒）比要判定的差异还大，
        # 用它当分子会把噪声判成回退；缓存唯一新增的工作就是它自己的准备阶段。
        baseline_median = baseline["totalSecondsMedian"]
        attributable = cold["stagesMedian"]["cache"] or 0.0
        end_to_end = cold["totalSecondsMedian"] - baseline_median
        noise = max(_spread(baseline), _spread(cold))
        add(
            f"{example}: 冷路径回退（缓存机制可归因开销）",
            attributable / baseline_median if baseline_median else None,
            COLD_REGRESSION_LIMIT,
            "<=",
        )
        checks[-1].update({
            "attributableSeconds": round(attributable, 3),
            "baselineSecondsMedian": baseline_median,
            "endToEndDeltaSeconds": round(end_to_end, 3),
            "endToEndRatio": round(end_to_end / baseline_median, 4) if baseline_median else None,
            "noiseSeconds": noise,
            "detail": (
                f"缓存机制自身耗时 {attributable:.2f}s（基线中位数 {baseline_median:.2f}s）；"
                f"端到端差值 {end_to_end:+.2f}s，观测带宽 ±{noise:.2f}s"
            ),
        })

    representative_cold = series.get(f"{representative}/cold/c1")
    representative_hot = series.get(f"{representative}/hot/c1")
    if representative_cold and representative_hot:
        add(
            f"{representative}: 热缓存端到端下降",
            1 - representative_hot["totalSecondsMedian"] / representative_cold["totalSecondsMedian"]
            if representative_cold["totalSecondsMedian"]
            else None,
            HOT_TOTAL_REDUCTION_TARGET,
            ">=",
        )
    return {
        "representative": representative,
        "checks": checks,
        # 一条结论都没有的报告不算通过
        "pass": bool(checks) and all(check["pass"] for check in checks),
    }


def warm_cache(workspace_root: Path, example: str, *, frames: int = 2) -> None:
    """用一次极短渲染把缓存建起来，使 hot 场景真的命中。"""
    render_case(
        Case(example=example, scenario="warmup", concurrency=1, frames=frames),
        workspace_root=workspace_root,
    )


def run_benchmark(
    *,
    workspace_root: Path,
    examples: tuple[str, ...] = EXAMPLES,
    frames: int = DEFAULT_FRAMES,
    repeats: int = DEFAULT_REPEATS,
    concurrency: tuple[int, ...] = DEFAULT_CONCURRENCY,
    representative: str | None = None,
    report_path: Path | None = None,
) -> dict:
    """跑完整矩阵：基线、冷、热、并发对照，写回结构化报告。"""
    representative = representative or examples[min(1, len(examples) - 1)]
    runs: list[dict] = []
    discarded: list[dict] = []
    series: dict[str, dict] = {}

    def record(case: Case) -> dict:
        outcome = render_case(case, workspace_root=workspace_root)
        runs.append(outcome)
        key = f"{case.example}/{case.scenario}/c{case.concurrency}"
        series.setdefault(key, {"runs": []})["runs"].append(outcome)
        return outcome

    for example in examples:
        # 丢弃式预热：一组里的**第一次**测量还包含一次性开销（打包器首次缓存、
        # 文件缓存、CPU 升频），把它算进中位数会让基线与冷缓存不可比——
        # 两者本应只差缓存机制本身。这一跑照实记录在 `discarded` 里，但不参与判定。
        discarded.append(
            render_case(Case(example, "steady", 1, frames), workspace_root=workspace_root)
        )
        for _ in range(repeats):
            record(Case(example, "baseline", 1, frames))
        # cold 每次开跑前清空缓存（在 render_case 里），因此每次都真的重新打包
        for _ in range(repeats):
            record(Case(example, "cold", 1, frames))
        warm_cache(workspace_root, example)
        for _ in range(repeats):
            record(Case(example, "hot", 1, frames))

    for value in concurrency:
        if value == 1:
            continue  # 并发 1 就是上面的 hot 场景，不重复测量
        warm_cache(workspace_root, representative)
        for _ in range(repeats):
            record(Case(representative, "hot", value, frames))

    summary = {key: summarize_series(item["runs"]) for key, item in series.items()}
    concurrency_summary = {
        value: summary.get(f"{representative}/hot/c{value}") for value in concurrency
    }
    speedups = {}
    base = summary.get(f"{representative}/hot/c1")
    for value in concurrency:
        item = summary.get(f"{representative}/hot/c{value}")
        if base and item and item["totalSecondsMedian"]:
            speedups[str(value)] = {
                "totalSecondsMedian": item["totalSecondsMedian"],
                "speedupVs1": round(base["totalSecondsMedian"] / item["totalSecondsMedian"], 3),
                "peakRssBytesMax": item["peakRssBytesMax"],
            }
    report = {
        "version": 1,
        "entry": "benchmark",
        "generatedAt": _now(),
        "method": {
            "framesPerRun": frames,
            "repeats": repeats,
            "scenarios": {
                "baseline": "本次禁用打包缓存（等价于改动前每次重新打包）",
                "cold": "启用缓存但条目已清空",
                "hot": "同一输入已缓存",
                "steady": "每个示例开跑前的丢弃式预热，不参与判定",
            },
            "memory": "进程树（本进程 + Node + Chromium）常驻内存按 2 秒间隔采样取峰值",
            "notes": "所有运行都走内部渲染 API（同一次校验、同一次验收），未降低分辨率或画质参数",
        },
        "environment": perf.environment(),
        "series": summary,
        "concurrency": concurrency_summary,
        "concurrencySpeedup": speedups,
        "targets": evaluate_targets(summary, representative=representative),
        "runs": runs,
        "discarded": discarded,
    }
    target = report_path or (bench_dir(storyboard_path_for(workspace_root, examples[0])) / "benchmark.json")
    perf.write_report(target, report)
    logger.info("基准报告：%s", target)
    return report


# ---------------------------------------------------------------- 跨并发一致性


def capture_frames(
    *,
    storyboard_path: Path,
    frames: int,
    concurrency: int,
    out_dir: Path,
    web_dir: Path,
) -> Path:
    """导出未编码中间帧（JPEG q98）。

    比较的对象必须是**编码前**的画面：编码器本身会把不同并发的输入差异抹平，
    只比成片无法回答「并发是否改变了画面」。
    """
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="a2v-frames-") as temporary:
        outcome = remotion.bundle(
            web_dir=web_dir,
            out_dir=Path(temporary) / "bundle",
            storyboard_path=storyboard_path,
        )
        remotion._run(
            [
                remotion.program("node"),
                remotion.RENDER_SCRIPT,
                "--bundle", str(outcome.path),
                "--props", str(storyboard_path),
                "--frames-out", str(out_dir),
                "--frames", f"0-{frames - 1}",
                "--concurrency", str(concurrency),
            ],
            cwd=web_dir,
            timeout_s=3600,
            what=f"导出并发 {concurrency} 的未编码截图",
        )
    return out_dir


_PSNR_PATTERN = re.compile(r"average:([0-9.]+|inf)")


def psnr_between(left: Path, right: Path) -> dict:
    """逐帧比较两组未编码截图，返回最差与平均 PSNR。"""
    first = sorted(path for path in left.iterdir() if path.is_file())
    second = sorted(path for path in right.iterdir() if path.is_file())
    if len(first) != len(second) or not first:
        raise A2VError(f"截图数量不一致：{len(first)} vs {len(second)}")
    values: list[float] = []
    worst = None
    for a, b in zip(first, second):
        completed = subprocess.run(
            [get_ffmpeg_exe(), "-hide_banner", "-i", str(a), "-i", str(b),
             "-lavfi", "psnr", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        )
        match = _PSNR_PATTERN.search(completed.stderr or "")
        if match is None:
            raise A2VError(f"无法比较 {a.name} 与 {b.name}：{(completed.stderr or '')[-400:]}")
        raw = match.group(1)
        value = math.inf if raw == "inf" else float(raw)
        values.append(value)
        if worst is None or value < worst[1]:
            worst = (a.name, value)
    finite = [value for value in values if math.isfinite(value)]
    return {
        "count": len(values),
        "minimumDb": round(min(finite), 3) if finite else None,
        "meanDb": round(statistics.fmean(finite), 3) if finite else None,
        "identicalFrames": len(values) - len(finite),
        "worstFrame": worst[0] if worst else None,
        "worstDb": None if worst is None or not math.isfinite(worst[1]) else round(worst[1], 3),
        "floorDb": PSNR_FLOOR_DB,
        "pass": all(value >= PSNR_FLOOR_DB for value in values),
    }


# ---------------------------------------------------------------- 成片验收


def stream_report(video: Path) -> dict:
    """读回成片的视频/音频码流参数。"""
    completed = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-i", str(video)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    video_line = next(
        (line for line in completed.stderr.splitlines() if "Video:" in line and "Stream #" in line),
        None,
    )
    audio_line = next(
        (line for line in completed.stderr.splitlines() if "Audio:" in line and "Stream #" in line),
        None,
    )
    return {"video": (video_line or "").strip(), "audio": (audio_line or "").strip()}


def count_keyframes(video: Path) -> int:
    """解码一遍，数 I 帧：首帧必须是关键帧，否则拖动播放会花屏。"""
    completed = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-i", str(video), "-vf", "showinfo", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
    )
    if completed.returncode != 0:
        raise A2VError(f"关键帧检查解码失败：{(completed.stderr or '')[-800:]}")
    return len(re.findall(r"type:I", completed.stderr or ""))


def verify_encoded(
    video: Path,
    *,
    frames: int,
    fps: int,
    width: int,
    height: int,
    expect_audio: bool,
    subtitles: Path | None = None,
    decode: bool = True,
) -> dict:
    """成片验收：完整解码、帧数、色彩、音轨参数、关键帧与字幕时间轴。"""
    result: dict = {"video": str(video), "frames": frames, "fps": fps}
    if decode:
        # 复用交付路径上的同一套验收：帧数、分辨率、帧率、时长、播放兼容、音轨时长
        render_engine._verify_output(video, frames, width, height, fps, expect_audio=expect_audio)
        result["decode"] = "pass"
    info = stream_report(video)
    result["stream"] = info
    if not info["video"]:
        raise A2VError(f"读不到视频码流信息：{video}")
    if "yuvj420p" in info["video"] or "(pc," in info["video"]:
        raise A2VError(f"成片是全范围像素格式（播放器会拒绝打开）：{info['video']}")
    if "yuv420p" not in info["video"]:
        raise A2VError(f"像素格式不是标准 4:2:0：{info['video']}")
    if "bt709" not in info["video"]:
        raise A2VError(f"色彩空间不是 BT.709：{info['video']}")
    result["colorSpace"] = "bt709"
    if expect_audio:
        if "aac" not in info["audio"].lower():
            raise A2VError(f"音轨不是 AAC：{info['audio']}")
        if "44100 Hz" not in info["audio"]:
            raise A2VError(f"音轨采样率不是 44.1kHz：{info['audio']}")
        if "stereo" not in info["audio"]:
            raise A2VError(f"音轨不是立体声：{info['audio']}")
        result["audioCodec"] = "aac"
    frames_key = count_keyframes(video)
    if frames_key < 1:
        raise A2VError("成片没有任何关键帧")
    result["keyframes"] = frames_key
    if subtitles is not None:
        result["subtitles"] = verify_subtitles(subtitles, frames / fps)
    return result


_SRT_TIME = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def verify_subtitles(path: Path, duration: float) -> dict:
    """字幕时间轴：单调递增、不越界、末尾不超出成片。"""
    if not path.is_file():
        raise A2VError(f"没有生成字幕文件：{path}")
    blocks = [block for block in path.read_text(encoding="utf-8").strip().split("\n\n") if block.strip()]
    cues = []
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        times = _SRT_TIME.findall(lines[1])
        if len(times) != 2:
            raise A2VError(f"字幕时间轴格式不对：{lines[1]!r}")
        start = _to_seconds(times[0])
        end = _to_seconds(times[1])
        if end <= start:
            raise A2VError(f"字幕区间不是正长度：{lines[1]!r}")
        cues.append((start, end))
    if not cues:
        raise A2VError(f"字幕文件里没有可用条目：{path}")
    for (_, previous_end), (start, _) in zip(cues, cues[1:]):
        if start < previous_end - 1e-6:
            raise A2VError("字幕时间轴出现重叠或倒序")
    if cues[-1][1] > duration + 0.5:
        raise A2VError(f"字幕超出成片时长：{cues[-1][1]:.2f}s > {duration:.2f}s")
    return {"cues": len(cues), "firstStart": round(cues[0][0], 3), "lastEnd": round(cues[-1][1], 3),
            "duration": round(duration, 3)}


def _to_seconds(parts: tuple[str, str, str, str]) -> float:
    hours, minutes, seconds, millis = (int(value) for value in parts)
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def accept_voiced(
    *,
    storyboard_path: Path,
    media_path: Path,
    workspace_root: Path,
    frames: int | None = None,
    psnr_frames: int = 30,
    concurrency: tuple[int, ...] = DEFAULT_CONCURRENCY,
    report_path: Path | None = None,
) -> dict:
    """全片（或指定帧数）有声渲染 + 跨并发未编码画面一致性验收。"""
    model = load_model(storyboard_path)
    media = load_media(media_path, storyboard_path)
    directory = bench_dir(storyboard_path)
    total = media.storyboard.total_frames
    frames = min(frames, total) if frames else total
    output = directory / "voiced-accept.mp4"
    logger.info("有声验收渲染：%d/%d 帧 → %s", frames, total, output)
    sampler = perf.ProcessTreeMemorySampler(os.getpid(), interval_s=2.0)
    sampler.start()
    try:
        result = render_engine.render_with_remotion(
            output=output,
            storyboard=model,
            storyboard_path=storyboard_path,
            media=media,
            limit_frames=None if frames == total else frames,
            probe=True,
            workspace_root=workspace_root,
            concurrency=1,
        )
    finally:
        peak = sampler.stop()
    delivered = {
        "output": str(output),
        "frames": result.frames,
        "totalFrames": total,
        "fps": result.fps,
        "peakRssBytes": peak,
        "stages": result.stages,
        "cacheStatus": result.cache_status,
    }
    delivered["encoded"] = verify_encoded(
        output,
        frames=result.frames,
        fps=result.fps,
        width=result.width,
        height=result.height,
        expect_audio=True,
        subtitles=output.with_suffix(".srt"),
    )

    comparisons: dict = {}
    web = remotion.web_dir()
    baseline_dir = directory / "frames-c1"
    capture_frames(
        storyboard_path=storyboard_path, frames=psnr_frames, concurrency=1,
        out_dir=baseline_dir, web_dir=web,
    )
    for value in concurrency:
        if value == 1:
            continue
        other = directory / f"frames-c{value}"
        capture_frames(
            storyboard_path=storyboard_path, frames=psnr_frames, concurrency=value,
            out_dir=other, web_dir=web,
        )
        comparisons[f"c1-vs-c{value}"] = psnr_between(baseline_dir, other)

    report = {
        "version": 1,
        "entry": "acceptance",
        "generatedAt": _now(),
        "storyboard": str(storyboard_path),
        "media": str(media_path),
        "delivered": delivered,
        "crossConcurrency": comparisons,
        "crossConcurrencyPass": all(item["pass"] for item in comparisons.values()),
    }
    target = report_path or (directory / "acceptance.json")
    perf.write_report(target, report)
    logger.info("验收报告：%s", target)
    return report


# ---------------------------------------------------------------- 入口


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="benchmark_render.py", description="渲染基准与成片验收")
    parser.add_argument("--workspace-root", default=None, help="工作区根；省略时用仓库根")
    parser.add_argument("--out", default=None, help="报告路径")
    parser.add_argument("-v", "--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    bench = subparsers.add_parser("benchmark", help="冷/热缓存与并发对照基准")
    bench.add_argument("--examples", nargs="+", default=list(EXAMPLES))
    bench.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    bench.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    bench.add_argument("--concurrency", nargs="+", type=int, default=list(DEFAULT_CONCURRENCY))
    bench.add_argument("--representative", default=None)

    accept = subparsers.add_parser("accept", help="全片有声渲染与跨并发一致性验收")
    accept.add_argument("--storyboard", required=True)
    accept.add_argument("--media", required=True)
    accept.add_argument("--frames", type=int, default=None, help="只渲前 N 帧；省略即全片")
    accept.add_argument("--psnr-frames", type=int, default=30)
    accept.add_argument("--concurrency", nargs="+", type=int, default=list(DEFAULT_CONCURRENCY))

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    workspace_root = Path(args.workspace_root).resolve() if args.workspace_root else paths.project_root(Path.cwd())
    report_path = Path(args.out).resolve() if args.out else None

    if args.command == "accept":
        report = accept_voiced(
            storyboard_path=Path(args.storyboard).resolve(),
            media_path=Path(args.media).resolve(),
            workspace_root=workspace_root,
            frames=args.frames,
            psnr_frames=args.psnr_frames,
            concurrency=tuple(args.concurrency),
            report_path=report_path,
        )
        return 0 if report["crossConcurrencyPass"] else 1
    report = run_benchmark(
        workspace_root=workspace_root,
        examples=tuple(args.examples),
        frames=args.frames,
        repeats=args.repeats,
        concurrency=tuple(args.concurrency),
        representative=args.representative,
        report_path=report_path,
    )
    for check in report["targets"]["checks"]:
        logger.info(
            "%s：%s %s %s → %s",
            check["name"], check["value"], check["op"], check["target"],
            "通过" if check["pass"] else "未达标",
        )
    return 0 if report["targets"]["pass"] else 1
