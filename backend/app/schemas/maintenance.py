from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.models.entities import MaintenanceStatus, MaintenanceType
from app.schemas.base import ORM, UTCDT


class MaintenanceCreate(BaseModel):
    equipment_id: int
    type: MaintenanceType = MaintenanceType.preventive
    status: MaintenanceStatus = MaintenanceStatus.scheduled
    description: str = Field(min_length=3, max_length=2000)
    scheduled_for: date | None = None
    performed_at: date | None = None
    next_due_at: date | None = None
    cost: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check(self):
        if self.status == MaintenanceStatus.done and not self.performed_at:
            raise ValueError("Un mantenimiento realizado requiere fecha de ejecución")
        if self.status == MaintenanceStatus.scheduled and not self.scheduled_for:
            raise ValueError("Un mantenimiento programado requiere fecha programada")
        if self.performed_at and self.next_due_at and self.next_due_at < self.performed_at:
            raise ValueError("La próxima revisión no puede ser anterior a la ejecución")
        return self


class MaintenanceUpdate(BaseModel):
    status: MaintenanceStatus | None = None
    description: str | None = Field(default=None, min_length=3, max_length=2000)
    scheduled_for: date | None = None
    performed_at: date | None = None
    next_due_at: date | None = None
    cost: float | None = Field(default=None, ge=0)


class MaintenanceOut(ORM):
    id: int
    equipment_id: int
    equipment_name: str | None = None
    equipment_code: str | None = None
    type: str
    status: str
    description: str
    scheduled_for: date | None
    performed_at: date | None
    next_due_at: date | None
    cost: float | None
    is_demo: bool
    created_at: UTCDT
