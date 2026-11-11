from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import demo_flag, get_current_user, require_admin
from app.core.timeutil import utcnow
from app.models.entities import Equipment, EquipmentType, Reservation, ReservationStatus, User
from app.schemas.reservation import DecisionIn, ReservationCreate, ReservationOut, SlotOut
from app.ws.manager import manager

router = APIRouter(prefix="/reservations", tags=["reservations"])
BLOCKING = (ReservationStatus.pending.value, ReservationStatus.approved.value)
MAX_ACTIVE_PER_CLIENT = 3


def _view(r: Reservation, viewer: User) -> dict:
    private = viewer.role == "admin" or r.user_id == viewer.id
    return {
        "id": r.id, "user_id": r.user_id if private else 0, "user_name": r.user.name if private else None, "printer_id": r.printer_id,
        "printer_name": r.printer.name, "start_at": r.start_at, "end_at": r.end_at, "status": r.status,
        "purpose": r.purpose if private else "", "admin_note": r.admin_note if private else "", "is_mine": r.user_id == viewer.id,
        "is_demo": r.is_demo, "created_at": r.created_at,
    }


def _q(demo: bool):
    return select(Reservation).options(joinedload(Reservation.user), joinedload(Reservation.printer)).where(Reservation.is_demo == demo)


def _overlap(db: Session, printer_id: int, start: datetime, end: datetime, exclude_id: int | None = None, statuses=BLOCKING):
    q = select(Reservation).where(Reservation.printer_id == printer_id, Reservation.status.in_(statuses),
                                  Reservation.start_at < end, Reservation.end_at > start)
    if exclude_id:
        q = q.where(Reservation.id != exclude_id)
    return db.scalar(q)


@router.get("", response_model=list[ReservationOut])
def list_all(status: ReservationStatus | None = None, printer_id: int | None = None, admin: User = Depends(require_admin),
             demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    q = _q(demo).order_by(Reservation.start_at.desc()).limit(500)
    if status:
        q = q.where(Reservation.status == status.value)
    if printer_id:
        q = q.where(Reservation.printer_id == printer_id)
    return [_view(r, admin) for r in db.scalars(q).unique()]


@router.get("/mine", response_model=list[ReservationOut])
def mine(user: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    q = _q(demo).where(Reservation.user_id == user.id).order_by(Reservation.start_at.desc()).limit(200)
    return [_view(r, user) for r in db.scalars(q).unique()]


@router.get("/availability", response_model=list[SlotOut])
def availability(printer_id: int, day: date, user: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    """Franjas ocupadas de una impresora en un día (hora local de la sala). No expone datos de otros usuarios."""
    off = timedelta(hours=get_settings().local_utc_offset_hours)
    start = datetime.combine(day, datetime.min.time()) - off
    q = _q(demo).where(Reservation.printer_id == printer_id, Reservation.status.in_(BLOCKING),
                       Reservation.start_at < start + timedelta(days=1), Reservation.end_at > start).order_by(Reservation.start_at)
    return [{"start_at": r.start_at, "end_at": r.end_at, "status": r.status, "is_mine": r.user_id == user.id} for r in db.scalars(q).unique()]


@router.post("", response_model=ReservationOut, status_code=201)
def create(data: ReservationCreate, user: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    is_admin = user.role == "admin"
    owner_id = user.id
    if data.user_id and data.user_id != user.id:
        if not is_admin:
            raise HTTPException(403, "No puede reservar a nombre de otro usuario")
        if not db.get(User, data.user_id):
            raise HTTPException(404, "Usuario no encontrado")
        owner_id = data.user_id
    printer = db.get(Equipment, data.printer_id)
    if not printer or printer.is_demo != demo or printer.type != EquipmentType.printer_3d.value:
        raise HTTPException(404, "Impresora no encontrada")
    if printer.status in ("out_of_service", "maintenance"):
        raise HTTPException(409, f"{printer.name} no está disponible para reservas ({printer.status})")
    if data.start_at < utcnow() - timedelta(minutes=5):
        raise HTTPException(422, "No se pueden crear reservas en el pasado")
    if data.start_at > utcnow() + timedelta(days=60):
        raise HTTPException(422, "Solo se puede reservar con hasta 60 días de anticipación")
    if not is_admin:
        active = db.scalars(select(Reservation.id).where(Reservation.user_id == user.id, Reservation.status.in_(BLOCKING),
                                                         Reservation.end_at > utcnow(), Reservation.is_demo == demo)).all()
        if len(active) >= MAX_ACTIVE_PER_CLIENT:
            raise HTTPException(409, f"Ya tiene {MAX_ACTIVE_PER_CLIENT} reservas activas; cancele alguna para crear otra")
    if _overlap(db, data.printer_id, data.start_at, data.end_at):
        raise HTTPException(409, "Esa franja ya está reservada o pendiente en esta impresora")
    r = Reservation(user_id=owner_id, printer_id=data.printer_id, start_at=data.start_at, end_at=data.end_at, purpose=data.purpose.strip(),
                    status=ReservationStatus.approved.value if is_admin else ReservationStatus.pending.value, is_demo=demo)
    db.add(r)
    db.commit()
    manager.notify("reservations", message="Nueva reserva registrada")
    return _view(db.scalars(_q(demo).where(Reservation.id == r.id)).unique().one(), user)


def _owned(db: Session, rid: int, demo: bool) -> Reservation:
    r = db.scalars(_q(demo).where(Reservation.id == rid)).unique().first()
    if not r:
        raise HTTPException(404, "Reserva no encontrada")
    return r


@router.post("/{rid}/cancel", response_model=ReservationOut)
def cancel(rid: int, user: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    r = _owned(db, rid, demo)
    if r.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "Solo puede cancelar sus propias reservas")
    if r.status not in BLOCKING:
        raise HTTPException(409, "Esta reserva ya no se puede cancelar")
    if user.role != "admin" and r.start_at <= utcnow():
        raise HTTPException(409, "No se puede cancelar una reserva que ya comenzó")
    r.status = ReservationStatus.cancelled.value
    db.commit()
    manager.notify("reservations")
    return _view(r, user)


@router.post("/{rid}/decision", response_model=ReservationOut)
def decide(rid: int, data: DecisionIn, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    r = _owned(db, rid, demo)
    if data.decision == "approve":
        if r.status != ReservationStatus.pending.value:
            raise HTTPException(409, "Solo se pueden aprobar reservas pendientes")
        if _overlap(db, r.printer_id, r.start_at, r.end_at, exclude_id=r.id, statuses=(ReservationStatus.approved.value,)):
            raise HTTPException(409, "Se cruza con otra reserva ya aprobada")
        r.status = ReservationStatus.approved.value
    elif data.decision == "reject":
        if r.status != ReservationStatus.pending.value:
            raise HTTPException(409, "Solo se pueden rechazar reservas pendientes")
        r.status = ReservationStatus.rejected.value
    else:
        if r.status != ReservationStatus.approved.value:
            raise HTTPException(409, "Solo se pueden completar reservas aprobadas")
        r.status = ReservationStatus.completed.value
    r.admin_note = data.admin_note
    db.commit()
    manager.notify("reservations", message=f"Reserva #{r.id} {r.status}")
    return _view(r, admin)
