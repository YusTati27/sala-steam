import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_env: str = "development"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'sala_steam.db').as_posix()}"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"

    local_utc_offset_hours: int = -5  # zona horaria de la sala (para agrupar por día/hora)

    # PIN para registrarse como administrador desde la pantalla de registro. Vacío = función deshabilitada.
    admin_signup_pin: str = ""

    simulator_enabled: bool = True
    sim_tick_seconds: float = 3.0
    sim_speed: float = 20.0  # minutos simulados que avanzan por minuto real

    # Opcional: crea el primer administrador al iniciar si no existe ningún usuario.
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "Administrador"

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Acepta URLs copiadas de proveedores (postgres://, postgresql://) y las adapta al driver psycopg."""
        v = v.strip()
        if not v:  # variable presente pero vacía (como en .env.example): usar SQLite local
            return f"sqlite:///{(BACKEND_DIR / 'sala_steam.db').as_posix()}"
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.jwt_secret_key:
        if s.is_production:
            raise RuntimeError("JWT_SECRET_KEY es obligatorio en producción")
        # Desarrollo: clave efímera (las sesiones se invalidan al reiniciar).
        s.jwt_secret_key = secrets.token_urlsafe(64)
    return s
