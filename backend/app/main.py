import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.api.v1 import auth, equipment, filaments, jobs, maintenance, reservations, stats, system, users
from app.core.config import BACKEND_DIR, get_settings
from app.core.db import Base, SessionLocal, engine
from app.core.security import decode_token, hash_password
from app.models import entities  # noqa: F401  (registra los modelos)
from app.models.entities import Role, User
from app.seed import simulator
from app.services import app_settings
from app.ws.manager import manager

log = logging.getLogger("sala_steam")


def init_data() -> None:
    s = get_settings()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if s.bootstrap_admin_email and s.bootstrap_admin_password and not db.scalar(select(User.id).where(User.is_demo.is_(False)).limit(1)):
            db.add(User(name=s.bootstrap_admin_name, email=s.bootstrap_admin_email.lower(), password_hash=hash_password(s.bootstrap_admin_password),
                        role=Role.admin.value))
            db.commit()
            log.warning("Administrador inicial creado: %s (cambie la contraseña desde Configuración)", s.bootstrap_admin_email)
        if s.simulator_enabled and app_settings.is_demo_mode(db) and not simulator.has_demo_data(db):
            simulator.generate_demo(db)


def _sim_step() -> list[str]:
    with SessionLocal() as db:
        if not app_settings.is_demo_mode(db):
            return []
        return simulator.tick(db)


async def simulator_loop() -> None:
    s = get_settings()
    while True:
        await asyncio.sleep(s.sim_tick_seconds)
        try:
            events = await run_in_threadpool(_sim_step)
        except Exception:  # el simulador nunca debe tumbar la app
            log.exception("Error en el simulador")
            continue
        if manager.connections:
            entities = ["jobs", "equipment", "filaments"] + (["stats"] if events else [])
            await manager.broadcast({"type": "update", "entities": entities, "message": events[0] if events else None, "level": "info"})


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.loop = asyncio.get_running_loop()
    await run_in_threadpool(init_data)
    task = asyncio.create_task(simulator_loop()) if get_settings().simulator_enabled else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Sala STEAM API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for r in (auth, users, equipment, filaments, jobs, reservations, maintenance, stats, system):
    app.include_router(r.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """El cliente envía {"token": "<JWT>"} como primer mensaje; después recibe eventos de actualización."""
    await ws.accept()
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)
        payload = decode_token(first.get("token", "")) if isinstance(first, dict) else None
        if not payload:
            await ws.close(code=4401)
            return
        await manager.connect(ws)
        await ws.send_json({"type": "ready"})
        while True:
            await ws.receive_text()  # mantiene la conexión; ignora mensajes
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
        pass
    finally:
        manager.disconnect(ws)


# En producción un solo servicio entrega también la interfaz (frontend/dist, generada con `npm run build`).
DIST = BACKEND_DIR.parent / "frontend" / "dist"
if (DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith(("api/", "ws")):
            raise HTTPException(404)
        target = (DIST / path).resolve()
        if path and target.is_file() and DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
