"""通用技术 QA：把「能不能导出」之外的画面与声音缺陷变成可复核的报告。

检查分两类：

- **硬判定**（失败即 `status: fail`）：冻结/重复帧、字幕对比度、响度与真峰值、
  音轨时长一致、每条 `claims` 的时间窗有覆盖镜头。
- **测量项**（只报告数值与提醒）：banding、aliasing、接触表，以及 `inspection.rhythm`
  的全片/逐场字数、旁白窗口、平均字速、静音分布与归因。它们受内容影响很大，
  用固定阈值判死会把正常画面误判成缺陷，因此只给数值与静帧复核入口。

报告写在作品 `outputs/qa.json`，接触表写在 `outputs/qa/contact-sheet.png`。
本模块不修改成片，也不参与导出门禁；它完成帧序列与自动信号复核所需的技术检查。
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from film_runtime.core.audio_policy import declared_audio
from film_runtime.core.delivery import outputs as output_root
from film_runtime.core.errors import VideoError
from film_runtime.core.project import _write_json
from film_runtime.engine import qa_inspection

#: 抽样画面的尺寸：够看出构图与 banding，又不会让抽样本身成为瓶颈。
SAMPLE_SIZE = (192, 104)
#: 冻结判据：相邻抽样帧的平均像素差低于该值即视为**重复帧**（不是慢镜头）。
#: 定标依据：同一支 174.6 秒三维示例，旧实时 screencast 片段在 1e-6 阈值下有 3.45 秒
#: 连续重复，受控逐帧采集片段最长 1.42 秒；把阈值放宽到 2e-5 会把慢速运镜也算成冻结。
FROZEN_DELTA = 1e-06
#: 冻结多久算缺陷（秒）：短暂停顿是叙事节奏，长时间重复同一帧才是卡住。
FROZEN_SECONDS = 3.0
#: freezedetect 只报告不短于该值的区间；更短的逐帧停顿不进入测量。
FREEZE_MIN_SECONDS = 0.1
#: 近乎静止（慢镜头或停顿）的参考阈值，只作为测量项报告。
NEAR_STILL_DELTA = 2e-05
#: 默认抽样步长（帧）。
DEFAULT_STEP = 30
#: 响度容差（LU）：母版混音与编码前后的正常波动，超出才判失败。
LOUDNESS_TOLERANCE = 2.0
TARGET = {"loudness": -14.0, "truePeak": -1.0}


def _run(args: list[str], *, binary: bool = False, timeout: int = 900):
    result = subprocess.run([get_ffmpeg_exe(), "-v", "error", *args],
                            capture_output=True, timeout=timeout)
    if result.returncode:
        raise VideoError(f"QA 媒体检查失败：{result.stderr.decode('utf-8', 'replace')[-1200:]}")
    return result.stdout if binary else result.stdout.decode("utf-8", "replace")


def sample_frames(video: Path, fps: int, step: int) -> list[bytes]:
    """按固定步长抽样灰度小图；返回每帧的原始字节。"""
    if step < 1:
        raise VideoError("抽样步长必须为正整数")
    width, height = SAMPLE_SIZE
    raw = _run(["-i", str(video), "-vf", f"fps={fps / step},scale={width}:{height},format=gray",
                "-f", "rawvideo", "-pix_fmt", "gray", "-"], binary=True)
    size = width * height
    return [raw[offset:offset + size] for offset in range(0, len(raw) - size + 1, size)]


def freeze_intervals(video: Path) -> list[tuple[float, float]]:
    """用 ffmpeg freezedetect 找冻结区间，返回 [(开始秒, 持续秒)]。

    检测在原生分辨率上执行，`n` 与现有平均像素差阈值同口径；`FREEZE_MIN_SECONDS`
    只过滤逐帧的极小停顿，不代表通过阈值。
    """
    result = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(video),
         "-vf", f"freezedetect=n={FROZEN_DELTA}:d={FREEZE_MIN_SECONDS}",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if result.returncode:
        raise VideoError(f"冻结帧检测失败：{result.stderr[-1200:]}")
    intervals: list[tuple[float, float]] = []
    current: float | None = None
    for kind, value in re.findall(
            r"lavfi\.freezedetect\.(freeze_start|freeze_duration|freeze_end):\s*([\d.]+)",
            result.stderr):
        seconds = float(value)
        if kind == "freeze_start":
            current = seconds
        elif kind == "freeze_duration" and current is not None:
            intervals.append((current, seconds))
            current = None
        elif kind == "freeze_end" and current is not None:
            intervals.append((current, max(0.0, seconds - current)))
            current = None
    if current is not None:
        # 冻结持续到片尾时 ffmpeg 只打印 freeze_start；用媒体时长补齐。
        intervals.append((current, max(0.0, _duration(video) - current)))
    return intervals


def frozen_frames(frames: list[bytes], fps: int, step: int, *,
                  video: Path | None = None) -> dict:
    """冻结帧报告：硬判定由 ffmpeg freezedetect 产生，采样只负责测量项。

    `video` 是生产路径必传的成片；纯帧列表调用保留给单元测试，用现有像素差
    作为降级判定。两者输出字段一致，调用方不需要分支。
    """
    deltas = []
    for previous, current in zip(frames, frames[1:]):
        total = sum(abs(a - b) for a, b in zip(previous, current))
        deltas.append(total / (len(previous) * 255))
    duplicates = sum(1 for delta in deltas if delta < FROZEN_DELTA)
    near = sum(1 for delta in deltas if delta < NEAR_STILL_DELTA)
    total = len(deltas) or 1

    if video is not None:
        intervals = freeze_intervals(video)
        longest_start_seconds, longest = max(intervals, key=lambda item: item[1], default=(0.0, 0.0))
        start_sample = round(longest_start_seconds * fps / step)
        end_sample = round((longest_start_seconds + longest) * fps / step)
    else:
        # 纯帧列表的降级路径：与旧实现一致的连续重复判定。
        run = longest_run = 0
        run_start = longest_start = 0
        for index, delta in enumerate(deltas):
            if delta < FROZEN_DELTA:
                if run == 0:
                    run_start = index
                run += 1
            else:
                run = 0
            if run > longest_run:
                longest_run, longest_start = run, run_start
        start_sample, end_sample = longest_start, longest_start + longest_run
        longest = longest_run * step / fps

    return {"sampledPairs": len(deltas), "minDelta": round(min(deltas), 7) if deltas else None,
            "meanDelta": round(sum(deltas) / len(deltas), 7) if deltas else None,
            "duplicatePairs": duplicates, "duplicateRatio": round(duplicates / total, 4),
            "nearStillRatio": round(near / total, 4),
            "longestStillSeconds": round(longest, 2), "frozenDelta": FROZEN_DELTA,
            "longestStillRange": {"startSample": start_sample, "endSample": end_sample},
            "status": "fail" if longest > FROZEN_SECONDS else "pass"}


def _shot_at(prepared: dict, frame: int) -> str | None:
    """把全片帧号定位到镜头 id；幕内镜头帧号先换成全片帧号。"""
    for scene in prepared["props"].get("compiledScenes", []):
        start = scene.get("startFrame", 0)
        for shot in ((scene.get("content", {}).get("props") or {}).get("shots") or []):
            if start + shot["startFrame"] <= frame < start + shot["endFrame"]:
                return shot["id"]
    return None


def _dark_levels(frame: bytes, ratio: float = 0.2) -> tuple[int, int]:
    """暗部像素的亮度层数与最大相邻跳变；跳变大说明渐变被量化成色带。"""
    ordered = sorted(frame)
    darkest = ordered[: max(1, int(len(ordered) * ratio))]
    levels = sorted(set(darkest))
    steps = [b - a for a, b in zip(levels, levels[1:])]
    return len(levels), max(steps) if steps else 0


def _total_variation(frame: bytes) -> float:
    """相邻像素差的均值：锯齿、摩尔纹与细密纹理都会抬高它。"""
    width, height = SAMPLE_SIZE
    total = 0
    for y in range(height):
        row = frame[y * width:(y + 1) * width]
        total += sum(abs(a - b) for a, b in zip(row, row[1:]))
    return total / (width * height)


def picture_metrics(frames: list[bytes]) -> dict:
    levels = [_dark_levels(frame) for frame in frames]
    variations = [_total_variation(frame) for frame in frames]
    return {
        "darkLevels": {"min": min(item[0] for item in levels), "max": max(item[0] for item in levels)},
        "darkMaxStep": max(item[1] for item in levels),
        "totalVariation": {"min": round(min(variations), 4), "max": round(max(variations), 4),
                           "mean": round(sum(variations) / len(variations), 4)},
    }


def contact_sheet(video: Path, target: Path, *, columns: int = 4, rows: int = 6, every: int = 5) -> Path:
    """均匀抽帧拼成一张接触表，供人一次看全片构图与曝光。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(["-i", str(video), "-vf", f"fps=1/{every},scale=480:-2,tile={columns}x{rows}",
          "-frames:v", "1", "-update", "1", "-y", str(target)])
    if not target.is_file():
        raise VideoError("接触表没有生成")
    return target


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        value = color.lstrip("#")
        if len(value) != 6:
            raise VideoError(f"颜色必须是 #rrggbb：{color}")
        channels = []
        for index in (0, 2, 4):
            channel = int(value[index:index + 2], 16) / 255
            channels.append(channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4)
        return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2]
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + .05) / (low + .05)


