from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.v1.auth import check_admin_pin
from app.core.db import get_db
from app.core.deps import demo_flag, require_admin
from app.core.security import hash_password
from app.models.entities import Role, User
from app.schemas.user import ResetPasswordIn, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserOut])
def list_users(q: str | None = None, role: Role | None = None, demo: bool = Depends(demo_flag), db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.is_demo, User.name)
    if not demo:
        stmt = stmt.where(User.is_demo.is_(False))
    if role:
        stmt = stmt.where(User.role == role.value)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    return list(db.scalars(stmt))


@router.post("", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    if data.role == Role.admin:
        check_admin_pin(request, data.admin_pin or "")
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Ya existe una cuenta con ese correo")
    user = User(name=data.name.strip(), email=email, password_hash=hash_password(data.password), role=data.role.value)
    db.add(user)
    db.commit()
    return user


def _get(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    return u


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, request: Request, me: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = _get(db, user_id)
    if data.role == Role.admin and u.role != Role.admin.value:
        check_admin_pin(request, data.admin_pin or "")
    if u.is_demo:
        raise HTTPException(409, "Los usuarios de demostración no se pueden modificar")
    if u.id == me.id and ((data.role and data.role != Role.admin) or data.is_active is False):
        raise HTTPException(409, "No puede quitarse su propio rol de administrador ni desactivarse")
    if data.name is not None:
        u.name = data.name.strip()
    if data.role is not None:
        u.role = data.role.value
    if data.is_active is not None:
        u.is_active = data.is_active
    db.commit()
    return u


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(user_id: int, data: ResetPasswordIn, db: Session = Depends(get_db)):
    u = _get(db, user_id)
    if u.is_demo:
        raise HTTPException(409, "Los usuarios de demostración no tienen acceso")
    u.password_hash = hash_password(data.new_password)
    db.commit()
