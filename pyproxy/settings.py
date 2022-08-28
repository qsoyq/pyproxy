import urllib.request

from pydantic import BaseSettings


class Settings(BaseSettings):

    system_proxies: dict = urllib.request.getproxies()
    udp_keep_alive_timeout: float = 60

    host: str = "0.0.0.0"
    port: int = 7999

    proxy_addr: str = '127.0.0.1'
    proxy_port: int = 7999


settings = Settings()
