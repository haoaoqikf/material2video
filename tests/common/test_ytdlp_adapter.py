"""yt-dlp 详情适配：格式排序与规范化字段。"""
from __future__ import annotations

import pytest

from m2v.core.errors import M2VError
from m2v.reference import ytdlp_adapter


def test_info_is_normalized_to_the_existing_metadata_shape():
    info = {
        "id": "7699065250221428002",
        "title": "标题",
        "description": "文案",
        "uploader": "作者",
        "uploader_id": "42",
        "timestamp": 1792578323,
        "duration": 93.902,
        "width": 1920,
        "height": 1080,
        "thumbnail": "https://cdn.example/cover.jpg",
        "webpage_url": "https://www.douyin.com/video/7699065250221428002",
        "formats": [
            {"url": "https://cdn.example/low.mp4", "vcodec": "avc1", "acodec": "aac", "height": 720, "tbr": 900},
            {"url": "https://cdn.example/high.mp4", "vcodec": "avc1", "acodec": "aac", "height": 1080, "tbr": 3000},
            {"url": "https://cdn.example/video-only.mp4", "vcodec": "avc1", "acodec": "none", "height": 2160},
        ],
    }
    item = ytdlp_adapter.detail_from_info(info, source_url="https://v.douyin.com/x/")
    assert item["awemeId"] == "7699065250221428002"
    assert item["kind"] == "video"
    assert item["desc"] == "文案"
    assert item["author"]["nickname"] == "作者"
    assert item["durationMs"] == 93902
    assert item["declaredWidth"] == 1920
    assert item["videoUrls"][0] == "https://cdn.example/high.mp4"


def test_info_without_download_url_is_unavailable():
    with pytest.raises(M2VError, match="可下载"):
        ytdlp_adapter.detail_from_info(
            {"id": "1", "formats": []}, source_url="https://v.douyin.com/x/")
