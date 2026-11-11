"""Simulador de la sala STEAM.

TODOS los registros generados aquí llevan `is_demo = True` y son datos INVENTADOS para demostración.
Nunca se mezclan con datos reales: el sistema trabaja en modo "demo" o "real" (ver app_settings).
"""

import random
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.timeutil import utcnow
from app.models.entities import (
    Equipment,
    EquipmentStatus,
    Filament,
    FilamentMovement,
    JobStatus,
    MaintenanceRecord,
    MovementType,
    PrintJob,
    Reservation,
    Role,
    User,
)
from app.services import jobs as jobsvc
from app.services.filaments import apply_movement

# (código, nombre, modelo, volumen, boquilla, materiales)
PRINTERS = [
    ("DEMO-IMP-01", "Impresora 01", "Prusa MK4", "250×210×220 mm", 0.4, ["PLA", "PETG", "ABS", "TPU"]),
    ("DEMO-IMP-02", "Impresora 02", "Bambu Lab P1S", "256×256×256 mm", 0.4, ["PLA", "PETG", "ABS", "TPU"]),
    ("DEMO-IMP-03", "Impresora 03", "Creality Ender-3 V3", "220×220×250 mm", 0.4, ["PLA", "PETG", "TPU"]),
    ("DEMO-IMP-04", "Impresora 04", "Anycubic Kobra 2", "220×220×250 mm", 0.4, ["PLA", "PETG"]),
    ("DEMO-IMP-05", "Impresora 05", "Elegoo Neptune 4", "225×225×265 mm", 0.4, ["PLA", "PETG", "TPU"]),
    ("DEMO-IMP-06", "Impresora 06", "Creality CR-10 Smart", "300×300×400 mm", 0.4, ["PLA", "PETG"]),
]
PROBLEM_PRINTER = "DEMO-IMP-03"
TOOLS = [
    ("DEMO-HER-01", "Estación de soldadura", "Hakko FX-888D"),
    ("DEMO-HER-02", "Taladro de banco", "Genérico 13 mm"),
    ("DEMO-HER-03", "Multímetro de laboratorio", "Fluke 115"),
]
COLORS = {
    "Negro": "#1A1A1A", "Blanco": "#F2F2F2", "Rojo": "#D32F2F", "Azul": "#1E4FD8", "Cian": "#00BCD4",
    "Gris": "#8E8E8E", "Verde": "#2E9E4F", "Naranja": "#F57C00", "Transparente": "#CFE8EF",
}
COLOR_W = {"Negro": 22, "Blanco": 16, "Rojo": 10, "Azul": 12, "Cian": 9, "Gris": 9, "Verde": 6, "Naranja": 5, "Transparente": 5}
SLOTS = {
    "PLA": ["Negro", "Blanco", "Rojo", "Azul", "Cian", "Gris", "Verde", "Naranja"],
    "PETG": ["Transparente", "Negro", "Azul", "Naranja"],
    "ABS": ["Negro", "Blanco", "Rojo"],
    "TPU": ["Negro"],
}
MATERIAL_W = {"PLA": 62, "PETG": 22, "ABS": 10, "TPU": 6}
BRANDS = {"PLA": "Marca Demo A", "PETG": "Marca Demo B", "ABS": "Marca Demo A", "TPU": "Marca Demo C"}
PROJECTS = [
    "Soporte de sensor", "Carcasa Arduino", "Engranaje de robot", "Prototipo de dron", "Maqueta de puente", "Llavero con logo",
    "Pieza de brazo robótico", "Funda de batería", "Rueda para robot", "Soporte de celular", "Caja para PCB", "Acople de motor",
    "Maqueta de edificio", "Brazo de grúa", "Carcasa de sensor", "Pieza de turbina", "Ficha de juego", "Molde de práctica",
]
FAIL_REASONS_BASE = ["adhesion", "nozzle_clog", "filament_issue", "warping", "power_outage", "user_error", "other"]


def _wchoice(rng: random.Random, weights: dict):
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def clear_demo(db: Session) -> None:
    for model in (FilamentMovement, Reservation, MaintenanceRecord, PrintJob, Filament, Equipment, User):
        db.execute(delete(model).where(model.is_demo.is_(True)))
    db.commit()


