import ssl

import socks

from pyproxy.settings import settings
from tests import proxy  # nopycln: import


def test_tcp(proxy):
    s = socks.socksocket()
    s.set_proxy(socks.SOCKS5, f"{settings.proxy_addr}", settings.proxy_port)
    s.settimeout(10)
    s.connect(("httpbin.org", 80))

    body = (b"GET /json HTTP/1.1\r\n"
            b"Host: httpbin.org\r\n"
            b"User-Agent: curl/7.83.1"
            b"Accept: */*\r\n"
            b"\r\n")
    s.sendall(body)
    res = s.recv(4096)
    assert res.startswith(b'HTTP/1.1 200 OK'), res
    s.close()


def test_tcp_over_tls():
    s = socks.socksocket()
    s.set_proxy(socks.SOCKS5, f"{settings.proxy_addr}", settings.proxy_port)
    s.settimeout(10)
    context = ssl.create_default_context()
    with context.wrap_socket(s, server_hostname="httpbin.org") as ss:
        ss.connect(("httpbin.org", 443))
        body = (
            b"GET /json HTTP/1.1\r\n"
            b"Host: httpbin.org\r\n"
            b"User-Agent: curl/7.83.1"
            b"Accept: */*\r\n"
            b"\r\n"
        )
        ss.sendall(body)
        res = ss.recv(4096)
        assert res.startswith(b'HTTP/1.1 200 OK'), res
        ss.close()
