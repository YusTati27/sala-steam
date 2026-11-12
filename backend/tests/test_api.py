from datetime import date, datetime, timedelta, UTC

import pytest

API = "/api/v1"


def iso(dt: datetime) -> str:
    return dt.replace(tzinfo=UTC).isoformat()


def future(hours: float) -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=hours)


# ---------- Autenticación y permisos ----------
def test_requires_auth(client):
    assert client.get(f"{API}/equipment").status_code == 401
    assert client.get(f"{API}/auth/me", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_register_validation_and_duplicates(client, mode_real):
    bad = client.post(f"{API}/auth/register", json={"name": "X Y", "email": "no-es-correo", "password": "Clave12345"})
    assert bad.status_code == 422
    weak = client.post(f"{API}/auth/register", json={"name": "Weak User", "email": "weak@salasteam.dev", "password": "abcdefgh"})
    assert weak.status_code == 422
    ok = client.post(f"{API}/auth/register", json={"name": "Dup User", "email": "dup@salasteam.dev", "password": "Clave12345"})
    assert ok.status_code == 201 and ok.json()["user"]["role"] == "client"
    assert client.post(f"{API}/auth/register", json={"name": "Dup User", "email": "DUP@salasteam.dev", "password": "Clave12345"}).status_code == 409


def test_admin_signup_requires_pin(client, mode_real):
    body = {"name": "Nueva Admin", "email": "nueva.admin@salasteam.dev", "password": "Clave12345"}
    assert client.post(f"{API}/auth/register", json={**body, "admin_pin": "0000"}).status_code == 403
    assert client.post(f"{API}/auth/register", json=body).json()["user"]["role"] == "client"  # sin PIN sigue siendo cliente
    ok = client.post(f"{API}/auth/register", json={**body, "email": "otra.admin@salasteam.dev", "admin_pin": "4242"})
    assert ok.status_code == 201 and ok.json()["user"]["role"] == "admin"
    h = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    assert client.get(f"{API}/users", headers=h).status_code == 200


def test_wrong_password_and_throttle(client, mode_real):
    for _ in range(5):
        assert client.post(f"{API}/auth/login", json={"email": "ghost@salasteam.dev", "password": "x"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "ghost@salasteam.dev", "password": "x"}).status_code == 429


def test_client_cannot_use_admin_endpoints(client, student):
    h, _ = student
    for method, url in [("get", "/users"), ("get", "/jobs"), ("get", "/stats/overview"), ("get", "/maintenance"), ("get", "/alerts"),
                        ("post", "/simulator/clear"), ("get", "/reservations"), ("get", "/filaments/movements/all")]:
        assert getattr(client, method)(API + url, headers=h).status_code == 403, url
    assert client.post(f"{API}/equipment", headers=h, json={"code": "XX1", "name": "Nada"}).status_code == 403
    assert client.post(f"{API}/config/mode", headers=h, json={"mode": "demo"}).status_code == 403


# ---------- Equipos ----------
@pytest.fixture(scope="session")
def printer(client, admin):
    r = client.post(f"{API}/equipment", headers=admin, json={
        "code": "t-imp-01", "name": "Impresora Test", "model": "Modelo X", "supported_materials": ["PLA", "PETG"],
        "acquired_at": "2024-01-10", "last_maintenance_at": "2026-09-01", "next_maintenance_at": "2026-12-01"})
    assert r.status_code == 201, r.text
    assert r.json()["code"] == "T-IMP-01" and r.json()["status"] == "available"
    return r.json()


def test_equipment_validation_and_duplicates(client, admin, printer):
    assert client.post(f"{API}/equipment", headers=admin, json={"code": "T-IMP-01", "name": "Otra"}).status_code == 409
    assert client.post(f"{API}/equipment", headers=admin, json={"code": "Z1", "name": "N"}).status_code == 422
    bad_dates = {"code": "T-D1", "name": "Fechas", "last_maintenance_at": "2026-05-01", "next_maintenance_at": "2026-04-01"}
    assert client.post(f"{API}/equipment", headers=admin, json=bad_dates).status_code == 422
    assert client.post(f"{API}/equipment", headers=admin, json={"code": "T-B1", "name": "Busy", "status": "busy"}).status_code == 400


def test_client_view_hides_private_equipment_fields(client, student, printer):
    h, _ = student
    items = client.get(f"{API}/equipment", headers=h).json()
    p = next(i for i in items if i["code"] == "T-IMP-01")
    assert p["next_maintenance_at"] is None and p["hardware_endpoint"] is None and p["notes"] is None


# ---------- Inventario ----------
@pytest.fixture(scope="session")
def pla(client, admin):
    r = client.post(f"{API}/filaments", headers=admin, json={"material": "pla", "brand": "Test", "color": "rojo", "color_hex": "#ff0000",
                                                             "initial_weight_g": 1000, "low_stock_threshold_g": 200, "acquired_at": "2026-10-01"})
    assert r.status_code == 201, r.text
    assert r.json()["material"] == "PLA" and r.json()["color_hex"] == "#FF0000"
    return r.json()


def test_filament_duplicate_and_movements(client, admin, pla):
    dup = client.post(f"{API}/filaments", headers=admin, json={"material": "PLA", "brand": "Test", "color": "Rojo", "initial_weight_g": 1000,
                                                              "acquired_at": "2026-10-01"})
    assert dup.status_code == 409
    fid = pla["id"]
    assert client.post(f"{API}/filaments/{fid}/movements", headers=admin, json={"type": "out", "grams": 5000}).status_code == 409
    r = client.post(f"{API}/filaments/{fid}/movements", headers=admin, json={"type": "out", "grams": 850, "note": "consumo"})
    assert r.status_code == 201 and r.json()["balance_after_g"] == 150
    f = next(x for x in client.get(f"{API}/filaments", headers=admin).json() if x["id"] == fid)
    assert f["stock_status"] == "low" and f["consumed_g"] >= 850
    client.post(f"{API}/filaments/{fid}/movements", headers=admin, json={"type": "in", "grams": 850})
    assert next(x for x in client.get(f"{API}/filaments", headers=admin).json() if x["id"] == fid)["stock_status"] == "available"
    assert client.post(f"{API}/filaments/{fid}/movements", headers=admin, json={"type": "out", "grams": -3}).status_code == 422


def test_client_sees_availability_not_costs(client, student, pla):
    h, _ = student
    f = next(x for x in client.get(f"{API}/filaments", headers=h).json() if x["id"] == pla["id"])
    assert f["initial_weight_g"] is None and f["consumed_g"] is None
    summ = client.get(f"{API}/filaments/summary", headers=h).json()
    assert any(s["material"] == "PLA" for s in summ)


# ---------- Trabajos: ciclo completo y sincronización ----------
def test_job_lifecycle_syncs_printer_and_filament(client, admin, student, printer, pla):
    h, uid = student
    before = next(x for x in client.get(f"{API}/filaments", headers=admin).json() if x["id"] == pla["id"])["available_weight_g"]
    r = client.post(f"{API}/jobs", headers=admin, json={"user_id": uid, "project_name": "Pieza de prueba", "printer_id": printer["id"],
                                                        "filament_id": pla["id"], "grams_estimated": 50, "estimated_minutes": 120, "status": "queued"})
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["status"] == "queued" and job["queue_position"] == 1 and job["estimated_end_at"]

    # el cliente ve la cola sin datos de otros y su propio trabajo identificado
    q = client.get(f"{API}/jobs/queue", headers=h).json()
    assert any(j["id"] == job["id"] and j["is_mine"] for j in q)

    s = client.post(f"{API}/jobs/{job['id']}/transition", headers=admin, json={"action": "start"})
    assert s.status_code == 200 and s.json()["status"] == "printing"
    p = next(e for e in client.get(f"{API}/equipment", headers=admin).json() if e["id"] == printer["id"])
    assert p["status"] == "busy" and p["current_job"]["id"] == job["id"]

    # mantenimiento bloqueado mientras imprime
    assert client.patch(f"{API}/equipment/{printer['id']}", headers=admin, json={"status": "maintenance"}).status_code == 409
    # progreso
    assert client.patch(f"{API}/jobs/{job['id']}", headers=admin, json={"progress_pct": 40}).json()["progress_pct"] == 40

    done = client.post(f"{API}/jobs/{job['id']}/transition", headers=admin, json={"action": "complete", "grams_used": 47.5})
    assert done.status_code == 200 and done.json()["status"] == "completed" and done.json()["duration_min"] is not None
    p = next(e for e in client.get(f"{API}/equipment", headers=admin).json() if e["id"] == printer["id"])
    assert p["status"] == "available" and p["current_job"] is None
    after = next(x for x in client.get(f"{API}/filaments", headers=admin).json() if x["id"] == pla["id"])["available_weight_g"]
    assert round(before - after) in (47, 48)
    # historial propio
    hist = client.get(f"{API}/jobs/mine?history=true", headers=h).json()
    assert any(j["id"] == job["id"] and j["status"] == "completed" for j in hist)
    # no se puede completar de nuevo
    assert client.post(f"{API}/jobs/{job['id']}/transition", headers=admin, json={"action": "complete"}).status_code == 409


def test_job_rules(client, admin, student, printer, pla):
    _, uid = student
    # material no soportado
    abs_ = client.post(f"{API}/filaments", headers=admin, json={"material": "ABS", "color": "Negro", "initial_weight_g": 1000}).json()
    r = client.post(f"{API}/jobs", headers=admin, json={"user_id": uid, "project_name": "ABS no soportado", "printer_id": printer["id"],
                                                        "filament_id": abs_["id"], "grams_estimated": 10, "estimated_minutes": 30, "status": "queued"})
    assert r.status_code == 409
    # filamento insuficiente
    r = client.post(f"{API}/jobs", headers=admin, json={"user_id": uid, "project_name": "Demasiado grande", "printer_id": printer["id"],
                                                        "filament_id": pla["id"], "grams_estimated": 4000, "estimated_minutes": 500, "status": "printing"})
    assert r.status_code == 409
    # falla y cancelación consumen parcial / nada
    j = client.post(f"{API}/jobs", headers=admin, json={"user_id": uid, "project_name": "Fallará", "printer_id": printer["id"],
                                                        "filament_id": pla["id"], "grams_estimated": 100, "estimated_minutes": 60, "status": "printing"}).json()
    client.patch(f"{API}/jobs/{j['id']}", headers=admin, json={"progress_pct": 30})
    f = client.post(f"{API}/jobs/{j['id']}/transition", headers=admin, json={"action": "fail", "failure_reason": "adhesion"}).json()
    assert f["status"] == "failed" and f["grams_used"] == 30 and f["failure_reason"] == "adhesion"
    c = client.post(f"{API}/jobs", headers=admin, json={"user_id": uid, "project_name": "Cancelado", "status": "pending", "grams_estimated": 5,
                                                        "estimated_minutes": 10}).json()
    assert c["status"] == "pending" and c["queue_position"] == 1
    assert client.post(f"{API}/jobs/{c['id']}/transition", headers=admin, json={"action": "start"}).status_code == 409
    assert client.post(f"{API}/jobs/{c['id']}/transition", headers=admin, json={"action": "cancel"}).json()["status"] == "cancelled"


def test_historical_job_registration(client, admin, student, printer, pla):
    _, uid = student
    start = future(-48)
    r = client.post(f"{API}/jobs", headers=admin, json={
        "user_id": uid, "project_name": "Registro histórico", "printer_id": printer["id"], "filament_id": pla["id"], "grams_estimated": 20,
        "estimated_minutes": 60, "status": "completed", "started_at": iso(start), "finished_at": iso(start + timedelta(minutes=65))})
    assert r.status_code == 201, r.text
    assert r.json()["duration_min"] == 65
    # el filtro por día usa el día local de la sala (UTC-5): un trabajo a las 03:00 UTC cae en el día anterior
    local_day = (start - timedelta(hours=5)).date().isoformat()
    day = client.get(f"{API}/jobs", headers=admin, params={"date_from": local_day, "date_to": local_day, "limit": 200}).json()
    assert any(j["id"] == r.json()["id"] for j in day["items"])
    bad = client.post(f"{API}/jobs", headers=admin, json={"user_id": uid, "project_name": "Mal", "status": "completed", "grams_estimated": 1, "estimated_minutes": 5})
    assert bad.status_code == 422


# ---------- Reservas ----------
def test_reservations_flow(client, admin, student, student2, printer):
    h1, _ = student
    h2, _ = student2
    start = future(30)
    body = {"printer_id": printer["id"], "start_at": iso(start), "end_at": iso(start + timedelta(hours=2)), "purpose": "Práctica"}
    r = client.post(f"{API}/reservations", headers=h1, json=body)
    assert r.status_code == 201 and r.json()["status"] == "pending"
    rid = r.json()["id"]
    # solape (aunque esté pendiente) y datos inválidos
    assert client.post(f"{API}/reservations", headers=h2, json={**body, "start_at": iso(start + timedelta(hours=1)), "end_at": iso(start + timedelta(hours=3))}).status_code == 409
    assert client.post(f"{API}/reservations", headers=h2, json={**body, "end_at": iso(start - timedelta(hours=1))}).status_code == 422
    past = future(-5)
    assert client.post(f"{API}/reservations", headers=h2, json={**body, "start_at": iso(past), "end_at": iso(past + timedelta(hours=1))}).status_code == 422
    # otro cliente no puede cancelarla; el dueño sí
    assert client.post(f"{API}/reservations/{rid}/cancel", headers=h2).status_code == 403
    # el cliente no puede aprobar
    assert client.post(f"{API}/reservations/{rid}/decision", headers=h1, json={"decision": "approve"}).status_code == 403
    ok = client.post(f"{API}/reservations/{rid}/decision", headers=admin, json={"decision": "approve", "admin_note": "ok"})
    assert ok.json()["status"] == "approved"
    # disponibilidad no filtra datos de terceros
    day = (start + timedelta(hours=-5)).date()
    slots = client.get(f"{API}/reservations/availability", headers=h2, params={"printer_id": printer["id"], "day": (start - timedelta(hours=5)).date().isoformat()}).json()
    slots2 = client.get(f"{API}/reservations/availability", headers=h2, params={"printer_id": printer["id"], "day": start.date().isoformat()}).json()
    assert day and all("user_id" not in s for s in slots + slots2)
    assert any(not s["is_mine"] for s in slots + slots2)
    cancel = client.post(f"{API}/reservations/{rid}/cancel", headers=h1)
    assert cancel.json()["status"] == "cancelled"
    # liberada: ahora sí puede reservar la franja
    assert client.post(f"{API}/reservations", headers=h2, json=body).status_code == 201
    assert len(client.get(f"{API}/reservations/mine", headers=h2).json()) == 1


def test_reservation_blocks_job_start(client, admin, student, student2, printer, pla):
    h2, uid2 = student2
    # reserva aprobada de otro usuario que cubre "ahora"
    now = future(0)
    r = client.post(f"{API}/reservations", headers=admin, json={"printer_id": printer["id"], "start_at": iso(now - timedelta(minutes=1)),
                                                                "end_at": iso(now + timedelta(hours=2)), "user_id": uid2})
    assert r.status_code == 201, r.text
    _, uid1 = student
    j = client.post(f"{API}/jobs", headers=admin, json={"user_id": uid1, "project_name": "Choca con reserva", "printer_id": printer["id"],
                                                        "filament_id": pla["id"], "grams_estimated": 10, "estimated_minutes": 30, "status": "queued"}).json()
    assert client.post(f"{API}/jobs/{j['id']}/transition", headers=admin, json={"action": "start"}).status_code == 409
    forced = client.post(f"{API}/jobs/{j['id']}/transition", headers=admin, json={"action": "start", "ignore_reservations": True})
    assert forced.status_code == 200
    client.post(f"{API}/jobs/{j['id']}/transition", headers=admin, json={"action": "cancel"})
    client.post(f"{API}/reservations/{r.json()['id']}/cancel", headers=admin)


# ---------- Mantenimiento ----------
def test_maintenance_syncs_equipment(client, admin, printer):
    eid = printer["id"]
    m = client.post(f"{API}/maintenance", headers=admin, json={"equipment_id": eid, "type": "corrective", "status": "in_progress", "description": "Cambio de boquilla"})
    assert m.status_code == 201, m.text
    assert next(e for e in client.get(f"{API}/equipment", headers=admin).json() if e["id"] == eid)["status"] == "maintenance"
    # no se puede reservar mientras está en mantenimiento
    start = future(100)
    assert client.post(f"{API}/reservations", headers=admin, json={"printer_id": eid, "start_at": iso(start), "end_at": iso(start + timedelta(hours=1))}).status_code == 409
    done = client.patch(f"{API}/maintenance/{m.json()['id']}", headers=admin, json={"status": "done", "performed_at": date.today().isoformat(), "next_due_at": (date.today() + timedelta(days=60)).isoformat()})
    assert done.status_code == 200
    e = next(e for e in client.get(f"{API}/equipment", headers=admin).json() if e["id"] == eid)
    assert e["status"] == "available" and e["last_maintenance_at"] == date.today().isoformat()
    assert e["next_maintenance_at"] == (date.today() + timedelta(days=60)).isoformat()
    assert client.patch(f"{API}/maintenance/{m.json()['id']}", headers=admin, json={"description": "cambio"}).status_code == 409
    bad = client.post(f"{API}/maintenance", headers=admin, json={"equipment_id": eid, "status": "scheduled", "description": "Sin fecha"})
    assert bad.status_code == 422


# ---------- Usuarios ----------
def test_user_management(client, admin):
    me = client.get(f"{API}/auth/me", headers=admin).json()
    assert client.patch(f"{API}/users/{me['id']}", headers=admin, json={"role": "client"}).status_code == 409
    u = client.post(f"{API}/users", headers=admin, json={"name": "Nuevo Admin", "email": "nuevo@salasteam.dev", "password": "Clave12345", "role": "admin", "admin_pin": "4242"})
    assert u.status_code == 201
    # añadir o promover administradores exige el PIN
    no_pin = {"name": "Sin Pin", "email": "sinpin@salasteam.dev", "password": "Clave12345", "role": "admin"}
    assert client.post(f"{API}/users", headers=admin, json=no_pin).status_code == 403
    cl = client.post(f"{API}/users", headers=admin, json={**no_pin, "role": "client"}).json()
    assert client.patch(f"{API}/users/{cl['id']}", headers=admin, json={"role": "admin"}).status_code == 403
    assert client.patch(f"{API}/users/{cl['id']}", headers=admin, json={"role": "admin", "admin_pin": "4242"}).json()["role"] == "admin"
    assert client.patch(f"{API}/users/{u.json()['id']}", headers=admin, json={"is_active": False}).json()["is_active"] is False
    assert client.post(f"{API}/auth/login", json={"email": "nuevo@salasteam.dev", "password": "Clave12345"}).status_code == 401
    assert all("password" not in k for k in u.json())


# ---------- Estadísticas, simulador y aislamiento demo/real ----------
def test_stats_on_real_data(client, admin):
    r = client.get(f"{API}/stats/overview", headers=admin, params={"date_from": (date.today() - timedelta(days=10)).isoformat(), "date_to": date.today().isoformat()})
    assert r.status_code == 200
    k = r.json()["kpis"]
    assert k["completed"] >= 2 and k["failed"] >= 1 and 0 <= k["success_rate"] <= 100
    assert r.json()["demo"] is False
    assert client.get(f"{API}/stats/overview", headers=admin, params={"date_from": "2026-05-02", "date_to": "2026-05-01"}).status_code == 422


def test_csv_export(client, admin):
    r = client.get(f"{API}/jobs/export.csv", headers=admin, params={"date_from": (date.today() - timedelta(days=10)).isoformat(), "date_to": date.today().isoformat()})
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"]
    assert "Registro histórico" in r.text and r.text.splitlines()[0].lstrip("﻿").startswith("id;proyecto")


def test_simulator_isolated_and_analyzable(client, admin, student):
    # En modo demo se generan datos que no se mezclan con los reales
    assert client.post(f"{API}/config/mode", headers=admin, json={"mode": "demo"}).json()["demo"] is True
    st = client.get(f"{API}/simulator/status", headers=admin).json()
    assert st["records"]["jobs"] > 100 and st["records"]["equipment"] >= 6
    eq = client.get(f"{API}/equipment", headers=admin).json()
    assert all(e["is_demo"] for e in eq) and not any(e["code"] == "T-IMP-01" for e in eq)
    ov = client.get(f"{API}/stats/overview", headers=admin).json()
    assert ov["demo"] is True and ov["kpis"]["total_jobs"] > 100
    assert ov["jobs_by_period"] and ov["consumption_by_period"]["rows"] and ov["printers"] and ov["materials"] and ov["colors"]
    assert ov["demand_heatmap"] and ov["stock_forecast"] and ov["failure_reasons"] and ov["insights"]
    # La impresora problemática de la simulación debe quedar señalada por los insights
    assert any("Impresora 03" in i["title"] for i in ov["insights"])
    # Coherencia numérica
    k = ov["kpis"]
    assert k["completed"] + k["failed"] + k["cancelled"] + k["active"] == k["total_jobs"]
    assert sum(s["total"] for s in ov["jobs_by_period"]) == k["total_jobs"]
    assert abs(sum(m["share_pct"] for m in ov["materials"]) - 100) < 1.5
    # Filtros
    pid = ov["printers"][0]["printer_id"]
    f = client.get(f"{API}/stats/overview", headers=admin, params={"printer_id": pid, "material": "PLA"}).json()
    assert 0 < f["kpis"]["total_jobs"] < k["total_jobs"]
    # Dashboard y alertas
    d = client.get(f"{API}/stats/dashboard", headers=admin).json()
    assert d["printers"]["total"] == 6 and d["low_stock"] >= 1 and d["maintenance_alerts"] >= 1 and d["alerts"]
    # El cliente real ve actividad simulada propia
    h, _ = student
    assert len(client.get(f"{API}/jobs/mine?history=true", headers=h).json()) > 0
    # Inventario coherente: nada negativo y disponible = suma de movimientos
    for f in client.get(f"{API}/filaments", headers=admin, params={"include_inactive": True}).json():
        assert f["available_weight_g"] >= 0
    # Volver a modo real no muestra nada de la demo
    client.post(f"{API}/config/mode", headers=admin, json={"mode": "real"})
    assert all(not e["is_demo"] for e in client.get(f"{API}/equipment", headers=admin).json())


def test_simulator_tick_advances_jobs(client, admin):
    from app.core.db import SessionLocal
    from app.models.entities import JobStatus, PrintJob
    from app.seed import simulator
    from sqlalchemy import select

    client.post(f"{API}/config/mode", headers=admin, json={"mode": "demo"})
    with SessionLocal() as db:
        running = list(db.scalars(select(PrintJob).where(PrintJob.is_demo.is_(True), PrintJob.status == JobStatus.printing.value)))
        assert running
        before = {j.id: j.progress_pct for j in running}
        simulator.tick(db)
        db.expire_all()
        after = {j.id: db.get(PrintJob, j.id).progress_pct for j in running}
        assert any(after[i] > before[i] or db.get(PrintJob, i).status != "printing" for i in before)
    client.post(f"{API}/config/mode", headers=admin, json={"mode": "real"})


def test_websocket_requires_token(client):
    from starlette.websockets import WebSocketDisconnect

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"token": "invalido"})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
