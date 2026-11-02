from __future__ import annotations

import json
from pathlib import Path

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.reference import douyin


API_DETAIL = {
    "aweme_id": "7699065250221428002",
    "desc": "数学，是最孤独的浪漫\n有人用一生去解。",
    "create_time": 1792578323,
    "author": {"uid": "1", "sec_uid": "SEC-1", "nickname": "阿猪的人生公式"},
    "video": {
        "duration": 93902,
        "width": 1920,
        "height": 1080,
        "play_addr": {"url_list": ["https://cdn.example/default.mp4"]},
        "play_addr_h264": {"url_list": ["https://cdn.example/h264.mp4"]},
        "play_addr_265": {"url_list": ["https://cdn.example/h265.mp4"]},
        "cover": {"url_list": ["https://cdn.example/cover.jpg"]},
        "bit_rate": [
            {"bit_rate": 1000000, "is_h265": False,
             "play_addr": {"url_list": ["https://cdn.example/low.mp4"]}},
            {"bit_rate": 3000000, "is_h265": False,
             "play_addr": {"url_list": ["https://cdn.example/high.mp4"]}},
            {"bit_rate": 9000000, "is_h265": True,
             "play_addr": {"url_list": ["https://cdn.example/high-265.mp4"]}},
        ],
    },
}

RSC_DETAIL = {
    "awemeId": "7699120421450723835",
    "desc": "第一次在广州火车站听这首歌。",
    "createTime": 1792666000,
    "authorInfo": {"uid": "2", "secUid": "SEC-2", "nickname": "秋姨."},
    "video": {"width": 1442, "height": 1080, "duration": 0},
    "images": [
        {
            "width": 1270,
            "height": 1920,
            "uri": "image-uri",
            "urlList": ["https://img.example/no-watermark.webp",
                        "https://img.example/no-watermark-2.webp"],
            "downloadUrlList": ["https://img.example/watermark.webp"],
        }
    ],
}


def _rsc_html(detail: dict) -> str:
    text = "3:[[\"$\",\"$L1\",null," + json.dumps(
        {"awemeId": detail["awemeId"], "aweme": {"detail": detail}},
        ensure_ascii=False,
    ) + "]]"
    return "<script>self.__pace_f.push([1," + json.dumps(text, ensure_ascii=False) + "])</script>"


def test_extract_share_url_from_share_text() -> None:
    text = (
        "1.58 复制打开抖音，看看【阿猪的人生公式的作品】数学，是最孤独的浪漫 "
        "https://v.douyin.com/RoCzhrDGM5g/ :1pm 09/09 k@c.At dAg:/"
    )
    assert douyin.extract_share_url(text) == "https://v.douyin.com/RoCzhrDGM5g/"

    note = (
        "8.25 复制打开抖音，看看【秋姨.的图文作品】第一次在广州火车站听这首歌 "
        "https://v.douyin.com/cO3diMlaQ04/ 12/10 jCH:/ :3pm X@Z.ZM"
    )
    assert douyin.extract_share_url(note) == "https://v.douyin.com/cO3diMlaQ04/"


def test_extract_share_url_rejects_other_sites() -> None:
    with pytest.raises(M2VError, match="抖音"):
        douyin.extract_share_url("https://www.youtube.com/watch?v=abc")
    with pytest.raises(M2VError, match="抖音"):
        douyin.extract_share_url("只有一段说明文字，没有链接")


def test_normalize_video_prefers_h264_high_bitrate() -> None:
    item = douyin.normalize_detail(API_DETAIL, source_url="https://v.douyin.com/x/")
    assert item["awemeId"] == "7699065250221428002"
    assert item["kind"] == "video"
    assert item["author"]["nickname"] == "阿猪的人生公式"
    assert item["videoUrls"] == [
        "https://cdn.example/high.mp4",
        "https://cdn.example/low.mp4",
        "https://cdn.example/h264.mp4",
        "https://cdn.example/default.mp4",
        "https://cdn.example/h265.mp4",
    ]
    assert item["durationMs"] == 93902
    assert item["declaredWidth"] == 1920 and item["declaredHeight"] == 1080
    assert item["coverUrl"] == "https://cdn.example/cover.jpg"


def test_normalize_note_prefers_no_watermark_images() -> None:
    item = douyin.normalize_detail(RSC_DETAIL)
    assert item["kind"] == "note"
    assert item["awemeId"] == "7699120421450723835"
    assert item["author"]["nickname"] == "秋姨."
    assert item["images"][0]["urls"] == [
        "https://img.example/no-watermark.webp",
        "https://img.example/no-watermark-2.webp",
        "https://img.example/watermark.webp",
    ]
    assert item["images"][0]["width"] == 1270


def test_detail_from_html_reads_rsc_payload() -> None:
    detail = douyin.detail_from_html(_rsc_html(RSC_DETAIL), "7699120421450723835")
    assert isinstance(detail, dict)
    assert detail["awemeId"] == "7699120421450723835"
    assert len(detail["images"]) == 1
    assert douyin.detail_from_html(_rsc_html(RSC_DETAIL), "另一個作品") is None


def test_aweme_id_from_canonical_url() -> None:
    assert douyin.aweme_id_from_url("https://www.douyin.com/video/7699065250221428002") == "7699065250221428002"
    assert douyin.aweme_id_from_url("https://www.douyin.com/note/7699120421450723835?x=1") == "7699120421450723835"
    assert douyin.aweme_id_from_url("https://v.douyin.com/abc/") is None


