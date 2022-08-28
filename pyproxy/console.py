import asyncio
import logging

import typer

from pyproxy.protocols.socks import SocksProtocol
from pyproxy.protocols.udp import UdpProtocol
from pyproxy.settings import settings
from pyproxy.utils import initialize

_typer = typer.Typer()
logger = logging.getLogger(__name__)


async def start_server(host: str, port: int, **kwargs):
    initialize(**kwargs)

    loop = asyncio.get_event_loop()
    kws = {
        'reuse_port': True,
        'reuse_address': True,
    }

    udp_waiter = loop.create_future()
    asyncio.ensure_future(start_udp_server(udp_waiter, host, port))

    server = await asyncio.start_server(SocksProtocol.handler, host, port, **kws)
    logger.info(f'listening on {host}:{port}')
    async with server:
        await server.serve_forever()
    # TODO: 支持暂停或关闭服务


async def start_udp_server(waiter: asyncio.Future, host: str, port: int):
    loop = asyncio.get_event_loop()
    transport, _ = await loop.create_datagram_endpoint(UdpProtocol, local_addr=(host, port), reuse_port=True)
    await waiter
    transport.close()
    logger.info("udp transport closed")


@_typer.command()
def run(
    log_level: int = typer.Option(logging.DEBUG,
                                  '--log_level',
                                  envvar='log_level'),
    host: str = typer.Option("0.0.0.0",
                             "--host",
                             envvar='host'),
    port: int = typer.Option(7999,
                             '--port',
                             envvar='port'),
    enable_system_proxy: bool = typer.Option(False,
                                             '--enable_system_proxy',
                                             envvar='enable_system_proxy'),
    soft_limit: int = typer.Option(65535,
                                   '--soft_limit'),
    log_format: str = typer.Option(r'%(asctime)s %(levelname)s %(filename)s %(lineno)s %(message)s'),
):
    """启动 http 服务"""
    logging.basicConfig(level=log_level, format=log_format)
    kwargs = {
        "enable_system_proxy": enable_system_proxy,
        "soft_limit": soft_limit,
        "system_proxies": settings.system_proxies,
    }

    asyncio.run(start_server(host, port, **kwargs))


def main():
    _typer()


if __name__ == '__main__':
    main()
