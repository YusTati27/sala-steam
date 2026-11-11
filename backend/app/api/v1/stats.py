from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import demo_flag, require_admin
from app.core.timeutil import utcnow
from app.models.entities import Equipment, EquipmentType, Filament, JobStatus, PrintJob, Reservation
from app.services import stats as svc
from app.services.alerts import build_alerts
from app.services.filaments import stock_status

router = APIRouter(tags=["stats"], dependencies=[Depends(require_admin)])


@router.get("/stats/overview")
def overview(date_from: date | None = None, date_to: date | None = None, printer_id: int | None = None, material: str | None = None,
             status: JobStatus | None = None, demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    dto = date_to or date.today()
    dfrom = date_from or dto - timedelta(days=179)
    if dfrom > dto:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la final")
    if (dto - dfrom).days > 800:
        raise HTTPException(422, "El rango máximo es de ~2 años")
    return svc.overview(db, demo, dfrom, dto, printer_id, material, status.value if status else None)


@router.get("/alerts")
def alerts(demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    return build_alerts(db, demo)


@router.get("/stats/dashboard")
def dashboard(demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    printers = list(db.scalars(select(Equipment).where(Equipment.is_demo == demo, Equipment.type == EquipmentType.printer_3d.value)))
    pc = {s: sum(1 for p in printers if p.status == s) for s in ("available", "busy", "maintenance", "out_of_service")}
    counts = dict(db.execute(select(PrintJob.status, func.count()).where(PrintJob.is_demo == demo).group_by(PrintJob.status)).all())
    comp, fail, canc = (counts.get(s, 0) for s in ("completed", "failed", "cancelled"))
    alerts_ = build_alerts(db, demo)
    low = [f for f in db.scalars(select(Filament).where(Filament.is_demo == demo, Filament.is_active.is_(True))) if stock_status(f) != "available"]
    today = date.today()
    ov = svc.overview(db, demo, today - timedelta(days=29), today)
    recent = svc.fetch_jobs(db, demo, today - timedelta(days=29), today)
    return {
        "demo": demo,
        "printers": {"total": len(printers), **pc},
        "jobs": {"completed": comp, "failed": fail, "cancelled": canc, "pending": counts.get("pending", 0) + counts.get("queued", 0),
                 "printing": counts.get("printing", 0), "completion_pct": svc.pct(comp, comp + fail + canc)},
        "maintenance_alerts": sum(1 for a in alerts_ if a["type"].startswith("maintenance") or a["type"] == "equipment_down"),
        "low_stock": len(low),
        "pending_reservations": db.scalar(select(func.count()).select_from(Reservation).where(Reservation.is_demo == demo, Reservation.status == "pending")),
        "last_30_days": {"kpis": ov["kpis"], "comparison": ov["comparison"], "series": ov["jobs_by_period"], "granularity": ov["period"]["granularity"],
                         "insights": ov["insights"][:4]},
        "alerts": alerts_[:8],
        "printing_now": [
            {"printer": j.printer.name if j.printer else "", "project": j.project_name, "progress_pct": j.progress_pct}
            for j in recent if j.status == JobStatus.printing.value
        ],
        "generated_at": utcnow().isoformat() + "Z",
    }

