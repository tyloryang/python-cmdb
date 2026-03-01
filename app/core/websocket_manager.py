import asyncio
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """管理多个 WebSocket 连接，按频道分组广播"""

    def __init__(self):
        # channel_id -> set of WebSocket
        self._channels: Dict[str, Set[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self._channels.setdefault(channel, set()).add(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        if channel in self._channels:
            self._channels[channel].discard(ws)
            if not self._channels[channel]:
                del self._channels[channel]

    async def broadcast(self, channel: str, message: str):
        sockets = list(self._channels.get(channel, []))
        if not sockets:
            return
        await asyncio.gather(
            *[ws.send_text(message) for ws in sockets],
            return_exceptions=True,
        )


ws_manager = WebSocketManager()
