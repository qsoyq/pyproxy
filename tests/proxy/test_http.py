import httpx

from httpx._types import ProxiesTypes

from pyproxy.settings import settings
from tests import proxy  # nopycln: import

_proxies_http: ProxiesTypes = {
    "http://": f"http://{settings.proxy_addr}:{settings.proxy_port}",
    "https://": f"http://{settings.proxy_addr}:{settings.proxy_port}",
}

_proxies_socks5: ProxiesTypes = {
    "http://": f"socks5://{settings.proxy_addr}:{settings.proxy_port}",
    "https://": f"socks5://{settings.proxy_addr}:{settings.proxy_port}",
}


def test_http(proxy):
    r = httpx.get("http://httpbin.org/json", timeout=10, proxies=_proxies_http)
    assert r.status_code == 200, r.text

    r = httpx.get("https://httpbin.org/json", timeout=10, proxies=_proxies_http)
    assert r.status_code == 200, r.text


def test_http_over_socks5(proxy):
    r = httpx.get("http://httpbin.org/json", timeout=10, proxies=_proxies_socks5)
    assert r.status_code == 200, r.text

    r = httpx.get("https://httpbin.org/json", timeout=10, proxies=_proxies_socks5)
    assert r.status_code == 200, r.text
