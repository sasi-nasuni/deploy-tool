import asyncio
from collections import defaultdict

from fastapi import WebSocket


class LogStreamer:
    def __init__(self) -> None:
        self._sockets: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, deployment_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._sockets[deployment_id].add(websocket)

    async def disconnect(self, deployment_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._sockets.get(deployment_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._sockets.pop(deployment_id, None)

    async def broadcast(self, deployment_id: str, message: str, done: bool = False) -> None:
        payload = {"message": message, "done": done}
        async with self._lock:
            sockets = list(self._sockets.get(deployment_id, set()))
        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                stale.append(socket)
        if stale:
            async with self._lock:
                current = self._sockets.get(deployment_id, set())
                for socket in stale:
                    current.discard(socket)
