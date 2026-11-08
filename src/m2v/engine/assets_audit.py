"""统一素材许可与原生尺寸审计，不用三维贴图配额替代实际用途复核。"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.core.project import _write_json, load_project
from m2v.core import media_policy

ROLES = ("color", "normal", "roughness", "emissive", "ring", "alpha", "other")


def _pixel_format(path: Path) -> str:
    """从 ffmpeg 的流信息里取像素格式，用它推导色彩空间与 alpha。"""
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                            capture_output=True, timeout=120)
    text = result.stderr.decode("utf-8", "replace")
    line = next((item for item in text.splitlines() if "Video:" in item and "Stream #" in item), "")
    match = re.search(r"\b(yuv[a-z0-9]*|yuva[a-z0-9]*|rgba?[a-z0-9]*|gray[a-z0-9]*|pal8|ya8)\b", line)
    return match.group(1) if match else "unknown"


def describe(path: Path) -> dict:
    """实测像素格式 → 色彩空间与 alpha；猜不出来时明确标注 unknown。"""
    pixel = _pixel_format(path)
    alpha = pixel.startswith(("yuva", "rgba", "ya"))
    color_space = "srgb" if pixel.startswith(("rgba", "rgb", "yuva", "yuv")) else "unknown"
    return {"pixelFormat": pixel, "colorSpace": color_space, "alpha": alpha}


def audit(root: Path, prepared: dict, record: dict) -> dict:
    """统一审计：所有素材检查许可和文件；清晰度保留人工屏幕用途复核。"""
    assets, problems, warnings = [], [], []
    for entry in record.get("assets", []):
        file = root / entry["path"]
        info = describe(file) if file.is_file() else {"pixelFormat": "missing", "colorSpace": "unknown", "alpha": False}
        item = {"id": entry["id"], "role": entry.get("role", "color"),
                "width": entry["width"], "height": entry["height"],
                "license": entry.get("license", "未知"), **info}
        assets.append(item)
        if not file.is_file():
            problems.append({"asset": entry["id"], "reason": "素材文件缺失"})
        try:
            metadata, errors, notes = media_policy.assess(entry)
            item.update(metadata)
            problems.extend({"asset": entry["id"], "code": error["code"], "reason": error["message"]}
                            for error in errors)
            warnings.extend({"asset": entry["id"], "code": note["code"], "reason": note["message"]}
                            for note in notes)
        except M2VError as exc:
            problems.append({"asset": entry["id"], "code": "invalid-usage", "reason": str(exc)})
        if min(item["width"], item["height"]) <= 0:
            problems.append({"asset": entry["id"], "reason": "素材尺寸无效"})
        else:
            warnings.append({"asset": entry["id"], "reason": "按原生尺寸与实际显示用途复核清晰度，不冒充4K"})
    report = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
              "assets": assets,
              "resolutionScope": "native-dimensions; screen-usage-not-evaluated",
              "problems": problems, "warnings": warnings,
              "status": "fail" if problems else "pass"}
    _write_json(root / "outputs/asset-audit.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="m2v assets audit", description="资产质量与许可审计")
    parser.add_argument("--project", required=True)

    args = parser.parse_args(argv)
    from m2v.types.scene_film import media_assets
    from m2v.standalone import executor
    root, manifest = load_project(args.project)

    prepared = executor.current(root, manifest)
    report = audit(root, prepared, media_assets.load_record(root))
    print(json.dumps({"status": report["status"], "problems": report["problems"],
                      "warnings": report["warnings"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
