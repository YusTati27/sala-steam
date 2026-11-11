from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import demo_flag, get_current_user, require_admin
from app.core.timeutil import utcnow
from app.models.entities import Filament, FilamentMovement, MovementType, User
from app.schemas.filament import FilamentCreate, FilamentOut, FilamentUpdate, MovementIn, MovementOut
from app.services.filaments import apply_movement, consumed_map, next_code, stock_status
from app.ws.manager import manager

router = APIRouter(prefix="/filaments", tags=["inventory"])


def _view(f: Filament, admin: bool, consumed: dict[int, float]) -> dict:
    return {
        "id": f.id, "code": f.code, "material": f.material, "brand": f.brand, "color": f.color, "color_hex": f.color_hex,
        "initial_weight_g": f.initial_weight_g if admin else None,
        "available_weight_g": round(f.available_weight_g),
        "consumed_g": round(consumed.get(f.id, 0.0)) if admin else None,
        "low_stock_threshold_g": f.low_stock_threshold_g if admin else None,
        "acquired_at": f.acquired_at if admin else None, "is_active": f.is_active, "is_demo": f.is_demo,
        "stock_status": stock_status(f), "notes": f.notes if admin else None,
    }


def _get(db: Session, fid: int, demo: bool) -> Filament:
    f = db.get(Filament, fid)
    if not f or f.is_demo != demo:
        raise HTTPException(404, "Filamento no encontrado")
    return f


@router.get("", response_model=list[FilamentOut])
def list_filaments(material: str | None = None, include_inactive: bool = False, user: User = Depends(get_current_user),
                   demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    q = select(Filament).where(Filament.is_demo == demo).order_by(Filament.material, Filament.color, Filament.id)
    if material:
        q = q.where(Filament.material == material.upper())
    if not (include_inactive and user.role == "admin"):
        q = q.where(Filament.is_active.is_(True))
    rows = list(db.scalars(q))
    cm = consumed_map(db, [f.id for f in rows]) if user.role == "admin" else {}
    return [_view(f, user.role == "admin", cm) for f in rows]


@router.get("/summary")
def summary(_: User = Depends(get_current_user), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    """Disponibilidad por material (visible para clientes)."""
    groups = defaultdict(list)
    for f in db.scalars(select(Filament).where(Filament.is_demo == demo, Filament.is_active.is_(True))):
        groups[f.material].append(f)
    out = []
    for m, fs in sorted(groups.items()):
        total = sum(f.available_weight_g for f in fs)
        usable = [f for f in fs if stock_status(f) != "empty"]
        low = [f for f in fs if stock_status(f) == "low"]
        out.append({
            "material": m, "available_g": round(total), "spools": len(fs), "colors": sorted({f.color for f in usable}),
            "status": "empty" if not usable else "low" if len(low) == len(usable) else "available",
        })
    return out


@router.get("/movements/all")
def all_movements(limit: int = 100, filament_id: int | None = None, _: User = Depends(require_admin),
                  demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    q = (select(FilamentMovement, Filament).join(Filament, Filament.id == FilamentMovement.filament_id)
         .where(FilamentMovement.is_demo == demo).order_by(FilamentMovement.created_at.desc(), FilamentMovement.id.desc())
         .limit(min(limit, 500)))
    if filament_id:
        q = q.where(FilamentMovement.filament_id == filament_id)
    return [
        {"id": m.id, "filament_id": f.id, "filament": f"{f.material} {f.color} ({f.code})", "type": m.type, "grams": m.grams,
         "balance_after_g": m.balance_after_g, "note": m.note, "job_id": m.job_id, "created_at": m.created_at.isoformat() + "Z"}
        for m, f in db.execute(q)
    ]


@router.post("", response_model=FilamentOut, status_code=201)
def create_filament(data: FilamentCreate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    code = (data.code or next_code(db)).strip().upper()
    if db.scalar(select(Filament.id).where(Filament.code == code)):
        raise HTTPException(409, f"Ya existe una bobina con el código {code}")
    avail = data.initial_weight_g if data.available_weight_g is None else data.available_weight_g
    if avail > data.initial_weight_g:
        raise HTTPException(422, "El peso disponible no puede superar el peso inicial")
    dup = db.scalar(select(Filament.id).where(
        Filament.is_demo == demo, Filament.material == data.material, Filament.color == data.color, Filament.brand == data.brand,
        Filament.acquired_at == data.acquired_at, Filament.initial_weight_g == data.initial_weight_g))
    if dup and data.acquired_at:
        raise HTTPException(409, "Ya existe una bobina idéntica registrada en esa fecha (posible duplicado)")
    f = Filament(code=code, material=data.material, brand=data.brand, color=data.color.strip().title(), color_hex=data.color_hex,
                 initial_weight_g=data.initial_weight_g, available_weight_g=0, low_stock_threshold_g=data.low_stock_threshold_g,
                 acquired_at=data.acquired_at, notes=data.notes, is_demo=demo)
    db.add(f)
    db.flush()
    apply_movement(db, f, MovementType.stock_in, avail, "Alta de bobina", user_id=admin.id)
    db.commit()
    manager.notify("filaments")
    return _view(f, True, {})


@router.patch("/{fid}", response_model=FilamentOut)
def update_filament(fid: int, data: FilamentUpdate, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag),
                    db: Session = Depends(get_db)):
    f = _get(db, fid, demo)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    db.commit()
    manager.notify("filaments")
    return _view(f, True, consumed_map(db, [f.id]))


@router.post("/{fid}/movements", response_model=MovementOut, status_code=201)
def add_movement(fid: int, data: MovementIn, admin: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    f = _get(db, fid, demo)
    mov = apply_movement(db, f, data.type, data.grams, data.note or {"in": "Entrada", "out": "Salida manual", "adjust": "Ajuste"}[data.type.value],
                         user_id=admin.id, when=utcnow())
    if data.type == MovementType.stock_in and not f.is_active:
        f.is_active = True
    db.commit()
    manager.notify("filaments")
    return mov


@router.get("/{fid}/movements", response_model=list[MovementOut])
def movements(fid: int, _: User = Depends(require_admin), demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    _get(db, fid, demo)
    return list(db.scalars(select(FilamentMovement).where(FilamentMovement.filament_id == fid)
                           .order_by(FilamentMovement.created_at.desc(), FilamentMovement.id.desc()).limit(200)))

