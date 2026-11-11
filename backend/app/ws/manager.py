import asyncio
import contextlib

from fastapi import WebSocket


class ConnectionManager:
    """Difunde eventos 'algo cambió' a los clientes conectados (el frontend vuelve a consultar)."""

    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, ws: WebSocket) -> None:
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)

    async def broadcast(self, message: dict) -> None:
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                self.connections.discard(ws)

    def notify(self, *entities: str, message: str | None = None, level: str = "info") -> None:
        """Seguro para llamar desde código síncrono (hilos de FastAPI)."""
        if not self.loop or not self.connections:
            return
        payload = {"type": "update", "entities": list(entities), "message": message, "level": level}
        with contextlib.suppress(Exception):
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self.loop)


manager = ConnectionManager()