def _install_fake_fetch(monkeypatch, detail: dict) -> None:
    bodies = [json.dumps({"aweme_detail": detail}, ensure_ascii=False)]
    monkeypatch.setattr(
        douyin, "_read_page",
        lambda *_args, **_kwargs: (
            bodies, "", "https://www.douyin.com/video/7699065250221428002", "标题",
        ),
    )
    monkeypatch.setattr(
        douyin, "ytdlp_probe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            douyin.YtDlpUnavailable("测试环境不访问 yt-dlp")),
    )

    def fake_download(urls, destination: Path, kind: str) -> dict:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake-media-bytes")
        return {"sha256": douyin._digest(destination), "bytes": destination.stat().st_size}

    monkeypatch.setattr(douyin, "_download_first", fake_download)


def test_fetch_uses_ytdlp_before_browser(monkeypatch, tmp_path: Path) -> None:
    item = {
        "schemaVersion": 1,
        "awemeId": "7699065250221428002",
        "kind": "video",
        "desc": "yt-dlp 提取",
        "author": {"uid": "1", "secUid": "", "nickname": "作者"},
        "createTime": 1792578323,
        "durationMs": 2000,
        "declaredWidth": 1920,
        "declaredHeight": 1080,
        "coverUrl": "",
        "videoUrls": ["https://cdn.example/video.mp4"],
        "images": [],
        "sourceUrl": "https://v.douyin.com/RoCzhrDGM5g/",
        "finalUrl": "https://www.douyin.com/video/7699065250221428002",
    }
    monkeypatch.setattr(douyin, "ytdlp_probe", lambda *_args, **_kwargs: dict(item))
    monkeypatch.setattr(
        douyin, "_read_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("不应启动浏览器")),
    )

    def fake_download(urls, destination: Path, kind: str) -> dict:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake-media-bytes")
        return {"sha256": douyin._digest(destination), "bytes": destination.stat().st_size}

    monkeypatch.setattr(douyin, "_download_first", fake_download)
    result = douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path)
    assert result.item["desc"] == "yt-dlp 提取"
    assert (result.directory / "video.mp4").is_file()


def test_fetch_can_disable_browser_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        douyin, "ytdlp_probe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            douyin.YtDlpUnavailable("平台要求签名")),
    )
    with pytest.raises(M2VError, match="yt-dlp"):
        douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path,
                     fallback_browser=False)


def test_fetch_writes_recipe_and_reuses_verified_copy(monkeypatch, tmp_path: Path) -> None:
    _install_fake_fetch(monkeypatch, API_DETAIL)
    result = douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path)

    directory = tmp_path / "7699065250221428002"
    assert result.directory == directory
    assert not result.reused
    assert (directory / "video.mp4").read_bytes() == b"fake-media-bytes"
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["kind"] == "video"
    assert metadata["author"]["nickname"] == "阿猪的人生公式"
    recipe = json.loads((directory / "recipe.json").read_text(encoding="utf-8"))
    assert recipe["schemaVersion"] == 1
    assert [entry["path"] for entry in recipe["files"]] == ["video.mp4"]
    assert recipe["files"][0]["sha256"] == douyin._digest(directory / "video.mp4")

    again = douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path)
    assert again.reused
    assert again.files[0]["sha256"] == recipe["files"][0]["sha256"]


def test_fetch_requires_force_after_tampering(monkeypatch, tmp_path: Path) -> None:
    _install_fake_fetch(monkeypatch, API_DETAIL)
    result = douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path)
    (result.directory / "video.mp4").write_bytes(b"tampered")

    with pytest.raises(M2VError, match="--force"):
        douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path)

    replaced = douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path, force=True)
    assert not replaced.reused
    assert (result.directory / "video.mp4").read_bytes() == b"fake-media-bytes"


def test_fetch_downloads_note_images(monkeypatch, tmp_path: Path) -> None:
    _install_fake_fetch(monkeypatch, RSC_DETAIL)
    result = douyin.fetch("https://v.douyin.com/cO3diMlaQ04/", output=tmp_path)
    assert result.item["kind"] == "note"
    images = sorted((result.directory / "images").iterdir())
    assert [path.name for path in images] == ["001.webp"]
    recipe = json.loads((result.directory / "recipe.json").read_text(encoding="utf-8"))
    assert recipe["files"][0]["path"] == "images/001.webp"


def test_verify_detects_tampering_and_cli_exit_code(monkeypatch, tmp_path: Path, capsys) -> None:
    _install_fake_fetch(monkeypatch, API_DETAIL)
    result = douyin.fetch("https://v.douyin.com/RoCzhrDGM5g/", output=tmp_path)

    assert main(["ref", "verify", str(result.directory)]) == 0
    assert "校验通过" in capsys.readouterr().out

    (result.directory / "video.mp4").write_bytes(b"changed")
    assert main(["ref", "verify", str(result.directory)]) == 1
    assert "摘要或字节数不符" in capsys.readouterr().err


def test_fetch_rejects_non_douyin_target(capsys) -> None:
    assert main(["ref", "fetch", "https://example.com/video/1"]) == 1
    assert "抖音" in capsys.readouterr().err
