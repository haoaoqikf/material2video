"""重新获取本示例的已审定输入；不在素材缺失时静默更换来源。"""
from __future__ import annotations

import json
import hashlib
import logging
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.types.general.media_assets import import_assets

logger = logging.getLogger(__name__)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    recipe = json.loads((root / "assets/recipe.json").read_text(encoding="utf-8"))
    entries = []
    with tempfile.TemporaryDirectory(prefix="m2v-science-") as temporary:
        work = Path(temporary)
        for item in recipe["assets"]:
            identity = item["id"]
            suffix = ".mp4" if item["kind"] == "video" else (".png" if item["id"] == "chatgpt-icon" else Path(item["downloadUrl"]).suffix)
            source = work / f"{identity}-original{suffix}"
            logger.info("获取 %s：%s", identity, item["downloadUrl"])
            request = urllib.request.Request(item["downloadUrl"], headers={"User-Agent": "Material2Video/1.0 (educational video)"})
            # 流式下载，避免原始档案文件整块载入内存。
            with urllib.request.urlopen(request, timeout=60) as response, source.open("wb") as target:
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
            transformed = work / f"{identity}{suffix}"
            if item["transform"] == "moon-continuous-silent":
                subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-ss", "84.25", "-i", str(source),
                                "-t", "10", "-an", "-vf", "setpts=PTS/0.75", "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                                "-pix_fmt", "yuv420p", str(transformed)], check=True)
            elif item["transform"] == "jpeg-q3":
                subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(source),
                                "-frames:v", "1", "-q:v", "3", str(transformed)], check=True)
            else:
                transformed = source
            with transformed.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != item["expectedSha256"]:
                raise RuntimeError(f"素材 {identity} 摘要变化；请核验源站内容或编码版本后更新配方，不自动替换")
            entry = {key: item[key] for key in ("id", "kind", "sourceUrl", "author", "license", "role")}
            entries.append({**entry, "localPath": transformed.name})
        # 所有下载成功后再统一导入。实测、摘要和来源登记由正式入口完成。
        import_assets(root, {"schemaVersion": 1, "assets": entries}, base=work)
    logger.info("已重新获取并导入 %d 项素材；若源站内容变化，请重新核验和prepare", len(entries))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
