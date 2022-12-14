import socket

import httpx

from tests import proxy  # nopycln: import
from tests import _proxies_http, _proxies_socks5, proxy_default_settings


def test_http(proxy):
    settings = proxy_default_settings
    r = httpx.get("http://httpbin.org/json", timeout=10, proxies=_proxies_http(settings))
    assert r.status_code == 200, r.text

    r = httpx.get("https://httpbin.org/json", timeout=10, proxies=_proxies_http(settings))
    assert r.status_code == 200, r.text


def test_http_over_ip(proxy):
    settings = proxy_default_settings
    ip = socket.gethostbyname("httpbin.org")
    r = httpx.get(f"http://{ip}/json", timeout=10, proxies=_proxies_http(settings))
    assert r.status_code == 200, r.text


def test_http_over_socks5(proxy):
    settings = proxy_default_settings
    r = httpx.get("http://httpbin.org/json", timeout=10, proxies=_proxies_socks5(settings))
    assert r.status_code == 200, r.text

    r = httpx.get("https://httpbin.org/json", timeout=10, proxies=_proxies_socks5(settings))
    assert r.status_code == 200, r.text


def test_http_over_ip_socks5(proxy):
    settings = proxy_default_settings
    ip = socket.gethostbyname("httpbin.org")
    r = httpx.get(f"http://{ip}/json", timeout=10, proxies=_proxies_socks5(settings))
    assert r.status_code == 200, r.text
