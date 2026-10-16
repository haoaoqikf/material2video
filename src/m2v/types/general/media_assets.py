"""助手搜索结果的导入边界：实测媒体、内容寻址及来源留证。

文章 v7 允许混合图片与视频镜头，素材由助手全网检索或从 Pexels、Pixabay 这类
可选图库获得。无论来源如何，进入作品的方式只有一条：先把候选写进导入清单，
由 ``m2v general assets import`` 下载或复制、实测真实类型与尺寸、按内容摘要命名
落盘，并把来源页、作者、许可与实测信息写进 ``assets/media-sources.json``。
准备与渲染只读本地文件，不联网取素材。
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from imageio_ffmpeg import get_ffmpeg_exe
from m2v.core.errors import M2VError
from m2v.core.project import _write_json, load_project
from m2v.core import security
from m2v.engine import media_probe
from m2v.engine.gallery import (
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TOLERANCE,
    MAX_DOWNLOAD_BYTES,
    PROVIDER_DEFAULTS,
    HttpTransport,
    build as build_gallery,
)
from m2v.engine.sound import asset_digest

logger = logging.getLogger(__name__)
RECORD = "assets/media-sources.json"
SUFFIXES = {"image": {".png", ".jpg", ".jpeg", ".webp"}, "video": {".mp4", ".mov", ".m4v", ".webm"}}
KINDS = ("video", "photo", "both")


def number(value, low, high, where):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise M2VError(f"{where}: 必须为 {low}～{high} 的有限数字")
    return value


def probe(path: Path, kind: str) -> dict:
    width, height = media_probe.probe_dimensions(path)
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=30)
    info = result.stderr
    is_image = bool(re.search(r"Input #0, (?:image2|png_pipe|jpeg_pipe|webp_pipe)", info))
    if is_image != (kind == "image"):
        raise M2VError(f"媒体类型不符：{path.name}，声明 {kind}")
    duration = None
    if kind == "video":
        match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
        if not match:
            raise M2VError(f"视频缺少有效时长：{path.name}")
        h, m, s = map(float, match.groups())
        duration = h * 3600 + m * 60 + s
        number(duration, .001, 86400, "媒体时长")
    # 验证首帧可解码；完整导出仍会执行全片媒体验收。
    decoded = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(path), "-map", "0:v:0",
                              "-frames:v", "1", "-f", "null", "-"], capture_output=True, timeout=30)
    if decoded.returncode:
        raise M2VError(f"媒体无法解码：{path.name}")
    return {"width": width, "height": height, "durationSeconds": duration}


def _http(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password


def import_assets(root: Path, manifest: dict, *, base: Path, transport=None, timeout_s=30) -> dict:
    """一批素材全部通过后发布记录；失败不会修改已有记录或已有素材。"""
    number(timeout_s, .01, 300, "timeoutSeconds")
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise M2VError("素材清单 schemaVersion 必须为 1")
    entries = manifest.get("assets")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 300:
        raise M2VError("assets 必须包含 1～300 项")
    prior = load_record(root)
    target_dir = root / "assets/media"
    target_dir.mkdir(parents=True, exist_ok=True)
    adopted = []
    transport = transport or HttpTransport()
    with tempfile.TemporaryDirectory(prefix="import-", dir=target_dir) as temporary:
        staged = []
        ids = set()
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict): raise M2VError(f"assets[{index}] 必须是对象")
            identity = entry.get("id")
            if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity) or identity in ids:
                raise M2VError(f"assets[{index}].id 无效或重复")
            ids.add(identity)
            try:
                kind = entry.get("kind")
                if kind not in SUFFIXES: raise M2VError("kind 必须为 image/video")
                local, remote = entry.get("localPath"), entry.get("mediaUrl")
                if bool(local) == bool(remote): raise M2VError("localPath/mediaUrl 必须二选一")
                origin = entry.get("sourceUrl") or "未知"
                if origin != "未知" and (not isinstance(origin, str) or not _http(origin)):
                    raise M2VError("sourceUrl 必须是公开网页地址")
                if remote and (not isinstance(remote, str) or not _http(remote)):
                    raise M2VError("mediaUrl 必须是 HTTP(S) 媒体直链")
                suffix = Path(local or urlsplit(remote).path).suffix.lower()
                if suffix not in SUFFIXES[kind]:
                    # 无扩展名 CDN 链接按类型命名，仍需实测，而不是相信 URL。
                    suffix = ".mp4" if kind == "video" else ".png"
                file = Path(temporary) / f"{identity}{suffix}"
                logger.info("导入素材 %s (%s)", identity, kind)
                if local:
                    source = (base / local).resolve()
                    if not source.is_file() or not 0 < source.stat().st_size <= MAX_DOWNLOAD_BYTES:
                        raise M2VError("本地素材缺失、为空或超过 256 MiB")
                    shutil.copyfile(source, file)
                else:
                    transport.download(remote, file, {}, timeout_s)
                if not 0 < file.stat().st_size <= MAX_DOWNLOAD_BYTES:
                    raise M2VError("下载素材为空或超过 256 MiB")
                info = probe(file, kind)
                sha = asset_digest(file)
                relative = f"assets/media/{sha}{suffix}"
                adopted.append({"id": identity, "path": relative, "kind": kind, **info, "sha256": sha,
                                "sourceUrl": origin, "mediaUrl": remote or "未知",
                                "author": entry.get("author") or "未知", "license": entry.get("license") or "未知"})
                staged.append((file, root / relative))
            except (M2VError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
                raise M2VError(f"素材 {identity} 导入失败：{exc}；请更换候选后重试") from exc
        for file, destination in staged:
            if not destination.exists() or asset_digest(destination) != asset_digest(file):
                security.deliver(file, destination)
    # 保留未被本批替换的 ID；相同文件可被多个素材 ID 引用。
    record = {"schemaVersion": 1, "assets": [e for e in prior["assets"] if e["id"] not in ids] + adopted}
    _write_json(root / RECORD, record)
    return record


def load_record(root: Path) -> dict:
    file = root / RECORD
    if not file.exists(): return {"schemaVersion": 1, "assets": []}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        if data.get("schemaVersion") != 1 or not isinstance(data.get("assets"), list): raise ValueError("结构无效")
        return data
    except (ValueError, OSError, AttributeError) as exc:
        raise M2VError(f"素材来源记录无效：{exc}") from exc


def validate_scene(root: Path, scene: dict) -> dict:
    from .explainer import local_file
    content = scene["content"]
    file = local_file(root, content.get("src"), "content.src")
    info = probe(file, scene["template"])
    mode = scene.get("aspectRatio", "canvas")
    if mode not in {"canvas", "any"}: raise M2VError("aspectRatio 必须为 canvas/any")
    if mode == "canvas" and abs(info["width"] / info["height"] / (1080/1920) - 1) > .02:
        raise M2VError(f"幕 {scene['id']} 素材比例不符；要求 9:16 ±2%，可显式设置 aspectRatio=any")
    if scene["template"] == "video":
        number(content.get("trimStartSeconds", 0), 0, info["durationSeconds"], "trimStartSeconds")
    else:
        number(content.get("photoZoom", 1), 1, 1.3, "photoZoom")
    relative = file.relative_to(root.resolve()).as_posix()
    matches = [e for e in load_record(root)["assets"] if e.get("path") == relative]
    if not matches:
        raise M2VError(f"幕 {scene['id']} 素材 {relative} 没有导入记录；请先执行 m2v general assets import 留证来源")
    for entry in matches:
        if entry.get("sha256") != asset_digest(file) or any(entry.get(k) != info[k] for k in info):
            raise M2VError(f"素材 {relative} 与来源记录不符，请重新导入")
    return info


def gallery_config(name: str, **overrides) -> dict:
    """文章画布固定 9:16，因此图库检索默认按画布比例与竖屏方向约束候选。"""
    defaults = PROVIDER_DEFAULTS.get(name)
    if defaults is None:
        raise M2VError(f"未知图库：{name}；当前可用：{'、'.join(sorted(PROVIDER_DEFAULTS))}")
    config = {"name": name, **defaults, "orientation": "portrait",
              "aspectRatio": "canvas", "aspectRatioTolerance": DEFAULT_TOLERANCE}
    config.update({key: value for key, value in overrides.items() if value is not None})
    return config


def search(root: Path, project: dict, *, provider_name="pexels", kind="both", queries=None,
           per_page=15, timeout_s=DEFAULT_TIMEOUT_SECONDS, transport=None) -> dict:
    """可选图库检索：只产出候选清单，不下载、不写作品文件。

    图库只是助手的一种来源；没有候选不算失败，助手可以改用其他公开媒体直链，
    再由 ``import`` 统一留证。
    """
    from . import explainer
    if kind not in KINDS:
        raise M2VError(f"kind 必须为 {'/'.join(KINDS)}")
    if type(per_page) is not int or not 1 <= per_page <= 80:
        raise M2VError("perPage 必须为 1～80 整数")
    number(timeout_s, .01, 300, "timeoutSeconds")
    source = explainer.load(root, project)
    if queries is None:
        queries = []
        for scene in source["scenes"]:
            words = scene.get("keywords")
            if not isinstance(words, list) or not words:
                raise M2VError(f"幕 {scene['id']} 未声明 keywords；请提供 --query 或先补充分镜关键词")
            queries.append(" ".join(words))
    if not isinstance(queries, list) or not queries or any(not isinstance(q, str) or not q.strip() for q in queries):
        raise M2VError("检索关键词必须是非空文本")
    if len(queries) != len(source["scenes"]):
        raise M2VError(f"关键词数量 {len(queries)} 与幕数 {len(source['scenes'])} 不一致")
    gallery = build_gallery(gallery_config(provider_name), transport,
                            cache_dir=root / "outputs/gallery-cache")
    kinds = ("video", "photo") if kind == "both" else (kind,)
    results = []
    for scene, query in zip(source["scenes"], queries):
        candidates = []
        for media in kinds:
            candidates.extend(gallery.search(query, media, per_page, timeout_s))
        results.append({"sceneId": scene["id"], "query": query,
                        "candidates": [item.to_json() for item in candidates]})
    return {"schemaVersion": 1, "provider": provider_name, "kind": kind, "queries": results}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m2v general assets", description="文章混合媒体素材的检索与导入")
    parser.add_argument("workflow", choices=("search", "import"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--provider", default="pexels", help="可选图库：pexels 或 pixabay")
    parser.add_argument("--kind", default="both", choices=KINDS)
    parser.add_argument("--query", action="append", dest="queries", help="按幕顺序提供关键词，可重复")
    parser.add_argument("--per-page", type=int, default=15)
    parser.add_argument("--manifest", help="导入清单路径")
    parser.add_argument("--base", help="清单里 localPath 的基准目录，默认作品目录")
    parser.add_argument("--timeout-seconds", type=float, default=None)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        root, project = load_project(args.project)
        if project["type"] != "general":
            raise M2VError("m2v general assets 仅适用于 general 作品")
        timeout_s = DEFAULT_TIMEOUT_SECONDS if args.timeout_seconds is None else args.timeout_seconds
        if args.workflow == "search":
            result = search(root, project, provider_name=args.provider, kind=args.kind,
                            queries=args.queries, per_page=args.per_page, timeout_s=timeout_s)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if not args.manifest:
            raise M2VError("import 需要 --manifest 指向导入清单")
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
        base = Path(args.base).expanduser().resolve() if args.base else root
        record = import_assets(root, manifest, base=base, timeout_s=timeout_s)
        print(f"已导入素材 {len(record['assets'])} 项；来源记录：{root / RECORD}")
        for entry in record["assets"]:
            size = f"{entry['width']}×{entry['height']}"
            duration = f"，{entry['durationSeconds']:.2f}s" if entry["durationSeconds"] else ""
            print(f"  {entry['id']}：{entry['path']}（{entry['kind']}，{size}{duration}，"
                  f"{entry['author']}，{entry['license']}）")
        return 0
    except M2VError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[error] 参数或材料错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
