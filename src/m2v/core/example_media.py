"""按固定配方恢复示例输入；不改变来源登记，不接受摘要漂移。"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

from imageio_ffmpeg import get_ffmpeg_exe

logger = logging.getLogger(__name__)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Material2Video/1.0 (educational video)"})
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as stream:
        shutil.copyfileobj(response, stream, 1024 * 1024)


def encode(source: Path, target: Path, transform: str) -> None:
    executable = get_ffmpeg_exe()
    version = subprocess.check_output([executable, "-version"], text=True).splitlines()[0]
    if version != "ffmpeg version 7.1-essentials_build-www.gyan.dev Copyright (c) 2000-2024 the FFmpeg developers":
        raise RuntimeError("精确恢复转换素材需要原编码器 ffmpeg 7.1-essentials_build-www.gyan.dev；请通过 IMAGEIO_FFMPEG_EXE 指定")
    args = [executable, "-y", "-v", "error"]
    if transform == "moon-continuous-silent":
        args += ["-ss", "84.25", "-i", str(source), "-t", "10", "-an", "-vf", "setpts=PTS/0.75",
                 "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p"]
    elif transform == "jpeg-q3":
        args += ["-i", str(source), "-frames:v", "1", "-q:v", "3"]
    elif transform == "tiff-png":
        args += ["-i", str(source), "-frames:v", "1"]
    elif transform == "specular-roughness":
        args += ["-i", str(source), "-vf", "lutrgb=r=235-val*0.8:g=235-val*0.8:b=235-val*0.8", "-frames:v", "1"]
    else:
        raise ValueError(f"未知转换：{transform}")
    subprocess.run([*args, str(target)], check=True)


def validate(path: Path, entry: dict) -> None:
    if digest(path) != entry["sha256"]:
        raise RuntimeError(f"素材 {entry['id']} SHA-256 不符；不更换来源或更新预期摘要")
    from m2v.types.scene_film.media_assets import probe
    info = probe(path, entry["kind"])
    if (info["width"], info["height"]) != (entry["width"], entry["height"]):
        raise RuntimeError(f"素材 {entry['id']} 尺寸与登记不符")
    if entry["kind"] == "video" and abs(info["durationSeconds"] - entry["durationSeconds"]) > .05:
        raise RuntimeError(f"素材 {entry['id']} 时长与登记不符")


def restore(root: Path, generate: Callable[[dict, Path], None] | None = None,
            *, fetch: Callable[[str, Path], None] = download) -> None:
    """恢复 ``root`` 下登记的示例媒体。

    已存在且摘要、尺寸、时长与登记一致的文件直接复用；其余项先在临时目录完成
    下载（或生成）、转换和校验，全部通过后才安装，失败时不改动已有素材。
    """
    root = root.resolve()
    record = json.loads((root / "assets/media-sources.json").read_text(encoding="utf-8"))
    recipe = json.loads((root / "assets/recipe.json").read_text(encoding="utf-8"))
    if record.get("schemaVersion") != 1 or recipe.get("schemaVersion") != 1:
        raise ValueError("恢复配方与来源登记的 schemaVersion 必须为 1")
    entries = {item["id"]: item for item in record["assets"]}
    recipes = {item["id"]: item for item in recipe["assets"]}
    if len(entries) != len(record["assets"]) or len(recipes) != len(recipe["assets"]) or entries.keys() != recipes.keys():
        raise ValueError("恢复配方与登记 ID 必须唯一且完整对应")
    pending = []
    reused = 0
    seen: dict[Path, str] = {}
    for identity, entry in entries.items():
        relative = Path(entry["path"])
        target = (root / relative).resolve()
        if relative.is_absolute() or not target.is_relative_to(root / "assets/media"):
            raise ValueError(f"媒体路径越界：{identity}")
        if recipes[identity]["expectedSha256"] != entry["sha256"]:
            raise ValueError(f"配方与登记摘要不一致：{identity}")
        # 多个 ID 可复用同一内容寻址文件；同一目标只恢复一次。
        if target in seen:
            if seen[target] != entry["sha256"]:
                raise ValueError(f"同一路径登记了不同内容：{identity}")
            continue
        seen[target] = entry["sha256"]
        if target.is_file() and digest(target) == entry["sha256"]:
            validate(target, entry)
            reused += 1
            logger.info("缓存命中：%s", identity)
        else:
            pending.append((entry, target))
    # 全部下载、生成和校验成功才安装；中途失败不动已有文件。
    with tempfile.TemporaryDirectory(prefix="m2v-example-") as temporary:
        work = Path(temporary)
        staged = []
        for entry, target in pending:
            identity = entry["id"]
            item = recipes[identity]
            output = work / (identity + target.suffix)
            logger.info("恢复素材：%s", identity)
            if item["transform"] == "generate":
                if generate is None:
                    raise ValueError(f"缺少生成器：{identity}")
                generate(item, output)
            else:
                url = item.get("downloadUrl")
                if not url:
                    raise ValueError(f"配方缺少下载地址：{identity}")
                source = work / (identity + "-source" + Path(urllib.parse.urlsplit(url).path).suffix)
                fetch(url, source)
                if item["transform"] == "copy":
                    shutil.copyfile(source, output)
                else:
                    encode(source, output, item["transform"])
            if not output.is_file():
                raise RuntimeError(f"恢复未产出文件：{identity}")
            validate(output, entry)
            staged.append((output, target))
        for output, target in staged:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(output, target.with_suffix(target.suffix + ".partial"))
            target.with_suffix(target.suffix + ".partial").replace(target)
    logger.info("恢复完成：%d 项更新，%d 项复用", len(pending), reused)
