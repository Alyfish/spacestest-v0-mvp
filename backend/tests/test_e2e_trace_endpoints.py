from e2e_test_support import E2EConfig, E2ETraceStore
from main import app

TEST_SECRET = "trace-test-secret"


def _configure_e2e(enabled: bool, *, stub_mode: bool = False, secret: str = TEST_SECRET):
    app.state.e2e_config = E2EConfig(
        enabled=enabled,
        stub_mode=stub_mode,
        secret=secret,
        max_runs=20,
        max_events_per_run=200,
        default_user_id="e2e-trace-user",
        default_user_email="e2e-trace-user@spaces.local",
    )
    app.state.e2e_trace_store = E2ETraceStore(max_runs=20, max_events_per_run=200)


def test_e2e_status_denied_when_disabled(client):
    _configure_e2e(False)

    response = client.get(
        "/e2e/status",
        headers={"X-E2E-Test-Secret": TEST_SECRET},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["status"] == "disabled"


def test_e2e_status_denied_with_invalid_secret(client):
    _configure_e2e(True, secret=TEST_SECRET)

    response = client.get(
        "/e2e/status",
        headers={"X-E2E-Test-Secret": "wrong-secret"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["status"] == "denied"


def test_e2e_traces_record_and_clear(client):
    _configure_e2e(True, stub_mode=True, secret=TEST_SECRET)
    run_id = "trace-run-001"

    trace_headers = {
        "X-E2E-Test-Secret": TEST_SECRET,
        "X-E2E-Run-ID": run_id,
        "X-E2E-User-Id": "trace-user-1",
    }

    create_response = client.post("/projects", headers=trace_headers)
    assert create_response.status_code == 200
    project_id = create_response.json()["project_id"]

    # This may fail if no image exists yet; either way it should still be traced.
    client.get(
        f"/projects/{project_id}/auto-detect",
        params={"image_type": "product"},
        headers=trace_headers,
    )

    read_response = client.get(
        f"/e2e/traces/{run_id}",
        headers={"X-E2E-Test-Secret": TEST_SECRET},
    )
    assert read_response.status_code == 200

    payload = read_response.json()
    traces = payload["traces"]
    assert payload["status"] == "ok"
    assert payload["count"] >= 2

    assert any(
        trace["method"] == "POST" and trace["path"] == "/projects"
        for trace in traces
    )
    assert any(
        trace["method"] == "GET"
        and trace["path"] == f"/projects/{project_id}/auto-detect"
        and trace.get("query", {}).get("image_type") == "product"
        for trace in traces
    )

    clear_response = client.delete(
        f"/e2e/traces/{run_id}",
        headers={"X-E2E-Test-Secret": TEST_SECRET},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["deleted"] >= 1

    empty_response = client.get(
        f"/e2e/traces/{run_id}",
        headers={"X-E2E-Test-Secret": TEST_SECRET},
    )
    assert empty_response.status_code == 200
    assert empty_response.json()["count"] == 0

    client.delete(f"/projects/{project_id}")
