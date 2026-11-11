from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.base import ORM, UTCDT


class ReservationCreate(BaseModel):
    printer_id: int
    start_at: UTCDT
    end_at: UTCDT
    purpose: str = Field(default="", max_length=255)
    user_id: int | None = None  # solo administradores pueden reservar a nombre de otro usuario

    @model_validator(mode="after")
    def _check(self):
        if self.end_at <= self.start_at:
            raise ValueError("La hora de fin debe ser posterior a la de inicio")
        if (self.end_at - self.start_at).total_seconds() > 8 * 3600:
            raise ValueError("Una reserva no puede superar 8 horas")
        if (self.end_at - self.start_at).total_seconds() < 15 * 60:
            raise ValueError("Una reserva debe durar al menos 15 minutos")
        return self


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject", "complete"]
    admin_note: str = Field(default="", max_length=255)


class ReservationOut(ORM):
    id: int
    user_id: int
    user_name: str | None = None
    printer_id: int
    printer_name: str | None = None
    start_at: UTCDT
    end_at: UTCDT
    status: str
    purpose: str
    admin_note: str
    is_mine: bool = False
    is_demo: bool
    created_at: UTCDT


class SlotOut(BaseModel):
    start_at: UTCDT
    end_at: UTCDT
    status: str
    is_mine: bool = False
