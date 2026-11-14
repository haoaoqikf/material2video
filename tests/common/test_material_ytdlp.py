"""固定版本平台 worker 的离线契约、网络纵深与真实子进程通信测试。"""
from __future__ import annotations

from dataclasses import asdict
from email.message import Message
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from m2v.materials.errors import MaterialError
from m2v.materials.network import NetworkBudget, SafeHTTP
from m2v.materials import ytdlp_worker as worker

pytest.importorskip("yt_dlp")


@pytest.fixture(autouse=True)
def restore_ytdlp_state(monkeypatch):
    from yt_dlp.downloader.external import FFmpegFD
    from yt_dlp.globals import plugin_dirs
    original = FFmpegFD.real_download
    directories = plugin_dirs.value
    monkeypatch.setenv("YTDLP_NO_PLUGINS", "1")
    yield
    FFmpegFD.real_download = original
    plugin_dirs.value = directories


def request(**changes):
    return {"schemaVersion": 1, "mode": "probe", "url": "https://www.youtube.com/watch?v=abcd_123", **changes}


def public_dns(host, port, *args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", int(port)))]


class Raw(io.BytesIO):
    def __init__(self, value=b"ok", *, status=200, headers=None):
        super().__init__(value)
        self.status, self.reason = status, "response"
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value


def test_request_whitelist_prevents_arbitrary_ytdlp_options_and_paths(tmp_path):
    for mutation in [dict(schemaVersion=2), dict(schemaVersion=True), dict(proxy="socks5://localhost"),
        dict(js_runtimes={"node": {}}), dict(external_downloader="ffmpeg"), dict(download_sections=[1, 2]),
        dict(url="http://127.0.0.1/"), dict(url="https://unreviewed.example.org/video"),
        dict(format_id="bestvideo+bestaudio"), dict(max_items=True), dict(max_items=99999),
        dict(subtitle_languages=["all"] * 9), dict(budget={"allow_private": True}), dict(budget={"total_bytes": float("inf")})]:
        with pytest.raises(MaterialError):
            worker.validate_request(request(**mutation))
    assert worker.validate_request(request())["format_id"] == "best"
    with pytest.raises(MaterialError, match="绝对暂存"):
        worker.validate_request(request(mode="download", directory="relative"))


def test_download_progress_enforces_aggregate_file_size_and_resource_callback():
    checked = []
    http = SafeHTTP(NetworkBudget(max_bytes=4), resource_check=lambda: checked.append(1))
    with worker.build_ytdlp(http, worker.validate_request(request())) as ydl:
        hook = ydl.params['progress_hooks'][0]
        hook({'status': 'downloading', 'downloaded_bytes': 4})
        assert checked == [1]
        with pytest.raises(MaterialError, match='单个输出'):
            hook({'status': 'downloading', 'downloaded_bytes': 5})


def test_download_resource_guard_checks_disk_files_and_total(tmp_path, monkeypatch):
    budget = NetworkBudget(max_bytes=4, total_bytes=6, min_free_bytes=1)
    (tmp_path / 'one').write_bytes(b'1234')
    worker._check_download_resources(tmp_path, budget)
    (tmp_path / 'two').write_bytes(b'abc')
    with pytest.raises(MaterialError, match='字节超过'):
        worker._check_download_resources(tmp_path, budget)
    monkeypatch.setattr(worker.shutil, 'disk_usage', lambda _: type('Disk', (), {'free': 0})())
    with pytest.raises(MaterialError, match='磁盘'):
        worker._check_download_resources(tmp_path, budget)


def test_search_constructs_only_bounded_supported_queries():
    value = {"schemaVersion": 1, "mode": "search", "provider": "youtube", "query": "机械臂抓取", "max_items": 3}
    assert worker.validate_request(value)["max_items"] == 3
    for mutation in [dict(provider="arbitrary"), dict(query="x\n--exec=evil"), dict(url="https://example.org/")]:
        with pytest.raises(MaterialError):
            worker.validate_request({**value, **mutation})


def test_only_public_handler_registered_and_external_routes_disabled():
    ydl = worker.build_ytdlp(SafeHTTP(), worker.validate_request(request()))
    try:
        director = ydl.build_request_director([object], [lambda *_: 999])
        assert list(director.handlers) == ["PublicOnlyUrllib"]
        assert not director.preferences
        assert not ydl.params["js_runtimes"] and not ydl.params["remote_components"]
        assert not ydl.params["cookiesfrombrowser"] and not ydl.params["usenetrc"]
        assert ydl.params["external_downloader"] == "native" and ydl.params["proxy"] == ""
        assert ydl.params["fixup"] == "never" and not ydl.params["continuedl"]
        director.close()
    finally:
        ydl.close()


def test_handler_revalidates_redirect_and_denies_proxy_extensions():
    from yt_dlp.networking import Request
    calls = []
    def exchange(target, addresses, method, headers, data, timeout):
        calls.append(target.url)
        return Raw(status=302, headers={"Location": "http://169.254.169.254/latest/meta-data"}), lambda: None
    http = SafeHTTP(resolver=public_dns, transport=exchange)
    with worker.build_ytdlp(http, worker.validate_request(request())) as ydl:
        for req in [Request("https://example.org/", proxies={"https": "http://localhost:8080"}),
                    Request("https://example.org/", extensions={"impersonate": "chrome"})]:
            with pytest.raises(Exception) as error:
                ydl._request_director.send(req)
            assert worker._classify(error.value).code == "security-blocked"
        assert not calls
        with pytest.raises(Exception) as error:
            ydl._request_director.send(Request("https://example.org/"))
        assert worker._classify(error.value).code == "security-blocked" and len(calls) == 1


def test_native_manifest_child_resource_cannot_bypass_handler():
    from yt_dlp.networking import Request
    calls = []
    def exchange(target, addresses, method, headers, data, timeout):
        calls.append(target.url)
        return Raw(b"#EXTM3U\nhttp://127.0.0.1/segment.ts\n"), lambda: None
    with worker.build_ytdlp(SafeHTTP(resolver=public_dns, transport=exchange), worker.validate_request(request())) as ydl:
        assert b"#EXTM3U" in ydl.urlopen(Request("https://cdn.example.org/list.m3u8")).read()
        with pytest.raises(Exception) as error:
            ydl.urlopen(Request("http://127.0.0.1/segment.ts"))
        assert worker._classify(error.value).code == "security-blocked"
    assert len(calls) == 1


def test_socket_guard_rejects_unresolved_names_private_and_unapproved_numeric(monkeypatch):
    connected = []
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    monkeypatch.setattr(socket.socket, "connect", lambda sock, address: connected.append(address))
    monkeypatch.setattr(socket.socket, "connect_ex", lambda sock, address: connected.append(address) or 0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with worker.socket_guard():
            socket.getaddrinfo("example.org", 443)
            sock.connect(("93.184.216.34", 443))
            assert sock.connect_ex(("93.184.216.34", 443)) == 0
            for address in [("example.org", 443), ("127.0.0.1", 443), ("1.1.1.1", 443), ("93.184.216.34", 8080)]:
                with pytest.raises(MaterialError):
                    sock.connect(address)
            assert len(connected) == 2
    finally:
        sock.close()


def test_socket_guard_rejects_mixed_dns_results(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: public_dns("x", 443) + [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 443))])
    with worker.socket_guard(), pytest.raises(MaterialError):
        socket.getaddrinfo("example.org", 443)


