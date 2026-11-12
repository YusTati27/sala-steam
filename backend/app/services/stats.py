"""Analítica de la sala: KPIs, series, comparación con el período anterior e insights automáticos.

Todo se calcula a partir de los trabajos reales de la base de datos (según el modo actual: demo o real).
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.timeutil import utcnow
from app.models.entities import Equipment, EquipmentType, Filament, JobStatus, PrintJob
from app.services import app_settings
from app.services.alerts import build_alerts

MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
REASONS = {
    "adhesion": "Mala adhesión a la cama",
    "nozzle_clog": "Obstrucción de boquilla",
    "filament_issue": "Problema de filamento",
    "warping": "Deformación (warping)",
    "power_outage": "Corte de energía",
    "user_error": "Error de diseño/usuario",
    "other": "Otro",
}
DONE = (JobStatus.completed.value, JobStatus.failed.value)


def local(dt: datetime) -> datetime:
    return dt + timedelta(hours=get_settings().local_utc_offset_hours)


def ref_time(j: PrintJob) -> datetime:
    return j.started_at or j.created_at


def pct(a: float, b: float) -> float | None:
    return round(100 * a / b, 1) if b else None


def delta(cur, prev):
    if cur is None or prev is None:
        return None
    return round(cur - prev, 1)


# ---------- Consulta ----------
def fetch_jobs(db: Session, demo: bool, dfrom: date, dto: date, printer_id=None, material=None, status=None) -> list[PrintJob]:
    t = func.coalesce(PrintJob.started_at, PrintJob.created_at)
    start = datetime.combine(dfrom, datetime.min.time()) - timedelta(hours=get_settings().local_utc_offset_hours)
    end = datetime.combine(dto + timedelta(days=1), datetime.min.time()) - timedelta(hours=get_settings().local_utc_offset_hours)
    q = (
        select(PrintJob)
        .options(joinedload(PrintJob.filament), joinedload(PrintJob.printer), joinedload(PrintJob.user))
        .where(PrintJob.is_demo == demo, t >= start, t < end)
    )
    if printer_id:
        q = q.where(PrintJob.printer_id == printer_id)
    if status:
        q = q.where(PrintJob.status == status)
    if material:
        q = q.join(Filament, PrintJob.filament_id == Filament.id).where(Filament.material == material.upper())
    return list(db.scalars(q).unique())


# ---------- KPIs ----------
def compute_kpis(jobs: list[PrintJob]) -> dict:
    c = Counter(j.status for j in jobs)
    completed, failed, cancelled = c[JobStatus.completed.value], c[JobStatus.failed.value], c[JobStatus.cancelled.value]
    active = c[JobStatus.pending.value] + c[JobStatus.queued.value] + c[JobStatus.printing.value]
    grams_total = sum(j.grams_used for j in jobs)
    wasted = sum(j.grams_used for j in jobs if j.status in (JobStatus.failed.value, JobStatus.cancelled.value))
    done = [j for j in jobs if j.status in DONE and j.duration_min]
    hours = sum(j.duration_min for j in done) / 60
    comp_durs = [j.duration_min for j in jobs if j.status == JobStatus.completed.value and j.duration_min]
    comp_grams = [j.grams_used for j in jobs if j.status == JobStatus.completed.value and j.grams_used]
    closed = completed + failed + cancelled
    return {
        "total_jobs": len(jobs),
        "completed": completed,
        "failed": failed,
        "cancelled": cancelled,
        "active": active,
        "success_rate": pct(completed, completed + failed),  # de lo que se llegó a imprimir
        "completion_rate": pct(completed, closed),  # de todo lo que se cerró
        "grams_total": round(grams_total, 0),
        "grams_wasted": round(wasted, 0),
        "waste_pct": pct(wasted, grams_total),
        "print_hours": round(hours, 1),
        "avg_duration_min": round(sum(comp_durs) / len(comp_durs), 0) if comp_durs else None,
        "avg_grams": round(sum(comp_grams) / len(comp_grams), 0) if comp_grams else None,
    }


# ---------- Series ----------
def granularity_for(days: int) -> str:
    return "day" if days <= 31 else "week" if days <= 120 else "month"


def bucket_key(dt: datetime, gran: str) -> str:
    d = local(dt).date()
    if gran == "month":
        return f"{d.year}-{d.month:02d}"
    if gran == "week":
        return (d - timedelta(days=d.weekday())).isoformat()
    return d.isoformat()


def bucket_label(key: str, gran: str) -> str:
    if gran == "month":
        y, m = key.split("-")
        return f"{MONTHS[int(m) - 1]} {y[2:]}"
    d = date.fromisoformat(key)
    return f"{d.day:02d}/{d.month:02d}" if gran == "day" else f"Sem {d.day:02d}/{d.month:02d}"


def all_buckets(dfrom: date, dto: date, gran: str) -> list[str]:
    keys, d = [], dfrom
    while d <= dto:
        k = bucket_key(datetime.combine(d, datetime.min.time()) - timedelta(hours=get_settings().local_utc_offset_hours) + timedelta(hours=12), gran)
        if not keys or keys[-1] != k:
            keys.append(k)
        d += timedelta(days=1)
    return keys


def jobs_series(jobs, buckets, gran):
    data = {k: Counter() for k in buckets}
    for j in jobs:
        k = bucket_key(ref_time(j), gran)
        if k in data:
            data[k][j.status] += 1
    out = []
    for k in buckets:
        c = data[k]
        active = c["pending"] + c["queued"] + c["printing"]
        out.append(
            {
                "period": k, "label": bucket_label(k, gran),
                "completed": c["completed"], "failed": c["failed"], "cancelled": c["cancelled"], "active": active,
                "total": sum(c.values()), "success_rate": pct(c["completed"], c["completed"] + c["failed"]),
            }
        )
    return out


def consumption_series(jobs, buckets, gran):
    mats = sorted({j.filament.material for j in jobs if j.filament and j.grams_used})
    data = {k: defaultdict(float) for k in buckets}
    for j in jobs:
        if not j.grams_used or not j.filament:
            continue
        k = bucket_key(ref_time(j), gran)
        if k in data:
            data[k][j.filament.material] += j.grams_used
            if j.status in (JobStatus.failed.value, JobStatus.cancelled.value):
                data[k]["_wasted"] += j.grams_used
    rows = []
    for k in buckets:
        row = {"period": k, "label": bucket_label(k, gran), "total_g": round(sum(v for m, v in data[k].items() if m != "_wasted")),
               "wasted_g": round(data[k]["_wasted"])}
        for m in mats:
            row[m] = round(data[k][m])
        rows.append(row)
    return mats, rows


def printer_stats(jobs, printers, days, open_hours):
    by = defaultdict(list)
    for j in jobs:
        if j.printer_id:
            by[j.printer_id].append(j)
    out = []
    avail_hours = max(1.0, days * open_hours)
    for p in printers:
        js = by.get(p.id, [])
        k = compute_kpis(js)
        out.append(
            {
                "printer_id": p.id, "name": p.name, "status": p.status, "jobs": len(js), "completed": k["completed"], "failed": k["failed"],
                "hours": k["print_hours"], "utilization_pct": min(100.0, round(100 * k["print_hours"] / avail_hours, 1)),
                "success_rate": k["success_rate"], "grams": k["grams_total"], "avg_duration_min": k["avg_duration_min"],
            }
        )
    out.sort(key=lambda r: r["hours"], reverse=True)
    return out


def material_stats(jobs):
    by = defaultdict(list)
    for j in jobs:
        if j.filament and j.grams_used:
            by[j.filament.material].append(j)
    total = sum(j.grams_used for js in by.values() for j in js) or 1
    rows = []
    for m, js in by.items():
        k = compute_kpis(js)
        g = sum(j.grams_used for j in js)
        rows.append({"material": m, "grams": round(g), "jobs": len(js), "share_pct": round(100 * g / total, 1),
                     "success_rate": k["success_rate"], "failed": k["failed"], "waste_pct": k["waste_pct"]})
    rows.sort(key=lambda r: r["grams"], reverse=True)
    return rows


def color_stats(jobs, top=10):
    by = defaultdict(lambda: {"grams": 0.0, "jobs": 0, "hex": "#888888"})
    for j in jobs:
        if j.filament and j.grams_used:
            r = by[j.filament.color]
            r["grams"] += j.grams_used
            r["jobs"] += 1
            r["hex"] = j.filament.color_hex
    total = sum(r["grams"] for r in by.values()) or 1
    rows = [{"color": c, "hex": r["hex"], "grams": round(r["grams"]), "jobs": r["jobs"], "share_pct": round(100 * r["grams"] / total, 1)}
            for c, r in by.items()]
    rows.sort(key=lambda r: r["grams"], reverse=True)
    return rows[:top]


def heatmap(jobs):
    cnt = Counter()
    for j in jobs:
        if j.status == JobStatus.pending.value:
            continue
        d = local(ref_time(j))
        cnt[(d.weekday(), d.hour)] += 1
    return [{"weekday": w, "hour": h, "jobs": n} for (w, h), n in sorted(cnt.items())]


def daily_demand(jobs):
    """Trabajos iniciados por fecha local (para el calendario de demanda)."""
    cnt = Counter()
    for j in jobs:
        if j.status != JobStatus.pending.value:
            cnt[local(ref_time(j)).date().isoformat()] += 1
    return [{"date": d, "jobs": n} for d, n in sorted(cnt.items())]


def stock_forecast(db: Session, demo: bool) -> list[dict]:
    since = utcnow() - timedelta(days=60)
    jobs = list(db.scalars(
        select(PrintJob).options(joinedload(PrintJob.filament)).where(
            PrintJob.is_demo == demo, PrintJob.status.in_(DONE), PrintJob.started_at >= since)
    ).unique())
    first = min((j.started_at for j in jobs), default=None)
    span = max(7, min(60, (utcnow() - first).days + 1)) if first else 60
    used = defaultdict(float)
    for j in jobs:
        if j.filament:
            used[j.filament.material] += j.grams_used
    avail = defaultdict(float)
    for f in db.scalars(select(Filament).where(Filament.is_demo == demo, Filament.is_active.is_(True))):
        avail[f.material] += f.available_weight_g
    rows = []
    for m in sorted(set(avail) | set(used)):
        daily = used[m] / span
        rows.append({"material": m, "available_g": round(avail[m]), "daily_g": round(daily, 1),
                     "days_left": round(avail[m] / daily) if daily > 0 else None})
    rows.sort(key=lambda r: (r["days_left"] is None, r["days_left"] or 0))
    return rows


# ---------- Insights ----------
def build_insights(kpi, prev, printers, materials, failure_reasons, heat, forecast, series, alerts, comparing_prev) -> list[dict]:
    ins: list[dict] = []

    def add(level, title, detail, action=""):
        ins.append({"level": level, "title": title, "detail": detail, "action": action})

    if kpi["total_jobs"] == 0:
        add("info", "Sin datos en el período", "No hay trabajos con los filtros seleccionados.", "Amplíe el rango de fechas o quite filtros.")
        return ins

    sr = kpi["success_rate"]
    if sr is not None:
        d = delta(sr, prev["success_rate"]) if comparing_prev else None
        trend = "" if d is None else (f" ({'+' if d >= 0 else ''}{d} pts vs. el período anterior)")
        level = "positive" if sr >= 90 else "warning" if sr >= 75 else "critical"
        add(level, f"Tasa de éxito de impresión: {sr}%{trend}",
            f"{kpi['completed']} completadas y {kpi['failed']} fallidas. Se pierden {kpi['grams_wasted']:.0f} g de filamento ({kpi['waste_pct']}% del consumo) en impresiones fallidas o canceladas.",
            "Meta sugerida: ≥ 90 %." if sr < 90 else "Mantener los controles actuales.")

    # Impresoras con tasa de fallo anómala
    for p in printers:
        if p["jobs"] >= 8 and p["success_rate"] is not None and sr is not None:
            fail = 100 - p["success_rate"]
            glob = 100 - sr
            if fail >= max(15, 1.6 * glob):
                add("critical" if fail >= 25 else "warning", f"{p['name']} concentra fallos: {fail:.0f}% de impresiones fallidas",
                    f"El promedio de la sala es {glob:.0f}%. Con {p['jobs']} trabajos en el período, es la causa principal de pérdida de material.",
                    "Programar mantenimiento correctivo (nivelación, boquilla, correas) y revisar sus trabajos recientes.")
    # Carga desbalanceada
    ranked = [p for p in printers if p["jobs"] > 0 and p.get("status") in ("available", "busy")]
    if len(ranked) >= 3:
        top, low = ranked[0], ranked[-1]
        if top["utilization_pct"] >= 70:
            add("warning", f"{top['name']} está muy cargada ({top['utilization_pct']:.0f}% de utilización)",
                f"La menos usada es {low['name']} con {low['utilization_pct']:.0f}%.", "Redistribuir trabajos o abrir más franjas de reserva en las impresoras con baja carga.")
        elif low["utilization_pct"] < 10 and top["utilization_pct"] > 3 * max(low["utilization_pct"], 1):
            add("info", f"{low['name']} casi no se usa ({low['utilization_pct']:.0f}%)",
                "Puede deberse a que está fuera de servicio, es un modelo menos práctico o no se ofrece a los usuarios.", "Verificar su estado o promoverla en la cola.")

    # Materiales
    if materials:
        top = materials[0]
        if top["share_pct"] >= 55:
            add("info", f"{top['material']} representa el {top['share_pct']}% del consumo", f"{top['grams']} g en {top['jobs']} trabajos.",
                f"Mantener stock holgado de {top['material']} (los colores más usados primero).")
        for m in materials:
            if m["jobs"] >= 8 and m["success_rate"] is not None and sr is not None and (100 - m["success_rate"]) >= max(15, 1.5 * (100 - sr)):
                add("warning", f"{m['material']} falla más que el resto ({100 - m['success_rate']:.0f}% de fallos)",
                    f"Con {m['jobs']} trabajos; el promedio general es {100 - sr:.0f}%.", "Revisar perfiles de temperatura, secado del filamento y adhesión para este material.")

    # Causas de fallo
    if failure_reasons and failure_reasons[0]["count"] >= 3:
        r = failure_reasons[0]
        add("info", f"Causa principal de fallos: {r['label'].lower()} ({r['pct']:.0f}%)", f"{r['count']} de {sum(x['count'] for x in failure_reasons)} fallos con causa registrada.",
            "Capacitar a los usuarios y ajustar el procedimiento de preparación correspondiente.")

    # Inventario
    for f in forecast:
        if f["days_left"] is not None and f["days_left"] <= 14:
            add("critical" if f["days_left"] <= 7 else "warning", f"Stock de {f['material']} alcanza para ~{f['days_left']} días",
                f"Quedan {f['available_g']} g y el consumo es ~{f['daily_g']} g/día (últimos 60 días).", "Reabastecer antes de que se agote.")
    low = [a for a in alerts if a["type"] == "low_stock"]
    if low:
        add("warning", f"{len(low)} bobina(s) con inventario bajo o agotado", "; ".join(a["title"].split(": ")[1] for a in low[:5]), "Registrar entradas o comprar reposición.")

    # Demanda
    if heat:
        by_day = Counter()
        by_block = Counter()
        for h in heat:
            by_day[h["weekday"]] += h["jobs"]
            by_block[(h["weekday"], h["hour"] // 2 * 2)] += h["jobs"]
        (wd, blk), n = by_block.most_common(1)[0]
        day, nday = by_day.most_common(1)[0]
        share = round(100 * nday / sum(by_day.values()))
        add("info", f"Pico de demanda: {WEEKDAYS[wd]} {blk:02d}:00–{blk + 2:02d}:00", f"{WEEKDAYS[day]} concentra el {share}% de los trabajos; el bloque más cargado tiene {n}.",
            "Reforzar la atención en esas horas y ofrecer reservas en franjas de baja demanda.")

    # Tendencia mensual / por período
    vals = [s["total_g"] for s in series if s["total_g"] > 0]
    if len(series) >= 3 and len(vals) >= 3:
        last, before = series[-2]["total_g"], series[-3]["total_g"]  # último período completo vs anterior
        if before > 0 and abs(last - before) / before >= 0.25:
            up = last > before
            add("info", f"Consumo {'al alza' if up else 'a la baja'}: {'+' if up else ''}{round(100 * (last - before) / before)}% en {series[-2]['label']}",
                f"{last} g frente a {before} g en {series[-3]['label']}.", "Ajustar compras según la tendencia." if up else "Verificar si hubo menor disponibilidad de equipos.")

    # Comparación con período anterior
    if comparing_prev and prev["total_jobs"]:
        dj = round(100 * (kpi["total_jobs"] - prev["total_jobs"]) / prev["total_jobs"])
        add("positive" if dj >= 0 else "info", f"Volumen de trabajos {'+' if dj >= 0 else ''}{dj}% vs. período anterior",
            f"{kpi['total_jobs']} frente a {prev['total_jobs']} trabajos.")

    mc = len([a for a in alerts if a["type"] in ("maintenance_overdue", "maintenance_soon")])
    if mc:
        add("warning", f"{mc} equipo(s) con mantenimiento vencido o próximo", "", "Revise la sección Mantenimiento.")

    order = {"critical": 0, "warning": 1, "info": 2, "positive": 3}
    ins.sort(key=lambda i: order[i["level"]])
    return ins


# ---------- Orquestación ----------
def overview(db: Session, demo: bool, dfrom: date, dto: date, printer_id=None, material=None, status=None) -> dict:
    days = (dto - dfrom).days + 1
    gran = granularity_for(days)
    jobs = fetch_jobs(db, demo, dfrom, dto, printer_id, material, status)
    prev_to = dfrom - timedelta(days=1)
    prev_from = prev_to - timedelta(days=days - 1)
    prev_jobs = fetch_jobs(db, demo, prev_from, prev_to, printer_id, material, status)

    kpi, prev = compute_kpis(jobs), compute_kpis(prev_jobs)
    buckets = all_buckets(dfrom, dto, gran)
    mats, cons = consumption_series(jobs, buckets, gran)
    printers = list(db.scalars(select(Equipment).where(Equipment.is_demo == demo, Equipment.type == EquipmentType.printer_3d.value)))
    if printer_id:
        printers = [p for p in printers if p.id == printer_id]
    pstats = printer_stats(jobs, printers, days, app_settings.open_hours(db))
    mstats = material_stats(jobs)
    reasons = Counter(j.failure_reason or "other" for j in jobs if j.status == JobStatus.failed.value)
    rtotal = sum(reasons.values()) or 1
    freasons = [{"reason": r, "label": REASONS.get(r, r), "count": n, "pct": round(100 * n / rtotal, 1)} for r, n in reasons.most_common()]
    heat = heatmap(jobs)
    forecast = stock_forecast(db, demo)
    series = jobs_series(jobs, buckets, gran)
    alerts = build_alerts(db, demo)
    users = defaultdict(lambda: [0, 0.0])
    for j in jobs:
        users[j.user.name][0] += 1
        users[j.user.name][1] += j.grams_used
    top_users = [{"name": n, "jobs": v[0], "grams": round(v[1])} for n, v in sorted(users.items(), key=lambda kv: -kv[1][0])[:5]]

    comparing_prev = prev["total_jobs"] >= 10  # con menos datos la comparación sería engañosa
    compare = {
        k: {"current": kpi[k], "previous": prev[k], "delta": delta(kpi[k], prev[k]),
            "delta_pct": pct(kpi[k] - prev[k], prev[k]) if kpi[k] is not None and prev[k] else None}
        for k in ("total_jobs", "completed", "failed", "success_rate", "grams_total", "print_hours")
    } if comparing_prev else None

    return {
        "demo": demo,
        "period": {"from": dfrom.isoformat(), "to": dto.isoformat(), "days": days, "granularity": gran,
                   "previous_from": prev_from.isoformat(), "previous_to": prev_to.isoformat()},
        "assumptions": {"open_hours_per_day": app_settings.open_hours(db),
                        "utilization": "horas de impresión ÷ (días del período × horas operativas por día)",
                        "success_rate": "completadas ÷ (completadas + fallidas)",
                        "completion_rate": "completadas ÷ (completadas + fallidas + canceladas)"},
        "kpis": kpi,
        "comparison": compare,
        "status_distribution": [{"status": s, "count": n} for s, n in Counter(j.status for j in jobs).most_common()],
        "jobs_by_period": series,
        "consumption_by_period": {"materials": mats, "rows": cons},
        "printers": pstats,
        "materials": mstats,
        "colors": color_stats(jobs),
        "failure_reasons": freasons,
        "demand_heatmap": heat,
        "demand_by_day": daily_demand(jobs),
        "stock_forecast": forecast,
        "top_users": top_users,
        "insights": build_insights(kpi, prev, pstats, mstats, freasons, heat, forecast, cons, alerts, comparing_prev),
        "generated_at": utcnow().isoformat() + "Z",
    }


def jobs_csv_rows(jobs: list[PrintJob]):
    yield ["id", "proyecto", "usuario", "impresora", "material", "color", "estado", "g_estimados", "g_usados", "minutos_estimados",
           "duracion_min", "progreso_pct", "causa_fallo", "inicio_local", "fin_local", "es_demo"]
    fmt = lambda d: local(d).strftime("%Y-%m-%d %H:%M") if d else ""  # noqa: E731
    for j in sorted(jobs, key=ref_time):
        yield [j.id, j.project_name, j.user.name, j.printer.name if j.printer else "", j.filament.material if j.filament else "",
               j.filament.color if j.filament else "", j.status, j.grams_estimated, j.grams_used, j.estimated_minutes,
               j.duration_min or "", j.progress_pct, REASONS.get(j.failure_reason or "", ""), fmt(j.started_at), fmt(j.finished_at),
               "SI" if j.is_demo else "NO"]
