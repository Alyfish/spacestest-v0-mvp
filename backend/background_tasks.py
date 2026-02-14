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
import traceback
from typing import Any, Dict, List, Optional

from job_manager import job_manager, JobType, JobStatus
from logger_config import setup_logging

logger = setup_logging()


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
):
    """
    Background task for generate-image endpoint.

    Generates a product visualization using the selected product.
    """
    data_manager = _get_data_manager()

    try:
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

        # Run sync operation in thread pool
        result = await asyncio.to_thread(
            data_manager.generate_product_visualization, project_id
        )

        # Check for cancellation
        if await job_manager.is_cancelled(job_id):
            return

        # 75% - Processing result
        await job_manager.update_progress(job_id, 75, "Processing generated image")

        # Prepare result for storage
        # Note: base64 image is stored in project context, not in job result
        stored_result = {
            "project_id": result.get("project_id", project_id),
            "selected_products": result.get("selected_products", []),
            "generation_prompt": result.get("generation_prompt", ""),
            "status": result.get("status", "success"),
            "message": result.get("message", "Image generated successfully"),
            "model_used": result.get("model_used"),
            "has_generated_image": bool(result.get("generated_image_base64")),
        }

        # 100% - Complete
        await job_manager.complete_job(job_id, stored_result)
        logger.info(
            f"Job {job_id} completed: generate_image",
            extra={"job_id": job_id, "project_id": project_id},
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
):
    """
    Background task for inspiration-redesign endpoint.

    Generates a redesigned room based on inspiration images and recommendations.
    """
    data_manager = _get_data_manager()

    try:
        # Claim the job
        if not await job_manager.claim_job(job_id):
            logger.warning(f"Job {job_id} already claimed or cancelled")
            return

        # 0% - Initializing
        await job_manager.update_progress(job_id, 0, "Initializing")

        if await job_manager.is_cancelled(job_id):
            return

        # 20% - Loading context
        await job_manager.update_progress(job_id, 20, "Loading inspiration context")

        project = data_manager.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        if await job_manager.is_cancelled(job_id):
            return

        # 40% - Preparing prompt
        await job_manager.update_progress(job_id, 40, "Preparing redesign prompt")

        if await job_manager.is_cancelled(job_id):
            return

        # 60% - Generating (this is the long part)
        await job_manager.update_progress(job_id, 60, "Generating redesigned image")

        result = await asyncio.to_thread(
            data_manager.generate_inspiration_redesign, project_id
        )

        if await job_manager.is_cancelled(job_id):
            return

        # 80% - Processing
        await job_manager.update_progress(job_id, 80, "Processing result")

        stored_result = {
            "project_id": result.get("project_id", project_id),
            "inspiration_prompt": result.get("inspiration_prompt", ""),
            "inspiration_recommendations": result.get("inspiration_recommendations", []),
            "status": result.get("status", "success"),
            "message": result.get("message", "Redesign completed successfully"),
            "model_used": result.get("model_used"),
            "has_generated_image": bool(result.get("generated_image_base64")),
        }

        await job_manager.complete_job(job_id, stored_result)
        logger.info(
            f"Job {job_id} completed: inspiration_redesign",
            extra={"job_id": job_id, "project_id": project_id},
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
):
    """
    Background task for search-recommendations endpoint.

    Searches for products matching the given recommendations.
    """
    data_manager = _get_data_manager()

    try:
        # Claim the job
        if not await job_manager.claim_job(job_id):
            logger.warning(f"Job {job_id} already claimed or cancelled")
            return

        # 0% - Initializing
        await job_manager.update_progress(job_id, 0, "Initializing")

        if await job_manager.is_cancelled(job_id):
            return

        # 20% - Analyzing
        await job_manager.update_progress(job_id, 20, "Analyzing recommendations")

        project = data_manager.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        if await job_manager.is_cancelled(job_id):
            return

        # 40% - Searching
        await job_manager.update_progress(job_id, 40, "Searching for products")

        if (
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

        # 70% - Filtering
        await job_manager.update_progress(job_id, 70, "Filtering and ranking results")

        if await job_manager.is_cancelled(job_id):
            return

        # 90% - Finalizing
        await job_manager.update_progress(job_id, 90, "Finalizing product list")

        stored_result = {
            "project_id": project_id,
            "categories": result.get("categories", []),
            "total_products": result.get("total_products", 0),
            "status": result.get("status", "success"),
            "message": result.get("message", "Search completed"),
        }

        await job_manager.complete_job(job_id, stored_result)
        logger.info(
            f"Job {job_id} completed: search_recommendations",
            extra={
                "job_id": job_id,
                "project_id": project_id,
                "total_products": stored_result["total_products"],
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
