import csv
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import demo_flag, get_current_user, require_admin
from app.core.timeutil import utcnow
from app.models.entities import JobStatus, PrintJob, User
from app.schemas.job import JobCreate, JobOut, JobPage, JobUpdate, TransitionIn
from app.services import jobs as svc
from app.services import stats
from app.ws.manager import manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get(db: Session, job_id: int, demo: bool) -> PrintJob:
    j = db.get(PrintJob, job_id)
    if not j or j.is_demo != demo:
        raise HTTPException(404, "Trabajo no encontrado")
    return j


@router.get("", response_model=JobPage)
def list_jobs(status: JobStatus | None = None, printer_id: int | None = None, user_id: int | None = None, q: str | None = None,
              date_from: date | None = None, date_to: date | None = None, limit: int = 25, offset: int = 0,
              admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    conds = [PrintJob.is_demo == demo]
    if status:
        conds.append(PrintJob.status == status.value)
    if printer_id:
        conds.append(PrintJob.printer_id == printer_id)
    if user_id:
        conds.append(PrintJob.user_id == user_id)
    if q:
        like = f"%{q.strip()}%"
        conds.append(or_(PrintJob.project_name.ilike(like), PrintJob.user.has(User.name.ilike(like))))
    t = func.coalesce(PrintJob.started_at, PrintJob.created_at)
    if date_from:
        conds.append(t >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        conds.append(t < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    total = db.scalar(select(func.count()).select_from(PrintJob).where(*conds)) or 0
    rows = svc.load_jobs(db, *conds, order=(func.coalesce(PrintJob.started_at, PrintJob.created_at).desc(), PrintJob.id.desc()),
                         limit=min(limit, 200), offset=offset)
    return {"items": svc.job_views(db, rows, admin), "total": total}


@router.get("/queue", response_model=list[JobOut])
def queue(user: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    """Trabajos en proceso, en cola y pendientes (visible para todos; los datos personales se ocultan a los clientes)."""
    rows = svc.load_jobs(db, PrintJob.is_demo == demo, PrintJob.status.in_(svc.ACTIVE))
    views = svc.job_views(db, rows, user)
    rank = {"printing": 0, "queued": 1, "pending": 2}
    views.sort(key=lambda v: (rank[v["status"]], v["printer_name"] or "~", v["queue_position"] or 0, v["id"]))
    return views


@router.get("/mine", response_model=list[JobOut])
def my_jobs(history: bool = False, user: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    conds = [PrintJob.is_demo == demo, PrintJob.user_id == user.id]
    conds.append(PrintJob.status.not_in(svc.ACTIVE) if history else PrintJob.status.in_(svc.ACTIVE))
    rows = svc.load_jobs(db, *conds, order=(func.coalesce(PrintJob.started_at, PrintJob.created_at).desc(), PrintJob.id.desc()), limit=300)
    return svc.job_views(db, rows, user)


@router.get("/export.csv")
def export_csv(date_from: date, date_to: date, printer_id: int | None = None, material: str | None = None, status: str | None = None,
               _: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    jobs = stats.fetch_jobs(db, demo, date_from, date_to, printer_id, material, status)
    buf = io.StringIO()
    buf.write("﻿")  # BOM para que Excel respete los acentos
    csv.writer(buf, delimiter=";").writerows(stats.jobs_csv_rows(jobs))
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="trabajos_{date_from}_{date_to}.csv"'})


@router.post("", response_model=JobOut, status_code=201)
def create_job(data: JobCreate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    owner = db.get(User, data.user_id)
    if not owner or not owner.is_active or (owner.is_demo and not demo):
        raise HTTPException(404, "Usuario responsable no encontrado")
    svc.validate_assignment(db, data.printer_id, data.filament_id)
    now = utcnow()
    job = PrintJob(user_id=data.user_id, project_name=data.project_name.strip(), printer_id=data.printer_id, filament_id=data.filament_id,
                   grams_estimated=data.grams_estimated, estimated_minutes=data.estimated_minutes, notes=data.notes, is_demo=demo,
                   status=JobStatus.pending.value, created_at=now)
    db.add(job)
    db.flush()
    db.refresh(job)
    target = data.status
    if target in (JobStatus.completed, JobStatus.failed):
        job.started_at, job.finished_at = data.started_at, data.finished_at
        job.status = target.value
        job.failure_reason = (data.failure_reason.value if data.failure_reason else "other") if target == JobStatus.failed else None
        job.grams_used = data.grams_used if data.grams_used is not None else data.grams_estimated
        if target == JobStatus.failed and data.grams_used is None:
            job.grams_used = round(data.grams_estimated * 0.5, 1)
            job.progress_pct = 50.0
        job.created_at = data.started_at
        svc.create_historical_consumption(db, job, admin.id)
    elif target == JobStatus.cancelled:
        job.status = JobStatus.cancelled.value
        job.finished_at = now
    elif target in (JobStatus.queued, JobStatus.printing):
        svc.transition(db, job, "queue", admin, now=now)
        if target == JobStatus.printing:
            svc.transition(db, job, "start", admin, now=now)
    db.commit()
    manager.notify("jobs", "equipment", "filaments")
    return svc.job_views(db, svc.load_jobs(db, PrintJob.id == job.id), admin)[0]


@router.patch("/{job_id}", response_model=JobOut)
def update_job(job_id: int, data: JobUpdate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    job = _get(db, job_id, demo)
    if job.status not in svc.ACTIVE:
        raise HTTPException(409, "Un trabajo finalizado no se puede editar")
    vals = data.model_dump(exclude_unset=True)
    if job.status == JobStatus.printing.value and ("printer_id" in vals or "filament_id" in vals):
        raise HTTPException(409, "No se puede cambiar la impresora o el filamento de un trabajo en proceso")
    if "progress_pct" in vals and job.status != JobStatus.printing.value:
        raise HTTPException(409, "Solo se puede actualizar el progreso de un trabajo en proceso")
    svc.validate_assignment(db, vals.get("printer_id", job.printer_id), vals.get("filament_id", job.filament_id))
    for k, v in vals.items():
        setattr(job, k, v)
    db.commit()
    manager.notify("jobs", "equipment")
    return svc.job_views(db, svc.load_jobs(db, PrintJob.id == job.id), admin)[0]


@router.post("/{job_id}/transition", response_model=JobOut)
def transition(job_id: int, data: TransitionIn, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    job = _get(db, job_id, demo)
    svc.transition(db, job, data.action, admin, data.grams_used, data.failure_reason.value if data.failure_reason else None,
                   data.printer_id, data.filament_id, data.ignore_reservations)
    db.commit()
    manager.notify("jobs", "equipment", "filaments")
    return svc.job_views(db, svc.load_jobs(db, PrintJob.id == job.id), admin)[0]

