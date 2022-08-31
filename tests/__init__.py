import asyncio
import socket
import threading

from typing import Generator

import pytest

from pyproxy.console import start_server
from pyproxy.settings import settings


@pytest.fixture(scope="session")
def proxy() -> Generator[threading.Thread, None, None]:
    coro = start_server(settings.host, settings.port)
    t = threading.Thread(target=asyncio.run, args=(coro, ), daemon=True)
    t.start()
    yield t
    # TODO: 等待后台服务清理退出


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
