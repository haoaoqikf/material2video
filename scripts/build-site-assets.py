"""Extract the static gallery's assets from existing local example videos."""

import json
import subprocess
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/site/assets"
FONT = ROOT / "fonts/files/NotoSansSC-Variable.ttf"
IMAGE_LIMIT = 300_000
CLIP_LIMIT = 3_000_000


@dataclass(frozen=True)
class Work:
    slug: str
    source: str
    poster_at: float
    clip_start: float | None = None
    clip_duration: int = 9

    @property
    def video(self) -> Path:
        return ROOT / "examples" / self.source


WORKS = (
    # 23/56.6/58/61/106s: Earth and Oort establish scale. At 58s Saturn's
    # rings and label both read clearly. 56.6–65.6s shows the edge-on reveal.
    Work("solar-system", "spatial-3d/solar-system-journey/outputs/video.mp4", 58, 56.6),
    # 13.6/14.7/16.7/18.9/21.8s: 18.9s has a settled gold 30% and a full
    # subtitle. Starting at 13.6s captures the rise from 10% and the first bar.
    Work("luck-on-stage", "principle-metaphor/luck-on-stage/outputs/video.mp4", 18.9, 13.6),
    # 19.6/22/24.5/27.5/34s: 19.6s is mostly empty. At 27.5s the gold
    # columns and bilingual subtitle are visible. 21–30s builds both halves.
    Work("compound", "data-evolution/compound-after-20/outputs/video.mp4", 27.5, 21),
    # 2.2/4.6/6.6/9/13.8s: the stable 6.6s first-flight frame has a clear
    # silhouette and title. 0.4–8.4s shows paper tape, telephone and flight,
    # then cuts to the next archival chapter before the clip ends.
    Work("american-science", "documentary-edit/american-science-milestones/outputs/video.mp4", 6.6, 0.4, 8),
    # 0.2/0.9/1.6s within the 1.93s preview: 0.9s shows both leaders in
    # their own cards. The preview is too short for a gallery clip.
    Work("market-cap", "data-evolution/global-market-cap-race-portrait/outputs/previews/video.mp4", 0.9),
)


def ffmpeg(*args: str) -> bytes:
    return subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def save_frame(video: Path, at: float, target: Path) -> None:
    data = ffmpeg(
        "-ss", str(at), "-i", str(video), "-map", "0:v:0", "-frames:v", "1",
        "-c:v", "png", "-threads", "1", "-f", "image2pipe", "pipe:1",
    )
    with Image.open(BytesIO(data)) as frame:
        frame = frame.convert("RGB")
        frame.thumbnail((1440, 1440), Image.Resampling.LANCZOS)
        frame.save(target, quality=80, optimize=True)


def save_clip(work: Work, start: float, target: Path) -> None:
    ffmpeg(
        "-ss", str(start), "-i", str(work.video), "-t", str(work.clip_duration),
        "-map", "0:v:0", "-an", "-vf",
        "scale=720:720:force_original_aspect_ratio=decrease:force_divisible_by=2",
        "-c:v", "libx264", "-crf", "28", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(target),
    )
    duration = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", str(target),
    ], text=True)
    if not 8 <= float(duration) <= 10:
        raise ValueError(f"{target.name}: {duration.strip()}s outside the 8–10s range")


def save_social_preview(directory: Path) -> None:
    canvas = Image.new("RGB", (1280, 640), "#11141c")
    draw = ImageDraw.Draw(canvas)
    brand = ImageFont.truetype(str(FONT), 32)
    brand.set_variation_by_name("SemiBold")
    headline = ImageFont.truetype(str(FONT), 50)
    headline.set_variation_by_name("Bold")
    draw.text((54, 57), "Material2Video", font=brand, fill="#bcb7ff")
    draw.multiline_text(
        (54, 213), "把文章、数据和\n素材做成可编辑的\n短视频。",
        font=headline, fill="#f5f4fa", spacing=13,
    )
    for name, size, position in (
        ("hero.jpg", (640, 360), (586, 42)),
        ("poster-luck-on-stage.jpg", (312, 176), (586, 418)),
        ("poster-compound.jpg", (312, 176), (914, 418)),
    ):
        with Image.open(directory / name) as frame:
            canvas.paste(ImageOps.fit(frame, size, Image.Resampling.LANCZOS), position)
    canvas.save(directory / "social-preview.png", optimize=True)


def main() -> None:
    sources = [FONT, *(work.video for work in WORKS)]
    missing = [path.relative_to(ROOT).as_posix() for path in sources if not path.is_file()]
    if missing:
        raise SystemExit("Missing gallery inputs:\n  " + "\n  ".join(missing))

    ASSETS.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".site-assets-", dir=ROOT) as staging:
        directory = Path(staging)
        for work in WORKS:
            save_frame(work.video, work.poster_at, directory / f"poster-{work.slug}.jpg")
            if work.clip_start is not None:
                save_clip(work, work.clip_start, directory / f"clip-{work.slug}.mp4")
        # At 64s the rings fill the frame and no subtitle band is burned in; 61s
        # carried the second half of a two-line caption ("从侧面到全貌，").
        save_frame(WORKS[0].video, 64, directory / "hero.jpg")
        save_social_preview(directory)

        outputs = sorted(directory.iterdir())
        for output in outputs:
            limit = CLIP_LIMIT if output.suffix == ".mp4" else IMAGE_LIMIT
            if (size := output.stat().st_size) > limit:
                raise ValueError(f"{output.name}: {size:,} bytes exceeds {limit:,}")
        for output in outputs:
            destination = ASSETS / output.name
            output.replace(destination)
            print(f"{destination.relative_to(ROOT).as_posix()}  {destination.stat().st_size:>9,} bytes")


if __name__ == "__main__":
    main()