def has_demo_data(db: Session) -> bool:
    return db.scalar(select(Equipment.id).where(Equipment.is_demo.is_(True)).limit(1)) is not None


def _local_to_utc(d: datetime) -> datetime:
    return d - timedelta(hours=get_settings().local_utc_offset_hours)


def _request_times(rng: random.Random, now: datetime, months: int) -> list[datetime]:
    off = timedelta(hours=get_settings().local_utc_offset_hours)
    start_day = (now + off).date() - timedelta(days=30 * months)
    day_w = {0: 1.0, 1: 1.1, 2: 1.0, 3: 1.0, 4: 0.8, 5: 0.25, 6: 0.04}
    hour_w = {7: 0.3, 8: 1, 9: 2, 10: 3, 11: 3, 12: 1.2, 13: 1.6, 14: 3, 15: 3, 16: 2, 17: 1, 18: 0.5, 19: 0.2}
    out = []
    d = start_day
    today = (now + off).date()
    while d < today:
        # Más demanda hacia mitad de semestre y semanas de entrega
        progress = (d - start_day).days / (30 * months)
        season = 0.7 + 0.9 * (1 - abs(progress - 0.62) * 2) if progress < 0.95 else 0.9
        lam = 4.2 * day_w[d.weekday()] * max(0.4, season)
        n = sum(1 for _ in range(16) if rng.random() < lam / 16)
        for _ in range(n):
            h = _wchoice(rng, hour_w)
            out.append(_local_to_utc(datetime(d.year, d.month, d.day, h, rng.randint(0, 59))))
        d += timedelta(days=1)
    return sorted(out)


