"""yt-dlp 抖音提取适配。

只负责“链接 → 规范化详情”，下载、来源与授权留证仍由 `douyin.py` 负责。
yt-dlp 的 Douyin 提取器直接请求详情接口；平台要求签名或新鲜 cookie 时它会失败，
这时由调用方决定是否退回浏览器解析。适配层不把 yt-dlp 的英文异常直接抛给用户。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError


class YtDlpUnavailable(M2VError):
    """yt-dlp 无法提取该链接；调用方可据此选择兜底路径。"""


class _QuietLogger:
    """吞掉 yt-dlp 的英文控制台输出；失败信息由适配层统一转成中文异常。"""

    def debug(self, _message: str) -> None:
        pass

    def info(self, _message: str) -> None:
        pass

    def warning(self, _message: str) -> None:
        pass

    def error(self, _message: str) -> None:
        pass


def _options(cookies: str | Path | None, timeout_s: float) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noprogress": True,
        "noplaylist": True,
        "socket_timeout": timeout_s,
        "retries": 2,
        "format": "best[ext=mp4]/best",
        "logger": _QuietLogger(),
    }
    if cookies is not None:
        options["cookiefile"] = str(Path(cookies).expanduser())
    return options


def _video_urls(info: dict[str, Any]) -> list[str]:
    ranked: list[tuple[int, int, int, int, str]] = []
    for entry in info.get("formats") or []:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        video = entry.get("vcodec")
        audio = entry.get("acodec")
        if not isinstance(url, str) or not url:
            continue
        # 契约优先 h264；h264 中优先可直接下载的音视频合流，再按分辨率与码率排序。
        combined = int(video not in (None, "none") and audio not in (None, "none"))
        h264 = int(isinstance(video, str) and video.startswith("avc"))
        height = int(entry.get("height") or 0)
        bitrate = int(entry.get("tbr") or 0)
        ranked.append((int(combined and h264), h264, combined, height * 10_000 + bitrate, url))
    ranked.sort(reverse=True)
    ordered: list[str] = []
    seen: set[str] = set()
    for _best, _h264, _combined, _score, url in ranked:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    direct = info.get("url")
    if isinstance(direct, str) and direct and direct not in seen:
        ordered.insert(0, direct)
    return ordered


def detail_from_info(
    info: dict[str, Any], *, source_url: str, final_url: str | None = None
) -> dict[str, Any]:
    """把 yt-dlp 的 info 规范成与页面解析相同的详情形状。"""
    video_urls = _video_urls(info)
    if not video_urls:
        raise YtDlpUnavailable("yt-dlp 没有返回可下载的视频地址")
    return {
        "schemaVersion": 1,
        "awemeId": str(info.get("id") or ""),
        "kind": "video",
        "desc": info.get("description") or info.get("title") or "",
        "author": {
            "uid": str(info.get("uploader_id") or ""),
            "secUid": "",
            "nickname": info.get("uploader") or "",
        },
        "createTime": int(info.get("timestamp") or 0),
        "durationMs": int(round(float(info.get("duration") or 0) * 1000)),
        "declaredWidth": int(info.get("width") or 0),
        "declaredHeight": int(info.get("height") or 0),
        "coverUrl": info.get("thumbnail") or "",
        "videoUrls": video_urls,
        "images": [],
        "sourceUrl": source_url,
        "finalUrl": final_url or info.get("webpage_url") or source_url,
    }


def probe(
    url: str, *, cookies: str | Path | None = None, timeout_s: float = 45
) -> dict[str, Any]:
    """用 yt-dlp 提取一条抖音视频；失败时抛 `YtDlpUnavailable`。"""
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - 依赖缺失时给出可操作提示
        raise YtDlpUnavailable("缺少 yt-dlp；请重新执行 uv sync") from exc

    try:
        with yt_dlp.YoutubeDL(_options(cookies, timeout_s)) as downloader:
            info = downloader.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise YtDlpUnavailable(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - yt-dlp 的异常层级不稳定
        raise YtDlpUnavailable(f"yt-dlp 提取失败：{exc}") from exc
    if not isinstance(info, dict):
        raise YtDlpUnavailable("yt-dlp 没有返回作品详情")
    if info.get("_type") == "playlist":
        entries = [entry for entry in info.get("entries") or [] if isinstance(entry, dict)]
        if len(entries) != 1:
            raise YtDlpUnavailable("链接不是单条抖音作品")
        info = entries[0]
    return detail_from_info(
        info,
        source_url=url,
        final_url=info.get("webpage_url") or url,
    )
