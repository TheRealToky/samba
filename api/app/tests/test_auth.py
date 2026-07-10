from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str, password: str = "password123") -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == email
    assert body["role"] == "student_public"  # least-privileged default


def test_register_login_me_roundtrip(client: TestClient, unique_email: str) -> None:
    _register(client, unique_email)

    # duplicate registration is rejected
    dup = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": unique_email, "password": "password123"},
    )
    assert dup.status_code == 409

    # wrong password
    bad = client.post(
        "/api/v1/auth/login", data={"username": unique_email, "password": "wrong"}
    )
    assert bad.status_code == 401

    # correct login
    ok = client.post(
        "/api/v1/auth/login", data={"username": unique_email, "password": "password123"}
    )
    assert ok.status_code == 200
    token = ok.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == unique_email


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_rbac_admin_only(client: TestClient, unique_email: str, admin_token: str) -> None:
    # A normal user cannot list users.
    _register(client, unique_email)
    user_token = client.post(
        "/api/v1/auth/login", data={"username": unique_email, "password": "password123"}
    ).json()["access_token"]

    forbidden = client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert forbidden.status_code == 403

    # An administrator can.
    allowed = client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert allowed.status_code == 200
    assert isinstance(allowed.json(), list)
