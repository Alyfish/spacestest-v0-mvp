"""
Background task executors for long-running operations.

Each executor:
1. Claims the job (atomic lock)
2. Checks for cancellation between phases
3. Updates progress
4. Executes the work
5. Stores result or error
"""

from __future__ import annotations

import asyncio
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from async_utils import timed
from job_manager import job_manager, JobType, JobStatus
from logger_config import setup_logging

logger = setup_logging()


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "item"


def _build_stub_search_result(
    project_id: str,
    recommendations: List[str],
) -> Dict[str, Any]:
    normalized = [r.strip() for r in recommendations if r and r.strip()]
    if not normalized:
        normalized = ["refresh lighting", "upgrade accent furniture"]

    categories = []
    for recommendation in normalized[:2]:
        slug = _slugify(recommendation)
        categories.append(
            {
                "recommendation": recommendation,
                "search_query": f"modern {slug.replace('_', ' ')}",
                "status": "complete",
                "products": [
                    {
                        "url": f"https://example.com/{slug}/1",
                        "title": f"{recommendation} Option 1",
                        "image_url": f"https://example.com/images/{slug}-1.jpg",
                        "store": "Target",
                        "price_str": "$129",
                        "price": 129.0,
                        "similarity_score": 0.92,
                    },
                    {
                        "url": f"https://example.com/{slug}/2",
                        "title": f"{recommendation} Option 2",
                        "image_url": f"https://example.com/images/{slug}-2.jpg",
                        "store": "Wayfair",
                        "price_str": "$179",
                        "price": 179.0,
                        "similarity_score": 0.88,
                    },
                ],
                "searched_at": datetime.utcnow().isoformat(),
                "error_message": None,
            }
        )

    return {
        "project_id": project_id,
        "categories": categories,
        "total_products": sum(len(cat["products"]) for cat in categories),
        "status": "success",
        "message": "Stub search completed for E2E",
    }


def _get_data_manager():
    """Lazy import of data_manager with feature flag support."""
    if os.getenv("USE_SUPABASE_DATA", "false").lower() == "true":
        from supabase_data_manager import data_manager
    else:
        from data_manager import data_manager
    return data_manager


