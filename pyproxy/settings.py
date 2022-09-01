from contextvars import ContextVar

from pydantic import BaseModel


class Settings(BaseModel):

    udp_keep_alive_timeout: float = 60

    host: str
    port: int

    proxy_addr: str
    proxy_port: int


_settings: ContextVar[Settings] = ContextVar('settings')

__all__ = ['_settings']
