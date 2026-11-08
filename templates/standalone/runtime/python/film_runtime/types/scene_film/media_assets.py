"""作品本地媒体登记、复制或下载、实测及摘要复核；渲染只使用已登记本地资源。"""
from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from imageio_ffmpeg import get_ffmpeg_exe
from film_runtime.core.errors import VideoError
from film_runtime.core.project import _write_json, load_project, _local_reference
from film_runtime.core import security, media_policy
from film_runtime.core import frames
from film_runtime.engine import media_probe
from film_runtime.core.media_policy import MEDIA_ROLES as ROLES
from film_runtime.engine.http_transport import HttpTransport, MAX_DOWNLOAD_BYTES
from film_runtime.core.validate import number
from film_runtime.engine.sound import asset_digest

logger = logging.getLogger(__name__)
RECORD = "assets/media-sources.json"
MEDIA_DIR = "assets/media"
#: 代码场景取已登记素材的 URL 前缀；服务器只在这个前缀下暴露白名单文件。
MEDIA_URL_PREFIX = "/media"
SUFFIXES = {"image": {".png", ".jpg", ".jpeg", ".webp"}, "video": {".mp4", ".mov", ".m4v", ".webm"}}
KINDS = ("video", "photo", "both")


def probe(path: Path, kind: str) -> dict:
    width, height = media_probe.probe_dimensions(path)
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=30)
    info = result.stderr
    is_image = bool(re.search(r"Input #0, (?:image2|png_pipe|jpeg_pipe|webp_pipe)", info))
    if is_image != (kind == "image"):
        raise VideoError(f"媒体类型不符：{path.name}，声明 {kind}")
    duration = None
    if kind == "video":
        match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
        if not match:
            raise VideoError(f"视频缺少有效时长：{path.name}")
        h, m, s = map(float, match.groups())
        duration = h * 3600 + m * 60 + s
        number(duration, .001, 86400, "媒体时长")
    # 验证首帧可解码；完整导出仍会执行全片媒体验收。
    decoded = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(path), "-map", "0:v:0",
                              "-frames:v", "1", "-f", "null", "-"], capture_output=True, timeout=30)
    if decoded.returncode:
        raise VideoError(f"媒体无法解码：{path.name}")
    return {"width": width, "height": height, "durationSeconds": duration}


