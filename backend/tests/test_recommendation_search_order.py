import asyncio
import logging
from types import SimpleNamespace

from data_manager import DataManager
from models import ProjectContext
from supabase_data_manager import SupabaseDataManager


class _EmptySerpClient:
    def search_and_analyze_products(self, *args, **kwargs):
        return []

    def search_images(self, *args, **kwargs):
        return []


def _build_context() -> ProjectContext:
    # Keep context ordering different from payload so tests catch any
    # context-based re-selection/reordering.
    return ProjectContext.model_validate(
        {
            "product_recommendations": [
                "Replace lamp",
                "Update bedding set",
                "Add area rug",
            ],
            "style_analysis": {
                "furniture_recommendations": [
                    {"item_type": "lamp"},
                    {"item_type": "rug"},
                ]
            },
        }
    )


def _build_supabase_manager(context: ProjectContext) -> SupabaseDataManager:
    manager = SupabaseDataManager.__new__(SupabaseDataManager)
    manager.logger = logging.getLogger("test.supabase.recommendation_order")
    manager.serp_client = _EmptySerpClient()
    manager.exa_client = None
    manager._exa_exhausted = False
    manager._get_project_row = lambda project_id: {"id": project_id}
    manager._get_project_context = lambda project_id: context
    manager._save_project_fields = lambda project_id, update: None
    return manager


def _build_json_manager(context: ProjectContext) -> DataManager:
    manager = DataManager.__new__(DataManager)
    manager.logger = logging.getLogger("test.json.recommendation_order")
    manager.serp_client = _EmptySerpClient()
    manager.exa_client = None
    manager._exa_exhausted = False
    projects = {"project-1": {"context": context.model_dump()}}
    manager._load_projects = lambda: projects
    manager._save_projects = lambda updated_projects: None
    return manager


def test_supabase_sync_search_uses_first_two_request_recommendations():
    payload = ["Update bedding set", "Add area rug", "Replace lamp"]
    context = _build_context()
    manager = _build_supabase_manager(context)

    result = manager.search_products_for_recommendations("project-1", payload)

    assert [cat["recommendation"] for cat in result["categories"]] == payload[:2]


def test_json_sync_search_uses_first_two_request_recommendations():
    payload = ["Update bedding set", "Add area rug", "Replace lamp"]
    context = _build_context()
    manager = _build_json_manager(context)

    result = manager.search_products_for_recommendations("project-1", payload)

    assert [cat["recommendation"] for cat in result["categories"]] == payload[:2]


def test_supabase_async_search_uses_first_two_request_recommendations():
    payload = ["Update bedding set", "Add area rug", "Replace lamp"]
    context = _build_context()
    manager = _build_supabase_manager(context)

    async def _fake_search_single(recommendation: str, _context, _app_state):
        return {
            "recommendation": recommendation,
            "search_query": recommendation,
            "status": "complete",
            "products": [],
            "searched_at": "2026-02-14T00:00:00",
            "error_message": None,
        }

    manager.search_single_recommendation_async = _fake_search_single

    result = asyncio.run(
        manager.search_products_for_recommendations_async(
            "project-1",
            payload,
            SimpleNamespace(),
        )
    )

    assert [cat["recommendation"] for cat in result["categories"]] == payload[:2]


def test_json_async_search_uses_first_two_request_recommendations():
    payload = ["Update bedding set", "Add area rug", "Replace lamp"]
    context = _build_context()
    manager = _build_json_manager(context)

    async def _fake_search_single(recommendation: str, _context, _app_state):
        return {
            "recommendation": recommendation,
            "search_query": recommendation,
            "status": "complete",
            "products": [],
            "searched_at": "2026-02-14T00:00:00",
            "error_message": None,
        }

    manager.search_single_recommendation_async = _fake_search_single

    result = asyncio.run(
        manager.search_products_for_recommendations_async(
            "project-1",
            payload,
            SimpleNamespace(),
        )
    )

    assert [cat["recommendation"] for cat in result["categories"]] == payload[:2]
