from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.entities import FailureReason, JobStatus
from app.schemas.base import ORM, UTCDT


class JobCreate(BaseModel):
    user_id: int
    project_name: str = Field(min_length=2, max_length=160)
    printer_id: int | None = None
    filament_id: int | None = None
    grams_estimated: float = Field(gt=0, le=5000)
    estimated_minutes: int = Field(gt=0, le=60 * 24 * 7)
    status: JobStatus = JobStatus.pending  # pending|queued|printing o histórico completed|failed|cancelled
    started_at: UTCDT | None = None
    finished_at: UTCDT | None = None
    grams_used: float | None = Field(default=None, ge=0, le=5000)
    failure_reason: FailureReason | None = None
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _check(self):
        hist = {JobStatus.completed, JobStatus.failed}
        if self.status in hist:
            if not (self.started_at and self.finished_at):
                raise ValueError("Un trabajo histórico requiere fecha de inicio y de fin")
            if self.finished_at <= self.started_at:
                raise ValueError("La fecha de fin debe ser posterior a la de inicio")
            if not self.printer_id or not self.filament_id:
                raise ValueError("Un trabajo histórico requiere impresora y filamento")
        if self.status in {JobStatus.queued, JobStatus.printing} and not self.printer_id:
            raise ValueError("Debe asignar una impresora")
        if self.status == JobStatus.printing and not self.filament_id:
            raise ValueError("Debe asignar un filamento para iniciar la impresión")
        return self


class JobUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=2, max_length=160)
    printer_id: int | None = None
    filament_id: int | None = None
    grams_estimated: float | None = Field(default=None, gt=0, le=5000)
    estimated_minutes: int | None = Field(default=None, gt=0, le=60 * 24 * 7)
    progress_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class TransitionIn(BaseModel):
    action: Literal["queue", "start", "complete", "fail", "cancel"]
    grams_used: float | None = Field(default=None, ge=0, le=5000)
    failure_reason: FailureReason | None = None
    printer_id: int | None = None
    filament_id: int | None = None
    ignore_reservations: bool = False


class JobOut(ORM):
    id: int
    user_id: int
    user_name: str | None = None
    project_name: str
    printer_id: int | None
    printer_name: str | None = None
    filament_id: int | None
    material: str | None = None
    color: str | None = None
    color_hex: str | None = None
    status: str
    grams_estimated: float
    grams_used: float
    estimated_minutes: int
    progress_pct: float
    queue_position: int | None = None
    estimated_end_at: UTCDT | None = None
    failure_reason: str | None
    notes: str | None = None
    is_mine: bool = False
    is_demo: bool
    created_at: UTCDT
    queued_at: UTCDT | None
    started_at: UTCDT | None
    finished_at: UTCDT | None
    duration_min: float | None


class JobPage(BaseModel):
    items: list[JobOut]
    total: int
