import asyncio
import logging
import socket
import struct
import traceback
import urllib.parse

from typing import Optional, Tuple, Union

from pyproxy.const import HTTP_PROXY_CONNECT_RESPONSE, ProxyCMD, Socks5CMD
from pyproxy.errors import ConnectError
from pyproxy.protocols.udp import UdpProtocol
from pyproxy.settings import settings
from pyproxy.utils import Socks5ProxyParser, release_udp_transport

logger = logging.getLogger(__name__)


class SocksProtocol(asyncio.protocols.Protocol):

    READ_LIMIT = 2**16

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        raddr = writer.transport.get_extra_info('peername')
        logger.debug(f'accept from: {raddr!r}')

        self.client = (reader, writer)
        self.target: Tuple[asyncio.StreamReader, asyncio.StreamWriter] | None = None
        self._finish: asyncio.Event = asyncio.Event()
        self._cmd: Optional[ProxyCMD] = None
        self._socks_dst: Optional[Tuple[Union[bytes, str], int]] = None
        self._dst: Tuple[str, int] | None = None

    @staticmethod
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        proxy = SocksProtocol(reader, writer)
        await proxy.run()

    async def run(self):
        try:
            await self.accept()
            await self.forward()
        except Exception:
            logger.warning(traceback.format_exc())
        finally:
            await self.close()

    async def close(self):
        self.client and self.client[1] and self.client[1].close()  #type: ignore
        self.target and self.target[1] and self.target[1].close()  #type: ignore

    async def output(self, message: bytes, writer: asyncio.StreamWriter, isReceive: bool):
        isReceiveChar = '<' if isReceive else '>'
        peername = writer.transport.get_extra_info('peername')
        prefix = f'{peername}{isReceiveChar}'
        logger.debug(f'[Output] {prefix} {message}')

    async def accept(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter] | None:
        """根据请求信息, 连接目标服务器, 并返回连接对象"""
        reader, writer = self.client
        data = await reader.read(self.READ_LIMIT)
        if not data:
            raise ConnectError()

        await self.output(data, writer, True)

        if data and b'HTTP' in data:
            await self.http_proxy(data)
            return

        # TODO: 支持认证
        if data[1] != 1:
            raise ConnectError('只接受匿名代理')

        await self.socks_proxy()

    async def http_proxy(self, data: bytes):
        self._cmd = ProxyCMD.HTTP

        _, writer = self.client
        # HTTPS 代理
        if data.startswith(b'CONNECT'):
            self._cmd = ProxyCMD.HTTPS
            items = data.split(b' ')
            # TODO ipv6 support
            host, port = items[1].split(b':')
            raddr = (host.decode(), int(port))

            target = await asyncio.open_connection(*raddr)
            self.target = target
            if not all(target):
                logger.debug(f'open connection to {raddr} fail')
                return None
            logger.debug('open connection success')

            resp = HTTP_PROXY_CONNECT_RESPONSE
            logger.debug(f'write connect response: \n{resp}')
            writer.write(resp)
            await writer.drain()
            await self.output(resp, writer, False)
            logger.debug('write connect response success.')

            self.target = target
        else:
            self._cmd = ProxyCMD.HTTP
            headers = {}
            items, body = data.split(b'\r\n\r\n')
            items = items.split(b'\r\n')
            method, addr, version = items[0].split(b' ')
            for item in items[1:]:
                if not item:
                    continue
                k, v = item.split(b': ', 1)
                headers[k] = v

            u = urllib.parse.urlparse(addr)
            # TODO: ipv6

            _addr = u.netloc.split(b':')
            if len(_addr) == 1:
                raddr = (_addr[0].decode(), 80)
            else:
                raddr = (_addr[0].decode(), int(_addr[1]))

            logger.debug(f'{method}, {addr}, {version}, {headers}, {raddr}, {body}')

            target = await asyncio.open_connection(*raddr)
            target[1].write(data)
            await target[1].drain()
            await self.output(data, target[1], False)
            self.target = target

    async def socks_proxy(self):
        reader, writer = self.client

        # 不需要任何认证
        ver = b'\x05'
        method = b'\x00'
        reply = ver + method
        writer.write(reply)
        await writer.drain()
        await self.output(reply, writer, False)

        data = await reader.read(self.READ_LIMIT)
        await self.output(data, writer, True)

        cmd = data[1]

        dst, _, _ = Socks5ProxyParser.unpack(data)
        self._dst = dst

        # 读取代理类型
        if cmd == Socks5CMD.CONNECT:
            self._cmd = ProxyCMD.SOCKS_CONNECT
            target = await asyncio.open_connection(*dst, loop=asyncio.get_event_loop())
            self.target = target

        elif cmd == Socks5CMD.BIND:
            self._cmd = ProxyCMD.SOCKS_BIND
            raise ConnectError("not support bind request")

        elif cmd == Socks5CMD.UDP:
            self._cmd = ProxyCMD.SOCKS_UDP
        logger.debug(f"cmd: {self._cmd},  target: {self.target},  dst: {self._dst}")
        await self.allow_socks_proxy(writer)

    async def allow_socks_proxy(self, writer: asyncio.StreamWriter):
        """允许客户端连接后, 根据代理设置封装回复
        """
        # TODO: ipv6、host
        ver = b'\x05'
        rep = b'\x00'
        rsv = b'\x00'
        atyp = b'\x01'
        addr = socket.inet_pton(socket.AF_INET, settings.proxy_addr)
        port = struct.pack('>H', settings.proxy_port)
        reply = ver + rep + rsv + atyp + addr + port
        writer.write(reply)
        await writer.drain()

    async def wait_closed(self):
        reader, writer = self.client
        while True:
            data = await reader.read(self.READ_LIMIT)
            if not data:
                break
        writer.close()

    async def forward(self):
        if self._cmd == ProxyCMD.SOCKS_UDP:
            # 根据协议, TCP 连接断开时, 需要同步关闭 UDP 代理
            await self.wait_closed()
            assert self._dst
            release_udp_transport(self._dst, UdpProtocol.MANAGER, UdpProtocol.LAST_ACTIVITY)
            return

        client, target = self.client, self.target
        assert client and target

        a: asyncio.Future = asyncio.ensure_future(self.receive_and_forward(client, target))
        b: asyncio.Future = asyncio.ensure_future(self.receive_and_forward(target, client))
        await self._finish.wait()

        a.done() or a.cancel()  # type:ignore
        b.done() or b.cancel()  # type:ignore

    async def receive_and_forward(
        self,
        sender: Tuple[asyncio.StreamReader,
                      asyncio.StreamWriter],
        receiver: Tuple[asyncio.StreamReader,
                        asyncio.StreamWriter]
    ):
        try:
            while not self._finish.is_set():
                data = await receiver[0].read(self.READ_LIMIT)
                if not data:
                    return

                sender[1].write(data)
                await sender[1].drain()
                await self.output(data, sender[1], False)
        except ConnectionResetError:
            logging.debug(traceback.format_exc())
        except Exception:
            logger.warning(traceback.format_exc())
        finally:
            # _finish 可能由另一端关闭
            if not self._finish.is_set():
                self._finish.set()
            raddr = sender[1].transport.get_extra_info('peername')
            if raddr:
                logger.debug(f'{raddr} lost connection.')
