# Arquitectura

Separación estricta frontend / backend; comunicación por API REST (`/api/v1`) y WebSocket (`/ws`).

## Backend (`backend/app`)
- `core/`: configuración (variables de entorno), seguridad (JWT, hash), dependencias de roles.
- `models/`: modelos SQLAlchemy. `schemas/`: validación Pydantic.
- `api/v1/`: routers (auth, users, equipment, filaments, jobs, reservations, maintenance, stats, simulator).
- `services/`: lógica de negocio y sincronización de estados impresora ↔ trabajo ↔ reserva.
- `ws/`: difusión de eventos en tiempo real.
- `integrations/`: interfaz `PrinterAdapter` (implementación simulada; OctoPrint/Moonraker futuros).
- `seed/`: datos DEMO marcados con `is_demo`.

## Frontend (`frontend/src`)
- `layouts/` (Cliente / Admin con barra lateral por rol), `routes/` (rutas protegidas),
  `features/` (auth, client, admin, simulator), `components/ui/`, `lib/` (API, WebSocket, tipos).

## Reglas
- Permisos verificados siempre en el backend; el frontend solo oculta opciones.
- Contraseñas con hash (argon2/bcrypt); ningún secreto en el repositorio.
