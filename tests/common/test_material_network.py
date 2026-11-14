"""素材网络边界：全部离线注入，不提供运行时允许私网开关。"""
from __future__ import annotations

from email.message import Message
import gzip
import hashlib
import io
import json
from pathlib import Path
import socket
import threading

import pytest

from m2v.materials.errors import MaterialError
from m2v.materials import network
from m2v.materials.network import NetworkBudget, SafeHTTP, public_ip, public_url, resolve_public, validate_url

PUBLIC = "93.184.216.34"


def dns(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (PUBLIC, port))]


class Raw(io.BytesIO):
    def __init__(self, body=b"", *, status=200, headers=None):
        super().__init__(body)
        self.status, self.reason = status, "response"
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = str(value)


class Transport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, target, addresses, method, headers, data, timeout):
        self.calls.append((target, addresses, method, {k.lower(): v for k, v in headers.items()}, data))
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value, lambda: None


def client(*responses, **options):
    transport = Transport(*responses)
    return SafeHTTP(resolver=dns, transport=transport, **options), transport


@pytest.mark.parametrize("ip", ["127.0.0.1", "0.0.0.0", "10.0.0.1", "169.254.169.254", "172.16.0.1", "192.168.0.1",
    "100.64.0.1", "224.0.0.1", "240.0.0.1", "::1", "::", "fe80::1", "fc00::1", "ff02::1",
    "::ffff:127.0.0.1", "64:ff9b::7f00:1", "64:ff9b:1::1", "2002:7f00:1::", "fe80::1%eth0"])
def test_non_public_ips_rejected(ip):
    with pytest.raises(MaterialError) as error:
        public_ip(ip)
    assert error.value.code == "security-blocked"


@pytest.mark.parametrize("url", ["file:///secret", "ftp://example.org/a", "http://localhost/a", "http://user:pass@example.org/",
    "http://example.org:8080/a", "http://127.1/", "http://2130706433/", "http://0177.0.0.1/",
    "http://0x7f000001/", "http://example.org\\@127.0.0.1/", "http://example.org/\r\nX:x", "http://[fe80::1%25eth0]/"])
def test_unsafe_url_syntax_rejected(url):
    with pytest.raises(MaterialError):
        validate_url(url)


def test_signed_path_escapes_preserved_and_youtube_source_identity_retained():
    assert validate_url("https://example.org/a%2Fb%3Fx?token=abc").path == "/a%2Fb%3Fx?token=abc"
    assert public_url("https://www.youtube.com/watch?v=abcd_123&token=secret") == "https://www.youtube.com/watch?v=abcd_123"
    assert public_url("https://cdn.example.org/a?token=secret#secret") == "https://cdn.example.org/a"
    target = validate_url('https://example.org/Artemis Origins.jpg?q=机械 臂')
    assert target.url == 'https://example.org/Artemis%20Origins.jpg?q=%E6%9C%BA%E6%A2%B0%20%E8%87%82'
    assert ' ' not in target.path
    with pytest.raises(MaterialError):
        validate_url(' https://example.org/a')


