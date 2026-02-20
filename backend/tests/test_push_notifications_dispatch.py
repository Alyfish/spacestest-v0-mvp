import push_notifications


def _disable_supabase(monkeypatch):
    monkeypatch.setattr(push_notifications, "_get_supabase_or_none", lambda: None)


def _reset_memory_store():
    push_notifications._in_memory_notifications.clear()  # noqa: SLF001


def test_register_notification_is_idempotent(monkeypatch):
    _disable_supabase(monkeypatch)
    _reset_memory_store()

    push_notifications.register_job_ready_notification(
        job_id="job-1",
        project_id="project-1",
        user_id="user-1",
        device_token="token-1",
        platform="ios",
    )
    push_notifications.register_job_ready_notification(
        job_id="job-1",
        project_id="project-1",
        user_id="user-1",
        device_token="token-1",
        platform="android",
    )

    pending = push_notifications.get_pending_job_ready_notifications("job-1")
    assert len(pending) == 1
    assert pending[0]["platform"] == "android"
    assert pending[0]["status"] == "pending"


def test_dispatch_marks_notification_sent(monkeypatch):
    _disable_supabase(monkeypatch)
    _reset_memory_store()

    push_notifications.register_job_ready_notification(
        job_id="job-2",
        project_id="project-2",
        user_id="user-2",
        device_token="token-2",
        platform="ios",
    )

    monkeypatch.setattr(
        push_notifications,
        "send_design_ready_push",
        lambda **_kwargs: {"name": "projects/test/messages/123"},
    )

    summary = push_notifications.dispatch_job_ready_notifications("job-2", "project-2")

    assert summary == {"total": 1, "sent": 1, "failed": 0}
    rows = list(push_notifications._in_memory_notifications.values())  # noqa: SLF001
    assert rows[0]["status"] == "sent"
    assert rows[0]["sent_at"] is not None
    assert rows[0]["last_error"] is None


def test_dispatch_marks_notification_failed_when_send_errors(monkeypatch):
    _disable_supabase(monkeypatch)
    _reset_memory_store()

    push_notifications.register_job_ready_notification(
        job_id="job-3",
        project_id="project-3",
        user_id="user-3",
        device_token="token-3",
        platform="android",
    )

    def _raise_send_error(**_kwargs):
        raise RuntimeError("FCM_PROJECT_ID is not configured")

    monkeypatch.setattr(push_notifications, "send_design_ready_push", _raise_send_error)

    summary = push_notifications.dispatch_job_ready_notifications("job-3", "project-3")

    assert summary == {"total": 1, "sent": 0, "failed": 1}
    rows = list(push_notifications._in_memory_notifications.values())  # noqa: SLF001
    assert rows[0]["status"] == "failed"
    assert "FCM_PROJECT_ID is not configured" in rows[0]["last_error"]
