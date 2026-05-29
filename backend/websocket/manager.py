from __future__ import annotations
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active.add(websocket)
        logger.info("WS client connected — total: %d", len(self._active))

    def disconnect(self, websocket: WebSocket) -> None:
        self._active.discard(websocket)
        logger.info("WS client disconnected — total: %d", len(self._active))

    async def broadcast(self, data: dict) -> None:
        payload = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in list(self._active):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._active.discard(ws)