def generate_demo(db: Session, months: int = 6, seed: int = 42) -> dict:
    rng = random.Random(seed)
    clear_demo(db)
    now = utcnow()
    today = date.today()

    # ----- Usuarios (claramente de demostración; no pueden iniciar sesión) -----
    unusable = hash_password(f"{rng.random()}-{seed}-{now.timestamp()}")
    demo_users = []
    for i in range(1, 15):
        u = User(name=f"Estudiante Demo {i:02d}", email=f"demo{i:02d}@demo.invalid", password_hash=unusable,
                 role=Role.client.value, is_active=True, is_demo=True)
        db.add(u)
        demo_users.append(u)
    real_clients = list(db.scalars(select(User).where(User.role == Role.client.value, User.is_demo.is_(False), User.is_active.is_(True))))
    db.flush()
    pool = demo_users + real_clients * 2  # los clientes reales también ven historial simulado propio

    # ----- Equipos -----
    printers: list[Equipment] = []
    maint_state = {
        "DEMO-IMP-01": (80, "available"), "DEMO-IMP-02": (100, "available"), "DEMO-IMP-03": (30, "available"),
        "DEMO-IMP-04": (45, "available"), "DEMO-IMP-05": (60, "maintenance"), "DEMO-IMP-06": (150, "out_of_service"),
    }
    for idx, (code, name, model, vol, noz, mats) in enumerate(PRINTERS):
        days_since, status = maint_state[code]
        last = today - timedelta(days=days_since)
        nxt = last + timedelta(days=90)
        notes = {"maintenance": "Cambio de hotend en curso (demo).", "out_of_service": "Falla de placa base, en espera de repuesto (demo)."}.get(status, "")
        eq = Equipment(code=code, name=name, model=model, type="printer_3d", status=status, build_volume=vol, nozzle_mm=noz,
                       supported_materials=mats, specs={"extrusor": "directo" if idx % 2 == 0 else "bowden", "cama_calefactada": True},
                       acquired_at=today - timedelta(days=400 + idx * 90), last_maintenance_at=last, next_maintenance_at=nxt,
                       notes=notes, is_demo=True)
        db.add(eq)
        printers.append(eq)
    for code, name, model in TOOLS:
        db.add(Equipment(code=code, name=name, model=model, type="tool", status="available", acquired_at=today - timedelta(days=700),
                         last_maintenance_at=today - timedelta(days=200), next_maintenance_at=today + timedelta(days=165), is_demo=True))
    db.flush()
    by_code = {p.code: p for p in printers}

    # ----- Planificación de trabajos históricos (sin solapes por impresora) -----
    next_free: dict[int, datetime] = {p.id: now - timedelta(days=30 * months + 1) for p in printers}
    out_of_service_since = now - timedelta(days=18)
    maint_since = now - timedelta(days=4)
    printer_w = {"DEMO-IMP-01": 22, "DEMO-IMP-02": 24, "DEMO-IMP-03": 16, "DEMO-IMP-04": 14, "DEMO-IMP-05": 12, "DEMO-IMP-06": 8}
    plans = []
    for req in _request_times(rng, now, months):
        code = _wchoice(rng, printer_w)
        p = by_code[code]
        if (code == "DEMO-IMP-06" and req > out_of_service_since) or (code == "DEMO-IMP-05" and req > maint_since):
            continue
        material = _wchoice(rng, {m: w for m, w in MATERIAL_W.items() if m in PRINTERS[printers.index(p)][5]})
        grams = max(8.0, min(380.0, rng.lognormvariate(3.8, 0.7)))
        est = int(max(15, min(14 * 60, grams * rng.uniform(2.4, 4.2))))
        start = max(req, next_free[p.id])
        loc = start + timedelta(hours=get_settings().local_utc_offset_hours)
        if loc.hour >= 21 or loc.hour < 7:
            nd = loc.date() + timedelta(days=1 if loc.hour >= 21 else 0)
            start = _local_to_utc(datetime(nd.year, nd.month, nd.day, 8, rng.randint(0, 30)))
        pf = 0.07 + (0.2 if code == PROBLEM_PRINTER else 0) + {"PETG": 0.04, "ABS": 0.07, "TPU": 0.05}.get(material, 0)
        roll = rng.random()
        status = "failed" if roll < pf else "cancelled" if roll < pf + 0.04 else "completed"
        frac = 1.0 if status == "completed" else rng.uniform(0.1, 0.9) if status == "failed" else rng.uniform(0.0, 0.5)
        dur = est * (rng.uniform(0.92, 1.15) if status == "completed" else frac * rng.uniform(0.95, 1.05))
        end = start + timedelta(minutes=dur)
        if end > now - timedelta(minutes=45) or (code == "DEMO-IMP-06" and end > out_of_service_since) or (code == "DEMO-IMP-05" and end > maint_since):
            continue
        next_free[p.id] = end + timedelta(minutes=rng.randint(5, 25))
        reason = None
        if status == "failed":
            w = {r: 1 for r in FAIL_REASONS_BASE}
            w.update({"user_error": 1.5, "power_outage": 0.4, "other": 0.6})
            if code == PROBLEM_PRINTER:
                w.update({"nozzle_clog": 9, "adhesion": 6})
            if material == "ABS":
                w["warping"] = 9
            if material == "PETG":
                w.update({"adhesion": 4, "filament_issue": 3})
            reason = _wchoice(rng, w)
        plans.append(dict(req=req, printer=p, material=material, grams=grams, est=est, start=start, end=end, status=status, frac=frac,
                          dur=dur, reason=reason, user=rng.choice(pool), name=f"{rng.choice(PROJECTS)} #{rng.randint(1, 99)}"))
    plans.sort(key=lambda x: x["end"])

    # ----- Filamentos: consumo cronológico, compras cuando falta material -----
    spools: dict[tuple[str, str], Filament] = {}
    all_spools: list[Filament] = []
    counter = [0]

    def new_spool(mat: str, color: str, when: datetime) -> Filament:
        counter[0] += 1
        old = spools.get((mat, color))
        if old:
            old.is_active = False  # se descarta el remanente de la bobina anterior
        f = Filament(code=f"DEMO-FIL-{counter[0]:03d}", material=mat, brand=BRANDS[mat], color=color, color_hex=COLORS[color],
                     initial_weight_g=1000, available_weight_g=0, low_stock_threshold_g=150, acquired_at=when.date(), is_demo=True,
                     created_at=when)
        db.add(f)
        db.flush()
        apply_movement(db, f, MovementType.stock_in, 1000, "Compra de bobina (demo)", when=when)
        spools[(mat, color)] = f
        all_spools.append(f)
        return f

    first = now - timedelta(days=30 * months + 2)
    for mat, cols in SLOTS.items():
        for c in cols:
            new_spool(mat, c, first)

    for pl in plans:
        cw = {c: COLOR_W[c] for c in SLOTS[pl["material"]]}
        color = _wchoice(rng, cw)
        sp = spools[(pl["material"], color)]
        used = round(pl["grams"] * pl["frac"], 1) if pl["status"] != "completed" else round(pl["grams"] * rng.uniform(0.97, 1.05), 1)
        if sp.available_weight_g < max(used, pl["grams"]):
            sp = new_spool(pl["material"], color, pl["start"] - timedelta(hours=rng.randint(2, 40)))
        job = PrintJob(user_id=pl["user"].id, project_name=pl["name"], printer_id=pl["printer"].id, filament_id=sp.id, status=pl["status"],
                       grams_estimated=round(pl["grams"], 1), grams_used=0, estimated_minutes=pl["est"],
                       progress_pct=round(pl["frac"] * 100, 1), failure_reason=pl["reason"], is_demo=True,
                       created_at=min(pl["req"], pl["start"]), queued_at=min(pl["req"], pl["start"]), started_at=pl["start"],
                       finished_at=pl["end"], duration_min=round(pl["dur"], 1))
        db.add(job)
        db.flush()
        if used > 0.5:
            job.grams_used = used
            apply_movement(db, sp, MovementType.stock_out, used, f"Trabajo #{job.id}: {job.project_name}", job_id=job.id, when=pl["end"], clamp=True)

    # Dos bobinas activas quedan con poco material para que las alertas de inventario tengan sentido
    for key, grams in ((("PLA", "Negro"), 130.0), (("PETG", "Azul"), 55.0)):
        sp = spools.get(key)
        if sp and sp.available_weight_g > grams:
            apply_movement(db, sp, MovementType.adjust, grams, "Conteo físico de remanente (demo)", when=now - timedelta(hours=3))

    # ----- Estado actual: en proceso, en cola y pendientes -----
    def pick_spool(mat: str, need: float):
        c = [f for (m, _), f in spools.items() if m == mat and f.is_active and f.available_weight_g >= need]
        return rng.choice(c) if c else None

    free = [p for p in printers if p.status == "available" and next_free[p.id] < now - timedelta(minutes=30)]
    rng.shuffle(free)
    printing_printers = []
    for p in free[:3]:
        mats = [m for m in PRINTERS[printers.index(p)][5] if m in ("PLA", "PETG")]
        mat = rng.choice(mats)
        grams = rng.uniform(30, 160)
        sp = pick_spool(mat, grams)
        if not sp:
            continue
        est = int(max(40, grams * rng.uniform(2, 3)))
        prog = rng.uniform(15, 80)
        started = now - timedelta(minutes=est * prog / 100)
        if started < next_free[p.id]:
            continue
        db.add(PrintJob(user_id=rng.choice(pool).id, project_name=f"{rng.choice(PROJECTS)} #{rng.randint(1, 99)}", printer_id=p.id,
                        filament_id=sp.id, status="printing", grams_estimated=round(grams, 1), estimated_minutes=est,
                        progress_pct=round(prog, 1), is_demo=True, created_at=started - timedelta(hours=1),
                        queued_at=started - timedelta(minutes=50), started_at=started))
        p.status = EquipmentStatus.busy.value
        printing_printers.append(p)
    queue_targets = (printing_printers + [p for p in free if p not in printing_printers])[:4] or free[:1]
    for i in range(4):
        if not queue_targets:
            break
        p = queue_targets[i % len(queue_targets)]
        mat = rng.choice([m for m in PRINTERS[printers.index(p)][5] if m in ("PLA", "PETG")])
        grams = rng.uniform(20, 140)
        sp = pick_spool(mat, grams)
        t = now - timedelta(minutes=rng.randint(10, 200))
        db.add(PrintJob(user_id=rng.choice(pool).id, project_name=f"{rng.choice(PROJECTS)} #{rng.randint(1, 99)}", printer_id=p.id,
                        filament_id=sp.id if sp else None, status="queued", grams_estimated=round(grams, 1),
                        estimated_minutes=int(max(30, grams * rng.uniform(2, 3))), is_demo=True, created_at=t, queued_at=t))
    for _ in range(2):
        grams = rng.uniform(15, 90)
        db.add(PrintJob(user_id=rng.choice(pool).id, project_name=f"{rng.choice(PROJECTS)} #{rng.randint(1, 99)}", status="pending",
                        grams_estimated=round(grams, 1), estimated_minutes=int(max(30, grams * 2.4)), is_demo=True,
                        created_at=now - timedelta(minutes=rng.randint(5, 90))))
    db.flush()

    # ----- Reservas -----
    res_taken: dict[int, list[tuple[datetime, datetime]]] = {p.id: [] for p in printers}
    n_res = 0
    operative = [p for p in printers if p.status != "out_of_service"]

    def add_res(day_offset: int, status: str):
        nonlocal n_res
        for _ in range(12):
            p = rng.choice(operative)
            d = (now + timedelta(days=day_offset)).date()
            s = _local_to_utc(datetime(d.year, d.month, d.day, rng.randint(8, 17), rng.choice([0, 30])))
            e = s + timedelta(minutes=rng.choice([60, 90, 120, 180]))
            if day_offset >= 0 and s <= now:
                continue
            if any(s < b and e > a for a, b in res_taken[p.id]):
                continue
            res_taken[p.id].append((s, e))
            db.add(Reservation(user_id=rng.choice(pool).id, printer_id=p.id, start_at=s, end_at=e, status=status,
                               purpose=rng.choice(["Práctica de laboratorio", "Proyecto final", "Prototipo", "Prueba de material"]),
                               is_demo=True, created_at=s - timedelta(days=rng.randint(1, 5))))
            n_res += 1
            return

    for _ in range(36):
        add_res(-rng.randint(1, 60), rng.choices(["completed", "cancelled", "rejected"], weights=[75, 15, 10])[0])
    for _ in range(6):
        add_res(rng.randint(1, 10), "approved")
    for _ in range(4):
        add_res(rng.randint(1, 12), "pending")

    # ----- Mantenimiento -----
    for p in printers:
        last = p.last_maintenance_at
        for k in range(3):
            d = last - timedelta(days=90 * k)
            db.add(MaintenanceRecord(equipment_id=p.id, type="preventive", status="done", performed_at=d, next_due_at=d + timedelta(days=90),
                                     description="Limpieza, lubricación de ejes y revisión de correas (demo)", cost=round(rng.uniform(15, 60), 2), is_demo=True))
    for desc in ("Reemplazo de boquilla obstruida", "Nivelación de cama y cambio de PEI", "Ajuste de correas y tensores"):
        d = today - timedelta(days=rng.randint(10, 120))
        db.add(MaintenanceRecord(equipment_id=by_code[PROBLEM_PRINTER].id, type="corrective", status="done", performed_at=d,
                                 description=desc + " (demo)", cost=round(rng.uniform(20, 90), 2), is_demo=True))
    db.add(MaintenanceRecord(equipment_id=by_code["DEMO-IMP-05"].id, type="corrective", status="in_progress",
                             description="Cambio de hotend (demo)", performed_at=today - timedelta(days=4), is_demo=True))
    db.add(MaintenanceRecord(equipment_id=by_code["DEMO-IMP-06"].id, type="corrective", status="scheduled",
                             description="Reemplazo de placa base cuando llegue el repuesto (demo)", scheduled_for=today + timedelta(days=12), is_demo=True))

    for p in printers:
        jobsvc.refresh_printer(db, p)
    db.commit()
    return {"jobs": db.scalar(select(func.count()).select_from(PrintJob).where(PrintJob.is_demo.is_(True))), "printers": len(printers), "spools": len(all_spools), "reservations": n_res}


