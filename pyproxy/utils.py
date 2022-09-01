import ipaddress
import logging
import os
import resource
import socket
import struct
import urllib.parse
import urllib.request

from contextvars import Token
from typing import Dict, Mapping, Optional, Tuple, Union

import socks

from pyproxy._types import UDP_MAPPING_TABLE_TYPE
from pyproxy.settings import Settings, _settings

logger = logging.getLogger(__name__)


def set_open_file_limit(soft_limit: Optional[int] = None):
    """Configure open file description soft limit on supported OS."""
    if soft_limit is None:
        return

    if os.name != 'nt':  # resource module not available on Windows OS
        curr_soft_limit, curr_hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        if curr_soft_limit < soft_limit < curr_hard_limit:
            rlimit = (resource.RLIMIT_NOFILE, (soft_limit, curr_hard_limit))
            resource.setrlimit(*rlimit)
            logger.debug(f'current file soft limit: {curr_soft_limit}.')
            logger.debug(f'Open file soft limit set to {soft_limit}.')


def open_system_proxy(system_proxies: Optional[Mapping[str, str]] = None):
    if system_proxies is None:
        system_proxies = urllib.request.getproxies()

    # TODO: 系统代理优化
    if 'all' in system_proxies:
        u = urllib.parse.urlparse(system_proxies['all'])
        addr = u.netloc.split(':').copy()

        if len(addr) == 1:
            host, port = addr[0], None
        else:
            host, port = addr[0], int(addr[1])
        socks.set_default_proxy(socks.SOCKS5, host, port)
        socket.socket = socks.socksocket


def initialize(
    *,
    host: str,
    port: int,
    proxy_addr: Optional[str] = None,
    proxy_port: Optional[int] = None,
    soft_limit: Optional[int] = None,
    system_proxies: Optional[Mapping[str,
                                     str]] = None,
    enable_system_proxy: bool = False,
    settings: Optional[Settings] = None,
) -> Token:

    if settings is None:
        assert proxy_addr and proxy_port
        settings = Settings(host=host, port=port, proxy_addr=proxy_addr, proxy_port=proxy_port)
    token = _settings.set(settings)

    try:
        _ = socket.inet_pton(socket.AF_INET, settings.proxy_addr)
    except socket.error:
        settings.proxy_addr = socket.gethostbyname(settings.proxy_addr)

    set_open_file_limit(soft_limit)

    if enable_system_proxy:
        open_system_proxy(system_proxies)

    return token


def release_udp_transport(
    dst: Tuple[str,
               int],
    manager: UDP_MAPPING_TABLE_TYPE,
    last_activity: Dict[Tuple[str,
                              int],
                        Union[int,
                              float]]
):
    pair = manager.pop(dst, None)
    last_activity.pop(dst, None)
    if pair:
        transport = pair[0]
        transport.close()


def parse_address(address: str, default_port: int = 80) -> Tuple[str, int, int]:
    """解析地址字符串

    address 可能包含端口号
    `127.0.0.1`
    `127.0.0.1:8000`
    """
    ip, port, version = None, None, None
    try:
        addr = ipaddress.ip_address(address)
        ip = address
        port = default_port
        version = addr.version

    except ValueError:
        idx = address.rindex(":")
        addr = ipaddress.ip_address(address[:idx])
        ip = address[:idx]
        port = int(address[idx + 1:])
        version = addr.version

    return ip, port, version


class Socks5ProxyParser:

    IPV4 = 1
    HOST = 3
    IPV6 = 4

    @staticmethod
    def unpack(data: bytes) -> Tuple[Tuple[str, int], bytes, bytes]:
        """按照 socks5 协议解析数据包
        """
        dst: tuple[str, int] = ("", 0)
        message: bytes = b''
        header: bytes = b''
        try:
            atyp = data[3]
            if atyp == Socks5ProxyParser.IPV4:
                addr = socket.inet_ntop(socket.AF_INET, data[4:8])
                port = int.from_bytes(data[8:10], 'big')
                dst = (addr, port)
                header = data[:10]
                message = data[10:]

            elif atyp == Socks5ProxyParser.IPV6:
                addr = socket.inet_ntop(socket.AF_INET6, data[4:20])
                port = int.from_bytes(data[20:22], 'big')
                dst = (addr, port)
                header = data[:22]
                message = data[22:]

            elif atyp == Socks5ProxyParser.HOST:
                hostLen = data[4]
                addr = (data[5:5 + hostLen]).decode()
                port = struct.unpack('>H', data[5 + hostLen:7 + hostLen])[0]
                dst = (addr, port)
                header = data[:7 + hostLen]
                message = data[7 + hostLen:]

        except Exception as e:
            logger.exception(e)

        return dst, header, message