def test_default_resolver_is_bound_at_request_time(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', dns)
    transport = Transport(Raw(b'ok'))
    assert SafeHTTP(transport=transport).get_bytes('https://example.org/a') == b'ok'
    assert transport.calls[0][1][0][4] == (PUBLIC, 443)


@pytest.mark.parametrize('cancel', [False, True])
def test_slow_system_dns_is_bounded_and_cancellable(monkeypatch, cancel):
    release = threading.Event()
    calls = []
    def slow(host, port, **kwargs):
        release.wait(2)
        return dns(host, port)
    def cancelled():
        calls.append(1)
        return cancel and len(calls) >= 2
    monkeypatch.setattr(socket, 'getaddrinfo', slow)
    transport = Transport()
    http = SafeHTTP(transport=transport, cancelled=cancelled,
                    budget=NetworkBudget(timeout_s=0.05, deadline_s=0.5))
    try:
        with pytest.raises(MaterialError) as error:
            http.get_bytes('https://example.org/a')
        assert error.value.code == ('cancelled' if cancel else 'network-timeout')
        assert not transport.calls
    finally:
        release.set()


@pytest.mark.parametrize('value', ['bytes 3-4/6', 'bytes 3-5/6'])
def test_resume_requires_complete_open_ended_range_and_matching_length(tmp_path, value):
    target = tmp_path / 'clip'
    (tmp_path / 'clip.part').write_bytes(b'abc')
    (tmp_path / 'clip.resume.json').write_text(json.dumps({'urlIdentity': hashlib.sha256(b'https://example.org/a').hexdigest(),
        'etag': '"v1"', 'lastModified': None, 'total': 6, 'bytes': 3, 'sha256': hashlib.sha256(b'abc').hexdigest()}))
    http, _ = client(Raw(b'de', status=206, headers={'ETag': '"v1"', 'Content-Range': value, 'Content-Length': 2}))
    with pytest.raises(MaterialError, match='版本及区间'):
        http.download('https://example.org/a', target)
    assert not target.exists() and (tmp_path / 'clip.part').read_bytes() == b'abc'


def test_resume_file_hardlink_is_rejected_before_truncation(tmp_path):
    import os
    original = tmp_path / 'original'
    original.write_bytes(b'preserve')
    try:
        os.link(original, tmp_path / 'clip.part')
    except OSError:
        pytest.skip('宿主不支持当前临时目录创建硬链接')
    http, transport = client()
    with pytest.raises(MaterialError, match='独立普通文件'):
        http.download('https://example.org/a', tmp_path / 'clip')
    assert original.read_bytes() == b'preserve' and not transport.calls


def test_any_private_dns_answer_rejects_before_transport():
    transport = Transport()
    def mixed(host, port, **kwargs):
        return dns(host, port) + [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]
    http = SafeHTTP(resolver=mixed, transport=transport)
    with pytest.raises(MaterialError, match="公开地址"):
        http.get_bytes("https://example.org/a")
    assert not transport.calls


def test_dns_results_used_for_connection_without_second_lookup(monkeypatch):
    connected, resolutions = [], []
    class Sock:
        def settimeout(self, value):
            pass
        def connect(self, value):
            connected.append(value)
        def close(self):
            pass
    class Conn:
        def __init__(self, *args, **kwargs):
            pass
        def request(self, *args, **kwargs):
            self._create_connection(("example.org", 80))
        def getresponse(self):
            return Raw(b"pinned")
        def close(self):
            pass
    def once(host, port, **kwargs):
        resolutions.append(host)
        return dns(host, port)
    monkeypatch.setattr(network.socket, "socket", lambda *args: Sock())
    monkeypatch.setattr(network.http.client, "HTTPConnection", Conn)
    http = SafeHTTP(resolver=once)
    assert http.get_bytes("http://example.org/") == b"pinned"
    assert resolutions == ["example.org"] and connected == [(PUBLIC, 80)]


def test_redirect_is_revalidated_and_sensitive_custom_headers_removed():
    http, transport = client(Raw(status=302, headers={"Location": "https://other.example.org/clip"}), Raw(b"ok"))
    assert http.get_bytes("https://example.org/", headers={"Authorization": "Bearer secret", "Cookie": "session=secret",
        "Referer": "https://private.example.org/", "X-Custom-Secret": "secret", "Range": "bytes=0-"}) == b"ok"
    forwarded = transport.calls[1][3]
    assert all(key not in forwarded for key in ["authorization", "cookie", "referer", "x-custom-secret"])
    assert forwarded["range"] == "bytes=0-"


def test_redirect_to_private_and_dns_rebinding_rejected():
    http, transport = client(Raw(status=302, headers={"Location": "http://127.0.0.1/metadata"}))
    with pytest.raises(MaterialError):
        http.get_bytes("https://example.org/")
    assert len(transport.calls) == 1
    answers = iter([dns("x", 443), [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]])
    http, transport = client(Raw(status=302, headers={"Location": "/again"}))
    http.resolver = lambda *args, **kwargs: next(answers)
    with pytest.raises(MaterialError):
        http.get_bytes("https://example.org/")
    assert len(transport.calls) == 1


def test_cross_origin_preserved_post_rejected_before_request():
    http, transport = client(Raw(status=307, headers={"Location": "https://other.example.org/"}))
    with pytest.raises(MaterialError):
        http.open("https://example.org/", method="POST", data=b"secret")
    assert len(transport.calls) == 1


def test_post_303_changes_method_and_discards_payload():
    http, transport = client(Raw(status=303, headers={"Location": "/new"}), Raw(b"ok"))
    with http.open("https://example.org/", method="POST", data=b"payload", headers={"Content-Type": "text/plain"}) as response:
        assert response.read() == b"ok"
    assert transport.calls[1][2] == "GET" and transport.calls[1][4] is None
    assert "content-type" not in transport.calls[1][3]


def test_redirect_and_request_counts_are_bounded():
    http, transport = client(Raw(status=302, headers={"Location": "/again"}), budget=NetworkBudget(max_redirects=0))
    with pytest.raises(MaterialError):
        http.get_bytes("https://example.org/")
    assert len(transport.calls) == 1
    http, _ = client(Raw(b"x"), budget=NetworkBudget(max_requests=1))
    http.get_bytes("https://example.org/")
    with pytest.raises(MaterialError, match="请求数量"):
        http.get_bytes("https://example.org/")


def test_retry_after_bounded_and_status_classified():
    clock = [0.0]
    http, transport = client(Raw(status=429, headers={"Retry-After": "0.4"}), Raw(b"ok"),
        clock=lambda: clock[0], sleep=lambda delay: clock.__setitem__(0, clock[0] + delay))
    assert http.get_bytes("https://example.org/?token=secret") == b"ok"
    assert clock[0] == pytest.approx(0.4) and len(transport.calls) == 2
    http, _ = client(Raw(status=429, headers={"Retry-After": "9999"}))
    with pytest.raises(MaterialError) as error:
        http.get_bytes("https://example.org/")
    assert error.value.code == "rate-limited"
    http, _ = client(Raw(status=403))
    with pytest.raises(MaterialError) as error:
        http.get_bytes("https://example.org/")
    assert error.value.code == "access-denied"


def test_no_retry_of_post_or_unbounded_transport_failure():
    http, transport = client(OSError("secret"), budget=NetworkBudget(retries=2, retry_delay_s=0))
    with pytest.raises(MaterialError) as error:
        http.open("https://example.org/", method="POST", data=b"x")
    assert "secret" not in str(error.value) and len(transport.calls) == 1
    http, transport = client(OSError(), OSError(), OSError(), budget=NetworkBudget(retries=2, retry_delay_s=0))
    with pytest.raises(MaterialError):
        http.get_bytes("https://example.org/")
    assert len(transport.calls) == 3


def test_unknown_length_total_and_gzip_expansion_bounded():
    http, _ = client(Raw(b"abcdef"), budget=NetworkBudget(max_bytes=4))
    with pytest.raises(MaterialError, match="字节预算"):
        http.get_bytes("https://example.org/")
    http, _ = client(Raw(b"abc"), Raw(b"def"), budget=NetworkBudget(max_bytes=10, total_bytes=5))
    assert http.get_bytes("https://example.org/one") == b"abc"
    with pytest.raises(MaterialError, match="总流量"):
        http.get_bytes("https://example.org/two")
    http, _ = client(Raw(gzip.compress(b"x" * 10000), headers={"Content-Encoding": "gzip"}), budget=NetworkBudget(max_bytes=128))
    with pytest.raises(MaterialError, match="解压响应"):
        http.get_bytes("https://example.org/")


def test_content_length_limit_closes_response():
    raw = Raw(b"huge", headers={"Content-Length": 1000})
    http, _ = client(raw, budget=NetworkBudget(max_bytes=100))
    with pytest.raises(MaterialError):
        http.get_bytes("https://example.org/")
    assert raw.closed


def test_cancellation_and_deadline_checked_before_network():
    http, transport = client(cancelled=lambda: True)
    with pytest.raises(MaterialError) as error:
        http.get_bytes("https://example.org/")
    assert error.value.code == "cancelled" and not transport.calls
    clock = [0.0]
    http, transport = client(clock=lambda: clock[0], budget=NetworkBudget(deadline_s=1))
    clock[0] = 2
    with pytest.raises(MaterialError) as error:
        http.get_bytes("https://example.org/")
    assert error.value.code == "network-timeout" and not transport.calls


def test_download_and_verified_resume_do_not_mix_remote_versions(tmp_path):
    class Interrupted(Raw):
        def __init__(self):
            super().__init__(b"", headers={"Content-Length": 10, "ETag": '"v1"'})
            self.calls = 0
        def read(self, size=-1):
            self.calls += 1
            if self.calls == 1:
                return b"abc"
            raise OSError("connection lost with token=secret")
    target = tmp_path / "clip.bin"
    http, _ = client(Interrupted(), budget=NetworkBudget(min_free_bytes=0))
    with pytest.raises(MaterialError):
        http.download("https://example.org/a?signature=secret", target)
    assert not target.exists()
    assert (tmp_path / "clip.bin.part").read_bytes() == b"abc"
    assert "secret" not in (tmp_path / "clip.bin.resume.json").read_text()
    http, transport = client(Raw(b"defghij", status=206, headers={"ETag": '"v1"', "Content-Range": "bytes 3-9/10", "Content-Length": 7}), budget=NetworkBudget(min_free_bytes=0))
    result = http.download("https://example.org/a?signature=secret", target)
    assert transport.calls[0][3]["range"] == "bytes=3-"
    assert target.read_bytes() == b"abcdefghij"
    assert result["bytes"] == 10 and result["transferredBytes"] == 7 and result["resumedBytes"] == 3
    assert result["sha256"] == hashlib.sha256(b"abcdefghij").hexdigest()
    assert not (tmp_path / "clip.bin.resume.json").exists()


def test_changed_remote_restarts_and_invalid_range_is_rejected(tmp_path):
    for name in ["changed", "bad"]:
        (tmp_path / (name + ".part")).write_bytes(b"abc")
        (tmp_path / (name + ".resume.json")).write_text(json.dumps({"urlIdentity": hashlib.sha256(b"https://example.org/a").hexdigest(),
            "etag": '"v1"', "lastModified": None, "total": 6, "bytes": 3, "sha256": hashlib.sha256(b"abc").hexdigest()}))
    http, _ = client(Raw(b"NEWNEW", headers={"ETag": '"v2"', "Content-Length": 6}), budget=NetworkBudget(min_free_bytes=0))
    result = http.download("https://example.org/a", tmp_path / "changed")
    assert (tmp_path / "changed").read_bytes() == b"NEWNEW" and result["resumedBytes"] == 0
    http, _ = client(Raw(b"xyz", status=206, headers={"ETag": '"v2"', "Content-Length": 3, "Content-Range": "bytes 3-5/6"}), budget=NetworkBudget(min_free_bytes=0))
    with pytest.raises(MaterialError, match="版本及区间"):
        http.download("https://example.org/a", tmp_path / "bad")
    assert not (tmp_path / "bad").exists() and (tmp_path / "bad.part").read_bytes() == b"abc"


def test_local_publication_error_has_finite_retries_and_preserves_verified_partial(tmp_path, monkeypatch):
    attempts, delays = [], []
    def denied(*args):
        attempts.append(1)
        raise PermissionError('injected local publication failure')
    http, _ = client(Raw(b'abc', headers={'Content-Length': 3}))
    monkeypatch.setattr(network.os, 'replace', denied)
    monkeypatch.setattr(http, '_wait', lambda seconds: delays.append(seconds))
    with pytest.raises(PermissionError):
        http.download('https://example.org/a', tmp_path / 'clip')
    expected = 3 if network.os.name == 'nt' else 1
    assert len(attempts) == expected and len(delays) == expected - 1
    assert not (tmp_path / 'clip').exists()
    assert (tmp_path / 'clip.part').read_bytes() == b'abc'


def test_disk_guard_and_existing_destination_leave_original_untouched(tmp_path, monkeypatch):
    target = tmp_path / "clip"
    target.write_bytes(b"original")
    http, transport = client()
    with pytest.raises(MaterialError, match="已存在"):
        http.download("https://example.org/a", target)
    assert target.read_bytes() == b"original" and not transport.calls
    monkeypatch.setattr(network.shutil, "disk_usage", lambda _: type("Disk", (), {"free": 0})())
    http, _ = client(Raw(b"bytes"))
    with pytest.raises(MaterialError, match="磁盘"):
        http.download("https://example.org/a", tmp_path / "new")
    assert not (tmp_path / "new").exists()


def test_json_error_and_headers_are_safe():
    http, _ = client(Raw(b"not json token=secret"))
    with pytest.raises(MaterialError) as error:
        http.get_json("https://example.org/?token=secret")
    assert "secret" not in str(error.value)
    for headers in [{"Host": "127.0.0.1"}, {"X-Test": "x\r\nHost: localhost"}]:
        http, transport = client()
        with pytest.raises(MaterialError):
            http.get_bytes("https://example.org/", headers=headers)
        assert not transport.calls
