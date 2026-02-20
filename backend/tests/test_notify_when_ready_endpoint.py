from datetime import datetime, timezone

import main
from job_manager import JobInfo

from .conftest import TEST_USER_ID


def _job_info(*, job_id: str, project_id: str, status: str) -> JobInfo:
    now = datetime.now(timezone.utc)
    return JobInfo(
        id=job_id,
        user_id=TEST_USER_ID,
        project_id=project_id,
        job_type="inspiration_redesign",
        status=status,
        progress_pct=0,
        phase="Testing",
        created_at=now,
        updated_at=now,
    )


def test_notify_when_ready_registers_pending_subscription(client, monkeypatch):
    project_id = "project-111"
    job_id = "11111111-1111-4111-8111-111111111111"
    captured = {}

    async def fake_get_job(_job_id):
        return _job_info(job_id=job_id, project_id=project_id, status="processing")

    def fake_register(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(main.data_manager, "get_project", lambda *_args, **_kwargs: {"id": project_id})
    monkeypatch.setattr(main.job_manager, "get_job", fake_get_job)
    monkeypatch.setattr("main.register_job_ready_notification", fake_register)

    response = client.post(
        f"/projects/{project_id}/jobs/{job_id}/notify-when-ready",
        json={
            "device_token": "test-token-abc-1234567890",
            "platform": "ios",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["job_id"] == job_id
    assert body["status"] == "registered"
    assert captured["job_id"] == job_id
    assert captured["project_id"] == project_id
    assert captured["user_id"] == TEST_USER_ID
    assert captured["platform"] == "ios"


def test_notify_when_ready_returns_already_done(client, monkeypatch):
    project_id = "project-222"
    job_id = "22222222-2222-4222-8222-222222222222"

    async def fake_get_job(_job_id):
        return _job_info(job_id=job_id, project_id=project_id, status="done")

    def fail_register(**_kwargs):
        raise AssertionError("register_job_ready_notification should not be called")

    monkeypatch.setattr(main.data_manager, "get_project", lambda *_args, **_kwargs: {"id": project_id})
    monkeypatch.setattr(main.job_manager, "get_job", fake_get_job)
    monkeypatch.setattr("main.register_job_ready_notification", fail_register)

    response = client.post(
        f"/projects/{project_id}/jobs/{job_id}/notify-when-ready",
        json={
            "device_token": "test-token-abc-1234567890",
            "platform": "android",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "already_done"


def test_notify_when_ready_rejects_mismatched_project(client, monkeypatch):
    project_id = "project-333"
    job_id = "33333333-3333-4333-8333-333333333333"

    async def fake_get_job(_job_id):
        return _job_info(
            job_id=job_id,
            project_id="different-project-id",
            status="processing",
        )

    monkeypatch.setattr(main.data_manager, "get_project", lambda *_args, **_kwargs: {"id": project_id})
    monkeypatch.setattr(main.job_manager, "get_job", fake_get_job)

    response = client.post(
        f"/projects/{project_id}/jobs/{job_id}/notify-when-ready",
        json={
            "device_token": "test-token-abc-1234567890",
            "platform": "ios",
        },
    )

    assert response.status_code == 404
