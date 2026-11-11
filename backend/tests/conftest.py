import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="sala_steam_test_"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{(_tmp / 'test.db').as_posix()}",
    JWT_SECRET_KEY="test-secret-key-only-for-tests-0123456789abcdef0123456789abcdef",
    SIMULATOR_ENABLED="false",
    ADMIN_SIGNUP_PIN="4242",
    BOOTSTRAP_ADMIN_EMAIL="admin@salasteam.dev",
    BOOTSTRAP_ADMIN_PASSWORD="Admin12345",
    APP_ENV="development",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return _login(client, "admin@salasteam.dev", "Admin12345")


@pytest.fixture(scope="session")
def mode_real(client, admin):
    """Las pruebas funcionales trabajan en modo real (base de datos vacía)."""
    assert client.post("/api/v1/config/mode", json={"mode": "real"}, headers=admin).status_code == 200


@pytest.fixture(scope="session")
def student(client, mode_real):
    r = client.post("/api/v1/auth/register", json={"name": "Ana Prueba", "email": "ana@salasteam.dev", "password": "Clave12345"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]["id"]


@pytest.fixture(scope="session")
def student2(client, mode_real):
    r = client.post("/api/v1/auth/register", json={"name": "Luis Prueba", "email": "luis@salasteam.dev", "password": "Clave12345"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]["id"]
