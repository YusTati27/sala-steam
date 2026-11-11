"""Utilidades de línea de comandos.

Crear (o promover a) administrador, pidiendo la contraseña por teclado (no queda en historial ni en archivos):

    python -m app.cli create-admin correo@dominio.com "Nombre Apellido"
"""

import getpass
import sys

from sqlalchemy import select

from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password, validate_password_strength
from app.models.entities import Role, User


def create_admin(email: str, name: str) -> int:
    Base.metadata.create_all(engine)
    email = email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role, user.is_active = Role.admin.value, True
            db.commit()
            print(f"La cuenta {email} ya existía: ahora es administrador (su contraseña no cambió).")
            return 0
        pw = getpass.getpass("Contraseña nueva (mín. 8, con letras y números): ")
        err = validate_password_strength(pw)
        if err:
            print(err)
            return 1
        if pw != getpass.getpass("Repite la contraseña: "):
            print("Las contraseñas no coinciden.")
            return 1
        db.add(User(name=name.strip(), email=email, password_hash=hash_password(pw), role=Role.admin.value))
        db.commit()
        print(f"Administrador creado: {email}")
        return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "create-admin":
        sys.exit(create_admin(sys.argv[2], sys.argv[3]))
    print(__doc__)
    sys.exit(2)
