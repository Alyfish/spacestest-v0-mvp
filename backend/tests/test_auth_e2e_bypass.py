import asyncio

import pytest
from fastapi import HTTPException

from auth import get_current_user


def test_get_current_user_allows_e2e_secret_bypass(monkeypatch):
    monkeypatch.setenv("E2E_TEST_MODE", "true")
    monkeypatch.setenv("E2E_TEST_SECRET", "auth-test-secret")
    monkeypatch.setenv("E2E_DEFAULT_USER_EMAIL", "e2e-default@spaces.local")

    user = asyncio.run(
        get_current_user(
            authorization=None,
            x_e2e_test_secret="auth-test-secret",
            x_e2e_user_id="e2e-user-123",
        )
    )

    assert user.id == "e2e-user-123"
    assert user.email == "e2e-default@spaces.local"
    assert user.role == "authenticated"


def test_get_current_user_rejects_invalid_secret_without_auth(monkeypatch):
    monkeypatch.setenv("E2E_TEST_MODE", "true")
    monkeypatch.setenv("E2E_TEST_SECRET", "auth-test-secret")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            get_current_user(
                authorization=None,
                x_e2e_test_secret="wrong-secret",
                x_e2e_user_id="e2e-user-123",
            )
        )

    assert exc_info.value.status_code == 401
    detail = exc_info.value.detail
    assert detail["error"]["code"] == "UNAUTHORIZED"