def subtitle_contrast(subtitle: dict) -> dict:
    ratio = _contrast_ratio(subtitle["textColor"], subtitle["plateColor"])
    return {"textColor": subtitle["textColor"], "plateColor": subtitle["plateColor"],
            "ratio": round(ratio, 2), "minimum": 4.5, "status": "pass" if ratio >= 4.5 else "fail"}


def loudness(audio: Path) -> dict:
    """母版响度与真峰值；统一目标 −14 LUFS / −1 dBTP，超限即失败。"""
    # ebur128 的汇总行走 info 级日志：`-v error` 会把要解析的内容一起吞掉。
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(audio),
                             "-af", "ebur128=peak=true", "-f", "null", "-"],
                            capture_output=True, timeout=900)
    text = result.stderr.decode("utf-8", "replace")
    integrated = true_peak = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("I:") and integrated is None:
            integrated = float(stripped.split()[1])
        elif stripped.startswith("Peak:") and true_peak is None:
            true_peak = float(stripped.split()[1])
    if integrated is None or true_peak is None:
        raise VideoError(f"无法从 ffmpeg 读取响度或真峰值：{text[-800:]}")
    target = TARGET
    return {"integratedLufs": round(integrated, 2), "truePeakDbfs": round(true_peak, 2),
            "targetLufs": target["loudness"], "targetTruePeak": target["truePeak"],
            "toleranceLu": LOUDNESS_TOLERANCE,
            "status": "pass" if (abs(integrated - target["loudness"]) <= LOUDNESS_TOLERANCE
                                 and true_peak <= target["truePeak"]) else "fail"}


