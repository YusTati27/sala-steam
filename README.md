# Sala STEAM — Plataforma de gestión

Sistema web para gestionar impresoras 3D, inventario de filamentos, reservas, trabajos y mantenimiento de una sala STEAM
universitaria. Dos roles —**cliente** y **administrador**— sobre una misma base de datos.

## Stack
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS 4 + Recharts + TanStack Query
- **Backend:** Python + FastAPI + SQLAlchemy 2 + Alembic
- **Base de datos:** SQLite en desarrollo (por defecto) · PostgreSQL en producción (`DATABASE_URL`)
- **Tiempo real:** WebSocket (`/ws`) · **Autenticación:** JWT + contraseñas con Argon2

## Puesta en marcha (desarrollo)
Requisitos: Python 3.11+ y Node.js 20+.

```bash
# 1) Backend
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt        # Windows (en Linux/macOS: .venv/bin/python)
copy .env.example .env                                         # y complete los valores (ver abajo)
.venv\Scripts\python -m uvicorn app.main:app --port 8010

# 2) Frontend (otra terminal)
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxy a http://127.0.0.1:8010)
```

`backend/.env` (nunca se sube al repositorio):
- `JWT_SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`: crea el primer administrador si la base está vacía. Cámbiela desde la app.
- `DATABASE_URL`: vacío = SQLite local. Para PostgreSQL: `postgresql+psycopg://usuario:clave@localhost:5432/sala_steam`.

El puerto 8000 suele estar ocupado en equipos con otro software; por eso se usa **8010** (ajuste `frontend/vite.config.ts` si cambia).

## Modo simulador (datos de demostración)
Al iniciar por primera vez el sistema arranca en **modo simulador**: genera ~6 meses de historial **inventado**
(6 impresoras, bobinas, ~600 trabajos, reservas, mantenimientos) y mantiene las impresiones en curso avanzando en vivo.
Todo registro simulado lleva `is_demo = true`, la interfaz muestra la insignia **SIMULADOR** y nunca se mezcla con datos reales.
Desde *Configuración* el administrador puede pasar a **modo real**, regenerar o borrar la simulación.

## Pruebas
```bash
cd backend && .venv\Scripts\python -m pytest -q     # 20 pruebas de API, permisos, reglas de negocio y analítica
cd frontend && npm run build                          # comprobación de tipos + build
```

## Migraciones
`alembic upgrade head` (en `backend/`) aplica el esquema. En desarrollo, la app también crea las tablas al iniciar.

## Documentación
- `docs/ARQUITECTURA.md` · `docs/ETAPAS.md` · `docs/INTEGRACION_HARDWARE.md`

## Seguridad
Secretos solo en `.env` (ignorado por git); contraseñas con Argon2; permisos validados en el backend por rol;
limitador de intentos de inicio de sesión; WebSocket autenticado con JWT en el primer mensaje.
