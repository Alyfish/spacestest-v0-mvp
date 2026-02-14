"""
Shared pytest fixtures for backend API tests.

Auth is bypassed via FastAPI dependency override — all tests run
as a fixed test user without needing a real Supabase JWT.
"""

import io
import os
import sys
from pathlib import Path

import pytest
from PIL import Image
from fastapi.testclient import TestClient

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import get_current_user, AuthenticatedUser
from main import app

# Fixed test user — never collides with real users
TEST_USER_ID = "00000000-aaaa-bbbb-cccc-test00000001"
TEST_USER_EMAIL = "test-runner@spaces-ai.local"


async def _mock_current_user() -> AuthenticatedUser:
    """Auth bypass: returns a deterministic test user."""
    return AuthenticatedUser(
        id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        role="authenticated",
    )


@pytest.fixture(scope="session", autouse=True)
def override_auth():
    """Replace real JWT verification with a no-op for the entire test session."""
    app.dependency_overrides[get_current_user] = _mock_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient — shared across all tests in the session."""
    with TestClient(app, root_path="/api") as c:
        yield c


@pytest.fixture()
def test_image_bytes() -> bytes:
    """Create a minimal valid JPEG in memory (100×100 solid blue)."""
    img = Image.new("RGB", (100, 100), color=(70, 130, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture()
def project_id(client):
    """
    Create a project, yield its ID, delete it after the test.
    Ensures every test gets a clean, isolated project.
    """
    resp = client.post("/projects")
    assert resp.status_code == 200, f"Failed to create project: {resp.text}"
    pid = resp.json()["project_id"]
    yield pid
    # Teardown — best-effort delete
    client.delete(f"/projects/{pid}")


@pytest.fixture()
def project_with_image(client, project_id, test_image_bytes):
    """
    A project that already has a base image uploaded.
    Yields the project_id.
    """
    resp = client.post(
        f"/projects/{project_id}/upload-image",
        files={"image": ("test_room.jpg", test_image_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200, f"Image upload failed: {resp.text}"
    return project_id


@pytest.fixture()
def project_with_space(client, project_with_image):
    """
    A project with image + space type set to 'bedroom'.
    Yields the project_id.
    """
    resp = client.post(
        f"/projects/{project_with_image}/space-type",
        json={"space_type": "bedroom"},
    )
    assert resp.status_code == 200, f"Space type selection failed: {resp.text}"
    return project_with_image
