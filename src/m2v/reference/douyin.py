"""抖音参考素材：yt-dlp 提取、直链下载、写来源与摘要留证。

默认先用 yt-dlp 读取作品详情；平台要求签名或新鲜 cookie 导致提取失败时，
才退回浏览器解析（页面自己完成签名与请求）。两条路径产出同一份规范化详情，
参考素材都落在 ``refs/douyin/<awemeId>/``：媒体默认用于制作前分析，不进入成片，
也不进入版本控制。目录里的 ``recipe.json`` 是唯一留证来源，``ref verify`` 按它复核。
用户明确要求复用单条参考音频时，由 ``m2v.reference.audio`` 提取到作品目录并留证，
渲染链路仍不直接读取 ``refs/``。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.workspace import bundle_repo_root, content_root
from .douyin_detail import (
    DETAIL_PATH,
    DESKTOP_UA,
    _detail_from_bodies,
    aweme_id_from_url,
    detail_from_html,
    extract_share_url,
    normalize_detail,
)
from .douyin_media import _download_first, _guess_ext, _measure, verify_directory
from .ytdlp_adapter import YtDlpUnavailable, probe as ytdlp_probe

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    """一次引用的结果：目录、规范化元数据、是否复用、逐文件摘要。"""

    directory: Path
    item: dict
    reused: bool
    files: list[dict]


def workspace_root() -> Path:
    """参考素材默认所在的根：内容根优先，其次是仓库根，最后是当前目录。"""
    return content_root() or bundle_repo_root() or Path.cwd()


def reference_root(explicit: str | Path | None = None) -> Path:
    """``--output`` 指定参考素材根目录；省略时是 ``<工作区>/refs/douyin``。"""
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    return workspace_root() / "refs" / "douyin"


def profile_dir() -> Path:
    """浏览器 profile 可能含登录 cookie，放在被忽略的缓存目录里。"""
    return workspace_root() / ".cache" / "douyin-profile"


def _read_page(url: str, *, headed: bool, timeout_s: float) -> tuple[list[str], str, str, str]:
    """打开页面，收集详情接口响应与最终 HTML；返回诊断需要的信息。"""
    from playwright.sync_api import sync_playwright

    profile = profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    bodies: list[str] = []
    with sync_playwright() as playwright:
        try:
            context = playwright.chromium.launch_persistent_context(
                str(profile),
                headless=not headed,
                user_agent=DESKTOP_UA,
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as exc:  # noqa: BLE001 - 浏览器启动失败统一转成可读错误
            raise M2VError(f"无法启动浏览器（profile：{profile}）：{exc}") from exc
        try:
            page = context.pages[0] if context.pages else context.new_page()

            def remember(response):
                if DETAIL_PATH not in response.url:
                    return
                try:
                    body = response.text()
                except Exception:  # noqa: BLE001 - 导航打断读取时不值得中断整体流程
                    return
                if body:
                    bodies.append(body)

            page.on("response", remember)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_s * 1000))
            except Exception as exc:  # noqa: BLE001
                raise M2VError(f"打开抖音页面失败：{exc}") from exc
            deadline = time.monotonic() + timeout_s
            html = ""
            while time.monotonic() < deadline:
                if bodies:
                    break
                page.wait_for_timeout(1000)
                try:
                    html = page.content()
                except Exception:  # noqa: BLE001 - 页面正在跳转时稍后重试
                    continue
                if detail_from_html(html):
                    break
            if not html:
                try:
                    html = page.content()
                except Exception:  # noqa: BLE001
                    html = ""
            final_url = page.url
            title = page.title()
        finally:
            context.close()
    return bodies, html, final_url, title


def _download_item(item: dict, directory: Path) -> list[dict]:
    records: list[dict] = []
    if item["kind"] == "note":
        if not item["images"]:
            raise M2VError("图文作品没有可下载的图片地址")
        image_dir = directory / "images"
        image_dir.mkdir()
        for index, image in enumerate(item["images"], 1):
            destination = image_dir / f"{index:03d}{_guess_ext(image['urls'][0], 'image')}"
            record = _download_first(image["urls"], destination, "image")
            record["path"] = f"images/{destination.name}"
            record.update(_measure(destination))
            records.append(record)
    else:
        if not item["videoUrls"]:
            raise M2VError("详情没有可用的视频直链")
        destination = directory / "video.mp4"
        record = _download_first(item["videoUrls"], destination, "video")
        record["path"] = "video.mp4"
        record.update(_measure(destination))
        records.append(record)
    return records


def _metadata(item: dict, *, captured_at: str, final_url: str) -> dict:
    return {
        "schemaVersion": 1,
        "awemeId": item["awemeId"],
        "kind": item["kind"],
        "desc": item["desc"],
        "author": item["author"],
        "createTime": item["createTime"],
        "durationMs": item["durationMs"],
        "declaredWidth": item["declaredWidth"],
        "declaredHeight": item["declaredHeight"],
        "coverUrl": item["coverUrl"],
        "sourceUrl": item["sourceUrl"],
        "finalUrl": final_url,
        "capturedAt": captured_at,
        "images": [
            {"width": image["width"], "height": image["height"], "uri": image["uri"]}
            for image in item["images"]
        ],
    }


def fetch(
    target: str,
    *,
    output: str | Path | None = None,
    headed: bool = False,
    force: bool = False,
    timeout_s: float = 45,
    cookies: str | Path | None = None,
    fallback_browser: bool = True,
) -> FetchResult:
    """下载一条抖音参考素材；已存在时先校验，校验失败必须 ``force`` 才替换。

    默认先用 yt-dlp；提取失败且允许兜底时退回浏览器解析。两条路径最终都写入
    同一套 ``metadata.json`` / ``recipe.json`` 留证。
    """
    url = extract_share_url(target)
    expected_id = aweme_id_from_url(url)
    final_url = url
    item: dict | None = None

    try:
        item = ytdlp_probe(url, cookies=cookies, timeout_s=timeout_s)
        final_url = item.get("finalUrl") or url
        if expected_id and item.get("awemeId") and item["awemeId"] != expected_id:
            raise YtDlpUnavailable(
                f"yt-dlp 返回的作品 ID {item['awemeId']} 与链接 {expected_id} 不一致"
            )
    except YtDlpUnavailable as exc:
        if not fallback_browser:
            raise M2VError(
                f"yt-dlp 无法读取抖音作品详情：{exc}；"
                "可提供 --cookies，或允许浏览器兜底"
            ) from exc
        logger.warning("yt-dlp 无法读取抖音详情（%s），退回浏览器解析", exc)
        item = _fetch_with_browser(
            url,
            expected_id=expected_id,
            headed=headed,
            timeout_s=timeout_s,
        )
        final_url = item["finalUrl"]

    if not item["awemeId"]:
        raise M2VError("详情缺少作品 ID，无法确定保存目录")

    root = reference_root(output)
    destination = root / item["awemeId"]
    if destination.exists():
        if not force:
            try:
                files = verify_directory(destination, quiet=True)
            except M2VError as exc:
                raise M2VError(
                    f"参考素材已存在但校验失败：{destination}（{exc}）；确认后使用 --force 替换"
                ) from exc
            return FetchResult(destination, item, True, files)

    root.mkdir(parents=True, exist_ok=True)
    staging = root / f".{item['awemeId']}.partial-{os.getpid()}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        files = _download_item(item, staging)
        captured_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        metadata = _metadata(item, captured_at=captured_at, final_url=final_url)
        recipe = {
            "schemaVersion": 1,
            "awemeId": item["awemeId"],
            "kind": item["kind"],
            "sourceUrl": url,
            "finalUrl": final_url,
            "capturedAt": captured_at,
            "files": files,
        }
        (staging / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "recipe.json").write_text(
            json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if destination.exists():
            previous = root / f".{item['awemeId']}.old-{os.getpid()}"
            shutil.rmtree(previous, ignore_errors=True)
            destination.replace(previous)
            try:
                staging.replace(destination)
            except Exception:
                previous.replace(destination)
                raise
            shutil.rmtree(previous, ignore_errors=True)
        else:
            staging.replace(destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return FetchResult(destination, item, False, files)


def _fetch_with_browser(
    url: str,
    *,
    expected_id: str | None,
    headed: bool,
    timeout_s: float,
) -> dict:
    """浏览器兜底：让页面完成签名，再读取详情接口或 RSC 载荷。"""
    bodies, html, final_url, title = _read_page(url, headed=headed, timeout_s=timeout_s)
    target_id = expected_id or aweme_id_from_url(final_url)
    detail = _detail_from_bodies(bodies, target_id)
    if detail is None and html:
        detail = detail_from_html(html, target_id)
    if detail is None:
        hint = (
            "；请确认链接可访问且未被风控"
            if headed
            else "；可加 --headed 打开可见浏览器完成登录或验证后重试"
        )
        raise M2VError(f"未能读取抖音作品详情（{final_url}｜{title[:60]}）{hint}")
    return normalize_detail(
        detail,
        aweme_id=target_id,
        source_url=url,
        final_url=final_url,
    )
