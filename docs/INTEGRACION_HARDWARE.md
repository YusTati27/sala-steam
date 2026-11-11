# Integración con impresoras reales

**Estado actual:** la plataforma funciona sin hardware. El operador registra inicio, avance, finalización o fallo desde
*Trabajos*. El simulador (modo demo) solo existe para demostración.

## Qué hay preparado
- Campo `hardware_endpoint` en cada equipo (URL de la impresora o de su servidor).
- Interfaz `PrinterAdapter` en `backend/app/integrations/printer_adapter.py` con `get_telemetry()`, `start_print()` y `cancel_print()`.
- Stubs `OctoPrintAdapter` y `MoonrakerAdapter` (lanzan `NotImplementedError`).
- Los cambios de estado pasan por `app/services/jobs.py::transition`, así que una integración solo debe llamar esas funciones
  (p. ej. actualizar `progress_pct`, completar o fallar el trabajo) y todo lo demás —estado de la impresora, descuento de filamento,
  cola, WebSocket— se sincroniza solo.

## Qué se necesita para activarlo
| Firmware / servidor | Qué hace falta | Endpoint típico |
|---|---|---|
| OctoPrint | Raspberry Pi/PC junto a la impresora, red local, **API key por impresora** | `GET /api/job`, `GET /api/printer` (cabecera `X-Api-Key`) |
| Klipper + Moonraker | Moonraker accesible en la red, (token opcional) | `GET /printer/objects/query?print_stats&display_status&extruder&heater_bed` |
| Bambu Lab / Prusa Connect | Modo LAN/cloud según el modelo; credenciales por equipo | depende del fabricante |

## Pasos
1. Implementar el adaptador correspondiente (o uno nuevo).
2. Guardar las claves **fuera del repositorio** (variables de entorno o un almacén de secretos), nunca en la base de datos en texto plano.
3. Añadir una tarea periódica (similar a `simulator_loop` en `app/main.py`) que consulte la telemetría y llame a `transition(...)`.
4. Probar primero con una sola impresora en red aislada.

## Pendiente de definir con la sala
Marca y modelo de cada impresora, si usan OctoPrint/Klipper, y si la red de la universidad permite que el servidor las alcance.
