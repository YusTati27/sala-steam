from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models.entities import (
    Equipment,
    EquipmentStatus,
    Filament,
    JobStatus,
    PrintJob,
    Reservation,
    ReservationStatus,
)
from app.services.equipment import MAINT_SOON_DAYS
from app.services.filaments import stock_status


def build_alerts(db: Session, demo: bool) -> list[dict]:
    alerts: list[dict] = []
    today = date.today()

    for eq in db.scalars(select(Equipment).where(Equipment.is_demo == demo).order_by(Equipment.name)):
        if eq.status == EquipmentStatus.out_of_service.value:
            alerts.append({"type": "equipment_down", "severity": "critical", "title": f"{eq.name} fuera de servicio",
                           "detail": eq.notes or "Requiere revisión", "entity": "equipment", "entity_id": eq.id})
        if eq.next_maintenance_at:
            left = (eq.next_maintenance_at - today).days
            if left < 0:
                alerts.append({"type": "maintenance_overdue", "severity": "critical",
                               "title": f"Mantenimiento vencido: {eq.name}",
                               "detail": f"Venció hace {-left} días ({eq.next_maintenance_at})", "entity": "equipment", "entity_id": eq.id})
            elif left <= MAINT_SOON_DAYS:
                alerts.append({"type": "maintenance_soon", "severity": "warning",
                               "title": f"Mantenimiento próximo: {eq.name}",
                               "detail": f"En {left} días ({eq.next_maintenance_at})", "entity": "equipment", "entity_id": eq.id})

    for f in db.scalars(select(Filament).where(Filament.is_demo == demo, Filament.is_active.is_(True))):
        st = stock_status(f)
        if st != "available":
            alerts.append({"type": "low_stock", "severity": "critical" if st == "empty" else "warning",
                           "title": f"{'Agotado' if st == 'empty' else 'Inventario bajo'}: {f.material} {f.color}",
                           "detail": f"Quedan {f.available_weight_g:.0f} g (umbral {f.low_stock_threshold_g:.0f} g)",
                           "entity": "filament", "entity_id": f.id})

    pending_res = db.scalar(
        select(func.count()).select_from(Reservation).where(
            Reservation.is_demo == demo, Reservation.status == ReservationStatus.pending.value
        )
    )
    if pending_res:
        alerts.append({"type": "reservations_pending", "severity": "info",
                       "title": f"{pending_res} reserva(s) esperan aprobación", "detail": "", "entity": "reservation", "entity_id": None})

    failed_recent = db.scalar(
        select(func.count()).select_from(PrintJob).where(
            PrintJob.is_demo == demo, PrintJob.status == JobStatus.failed.value,
            PrintJob.finished_at >= utcnow() - timedelta(hours=48),
        )
    )
    if failed_recent:
        alerts.append({"type": "recent_failures", "severity": "warning",
                       "title": f"{failed_recent} impresión(es) fallida(s) en las últimas 48 h", "detail": "", "entity": "job", "entity_id": None})

    order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: order[a["severity"]])
    return alerts
