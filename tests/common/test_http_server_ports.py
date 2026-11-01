"""静态服务器的端口选择：不能落到 Chromium 拒绝访问的端口上。"""
from __future__ import annotations

from m2v.engine import http_server


def test_ephemeral_port_retries_chromium_blocked_ports(monkeypatch, tmp_path):
    """实测过 1719：操作系统把它当空闲端口分配，页面却直接 ERR_UNSAFE_PORT。"""
    ports = iter([1719, 52341])
    created = []

    class FakeServer:
        def __init__(self, address, handler):
            self.server_address = (address[0], next(ports))
            created.append(self.server_address[1])

        def server_close(self):
            pass

        def shutdown(self):
            pass

        def serve_forever(self):
            pass

    monkeypatch.setattr(http_server, "ThreadingHTTPServer", FakeServer)
    server = http_server.LocalServer(tmp_path)
    try:
        assert server.start().endswith(":52341")
    finally:
        server.close()
    assert created == [1719, 52341], "撞上受限端口后必须重摇"


def test_explicit_port_is_honoured(monkeypatch, tmp_path):
    """调用方明确指定端口时不做重摇：那是它的选择，不是操作系统的分配。"""
    created = []

    class FakeServer:
        def __init__(self, address, handler):
            self.server_address = (address[0], address[1])
            created.append(address[1])

        def server_close(self):
            pass

        def shutdown(self):
            pass

        def serve_forever(self):
            pass

    monkeypatch.setattr(http_server, "ThreadingHTTPServer", FakeServer)
    server = http_server.LocalServer(tmp_path, port=1719)
    try:
        assert server.start().endswith(":1719")
    finally:
        server.close()
    assert created == [1719]
