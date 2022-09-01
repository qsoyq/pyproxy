import socket

import socks

from tests import proxy, proxy_default_settings, udp_echo_server  # nopycln: import


def test_udp(proxy, udp_echo_server):

    s = socks.socksocket(socket.AF_INET, socket.SOCK_DGRAM)
    s.set_proxy(socks.SOCKS5, f"{proxy_default_settings.proxy_addr}", proxy_default_settings.proxy_port)
    s.settimeout(10)
    # TODO: 使用一个线上服务代替本地服务器
    dst = ('127.0.0.1', 31337)
    text = b"Get some UDP info"
    s.sendto(text, dst)
    res = s.recv(4096)
    assert res == text, res
