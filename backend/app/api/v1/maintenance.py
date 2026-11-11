from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.db import get_db
from app.core.deps import demo_flag, require_admin
from app.models.entities import Equipment, EquipmentStatus, MaintenanceRecord, MaintenanceStatus, MaintenanceType, User
from app.schemas.maintenance import MaintenanceCreate, MaintenanceOut, MaintenanceUpdate
from app.services import jobs as jobsvc
from app.ws.manager import manager

router = APIRouter(prefix="/maintenance", tags=["maintenance"], dependencies=[Depends(require_admin)])
PREVENTIVE_INTERVAL_DAYS = 90


def _view(m: MaintenanceRecord) -> dict:
    return {**{c.name: getattr(m, c.name) for c in m.__table__.columns}, "equipment_name": m.equipment.name, "equipment_code": m.equipment.code}


def _sync_equipment(db: Session, m: MaintenanceRecord) -> None:
    """Sincroniza estado y fechas del equipo con el registro de mantenimiento."""
    eq = m.equipment
    if m.status == MaintenanceStatus.in_progress.value:
        if jobsvc.printing_job(db, eq.id):
            raise HTTPException(409, "La impresora tiene un trabajo en proceso; termínelo o cancélelo antes de iniciar mantenimiento")
        eq.status = EquipmentStatus.maintenance.value
    elif m.status == MaintenanceStatus.done.value:
        if m.performed_at and (eq.last_maintenance_at is None or m.performed_at >= eq.last_maintenance_at):
            eq.last_maintenance_at = m.performed_at
            if m.next_due_at:
                eq.next_maintenance_at = m.next_due_at
            elif m.type == MaintenanceType.preventive.value:
                eq.next_maintenance_at = m.performed_at + timedelta(days=PREVENTIVE_INTERVAL_DAYS)
        still = db.scalar(select(MaintenanceRecord.id).where(
            MaintenanceRecord.equipment_id == eq.id, MaintenanceRecord.status == MaintenanceStatus.in_progress.value,
            MaintenanceRecord.id != m.id))
        if eq.status == EquipmentStatus.maintenance.value and not still:
            eq.status = EquipmentStatus.available.value
    db.flush()
    jobsvc.refresh_printer(db, eq)


@router.get("", response_model=list[MaintenanceOut])
def list_records(equipment_id: int | None = None, status: MaintenanceStatus | None = None, demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    q = (select(MaintenanceRecord).options(joinedload(MaintenanceRecord.equipment)).where(MaintenanceRecord.is_demo == demo)
         .order_by(MaintenanceRecord.created_at.desc(), MaintenanceRecord.id.desc()).limit(500))
    if equipment_id:
        q = q.where(MaintenanceRecord.equipment_id == equipment_id)
    if status:
        q = q.where(MaintenanceRecord.status == status.value)
    return [_view(m) for m in db.scalars(q).unique()]


@router.get("/attention")
def needs_attention(demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    """Equipos que requieren atención: vencidos, próximos (≤14 días) o fuera de servicio."""
    today = date.today()
    out = []
    for e in db.scalars(select(Equipment).where(Equipment.is_demo == demo).order_by(Equipment.name)):
        left = (e.next_maintenance_at - today).days if e.next_maintenance_at else None
        reason = ("fuera_de_servicio" if e.status == "out_of_service" else "vencido" if left is not None and left < 0
                  else "proximo" if left is not None and left <= 14 else None)
        if reason:
            out.append({"equipment_id": e.id, "name": e.name, "code": e.code, "status": e.status, "reason": reason,
                        "days_left": left, "next_maintenance_at": e.next_maintenance_at})
    out.sort(key=lambda r: (r["days_left"] is None, r["days_left"] if r["days_left"] is not None else 0))
    return out


@router.post("", response_model=MaintenanceOut, status_code=201)
def create_record(data: MaintenanceCreate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    eq = db.get(Equipment, data.equipment_id)
    if not eq or eq.is_demo != demo:
        raise HTTPException(404, "Equipo no encontrado")
    m = MaintenanceRecord(**{**data.model_dump(), "type": data.type.value, "status": data.status.value}, performed_by=admin.id, is_demo=demo)
    if m.status == MaintenanceStatus.in_progress.value and not m.performed_at:
        m.performed_at = date.today()
    db.add(m)
    db.flush()
    db.refresh(m)
    _sync_equipment(db, m)
    db.commit()
    manager.notify("maintenance", "equipment")
    return _view(m)


@router.patch("/{mid}", response_model=MaintenanceOut)
def update_record(mid: int, data: MaintenanceUpdate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    m = db.get(MaintenanceRecord, mid)
    if not m or m.is_demo != demo:
        raise HTTPException(404, "Registro no encontrado")
    if m.status == MaintenanceStatus.done.value:
        raise HTTPException(409, "Un mantenimiento realizado no se puede modificar")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v.value if hasattr(v, "value") else v)
    if m.status == MaintenanceStatus.done.value and not m.performed_at:
        m.performed_at = date.today()
    _sync_equipment(db, m)
    db.commit()
    manager.notify("maintenance", "equipment")
    return _view(m)
