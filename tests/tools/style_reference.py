"""风格示例的并排基准与八项指标：可复算的证据，供冷审与归档。

参考侧取自已登记样片的采样帧（只读，不进成片），本片侧取自示例的 lookdev still。
全部处理走 ffmpeg，不引入新依赖。输出写到作品 outputs/（已被版本控制忽略）：

  <slug>/outputs/style-reference/compare-*.png   并排图，左参考右本片
  <slug>/outputs/style-reference/metrics.json    八项指标里可像素量测的那几项

用法：
  uv run python tests/tools/style_reference.py            # 两个示例都做
  uv run python tests/tools/style_reference.py fold       # 只做其中一个
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

REPO = Path(__file__).resolve().parents[2]
STYLES = REPO / "styles"
REFERENCE = Path(r"C:\D_Merged_From_D\project\third-party\vibe-knowledge-film\examples")

# 每个示例：叙事位置 → 参考帧与本片同一位置的帧。两边必须讲同一件事。
PAIRS = {
    "fold": {
        "dir": STYLES / "vibe-night" / "examples" / "fold",
        "pairs": [
            ("chain", REFERENCE / "fold_C/review/s_0005.90.png", "still-000055.png"),
            ("fold", REFERENCE / "fold_C/review/s_0018.10.png", "still-000495.png"),
            ("sickle", REFERENCE / "fold_C/review/s_0005.90.png", "still-000275.png"),
        ],
    },
    "pigeon": {
        "dir": STYLES / "vibe-fable" / "examples" / "pigeon",
        "pairs": [
            ("feeder", REFERENCE / "pigeon_B/review/f_8.0.png", "still-000247.png"),
            ("wander", REFERENCE / "pigeon_B/review/f_16.0.png", "still-000412.png"),
            ("repeat", REFERENCE / "pigeon_B/review/f_21.5.png", "still-000742.png"),
        ],
    },
}

SIDE = 800
# 缩小到 480×270 再做统计：与手机观看尺度接近，又保留得下珠子上的高光。
SAMPLE = (480, 270)


def ffmpeg(*args: str) -> bytes:
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", *args],
                            capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[:400])
    return result.stdout


def rgb_sample(path: Path) -> list[tuple[int, int, int]]:
    """把一帧缩到 SAMPLE 尺寸，取原始 RGB 三元组。"""
    raw = ffmpeg("-i", str(path), "-vf", f"scale={SAMPLE[0]}:{SAMPLE[1]}",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-")
    expected = SAMPLE[0] * SAMPLE[1] * 3
    if len(raw) != expected:
        raise RuntimeError(f"{path.name}: 期望 {expected} 字节，实际 {len(raw)}")
    return [tuple(raw[index:index + 3]) for index in range(0, len(raw), 3)]


def luma(pixel: tuple[int, int, int]) -> float:
    return 0.2126 * pixel[0] + 0.7152 * pixel[1] + 0.0722 * pixel[2]


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def metrics(path: Path) -> dict:
    """八项指标里可以纯像素测的那些；线宽、光源方向与剪辑节奏仍靠人工判读。"""
    pixels = rgb_sample(path)
    width, height = SAMPLE
    lum = [luma(pixel) for pixel in pixels]
    background = median(lum)
    content = [(index % width, index // width) for index, value in enumerate(lum)
               if value > max(background + 18, 45)]
    if content:
        xs = [x for x, _ in content]
        ys = [y for _, y in content]
        subject_w, subject_h = (max(xs) - min(xs)) / width, (max(ys) - min(ys)) / height
    else:
        subject_w = subject_h = 0.0
    # 空场率：四角 40×40 的中位亮度为底，与底距离超过 24 的像素算内容。
    corner = [lum[y * width + x] for y in list(range(40)) + list(range(height - 40, height))
              for x in list(range(40)) + list(range(width - 40, width))]
    base = median(corner)
    empty = sum(1 for value in lum if abs(value - base) <= 24) / len(lum)
    saturation = [(max(p) - min(p)) / max(max(p), 1) for p in pixels if max(p) > 10]
    highlight = sum(1 for value in lum if value > 160) / len(lum)
    # 背景质感：四角 40×40 的局部亮度标准差，取四角均值。
    textures = []
    for ox, oy in ((0, 0), (width - 40, 0), (0, height - 40), (width - 40, height - 40)):
        block = [lum[(oy + y) * width + ox + x] for y in range(40) for x in range(40)]
        mean = sum(block) / len(block)
        textures.append((sum((value - mean) ** 2 for value in block) / len(block)) ** 0.5)
    return {
        "backgroundLuma": round(background, 1),
        "subjectWidthRatio": round(subject_w, 4),
        "subjectHeightRatio": round(subject_h, 4),
        "emptyRatio": round(empty, 4),
        "highlightRatio": round(highlight, 4),
        "meanSaturation": round(sum(saturation) / len(saturation), 4),
        "cornerTexture": round(sum(textures) / len(textures), 2),
    }


def side_by_side(reference: Path, ours: Path, target: Path) -> None:
    """左参考、右本片，各自缩到 800 宽；用 ffmpeg 的 hstack 拼。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", str(reference), "-i", str(ours),
           "-filter_complex", f"[0:v]scale={SIDE}:-2[a];[1:v]scale={SIDE}:-2[b];[a][b]hstack",
           "-frames:v", "1", "-y", str(target))


def main(argv: list[str]) -> int:
    wanted = argv or list(PAIRS)
    for slug in wanted:
        entry = PAIRS[slug]
        stills = entry["dir"] / "outputs" / "lookdev"
        if not stills.is_dir():
            print(f"缺少 lookdev 产物：{stills}", file=sys.stderr)
            return 2
        out = entry["dir"] / "outputs" / "style-reference"
        out.mkdir(parents=True, exist_ok=True)
        rows = {}
        for name, reference, still in entry["pairs"]:
            ours = stills / still
            if not ours.is_file():
                print(f"缺少本片帧：{ours}", file=sys.stderr)
                return 2
            side_by_side(reference, ours, out / f"compare-{name}.png")
            rows[name] = {"reference": metrics(reference), "ours": metrics(ours),
                          "files": {"reference": reference.name, "ours": still}}
        (out / "metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
        print(f"{slug}: {len(rows)} 组对照写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
