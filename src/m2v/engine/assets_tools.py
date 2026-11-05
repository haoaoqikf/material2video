"""素材台账与候选接触表：制作期只读检查，不参与准备与渲染。

``m2v assets audit`` 是绑定准备指纹的交付前审计；本模块补两条制作期命令：

- ``report``：把 ``assets/media-sources.json``、场景里的 ``useMediaAsset`` 引用与
  ``SOURCES.md`` 放在一起交叉核对，回答“登记了没引用 / 引用了没登记 / 许可与
  来源缺没缺 / 文件与摘要还对得上吗”。
- ``contact-sheet``：把候选视频按时刻抽帧、或把多张候选图片拼成一张带序号的
  接触表，让“建立—动作—结果”能在一次查看里被检查，而不是反复拖进度条。

两者都只读输入，不导入素材、不改来源记录、不写准备指纹。许可未知仅提示，
明确禁止当前用途与条件未满足按共享政策报告错误。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFont

from m2v.core.errors import M2VError
from m2v.core.project import _write_json, load_project
from m2v.core import media_policy

RECORD = "assets/media-sources.json"
MEDIA_DIR = "assets/media"
REPORT = "outputs/assets-report.json"
#: 与 ``media_assets.SUFFIXES`` 保持同一组可用扩展名；这里只用于判断候选类型。
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
UNKNOWN = media_policy.UNKNOWN_LICENSES

_LITERAL_CALL = re.compile(r"useMediaAsset\s*\(\s*[\"'`]([A-Za-z0-9_-]{1,80})[\"'`]\s*\)")
_ANY_CALL = re.compile(r"useMediaAsset\s*\(")
_BACKTICK = re.compile(r"`([A-Za-z0-9_-]{1,80})`")
_DURATION = re.compile(r"Duration: (\d+):(\d+):([\d.]+)")


# --------------------------------------------------------------------------- 报告


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_record(root: Path) -> dict:
    file = root / RECORD
    if not file.exists():
        return {"schemaVersion": 1, "assets": []}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise M2VError(f"素材来源记录无效：{exc}") from exc
    if data.get("schemaVersion") != 1 or not isinstance(data.get("assets"), list):
        raise M2VError("素材来源记录结构无效：需要 schemaVersion 1 与 assets 列表")
    return data


def _scan_usage(root: Path) -> tuple[set[str], bool, str]:
    """扫描场景里的 ``useMediaAsset`` 与全部场景文本。

    返回直接字面量调用、是否存在动态调用、以及拼接后的场景源码。包装组件常把
    ``id`` 当 props 传进 ``<Media id="x" />``，调用点只看到 ``useMediaAsset(id)``；
    因此「是否被引用」还要看 ID 是否以引号字面量出现在场景源码里，而「未登记
    引用」只认显式的 ``useMediaAsset("x")``，避免把普通字符串误判成素材。
    """
    used: set[str] = set()
    dynamic = False
    chunks: list[str] = []
    scenes = root / "scenes"
    if not scenes.is_dir():
        return used, dynamic, ""
    for path in sorted({*scenes.rglob("*.tsx"), *scenes.rglob("*.ts")}):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise M2VError(f"无法读取场景源码 {path.name}：{exc}") from exc
        chunks.append(text)
        used.update(_LITERAL_CALL.findall(text))
        for match in _ANY_CALL.finditer(text):
            if not _LITERAL_CALL.match(text, match.start()):
                dynamic = True
    return used, dynamic, "\n".join(chunks)


def _quoted(identity: str, text: str) -> bool:
    return any(f"{quote}{identity}{quote}" in text for quote in ('"', "'", "`"))


def _mentioned(path: Path | None) -> set[str] | None:
    if path is None or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise M2VError(f"无法读取来源表 {path.name}：{exc}") from exc
    return set(_BACKTICK.findall(text))


def build_report(root: Path, *, sources: Path | None = None) -> dict:
    """交叉核对素材记录、场景引用与来源表；返回可写入 JSON 的报告。"""
    record = _load_record(root)
    entries = [item for item in record["assets"] if isinstance(item, dict)]
    calls, dynamic, scene_text = _scan_usage(root)
    media_root = (root / MEDIA_DIR).resolve()
    sources_path = sources if sources is not None else (
        root / "SOURCES.md" if (root / "SOURCES.md").is_file() else None)
    mentioned = _mentioned(sources_path)

    assets, problems, warnings = [], [], []
    registered: set[str] = set()
    digests: dict[str, list[str]] = {}

    for entry in entries:
        identity = str(entry.get("id") or "")
        if not identity:
            problems.append({"code": "missing-id", "message": "素材记录存在缺少 id 的条目"})
            continue
        registered.add(identity)
        relative = entry.get("path")
        file = (root / relative).resolve() if isinstance(relative, str) else None
        exists = bool(file and file.is_file())
        inside = bool(file and file.is_relative_to(media_root))
        sha_ok = bool(exists and inside and isinstance(entry.get("sha256"), str)
                      and _sha256(file) == entry["sha256"])
        license_value = str(entry.get("license") or "未知").strip()
        author_known = str(entry.get("author") or "未知").strip().lower() not in UNKNOWN
        source_known = str(entry.get("sourceUrl") or "未知").strip().lower() not in UNKNOWN
        width, height = entry.get("width"), entry.get("height")
        dimensions_ok = (isinstance(width, int) and isinstance(height, int)
                         and width > 0 and height > 0)

        item = {
            "id": identity,
            "path": relative if isinstance(relative, str) else None,
            "kind": entry.get("kind"),
            "license": license_value,
            "author": entry.get("author") or "未知",
            "sourceUrl": entry.get("sourceUrl") or "未知",
            "fileExists": exists,
            "insideMediaDir": inside,
            "sha256Matches": sha_ok,
            "dimensions": [width, height],
            "referenced": identity in calls or _quoted(identity, scene_text),
            "sourcesMentioned": (identity in mentioned) if mentioned is not None else None,
            "issues": [],
        }

        def problem(code: str, message: str) -> None:
            problems.append({"code": code, "asset": identity, "message": message})
            item["issues"].append({"severity": "error", "code": code, "message": message})

        def warning(code: str, message: str) -> None:
            warnings.append({"code": code, "asset": identity, "message": message})
            item["issues"].append({"severity": "warning", "code": code, "message": message})

        if not isinstance(relative, str) or not relative:
            problem("missing-path", f"素材 {identity or '（无 ID）'} 缺少 path")
        elif not inside:
            problem("path-outside-media", f"素材 {identity} 的路径不在 {MEDIA_DIR}/ 内")
        elif not exists:
            problem("missing-file", f"素材文件缺失：{relative}")
        elif not sha_ok:
            problem("sha-mismatch", f"素材 {identity} 与来源记录不符，请重新导入")
        if not dimensions_ok:
            problem("invalid-dimensions", f"素材 {identity} 的宽高无效")
        try:
            metadata, errors, notes = media_policy.assess(entry)
            item.update(metadata)
            for error in errors:
                problem(error["code"], f"素材 {identity}：{error['message']}")
            for note in notes:
                warning(note["code"], f"素材 {identity}：{note['message']}")
        except M2VError as exc:
            problem("invalid-usage", f"素材 {identity} 采用元数据无效：{exc}")
        if not author_known:
            warning("author-unknown", f"素材 {identity} 作者未知")
        if not source_known:
            warning("source-unknown", f"素材 {identity} 来源页未知")
        if not item["referenced"]:
            warning("unused", f"登记素材 {identity} 未被场景引用；若为预留可忽略")
        if mentioned is not None and identity not in mentioned:
            warning("sources-missing", f"素材 {identity} 未出现在 {sources_path.name} 的素材表")
        if sha_ok:
            digests.setdefault(entry["sha256"], []).append(identity)
        assets.append(item)

    unregistered = sorted(calls - registered)
    for identity in unregistered:
        problems.append({"code": "used-not-registered", "asset": identity,
                         "message": f"场景引用了未登记素材 {identity}；请先 assets import"})
    unused = sorted(item["id"] for item in assets if not item["referenced"])
    referenced = sum(1 for item in assets if item["referenced"])

    duplicates = [{"sha256": sha, "ids": ids} for sha, ids in digests.items() if len(ids) > 1]
    for item in duplicates:
        warnings.append({"code": "duplicate-file",
                         "message": f"多个 ID 引用同一文件：{'、'.join(item['ids'])}"})

    if dynamic and unused:
        warnings.append({"code": "dynamic-usage",
                         "message": "存在非字面量 useMediaAsset 调用；未引用清单可能不完整"})

    return {
        "schemaVersion": 1,
        "project": root.name,
        "status": "fail" if problems else "pass",
        "notice": "制作期台账；不替代 prepare 与 assets audit。",
        "summary": {
            "registered": len(registered),
            "referenced": referenced,
            "errors": len(problems),
            "warnings": len(warnings),
        },
        "assets": assets,
        "unregistered": unregistered,
        "unused": unused,
        "duplicates": duplicates,
        "dynamicUsage": dynamic,
        "sources": None if sources_path is None else {
            "path": sources_path.name,
            "missing": sorted(registered - mentioned) if mentioned is not None else [],
        },
        "problems": problems,
        "warnings": warnings,
    }


def report_main(*, project: str, sources: str | None = None, as_json: bool = False) -> int:
    root, manifest = load_project(project)
    if manifest["type"] != "general":
        raise M2VError("m2v assets report 仅适用于 general 作品")
    source_path = None
    if sources:
        candidate = Path(sources).expanduser()
        source_path = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if source_path is not None and not source_path.is_file():
        raise M2VError(f"来源表不存在：{source_path}")
    report = build_report(root, sources=source_path)
    _write_json(root / REPORT, report)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"素材台账：{root}（登记 {summary['registered']}，引用 {summary['referenced']}，"
              f"错误 {summary['errors']}，警告 {summary['warnings']}）")
        for item in report["problems"]:
            print(f"  [错误] {item['message']}")
        for item in report["warnings"]:
            print(f"  [警告] {item['message']}")
        print("  说明：本报告是制作期台账，不替代 prepare 与 assets audit。")
        print(f"  报告：{REPORT}")
    return 0 if report["status"] == "pass" else 1


# ----------------------------------------------------------------------- 接触表


def _media_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    raise M2VError(f"不支持的候选类型：{path.name}（仅图片与视频）")


def _duration(path: Path) -> float:
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=60)
    match = _DURATION.search(result.stderr)
    if match is None:
        raise M2VError(f"无法读取视频时长：{path.name}")
    hours, minutes, seconds = (float(part) for part in match.groups())
    value = hours * 3600 + minutes * 60 + seconds
    if value <= 0:
        raise M2VError(f"视频时长无效：{path.name}")
    return value


def _extract_frame(video: Path, seconds: float, target: Path) -> None:
    result = subprocess.run(
        [get_ffmpeg_exe(), "-y", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video),
         "-frames:v", "1", str(target)], capture_output=True, timeout=120)
    if result.returncode or not target.is_file() or target.stat().st_size == 0:
        detail = result.stderr.decode("utf-8", "replace")[-400:]
        raise M2VError(f"抽帧失败：{video.name} @ {seconds:.2f}s（{detail}）")


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # 旧版 Pillow 不支持 load_default(size=...)
        return ImageFont.load_default()


def _check_times(times: list[float], duration: float, name: str) -> list[float]:
    if not times:
        raise M2VError("视频至少需要一个取帧时刻")
    for value in times:
        if value < 0 or value >= duration:
            raise M2VError(f"取帧时刻 {value:.2f}s 超出 {name} 的时长 {duration:.2f}s")
    return times


def _even_times(duration: float, samples: int) -> list[float]:
    return [min(duration - 0.01, duration * (index + 0.5) / samples) for index in range(samples)]


def contact_sheet(inputs: list[Path], *, times: list[float] | None = None, samples: int = 6,
                  columns: int = 3, tile_width: int = 480, out: Path | None = None,
                  project_root: Path | None = None) -> dict:
    """拼一张带序号的接触表并写同名 JSON 索引。

    图片按传入顺序各占一格；视频按显式时刻抽帧，未给时刻时均匀取样。一次最多
    一个视频，避免“每段视频各取几帧”的语义含糊。
    """
    files = [Path(item).expanduser().resolve() for item in inputs]
    if not 1 <= len(files) <= 24:
        raise M2VError("contact-sheet 需要 1～24 个候选文件")
    if not 1 <= columns <= 8:
        raise M2VError("--columns 必须为 1～8")
    if not 1 <= samples <= 60:
        raise M2VError("--samples 必须为 1～60")
    if not 160 <= tile_width <= 1920:
        raise M2VError("--tile-width 必须为 160～1920")
    for path in files:
        if not path.is_file():
            raise M2VError(f"候选文件不存在：{path}")
    kinds = [_media_kind(path) for path in files]
    videos = [path for path, kind in zip(files, kinds) if kind == "video"]
    if len(videos) > 1:
        raise M2VError("contact-sheet 一次只接受一个视频；多段候选请分别生成")
    if times and not videos:
        raise M2VError("--times 只适用于视频；图片候选按传入顺序拼格")

    target = out.expanduser().resolve() if out else (
        (project_root / "outputs/qa/contact-sheet.png") if project_root
        else files[0].parent / "contact-sheet.png")
    if target.suffix.lower() != ".png":
        raise M2VError("--out 必须是以 .png 结尾的路径")
    target.parent.mkdir(parents=True, exist_ok=True)
    index_path = target.with_suffix(".json")

    frames: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="m2v-contact-", dir=target.parent) as temporary:
        work = Path(temporary)
        if videos:
            video = videos[0]
            duration = _duration(video)
            chosen = _check_times(times, duration, video.name) if times else _even_times(duration, samples)
            for index, seconds in enumerate(chosen):
                frame = work / f"frame-{index:03d}.png"
                _extract_frame(video, seconds, frame)
                frames.append({"input": video, "seconds": seconds, "file": frame})
        for path in files:
            if path not in videos:
                frames.append({"input": path, "seconds": None, "file": path})

        images = []
        for frame in frames:
            try:
                with Image.open(frame["file"]) as opened:
                    images.append(opened.convert("RGB").copy())
            except (OSError, ValueError) as exc:
                raise M2VError(f"候选无法读取：{frame['input'].name}（{exc}）") from exc

        widest = max(image.width / image.height for image in images)
        cell_width = tile_width
        cell_height = max(160, min(1600, round(tile_width / widest)))
        gap = 8
        cols = min(columns, len(images))
        rows = math.ceil(len(images) / cols)
        sheet = Image.new("RGB", (cols * cell_width + (cols + 1) * gap,
                                  rows * cell_height + (rows + 1) * gap), (17, 17, 17))
        draw = ImageDraw.Draw(sheet)
        font = _font(max(14, tile_width // 24))
        tiles = []
        for position, (frame, image) in enumerate(zip(frames, images)):
            image.thumbnail((cell_width, cell_height), Image.LANCZOS)
            col, row = position % cols, position // cols
            x = gap + col * (cell_width + gap) + (cell_width - image.width) // 2
            y = gap + row * (cell_height + gap) + (cell_height - image.height) // 2
            sheet.paste(image, (x, y))
            label = str(position + 1)
            box = draw.textbbox((0, 0), label, font=font)
            draw.rectangle([x + 6, y + 6, x + 6 + (box[2] - box[0]) + 10,
                            y + 6 + (box[3] - box[1]) + 10], fill=(0, 0, 0))
            draw.text((x + 11, y + 9), label, font=font, fill=(241, 236, 221))
            tiles.append({
                "index": position + 1,
                "input": frame["input"].name,
                "timeSeconds": None if frame["seconds"] is None
                else round(float(frame["seconds"]), 3),
                "sourceWidth": image.width,
                "sourceHeight": image.height,
            })
        temporary_png = work / "contact-sheet.png"
        sheet.save(temporary_png, format="PNG")
        temporary_png.replace(target)

    index = {
        "schemaVersion": 1,
        "output": target.name,
        "columns": cols,
        "rows": rows,
        "cell": {"width": cell_width, "height": cell_height},
        "tiles": tiles,
    }
    _write_json(index_path, index)
    return {**index, "output": str(target), "index": str(index_path)}


def contact_main(*, project: str | None, inputs: list[str], times: str | None = None,
                 samples: int = 6, columns: int = 3, tile_width: int = 480,
                 out: str | None = None, as_json: bool = False) -> int:
    if not inputs:
        raise M2VError("contact-sheet 需要至少一个 --input")
    project_root = load_project(project)[0] if project else None
    parsed = None
    if times:
        try:
            parsed = [float(item) for item in re.split(r"[,，\s]+", times.strip()) if item]
        except ValueError as exc:
            raise M2VError("--times 需要逗号分隔的秒数，例如 --times 0,2.5,6") from exc
        if not parsed:
            raise M2VError("--times 不能为空")
    result = contact_sheet([Path(item) for item in inputs], times=parsed, samples=samples,
                           columns=columns, tile_width=tile_width,
                           out=Path(out) if out else None, project_root=project_root)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"接触表：{result['output']}")
        print(f"索引：{result['index']}（{len(result['tiles'])} 格，{result['columns']} 列）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="m2v assets tools", description="素材台账与候选接触表")
    parser.add_argument("workflow", choices=("report", "contact-sheet"))
    parser.add_argument("--project")
    parser.add_argument("--sources", help="report 的 SOURCES.md 路径")
    parser.add_argument("--input", action="append", dest="inputs", metavar="FILE")
    parser.add_argument("--times")
    parser.add_argument("--samples", type=int, default=6)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--tile-width", type=int, default=480)
    parser.add_argument("--out")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.workflow == "report":
            if not args.project:
                raise M2VError("report 需要 --project")
            return report_main(project=args.project, sources=args.sources, as_json=args.json)
        return contact_main(project=args.project, inputs=args.inputs or [], times=args.times,
                            samples=args.samples, columns=args.columns,
                            tile_width=args.tile_width, out=args.out, as_json=args.json)
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[error] 参数或材料错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
