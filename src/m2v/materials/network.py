"""制作期受控 HTTP；域名解析结果直接用于连接，不依赖环境代理。

所有派生请求（含平台分片）必须复用本传输。注入 transport/resolver 是离线测试
边界，而不是关闭私网保护的运行参数。响应、日志和恢复旁车不保存带签名的 URL。
"""
from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import gzip
import hashlib
import http.client
import io
import ipaddress
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import threading
import time
from typing import Callable, Mapping
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request

from .errors import MaterialError
from .paths import no_links

_LOG = logging.getLogger(__name__)
_REDIRECTS = {301, 302, 303, 307, 308}
_RETRY_STATUS = {408, 429, 500, 502, 503, 504}
_BLOCKED_HEADERS = {"host", "proxy-authorization", "proxy-connection", "connection", "transfer-encoding", "upgrade", "expect", "te", "trailer"}
# OS DNS 没有可移植的强制取消接口：有限 daemon 槽位防止超时请求积累无限线程。
_DNS_SLOTS = threading.BoundedSemaphore(4)


def _error(code: str, message: str, *, retryable: bool = False) -> MaterialError:
    return MaterialError(code, message, stage="network", retryable=retryable)


def public_url(url: str) -> str:
    """供公开记录使用；删除全部查询和 fragment，不猜测 token 参数名称。"""
    try:
        parts = urlsplit(str(url))
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return "[redacted-url]"
        host = parts.hostname.encode("idna").decode("ascii")
        host = f"[{host}]" if ":" in host else host
        port = parts.port
        netloc = host + (f":{port}" if port and port not in {80, 443} else "")
        # Long opaque path segments can themselves be bearer credentials.
        path = "/".join("[redacted]" if len(x) > 96 else x for x in parts.path.split("/"))
        query = ""
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com"} and path == "/watch":
            values = dict(parse_qsl(parts.query))
            if re.fullmatch(r"[A-Za-z0-9_-]{1,32}", values.get("v", "")):
                query = urlencode({"v": values["v"]})
        return urlunsplit((parts.scheme, netloc, path, query, ""))
    except (ValueError, UnicodeError):
        return "[redacted-url]"


def redact_text(text: str, *, secrets: tuple[str, ...] = (), limit: int = 2000) -> str:
    value = str(text)
    for secret in secrets:
        if secret:
            value = value.replace(secret, "[redacted]")
    value = re.sub(r"https?://[^\s<>\"']+", lambda m: public_url(m.group()), value)
    value = re.sub(r"(?i)\b(cookie|authorization|api[_-]?key|token|password)\s*[:=]\s*[^\s,;]+", r"\1=[redacted]", value)
    return value[:limit]


def public_ip(value: str) -> str:
    """仅允许普通全球可路由地址；保守拒绝 IPv6 过渡隧道。"""
    try:
        if "%" in value:
            raise ValueError("scope")
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address):
            if address.ipv4_mapped is not None:
                public_ip(str(address.ipv4_mapped))
            if address.sixtofour is not None or address.teredo is not None:
                raise ValueError("transition")
            if address in ipaddress.ip_network("64:ff9b::/96") or address in ipaddress.ip_network("64:ff9b:1::/48"):
                raise ValueError("nat64")
        if not address.is_global or any((address.is_private, address.is_loopback, address.is_link_local,
                                         address.is_multicast, address.is_reserved, address.is_unspecified)):
            raise ValueError("non-public")
        return str(address)
    except ValueError:
        raise _error("security-blocked", "网络目标不是允许的公开地址") from None


@dataclass(frozen=True)
class URLTarget:
    url: str
    scheme: str
    host: str
    port: int
    path: str

    @property
    def origin(self) -> tuple[str, str, int]:
        return self.scheme, self.host, self.port