def _duration(path: Path) -> float:
    """读取媒体时长；ffmpeg 在没有指定输出时会以非零退出码结束，这里只看流信息。"""
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                            capture_output=True, timeout=120)
    return _probe_duration(result.stderr.decode("utf-8", "replace"))


def _probe_duration(text: str) -> float:
    for line in text.splitlines():
        if "Duration:" in line:
            stamp = line.split("Duration:")[1].split(",")[0].strip()
            hours, minutes, seconds = stamp.split(":")
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise VideoError("无法读取媒体时长")


def audio_sync(video: Path, audio: Path, expected_seconds: float) -> dict:
    difference = abs(_duration(video) - _duration(audio))
    return {"videoSeconds": round(_duration(video), 3), "audioSeconds": round(_duration(audio), 3),
            "expectedSeconds": round(expected_seconds, 3), "differenceSeconds": round(difference, 3),
            "toleranceSeconds": 0.1, "status": "pass" if difference <= 0.1 else "fail"}


def claims_check(prepared: dict) -> dict:
    """只检查 claims 时间窗覆盖，不判断特征实际可见性。"""
    scenes = prepared["props"].get("compiledScenes", [])
    pending, missing = [], []
    for scene in scenes:
        shots = (scene.get("content", {}).get("props") or {}).get("shots") or []
        for segment in scene.get("narrationSegments", []):
            claims = segment.get("claims") or []
            if not claims:
                continue
            window = scene.get("segmentWindows", {}).get(segment["id"])
            if window is None:
                missing.append({"scene": scene["id"], "segment": segment["id"], "reason": "缺少时间窗"})
                continue
            covering = [shot["id"] for shot in shots
                        if shot["startFrame"] <= window["startFrame"] and shot["endFrame"] >= window["endFrame"]]
            entry = {"scene": scene["id"], "segment": segment["id"], "claims": claims,
                     "startFrame": window["startFrame"], "endFrame": window["endFrame"],
                     "shots": covering}
            pending.append(entry)
            if not covering:
                missing.append({"scene": scene["id"], "segment": segment["id"],
                                "reason": "没有镜头覆盖该旁白窗口"})
    return {"scope": "shot-window-coverage", "visibility": "not-evaluated",
            "segments": pending, "problems": missing,
            "status": "fail" if missing else "pass"}


