"""Test fixtures. These are integration-style: they run against a real
Postgres+PostGIS (the `postgis` compose service). Run with:

    docker compose exec api pytest -q

Set TEST_DATABASE_URL to point at a throwaway database if you don't want tests
touching your dev data.
"""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Allow overriding the DB before app modules read settings.
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from app.core.roles import RoleEnum  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.user_service import UserService  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(engine, checkfirst=True)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def admin_token(client: TestClient) -> str:
    """Create an administrator directly (self-registration can't grant admin)."""
    email = f"admin_{uuid.uuid4().hex[:12]}@example.com"
    password = "admin-password-123"
    with SessionLocal() as db:
        UserService(db).create_user(
            name="Admin", email=email, password=password, role=RoleEnum.ADMINISTRATOR
        )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"]