def test_ffmpeg_hard_guard_covers_direct_hls_fallback_and_native_mapping():
    from yt_dlp.downloader import get_suitable_downloader
    from yt_dlp.downloader.external import FFmpegFD
    from yt_dlp.downloader.hls import HlsFD
    from yt_dlp.downloader.dash import DashSegmentsFD
    with worker.build_ytdlp(SafeHTTP(), worker.validate_request(request())) as ydl:
        for protocol, expected in [("m3u8", HlsFD), ("m3u8_native", HlsFD), ("http_dash_segments", DashSegmentsFD)]:
            info = {"url": "https://example.org/media", "protocol": protocol, "ext": "mp4"}
            assert get_suitable_downloader(info, ydl.params) is expected
        # HlsFD 的内部 fallback 可直接实例化 FFmpegFD，不经过 ydl.dl。
        with pytest.raises(MaterialError, match="FFmpeg"):
            FFmpegFD.real_download(None, "ignored.mp4", {"url": "http://127.0.0.1/"})


@pytest.mark.parametrize("media", [{"is_live": True}, {"live_status": "is_upcoming"}, {"has_drm": True},
    {"section_start": 0}, {"section_end": 1}, {"requested_formats": [{"url": "https://example.org"}]},
    {"fragments": [{}] * 3}])
