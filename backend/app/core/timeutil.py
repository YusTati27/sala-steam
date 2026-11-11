from datetime import UTC, datetime


def utcnow() -> datetime:
    """Fecha/hora UTC sin zona horaria (convención interna del proyecto)."""
    return datetime.now(UTC).replace(tzinfo=None)


def to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value
