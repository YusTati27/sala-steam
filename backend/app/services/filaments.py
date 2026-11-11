from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models.entities import Filament, FilamentMovement, MovementType


def stock_status(f: Filament) -> str:
    if f.available_weight_g <= 0.5:
        return "empty"
    if f.available_weight_g <= f.low_stock_threshold_g:
        return "low"
    return "available"


def apply_movement(
    db: Session,
    f: Filament,
    type_: MovementType,
    grams: float,
    note: str = "",
    job_id: int | None = None,
    user_id: int | None = None,
    when: datetime | None = None,
    clamp: bool = False,
) -> FilamentMovement:
    """Registra una entrada/salida/ajuste y mantiene `available_weight_g` coherente.

    adjust: `grams` es el peso real medido (se fija como nuevo disponible).
    clamp: en salidas, descuenta como máximo lo disponible (consumo de un trabajo).
    """
    if type_ == MovementType.stock_in:
        f.available_weight_g += grams
        recorded = grams
    elif type_ == MovementType.stock_out:
        if grams > f.available_weight_g + 1e-6:
            if not clamp:
                raise HTTPException(409, f"Stock insuficiente: quedan {f.available_weight_g:.0f} g")
            grams = f.available_weight_g
        f.available_weight_g -= grams
        recorded = grams
    else:
        f.available_weight_g = grams
        recorded = grams
    f.available_weight_g = round(max(0.0, f.available_weight_g), 2)
    mov = FilamentMovement(
        filament_id=f.id,
        type=type_.value,
        grams=round(recorded, 2),
        balance_after_g=f.available_weight_g,
        note=note,
        job_id=job_id,
        user_id=user_id,
        is_demo=f.is_demo,
        created_at=when or utcnow(),
    )
    db.add(mov)
    return mov


def consumed_map(db: Session, ids: list[int] | None = None) -> dict[int, float]:
    q = select(FilamentMovement.filament_id, func.sum(FilamentMovement.grams)).where(
        FilamentMovement.type == MovementType.stock_out.value
    )
    if ids is not None:
        q = q.where(FilamentMovement.filament_id.in_(ids))
    return {fid: float(g or 0) for fid, g in db.execute(q.group_by(FilamentMovement.filament_id))}


def next_code(db: Session) -> str:
    n = (db.scalar(select(func.max(Filament.id))) or 0) + 1
    code = f"FIL-{n:04d}"
    while db.scalar(select(Filament.id).where(Filament.code == code)):
        n += 1
        code = f"FIL-{n:04d}"
    return code
