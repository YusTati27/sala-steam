import enum
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.timeutil import utcnow


class Role(enum.StrEnum):
    client = "client"
    admin = "admin"


class EquipmentType(enum.StrEnum):
    printer_3d = "printer_3d"
    tool = "tool"
    other = "other"


class EquipmentStatus(enum.StrEnum):
    available = "available"
    busy = "busy"
    maintenance = "maintenance"
    out_of_service = "out_of_service"


class JobStatus(enum.StrEnum):
    pending = "pending"
    queued = "queued"
    printing = "printing"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class ReservationStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    completed = "completed"


class MovementType(enum.StrEnum):
    stock_in = "in"
    stock_out = "out"
    adjust = "adjust"


class MaintenanceType(enum.StrEnum):
    preventive = "preventive"
    corrective = "corrective"


class MaintenanceStatus(enum.StrEnum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    done = "done"


class FailureReason(enum.StrEnum):
    adhesion = "adhesion"
    nozzle_clog = "nozzle_clog"
    filament_issue = "filament_issue"
    warping = "warping"
    power_outage = "power_outage"
    user_error = "user_error"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=Role.client.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(120), default="")
    type: Mapped[str] = mapped_column(String(20), default=EquipmentType.printer_3d.value, index=True)
    status: Mapped[str] = mapped_column(String(20), default=EquipmentStatus.available.value, index=True)
    build_volume: Mapped[str] = mapped_column(String(60), default="")
    nozzle_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    supported_materials: Mapped[list] = mapped_column(JSON, default=list)
    specs: Mapped[dict] = mapped_column(JSON, default=dict)
    hardware_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acquired_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_maintenance_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_maintenance_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Filament(Base):
    __tablename__ = "filaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    material: Mapped[str] = mapped_column(String(30), index=True)
    brand: Mapped[str] = mapped_column(String(80), default="")
    color: Mapped[str] = mapped_column(String(40))
    color_hex: Mapped[str] = mapped_column(String(9), default="#888888")
    initial_weight_g: Mapped[float] = mapped_column(Float)
    available_weight_g: Mapped[float] = mapped_column(Float)
    low_stock_threshold_g: Mapped[float] = mapped_column(Float, default=200.0)
    acquired_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FilamentMovement(Base):
    __tablename__ = "filament_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    filament_id: Mapped[int] = mapped_column(ForeignKey("filaments.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))
    grams: Mapped[float] = mapped_column(Float)  # siempre positivo; el tipo define el sentido
    balance_after_g: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(String(255), default="")
    job_id: Mapped[int | None] = mapped_column(ForeignKey("print_jobs.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    filament: Mapped[Filament] = relationship()


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_name: Mapped[str] = mapped_column(String(160))
    printer_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id"), nullable=True, index=True)
    filament_id: Mapped[int | None] = mapped_column(ForeignKey("filaments.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.pending.value, index=True)
    grams_estimated: Mapped[float] = mapped_column(Float, default=0.0)
    grams_used: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=60)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    failure_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship()
    printer: Mapped[Equipment | None] = relationship()
    filament: Mapped[Filament | None] = relationship()


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    printer_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default=ReservationStatus.pending.value, index=True)
    purpose: Mapped[str] = mapped_column(String(255), default="")
    admin_note: Mapped[str] = mapped_column(String(255), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship()
    printer: Mapped[Equipment] = relationship()


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    type: Mapped[str] = mapped_column(String(20), default=MaintenanceType.preventive.value)
    status: Mapped[str] = mapped_column(String(20), default=MaintenanceStatus.scheduled.value, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    scheduled_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    performed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    performed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    equipment: Mapped[Equipment] = relationship()


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))
