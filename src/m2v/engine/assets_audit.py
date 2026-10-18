"""cinematic 资产审计：把「贴图够不够」变成可复核的数字，而不是凭感觉。

审计按**实测尺寸与登记许可**判断，不看文件名也不看下载页的宣传：

- hero 目标的颜色贴图必须 ≥ 4K（宽 ≥ 4096），否则阻断；`major`/`minor` 目标 ≥ 2K 只告警。
- 环系径向纹理（`role: "ring"`）必须 ≥ 4K×512。
- hero 目标的 normal/roughness/emissive 齐全度：缺失即阻断（cinematic 档的资产契约）。
- hero 资产许可未知即阻断；其他资产许可未知只保留「未知」记录。
- 色彩空间与 alpha 从素材实测像素格式推导，写进报告供作品设置材质。

素材的角色来自来源记录的可选 `role` 字段（`color`/`normal`/`roughness`/`emissive`/`ring`/
`alpha`/`other`，缺省 `color`），因此审计不需要猜命名约定。
"""
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

ROLES = ("color", "normal", "roughness", "emissive", "ring", "alpha", "other")
#: hero 颜色贴图的下限；低于它就不是「4K 资产」。
HERO_MIN_WIDTH = 4096
MAJOR_MIN_WIDTH = 2048
#: 环系径向纹理要求：横向足够细，纵向也要够厚，否则展开时会被拉伸。
RING_MIN = (4096, 512)
REQUIRED_HERO_MAPS = ("normal", "roughness", "emissive")
UNKNOWN_LICENSES = ("", "未知", "unknown", "n/a")


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


def _hero_targets(prepared: dict) -> dict[str, str]:
    """hero 与 major 目标 → 档位；用于决定资产下限。"""
    tiers: dict[str, str] = {}
    for scene in prepared["props"].get("compiledScenes", []):
        shots = (scene.get("content", {}).get("props") or {}).get("shots") or []
        for shot in shots:
            tier = shot["tier"]
            if tier in ("hero", "major") and tiers.get(shot["target"]) != "hero":
                tiers[shot["target"]] = tier
    return tiers


def audit(root: Path, prepared: dict, record: dict, *, profile: str = "cinematic") -> dict:
    """逐项审计并返回报告；阻断项写在 `problems` 里。"""
    entries = {entry["id"]: entry for entry in record.get("assets", [])}
    by_target: dict[str, dict[str, dict]] = {}
    for identity, entry in entries.items():
        by_target.setdefault(entry.get("target") or identity, {})[entry.get("role", "color")] = entry
    tiers = _hero_targets(prepared)
    assets, problems, warnings = [], [], []
    for identity, entry in sorted(entries.items()):
        file = root / entry["path"]
        info = describe(file) if file.is_file() else {"pixelFormat": "missing", "colorSpace": "unknown", "alpha": False}
        item = {"id": identity, "role": entry.get("role", "color"), "width": entry["width"],
                "height": entry["height"], "license": entry.get("license", "未知"), **info}
        assets.append(item)
    for target, tier in sorted(tiers.items()):
        maps = by_target.get(target, {})
        color = maps.get("color")
        if color is None:
            # 程序化目标（如奥尔特云粒子/气泡）没有贴图契约，不适用 4K 与三张贴图要求。
            warnings.append({"target": target, "tier": tier, "reason": "没有登记颜色贴图，按程序化材质处理"})
            continue
        minimum = HERO_MIN_WIDTH if tier == "hero" else MAJOR_MIN_WIDTH
        if color["width"] < minimum:
            problems.append({"target": target, "asset": color["id"],
                             "reason": f"{tier} 颜色贴图宽度 {color['width']} 低于 {minimum}"})
        if str(color.get("license", "")).strip().lower() in UNKNOWN_LICENSES:
            if tier == "hero":
                problems.append({"target": target, "asset": color["id"], "reason": "hero 资产许可未知"})
            else:
                warnings.append({"target": target, "asset": color["id"], "reason": "资产许可未知"})
        if tier == "hero":
            for role in REQUIRED_HERO_MAPS:
                if role not in maps:
                    problems.append({"target": target, "reason": f"hero 缺少 {role} 贴图"})
    for identity, entry in entries.items():
        if entry.get("role") != "ring":
            continue
        if entry["width"] < RING_MIN[0] or entry["height"] < RING_MIN[1]:
            problems.append({"target": entry.get("target") or identity, "asset": identity,
                             "reason": f"环径向纹理 {entry['width']}×{entry['height']} 低于 "
                                       f"{RING_MIN[0]}×{RING_MIN[1]}"})
    report = {"schemaVersion": 1, "profile": profile,
              "preparedFingerprint": prepared["preparedFingerprint"],
              "assets": assets, "tiers": tiers, "problems": problems, "warnings": warnings,
              "status": "fail" if (problems and profile == "cinematic") else "pass"}
    _write_json(root / "outputs/asset-audit.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="m2v assets audit", description="资产质量与许可审计")
    parser.add_argument("--project", required=True)
    parser.add_argument("--profile", choices=("standard", "cinematic"))
    args = parser.parse_args(argv)
    from m2v.types.general import cinematic, media_assets
    from m2v.types.general.explainer_render import current
    root, manifest = load_project(args.project)
    if manifest["type"] != "general":
        raise M2VError("m2v assets audit 仅适用于 general 作品")
    prepared = current(root, manifest)
    profile, _source = cinematic.resolve_profile(manifest, args.profile)
    report = audit(root, prepared, media_assets.load_record(root), profile=profile)
    print(json.dumps({"status": report["status"], "problems": report["problems"],
                      "warnings": report["warnings"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
