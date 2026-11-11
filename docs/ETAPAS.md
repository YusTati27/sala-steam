# Plan por etapas
1. [x] Arquitectura y organización
2. [x] Base de datos y migraciones (Alembic `0001`)
3. [x] Backend y API (+ simulador)
4. [x] Autenticación y roles
5. [x] Interfaz de clientes
6. [x] Interfaz de administración
7. [x] Equipos e inventario
8. [x] Trabajos y reservas
9. [x] Estadísticas y gráficas (con hallazgos automáticos, comparación con período previo, CSV e impresión)
10. [~] Integraciones y notificaciones — notificaciones en vivo por WebSocket y alertas; hardware real solo preparado (ver INTEGRACION_HARDWARE.md)
11. [x] Pruebas y corrección de errores (20 pruebas backend; build de frontend)

## Limitaciones conocidas
- Sin pruebas automatizadas de frontend (se verificó manualmente en navegador).
- El limitador de login es en memoria (un solo proceso); en producción usar un almacén compartido o un proxy.
- La tabla `audit_log` del diseño inicial no se implementó.
- Zona horaria de la sala fija por `LOCAL_UTC_OFFSET_HOURS` (por defecto -5).
- No se probó contra PostgreSQL (solo SQLite); el código usa SQLAlchemy portable y el driver `psycopg` está en los requisitos.
