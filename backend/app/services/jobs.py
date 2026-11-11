"""Reglas de negocio de trabajos de impresión y sincronización con impresoras, filamentos y reservas."""

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.timeutil import utcnow
from app.models.entities import (
    Equipment,
    EquipmentStatus,
    EquipmentType,
    Filament,
    JobStatus,
    MovementType,
    PrintJob,
    Reservation,
    ReservationStatus,
    User,
)
from app.services.filaments import apply_movement

ACTIVE = (JobStatus.pending.value, JobStatus.queued.value, JobStatus.printing.value)
MANUAL_STATES = (EquipmentStatus.maintenance.value, EquipmentStatus.out_of_service.value)


# ---------- Impresoras ----------
def printing_job(db: Session, printer_id: int) -> PrintJob | None:
    return db.scalar(
        select(PrintJob).where(PrintJob.printer_id == printer_id, PrintJob.status == JobStatus.printing.value)
    )


def refresh_printer(db: Session, eq: Equipment) -> None:
    """Estado derivado: ocupado si hay un trabajo imprimiendo; mantenimiento/fuera de servicio son manuales."""
    if eq.status in MANUAL_STATES:
        return
    eq.status = EquipmentStatus.busy.value if printing_job(db, eq.id) else EquipmentStatus.available.value


def schedule_for(db: Session, printer_id: int, now: datetime | None = None):
    """Devuelve (trabajo actual, cola, {job_id: fin estimado}, disponible_en, cola_libre_en)."""
    now = now or utcnow()
    rows = db.scalars(
        select(PrintJob).where(
            PrintJob.printer_id == printer_id,
            PrintJob.status.in_(ACTIVE),
        )
    ).all()
    cur = next((j for j in rows if j.status == JobStatus.printing.value), None)
    queued = sorted(
        (j for j in rows if j.status == JobStatus.queued.value), key=lambda j: (j.queued_at or j.created_at, j.id)
    )
    pending = sorted((j for j in rows if j.status == JobStatus.pending.value), key=lambda j: (j.created_at, j.id))
    ends: dict[int, datetime] = {}
    t = now
    if cur:
        t = now + timedelta(minutes=max(0.0, cur.estimated_minutes * (1 - cur.progress_pct / 100)))
        ends[cur.id] = t
    available_at = t
    for j in queued:
        t = t + timedelta(minutes=j.estimated_minutes)
        ends[j.id] = t
    return cur, queued + pending, ends, available_at, t


# ---------- Vistas ----------
def _opts():
    return (joinedload(PrintJob.user), joinedload(PrintJob.printer), joinedload(PrintJob.filament))


def load_jobs(db: Session, *conditions, order=None, limit: int | None = None, offset: int = 0) -> list[PrintJob]:
    q = select(PrintJob).options(*_opts()).where(*conditions)
    q = q.order_by(*(order or (PrintJob.created_at.desc(),)))
    if limit is not None:
        q = q.limit(limit).offset(offset)
    return list(db.scalars(q).unique())


def job_views(db: Session, jobs: list[PrintJob], viewer: User) -> list[dict]:
    is_admin = viewer.role == "admin"
    cache: dict[int, tuple] = {}
    unassigned = sorted(
        (j.id for j in db.scalars(
            select(PrintJob).where(PrintJob.printer_id.is_(None), PrintJob.status == JobStatus.pending.value)
            .order_by(PrintJob.created_at, PrintJob.id)
        )),
    )
    out = []
    for j in jobs:
        ends, position = {}, None
        if j.printer_id:
            if j.printer_id not in cache:
                cache[j.printer_id] = schedule_for(db, j.printer_id)
            cur, queue, ends, _, _ = cache[j.printer_id]
            if j.status in (JobStatus.queued.value, JobStatus.pending.value):
                ids = [q.id for q in queue]
                position = ids.index(j.id) + 1 if j.id in ids else None
        elif j.status == JobStatus.pending.value and j.id in unassigned:
            position = unassigned.index(j.id) + 1
        mine = j.user_id == viewer.id
        show_private = is_admin or mine
        out.append(
            {
                "id": j.id,
                "user_id": j.user_id if show_private else 0,
                "user_name": j.user.name if show_private else None,
                "project_name": j.project_name,
                "printer_id": j.printer_id,
                "printer_name": j.printer.name if j.printer else None,
                "filament_id": j.filament_id,
                "material": j.filament.material if j.filament else None,
                "color": j.filament.color if j.filament else None,
                "color_hex": j.filament.color_hex if j.filament else None,
                "status": j.status,
                "grams_estimated": j.grams_estimated,
                "grams_used": j.grams_used,
                "estimated_minutes": j.estimated_minutes,
                "progress_pct": j.progress_pct,
                "queue_position": position,
                "estimated_end_at": ends.get(j.id),
                "failure_reason": j.failure_reason,
                "notes": j.notes if show_private else None,
                "is_mine": mine,
                "is_demo": j.is_demo,
                "created_at": j.created_at,
                "queued_at": j.queued_at,
                "started_at": j.started_at,
                "finished_at": j.finished_at,
                "duration_min": j.duration_min,
            }
        )
    return out


