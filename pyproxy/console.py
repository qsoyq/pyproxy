import asyncio
import logging
import urllib.request

from typing import Optional

import typer

import pyproxy

from pyproxy.protocols.socks import SocksProtocol
from pyproxy.protocols.udp import UdpProtocol
from pyproxy.settings import _settings
from pyproxy.utils import initialize

_typer = typer.Typer()
logger = logging.getLogger(__name__)


async def start_server(host: str, port: int, **kwargs):
    token = initialize(host=host, port=port, **kwargs)

    loop = asyncio.get_event_loop()
    kws = {
        'reuse_port': True,
        'reuse_address': True,
    }

    udp_waiter = loop.create_future()
    asyncio.ensure_future(start_udp_server(udp_waiter, host, port))

    server = await asyncio.start_server(SocksProtocol.handler, host, port, **kws)
    logger.info(f'listening on {host}:{port}')
    try:
        async with server:
            await server.serve_forever()
    except Exception:
        pass
    finally:
        _settings.reset(token)
    # TODO: 支持暂停或关闭服务


async def start_udp_server(waiter: asyncio.Future, host: str, port: int):
    loop = asyncio.get_event_loop()
    transport, _ = await loop.create_datagram_endpoint(UdpProtocol, local_addr=(host, port), reuse_port=True)
    await waiter
    transport.close()
    logger.info("udp transport closed")


def version_callback(value: bool):
    if value:
        print(f"PyProxy CLI Version: {pyproxy.__version__}")
        raise typer.Exit()


@_typer.command()
def run(
    log_level: int = typer
    .Option(logging.INFO,
            '--log_level',
            envvar='log_level',
            help='日志级别, DEBUG:10, INFO: 20, WARNING: 30, ERROR:40'),
    host: str = typer.Option("0.0.0.0",
                             "--host",
                             envvar='host',
                             help='服务监听地址'),
    port: int = typer.Option(7999,
                             '--port',
                             envvar='port',
                             help='服务监听端口'),
    enable_system_proxy: bool = typer
    .Option(False,
            '--enable_system_proxy',
            envvar='enable_system_proxy',
            help='是否启用系统代理'),
    soft_limit: int = typer.Option(65535,
                                   '--soft_limit'),
    log_format: str = typer.Option(r'%(asctime)s %(levelname)s %(filename)s %(lineno)s %(message)s'),
    proxy_addr: str = typer.Option('127.0.0.1',
                                   '--proxy_addr',
                                   envvar='proxy_addr',
                                   help='客户端访问的目标地址'),
    proxy_port: int = typer.Option(7999,
                                   '--proxy_port',
                                   envvar='proxy_port',
                                   help='客户端访问的目标端口'),
    version: Optional[bool] = typer.Option(None,
                                           "--version",
                                           callback=version_callback),
):
    """https://github.com/qsoyq/pyproxy"""
    logging.basicConfig(level=log_level, format=log_format)
    kwargs = {
        "enable_system_proxy": enable_system_proxy,
        "soft_limit": soft_limit,
        "system_proxies": urllib.request.getproxies(),
        "proxy_addr": proxy_addr,
        "proxy_port": proxy_port,
    }

    asyncio.run(start_server(host, port, **kwargs))


def main():
    _typer()


if __name__ == '__main__':
    main()
