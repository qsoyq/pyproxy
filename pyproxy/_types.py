import asyncio

from typing import Dict, Tuple

UDP_MAPPING_TABLE_TYPE = Dict[Tuple[str, int], Tuple[asyncio.DatagramTransport, asyncio.BaseProtocol]]