def _http(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password


def import_assets(root: Path, manifest: dict, *, base: Path, transport=None, timeout_s=30) -> dict:
    """一批素材全部通过后发布记录；失败不会修改已有记录或已有素材。"""
    number(timeout_s, .01, 300, "timeoutSeconds")
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise VideoError("素材清单 schemaVersion 必须为 1")
    entries = manifest.get("assets")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 300:
        raise VideoError("assets 必须包含 1～300 项")
    prior = load_record(root)
    target_dir = _local_reference(root, MEDIA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    adopted = []
    transport = transport or HttpTransport()
    with tempfile.TemporaryDirectory(prefix="import-", dir=target_dir) as temporary:
        staged = []
        ids = set()
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict): raise VideoError(f"assets[{index}] 必须是对象")
            identity = entry.get("id")
            if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity) or identity in ids:
                raise VideoError(f"assets[{index}].id 无效或重复")
            ids.add(identity)
            try:
                kind = entry.get("kind")
                if kind not in SUFFIXES: raise VideoError("kind 必须为 image/video")
                role = entry.get("role", "color")
                if role not in ROLES:
                    raise VideoError("role 必须是已知贴图角色或 other（二维媒体）")
                target = entry.get("target", identity)
                if not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", target):
                    raise VideoError("target 必须是有效的素材目标 ID")
                local, remote = entry.get("localPath"), entry.get("mediaUrl")
                if bool(local) == bool(remote): raise VideoError("localPath/mediaUrl 必须二选一")
                origin = entry.get("sourceUrl") or "未知"
                if origin != "未知" and (not isinstance(origin, str) or not _http(origin)):
                    raise VideoError("sourceUrl 必须是公开网页地址")
                if remote and (not isinstance(remote, str) or not _http(remote)):
                    raise VideoError("mediaUrl 必须是 HTTP(S) 媒体直链")
                suffix = Path(local or urlsplit(remote).path).suffix.lower()
                if suffix not in SUFFIXES[kind]:
                    # 无扩展名 CDN 链接按类型命名，仍需实测，而不是相信 URL。
                    suffix = ".mp4" if kind == "video" else ".png"
                file = Path(temporary) / f"{identity}{suffix}"
                logger.info("导入素材 %s (%s)", identity, kind)
                if local:
                    source = (base / local).resolve()
                    if (not source.is_relative_to(root.resolve()) or not source.is_file()
                            or not 0 < source.stat().st_size <= MAX_DOWNLOAD_BYTES):
                        raise VideoError("本地素材缺失、为空或超过 256 MiB")
                    shutil.copyfile(source, file)
                else:
                    transport.download(remote, file, {}, timeout_s)
                if not 0 < file.stat().st_size <= MAX_DOWNLOAD_BYTES:
                    raise VideoError("下载素材为空或超过 256 MiB")
                info = probe(file, kind)
                source_metadata = media_policy.metadata({**entry, **info})
                sha = asset_digest(file)
                relative = f"assets/media/{sha}{suffix}"
                adopted.append({"id": identity, "path": relative, "kind": kind, **info, "sha256": sha,
                                "sourceUrl": origin, "mediaUrl": remote or "未知",
                                "author": entry.get("author") or "未知", "license": entry.get("license") or "未知",
                                **source_metadata,
                                **({"role": role} if "role" in entry else {}),
                                **({"target": target} if "target" in entry else {})})
                staged.append((file, root / relative))
            except (VideoError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
                raise VideoError(f"素材 {identity} 导入失败：{exc}；请更换候选后重试") from exc
        for file, destination in staged:
            if not destination.exists() or asset_digest(destination) != asset_digest(file):
                security.deliver(file, destination)
    # 保留未被本批替换的 ID；相同文件可被多个素材 ID 引用。
    record = {"schemaVersion": 1, "assets": [e for e in prior["assets"] if e["id"] not in ids] + adopted}
    _write_json(_local_reference(root, RECORD), record)
    return record


def load_record(root: Path) -> dict:
    file = _local_reference(root, RECORD)
    if not file.exists(): return {"schemaVersion": 1, "assets": []}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        if data.get("schemaVersion") != 1 or not isinstance(data.get("assets"), list): raise ValueError("结构无效")
        return data
    except (ValueError, OSError, AttributeError) as exc:
        raise VideoError(f"素材来源记录无效：{exc}") from exc


def resolve(root: Path) -> dict:
    """复核全部登记素材，返回「ID → 只读解析信息」与一份摘要指纹。

    代码场景只能按 ID 取素材，作品里写的是哪一幕用哪一项并不进入契约，因此
    复核不再区分「本幕用到」与否：记录里任何一项对不上都让准备失败，而不是
    等到某一幕恰好用它时才报错。图片与视频都不受画幅比例限制，裁切与摆位由
    作品代码决定。
    """
    from film_runtime.core.fingerprints import fingerprint
    media_root = _local_reference(root, MEDIA_DIR)
    media: dict[str, dict] = {}
    digests: dict[str, dict] = {}
    for index, entry in enumerate(load_record(root)["assets"]):
        where = f"assets[{index}]"
        if not isinstance(entry, dict):
            raise VideoError(f"素材记录 {where} 必须是对象")
        identity = entry.get("id")
        if not isinstance(identity, str) or not identity:
            raise VideoError(f"素材记录 {where} 缺少有效 id")
        if identity in media:
            raise VideoError(f"素材记录存在重复 ID：{identity}")
        kind = entry.get("kind")
        if kind not in SUFFIXES:
            raise VideoError(f"素材 {identity} 的类型必须是 image/video")
        try:
            source_metadata, problems, warnings = media_policy.assess(entry)
        except VideoError as exc:
            raise VideoError(f"素材 {identity} 采用元数据无效：{exc}") from exc
        if problems:
            raise VideoError(f"素材 {identity}：{problems[0]['message']}")
        for warning in warnings:
            logger.warning("素材 %s：%s", identity, warning["message"])
        role = entry.get("role", "color")
        if role not in ROLES:
            raise VideoError(f"素材 {identity} 的 role 必须是已知贴图角色或 other（二维媒体）")
        target = entry.get("target", identity)
        if not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", target):
            raise VideoError(f"素材 {identity} 的 target 必须是有效的素材目标 ID")
        relative = entry.get("path")
        if not isinstance(relative, str):
            raise VideoError(f"素材 {identity} 缺少 path")
        file = _local_reference(root, relative)
        if not file.is_relative_to(media_root) or not file.is_file():
            raise VideoError(f"素材 {identity} 必须指向 {MEDIA_DIR}/ 下存在的已导入文件")
        sha = entry.get("sha256")
        if not isinstance(sha, str) or sha != asset_digest(file):
            raise VideoError(f"素材 {identity} 与来源记录不符，请重新导入")
        info = probe(file, kind)
        if any(entry.get(key) != info[key] for key in info):
            raise VideoError(f"素材 {identity} 的实测尺寸、类型或时长与来源记录不符，请重新导入")
        # 色彩空间与 alpha 由实测像素格式推导，登记许可靠来源记录：作品据此设置材质
        # 与片尾署名。它们不写回来源记录，因此既有作品不需要重新导入素材。
        from film_runtime.engine.assets_audit import describe
        pixel = describe(file)
        media[identity] = {"src": f"{MEDIA_URL_PREFIX}/{file.name}", "kind": kind, **info,
                           "colorSpace": pixel["colorSpace"], "alpha": pixel["alpha"],
                           "license": entry.get("license") or "未知"}
        digests[identity] = {"path": relative, "sha256": sha, **info, **source_metadata,
                             "license": entry.get("license") or "未知"}
    return {"media": media, "digest": fingerprint(digests)}


DEFAULT_GALLERY = "pixabay"
