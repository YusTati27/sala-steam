from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.models.entities import MovementType
from app.schemas.base import ORM, UTCDT

MATERIALS = ["PLA", "PETG", "ABS", "TPU", "ASA", "NYLON", "OTRO"]


def _norm_hex(v: str) -> str:
    v = v.strip()
    if not (len(v) == 7 and v.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in v[1:])):
        raise ValueError("Color hexadecimal inválido (ej. #FF0000)")
    return v.upper()


class FilamentCreate(BaseModel):
    code: str | None = Field(default=None, max_length=40)
    material: str = Field(min_length=2, max_length=30)
    brand: str = Field(default="", max_length=80)
    color: str = Field(min_length=2, max_length=40)
    color_hex: str = "#888888"
    initial_weight_g: float = Field(gt=0, le=20000)
    available_weight_g: float | None = Field(default=None, ge=0, le=20000)
    low_stock_threshold_g: float = Field(default=200, ge=0, le=20000)
    acquired_at: date | None = None
    notes: str = Field(default="", max_length=1000)

    _hex = field_validator("color_hex")(_norm_hex)

    @field_validator("material")
    @classmethod
    def _mat(cls, v: str) -> str:
        return v.strip().upper()


class FilamentUpdate(BaseModel):
    brand: str | None = None
    color: str | None = Field(default=None, min_length=2, max_length=40)
    color_hex: str | None = None
    low_stock_threshold_g: float | None = Field(default=None, ge=0, le=20000)
    is_active: bool | None = None
    notes: str | None = None

    @field_validator("color_hex")
    @classmethod
    def _h(cls, v):
        return _norm_hex(v) if v is not None else v


class FilamentOut(ORM):
    id: int
    code: str
    material: str
    brand: str
    color: str
    color_hex: str
    initial_weight_g: float | None = None
    available_weight_g: float
    consumed_g: float | None = None
    low_stock_threshold_g: float | None = None
    acquired_at: date | None = None
    is_active: bool
    is_demo: bool
    stock_status: str  # available | low | empty
    notes: str | None = None


class MovementIn(BaseModel):
    type: MovementType
    grams: float = Field(gt=0, le=20000)
    note: str = Field(default="", max_length=255)


class MovementOut(ORM):
    id: int
    filament_id: int
    type: str
    grams: float
    balance_after_g: float
    note: str
    job_id: int | None
    created_at: UTCDT
