import asyncio
import logging
import time

from collections import defaultdict
from typing import Dict, Tuple, Union

from pyproxy._types import UDP_MAPPING_TABLE_TYPE
from pyproxy.settings import settings
from pyproxy.utils import Socks5ProxyParser, release_udp_transport

logger = logging.getLogger(__name__)


class UdpForwardProtocol(asyncio.protocols.DatagramProtocol):

    def __init__(
        self,
        manager: UDP_MAPPING_TABLE_TYPE,
        last_activity: Dict[Tuple[str,
                                  int],
                            Union[int,
                                  float]],
        header: bytes,
        dst_transport: asyncio.transports.DatagramTransport,
        dst: Tuple[str,
                   int]
    ):
        self._header = header
        self._dst_transport = dst_transport
        self._dst = dst
        self._last_activity = last_activity
        self._manager = manager
        logger.info(f"[UdpForwardProtocol] {dst}")

    def __repr__(self):
        return f'<UdpForwardProtocol dst={self._dst}>'

    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        logger.debug(f'[UdpForwardProtocol] datagram_received, {addr!r}, {data!r}')
        self.sendto(data, self._dst)

    def sendto(self, data: bytes, addr: Tuple[str, int]):
        self._dst_transport.sendto(self._header + data, addr)
        self._last_activity[self._dst] = time.time()

    def error_received(self, exc):
        logger.warning(f'[UdpForwardProtocol] error received:{exc!r}\n\n')
        release_udp_transport(self._dst, self._manager, self._last_activity)

    def connection_lost(self, exc):
        if exc is not None:
            logger.warning(f'[UdpForwardProtocol] connection lost:{exc!r}\n\n')
        logger.debug(f'[UdpForwardProtocol] connection lost: {self._dst}')
        release_udp_transport(self._dst, self._manager, self._last_activity)


class UdpProtocol(asyncio.DatagramProtocol):

    KEEPALIVE_LOOP_WAIT = 1
    MANAGER: Dict[Tuple[str, int], Tuple[asyncio.DatagramTransport, asyncio.BaseProtocol]] = {}
    LAST_ACTIVITY: Dict[Tuple[str, int], float] = defaultdict(int)

    def __init__(self):
        self._manager: Dict[Tuple[str, int], Tuple[asyncio.BaseTransport, asyncio.BaseProtocol]] = {}
        self._last_activity: Dict[Tuple[str, int], float] = defaultdict(int)
        asyncio.ensure_future(self.keepalive_loop())

    async def keepalive_loop(self):
        # 释放超时连接
        while True:
            await asyncio.sleep(self.KEEPALIVE_LOOP_WAIT)
            cur = time.time()
            keys = list(self._last_activity.keys())
            for dst in keys:
                v = self._last_activity[dst]
                if v + settings.udp_keep_alive_timeout >= cur:
                    continue
                release_udp_transport(dst, self.MANAGER, self.LAST_ACTIVITY)

    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self._last_activity[addr] = time.time()
        loop = asyncio.get_running_loop()
        loop.create_task(self.handle_datagram_received(data, addr))

    async def handle_datagram_received(self, data: bytes, addr: Tuple[str, int]):
        logger.info(f"manager: {len(self._manager)} {self._manager!r}")
        dst, header, message = Socks5ProxyParser.unpack(data)
        logger.info(f"addr: {addr}, dst: {dst}, header: {header}, message: {message}")

        if dst is None or message is None:
            self.transport.close()
            return

        if addr not in self.MANAGER:
            loop = asyncio.get_running_loop()
            remote_transport, remote_protocol = await loop.create_datagram_endpoint(
                lambda: UdpForwardProtocol(self.MANAGER, self.LAST_ACTIVITY, header, self.transport, addr), remote_addr=dst)
            self.MANAGER[addr] = (remote_transport, remote_protocol)  # type: ignore
        self.MANAGER[addr][0].sendto(message)

    def error_received(self, exc):
        logger.warning(f'Error received:{exc!r}')

    def connection_lost(self, exc):
        logger.debug(f"Connection Lost {exc!r}\n\n")