# ---------- Validaciones ----------
def _get_printer(db: Session, printer_id: int) -> Equipment:
    p = db.get(Equipment, printer_id)
    if not p or p.type != EquipmentType.printer_3d.value:
        raise HTTPException(404, "Impresora no encontrada")
    return p


def _check_material(printer: Equipment, filament: Filament) -> None:
    mats = [m.upper() for m in (printer.supported_materials or [])]
    if mats and filament.material.upper() not in mats:
        raise HTTPException(409, f"{printer.name} no admite {filament.material} (admite {', '.join(mats)})")


def reservation_conflict(db: Session, printer_id: int, user_id: int, start: datetime, end: datetime) -> Reservation | None:
    return db.scalar(
        select(Reservation).where(
            Reservation.printer_id == printer_id,
            Reservation.user_id != user_id,
            Reservation.status == ReservationStatus.approved.value,
            Reservation.start_at < end,
            Reservation.end_at > start,
        )
    )


def validate_assignment(db: Session, printer_id: int | None, filament_id: int | None) -> tuple[Equipment | None, Filament | None]:
    printer = _get_printer(db, printer_id) if printer_id else None
    filament = None
    if filament_id:
        filament = db.get(Filament, filament_id)
        if not filament or not filament.is_active:
            raise HTTPException(404, "Filamento no encontrado o inactivo")
    if printer and filament:
        _check_material(printer, filament)
    return printer, filament


# ---------- Transiciones ----------
def start_job(db: Session, job: PrintJob, ignore_reservations: bool = False, now: datetime | None = None) -> None:
    now = now or utcnow()
    printer, filament = validate_assignment(db, job.printer_id, job.filament_id)
    if not printer:
        raise HTTPException(409, "Asigne una impresora antes de iniciar")
    if not filament:
        raise HTTPException(409, "Asigne un filamento antes de iniciar")
    if printer.status in MANUAL_STATES:
        raise HTTPException(409, f"{printer.name} no está operativa ({printer.status})")
    other = printing_job(db, printer.id)
    if other and other.id != job.id:
        raise HTTPException(409, f"{printer.name} ya está imprimiendo '{other.project_name}'")
    if filament.available_weight_g < job.grams_estimated:
        raise HTTPException(
            409, f"Filamento insuficiente: se requieren {job.grams_estimated:.0f} g y quedan {filament.available_weight_g:.0f} g"
        )
    if not ignore_reservations:
        conflict = reservation_conflict(db, printer.id, job.user_id, now, now + timedelta(minutes=job.estimated_minutes))
        if conflict:
            raise HTTPException(
                409, f"Hay una reserva aprobada en {printer.name} que se cruza con este trabajo (reserva #{conflict.id})"
            )
    job.status = JobStatus.printing.value
    job.started_at = now
    job.progress_pct = 0.0
    job.finished_at = None
    db.flush()
    refresh_printer(db, printer)


def _consume(db: Session, job: PrintJob, grams: float, when: datetime, actor_id: int | None) -> None:
    job.grams_used = round(grams, 1)
    if job.filament and grams > 0:
        apply_movement(
            db, job.filament, MovementType.stock_out, grams, f"Trabajo #{job.id}: {job.project_name}",
            job_id=job.id, user_id=actor_id, when=when, clamp=True,
        )