def test_live_drm_section_merge_and_fragment_limits_are_explicit(media):
    with pytest.raises(MaterialError):
        worker._check_media(media, NetworkBudget(max_requests=2))


def test_metadata_contains_no_signed_media_locator_or_cookie():
    value = worker._metadata({"id": "abcd_123", "title": "token=secret", "url": "https://cdn.example.org/secret?token=secret",
        "http_headers": {"Cookie": "secret"}, "webpage_url": "https://www.youtube.com/watch?v=abcd_123&token=secret",
        "formats": [{"format_id": "137", "url": "https://cdn.example.org/v?signature=secret", "vcodec": "avc1", "width": 1920}],
        "subtitles": {"en": [{"url": "https://cdn.example.org/sub?token=secret"}]}})
    encoded = json.dumps(value)
    assert "secret" not in encoded and "signature" not in encoded
    assert value["sourceUrl"].endswith("watch?v=abcd_123")
    assert value["formats"][0]["format_id"] == "137" and value["subtitles"]["manual"] == ["en"]


def test_flat_search_entries_preserve_only_canonical_platform_source_pages():
    value = worker._metadata({'_type': 'url', 'url': 'https://www.bilibili.com/video/BV1xx411c7mD?token=secret', 'id': 'entry'})
    assert value['sourceUrl'] == 'https://www.bilibili.com/video/BV1xx411c7mD'
    assert 'sourceUrl' not in worker._metadata({'webpage_url': 'bilisearch1:机械臂'})
    assert 'sourceUrl' not in worker._metadata({'_type': 'url', 'url': 'https://evilbilibili.com/video/BV1xx411c7mD'})
    assert 'sourceUrl' not in worker._metadata({'_type': 'url', 'url': 'https://www.youtube.com/videoplayback?token=secret'})
    assert 'sourceUrl' not in worker._metadata({'url': 'https://cdn.example.org/signed?token=secret'})


def test_execute_uses_bounded_search_and_whitelisted_result(monkeypatch):
    seen = []
    class Logger:
        messages = []
    class FakeYDL:
        material_logger = Logger()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def extract_info(self, locator, download=False):
            seen.append((locator, download))
            return {"entries": ({"id": str(i), "title": "candidate", "webpage_url": f"https://www.youtube.com/watch?v=id{i}"} for i in range(100))}
    monkeypatch.setattr(worker, "build_ytdlp", lambda *args: FakeYDL())
    value = worker.execute({"schemaVersion": 1, "mode": "search", "provider": "youtube", "query": "robot arm", "max_items": 2})
    assert seen == [("ytsearch2:robot arm", False)]
    assert len(value["entries"]) == 2 and value["toolchain"]["externalProcesses"] is False


def test_explicit_cookie_input_is_not_saved_back(tmp_path):
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n.example.org\tTRUE\t/\tTRUE\t0\tsession\tsecret\n")
    before = cookie.read_bytes()
    with worker.build_ytdlp(SafeHTTP(), worker.validate_request(request(cookies=str(cookie)))) as ydl:
        assert len(ydl.cookiejar) == 1
    assert cookie.read_bytes() == before


