from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.models.entities import EquipmentStatus, EquipmentType
from app.schemas.base import ORM, UTCDT


class EquipmentBase(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    model: str = Field(default="", max_length=120)
    type: EquipmentType = EquipmentType.printer_3d
    status: EquipmentStatus = EquipmentStatus.available
    build_volume: str = Field(default="", max_length=60)
    nozzle_mm: float | None = Field(default=None, gt=0, le=2)
    supported_materials: list[str] = Field(default_factory=list)
    specs: dict = Field(default_factory=dict)
    hardware_endpoint: str | None = Field(default=None, max_length=255)
    acquired_at: date | None = None
    last_maintenance_at: date | None = None
    next_maintenance_at: date | None = None
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _dates(self):
        if self.last_maintenance_at and self.next_maintenance_at and self.next_maintenance_at < self.last_maintenance_at:
            raise ValueError("El próximo mantenimiento no puede ser anterior al último")
        return self


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=40)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    model: str | None = None
    type: EquipmentType | None = None
    status: EquipmentStatus | None = None
    build_volume: str | None = None
    nozzle_mm: float | None = Field(default=None, gt=0, le=2)
    supported_materials: list[str] | None = None
    specs: dict | None = None
    hardware_endpoint: str | None = None
    acquired_at: date | None = None
    last_maintenance_at: date | None = None
    next_maintenance_at: date | None = None
    notes: str | None = None


class CurrentJob(BaseModel):
    id: int
    project_name: str
    progress_pct: float
    estimated_end_at: UTCDT | None = None
    is_mine: bool = False


class EquipmentOut(ORM):
    id: int
    code: str
    name: str
    model: str
    type: str
    status: str
    build_volume: str
    nozzle_mm: float | None
    supported_materials: list
    specs: dict
    hardware_endpoint: str | None = None
    acquired_at: date | None
    last_maintenance_at: date | None
    next_maintenance_at: date | None
    notes: str | None = ""
    is_demo: bool
    # Calculados
    current_job: CurrentJob | None = None
    available_at: UTCDT | None = None
    queue_length: int = 0
    queue_clear_at: UTCDT | None = None
    maintenance_days_left: int | None = None
