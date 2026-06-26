import asyncio
from datetime import datetime, timezone

from fastapi import WebSocket


class LogStreamer:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._history: dict[str, list[dict]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, deployment_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(deployment_id, set()).add(websocket)
            history = list(self._history.get(deployment_id, []))
        for entry in history:
            await websocket.send_json(entry)

    async def disconnect(self, deployment_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if deployment_id in self._connections:
                self._connections[deployment_id].discard(websocket)
                if not self._connections[deployment_id]:
                    self._connections.pop(deployment_id, None)

    async def broadcast(
        self,
        deployment_id: str,
        message_type: str,
        line: str,
        *,
        done: bool = False,
    ) -> None:
        payload = {
            "type": message_type,
            "line": line,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if done:
            payload["done"] = True

        async with self._lock:
            self._history.setdefault(deployment_id, []).append(payload)
            subscribers = list(self._connections.get(deployment_id, set()))

        stale_connections: list[WebSocket] = []
        for websocket in subscribers:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale_connections.append(websocket)

        if stale_connections:
            async with self._lock:
                for websocket in stale_connections:
                    self._connections.get(deployment_id, set()).discard(websocket)

    async def clear(self, deployment_id: str) -> None:
        async with self._lock:
            self._history.pop(deployment_id, None)
            self._connections.pop(deployment_id, None)
