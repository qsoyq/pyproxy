from enum import IntEnum


class Socks5CMD(IntEnum):
    CONNECT = 1
    BIND = 2
    UDP = 3


class Socks5ATYP(IntEnum):
    IPV4 = 1
    HOST = 3
    IPV6 = 4


class ProxyCMD(IntEnum):

    SOCKS_CONNECT = 1
    SOCKS_BIND = 2
    SOCKS_UDP = 3
    HTTP = 4
    HTTPS = 5


HTTP_PROXY_CONNECT_RESPONSE = (b'HTTP/1.0 200 Connection Established\r\n'
                               b'Connection: close\r\n'
                               b'\r\n')