def _close(db: Session, job: PrintJob, status: JobStatus, now: datetime) -> None:
    job.status = status.value
    job.finished_at = now
    if job.started_at:
        job.duration_min = round(max(0.0, (now - job.started_at).total_seconds() / 60), 1)
    db.flush()
    if job.printer:
        refresh_printer(db, job.printer)


def transition(
    db: Session,
    job: PrintJob,
    action: str,
    actor: User | None = None,
    grams_used: float | None = None,
    failure_reason: str | None = None,
    printer_id: int | None = None,
    filament_id: int | None = None,
    ignore_reservations: bool = False,
    now: datetime | None = None,
) -> PrintJob:
    now = now or utcnow()
    actor_id = actor.id if actor else None
    st = job.status
    if printer_id or filament_id:
        validate_assignment(db, printer_id or job.printer_id, filament_id or job.filament_id)
        job.printer_id = printer_id or job.printer_id
        job.filament_id = filament_id or job.filament_id
        db.flush()
        db.refresh(job)

    if action == "queue":
        if st != JobStatus.pending.value:
            raise HTTPException(409, "Solo un trabajo pendiente puede ponerse en cola")
        if not job.printer_id:
            raise HTTPException(409, "Asigne una impresora para poner el trabajo en cola")
        job.status = JobStatus.queued.value
        job.queued_at = now
    elif action == "start":
        if st not in (JobStatus.pending.value, JobStatus.queued.value):
            raise HTTPException(409, "Solo se puede iniciar un trabajo pendiente o en cola")
        start_job(db, job, ignore_reservations, now)
    elif action == "complete":
        if st != JobStatus.printing.value:
            raise HTTPException(409, "Solo se puede completar un trabajo en proceso")
        job.progress_pct = 100.0
        _consume(db, job, grams_used if grams_used is not None else job.grams_estimated, now, actor_id)
        _close(db, job, JobStatus.completed, now)
    elif action == "fail":
        if st != JobStatus.printing.value:
            raise HTTPException(409, "Solo se puede marcar como fallido un trabajo en proceso")
        partial = job.grams_estimated * job.progress_pct / 100
        _consume(db, job, grams_used if grams_used is not None else partial, now, actor_id)
        job.failure_reason = failure_reason or "other"
        _close(db, job, JobStatus.failed, now)
    elif action == "cancel":
        if st not in ACTIVE:
            raise HTTPException(409, "El trabajo ya finalizó")
        if st == JobStatus.printing.value:
            partial = job.grams_estimated * job.progress_pct / 100
            _consume(db, job, grams_used if grams_used is not None else partial, now, actor_id)
        _close(db, job, JobStatus.cancelled, now)
    else:  # pragma: no cover
        raise HTTPException(400, "Acción inválida")
    return job


def start_next_in_queue(db: Session, printer_id: int, now: datetime | None = None) -> PrintJob | None:
    """Usado por el simulador: al liberarse la impresora arranca el siguiente trabajo en cola."""
    printer = db.get(Equipment, printer_id)
    if not printer or printer.status in MANUAL_STATES or printing_job(db, printer_id):
        return None
    nxt = db.scalar(
        select(PrintJob)
        .where(PrintJob.printer_id == printer_id, PrintJob.status == JobStatus.queued.value)
        .order_by(PrintJob.queued_at, PrintJob.id)
    )
    if not nxt:
        return None
    try:
        start_job(db, nxt, ignore_reservations=True, now=now)
    except HTTPException:
        return None
    return nxt


def create_historical_consumption(db: Session, job: PrintJob, actor_id: int | None) -> None:
    """Para trabajos registrados a posteriori (completados/fallidos)."""
    grams = job.grams_used if job.grams_used else job.grams_estimated
    if job.status == JobStatus.completed.value:
        job.progress_pct = 100.0
    _consume(db, job, grams, job.finished_at or utcnow(), actor_id)
    job.duration_min = round((job.finished_at - job.started_at).total_seconds() / 60, 1)
