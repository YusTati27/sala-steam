from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.models.entities import Equipment, Filament, PrintJob, Reservation, User
from app.seed import simulator
from app.services import app_settings
from app.ws.manager import manager

router = APIRouter(tags=["system"])


def _config(db: Session) -> dict:
    s = get_settings()
    return {
        "mode": app_settings.get(db, "mode"),
        "demo": app_settings.is_demo_mode(db),
        "simulator_enabled": s.simulator_enabled,
        "open_hours_per_day": app_settings.open_hours(db),
        "utc_offset_hours": s.local_utc_offset_hours,
    }


@router.get("/config")
def get_config(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _config(db)


class ModeIn(BaseModel):
    mode: Literal["demo", "real"]


@router.post("/config/mode")
def set_mode(data: ModeIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    app_settings.set_value(db, "mode", data.mode)
    if data.mode == "demo" and not simulator.has_demo_data(db):
        simulator.generate_demo(db)
    manager.notify("all", message=f"Modo {'simulador' if data.mode == 'demo' else 'real'} activado")
    return _config(db)


class SettingsIn(BaseModel):
    open_hours_per_day: float = Field(ge=1, le=24)


@router.post("/config/settings")
def set_settings(data: SettingsIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    app_settings.set_value(db, "open_hours_per_day", str(data.open_hours_per_day))
    manager.notify("stats")
    return _config(db)


@router.get("/simulator/status")
def status(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    def n(model):
        return db.scalar(select(func.count()).select_from(model).where(model.is_demo.is_(True))) or 0

    return {**_config(db), "records": {"equipment": n(Equipment), "filaments": n(Filament), "jobs": n(PrintJob), "reservations": n(Reservation),
                                       "users": n(User)}}


class RegenIn(BaseModel):
    months: int = Field(default=6, ge=1, le=18)
    seed: int = 42


@router.post("/simulator/regenerate")
def regenerate(data: RegenIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    result = simulator.generate_demo(db, data.months, data.seed)
    manager.notify("all", message="Datos de simulación regenerados")
    return result


@router.post("/simulator/clear", status_code=204)
def clear(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    simulator.clear_demo(db)
    manager.notify("all", message="Datos de simulación eliminados")
