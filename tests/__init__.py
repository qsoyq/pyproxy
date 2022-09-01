import asyncio
import socket
import threading

from typing import Generator

import pytest

from httpx._types import ProxiesTypes

from pyproxy.console import start_server
from pyproxy.settings import Settings

proxy_default_settings = Settings(host='127.0.0.1', port=7999, proxy_addr='127.0.0.1', proxy_port=7999)
proxy_settings = Settings(host='127.0.0.1', port=7555, proxy_addr='127.0.0.1', proxy_port=7555)
proxy_over_host_settings = Settings(host='127.0.0.1', port=7888, proxy_addr='localhost', proxy_port=7888)


@pytest.fixture(scope="session")
def proxy() -> Generator[threading.Thread, None, None]:
    coro = start_server(
        proxy_default_settings.host,
        proxy_default_settings.port,
        proxy_addr=proxy_default_settings.proxy_addr,
        proxy_port=proxy_default_settings.proxy_port
    )
    t = threading.Thread(target=asyncio.run, args=(coro, ), daemon=True)
    t.start()
    yield t


@pytest.fixture(scope="session")
def proxy_with_settings() -> Generator[threading.Thread, None, None]:
    coro = start_server(proxy_settings.host, proxy_settings.port, settings=proxy_settings)
    t = threading.Thread(target=asyncio.run, args=(coro, ), daemon=True)
    t.start()
    yield t


@pytest.fixture(scope="session")
def proxy_over_host() -> Generator[threading.Thread, None, None]:
    coro = start_server(
        proxy_over_host_settings.host,
        proxy_over_host_settings.port,
        settings=proxy_over_host_settings
    )
    t = threading.Thread(target=asyncio.run, args=(coro, ), daemon=True)
    t.start()
    yield t


@pytest.fixture(scope="session")
def udp_echo_server() -> Generator[threading.Thread, None, None]:
    t = threading.Thread(target=_udp_echo_server, daemon=True)
    t.start()
    yield t


def _udp_echo_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_address = '0.0.0.0'
    server_port = 31337

    server = (server_address, server_port)
    sock.bind(server)
    while True:
        payload, client_address = sock.recvfrom(4096)
        sent = sock.sendto(payload, client_address)


def base_settings():
    return Settings(host='127.0.0.1', port=7999, proxy_addr='127.0.0.1', proxy_port=7999)


def _proxies_http(settings: Settings) -> ProxiesTypes:
    return {
        "http://": f"http://{settings.proxy_addr}:{settings.proxy_port}",
        "https://": f"http://{settings.proxy_addr}:{settings.proxy_port}",
    }


def _proxies_socks5(settings: Settings) -> ProxiesTypes:
    return {
        "http://": f"socks5://{settings.proxy_addr}:{settings.proxy_port}",
        "https://": f"socks5://{settings.proxy_addr}:{settings.proxy_port}",
    }
