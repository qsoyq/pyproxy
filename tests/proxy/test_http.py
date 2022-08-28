import httpx

from httpx._types import ProxiesTypes

from pyproxy.settings import settings

_proxies: ProxiesTypes = {
    "http://": f"http://{settings.proxy_addr}:{settings.proxy_port}",
    "https://": f"http://{settings.proxy_addr}:{settings.proxy_port}",
}


def test_http(proxy):
    r = httpx.get("http://httpbin.org/json", timeout=10, proxies=_proxies)
    assert r.status_code == 200, r.text

    r = httpx.get("https://httpbin.org/json", timeout=10, proxies=_proxies)
    assert r.status_code == 200, r.text