async def execute_generate_image(
    job_id: str,
    project_id: str,
    use_stub: bool = False,
):
    """
    Background task for generate-image endpoint.

    Generates a product visualization using the selected product.
    """
    data_manager = _get_data_manager()
    timings: Dict[str, float] = {}
    job_start = time.perf_counter()

    try:
        async with timed("claim_and_init", timings):
            # Claim the job (atomic)
            if not await job_manager.claim_job(job_id):
                logger.warning(f"Job {job_id} already claimed or cancelled")
                return

            # 0% - Initializing
            await job_manager.update_progress(job_id, 0, "Initializing")

            # Check for cancellation
            if await job_manager.is_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled before processing")
                return

        async with timed("load_context", timings):
            # 25% - Loading context
            await job_manager.update_progress(job_id, 25, "Loading project context")

            project = data_manager.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Check for cancellation
            if await job_manager.is_cancelled(job_id):
                return

        # 50% - Generating
        await job_manager.update_progress(job_id, 50, "Generating image with AI")

        async with timed("generate", timings):
            if use_stub:
                await asyncio.sleep(0.05)
                result = {
                    "project_id": project_id,
                    "selected_products": [],
                    "generation_prompt": "Stub generation prompt for E2E",
                    "status": "success",
                    "message": "Image generated successfully (stub)",
                    "model_used": "e2e_stub",
                    "generated_image_base64": "stub",
                }
            else:
                # Run sync operation in thread pool
                result = await asyncio.to_thread(
                    data_manager.generate_product_visualization, project_id
                )

            # Check for cancellation
            if await job_manager.is_cancelled(job_id):
                return

        async with timed("process_result", timings):
            # 75% - Processing result
            await job_manager.update_progress(job_id, 75, "Processing generated image")

            # Prepare result for storage
            # Note: base64 image is stored in project context, not in job result
            total_ms = round((time.perf_counter() - job_start) * 1000, 2)
            stored_result = {
                "project_id": result.get("project_id", project_id),
                "selected_products": result.get("selected_products", []),
                "generation_prompt": result.get("generation_prompt", ""),
                "status": result.get("status", "success"),
                "message": result.get("message", "Image generated successfully"),
                "model_used": result.get("model_used"),
                "has_generated_image": bool(result.get("generated_image_base64")),
                "timings_ms": timings,
                "total_ms": total_ms,
            }

        # 100% - Complete
        await job_manager.complete_job(job_id, stored_result)
        logger.info(
            f"Job {job_id} completed: generate_image",
            extra={
                "job_id": job_id,
                "project_id": project_id,
                "extra_data": {"timings_ms": timings, "total_ms": total_ms},
            },
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(
            f"Job {job_id} failed: {e}",
            extra={"job_id": job_id, "project_id": project_id, "trace": error_trace},
        )
        await job_manager.fail_job(
            job_id,
            error=str(e),
            error_code="GENERATION_FAILED",
            error_trace=error_trace,
        )


async def execute_inspiration_redesign(
    job_id: str,
    project_id: str,
    use_stub: bool = False,
):
    """
    Background task for inspiration-redesign endpoint.

    Generates a redesigned room based on inspiration images and recommendations.
    """
    data_manager = _get_data_manager()
    timings: Dict[str, float] = {}
    job_start = time.perf_counter()

    try:
        async with timed("claim_and_init", timings):
            # Claim the job
            if not await job_manager.claim_job(job_id):
                logger.warning(f"Job {job_id} already claimed or cancelled")
                return

            # 0% - Initializing
            await job_manager.update_progress(job_id, 0, "Initializing")

            if await job_manager.is_cancelled(job_id):
                return

        async with timed("load_context", timings):
            # 20% - Loading context
            await job_manager.update_progress(job_id, 20, "Loading inspiration context")

            project = data_manager.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            if await job_manager.is_cancelled(job_id):
                return

        async with timed("prepare_prompt", timings):
            # 40% - Preparing prompt
            await job_manager.update_progress(job_id, 40, "Preparing redesign prompt")

            if await job_manager.is_cancelled(job_id):
                return

        # 60% - Generating (this is the long part)
        await job_manager.update_progress(job_id, 60, "Generating redesigned image")

        async with timed("generate", timings):
            if use_stub:
                await asyncio.sleep(0.05)
                result = {
                    "project_id": project_id,
                    "inspiration_prompt": "Stub inspiration prompt for E2E",
                    "inspiration_recommendations": [
                        "Upgrade lighting layers",
                        "Add textured statement rug",
                    ],
                    "status": "success",
                    "message": "Redesign completed successfully (stub)",
                    "model_used": "e2e_stub",
                    "generated_image_base64": "stub",
                }
            else:
                result = await asyncio.to_thread(
                    data_manager.generate_inspiration_redesign, project_id
                )

            if await job_manager.is_cancelled(job_id):
                return

        async with timed("process_result", timings):
            # 80% - Processing
            await job_manager.update_progress(job_id, 80, "Processing result")

            total_ms = round((time.perf_counter() - job_start) * 1000, 2)
            stored_result = {
                "project_id": result.get("project_id", project_id),
                "inspiration_prompt": result.get("inspiration_prompt", ""),
                "inspiration_recommendations": result.get("inspiration_recommendations", []),
                "status": result.get("status", "success"),
                "message": result.get("message", "Redesign completed successfully"),
                "model_used": result.get("model_used"),
                "has_generated_image": bool(result.get("generated_image_base64")),
                "timings_ms": timings,
                "total_ms": total_ms,
            }

        await job_manager.complete_job(job_id, stored_result)
        logger.info(
            f"Job {job_id} completed: inspiration_redesign",
            extra={
                "job_id": job_id,
                "project_id": project_id,
                "extra_data": {"timings_ms": timings, "total_ms": total_ms},
            },
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(
            f"Job {job_id} failed: {e}",
            extra={"job_id": job_id, "project_id": project_id, "trace": error_trace},
        )
        await job_manager.fail_job(
            job_id,
            error=str(e),
            error_code="REDESIGN_FAILED",
            error_trace=error_trace,
        )


async def execute_search_recommendations(
    job_id: str,
    project_id: str,
    recommendations: List[str],
    app_state: Optional[Any] = None,
    use_stub: bool = False,
):
    """
    Background task for search-recommendations endpoint.

    Searches for products matching the given recommendations.
    """
    data_manager = _get_data_manager()
    timings: Dict[str, float] = {}
    job_start = time.perf_counter()

    try:
        async with timed("claim_and_init", timings):
            # Claim the job
            if not await job_manager.claim_job(job_id):
                logger.warning(f"Job {job_id} already claimed or cancelled")
                return

            # 0% - Initializing
            await job_manager.update_progress(job_id, 0, "Initializing")

            if await job_manager.is_cancelled(job_id):
                return

        async with timed("load_context", timings):
            # 20% - Analyzing
            await job_manager.update_progress(job_id, 20, "Analyzing recommendations")

            project = data_manager.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            if await job_manager.is_cancelled(job_id):
                return

        # 40% - Searching
        await job_manager.update_progress(job_id, 40, "Searching for products")

        async with timed("search", timings):
            if use_stub:
                await asyncio.sleep(0.05)
                result = _build_stub_search_result(project_id, recommendations)
            elif (
                app_state is not None
                and hasattr(data_manager, "search_products_for_recommendations_async")
            ):
                result = await data_manager.search_products_for_recommendations_async(
                    project_id,
                    recommendations,
                    app_state,
                )
            else:
                result = await asyncio.to_thread(
                    data_manager.search_products_for_recommendations,
                    project_id,
                    recommendations,
                )

            if await job_manager.is_cancelled(job_id):
                return

        async with timed("process_result", timings):
            # 70% - Filtering
            await job_manager.update_progress(job_id, 70, "Filtering and ranking results")

            if await job_manager.is_cancelled(job_id):
                return

            # 90% - Finalizing
            await job_manager.update_progress(job_id, 90, "Finalizing product list")

            total_ms = round((time.perf_counter() - job_start) * 1000, 2)
            stored_result = {
                "project_id": project_id,
                "categories": result.get("categories", []),
                "total_products": result.get("total_products", 0),
                "status": result.get("status", "success"),
                "message": result.get("message", "Search completed"),
                "timings_ms": timings,
                "total_ms": total_ms,
            }

        await job_manager.complete_job(job_id, stored_result)
        logger.info(
            f"Job {job_id} completed: search_recommendations",
            extra={
                "job_id": job_id,
                "project_id": project_id,
                "total_products": stored_result["total_products"],
                "extra_data": {"timings_ms": timings, "total_ms": total_ms},
            },
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(
            f"Job {job_id} failed: {e}",
            extra={"job_id": job_id, "project_id": project_id, "trace": error_trace},
        )
        await job_manager.fail_job(
            job_id,
            error=str(e),
            error_code="SEARCH_FAILED",
            error_trace=error_trace,
        )
