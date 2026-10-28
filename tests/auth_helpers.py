"""Helpers for tests that exercise the real local login endpoint."""

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import AuthSettings, DEFAULT_PERMISSIONS


TEST_USERNAME = "phase8g7-test-user"
TEST_PASSWORD = "phase8g7-local-test-password"


@lru_cache(maxsize=1)
def get_test_auth_settings() -> AuthSettings:
    return AuthSettings(
        username=TEST_USERNAME,
        password_hash=PasswordHasher().hash(TEST_PASSWORD),
        permissions=DEFAULT_PERMISSIONS,
    )


def configured_test_app(**kwargs) -> FastAPI:
    kwargs.setdefault("auth_settings", get_test_auth_settings())
    return create_app(**kwargs)


@contextmanager
def authenticated_client(app: FastAPI) -> Iterator[TestClient]:
    """Log in through /auth/login and add its returned bearer to this client."""

    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client

