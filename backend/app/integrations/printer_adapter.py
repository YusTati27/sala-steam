"""Capa de integración con impresoras reales.

El sistema NO requiere hardware para funcionar: el operador registra el avance desde el panel.
Para automatizarlo, implemente `PrinterAdapter` para el firmware/servidor de cada impresora y guarde su URL en
`Equipment.hardware_endpoint`. Ver docs/INTEGRACION_HARDWARE.md.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PrinterTelemetry:
    state: str  # idle | printing | paused | error | offline
    progress_pct: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    remaining_min: float | None = None


class PrinterAdapter(ABC):
    def __init__(self, endpoint: str, api_key: str | None = None) -> None:
        self.endpoint, self.api_key = endpoint, api_key

    @abstractmethod
    def get_telemetry(self) -> PrinterTelemetry: ...

    @abstractmethod
    def start_print(self, file_name: str) -> None: ...

    @abstractmethod
    def cancel_print(self) -> None: ...


class OctoPrintAdapter(PrinterAdapter):
    """Pendiente: GET {endpoint}/api/job y /api/printer con cabecera X-Api-Key. Requiere red y una API key por impresora."""

    def get_telemetry(self) -> PrinterTelemetry:
        raise NotImplementedError("Integración OctoPrint pendiente de hardware")

    def start_print(self, file_name: str) -> None:
        raise NotImplementedError

    def cancel_print(self) -> None:
        raise NotImplementedError


class MoonrakerAdapter(PrinterAdapter):
    """Pendiente: Klipper/Moonraker -> GET {endpoint}/printer/objects/query?print_stats&display_status&heater_bed&extruder."""

    def get_telemetry(self) -> PrinterTelemetry:
        raise NotImplementedError("Integración Moonraker pendiente de hardware")

    def start_print(self, file_name: str) -> None:
        raise NotImplementedError

    def cancel_print(self) -> None:
        raise NotImplementedError
