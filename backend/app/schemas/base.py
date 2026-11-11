from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer

from app.core.timeutil import to_naive_utc


def _parse(v):
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if isinstance(v, datetime):
        return to_naive_utc(v)
    return v


# Se almacena como UTC "naive"; al serializar se añade 'Z' para que el navegador lo interprete bien.
UTCDT = Annotated[
    datetime,
    BeforeValidator(_parse),
    PlainSerializer(lambda d: d.isoformat() + "Z", return_type=str, when_used="always"),
]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
