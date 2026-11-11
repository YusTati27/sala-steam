from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import validate_password_strength
from app.models.entities import Role
from app.schemas.base import ORM, UTCDT


def _check_pw(v: str) -> str:
    err = validate_password_strength(v)
    if err:
        raise ValueError(err)
    return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=200)
    admin_pin: str | None = Field(default=None, max_length=64)  # si se envía, solicita rol de administrador

    _pw = field_validator("password")(_check_pw)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(max_length=200)

    _pw = field_validator("new_password")(_check_pw)


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    is_demo: bool
    created_at: UTCDT


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=200)
    role: Role = Role.client
    admin_pin: str | None = Field(default=None, max_length=64)  # obligatorio si role = admin

    _pw = field_validator("password")(_check_pw)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    admin_pin: str | None = Field(default=None, max_length=64)  # obligatorio al promover a administrador


class ResetPasswordIn(BaseModel):
    new_password: str = Field(max_length=200)

    _pw = field_validator("new_password")(_check_pw)
