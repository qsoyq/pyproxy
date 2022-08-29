import asyncio
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