def validate_url(url: str) -> URLTarget:
    if (not isinstance(url, str) or len(url) > 32768 or url.startswith(' ')
            or re.search(r"[\x00-\x1f\x7f\\]", url)):
        raise _error("security-blocked", "URL 含不允许字符或超过长度限制")
    try:
        p = urlsplit(url)
        if p.scheme not in {"http", "https"} or not p.hostname or p.username is not None or p.password is not None:
            raise ValueError("scheme or credentials")
        host = p.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        port = p.port or (443 if p.scheme == "https" else 80)
        if port not in {80, 443} or not host or "%" in host:
            raise ValueError("port or scope")
        # Numeric shorthand, octal and hexadecimal forms are resolved by some OSes.
        # Only canonical IP syntax or an ordinary DNS name is accepted here.
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host or re.fullmatch(r"[0-9.]+", host):
                raise ValueError("ambiguous host")
            if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in host.split(".")):
                raise ValueError("invalid DNS name")
            if any(label.startswith("0x") for label in host.split(".")):
                raise ValueError("ambiguous numeric host")
        else:
            public_ip(str(address))
        encoded_path = quote(p.path or '/', safe="/%:@!$&'()*+,;=-._~")
        query = quote(p.query, safe="/?@!$&'()*+,;=:%-._~")
        path = encoded_path + ('?' + query if query else '')
        normalized_host = f'[{host}]' if ':' in host else host
        default_port = 443 if p.scheme == 'https' else 80
        netloc = normalized_host + (f':{port}' if port != default_port else '')
        return URLTarget(urlunsplit((p.scheme, netloc, encoded_path, query, '')), p.scheme, host, port, path)
    except (ValueError, UnicodeError):
        raise _error("security-blocked", "仅允许无内嵌凭据、80/443 端口的公开 HTTP(S) URL") from None


