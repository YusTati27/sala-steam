from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import demo_flag, get_current_user, require_admin
from app.models.entities import Equipment, EquipmentStatus, EquipmentType, MaintenanceRecord, PrintJob, Reservation, User
from app.schemas.equipment import EquipmentCreate, EquipmentOut, EquipmentUpdate
from app.services import jobs as jobsvc
from app.services.equipment import equipment_view
from app.ws.manager import manager

router = APIRouter(prefix="/equipment", tags=["equipment"])


def _get(db: Session, eq_id: int, demo: bool) -> Equipment:
    eq = db.get(Equipment, eq_id)
    if not eq or eq.is_demo != demo:
        raise HTTPException(404, "Equipo no encontrado")
    return eq


@router.get("", response_model=list[EquipmentOut])
def list_equipment(type: EquipmentType | None = None, status: EquipmentStatus | None = None, user: User = Depends(get_current_user),
                   demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    q = select(Equipment).where(Equipment.is_demo == demo).order_by(Equipment.type, Equipment.code)
    if type:
        q = q.where(Equipment.type == type.value)
    if status:
        q = q.where(Equipment.status == status.value)
    return [equipment_view(db, e, user) for e in db.scalars(q)]


@router.get("/{eq_id}", response_model=EquipmentOut)
def get_equipment(eq_id: int, user: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    return equipment_view(db, _get(db, eq_id, demo), user)


@router.post("", response_model=EquipmentOut, status_code=201)
def create_equipment(data: EquipmentCreate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    if data.status == EquipmentStatus.busy:
        raise HTTPException(400, "El estado 'ocupado' lo define el sistema según los trabajos en proceso")
    code = data.code.strip().upper()
    if db.scalar(select(Equipment.id).where(func.upper(Equipment.code) == code)):
        raise HTTPException(409, f"Ya existe un equipo con el código {code}")
    eq = Equipment(**{**data.model_dump(), "code": code, "type": data.type.value, "status": data.status.value}, is_demo=demo)
    db.add(eq)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Código duplicado") from None
    manager.notify("equipment")
    return equipment_view(db, eq, admin)


@router.patch("/{eq_id}", response_model=EquipmentOut)
def update_equipment(eq_id: int, data: EquipmentUpdate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag),
                     db: Session = Depends(get_db)):
    eq = _get(db, eq_id, demo)
    vals = data.model_dump(exclude_unset=True)
    if "code" in vals:
        code = vals["code"].strip().upper()
        dup = db.scalar(select(Equipment.id).where(func.upper(Equipment.code) == code, Equipment.id != eq.id))
        if dup:
            raise HTTPException(409, f"Ya existe un equipo con el código {code}")
        vals["code"] = code
    new_status = vals.get("status")
    if new_status == EquipmentStatus.busy:
        raise HTTPException(400, "El estado 'ocupado' lo define el sistema según los trabajos en proceso")
    if new_status in (EquipmentStatus.maintenance, EquipmentStatus.out_of_service) and jobsvc.printing_job(db, eq.id):
        raise HTTPException(409, "La impresora tiene un trabajo en proceso; termínelo o cancélelo primero")
    for k, v in vals.items():
        setattr(eq, k, v.value if hasattr(v, "value") else v)
    last, nxt = eq.last_maintenance_at, eq.next_maintenance_at
    if last and nxt and nxt < last:
        db.rollback()
        raise HTTPException(422, "El próximo mantenimiento no puede ser anterior al último")
    db.flush()
    jobsvc.refresh_printer(db, eq)
    db.commit()
    manager.notify("equipment", "jobs")
    return equipment_view(db, eq, admin)


@router.delete("/{eq_id}", status_code=204)
def delete_equipment(eq_id: int, _: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    eq = _get(db, eq_id, demo)
    used = (
        db.scalar(select(func.count()).select_from(PrintJob).where(PrintJob.printer_id == eq.id))
        or db.scalar(select(func.count()).select_from(Reservation).where(Reservation.printer_id == eq.id))
        or db.scalar(select(func.count()).select_from(MaintenanceRecord).where(MaintenanceRecord.equipment_id == eq.id))
    )
    if used:
        raise HTTPException(409, "El equipo tiene historial asociado; márquelo como 'fuera de servicio' en lugar de eliminarlo")
    db.delete(eq)
    db.commit()
    manager.notify("equipment")
