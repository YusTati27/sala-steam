from datetime import date

from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models.entities import Equipment, EquipmentType, User
from app.services.jobs import schedule_for

MAINT_SOON_DAYS = 14


def maintenance_days_left(eq: Equipment) -> int | None:
    return (eq.next_maintenance_at - date.today()).days if eq.next_maintenance_at else None


def equipment_view(db: Session, eq: Equipment, viewer: User) -> dict:
    is_admin = viewer.role == "admin"
    now = utcnow()
    data = {
        "id": eq.id, "code": eq.code, "name": eq.name, "model": eq.model, "type": eq.type, "status": eq.status,
        "build_volume": eq.build_volume, "nozzle_mm": eq.nozzle_mm, "supported_materials": eq.supported_materials or [],
        "specs": eq.specs or {}, "hardware_endpoint": eq.hardware_endpoint if is_admin else None,
        "acquired_at": eq.acquired_at, "last_maintenance_at": eq.last_maintenance_at if is_admin else None,
        "next_maintenance_at": eq.next_maintenance_at if is_admin else None,
        "notes": eq.notes if is_admin else None, "is_demo": eq.is_demo,
        "current_job": None, "available_at": None, "queue_length": 0, "queue_clear_at": None,
        "maintenance_days_left": maintenance_days_left(eq) if is_admin else None,
    }
    if eq.type == EquipmentType.printer_3d.value:
        cur, queue, ends, available_at, clear_at = schedule_for(db, eq.id, now)
        if cur:
            data["current_job"] = {
                "id": cur.id,
                "project_name": cur.project_name,
                "progress_pct": cur.progress_pct,
                "estimated_end_at": ends.get(cur.id),
                "is_mine": cur.user_id == viewer.id,
            }
        data["queue_length"] = len(queue)
        if eq.status in ("available", "busy"):
            data["available_at"] = available_at
            data["queue_clear_at"] = clear_at
    return data
