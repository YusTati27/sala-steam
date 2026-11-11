import hmac
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import Role, User
from app.schemas.user import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.seed.simulator import ensure_demo_for_user
from app.services import app_settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Limitador sencillo en memoria (por proceso): 5 intentos fallidos por 15 min por correo+IP.
_fails: dict[str, list[float]] = defaultdict(list)
WINDOW, MAX_FAILS = 15 * 60, 5


def _throttle_key(request: Request, email: str) -> str:
    return f"{email.lower()}|{request.client.host if request.client else '-'}"


def check_admin_pin(request: Request, pin: str) -> None:
    """Valida el PIN de alta de administradores (tiempo constante y límite de intentos por IP)."""
    expected = get_settings().admin_signup_pin
    if not expected:
        raise HTTPException(403, "El registro de administradores está deshabilitado")
    key = f"pin|{request.client.host if request.client else '-'}"
    now = time.time()
    _fails[key] = [t for t in _fails[key] if now - t < WINDOW]
    if len(_fails[key]) >= MAX_FAILS:
        raise HTTPException(429, "Demasiados intentos con el PIN. Intente de nuevo en unos minutos")
    if not hmac.compare_digest(pin.encode(), expected.encode()):
        _fails[key].append(now)
        raise HTTPException(403, "PIN de administrador incorrecto")


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower()
    wants_admin = bool(data.admin_pin)
    if wants_admin:
        check_admin_pin(request, data.admin_pin)
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Ya existe una cuenta con ese correo")
    user = User(name=data.name.strip(), email=email, password_hash=hash_password(data.password),
                role=Role.admin.value if wants_admin else Role.client.value)
    db.add(user)
    db.commit()
    if app_settings.is_demo_mode(db):
        ensure_demo_for_user(db, user)
    return TokenOut(access_token=create_access_token(user.id, user.role), user=user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    key = _throttle_key(request, data.email)
    now = time.time()
    _fails[key] = [t for t in _fails[key] if now - t < WINDOW]
    if len(_fails[key]) >= MAX_FAILS:
        raise HTTPException(429, "Demasiados intentos fallidos. Intente de nuevo en unos minutos")
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not user.is_active or user.is_demo or not verify_password(data.password, user.password_hash):
        _fails[key].append(now)
        raise HTTPException(401, "Correo o contraseña incorrectos")
    _fails.pop(key, None)
    if app_settings.is_demo_mode(db):
        ensure_demo_for_user(db, user)
    return TokenOut(access_token=create_access_token(user.id, user.role), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=204)
def change_password(data: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "La contraseña actual es incorrecta")
    user.password_hash = hash_password(data.new_password)
    db.commit()