# ---------- Reasignación de historial simulado a clientes reales ----------
def ensure_demo_for_user(db: Session, user: User) -> None:
    """Un cliente real que entra en modo simulador ve actividad simulada propia (reasignando trabajos demo)."""
    if user.is_demo or user.role != Role.client.value:
        return
    if db.scalar(select(PrintJob.id).where(PrintJob.user_id == user.id, PrintJob.is_demo.is_(True)).limit(1)):
        return
    rng = random.Random(user.id)
    hist = list(db.scalars(select(PrintJob).where(PrintJob.is_demo.is_(True), PrintJob.status.in_(["completed", "failed"]),
                                                  PrintJob.user.has(User.is_demo.is_(True))).order_by(PrintJob.finished_at.desc()).limit(120)))
    for j in rng.sample(hist, min(7, len(hist))):
        j.user_id = user.id
    live = list(db.scalars(select(PrintJob).where(PrintJob.is_demo.is_(True), PrintJob.status.in_(["queued", "pending"]))))
    for j in live[:1]:
        j.user_id = user.id
    res = list(db.scalars(select(Reservation).where(Reservation.is_demo.is_(True), Reservation.start_at > utcnow()).limit(3)))
    for r in res[:1]:
        r.user_id = user.id
    db.commit()


# ---------- Simulación en vivo ----------
def tick(db: Session) -> list[str]:
    """Avanza los trabajos demo en proceso. Devuelve mensajes de eventos para notificar por WebSocket."""
    s = get_settings()
    rng = random.Random()
    events: list[str] = []
    now = utcnow()
    running = list(db.scalars(select(PrintJob).where(PrintJob.is_demo.is_(True), PrintJob.status == JobStatus.printing.value)))
    step_min = s.sim_tick_seconds / 60 * s.sim_speed  # minutos simulados por tick
    for j in running:
        j.progress_pct = min(100.0, round(j.progress_pct + step_min / max(1, j.estimated_minutes) * 100, 2))
        code = j.printer.code if j.printer else ""
        fail_p = 0.0007 * (2.5 if code == PROBLEM_PRINTER else 1.0)
        if j.progress_pct >= 100:
            j.started_at = now - timedelta(minutes=j.estimated_minutes * rng.uniform(0.95, 1.1))
            jobsvc.transition(db, j, "complete", now=now)
            events.append(f"Trabajo completado: {j.project_name}")
            jobsvc.start_next_in_queue(db, j.printer_id, now)
        elif rng.random() < fail_p and j.progress_pct > 8:
            j.started_at = now - timedelta(minutes=j.estimated_minutes * j.progress_pct / 100)
            reason = rng.choice(["nozzle_clog", "adhesion"] if code == PROBLEM_PRINTER else FAIL_REASONS_BASE)
            jobsvc.transition(db, j, "fail", failure_reason=reason, now=now)
            events.append(f"Impresión fallida: {j.project_name}")
            jobsvc.start_next_in_queue(db, j.printer_id, now)
    # Arranca trabajos en cola en impresoras libres
    for p in db.scalars(select(Equipment).where(Equipment.is_demo.is_(True), Equipment.status == "available", Equipment.type == "printer_3d")):
        started = jobsvc.start_next_in_queue(db, p.id, now)
        if started:
            events.append(f"Inicia impresión: {started.project_name}")
    # Entra trabajo nuevo de vez en cuando para mantener viva la cola
    active = db.scalars(select(PrintJob.id).where(PrintJob.is_demo.is_(True), PrintJob.status.in_(["queued", "pending"]))).all()
    if len(active) < 5 and rng.random() < 0.07:
        users = list(db.scalars(select(User).where(User.is_demo.is_(True))))
        ps = list(db.scalars(select(Equipment).where(Equipment.is_demo.is_(True), Equipment.type == "printer_3d",
                                                     Equipment.status.in_(["available", "busy"]))))
        if users and ps:
            p = rng.choice(ps)
            mats = [m for m in p.supported_materials if m in ("PLA", "PETG")]
            fil = list(db.scalars(select(Filament).where(Filament.is_demo.is_(True), Filament.is_active.is_(True),
                                                         Filament.material.in_(mats), Filament.available_weight_g > 200)))
            if fil:
                g = rng.uniform(20, 120)
                db.add(PrintJob(user_id=rng.choice(users).id, project_name=f"{rng.choice(PROJECTS)} #{rng.randint(1, 99)}", printer_id=p.id,
                                filament_id=rng.choice(fil).id, status="queued", grams_estimated=round(g, 1),
                                estimated_minutes=int(max(30, g * 2.4)), is_demo=True, created_at=now, queued_at=now))
                events.append("Nuevo trabajo en cola")
    db.commit()
    return events