def resolve_public(target: URLTarget, resolver: Callable = socket.getaddrinfo) -> list[tuple]:
    try:
        entries = resolver(target.host, target.port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        raise _error("network-unavailable", "公开来源 DNS 解析失败", retryable=True) from None
    if not entries:
        raise _error("network-unavailable", "公开来源没有可连接地址", retryable=True)
    checked = []
    for family, socktype, proto, canonname, sockaddr in entries:
        if family not in {socket.AF_INET, socket.AF_INET6} or socktype != socket.SOCK_STREAM:
            raise _error("security-blocked", "DNS 返回不受支持的地址族")
        public_ip(sockaddr[0])  # 任一受限结果即拒绝整个解析，不能挑一个公开地址掩盖混合 DNS。
        if sockaddr[1] != target.port or (family == socket.AF_INET6 and len(sockaddr) > 3 and sockaddr[3]):
            raise _error("security-blocked", "DNS 返回异常端口或 IPv6 scope")
        checked.append((family, socktype, proto, canonname, sockaddr))
    return checked


@dataclass(frozen=True)
class NetworkBudget:
    max_bytes: int = 512 * 1024 * 1024
    total_bytes: int = 2 * 1024 * 1024 * 1024
    timeout_s: float = 30.0
    deadline_s: float = 300.0
    retries: int = 2
    max_redirects: int = 8
    max_requests: int = 1000
    retry_delay_s: float = 1.0
    max_retry_after_s: float = 30.0
    min_free_bytes: int = 64 * 1024 * 1024

    def __post_init__(self):
        integers = ("max_bytes", "total_bytes", "retries", "max_redirects", "max_requests", "min_free_bytes")
        for name in integers:
            value = getattr(self, name)
            if type(value) is not int or value < (1 if name in {"max_bytes", "total_bytes", "max_requests"} else 0):
                raise _error("invalid-request", f"非法网络预算：{name}")
        for name in ("timeout_s", "deadline_s", "retry_delay_s", "max_retry_after_s"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise _error("invalid-request", f"非法网络预算：{name}")
        if self.timeout_s <= 0 or self.deadline_s <= 0 or self.retries > 10 or self.max_redirects > 20:
            raise _error("invalid-request", "网络预算超出有限范围")


class _Meter:
    def __init__(self, budget: NetworkBudget, clock: Callable, cancelled: Callable | None, resource_check=None):
        self.budget, self.clock, self.cancelled = budget, clock, cancelled
        self.resource_check = resource_check
        self.started = clock()
        self._next_resource_check = self.started
        self.bytes = 0
        self.requests = 0
        self.lock = threading.Lock()

    def check(self):
        if self.cancelled and self.cancelled():
            raise _error("cancelled", "素材网络操作已取消")
        now = self.clock()
        if now - self.started >= self.budget.deadline_s:
            raise _error("network-timeout", "素材网络操作超过总时限", retryable=True)
        if self.resource_check and now >= self._next_resource_check:
            self.resource_check()
            self._next_resource_check = now + 0.25

    def request(self):
        with self.lock:
            self.check()
            if self.requests >= self.budget.max_requests:
                raise _error("resource-limit", "达到网络请求数量预算")
            self.requests += 1

    def consume(self, amount: int):
        with self.lock:
            self.check()
            self.bytes += amount
            if self.bytes > self.budget.total_bytes:
                raise _error("resource-limit", "达到网络总流量预算")


class _WireReader(io.RawIOBase):
    def __init__(self, raw, meter: _Meter, limit: int):
        self.raw, self.meter, self.limit, self.count = raw, meter, limit, 0

    def readable(self):
        return True

    def read(self, size=-1):
        self.meter.check()
        size = min(65536, self.limit - self.count + 1) if size is None or size < 0 else min(size, self.limit - self.count + 1)
        try:
            value = self.raw.read(size)
        except (OSError, http.client.HTTPException):
            raise _error("network-unavailable", "读取公开来源时连接中断", retryable=True) from None
        self.count += len(value)
        self.meter.consume(len(value))
        if self.count > self.limit:
            raise _error("resource-limit", "响应超过单件字节预算")
        return value


class SafeResponse(io.RawIOBase):
    """限量流；read(None) 也分块解码，避免 gzip/未知长度响应绕过预算。"""
    def __init__(self, raw, closer: Callable, target: URLTarget, meter: _Meter, limit: int):
        self.raw, self._closer, self._meter, self._limit = raw, closer, meter, limit
        self.url, self.status, self.reason = target.url, raw.status, getattr(raw, "reason", "")
        self.headers = raw.headers
        self._wire = _WireReader(raw, meter, limit)
        self._decoded_count = 0
        encoding = str(self.headers.get("Content-Encoding", "identity")).lower().strip()
        if encoding not in {"", "identity", "gzip", "x-gzip"}:
            self.close()
            raise _error("unsupported-source", "响应采用尚未受控支持的压缩格式")
        self._decoded = gzip.GzipFile(fileobj=self._wire) if encoding in {"gzip", "x-gzip"} else self._wire

    def readable(self):
        return True

    def info(self):
        return self.headers

    def geturl(self):
        return self.url

    def read(self, size=-1):
        if self.closed:
            return b""
        if size is None or size < 0:
            chunks = []
            while chunk := self.read(65536):
                chunks.append(chunk)
            return b"".join(chunks)
        self._meter.check()
        try:
            data = self._decoded.read(min(size, self._limit - self._decoded_count + 1))
        except (EOFError, gzip.BadGzipFile):
            raise _error("media-invalid", "响应压缩内容损坏") from None
        self._decoded_count += len(data)
        if self._decoded_count > self._limit:
            raise _error("resource-limit", "解压响应超过单件字节预算")
        return data

    def close(self):
        if not self.closed:
            self.raw.close()
            self._closer()
        super().close()


def _exchange(target, addresses, method, headers, data, timeout):
    """只连接校验时返回的数值 sockaddr；HTTPS SNI/证书仍验证原始域名。"""
    connection = (http.client.HTTPSConnection(target.host, target.port, timeout=timeout,
                    context=ssl.create_default_context()) if target.scheme == "https"
                  else http.client.HTTPConnection(target.host, target.port, timeout=timeout))

    def connect(address, timeout=timeout, source_address=None, **_):
        last_error = None
        deadline = time.monotonic() + timeout
        for family, socktype, proto, _, sockaddr in addresses:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('public connection deadline')
            sock = socket.socket(family, socktype, proto)
            try:
                sock.settimeout(remaining)
                sock.connect(sockaddr)
                return sock
            except OSError as exc:
                sock.close()
                last_error = exc
        raise last_error or OSError("No public address")

    connection._create_connection = connect
    try:
        connection.request(method, target.path, body=data, headers=headers)
        return connection.getresponse(), connection.close
    except BaseException:
        connection.close()
        raise


def _headers(values: Mapping[str, str] | None) -> dict[str, str]:
    result = {"User-Agent": "material2video/1.0 (controlled material acquisition)", "Accept-Encoding": "identity"}
    for key, value in (values or {}).items():
        if (not isinstance(key, str) or not isinstance(value, str)
                or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key) or re.search(r"[\x00-\x1f\x7f]", value)):
            raise _error("security-blocked", "非法 HTTP 请求头")
        if key.lower() in _BLOCKED_HEADERS:
            raise _error("security-blocked", "不允许覆盖连接或代理请求头")
        if key.lower() not in {"accept-encoding", "content-length"}:
            result[key] = value
    return result


def _status_error(status: int) -> MaterialError:
    code = {401: "auth-required", 403: "access-denied", 404: "not-found", 410: "source-removed", 429: "rate-limited"}.get(status, "network-unavailable")
    return _error(code, f"公开来源返回 HTTP {status}", retryable=status in _RETRY_STATUS)


class SafeHTTP:
    def __init__(self, budget: NetworkBudget | None = None, *, resolver: Callable | None = None,
                 transport: Callable | None = None, cancelled: Callable | None = None,
                 clock: Callable = time.monotonic, sleep: Callable = time.sleep, resource_check=None):
        self.budget = budget or NetworkBudget()
        # 默认解析器在发请求时查找，使隔离 worker 的 socket 守卫不会被旧绑定绕过。
        self.resolver, self.transport = resolver, transport or _exchange
        self._clock, self._sleep = clock, sleep
        self._meter = _Meter(self.budget, clock, cancelled, resource_check)

    def check(self) -> None:
        """适配器在本地拼接/下载进度处复用取消、总时限与资源护栏。"""
        self._meter.check()

    @property
    def stats(self) -> dict:
        return {"bytes": self._meter.bytes, "requests": self._meter.requests,
                "elapsedSeconds": max(0, self._clock() - self._meter.started)}

    def _resolve(self, target: URLTarget) -> list[tuple]:
        if self.resolver is not None:
            return resolve_public(target, self.resolver)  # 显式注入仅用于可控适配器和离线测试。
        started, done, outcome = self._clock(), threading.Event(), []
        def check():
            self._meter.check()
            if self._clock() - started >= self.budget.timeout_s:
                raise _error('network-timeout', '公开来源 DNS 解析超过时限', retryable=True)
        while not _DNS_SLOTS.acquire(timeout=0.05):
            check()
        resolver = socket.getaddrinfo  # 必须在 worker 守卫已生效之后捕获。
        def resolve():
            try:
                outcome.append(resolve_public(target, resolver))
            except BaseException as exc:
                outcome.append(exc)
            finally:
                _DNS_SLOTS.release()
                done.set()
        try:
            thread = threading.Thread(target=resolve, name='m2v-public-dns', daemon=True)
            thread.start()
        except BaseException:
            _DNS_SLOTS.release()
            raise
        while not done.wait(0.05):
            check()
        check()
        if isinstance(outcome[0], BaseException):
            raise outcome[0]
        return outcome[0]

    def _wait(self, seconds):
        until = self._clock() + seconds
        while self._clock() < until:
            self._meter.check()
            self._sleep(min(0.2, until - self._clock()))

    def _delay(self, response, attempt):
        delay = self.budget.retry_delay_s * (2 ** attempt)
        value = response.headers.get("Retry-After")
        if value:
            try:
                delay = float(value)
            except ValueError:
                try:
                    delay = max(0, parsedate_to_datetime(value).timestamp() - time.time())
                except (TypeError, ValueError, OverflowError):
                    pass
        if not math.isfinite(delay) or delay > self.budget.max_retry_after_s:
            raise _error("rate-limited", "服务端要求的等待超过本次有限预算，请稍后重试", retryable=True)
        return max(0, delay)

    def open(self, url: str, *, method: str = "GET", headers: Mapping[str, str] | None = None,
             data: bytes | None = None, max_bytes: int | None = None, cookiejar=None,
             timeout_s: float | None = None, allow_http_errors: bool = False) -> SafeResponse:
        if method not in {"GET", "HEAD", "POST"} or (data is not None and (not isinstance(data, bytes) or len(data) > 2 * 1024 * 1024)):
            raise _error("security-blocked", "HTTP 方法或请求体超出受控范围")
        limit = self.budget.max_bytes if max_bytes is None else max_bytes
        if type(limit) is not int or not 0 < limit <= self.budget.max_bytes:
            raise _error("invalid-request", "响应字节上限必须在单件预算内")
        current, request_headers = validate_url(url), _headers(headers)
        redirects = 0
        attempt = 0
        while True:
            self._meter.request()
            addresses = self._resolve(current)
            req = Request(current.url, headers=request_headers, method=method, data=data)
            if cookiejar is not None:
                cookiejar.add_cookie_header(req)
            timeout = min(timeout_s or self.budget.timeout_s, self.budget.timeout_s,
                          self.budget.deadline_s - (self._clock() - self._meter.started))
            try:
                raw, closer = self.transport(current, addresses, method, dict(req.header_items()), data, max(0.01, timeout))
                response = SafeResponse(raw, closer, current, self._meter, limit)
            except (OSError, http.client.HTTPException):
                if method not in {"GET", "HEAD"} or attempt >= self.budget.retries:
                    raise _error("network-unavailable", "连接公开来源失败", retryable=True) from None
                _LOG.warning("素材网络连接重试 source=%s attempt=%s", public_url(current.url), attempt + 1)
                self._wait(min(self.budget.retry_delay_s * 2**attempt, self.budget.max_retry_after_s))
                attempt += 1
                continue
            if cookiejar is not None:
                cookiejar.extract_cookies(response, req)
            if response.status in _REDIRECTS:
                location = response.headers.get("Location")
                response.close()
                if not location or redirects >= self.budget.max_redirects:
                    raise _error("security-blocked", "重定向缺少地址或超出次数预算")
                next_target = validate_url(urljoin(current.url, location))
                cross_origin = current.origin != next_target.origin
                if cross_origin and response.status in {307, 308} and data:
                    raise _error("security-blocked", "拒绝跨来源保留敏感请求体的重定向")
                if cross_origin:
                    # 非标准 token 请求头无法穷举；跨源只保留明确无会话信息的头。
                    request_headers = {k: v for k, v in request_headers.items()
                                       if k.lower() in {"user-agent", "accept", "accept-language", "accept-encoding", "range", "if-range"}}
                if response.status == 303 or (response.status in {301, 302} and method == "POST"):
                    method, data = "GET", None
                    request_headers = {k: v for k, v in request_headers.items() if k.lower() not in {"content-type", "content-length"}}
                current, redirects = next_target, redirects + 1
                continue
            if response.status in _RETRY_STATUS and method in {"GET", "HEAD"} and attempt < self.budget.retries:
                try:
                    delay = self._delay(response, attempt)
                finally:
                    response.close()
                _LOG.warning("素材来源有限重试 source=%s status=%s attempt=%s", public_url(current.url), response.status, attempt + 1)
                self._wait(delay)
                attempt += 1
                continue
            if not allow_http_errors and not 200 <= response.status < 300:
                response.close()
                raise _status_error(response.status)
            length = response.headers.get("Content-Length")
            if length and method != "HEAD":
                try:
                    if int(length) < 0 or int(length) > limit:
                        response.close()
                        raise _error("resource-limit", "响应声明长度超过单件预算")
                except ValueError:
                    response.close()
                    raise _error("media-invalid", "响应长度无效") from None
            return response

    def get_bytes(self, url: str, *, headers=None, max_bytes: int | None = None) -> bytes:
        with self.open(url, headers=headers, max_bytes=max_bytes) as response:
            return response.read()

    def get_json(self, url: str, *, headers=None, max_bytes: int | None = None):
        limit = min(self.budget.max_bytes, 8 * 1024 * 1024) if max_bytes is None else max_bytes
        try:
            return json.loads(self.get_bytes(url, headers=headers, max_bytes=limit))
        except (ValueError, UnicodeError):
            raise _error("media-invalid", "公开接口未返回有效 JSON") from None

    def download(self, url: str, destination: Path | str, *, headers=None, max_bytes: int | None = None,
                 resume: bool = True) -> dict:
        """下载至调用方明确的暂存路径；成功才发布，验证后的中断可保留以续传。

        恢复旁车只保存 URL 身份摘要、强 ETag 或 last-modified+总长度及已取内容
        摘要。服务器未证明相同版本时从头获取，绝不把新版本接到旧字节。
        """
        validate_url(url)
        target = no_links(Path(destination), stage='network')  # mkdir 前检查，包括已断开的联接。
        if target.exists():
            raise _error("conflict", "下载目标已存在，不能覆盖")
        target.parent.mkdir(parents=True, exist_ok=True)
        no_links(target, stage='network')
        part = target.with_name(target.name + ".part")
        sidecar = target.with_name(target.name + ".resume.json")
        for entry in (part, sidecar):
            no_links(entry, stage='network')
            if entry.exists():
                info = entry.lstat()
                if getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_nlink != 1 or not entry.is_file():
                    raise _error("security-blocked", "恢复文件必须是非链接的独立普通文件")
        limit = self.budget.max_bytes if max_bytes is None else max_bytes
        identity = hashlib.sha256(url.encode()).hexdigest()
        state, offset = {}, 0
        if resume and part.is_file() and sidecar.is_file():
            try:
                state = json.loads(sidecar.read_text(encoding="utf-8"))
                length = part.stat().st_size
                strong = isinstance(state.get('etag'), str) and not state['etag'].startswith('W/')
                if not strong:
                    state['etag'] = None
                validator = strong or (state.get("lastModified") and type(state.get("total")) is int)
                if (state.get("urlIdentity") == identity and validator and 0 < length < state.get("total", 0)
                        and length == state.get("bytes") and _file_hash(part) == state.get("sha256")):
                    offset = length
            except (OSError, ValueError, TypeError, AttributeError):
                state = {}
        request_headers = dict(headers or {})
        if offset:
            request_headers.update({"Range": f"bytes={offset}-", "If-Range": state.get("etag") or state["lastModified"]})
        response = self.open(url, headers=request_headers, max_bytes=limit)
        with response:
            total = None
            if response.headers.get("Content-Encoding", "identity").lower() not in {"", "identity"}:
                raise _error("unsupported-source", "文件下载不接受压缩封装，以保持续传字节身份")
            if response.headers.get("Content-Length"):
                try:
                    total = int(response.headers['Content-Length'])
                    if total < 0:
                        raise ValueError
                except ValueError:
                    raise _error('media-invalid', '来源返回无效文件长度') from None
            if response.status == 206:
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                same_validator = ((state.get("etag") and response.headers.get("ETag") == state["etag"])
                                  or (not state.get("etag") and response.headers.get("Last-Modified") == state.get("lastModified")))
                if (not offset or not match or int(match[1]) != offset or int(match[2]) < offset
                        or int(match[2]) != int(match[3]) - 1
                        or (total is not None and total != int(match[2]) - int(match[1]) + 1)
                        or int(match[3]) != state.get("total") or not same_validator):
                    raise _error("hash-mismatch", "续传响应未证明文件版本及区间一致")
                total = int(match[3])
            else:
                offset = 0
            if total is not None and total > limit:
                raise _error("resource-limit", "源文件超过下载预算")
            _disk_guard(target.parent, self.budget.min_free_bytes, max(0, (total or 65536) - offset))
            record = {"urlIdentity": identity, "etag": response.headers.get("ETag"),
                      "lastModified": response.headers.get("Last-Modified"), "total": total}
            written = offset
            try:
                with part.open("ab" if offset else "wb") as output:
                    while chunk := response.read(65536):
                        written += len(chunk)
                        if written > limit:
                            raise _error("resource-limit", "源文件超过下载预算")
                        _disk_guard(target.parent, self.budget.min_free_bytes, len(chunk))
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                if total is not None and written != total:
                    raise _error("network-unavailable", "源文件传输未完成", retryable=True)
                if written == 0:
                    raise _error("media-invalid", "源文件为空")
                digest = _file_hash(part)
                # O_EXCL 占位防止并发操作覆盖已有文件；正式调用者仍须探测后发布素材。
                fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                try:
                    for attempt in range(3):
                        try:
                            os.replace(part, target)
                            break
                        except PermissionError:
                            if os.name != 'nt' or attempt == 2:
                                raise
                            # Windows 扫描/打开句柄可能暂时拒绝同一次原子替换。只限次重试，
                            # 不更改权限、不退化为覆盖复制，最终仍失败则保留 .part。
                            _LOG.debug('本地原子发布被 Windows 暂时拒绝，有限重试 attempt=%d', attempt + 1)
                            self._wait(0.05 * (attempt + 1))
                except BaseException:
                    target.unlink(missing_ok=True)
                    raise
                sidecar.unlink(missing_ok=True)
                return {"path": str(target), "bytes": written, "sha256": digest,
                        "sourceUrl": public_url(response.url), "resumedBytes": offset,
                        "transferredBytes": self.stats["bytes"], "requests": self.stats["requests"],
                        "elapsedSeconds": self.stats["elapsedSeconds"]}
            except BaseException:
                if part.is_file():
                    record.update(bytes=part.stat().st_size, sha256=_file_hash(part))
                    sidecar.write_text(json.dumps(record), encoding="utf-8")
                raise


def _disk_guard(directory: Path, floor: int, pending: int):
    if shutil.disk_usage(directory).free - pending < floor:
        raise _error("resource-limit", "磁盘剩余空间不足，停止获取")


def _file_hash(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()