def delivered_video(root: Path) -> Path:
    """成片位置：产物统一在作品目录下的 `outputs/`，示例也不例外。"""
    return root / "outputs/video.mp4"


def _video_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(root: Path, prepared: dict, *, video: Path | None = None, step: int = DEFAULT_STEP) -> dict:
    """执行全部检查并写入 `outputs/qa.json`；返回报告。"""
    root = root.resolve()
    fps = prepared["fps"]
    expected = prepared["durationInFrames"] / fps
    audio_segments = prepared.get("audio", {}).get("segments", [])
    target = (video or delivered_video(root)).resolve()
    if not target.is_file():
        raise VideoError(f"缺少待检查的成片：{target}；请先 preview 或 render")
    frames = sample_frames(target, fps, step)
    if len(frames) < 2:
        raise VideoError("成片太短，无法抽样检查")
    qa_dir = output_root(root) / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    audio_required = bool(audio_segments)
    audio_required = declared_audio(prepared)
    inspection = qa_inspection.inspect(target, prepared, qa_dir, audio_required=audio_required)
    has_audio = inspection["audioSignals"]["status"] != "not-applicable"
    no_audio = {"status": "not-applicable", "detail": "无音轨，契约允许"}
    if has_audio:
        video_seconds = _duration(target)
        audio_seconds = inspection["audioSignals"]["durationSeconds"]
        difference = max(abs(video_seconds - audio_seconds), abs(expected - audio_seconds),
                         abs(expected - video_seconds))
        sync = {"videoSeconds": video_seconds, "audioSeconds": audio_seconds,
                "expectedSeconds": expected, "differenceSeconds": round(difference, 5),
                "toleranceSeconds": .1, "status": "pass" if difference <= .1 else "fail"}
    else:
        sync = dict(no_audio)
    frozen = frozen_frames(frames, fps, step, video=target)
    # 冻结段必须能定位到镜头与时间戳，而不是只报一个总秒数。
    sample = frozen["longestStillRange"]
    start_frame = sample["startSample"] * step
    end_frame = sample["endSample"] * step
    frozen["problem"] = ({"startSeconds": round(start_frame / fps, 2),
                          "endSeconds": round(end_frame / fps, 2),
                          "shot": _shot_at(prepared, start_frame)}
                         if sample["endSample"] > sample["startSample"] else None)
    scenes = prepared["props"].get("compiledScenes", [])
    soundtrack = prepared["props"].get("soundtrack") or {}
    # 显式声明空 soundtrack（如 {"effects": []}）仍是无声设计；只有实际音乐或音效
    # 才会把成片带入有声响度目标。
    has_sound_design = bool(soundtrack.get("music") or soundtrack.get("effects"))
    silent_expected = bool(scenes) and not has_sound_design and not any(
        scene.get("narrationSegments") for scene in scenes)
    if silent_expected and has_audio:
        peak = inspection["audioSignals"]["peakAbsolute"]
        audio_level = {"status": "pass" if peak == 0 else "fail", "peakAbsolute": peak,
                       "detail": "无旁白且无声轨设计：全片必须数字静音"}
    else:
        audio_level = loudness(target) if has_audio else dict(no_audio)
    checks = {
        "frozenFrames": frozen,
        "picture": picture_metrics(frames),
        "subtitleContrast": subtitle_contrast(prepared["props"]["subtitle"]),
        "loudness": audio_level,
        "audioSync": sync,
        "claims": claims_check(prepared),
    }
    # 检查范围随报告保存，避免调用方把技术 pass 扩大解释为视觉通过。
    scopes = {
        "frozenFrames": ("decision", "sampled-frame-repetition"),
        "picture": ("measurement", "dark-levels-and-spatial-variation"),
        "subtitleContrast": ("decision", "configured-color-contrast"),
        "loudness": ("decision", "delivery-audio-loudness-and-peak"),
        "audioSync": ("decision", "track-duration-difference"),
        "claims": ("decision", "shot-window-coverage"),
    }
    for name, (kind, scope) in scopes.items():
        checks[name].update(kind=kind, scope=scope)
    # 所有分页都登记；单页入口只是第一页，不再额外生成会截断尾段的旧接触表。
    sheet = qa_dir.parent / inspection["sequence"]["pages"][0]

    def relative(path: Path) -> str:
        """记录相对作品根或输出根；两者对示例与正式作品都成立。"""
        for base in (root, output_root(root)):
            if path.is_relative_to(base):
                return path.relative_to(base).as_posix()
        return str(path)

    # 帧序列入口指向实际交付目录。
    observation_record = target.parent / "visual-notes.md"
    observation_path = relative(observation_record)
    report = {"schemaVersion": 1,
              "videoSha256": _video_digest(target),
              "preparedFingerprint": prepared["preparedFingerprint"],
              "video": str(target.relative_to(root).as_posix()) if target.is_relative_to(root) else str(target),
              "durationInFrames": prepared["durationInFrames"], "fps": fps,
              "sampleStep": step, "contactSheet": relative(sheet),
              "contactSheets": inspection["sequence"]["pages"],
              "scope": "technical-only",
              "inspection": inspection,
              "observation": {"status": "not-evaluated",
                              "record": observation_path,
                              "requiredChecks": ["composition", "material", "mobile-legibility",
                                                 "claim-visibility", "frame-sequence", "audio-candidate-review",
                                                 "rhythm-measurement"],
                              "detail": "技术结论不代表视觉完成；助手须复核帧序列与音频候选，无需连续播放或实际试听。"},
              "checks": checks,
              "status": "fail" if any(item.get("status") == "fail" for item in checks.values()) else "pass"}
    report_path = output_root(root) / "qa.json"
    _write_json(report_path, report)
    # 成片旁车记录 QA 指纹：交付、溯源与本次技术质检一一对应。
    sidecar = target.with_suffix(".provenance.json")
    if sidecar.is_file():
        provenance = json.loads(sidecar.read_text(encoding="utf-8"))
        provenance["qa"] = {"report": relative(report_path),
                            "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()}
        _write_json(sidecar, provenance)
    return report


def main(argv: list[str] | None = None) -> int:
    """`pnpm run qa --project <目录>`。"""
    import argparse
    parser = argparse.ArgumentParser(prog="pnpm run qa", description="通用技术 QA")
    parser.add_argument("--project", required=True)

    parser.add_argument("--video", help="待检查的成片；省略时取作品 outputs/video.mp4")
    parser.add_argument("--step", type=int, default=DEFAULT_STEP)
    args = parser.parse_args(argv)
    from film_runtime.core.project import load_project
    from film_runtime.types.scene_film.explainer_render import current
    root, manifest = load_project(args.project)
    prepared = current(root, manifest)
    report = run(root, prepared, video=Path(args.video) if args.video else None,
                 step=args.step)
    print(json.dumps({"status": report["status"], "scope": report["scope"],
                     "observation": report["observation"], "checks": {name: item.get("status", "measured")
                                                             for name, item in report["checks"].items()}},
                     ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1
