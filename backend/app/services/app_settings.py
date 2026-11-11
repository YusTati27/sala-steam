from sqlalchemy.orm import Session

from app.models.entities import AppSetting

DEFAULTS = {"mode": "demo", "open_hours_per_day": "10"}


def get(db: Session, key: str) -> str:
    row = db.get(AppSetting, key)
    return row.value if row else DEFAULTS[key]


def set_value(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


def is_demo_mode(db: Session) -> bool:
    return get(db, "mode") == "demo"


def open_hours(db: Session) -> float:
    try:
        return max(1.0, min(24.0, float(get(db, "open_hours_per_day"))))
    except ValueError:
        return 10.0
