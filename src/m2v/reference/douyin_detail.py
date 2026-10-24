"""抖音作品链接、详情载荷与页面内嵌数据解析。"""
from __future__ import annotations

import json
import re
import urllib.parse

from m2v.core.errors import M2VError

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
REFERER = "https://www.douyin.com/"
DETAIL_PATH = "/aweme/v1/web/aweme/detail/"
DOUYIN_HOSTS = ("douyin.com", "iesdouyin.com")
SHARE_URL = re.compile(r"https?://[^\s<>\"'，。！？、）)]+")
AWEME_PATH = re.compile(r"/(?:share/)?(?:video|note)/(\d{5,})")
_PACE_PUSH = re.compile(r"self\.__pace_f\.push\((\[.*?\])\)\s*</script>", re.S)
_RSC_PREFIX = re.compile(r"^\d+:")


def extract_share_url(text: str) -> str:
    """从分享文本中取出第一个抖音链接，忽略前后的说明文字与日期。"""
    for match in SHARE_URL.finditer(text.strip()):
        candidate = match.group(0).rstrip(".,;:!?)]}'\"")
        host = (urllib.parse.urlsplit(candidate).hostname or "").lower()
        if any(host == item or host.endswith("." + item) for item in DOUYIN_HOSTS):
            return candidate
    raise M2VError(
        "没有找到抖音分享链接；请粘贴形如 https://v.douyin.com/xxxx/ 的分享文本"
    )


def aweme_id_from_url(url: str) -> str | None:
    """从视频页/图文页 URL 取作品 ID；短链没有 ID，返回 ``None``。"""
    match = AWEME_PATH.search(urllib.parse.urlsplit(url).path)
    return match.group(1) if match else None


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _urls(value) -> list[str]:
    if not isinstance(value, dict):
        return []
    items = value.get("url_list") or value.get("urlList") or []
    return [item for item in items if isinstance(item, str) and item]


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def video_urls(video: dict) -> list[str]:
    """按 h264 码率从高到低排列直链，再补默认与 h265 兜底。"""
    ranked: list[tuple[int, list[str]]] = []
    for entry in video.get("bit_rate") or video.get("bitRateList") or []:
        if not isinstance(entry, dict) or entry.get("is_h265") or entry.get("isH265"):
            continue
        urls = _urls(entry.get("play_addr") or entry.get("playAddr"))
        if urls:
            ranked.append((_int(entry.get("bit_rate") or entry.get("bitRate")), urls))
    ranked.sort(key=lambda item: item[0], reverse=True)
    ordered = [url for _, urls in ranked for url in urls]
    for key in (
        "play_addr_h264", "playAddrH264", "play_addr", "playAddr",
        "play_addr_265", "playAddrH265",
    ):
        ordered.extend(_urls(video.get(key)))
    return _dedupe(ordered)


def image_entries(images) -> list[dict]:
    """图文图片：``url_list`` 是无水印地址，``download_url_list`` 带水印，只作兜底。"""
    entries: list[dict] = []
    for item in images or []:
        if not isinstance(item, dict):
            continue
        urls = _dedupe(
            _urls({"urlList": item.get("url_list") or item.get("urlList")})
            + _urls({"urlList": item.get("download_url_list") or item.get("downloadUrlList")})
        )
        if not urls:
            continue
        entries.append({
            "urls": urls,
            "width": _int(item.get("width")),
            "height": _int(item.get("height")),
            "uri": item.get("uri") or "",
        })
    return entries


def normalize_detail(
    detail: dict,
    *,
    aweme_id: str | None = None,
    source_url: str = "",
    final_url: str = "",
) -> dict:
    """把详情接口（snake_case）与页面 RSC（camelCase）统一成一份元数据。"""
    video = detail.get("video") or {}
    images = image_entries(detail.get("images"))
    author = detail.get("author") or detail.get("authorInfo") or {}
    cover_urls = _dedupe(
        _urls(video.get("cover"))
        + _urls({"urlList": video.get("coverUrlList")})
        + _urls({"urlList": video.get("originCoverUrlList")})
    )
    return {
        "schemaVersion": 1,
        "awemeId": str(detail.get("aweme_id") or detail.get("awemeId") or aweme_id or ""),
        "kind": "note" if images else "video",
        "desc": detail.get("desc") or "",
        "author": {
            "uid": str(author.get("uid") or ""),
            "secUid": author.get("sec_uid") or author.get("secUid") or "",
            "nickname": author.get("nickname") or "",
        },
        "createTime": _int(detail.get("create_time") or detail.get("createTime")),
        "durationMs": _int(video.get("duration")),
        "declaredWidth": _int(video.get("width")),
        "declaredHeight": _int(video.get("height")),
        "coverUrl": cover_urls[0] if cover_urls else "",
        "videoUrls": video_urls(video),
        "images": images,
        "sourceUrl": source_url,
        "finalUrl": final_url,
    }


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def pace_texts(html: str):
    """逐个产出 ``self.__pace_f.push([...])`` 里的字符串载荷。"""
    for match in _PACE_PUSH.finditer(html):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and len(value) > 1 and isinstance(value[1], str):
            yield value[1]


def detail_from_html(html: str, aweme_id: str | None = None) -> dict | None:
    """从页面内嵌 RSC 载荷里找作品详情；图文页没有详情接口，靠这条路径。"""
    for text in pace_texts(html):
        try:
            data = json.loads(_RSC_PREFIX.sub("", text, count=1))
        except json.JSONDecodeError:
            continue
        for node in _walk(data):
            aweme = node.get("aweme")
            detail = aweme.get("detail") if isinstance(aweme, dict) else None
            if not isinstance(detail, dict) and isinstance(node.get("detail"), dict):
                detail = node["detail"]
            if not isinstance(detail, dict):
                continue
            found_id = str(detail.get("awemeId") or detail.get("aweme_id") or "")
            if aweme_id and found_id and found_id != aweme_id:
                continue
            if detail.get("images") or detail.get("video") or detail.get("desc"):
                return detail
    return None


def _detail_from_bodies(bodies: list[str], aweme_id: str | None) -> dict | None:
    for body in bodies:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        detail = payload.get("aweme_detail") if isinstance(payload, dict) else None
        if not isinstance(detail, dict):
            continue
        found_id = str(detail.get("aweme_id") or "")
        if aweme_id and found_id and found_id != aweme_id:
            continue
        if detail.get("video") or detail.get("images") or detail.get("desc"):
            return detail
    return None
