import httpx


def test_get_project_context_retries_remote_protocol_error(monkeypatch):
    from supabase_data_manager import SupabaseDataManager

    attempts = {"count": 0}

    def fake_get_project_row(project_id: str):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.RemoteProtocolError("Server disconnected")
        return {"id": project_id}

    def fake_row_to_project_dict(row: dict):
        return {
            "context": {
                "base_image": "https://example.com/base.jpg",
                "space_type": "bedroom",
                "improvement_mode": "iterative",
            }
        }

    dm = SupabaseDataManager.__new__(SupabaseDataManager)
    monkeypatch.setattr(dm, "_get_project_row", fake_get_project_row, raising=False)
    monkeypatch.setattr(dm, "_row_to_project_dict", fake_row_to_project_dict, raising=False)

    context = dm._get_project_context("project_retry_test")

    assert context.space_type == "bedroom"
    assert attempts["count"] == 2