def test_actual_worker_json_roundtrip_fails_before_network_for_nonempty_directory(tmp_path):
    directory = tmp_path / "staging"
    directory.mkdir()
    (directory / "preserve.txt").write_text("existing")
    with pytest.raises(MaterialError) as error:
        worker.run_ytdlp(request(mode="download", directory=str(directory)), timeout_s=10)
    assert error.value.code == "conflict" and (directory / "preserve.txt").read_text() == "existing"


@pytest.mark.parametrize('operation', [
    "subprocess.run([sys.executable, '-c', 'print(123)'])",
    "os.execv(sys.executable, [sys.executable, '-c', 'print(123)'])",
    "sys.audit('os.startfile', 'https://example.org/', 'open')",
])
def test_actual_worker_process_guard_rejects_spawn_exec_and_shell_open(operation):
    code = ('import os,sys,subprocess\nfrom m2v.materials.ytdlp_worker import _install_process_guard\n'
            'from m2v.materials.errors import MaterialError\n_install_process_guard()\n'
            f'try:\n    {operation}\nexcept MaterialError as exc:\n    print(exc.code)\n')
    process = subprocess.run([sys.executable, '-c', code], text=True, encoding='utf-8',
                             capture_output=True, timeout=10)
    assert process.returncode == 0 and process.stdout.strip() == 'security-blocked'


def test_actual_worker_bounds_message_before_write_and_emits_utf8_under_gbk():
    code = ("from m2v.materials import ytdlp_worker as w\n"
            "w.execute=lambda request: {'text': 'x'*1024}\nw._MAX_MESSAGE=512\nraise SystemExit(w.main())")
    environment = {**os.environ, 'PYTHONIOENCODING': 'gbk'}
    process = subprocess.run([sys.executable, '-c', code], input='{}', text=True, encoding='utf-8',
                             capture_output=True, env=environment, timeout=10)
    envelope = json.loads(process.stdout)
    assert process.returncode == 2 and envelope['error']['code'] == 'resource-limit'
    assert len(process.stdout.encode('utf-8')) < 512 and '响应超过上限' in envelope['error']['message']


def test_actual_module_rejects_unknown_request_without_echoing_secrets():
    process = subprocess.run([sys.executable, "-m", "m2v.materials.ytdlp_worker"],
        input=json.dumps({"schemaVersion": 1, "mode": "probe", "url": "https://www.youtube.com/watch?v=x&token=secret", "exec": "secret"}),
        text=True, encoding='utf-8', capture_output=True, timeout=10)
    envelope = json.loads(process.stdout)
    assert process.returncode == 2 and envelope["ok"] is False
    assert envelope["error"]["code"] == "invalid-request"
    assert "secret" not in process.stdout + process.stderr


def test_parent_cancellation_kills_child_and_does_not_read_error_log(monkeypatch):
    class Child:
        pass
    child, killed = Child(), []
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(worker, "_kill_tree", lambda process: killed.append(process))
    with pytest.raises(MaterialError) as error:
        worker.run_ytdlp(request(), cancelled=lambda: True)
    assert error.value.code == "cancelled" and killed == [child]


def test_actual_isolated_process_tree_can_be_terminated_without_network():
    creation = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    child = subprocess.Popen([sys.executable, '-c', 'import threading; threading.Event().wait(30)'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **creation)
    try:
        worker._kill_tree(child)
        assert child.poll() is not None
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


def test_parent_timeout_kills_child(monkeypatch):
    class Child:
        pass
    child, killed = Child(), []
    monkeypatch.setattr(worker.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(worker, "_kill_tree", lambda process: killed.append(process))
    clock = iter([0.0, 2.0])
    monkeypatch.setattr(worker.time, "monotonic", lambda: next(clock))
    with pytest.raises(MaterialError) as error:
        worker.run_ytdlp(request(), timeout_s=1)
    assert error.value.code == "network-timeout" and killed == [child]
