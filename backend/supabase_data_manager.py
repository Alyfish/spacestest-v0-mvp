"""
Supabase-backed DataManager — drop-in replacement for DataManager.

Same public interface as data_manager.DataManager, but reads/writes from
Supabase PostgreSQL + Storage instead of data/projects.json + data/images/.

Toggle via USE_SUPABASE_DATA=true environment variable.
Follows the dual-storage + feature flag pattern from job_manager.py.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import logging
import os
import random
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import UploadFile

from logger_config import (
    log_api_call,
    log_external_api_call,
    log_project_status_change,
    log_user_action,
    setup_logging,
)
from models import ImprovementMarker, ProjectContext, ClipRect
from retry import retry_sync
from supabase_client import get_supabase_client, is_supabase_configured

logger = setup_logging()

# Same status ordering as data_manager.py
STATUS_ORDER = [
    "NEW",
    "BASE_IMAGE_UPLOADED",
    "SPACE_TYPE_SELECTED",
    "IMPROVEMENT_MARKERS_SAVED",
    "MARKER_RECOMMENDATIONS_READY",
    "INSPIRATION_IMAGES_UPLOADED",
    "INSPIRATION_RECOMMENDATIONS_READY",
    "PRODUCT_RECOMMENDATIONS_READY",
    "PRODUCT_RECOMMENDATION_SELECTED",
    "PRODUCT_SEARCH_COMPLETE",
    "PRODUCT_SELECTED",
    "IMAGE_GENERATED",
    "INSPIRATION_REDESIGN_COMPLETE",
]
MARKERS_SAVED_STATUS = "IMPROVEMENT_MARKERS_SAVED"

STORAGE_BUCKET = "project-images"


class SupabaseDataManager:
    """
    Supabase-backed data manager with the same public interface as DataManager.

    All AI client calls are identical to DataManager — only the data access
    layer changes from JSON file I/O to Supabase table queries.
    """

    def __init__(self):
        self.logger = logging.getLogger("spaces_ai")

        # Initialize Supabase client
        if not is_supabase_configured():
            raise RuntimeError(
                "SupabaseDataManager requires SUPABASE_URL and SUPABASE_SERVICE_KEY. "
                "Set USE_SUPABASE_DATA=false to use JSON file storage instead."
            )
        self._supabase = get_supabase_client()
        self.logger.info("SupabaseDataManager initialized with Supabase storage")

        # Initialize AI clients — same as DataManager.__init__ (data_manager.py:53-100)
        from gemini_client import GeminiClient

        self.gemini_client = GeminiClient()

        try:
            from serp_client import SerpClient
            self.serp_client = SerpClient()
            self.logger.info("Successfully initialized SERP client")
        except Exception as e:
            self.logger.warning(f"Could not initialize SERP client: {e}")
            self.serp_client = None

        self._exa_exhausted = False  # Set True on 402 to skip further Exa calls

        try:
            from exa_client import ExaClient
            self.exa_client = ExaClient()
            self.logger.info("Successfully initialized Exa client")
        except Exception as e:
            self.logger.warning(f"Exa client not available: {e}")
            self.exa_client = None

        try:
            from clip_client import CLIPClient
            self.clip_client = CLIPClient()
            if self.clip_client.is_available():
                self.logger.info("Successfully initialized CLIP client")
            else:
                self.logger.warning("CLIP client initialized but model not available")
                self.clip_client = None
        except Exception as e:
            self.logger.warning(f"Could not initialize CLIP client: {e}")
            self.clip_client = None

        try:
            from openai_client import OpenAIClient
            self.openai_client = OpenAIClient()
        except Exception as e:
            self.logger.warning(f"OpenAI client not available: {e}")
            self.openai_client = None

        try:
            from affiliate_client import AffiliateClient
            self.affiliate_client = AffiliateClient()
        except Exception:
            self.affiliate_client = None

    # =========================================================================
    # STORAGE PRIMITIVES (replace _load_projects/_save_projects)
    # =========================================================================

    def _get_project_row(self, project_id: str) -> Optional[dict]:
        """Fetch a single project row from Supabase."""
        result = (
            self._supabase.table("projects")
            .select("*")
            .eq("id", project_id)
            .maybe_single()
            .execute()
        )
        return result.data if result.data else None

    def _save_project_fields(self, project_id: str, updates: dict) -> None:
        """Update specific columns on a project row."""
        self._supabase.table("projects").update(updates).eq("id", project_id).execute()

    def _row_to_project_dict(self, row: dict) -> dict:
        """
        Convert a Supabase row to the legacy project dict format.

        Returns the shape that main.py expects:
        {
            "user_id": str,
            "status": str,
            "created_at": str,
            "context": { ProjectContext fields }
        }

        This is a transitional adapter — long-term, endpoints should work
        with the flat DB row directly.
        """
        project_id = str(row["id"])

        # Fetch markers from separate table
        markers_result = (
            self._supabase.table("improvement_markers")
            .select("*")
            .eq("project_id", project_id)
            .order("sort_order")
            .execute()
        )
        markers = [
            ImprovementMarker(
                id=m["marker_id"],
                position={"x": m["position_x"], "y": m["position_y"]},
                description=m["description"],
                color=m["color"],
            )
            for m in (markers_result.data or [])
        ]

        # Fetch image URLs from project_images table
        images_result = (
            self._supabase.table("project_images")
            .select("image_type, public_url, sort_order")
            .eq("project_id", project_id)
            .order("sort_order")
            .execute()
        )
        images_by_type: Dict[str, List[str]] = {}
        for img in (images_result.data or []):
            img_type = img["image_type"]
            if img_type not in images_by_type:
                images_by_type[img_type] = []
            images_by_type[img_type].append(img["public_url"])

        # Build ProjectContext from row columns + related tables
        context = ProjectContext(
            # Image paths/URLs
            base_image=images_by_type.get("base", [None])[0],
            labelled_base_image=images_by_type.get("labelled", [None])[0],
            inspiration_images=images_by_type.get("inspiration", []),
            generated_image_base64=images_by_type.get("generated", [None])[0],
            inspiration_generated_image_base64=images_by_type.get("inspiration_generated", [None])[0],
            # Scalars
            is_base_image_empty_room=row.get("is_base_image_empty_room"),
            improvement_mode=row.get("improvement_mode"),
            space_type=row.get("space_type"),
            inspiration_images_skipped=row.get("inspiration_images_skipped", False),
            color_analysis_skipped=row.get("color_analysis_skipped", False),
            style_analysis_skipped=row.get("style_analysis_skipped", False),
            # Markers from related table
            improvement_markers=markers,
            # String arrays
            marker_recommendations=row.get("marker_recommendations") or [],
            inspiration_recommendations=row.get("inspiration_recommendations") or [],
            product_recommendations=row.get("product_recommendations") or [],
            selected_product_recommendations=row.get("selected_product_recommendations") or [],
            preferred_stores=row.get("preferred_stores") or [],
            # JSONB columns
            color_analysis=row.get("color_analysis"),
            style_analysis=row.get("style_analysis"),
            color_scheme=row.get("color_scheme"),
            design_style=row.get("design_style"),
            pre_searched_categories=row.get("pre_searched_categories") or {},
            product_search_results=row.get("product_search_results") or [],
            selected_products=row.get("selected_products") or [],
            favorite_products=row.get("favorite_products") or [],
            selected_trending_products=row.get("selected_trending_products") or [],
            # Generation metadata
            generation_prompt=row.get("generation_prompt"),
            generation_model_used=row.get("generation_model_used"),
            inspiration_generation_prompt=row.get("inspiration_generation_prompt"),
            inspiration_model_used=row.get("inspiration_model_used"),
        )

        return {
            "user_id": str(row["user_id"]),
            "status": row["status"],
            "created_at": row.get("created_at", ""),
            "context": context.model_dump(),
        }

    def _get_project_context(self, project_id: str) -> ProjectContext:
        """Shorthand: fetch row and return ProjectContext."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        project_dict = self._row_to_project_dict(row)
        return ProjectContext.model_validate(project_dict["context"])

    def _get_project_status(self, project_id: str) -> str:
        """Fetch just the status column."""
        result = (
            self._supabase.table("projects")
            .select("status")
            .eq("id", project_id)
            .maybe_single()
            .execute()
        )
        if not result.data:
            raise ValueError(f"Project {project_id} not found")
        return result.data["status"]

    # =========================================================================
    # IMAGE HELPERS
    # =========================================================================

    def _upload_to_storage(
        self,
        project_id: str,
        user_id: str,
        image_type: str,
        file_bytes: bytes,
        filename: str,
        mime_type: str = "image/png",
        sort_order: int = 0,
    ) -> str:
        """Upload bytes to Supabase Storage and record in project_images table.

        Returns:
            Public URL of the uploaded file.
        """
        storage_path = f"{project_id}/{image_type}/{filename}"

        # Upload to storage bucket
        self._supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            file_bytes,
            {"content-type": mime_type},
        )

        # Get public URL
        public_url = self._supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

        # Record in project_images table
        self._supabase.table("project_images").insert(
            {
                "project_id": project_id,
                "user_id": user_id,
                "image_type": image_type,
                "storage_path": storage_path,
                "public_url": public_url,
                "original_filename": filename,
                "mime_type": mime_type,
                "file_size_bytes": len(file_bytes),
                "sort_order": sort_order,
            }
        ).execute()

        return public_url

    def _get_image_url(self, project_id: str, image_type: str) -> Optional[str]:
        """Get the public URL for a project image by type."""
        result = (
            self._supabase.table("project_images")
            .select("public_url")
            .eq("project_id", project_id)
            .eq("image_type", image_type)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["public_url"]
        return None

    def _get_image_urls(self, project_id: str, image_type: str) -> List[str]:
        """Get all public URLs for a project image type (e.g. inspiration images)."""
        result = (
            self._supabase.table("project_images")
            .select("public_url")
            .eq("project_id", project_id)
            .eq("image_type", image_type)
            .order("sort_order")
            .execute()
        )
        return [r["public_url"] for r in (result.data or [])]

    def _delete_project_storage(self, project_id: str) -> None:
        """Delete all Storage files for a project (cascade only clears DB rows)."""
        images_result = (
            self._supabase.table("project_images")
            .select("storage_path")
            .eq("project_id", project_id)
            .execute()
        )
        paths = [img["storage_path"] for img in (images_result.data or [])]
        if paths:
            self._supabase.storage.from_(STORAGE_BUCKET).remove(paths)
            self.logger.info(f"Deleted {len(paths)} storage files for project {project_id}")

    def _download_image_to_tempfile(self, url: str, suffix: str = ".png") -> str:
        """Download an image URL to a temp file. Returns temp file path.

        Caller is responsible for cleanup (os.unlink).
        """
        import httpx

        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name

    # =========================================================================
    # UTILITY METHODS (mirrored from DataManager)
    # =========================================================================

    def _status_rank(self, status: str) -> int:
        """Return ordering index for statuses."""
        try:
            return STATUS_ORDER.index(status)
        except ValueError:
            return len(STATUS_ORDER)

    def _ready_for_marker_recommendations(self, context: ProjectContext) -> bool:
        """Check if we have enough design context to generate marker recommendations."""
        return (
            context.base_image is not None
            and context.space_type is not None
            and len(context.improvement_markers) > 0
            and context.labelled_base_image is not None
            and (bool(context.color_analysis) or context.color_analysis_skipped)
            and (bool(context.style_analysis) or context.style_analysis_skipped)
            and bool(context.preferred_stores)
        )

    def _check_room_emptiness(self, image_path: str) -> bool:
        """Check if the uploaded image shows an empty room using AI analysis."""
        try:
            from pydantic import BaseModel

            class RoomEmptinessCheck(BaseModel):
                is_empty: bool
                confidence: float
                reasoning: str

            result = self.gemini_client.analyze_image_with_vision(
                prompt="Analyze this room image and determine if it's empty. Consider furniture, decorations, and general room contents.",
                pydantic_model=RoomEmptinessCheck,
                image_path=image_path,
                system_message="You are an expert at analyzing room images. Determine if a room is empty based on the presence of furniture, decorations, or other items. Be conservative - if there's any significant furniture or decoration, consider it not empty.",
            )
            return result.is_empty
        except Exception as e:
            self.logger.error(f"Error checking room emptiness: {e}")
            return False

    def _pil_to_base64(self, image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string."""
        buffer = BytesIO()
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _generate_marker_recommendations(
        self,
        space_type: str,
        markers: List[ImprovementMarker],
        labelled_image_path: str,
        context: ProjectContext,
    ) -> List[str]:
        """Generate AI recommendations based on improvement markers.

        Same logic as DataManager._generate_marker_recommendations.
        """
        try:
            from pydantic import BaseModel

            class AIRecommendationResponse(BaseModel):
                recommendations: List[str]

            color_palette = context.color_analysis.get("palette_name") if context.color_analysis else None
            primary_colors = context.color_analysis.get("primary_colors") if context.color_analysis else None
            style_name = context.style_analysis.get("style_name") if context.style_analysis else None
            style_materials = context.style_analysis.get("materials") if context.style_analysis else None
            preferred_stores = context.preferred_stores or []

            marker_info = "\n".join(
                [
                    f"Marker {i + 1} ({marker.color}): {marker.description}"
                    for i, marker in enumerate(markers)
                ]
            )

            prompt = f"""
            Analyze the BASE ROOM IMAGE and provide specific interior design recommendations based on the user's improvement markers.

            Space Type: {space_type}
            Color Palette: {color_palette or "Not provided"}
            Primary Colors (guidance): {primary_colors or "Not provided"}
            Design Style: {style_name or "Not provided"}
            Style Materials: {style_materials or "Not provided"}
            Preferred Stores: {preferred_stores or "Not provided"}

            User's Improvement Requests:
            {marker_info}

            Provide specific, actionable recommendations as bullet points. Each recommendation should:
            - Be specific about what to change and where
            - Reference the marker locations in the image
            - Include practical suggestions for furniture, decor, or layout changes
            - Align with the given color palette and design style
            - Favor items that could realistically be sourced from the preferred stores listed
            - Be written in a clear, actionable format
            - Keep outputs concise (1-2 sentences each)

            IMPORTANT: Return exactly 6 recommendations, each as a simple string that clearly states what to do and where.
            """

            result = self.gemini_client.analyze_image_with_vision(
                prompt=prompt,
                pydantic_model=AIRecommendationResponse,
                image_path=labelled_image_path,
                system_message="You are an expert interior designer. Provide specific, actionable recommendations for improving spaces based on user feedback. Focus on practical changes that can be easily implemented, aligned to the provided color palette, design style, and preferred stores. Always return exactly 4 recommendations.",
            )

            recs = (result.recommendations or [])[:6]
            while len(recs) < 6:
                recs.append("Add a cohesive accent that matches the selected style and palette")
            return recs

        except Exception as e:
            self.logger.error(f"Error generating marker recommendations: {e}", exc_info=True)
            return [
                "Add a statement piece at marker 1 to create a focal point",
                "Improve lighting in the area marked with marker 2",
                "Add texture and visual interest at marker 3",
            ]

    def _try_generate_marker_recommendations(self, project_id: str) -> None:
        """Generate marker recommendations once style/color/stores are set."""
        row = self._get_project_row(project_id)
        if not row:
            return

        project_dict = self._row_to_project_dict(row)
        context = ProjectContext.model_validate(project_dict["context"])

        # Already generated
        if row["status"] == "MARKER_RECOMMENDATIONS_READY" and (row.get("marker_recommendations") or []):
            return

        # Avoid downgrading projects that have progressed beyond marker recommendations
        allowed_statuses = {
            "SPACE_TYPE_SELECTED",
            MARKERS_SAVED_STATUS,
            "MARKER_RECOMMENDATIONS_READY",
        }
        if row["status"] not in allowed_statuses:
            return

        if not self._ready_for_marker_recommendations(context):
            return

        # For marker recommendations, we need a local image file for Gemini vision
        labelled_url = context.labelled_base_image
        if not labelled_url:
            self.logger.warning(f"No labelled image for project {project_id}")
            return

        # Download from Storage to temp file if it's a URL
        if labelled_url.startswith("http"):
            tmp_path = self._download_image_to_tempfile(labelled_url, suffix=".png")
        else:
            tmp_path = labelled_url
            if not Path(tmp_path).exists():
                self.logger.warning(f"Labelled image not found at {tmp_path}")
                return

        try:
            recs = self._generate_marker_recommendations(
                context.space_type or "space",
                context.improvement_markers,
                tmp_path,
                context,
            )

            self._save_project_fields(project_id, {
                "marker_recommendations": recs,
                "status": "MARKER_RECOMMENDATIONS_READY",
            })
        finally:
            # Clean up temp file if we downloaded it
            if labelled_url.startswith("http") and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # =========================================================================
    # GROUP A: CORE CRUD
    # =========================================================================

    def create_project(self, user_id: str) -> str:
        """Create a new project and return its ID."""
        project_id = str(uuid.uuid4())

        self._supabase.table("projects").insert(
            {
                "id": project_id,
                "user_id": user_id,
                "status": "NEW",
            }
        ).execute()

        self.logger.info(
            "Created new project",
            extra={"project_id": project_id, "user_id": user_id, "status": "NEW"},
        )
        log_user_action("project_created", project_id=project_id, user_id=user_id)
        return project_id

    @retry_sync(max_retries=2, base_delay=0.5, exponential_base=2.0)
    def get_project(self, project_id: str, user_id: str | None = None) -> dict | None:
        """Get a project by ID with optional ownership verification."""
        from errors import forbidden_error

        row = self._get_project_row(project_id)
        if not row:
            return None

        if user_id:
            if str(row["user_id"]) != user_id:
                raise forbidden_error(f"Access denied to project {project_id}")

        return self._row_to_project_dict(row)

    def get_all_projects(self, user_id: str | None = None) -> dict:
        """Get all projects, optionally filtered by user."""
        query = self._supabase.table("projects").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        query = query.order("created_at", desc=True)
        result = query.execute()

        return {
            str(row["id"]): self._row_to_project_dict(row)
            for row in (result.data or [])
        }

    def delete_project(self, project_id: str, user_id: str | None = None) -> bool:
        """Delete a project, its storage files, and all related data."""
        from errors import forbidden_error

        row = self._get_project_row(project_id)
        if not row:
            return False

        if user_id:
            if str(row["user_id"]) != user_id:
                raise forbidden_error(f"Access denied to project {project_id}")

        # 1. Delete Storage files first (DB cascade won't do this)
        self._delete_project_storage(project_id)

        # 2. Delete from DB (CASCADE handles project_images, markers rows)
        self._supabase.table("projects").delete().eq("id", project_id).execute()

        self.logger.info(f"Deleted project {project_id}")
        log_user_action("project_deleted", project_id=project_id, user_id=user_id)
        return True

    # =========================================================================
    # GROUP B: SIMPLE CONTEXT UPDATES
    # =========================================================================

    def select_space_type(self, project_id: str, space_type: str) -> str:
        """Select space type for a project and update status."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        self._save_project_fields(project_id, {
            "space_type": space_type,
            "status": "SPACE_TYPE_SELECTED",
        })
        return space_type

    def set_improvement_mode(self, project_id: str, mode: str) -> str:
        """Set the improvement mode for a project (iterative or complete_revamp)."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        if mode not in ("iterative", "complete_revamp", "inspiration"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'iterative', 'complete_revamp', or 'inspiration'")

        self._save_project_fields(project_id, {"improvement_mode": mode})
        self.logger.info(f"Set improvement mode to '{mode}' for project {project_id}")
        return mode

    def skip_color_analysis(self, project_id: str) -> None:
        """Skip color analysis for a project to unblock downstream steps."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        self._save_project_fields(project_id, {
            "color_analysis": None,
            "color_scheme": None,
            "color_analysis_skipped": True,
        })
        self._try_generate_marker_recommendations(project_id)

    def skip_style_analysis(self, project_id: str) -> None:
        """Skip style analysis for a project to unblock downstream steps."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        self._save_project_fields(project_id, {
            "style_analysis": None,
            "design_style": None,
            "style_analysis_skipped": True,
        })
        self._try_generate_marker_recommendations(project_id)

    def skip_inspiration_images(self, project_id: str) -> None:
        """Skip inspiration images to unblock downstream steps."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        self._save_project_fields(project_id, {
            "inspiration_images_skipped": True,
            "inspiration_recommendations": [],
        })

    def update_preferred_stores(self, project_id: str, stores: List[str]) -> List[str]:
        """Update the list of preferred retail stores in the project context."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        self._save_project_fields(project_id, {"preferred_stores": stores})
        self._try_generate_marker_recommendations(project_id)
        return stores

    def set_favorite_products(
        self, project_id: str, favorites: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Save user's selected favorite products from the 'Like These?' screen."""
        self.logger.info(
            "Saving favorite products",
            extra={"project_id": project_id, "count": len(favorites)},
        )

        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        validated_favorites = []
        for fav in favorites:
            validated_favorites.append({
                "category": fav.get("category", ""),
                "url": fav.get("url", ""),
                "title": fav.get("title", ""),
                "image_url": fav.get("image_url", ""),
                "store": fav.get("store", ""),
                "price_str": fav.get("price_str"),
            })

        self._save_project_fields(project_id, {"favorite_products": validated_favorites})

        favorites_by_category: Dict[str, int] = {}
        for fav in validated_favorites:
            cat = fav.get("category", "unknown")
            favorites_by_category[cat] = favorites_by_category.get(cat, 0) + 1

        self.logger.info(
            "Favorite products saved successfully",
            extra={"project_id": project_id, "count": len(validated_favorites), "by_category": favorites_by_category},
        )

        return {
            "project_id": project_id,
            "favorites_count": len(validated_favorites),
            "favorites_by_category": favorites_by_category,
            "status": "success",
            "message": f"Saved {len(validated_favorites)} favorite products",
        }

    def set_selected_trending_products(
        self, project_id: str, products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Save user's selected trending products for image generation."""
        self.logger.info(
            "Saving selected trending products",
            extra={"project_id": project_id, "count": len(products)},
        )

        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        validated = []
        for p in products:
            validated.append({
                "category": p.get("category", ""),
                "url": p.get("url", ""),
                "title": p.get("title", ""),
                "image_url": p.get("image_url", ""),
                "store": p.get("store", ""),
                "price_str": p.get("price_str"),
            })

        self._save_project_fields(project_id, {"selected_trending_products": validated})

        by_category: Dict[str, int] = {}
        for p in validated:
            cat = p.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "project_id": project_id,
            "trending_count": len(validated),
            "by_category": by_category,
            "status": "success",
            "message": f"Saved {len(validated)} trending products",
        }

    def trigger_marker_recommendations(self, project_id: str) -> List[str]:
        """Explicitly generate marker-based recommendations after gating criteria are met."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        project_dict = self._row_to_project_dict(row)
        context = ProjectContext.model_validate(project_dict["context"])

        if not self._ready_for_marker_recommendations(context):
            raise ValueError(
                "Project is not ready for marker recommendations. "
                "Please ensure base image, space type, labelled markers, "
                "color analysis, style analysis, and preferred stores are set."
            )

        labelled_url = context.labelled_base_image
        if not labelled_url:
            raise ValueError("Labelled image not found")

        if labelled_url.startswith("http"):
            tmp_path = self._download_image_to_tempfile(labelled_url, suffix=".png")
        else:
            tmp_path = labelled_url
            if not Path(tmp_path).exists():
                raise ValueError(f"Labelled image not found at {tmp_path}")

        try:
            recs = self._generate_marker_recommendations(
                context.space_type or "space",
                context.improvement_markers,
                tmp_path,
                context,
            )

            updates: dict = {"marker_recommendations": recs}
            current_rank = self._status_rank(row["status"])
            marker_rank = self._status_rank("MARKER_RECOMMENDATIONS_READY")
            if current_rank < marker_rank:
                updates["status"] = "MARKER_RECOMMENDATIONS_READY"

            self._save_project_fields(project_id, updates)
            return recs
        finally:
            if labelled_url.startswith("http") and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # =========================================================================
    # GROUP C: IMAGE OPERATIONS (Supabase Storage)
    # =========================================================================

    def upload_image(
        self, project_id: str, image_file: UploadFile, filename: str
    ) -> str:
        """Upload a base room image to Supabase Storage."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        user_id = str(row["user_id"])
        file_bytes = image_file.file.read()
        mime = image_file.content_type or "image/jpeg"

        # Upload to Supabase Storage
        public_url = self._upload_to_storage(
            project_id, user_id, "base", file_bytes, filename, mime
        )

        # Check room emptiness via temp file (Gemini needs local path)
        tmp = tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False)
        tmp.write(file_bytes)
        tmp.close()

        try:
            is_empty = self._check_room_emptiness(tmp.name)
        finally:
            os.unlink(tmp.name)

        # Update project row
        self._save_project_fields(project_id, {
            "is_base_image_empty_room": is_empty,
            "status": "BASE_IMAGE_UPLOADED",
        })

        return public_url

    def upload_inspiration_image(
        self, project_id: str, image_file: UploadFile, filename: str
    ) -> str:
        """Upload a single inspiration image to Supabase Storage."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        user_id = str(row["user_id"])
        file_bytes = image_file.file.read()
        mime = image_file.content_type or "image/jpeg"

        # Determine sort order from existing inspiration images
        existing = self._get_image_urls(project_id, "inspiration")
        sort_order = len(existing)

        ts = int(time.time())
        storage_filename = f"inspiration_{sort_order}_{ts}{Path(filename).suffix}"

        public_url = self._upload_to_storage(
            project_id, user_id, "inspiration", file_bytes, storage_filename, mime, sort_order
        )

        # Update status if applicable
        current_status = row["status"]
        if self._status_rank(current_status) < self._status_rank("INSPIRATION_IMAGES_UPLOADED"):
            self._save_project_fields(project_id, {"status": "INSPIRATION_IMAGES_UPLOADED"})

        return public_url

    def upload_inspiration_images_batch(
        self, project_id: str, image_files: List[UploadFile]
    ) -> List[str]:
        """Batch upload multiple inspiration images."""
        urls = []
        for i, image_file in enumerate(image_files):
            filename = image_file.filename or f"inspiration_{i}.jpg"
            url = self.upload_inspiration_image(project_id, image_file, filename)
            urls.append(url)
        return urls

    # =========================================================================
    # GROUP D: MARKER OPERATIONS
    # =========================================================================

    def save_improvement_markers(
        self, project_id: str, markers: List[ImprovementMarker]
    ) -> str:
        """Save improvement markers, create labelled image, trigger recommendations."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        user_id = str(row["user_id"])

        # Delete existing markers for this project
        self._supabase.table("improvement_markers").delete().eq(
            "project_id", project_id
        ).execute()

        # Insert new markers
        for i, marker in enumerate(markers):
            self._supabase.table("improvement_markers").insert(
                {
                    "project_id": project_id,
                    "user_id": user_id,
                    "marker_id": marker.id,
                    "position_x": marker.position.x,
                    "position_y": marker.position.y,
                    "description": marker.description,
                    "color": marker.color,
                    "sort_order": i,
                }
            ).execute()

        # Create labelled image with markers overlaid
        base_url = self._get_image_url(project_id, "base")
        labelled_url = None

        if base_url:
            tmp_base = self._download_image_to_tempfile(base_url, suffix=".jpg")
            try:
                labelled_url = self._create_and_upload_labelled_image(
                    project_id, user_id, tmp_base, markers
                )
            finally:
                os.unlink(tmp_base)

        # Update project status
        self._save_project_fields(project_id, {
            "status": MARKERS_SAVED_STATUS,
        })

        # Try generating recommendations if all prerequisites met
        self._try_generate_marker_recommendations(project_id)

        return labelled_url or "markers_saved"

    def _create_and_upload_labelled_image(
        self,
        project_id: str,
        user_id: str,
        base_image_path: str,
        markers: List[ImprovementMarker],
    ) -> str:
        """Create a labelled image with marker overlays and upload to Storage."""
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(base_image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        color_map = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "purple": (128, 0, 128),
            "orange": (255, 165, 0),
        }

        for i, marker in enumerate(markers):
            x = int(marker.position.x * width)
            y = int(marker.position.y * height)
            # Support hex color codes and named colors
            if marker.color and marker.color.startswith('#') and len(marker.color) == 7:
                try:
                    hex_str = marker.color.lstrip('#')
                    color = tuple(int(hex_str[j:j+2], 16) for j in (0, 2, 4))
                except ValueError:
                    color = color_map.get(marker.color, (255, 0, 0))
            else:
                color = color_map.get(marker.color, (255, 0, 0))
            r = 15
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color, outline="white", width=2)
            draw.text((x + r + 5, y - 10), str(i + 1), fill=color)

        # Save to bytes and upload
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        file_bytes = buffer.getvalue()

        # Remove old labelled images
        old_labelled = (
            self._supabase.table("project_images")
            .select("storage_path")
            .eq("project_id", project_id)
            .eq("image_type", "labelled")
            .execute()
        )
        old_paths = [r["storage_path"] for r in (old_labelled.data or [])]
        if old_paths:
            self._supabase.storage.from_(STORAGE_BUCKET).remove(old_paths)
            self._supabase.table("project_images").delete().eq(
                "project_id", project_id
            ).eq("image_type", "labelled").execute()

        ts = int(time.time())
        public_url = self._upload_to_storage(
            project_id, user_id, "labelled", file_bytes, f"labelled_{ts}.png"
        )

        return public_url

    # =========================================================================
    # FOUNDATION HELPERS (Supabase Storage image access)
    # =========================================================================

    def _get_image_bytes_from_storage(self, project_id: str, image_type: str) -> Optional[bytes]:
        """Download an image from Storage and return raw bytes."""
        url = self._get_image_url(project_id, image_type)
        if not url:
            return None
        import httpx
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    def _get_pil_image_from_storage(self, project_id: str, image_type: str):
        """Download image from Storage and return (PIL.Image, raw_bytes) tuple."""
        from PIL import Image
        raw = self._get_image_bytes_from_storage(project_id, image_type)
        if raw is None:
            raise ValueError(f"No {image_type} image found for project {project_id}")
        img = Image.open(BytesIO(raw))
        return img, raw

    def _replace_image_in_storage(
        self, project_id: str, user_id: str, image_type: str, file_bytes: bytes, filename: str
    ) -> str:
        """Delete old images of a type, then upload new one. Returns public URL."""
        old = (
            self._supabase.table("project_images")
            .select("storage_path")
            .eq("project_id", project_id)
            .eq("image_type", image_type)
            .execute()
        )
        old_paths = [r["storage_path"] for r in (old.data or [])]
        if old_paths:
            self._supabase.storage.from_(STORAGE_BUCKET).remove(old_paths)
            self._supabase.table("project_images").delete().eq(
                "project_id", project_id
            ).eq("image_type", image_type).execute()
        return self._upload_to_storage(project_id, user_id, image_type, file_bytes, filename)

    @contextlib.contextmanager
    def _temp_image(self, project_id: str, image_type: str, suffix: str = ".png"):
        """Context manager: download image to temp file, yield path, cleanup."""
        url = self._get_image_url(project_id, image_type)
        if not url:
            raise ValueError(f"No {image_type} image found for project {project_id}")
        tmp_path = self._download_image_to_tempfile(url, suffix=suffix)
        try:
            yield tmp_path
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # =========================================================================
    # PORTED HELPERS (pure logic from DataManager, no data I/O changes)
    # =========================================================================

    DECOR_SEARCH_TEMPLATES = {
        "wall art": "{style} wall art canvas print framed artwork home decor",
        "art": "{style} wall art canvas print framed artwork home decor",
        "geometric art": "{style} geometric wall art canvas print abstract modern",
        "rug": "{style} area rug carpet floor mat {color}",
        "geometric rug": "{style} geometric pattern area rug modern carpet",
        "vase": "{style} decorative vase ceramic glass flower vase home decor",
        "lamp": "{style} lamp lighting fixture {color}",
        "floor lamp": "{style} floor lamp standing lamp modern lighting",
        "table lamp": "{style} table lamp desk lamp bedside lighting",
        "mirror": "{style} wall mirror decorative mirror home decor",
        "plant": "artificial plant faux greenery indoor plant decor",
        "throw pillow": "{style} throw pillow decorative cushion {color}",
        "curtain": "{style} curtain drapes window treatment {color}",
        "shelf": "{style} wall shelf floating shelf storage decor",
        "clock": "{style} wall clock decorative clock modern",
    }

    def _dedupe_products_by_url(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate products by product_id or normalized URL."""
        from urllib.parse import urlparse, urlunparse

        def normalize(u: str) -> str:
            try:
                parsed = urlparse(u)
                cleaned = parsed._replace(query="", fragment="")
                return urlunparse(cleaned).lower()
            except Exception:
                return u.split("?")[0].lower()

        seen = set()
        deduped: List[Dict[str, Any]] = []
        for p in products:
            product_id = p.get("id") or p.get("product_id") or ""
            if product_id:
                key = f"pid:{product_id}"
            else:
                url = p.get("url") or ""
                title = p.get("title", "")[:50]
                key = f"{normalize(url)}|{title.lower()}"
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped.append(p)
        return deduped

    def _type_guard(self, title: str, target_type: str) -> bool:
        """Allow only titles that match the target type family."""
        t = title.lower()
        tt = target_type.lower()
        try:
            from config import FeatureFlags, FURNITURE_SYNONYMS, HARD_NEGATIVES
            use_enhanced = FeatureFlags.ENHANCED_TYPE_GUARD
        except ImportError:
            use_enhanced = False
            FURNITURE_SYNONYMS = {}
            HARD_NEGATIVES = []

        if use_enhanced:
            if any(neg in t for neg in HARD_NEGATIVES):
                return False
            type_map = {
                "shelf": ["shelf", "shelving", "bookcase", "bookshelf", "wall shelf", "floating shelf", "etagere"],
                "console table": ["console table", "sofa table", "entry table", "hallway table", "entryway table", "console"],
                "table": ["table", "dining table", "coffee table", "cocktail table", "side table", "end table", "accent table", "desk"],
                "coffee table": ["coffee table", "cocktail table", "tea table"],
                "side table": ["side table", "end table", "accent table", "lamp table"],
                "nightstand": ["nightstand", "bedside table", "night table", "bedside stand"],
                "bench": ["bench", "ottoman", "entry bench", "settee", "banquette", "footstool", "pouf"],
                "ottoman": ["ottoman", "footstool", "pouf", "hassock", "footrest"],
                "chair": ["chair", "armchair", "accent chair", "dining chair", "desk chair", "lounge chair", "club chair", "recliner"],
                "armchair": ["armchair", "accent chair", "lounge chair", "club chair", "arm chair"],
                "sofa": ["sofa", "couch", "sectional", "loveseat", "settee", "sleeper sofa", "sofa bed"],
                "sectional": ["sectional", "sectional sofa", "modular sofa", "l-shaped sofa"],
                "bed": ["bed", "platform bed", "bed frame", "headboard", "bedframe", "sleigh bed", "canopy bed"],
                "lamp": ["lamp", "floor lamp", "table lamp", "desk lamp", "sconce", "light", "lighting"],
                "floor lamp": ["floor lamp", "standing lamp", "torchiere", "arc lamp"],
                "table lamp": ["table lamp", "desk lamp", "bedside lamp"],
                "dresser": ["dresser", "chest of drawers", "bureau", "chest", "highboy", "lowboy"],
                "cabinet": ["cabinet", "sideboard", "buffet", "credenza", "hutch", "cupboard", "armoire"],
                "storage": ["cabinet", "dresser", "sideboard", "buffet", "storage", "credenza", "chest"],
                "tv stand": ["tv stand", "media console", "entertainment center", "media cabinet", "tv console"],
                "rug": ["rug", "area rug", "runner", "carpet", "mat"],
                "desk": ["desk", "writing desk", "computer desk", "work desk", "secretary desk", "office desk"],
                "stool": ["stool", "bar stool", "counter stool", "barstool"],
            }
            for key, synonyms in FURNITURE_SYNONYMS.items():
                if key not in type_map:
                    type_map[key] = [key] + synonyms
                else:
                    existing = set(type_map[key])
                    existing.update(synonyms)
                    type_map[key] = list(existing)
        else:
            negatives = ["decor", "how to", "ideas", "tutorial", "guide", "inspiration", "poster", "print"]
            if any(neg in t for neg in negatives):
                return False
            type_map = {
                "shelf": ["shelf", "shelving", "bookcase", "wall shelf"],
                "console table": ["console table", "sofa table", "entry table"],
                "table": ["table", "dining table", "coffee table", "side table", "end table", "desk"],
                "bench": ["bench", "ottoman", "entry bench"],
                "chair": ["chair", "armchair", "accent chair", "dining chair", "desk chair"],
                "sofa": ["sofa", "couch", "sectional", "loveseat"],
                "bed": ["bed", "platform bed", "bed frame", "headboard"],
                "lamp": ["lamp", "floor lamp", "table lamp", "sconce"],
                "storage": ["cabinet", "dresser", "sideboard", "buffet", "storage"],
                "rug": ["rug", "runner"],
            }

        for family, keywords in type_map.items():
            if tt in family or tt in " ".join(keywords):
                return any(k in t for k in keywords)
        return tt in t

    def _filter_products_with_images(self, products: List[Dict[str, Any]], min_count: int = 4) -> List[Dict[str, Any]]:
        """Filter products ensuring they have valid images."""
        def get_image(p):
            return (
                p.get("image_url") or p.get("thumbnail") or
                (p.get("images") or [None])[0] or p.get("image")
            )
        bad_patterns = ["placeholder", ".svg", "no-image", "default", "blank", "empty", "missing"]
        with_good_images = []
        with_any_images = []
        without_images = []
        for p in products:
            img = get_image(p)
            if img and len(img) > 10:
                p["image_url"] = img
                if any(pat in img.lower() for pat in bad_patterns):
                    with_any_images.append(p)
                else:
                    with_good_images.append(p)
            else:
                without_images.append(p)
        result = with_good_images[:min_count]
        if len(result) < min_count:
            needed = min_count - len(result)
            result.extend(with_any_images[:needed])
        if len(result) < min_count:
            needed = min_count - len(result)
            result.extend(without_images[:needed])
        return result

    def _select_best_recommendations(self, context: ProjectContext, max_count: int = 2) -> List[str]:
        """Auto-select best recommendations based on style analysis."""
        recommendations = context.product_recommendations or []
        if len(recommendations) <= max_count:
            return recommendations
        style_items = []
        if context.style_analysis and isinstance(context.style_analysis, dict):
            furniture_recs = context.style_analysis.get("furniture_recommendations", [])
            for rec in furniture_recs:
                if isinstance(rec, dict):
                    item_type = rec.get("item_type", "").lower()
                    if item_type:
                        style_items.append(item_type)
        scored = []
        for rec in recommendations:
            rec_lower = rec.lower()
            score = 0
            for style_item in style_items:
                if style_item in rec_lower:
                    score += 10
            high_impact = ["sofa", "bed", "table", "desk", "chair", "bookcase", "dresser"]
            for item in high_impact:
                if item in rec_lower:
                    score += 5
            decor_items = ["art", "lamp", "rug", "mirror", "plant"]
            for item in decor_items:
                if item in rec_lower:
                    score += 3
            scored.append((rec, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [rec for rec, score in scored[:max_count]]

    def _validate_product_links(self, products: List[Dict], max_validate: int = 5) -> List[Dict]:
        """Validate that product URLs lead to actual product pages."""
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def check_link(product):
            url = product.get("url", "")
            if not url:
                return product, False
            try:
                resp = requests.head(url, timeout=3, allow_redirects=True)
                is_valid = resp.status_code == 200
                product["link_validated"] = is_valid
                return product, is_valid
            except Exception:
                product["link_validated"] = False
                return product, False

        validated = []
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(check_link, p): p for p in products[:max_validate]}
                for future in as_completed(futures, timeout=10):
                    try:
                        product, is_valid = future.result()
                        if is_valid:
                            validated.append(product)
                    except Exception:
                        pass
        except Exception:
            return products
        validated.extend(products[max_validate:])
        return validated

    def _validate_product_pages_with_exa(
        self, products: List[Dict[str, Any]], max_validate: int = 15, min_valid_threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """Validate product URLs are actual product pages using Exa."""
        from config import is_blocked_domain

        if not products:
            return products
        pre_filtered = []
        for p in products:
            url = p.get("url", "")
            if not is_blocked_domain(url):
                pre_filtered.append(p)
        products = pre_filtered
        if not self.exa_client or not products:
            return products
        to_validate = products[:max_validate]
        remainder = products[max_validate:]
        urls_to_check = [p.get("url", "") for p in to_validate if p.get("url")]
        if not urls_to_check:
            return products
        try:
            validation_results = self.exa_client.validate_product_urls_batch(
                urls=urls_to_check, batch_size=5, max_chars=2000
            )
            validated = []
            for product in to_validate:
                url = product.get("url", "")
                if url in validation_results:
                    result = validation_results[url]
                    if result.get("is_valid"):
                        product["exa_validated"] = True
                        validated.append(product)
                else:
                    product["exa_validated"] = False
                    validated.append(product)
            return validated + remainder
        except Exception as e:
            self.logger.error(f"Exa validation failed: {e}")
            return products

    def _prepare_crop_for_search(self, crop, target_size: int = 512):
        """Prepare crop for optimal reverse image search quality."""
        from PIL import Image, ImageEnhance
        w, h = crop.size
        if max(w, h) < target_size:
            scale = target_size / max(w, h)
            crop = crop.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        if crop.mode != 'RGB':
            crop = crop.convert('RGB')
        enhancer = ImageEnhance.Contrast(crop)
        crop = enhancer.enhance(1.1)
        return crop

    def _generate_multi_queries(self, label: str, attributes: Dict) -> List[str]:
        """Generate multiple search queries for better coverage."""
        queries = []
        label_lower = label.lower()
        color = attributes.get("color", "")
        material = attributes.get("material", "")
        style = attributes.get("style", "")
        full_parts = [p for p in [color, material, style, label] if p]
        full_query = " ".join(full_parts).strip()
        if full_query:
            queries.append(full_query)
        if "bed" in label_lower and "bedding" not in label_lower:
            features = []
            if "upholstered" in label_lower or (material and "fabric" in material.lower()):
                features.append("upholstered")
            if "wingback" in label_lower or "wing" in label_lower:
                features.append("wingback")
            if "tufted" in label_lower or "channel" in label_lower:
                features.append("channel tufted")
            if "canopy" in label_lower:
                features.append("canopy")
            if "platform" in label_lower:
                features.append("platform")
            if features and color:
                feature_query = f"{color} {' '.join(features)} bed frame"
                if feature_query not in queries:
                    queries.append(feature_query)
        if style and style.lower() not in full_query.lower():
            style_query = f"{style} {label}"
            if color:
                style_query = f"{color} {style_query}"
            if style_query not in queries:
                queries.append(style_query)
        simple_query = f"{color} {label}".strip() if color else label
        if simple_query not in queries:
            queries.append(simple_query)
        seen = set()
        unique_queries = []
        for q in queries:
            q_normalized = " ".join(q.lower().split())
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q)
        return unique_queries[:3]

    def _generate_search_query(self, context: ProjectContext) -> str:
        """Generate an optimized search query using AI."""
        try:
            from pydantic import BaseModel
            class SearchQuery(BaseModel):
                query: str
                reasoning: str
            recs_text = ", ".join(context.selected_product_recommendations) if context.selected_product_recommendations else "furniture"
            context_info = f"Space Type: {context.space_type}\nSelected Recommendations: {recs_text}\n"
            if context.improvement_markers:
                markers_summary = ", ".join([m.description for m in context.improvement_markers])
                context_info += f"Improvement Areas: {markers_summary}\n"
            if context.inspiration_recommendations:
                context_info += f"Style Preferences: {', '.join(context.inspiration_recommendations[:2])}\n"
            if context.color_analysis:
                palette_name = context.color_analysis.get("palette_name", "")
                if palette_name:
                    context_info += f"Color Palette: {palette_name}\n"
            if context.style_analysis:
                style_name = context.style_analysis.get("style_name", "")
                if style_name:
                    context_info += f"Design Style: {style_name}\n"
            if context.preferred_stores:
                context_info += f"Preferred Stores: {', '.join(context.preferred_stores[:3])}\n"
            prompt = f"""Generate a specific, optimized shopping search query for this recommendation.
{context_info}
Create a search query that is 3-8 words, specific, optimized for e-commerce, and avoids decor-only results."""
            result = self.gemini_client.get_structured_completion(prompt=prompt, pydantic_model=SearchQuery)
            return f"{result.query} -decor -ideas"
        except Exception as e:
            self.logger.warning(f"Error generating search query: {e}")
            recs_text = ", ".join(context.selected_product_recommendations) if context.selected_product_recommendations else "furniture"
            return f"{recs_text} {context.space_type} -decor -ideas"

    def _generate_search_query_for_recommendation(self, context: ProjectContext, recommendation: str) -> str:
        """Generate a search query for a single recommendation using templates."""
        rec_lower = recommendation.lower()
        for prefix in ["add ", "change ", "replace ", "install ", "hang ", "place "]:
            if rec_lower.startswith(prefix):
                rec_lower = rec_lower[len(prefix):]
                break
        style_name = ""
        if context.style_analysis and isinstance(context.style_analysis, dict):
            style_name = context.style_analysis.get("style_name", "modern")
        color = ""
        if context.color_analysis and isinstance(context.color_analysis, dict):
            accent_colors = context.color_analysis.get("accent_colors", [])
            if accent_colors and isinstance(accent_colors, list) and len(accent_colors) > 0:
                first_color = accent_colors[0]
                if isinstance(first_color, dict):
                    color = first_color.get("description", "")[:15]
        search_query = None
        for item_key, template in self.DECOR_SEARCH_TEMPLATES.items():
            if item_key in rec_lower:
                search_query = template.format(style=style_name, color=color, size="", type="").strip()
                while "  " in search_query:
                    search_query = search_query.replace("  ", " ")
                break
        if not search_query:
            query_parts = [rec_lower]
            if style_name:
                query_parts.insert(0, style_name.lower())
            if color:
                query_parts.append(color.lower())
            search_query = " ".join(query_parts)
        search_query = f"trending {search_query}"
        search_query += " -ideas -inspiration -\"how to\" -diy -tutorial -book -magazine -pattern"
        return search_query[:120]

    def _curate_products_with_ai(self, products: List[Dict[str, Any]], category: str, style: str = "", room_type: str = "", max_products: int = 8) -> List[Dict[str, Any]]:
        """Use Gemini Vision to evaluate and rank products by visual quality."""
        from config import AI_PRODUCT_CURATION, QUALITY_RETAILER_SCORES
        import requests as req_lib
        from PIL import Image
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not AI_PRODUCT_CURATION.get("enabled", True) or not products:
            return products[:max_products]
        max_eval = AI_PRODUCT_CURATION.get("max_products_to_evaluate", 16)
        products_to_eval = products[:max_eval]

        def download_image(product: Dict) -> tuple:
            image_url = product.get("image_url", "") or ""
            if not image_url or len(image_url) < 10:
                return product, None
            try:
                response = req_lib.get(image_url, timeout=5)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    min_dim = AI_PRODUCT_CURATION.get("min_image_dimension", 200)
                    if img.width < min_dim or img.height < min_dim:
                        return product, None
                    img.thumbnail((400, 400))
                    buffer = BytesIO()
                    img.convert("RGB").save(buffer, format="JPEG", quality=80)
                    return product, base64.b64encode(buffer.getvalue()).decode()
            except Exception:
                pass
            return product, None

        products_with_images = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(download_image, p): p for p in products_to_eval}
            for future in as_completed(futures):
                product, img_b64 = future.result()
                if img_b64:
                    products_with_images.append((product, img_b64))
        if not products_with_images:
            return products[:max_products]

        for product, _ in products_with_images:
            store = (product.get("store") or "").lower()
            product["_store_quality"] = QUALITY_RETAILER_SCORES.get(store, QUALITY_RETAILER_SCORES.get("default", 0.7))

        batch_size = AI_PRODUCT_CURATION.get("batch_size", 8)
        all_scored = []
        for batch_start in range(0, len(products_with_images), batch_size):
            batch = products_with_images[batch_start:batch_start + batch_size]
            try:
                scored_batch = self._evaluate_product_batch_with_gemini(batch, category, style, room_type)
                all_scored.extend(scored_batch)
            except Exception:
                for product, _ in batch:
                    product["_ai_score"] = product.get("_store_quality", 0.7)
                    all_scored.append(product)

        min_score = AI_PRODUCT_CURATION.get("min_quality_score", 0.5)
        for p in all_scored:
            ai_score = p.get("_ai_score", 0.5)
            store_score = p.get("_store_quality", 0.7)
            p["_final_score"] = ai_score * 0.7 + store_score * 0.3
        all_scored.sort(key=lambda p: p.get("_final_score", 0), reverse=True)
        filtered = [p for p in all_scored if p.get("_final_score", 0) >= min_score]
        if len(filtered) < 3 and len(all_scored) >= 3:
            filtered = all_scored[:max(3, len(filtered))]
        result = filtered[:max_products]
        for p in result:
            p.pop("_store_quality", None)
            p.pop("_ai_score", None)
            p.pop("_final_score", None)
        return result

    def _evaluate_product_batch_with_gemini(self, batch: List[tuple], category: str, style: str, room_type: str) -> List[Dict[str, Any]]:
        """Evaluate a batch of products using Gemini Vision."""
        from pydantic import BaseModel, Field
        from typing import List as TypeList
        if not batch:
            return []

        class ProductScore(BaseModel):
            index: int = Field(description="Product index (0-based)")
            quality_score: float = Field(description="Visual/design quality score 0.0-1.0")
            style_match: float = Field(description="Style match score 0.0-1.0")
            reasoning: str = Field(description="Brief reason for scores")

        class ProductEvaluationResponse(BaseModel):
            scores: TypeList[ProductScore]

        image_parts = []
        product_info = []
        for i, (product, img_b64) in enumerate(batch):
            image_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
            product_info.append(f"Product {i}: {product.get('title', 'Unknown')[:80]} (from {product.get('store', 'Unknown')})")

        style_desc = style if style else "modern, aesthetic"
        room_desc = room_type if room_type else "any room"
        prompt = f"""Evaluate these {len(batch)} product images for a {category} in a {room_desc}.
Requested style: {style_desc}

Products:
{chr(10).join(product_info)}

For each product, score quality_score (0-1) and style_match (0-1). Be critical."""

        try:
            result = self.gemini_client.analyze_images_with_vision(
                prompt=prompt, pydantic_model=ProductEvaluationResponse,
                image_parts=image_parts,
                system_message="You are an expert interior designer evaluating product quality.",
            )
            score_map = {s.index: s for s in result.scores}
            scored_products = []
            for i, (product, _) in enumerate(batch):
                if i in score_map:
                    s = score_map[i]
                    from config import AI_PRODUCT_CURATION
                    weights = AI_PRODUCT_CURATION.get("score_weights", {})
                    quality_weight = weights.get("visual_quality", 0.35) + weights.get("design_aesthetic", 0.35)
                    style_weight = weights.get("style_match", 0.30)
                    product["_ai_score"] = s.quality_score * quality_weight + s.style_match * style_weight
                else:
                    product["_ai_score"] = 0.5
                scored_products.append(product)
            return scored_products
        except Exception:
            for product, _ in batch:
                product["_ai_score"] = 0.5
            return [p for p, _ in batch]

    def _coerce_bbox_normalized(
        self,
        bbox: Any,
        *,
        click_x: float,
        click_y: float,
        box_size: float = 0.2,
    ) -> List[float]:
        """Coerce a bbox into [ymin, xmin, ymax, xmax] normalized format."""
        fallback = [
            max(0.0, click_y - box_size / 2),
            max(0.0, click_x - box_size / 2),
            min(1.0, click_y + box_size / 2),
            min(1.0, click_x + box_size / 2),
        ]

        # New detector format
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            try:
                ymin, xmin, ymax, xmax = [float(v) for v in bbox]
            except (TypeError, ValueError):
                return fallback
        # Legacy shape from old Supabase path
        elif isinstance(bbox, dict):
            try:
                x1 = float(bbox.get("x1", fallback[1]))
                y1 = float(bbox.get("y1", fallback[0]))
                x2 = float(bbox.get("x2", fallback[3]))
                y2 = float(bbox.get("y2", fallback[2]))
                ymin, xmin, ymax, xmax = y1, x1, y2, x2
            except (TypeError, ValueError):
                return fallback
        else:
            return fallback

        if ymin > ymax:
            ymin, ymax = ymax, ymin
        if xmin > xmax:
            xmin, xmax = xmax, xmin

        ymin = max(0.0, min(1.0, ymin))
        xmin = max(0.0, min(1.0, xmin))
        ymax = max(0.0, min(1.0, ymax))
        xmax = max(0.0, min(1.0, xmax))

        # Guard against degenerate boxes
        if ymax <= ymin:
            ymax = min(1.0, ymin + 0.01)
        if xmax <= xmin:
            xmax = min(1.0, xmin + 0.01)

        return [ymin, xmin, ymax, xmax]

    def _normalize_spatial_item(
        self,
        item: Any,
        *,
        click_x: float,
        click_y: float,
    ) -> Optional[Dict[str, Any]]:
        """Normalize one spatial detection candidate to a stable shape."""
        if not isinstance(item, dict):
            return None

        label = self._normalize_clip_text_value(item.get("label"), default="furniture")
        bbox_raw = item.get("bbox_normalized")
        if bbox_raw is None:
            bbox_raw = item.get("bounding_box")
        bbox_normalized = self._coerce_bbox_normalized(
            bbox_raw,
            click_x=click_x,
            click_y=click_y,
        )

        return {
            "label": label,
            "bbox_normalized": bbox_normalized,
            "color": self._normalize_clip_text_value(item.get("color"), default=""),
            "material": self._normalize_clip_text_value(item.get("material"), default=""),
            "style": self._normalize_clip_text_value(item.get("style"), default=""),
            "search_query": self._normalize_clip_text_value(
                item.get("search_query"), default=label
            ),
        }

    def _normalize_spatial_detection(
        self,
        detection: Any,
        *,
        click_x: float,
        click_y: float,
    ) -> Optional[Dict[str, Any]]:
        """Normalize spatial detector output from current or legacy formats."""
        if not isinstance(detection, dict):
            return None

        # Current format from spatial_utils.py
        if "label" in detection and "bbox_normalized" in detection:
            label = self._normalize_clip_text_value(
                detection.get("label"), default="furniture"
            )
            bbox_normalized = self._coerce_bbox_normalized(
                detection.get("bbox_normalized"),
                click_x=click_x,
                click_y=click_y,
            )
            attrs = detection.get("attributes") or {}
            additional_items = []
            for raw_item in detection.get("additional_items") or []:
                normalized = self._normalize_spatial_item(
                    raw_item,
                    click_x=click_x,
                    click_y=click_y,
                )
                if normalized:
                    additional_items.append(normalized)
            return {
                "label": label,
                "bbox_normalized": bbox_normalized,
                "attributes": {
                    "color": self._normalize_clip_text_value(attrs.get("color"), default=""),
                    "material": self._normalize_clip_text_value(attrs.get("material"), default=""),
                    "style": self._normalize_clip_text_value(attrs.get("style"), default=""),
                },
                "search_query": self._normalize_clip_text_value(
                    detection.get("search_query"), default=label
                ),
                "confidence": self._safe_float(detection.get("confidence"), 0.7),
                "additional_items": additional_items,
            }

        # Legacy format from earlier Supabase implementation
        if "primary_item" in detection:
            primary = self._normalize_spatial_item(
                detection.get("primary_item") or {},
                click_x=click_x,
                click_y=click_y,
            )
            if not primary:
                return None
            additional_items = []
            for raw_item in detection.get("additional_items") or []:
                normalized = self._normalize_spatial_item(
                    raw_item,
                    click_x=click_x,
                    click_y=click_y,
                )
                if normalized:
                    additional_items.append(normalized)
            return {
                "label": primary["label"],
                "bbox_normalized": primary["bbox_normalized"],
                "attributes": {
                    "color": primary.get("color", ""),
                    "material": primary.get("material", ""),
                    "style": primary.get("style", ""),
                },
                "search_query": primary.get("search_query", primary["label"]),
                "confidence": self._safe_float(detection.get("confidence"), 0.7),
                "additional_items": additional_items,
            }

        return None

    def _validate_click_on_primary(self, detection: Dict, click_x: float, click_y: float) -> Dict:
        """Ensure the primary item best matches the click point."""
        additional = detection.get("additional_items") or []
        if not additional:
            return detection

        primary = {
            "label": detection.get("label", "furniture"),
            "bbox_normalized": detection.get("bbox_normalized", [0, 0, 1, 1]),
            "color": (detection.get("attributes") or {}).get("color", ""),
            "material": (detection.get("attributes") or {}).get("material", ""),
            "style": (detection.get("attributes") or {}).get("style", ""),
            "search_query": detection.get(
                "search_query", detection.get("label", "furniture")
            ),
        }

        all_items = [primary] + [i for i in additional if isinstance(i, dict)]
        scored: List[Dict[str, Any]] = []
        for item in all_items:
            bbox = self._coerce_bbox_normalized(
                item.get("bbox_normalized"),
                click_x=click_x,
                click_y=click_y,
            )
            ymin, xmin, ymax, xmax = bbox
            click_inside = ymin <= click_y <= ymax and xmin <= click_x <= xmax
            center_x = (xmin + xmax) / 2
            center_y = (ymin + ymax) / 2
            distance = ((click_x - center_x) ** 2 + (click_y - center_y) ** 2) ** 0.5
            area = (ymax - ymin) * (xmax - xmin)

            score = 0.0
            if click_inside:
                score += 100.0
                score += 50.0 * (1 - min(area, 1.0))
                score += 10.0 * (1 - min(distance, 1.0))
            else:
                score += 10.0 * (1 - min(distance, 1.0))

            scored.append(
                {
                    **item,
                    "bbox_normalized": bbox,
                    "_selection_score": score,
                }
            )

        scored.sort(key=lambda item: item.get("_selection_score", 0.0), reverse=True)
        best = scored[0]
        original_label = str(primary.get("label", "furniture"))

        if str(best.get("label", "")) != original_label:
            detection["label"] = best.get("label", original_label)
            detection["bbox_normalized"] = best.get("bbox_normalized", primary["bbox_normalized"])
            detection["search_query"] = best.get("search_query", detection.get("search_query", original_label))
            detection["attributes"] = {
                "color": best.get("color", ""),
                "material": best.get("material", ""),
                "style": best.get("style", (detection.get("attributes") or {}).get("style", "")),
            }

            new_additional = []
            for item in scored[1:]:
                item.pop("_selection_score", None)
                if item.get("label") != best.get("label"):
                    new_additional.append(item)
            detection["additional_items"] = new_additional

        return detection

    def _is_actual_bed(self, label: str) -> bool:
        """Determine if a furniture label refers to a bed or bed region."""
        label_lower = label.lower()
        try:
            from config import BED_PRIMARY_INDICATORS, NOT_BED_COMPOUND_TERMS
        except ImportError:
            BED_PRIMARY_INDICATORS = ["bed", "bed frame", "platform bed", "headboard"]
            NOT_BED_COMPOUND_TERMS = ["bedside", "bed table", "bed lamp"]
        for term in NOT_BED_COMPOUND_TERMS:
            if term in label_lower:
                return False
        non_bed = ["lamp", "table", "chair", "rug", "desk", "shelf", "cabinet", "dresser", "mirror", "plant", "vase", "clock", "art", "curtain", "stool"]
        for item in non_bed:
            if item in label_lower and "bed" not in label_lower.replace(item, ""):
                return False
        for indicator in BED_PRIMARY_INDICATORS:
            if indicator in label_lower:
                return True
        if "bed" in label_lower:
            return True
        bedding_items = ["duvet", "comforter", "pillow", "sheet", "bedding", "quilt", "blanket", "throw"]
        for item in bedding_items:
            if item in label_lower:
                return True
        bed_patterns = ["tufted upholstered", "wingback upholstered", "channel upholstered", "velvet upholstered", "fabric upholstered"]
        for pattern in bed_patterns:
            if pattern in label_lower:
                return True
        return False

    def _detect_bed_sub_components(self, crop_b64: str) -> Dict:
        """Use Gemini Vision to detect visible sub-components within a bed image."""
        from pydantic import BaseModel, Field
        from typing import List as TypeList, Optional as Opt

        class BedComponent(BaseModel):
            visible: bool = False
            color: str = ""
            secondary_color: str = ""
            pattern: str = ""
            material: str = ""
            style: str = ""
            count: int = 1

        class BedComponentsResponse(BaseModel):
            pillows: BedComponent = BedComponent()
            bedding: BedComponent = BedComponent()
            throw: BedComponent = BedComponent()
            bed_frame: BedComponent = BedComponent()

        prompt = """Analyze this bed image and detect visible sub-components.
For each component (pillows, bedding, throw, bed_frame), determine:
- visible: Is it clearly visible?
- color: Primary color
- pattern: solid, striped, textured, floral, geometric, etc.
- material: linen, cotton, velvet, knit, wood, etc.
- style: modern, traditional, bohemian, minimalist, etc.
- count: Number visible (for pillows)"""

        try:
            image_parts = [{"inline_data": {"mime_type": "image/jpeg", "data": crop_b64}}]
            result = self.gemini_client.analyze_images_with_vision(
                prompt=prompt, pydantic_model=BedComponentsResponse, image_parts=image_parts,
                system_message="You are an expert at identifying bed components in images.",
            )
            return result.model_dump()
        except Exception as e:
            self.logger.warning(f"Bed component detection failed: {e}")
            return {}

    def _search_bed_components(self, label: str, attributes: Dict, lens_products: List[Dict], context: ProjectContext) -> Dict[str, List[Dict]]:
        """Search for bed component products (frame, bedding, throw, pillows)."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        components = {}

        # bed_frame: Use Google Lens visual results filtered for bed-related items
        bed_keywords = ["bed", "frame", "headboard", "platform", "upholstered"]
        bed_frame_products = []
        for p in lens_products:
            title_lower = (p.get("title", "") or "").lower()
            if any(kw in title_lower for kw in bed_keywords):
                bed_frame_products.append(p)
        components["bed_frame"] = bed_frame_products[:4]

        # Search other components in parallel
        def search_component(component_name: str, search_terms: List[str]) -> tuple:
            try:
                color = attributes.get("color", "white")
                material = attributes.get("material", "cotton")
                style_name = ""
                if context.style_analysis and isinstance(context.style_analysis, dict):
                    style_name = context.style_analysis.get("style_name", "modern")
                query = f"{color} {material} {style_name} {' '.join(search_terms)}"
                products = []
                if self.serp_client:
                    try:
                        serp_results = self.serp_client.search_and_analyze_products(query=query, space_type="bedroom", num_results=10)
                        products.extend(serp_results)
                    except Exception:
                        pass
                if self.exa_client:
                    try:
                        exa_results = self.exa_client.search_and_analyze_products(query=query, space_type="bedroom", num_results=8, similar_per_seed=2)
                        products.extend(exa_results)
                    except Exception:
                        pass
                products = self._dedupe_products_by_url(products)
                formatted = []
                for p in products:
                    images_array = p.get("images") or []
                    image_url = p.get("thumbnail") or p.get("image_url") or (images_array[0] if images_array else "") or ""
                    if image_url:
                        formatted.append({
                            "url": p.get("url", ""),
                            "title": p.get("title", ""),
                            "image_url": image_url,
                            "store": p.get("store", p.get("source", "Unknown")),
                            "price_str": p.get("price_str", ""),
                        })
                return component_name, formatted[:4]
            except Exception as e:
                self.logger.warning(f"Bed component search failed for {component_name}: {e}")
                return component_name, []

        try:
            from config import BED_COMPONENTS
        except ImportError:
            BED_COMPONENTS = {
                "bedding": {"search_terms": ["comforter", "duvet", "bedding set"]},
                "throw": {"search_terms": ["throw blanket", "bed throw"]},
                "pillows": {"search_terms": ["decorative pillows", "throw pillows", "bed pillows"]},
            }
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            for comp_name, comp_config in BED_COMPONENTS.items():
                if comp_name == "bed_frame":
                    continue
                terms = comp_config.get("search_terms", [comp_name])
                futures[executor.submit(search_component, comp_name, terms)] = comp_name
            for future in as_completed(futures):
                comp_name, results = future.result()
                components[comp_name] = results
        return components

    # =========================================================================
    # GROUP E: AI-HEAVY METHODS
    # =========================================================================

    # --- Phase 1: Simple context methods ---

    def get_pre_searched_suggestions(self, project_id: str) -> Dict[str, Any]:
        """Get all pre-searched product suggestions organized by category."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        pre_searched = row.get("pre_searched_categories") or {}
        if not pre_searched:
            return {
                "project_id": project_id, "categories": [], "total_products": 0,
                "overall_status": "empty", "message": "No products have been searched yet",
            }
        categories = list(pre_searched.values())
        total_products = sum(len(cat.get("products", [])) for cat in categories)
        statuses = [cat.get("status", "pending") for cat in categories]
        if all(s == "complete" for s in statuses):
            overall_status = "all_complete"
        elif all(s == "error" for s in statuses):
            overall_status = "all_error"
        elif any(s == "pending" for s in statuses):
            overall_status = "some_pending"
        else:
            overall_status = "mixed"
        return {
            "project_id": project_id, "categories": categories, "total_products": total_products,
            "overall_status": overall_status,
            "message": f"Found {total_products} products across {len(categories)} categories",
        }

    def select_product_recommendation(self, project_id: str, selected_recommendation: str):
        """Select/toggle a product recommendation."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        is_product_rec = context.product_recommendations and selected_recommendation in context.product_recommendations
        is_inspiration_rec = context.inspiration_recommendations and selected_recommendation in context.inspiration_recommendations
        if not (is_product_rec or is_inspiration_rec):
            raise ValueError(f"'{selected_recommendation}' is not a valid recommendation option")
        current_selections = list(context.selected_product_recommendations or [])
        if selected_recommendation in current_selections:
            current_selections.remove(selected_recommendation)
        else:
            current_selections.append(selected_recommendation)
        updates = {"selected_product_recommendations": current_selections}
        if current_selections:
            updates["status"] = "PRODUCT_RECOMMENDATION_SELECTED"
        elif context.product_recommendations:
            updates["status"] = "PRODUCT_RECOMMENDATIONS_READY"
        elif context.inspiration_recommendations:
            updates["status"] = "INSPIRATION_RECOMMENDATIONS_READY"
        self._save_project_fields(project_id, updates)
        log_user_action("product_recommendation_selected", project_id=project_id, recommendation=selected_recommendation)
        return current_selections

    def set_selected_product_recommendations(
        self, project_id: str, recommendations: List[str]
    ) -> List[str]:
        """Atomically overwrite the entire selected_product_recommendations list."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        valid_pool = set(context.product_recommendations or []) | set(context.inspiration_recommendations or [])
        if valid_pool:
            invalid = [r for r in recommendations if r not in valid_pool]
            if invalid:
                logger.warning(
                    "Recommendations not in stored pool (accepting anyway): %s", invalid,
                )
        updates: dict = {"selected_product_recommendations": recommendations}
        if recommendations:
            updates["status"] = "PRODUCT_RECOMMENDATION_SELECTED"
        elif context.product_recommendations:
            updates["status"] = "PRODUCT_RECOMMENDATIONS_READY"
        elif context.inspiration_recommendations:
            updates["status"] = "INSPIRATION_RECOMMENDATIONS_READY"
        self._save_project_fields(project_id, updates)
        log_user_action("set_selected_recommendations", project_id=project_id, count=len(recommendations))
        return recommendations

    def select_product_for_generation(
        self, project_id: str, product_url: str, product_title: str,
        product_image_url: str, generation_prompt: str = None,
        color_scheme: Dict[str, Any] = None, design_style: Dict[str, Any] = None,
    ):
        """Select a product for image generation."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        current_products = list(context.selected_products or [])
        exists = any(p.get('url') == product_url for p in current_products)
        if not exists:
            current_products.append({
                "url": product_url, "title": product_title,
                "image_url": product_image_url, "selected_at": datetime.now().isoformat(),
            })
        updates: dict = {
            "selected_products": current_products,
            "generation_prompt": generation_prompt,
            "status": "PRODUCT_SELECTED",
        }
        if color_scheme:
            updates["color_scheme"] = color_scheme
        if design_style:
            updates["design_style"] = design_style
        self._save_project_fields(project_id, updates)
        log_user_action("product_selected", project_id=project_id, product_url=product_url)
        return {
            "project_id": project_id, "selected_products": current_products,
            "status": "success", "message": f"Added to selection: {product_title[:50]}...",
        }

    def auto_select_best_product(self, project_id: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Auto-select the best product from search results based on scoring."""
        if not products:
            raise ValueError("No products to select from")
        scored_products = []
        for p in products:
            score = 0.0
            reasons = []
            similarity = p.get("similarity_score", 0) or p.get("relevance_score", 0.5)
            score += similarity * 50
            if similarity >= 0.8:
                reasons.append("high visual match")
            images = p.get("images", [])
            if images and len(images) > 0 and len(images[0]) > 10:
                score += 20
                reasons.append("clear product image")
            else:
                score -= 100
            store_trust = p.get("store_trust", 0.5)
            score += store_trust * 15
            if store_trust >= 0.85:
                reasons.append("trusted retailer")
            price = p.get("price")
            if price and price > 0:
                score += 10
                reasons.append("price available")
            rating = p.get("rating", 0)
            if rating and rating >= 4.0:
                score += 5
                reasons.append(f"highly rated ({rating})")
            scored_products.append({"product": p, "score": score, "reasons": reasons})
        scored_products.sort(key=lambda x: x["score"], reverse=True)
        best = scored_products[0]
        selected_product = best["product"]
        selection_reason = ", ".join(best["reasons"]) if best["reasons"] else "best overall match"
        alternatives = [sp["product"] for sp in scored_products[1:4]]
        self._save_project_fields(project_id, {"auto_selected_product": selected_product})
        return {"selected_product": selected_product, "selection_reason": selection_reason, "alternatives": alternatives}

    # --- Phase 2: AI methods ---

    def apply_color_scheme(self, project_id: str, palette_name: str, colors: List[str], let_ai_decide: bool = False) -> Dict[str, Any]:
        """Apply a color scheme using the Color Agent."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        if not context.base_image:
            raise ValueError("No base image found for this project")
        if not context.space_type:
            raise ValueError("No space type selected for this project")
        with self._temp_image(project_id, "base", suffix=".jpg") as tmp_path:
            color_analysis = self.gemini_client.analyze_color_application(
                image_path=tmp_path, palette_name=palette_name, palette_colors=colors,
                space_type=context.space_type, let_ai_decide=let_ai_decide,
            )
        color_scheme_data = {"palette_name": palette_name, "colors": colors, "let_ai_decide": let_ai_decide}
        self._save_project_fields(project_id, {
            "color_analysis": color_analysis, "color_scheme": color_scheme_data, "color_analysis_skipped": False,
        })
        self._try_generate_marker_recommendations(project_id)
        return color_analysis

    def apply_style(self, project_id: str, style_name: str, let_ai_decide: bool = False) -> Dict[str, Any]:
        """Apply an interior design style using the Style Agent."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        if not context.base_image:
            raise ValueError("No base image found for this project")
        if not context.space_type:
            raise ValueError("No space type selected for this project")
        color_scheme = context.color_scheme
        with self._temp_image(project_id, "base", suffix=".jpg") as tmp_path:
            style_analysis = self.gemini_client.analyze_style_application(
                image_path=tmp_path, style_name=style_name, space_type=context.space_type,
                color_scheme=color_scheme, let_ai_decide=let_ai_decide,
            )
        design_style_data = {"style_name": style_name, "let_ai_decide": let_ai_decide}
        self._save_project_fields(project_id, {
            "style_analysis": style_analysis, "design_style": design_style_data, "style_analysis_skipped": False,
        })
        self._try_generate_marker_recommendations(project_id)
        return style_analysis

    def generate_product_recommendations(self, project_id: str) -> List[str]:
        """Generate AI product recommendations based on project context."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        if not context.is_ready_for_product_recommendations():
            raise ValueError("Project is not ready for product recommendations")
        from pydantic import BaseModel
        class AIProductRecommendations(BaseModel):
            recommendations: List[str]
            reasoning: str
        context_info = f"Space Type: {context.space_type}\nRoom Status: {'Empty room' if context.is_base_image_empty_room else 'Furnished room'}\n"
        if context.improvement_markers:
            markers_info = "\n".join([f"- {m.description} (at {m.position.x:.1%}, {m.position.y:.1%})" for m in context.improvement_markers])
            context_info += f"\nImprovement Areas:\n{markers_info}"
        if context.color_analysis:
            ca = context.color_analysis
            context_info += f"\n\nColor Analysis:\n- Primary: {ca.get('primary_colors', [])}\n- Palette: {ca.get('palette_name', 'Custom')}"
        if context.style_analysis:
            sa = context.style_analysis
            context_info += f"\n\nStyle Analysis:\n- Style: {sa.get('style_name', 'Custom')}\n- Materials: {sa.get('materials', [])}"
        if context.inspiration_recommendations:
            context_info += f"\n\nStyle Recommendations from Inspiration:\n" + "\n".join([f"- {rec}" for rec in context.inspiration_recommendations])
        prompt = f"""Based on this comprehensive interior design project context, generate exactly 6 specific, actionable product recommendations.
{context_info}
Requirements:
- Each recommendation should be a specific action like "change sofa", "add coffee table", etc.
- Focus on items with the most visual impact aligned with detected style and color guidelines.
- Keep each recommendation to 2-4 words maximum.
Return exactly 6 distinct, complementary recommendations."""
        result = self.gemini_client.get_structured_completion(
            prompt=prompt, pydantic_model=AIProductRecommendations,
            system_message="You are an expert interior designer specializing in high-impact product recommendations.",
        )
        self._save_project_fields(project_id, {
            "product_recommendations": result.recommendations, "status": "PRODUCT_RECOMMENDATIONS_READY",
        })
        log_project_status_change(project_id, row["status"], "PRODUCT_RECOMMENDATIONS_READY")
        return result.recommendations

    def generate_inspiration_recommendations(self, project_id: str) -> List[str]:
        """Generate AI recommendations based on inspiration images."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        if not context.inspiration_images:
            raise ValueError("No inspiration images found for this project")
        if not context.base_image:
            raise ValueError("No base image found for this project")
        if not context.space_type:
            raise ValueError("No space type selected for this project")
        if not context.color_analysis and not context.color_analysis_skipped:
            raise ValueError("Please select a color palette or skip color analysis first")
        if not context.style_analysis and not context.style_analysis_skipped:
            raise ValueError("Please select a design style or skip style analysis first")
        from pydantic import BaseModel
        class AIInspirationResponse(BaseModel):
            recommendations: List[str]
        color_name = context.color_analysis.get("palette_name", "Custom") if context.color_analysis else "Not provided"
        style_name = context.style_analysis.get("style_name", "Modern") if context.style_analysis else "Not provided"
        style_overview = context.style_analysis.get("style_overview", "") if context.style_analysis else ""
        materials = ", ".join(context.style_analysis.get("materials", [])[:5]) if context.style_analysis else ""
        preferred_stores = ", ".join(context.preferred_stores or [])
        markers_text = ""
        if context.improvement_markers:
            markers_text = "\nUser's Specific Improvement Requests:\n" + "\n".join([f"- {m.description}" for m in context.improvement_markers])
        prompt = f"""Analyze the base room image along with the inspiration images for this {context.space_type} project.
Color Palette: {color_name}
Style: {style_name} — {style_overview}
Materials: {materials}
Preferred Stores: {preferred_stores}
{markers_text}
Provide exactly 4 specific, actionable design recommendations that address user's improvement requests,
incorporate the selected color palette and design style, and are practical for the {context.space_type}."""

        # Download base image and first inspiration image to temp files
        base_url = self._get_image_url(project_id, "base")
        inspiration_urls = self._get_image_urls(project_id, "inspiration")
        if not base_url:
            raise ValueError("Base image not found in storage")
        if not inspiration_urls:
            raise ValueError("Inspiration images not found in storage")
        tmp_base = self._download_image_to_tempfile(base_url, suffix=".jpg")
        tmp_inspo = self._download_image_to_tempfile(inspiration_urls[0], suffix=".jpg")
        try:
            result = self.gemini_client.analyze_image_with_vision(
                prompt=prompt, pydantic_model=AIInspirationResponse, image_path=tmp_base,
                additional_image_paths=[tmp_inspo],
                system_message="You are an expert interior designer. Provide exactly 4 specific recommendations.",
            )
        finally:
            for p in [tmp_base, tmp_inspo]:
                if os.path.exists(p):
                    os.unlink(p)
        recommendations = result.recommendations[:4]
        while len(recommendations) < 4:
            recommendations.append(f"Consider adding decorative accents that complement your {style_name} style")
        self._save_project_fields(project_id, {
            "inspiration_recommendations": recommendations, "status": "INSPIRATION_RECOMMENDATIONS_READY",
        })
        return recommendations

    def search_products(self, project_id: str) -> dict:
        """Search for products based on the selected recommendation."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        if not context.is_ready_for_product_search():
            raise ValueError("Project is not ready for product search")
        if not self.serp_client and not self.exa_client:
            raise ValueError("No product search client available")
        search_query = self._generate_search_query(context)
        products: List[Dict[str, Any]] = []
        if self.serp_client:
            serp_products = self.serp_client.search_and_analyze_products(
                query=search_query, space_type=context.space_type or "general", num_results=12,
            )
            for p in serp_products:
                p["source_api"] = "serp"
            products.extend(serp_products)
        if self.exa_client:
            try:
                exa_products = self.exa_client.search_and_analyze_products(
                    query=search_query, space_type=context.space_type or "general", num_results=10, similar_per_seed=3,
                )
                for p in exa_products:
                    p["source_api"] = "exa"
                products.extend(exa_products)
            except Exception as e:
                self.logger.warning(f"Exa product search failed: {e}")
        products = self._dedupe_products_by_url(products)
        target_type = ""
        if context.selected_product_recommendations:
            target_type = context.selected_product_recommendations[0].split()[0]
        filtered_products = []
        bad_patterns = ["placeholder", ".svg", "no-image", "default", "blank", "empty", "missing"]
        for p in products:
            title = p.get("title", "")
            if target_type and not self._type_guard(title, target_type):
                continue
            if not p.get("is_product_page", True):
                continue
            images = p.get("images", [])
            if not images:
                continue
            first_image = images[0] if images else ""
            if any(pat in first_image.lower() for pat in bad_patterns):
                continue
            filtered_products.append(p)
        filtered_products = filtered_products[:4]
        search_result = {"search_query": search_query, "products": filtered_products, "total_found": len(filtered_products)}
        self._save_project_fields(project_id, {
            "product_search_results": filtered_products, "status": "PRODUCT_SEARCH_COMPLETE",
        })
        log_project_status_change(project_id, row["status"], "PRODUCT_SEARCH_COMPLETE")
        return search_result

    def search_products_for_recommendations(self, project_id: str, recommendations: List[str]) -> Dict[str, Any]:
        """Search for real products for each selected recommendation in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        if not self.serp_client and not self.exa_client:
            raise ValueError("No product search client available")
        if len(recommendations) > 2:
            recommendations = recommendations[:2]

        def search_single_recommendation(recommendation: str) -> Dict[str, Any]:
            try:
                import time as _time
                from config import FeatureFlags, RETAILER_DOMAINS, is_valid_product
                from urllib.parse import urlparse
                _start = _time.time()
                api_call_count = 0
                filter_reasons: Dict[str, int] = {}

                rec_lower = recommendation.lower()
                for prefix in ["add ", "change ", "replace ", "install ", "hang ", "place "]:
                    if rec_lower.startswith(prefix):
                        rec_lower = rec_lower[len(prefix):]
                        break
                style_name = ""
                if context.style_analysis and isinstance(context.style_analysis, dict):
                    style_name = context.style_analysis.get("style_name", "modern")

                products: List[Dict[str, Any]] = []
                img_count = shop_count = exa_count = 0
                queries_attempted = []

                if FeatureFlags.SEARCH_STRATEGY == "images_first_v2":
                    # --- V2: Google Images primary, Shopping supplement, no negative terms ---

                    # Step 1: Google Images (primary — proven 78+ results)
                    if self.serp_client:
                        image_query = f"{rec_lower} furniture buy online"
                        queries_attempted.append(image_query)
                        try:
                            image_results = self.serp_client.search_images(query=image_query, num_results=20)
                            api_call_count += 1
                            for img in image_results:
                                image_url = img.get("thumbnail") or img.get("image_url") or ""
                                # Prioritize results from known retailer domains
                                source_url = img.get("url", "")
                                domain = urlparse(source_url).netloc.lower().replace("www.", "") if source_url else ""
                                is_retailer = any(rd in domain for rd in RETAILER_DOMAINS)
                                products.append({
                                    "title": img.get("title", ""), "url": source_url,
                                    "thumbnail": image_url, "image_url": image_url,
                                    "source": img.get("source", "Unknown"),
                                    "store": img.get("source", "Unknown"),
                                    "source_api": "google_images", "search_query": image_query,
                                    "_is_retailer": is_retailer,
                                })
                            img_count = len(image_results)
                        except Exception:
                            pass

                    # Step 2: Google Shopping (supplement — commercial qualifier, no negative terms)
                    if self.serp_client:
                        shopping_query = f"buy {rec_lower} price"
                        queries_attempted.append(shopping_query)
                        try:
                            serp_products = self.serp_client.search_and_analyze_products(
                                query=shopping_query, space_type=context.space_type or "general", num_results=10
                            )
                            api_call_count += 1
                            # Check if Shopping results are poisoned (>70% Etsy plans)
                            etsy_plan_count = sum(
                                1 for p in serp_products
                                if "etsy" in (p.get("source", "") or "").lower()
                                and not is_valid_product(p.get("title", ""))
                            )
                            if len(serp_products) > 0 and etsy_plan_count / len(serp_products) > 0.7:
                                # Poisoned — retry with material-focused query
                                self.logger.info(f"Shopping results poisoned ({etsy_plan_count}/{len(serp_products)} Etsy plans), retrying")
                                retry_query = f"{rec_lower} ready to ship"
                                queries_attempted.append(retry_query)
                                serp_products = self.serp_client.search_and_analyze_products(
                                    query=retry_query, space_type=context.space_type or "general", num_results=10
                                )
                                api_call_count += 1
                            for p in serp_products:
                                p["source_api"] = "serp"
                                p["search_query"] = shopping_query
                            products.extend(serp_products)
                            shop_count = len(serp_products)
                        except Exception:
                            pass

                    # Step 3: Exa (only if not exhausted)
                    if self.exa_client and not self._exa_exhausted:
                        try:
                            exa_products = self.exa_client.search_and_analyze_products(
                                query=f"{rec_lower} furniture", space_type=context.space_type or "general",
                                num_results=8, similar_per_seed=2
                            )
                            api_call_count += 1
                            for p in exa_products:
                                p["source_api"] = "exa"
                            products.extend(exa_products)
                            exa_count = len(exa_products)
                        except Exception as exa_err:
                            if "402" in str(exa_err) or "credits" in str(exa_err).lower():
                                self._exa_exhausted = True
                                self.logger.warning("Exa credits exhausted — skipping for this session")

                else:
                    # --- V1: Old strategy (Shopping primary) for rollback ---
                    query_variations = [
                        f"trending {rec_lower}", f"best {rec_lower} 2025", f"popular {rec_lower}",
                        f"{style_name} {rec_lower}" if style_name else f"modern {rec_lower}",
                        f"buy {rec_lower} online", f"{rec_lower} furniture",
                    ]
                    random.shuffle(query_variations)
                    for query in query_variations:
                        queries_attempted.append(query)
                        full_query = f"{query} -ideas -inspiration -diy -tutorial -plans -woodworking -blueprint -project -pattern -PDF"
                        if self.serp_client:
                            try:
                                serp_products = self.serp_client.search_and_analyze_products(query=full_query, space_type=context.space_type or "general", num_results=10)
                                api_call_count += 1
                                for p in serp_products:
                                    p["source_api"] = "serp"
                                    p["search_query"] = query
                                products.extend(serp_products)
                            except Exception:
                                pass
                        if self.exa_client and not self._exa_exhausted:
                            try:
                                exa_products = self.exa_client.search_and_analyze_products(query=full_query, space_type=context.space_type or "general", num_results=8, similar_per_seed=2)
                                api_call_count += 1
                                for p in exa_products:
                                    p["source_api"] = "exa"
                                    p["search_query"] = query
                                products.extend(exa_products)
                            except Exception as exa_err:
                                if "402" in str(exa_err) or "credits" in str(exa_err).lower():
                                    self._exa_exhausted = True
                                    self.logger.warning("Exa credits exhausted — skipping for this session")
                        if self.serp_client:
                            try:
                                image_results = self.serp_client.search_images(query=f"{rec_lower} furniture buy online", num_results=10)
                                api_call_count += 1
                                for img in image_results:
                                    image_url = img.get("thumbnail") or img.get("image_url") or ""
                                    products.append({"title": img.get("title", ""), "url": img.get("url", ""), "thumbnail": image_url, "image_url": image_url, "source": img.get("source", "Unknown"), "store": img.get("source", "Unknown"), "source_api": "google_images", "search_query": query})
                            except Exception:
                                pass

                # --- Common: dedupe, format, filter, curate ---
                products = self._dedupe_products_by_url(products)

                # Sort: retailer-sourced images first (v2 only)
                products.sort(key=lambda p: (0 if p.get("_is_retailer") else 1))

                formatted_products = []
                filtered_count = 0
                for p in products:
                    title = p.get("title", "")
                    if not is_valid_product(title):
                        filtered_count += 1
                        # Track filter reasons
                        for phrase in ["plan", "blueprint", "pattern", "pdf", "template"]:
                            if phrase in title.lower():
                                filter_reasons[phrase] = filter_reasons.get(phrase, 0) + 1
                                break
                        continue
                    images_array = p.get("images") or []
                    image_url = p.get("thumbnail") or p.get("image_url") or (images_array[0] if images_array else None) or p.get("image") or ""
                    formatted_products.append({
                        "url": p.get("url", p.get("product_link", p.get("link", ""))),
                        "title": title, "image_url": image_url,
                        "store": p.get("store", p.get("source", "Unknown")),
                        "price_str": p.get("price_str", str(p.get("price", "")) if p.get("price") else ""),
                        "price": p.get("price") if isinstance(p.get("price"), (int, float)) else None,
                        "similarity_score": p.get("similarity_score"),
                    })
                formatted_products = self._filter_products_with_images(formatted_products, min_count=4)

                # Retry with broader query if too few products
                if len(formatted_products) < 4 and self.serp_client:
                    fallback_query = f"{rec_lower} buy online"
                    queries_attempted.append(f"RETRY: {fallback_query}")
                    try:
                        retry_images = self.serp_client.search_images(
                            query=fallback_query, num_results=20,
                        )
                        api_call_count += 1
                        retry_products = []
                        for img in retry_images:
                            image_url = img.get("thumbnail") or img.get("image_url") or ""
                            if not image_url or len(image_url) < 10:
                                continue
                            retry_products.append({
                                "url": img.get("url", ""),
                                "title": img.get("title", ""),
                                "image_url": image_url,
                                "store": img.get("source", "Unknown"),
                            })
                        # Merge with existing, dedupe
                        existing_urls = {p.get("url", "") for p in formatted_products}
                        for p in retry_products:
                            if p["url"] and p["url"] not in existing_urls:
                                formatted_products.append(p)
                                existing_urls.add(p["url"])
                            if len(formatted_products) >= 6:
                                break
                        self.logger.info(
                            f"Retry search for '{recommendation}': now have {len(formatted_products)} products"
                        )
                    except Exception as retry_err:
                        self.logger.warning(f"Retry search failed for '{recommendation}': {retry_err}")

                random.shuffle(formatted_products)
                try:
                    from config import AI_PRODUCT_CURATION
                    if AI_PRODUCT_CURATION.get("enabled", True) and len(formatted_products) >= 4:
                        curated = self._curate_products_with_ai(products=formatted_products, category=rec_lower, style=style_name, room_type=context.space_type or "room", max_products=6)
                        if curated and len(curated) >= 2:
                            if len(curated) > 6:
                                top = curated[:min(10, len(curated))]
                                formatted_products = random.sample(top, min(6, len(top)))
                            else:
                                formatted_products = curated
                            random.shuffle(formatted_products)
                        else:
                            formatted_products = formatted_products[:6]
                    else:
                        formatted_products = formatted_products[:6]
                except Exception:
                    formatted_products = formatted_products[:6]

                latency_ms = int((_time.time() - _start) * 1000)
                self.logger.info(
                    f"Product search complete for '{recommendation}'",
                    extra={
                        "recommendation": recommendation,
                        "strategy": FeatureFlags.SEARCH_STRATEGY,
                        "queries_attempted": queries_attempted,
                        "results_per_source": {"images": img_count, "shopping": shop_count, "exa": exa_count},
                        "filtered_count": filtered_count,
                        "top_filter_reasons": dict(sorted(filter_reasons.items(), key=lambda x: -x[1])[:5]),
                        "total_products": len(formatted_products),
                        "latency_ms": latency_ms,
                        "api_calls": api_call_count,
                    },
                )

                if len(formatted_products) < 4:
                    self.logger.warning(
                        f"Low product count for '{recommendation}': only {len(formatted_products)} products "
                        f"(img={img_count}, shop={shop_count}, exa={exa_count}, filtered={filtered_count})"
                    )

                return {
                    "recommendation": recommendation, "search_query": queries_attempted[0] if queries_attempted else "",
                    "status": "complete", "products": formatted_products,
                    "searched_at": datetime.now().isoformat(), "error_message": None,
                }
            except Exception as e:
                return {
                    "recommendation": recommendation, "search_query": "", "status": "error",
                    "products": [], "searched_at": datetime.now().isoformat(), "error_message": str(e),
                }

        categories = []
        rec_order = {rec: i for i, rec in enumerate(recommendations)}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(search_single_recommendation, rec): rec for rec in recommendations}
            for future in as_completed(futures):
                categories.append(future.result())

                # Persist partial results as each category completes so clients
                # can render real products before the whole job finishes.
                partial_sorted = sorted(
                    categories,
                    key=lambda c: rec_order.get(c.get("recommendation"), 999),
                )
                partial_pre_searched = {
                    cat["recommendation"]: cat
                    for cat in partial_sorted
                    if cat.get("recommendation")
                }
                if partial_pre_searched:
                    self._save_project_fields(
                        project_id,
                        {"pre_searched_categories": partial_pre_searched},
                    )

        categories.sort(key=lambda c: rec_order.get(c["recommendation"], 999))
        pre_searched = {cat["recommendation"]: cat for cat in categories}
        self._save_project_fields(project_id, {"pre_searched_categories": pre_searched})
        total_products = sum(len(cat["products"]) for cat in categories)
        return {
            "project_id": project_id, "categories": categories, "total_products": total_products,
            "ai_selected": len(recommendations) <= 2, "status": "success",
            "message": f"Found {total_products} products across {len(categories)} categories",
        }

    # --- Phase 3: Image generation methods ---

    def generate_product_visualization(self, project_id: str) -> Dict[str, Any]:
        """Generate a product visualization image using Gemini."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        user_id = str(row["user_id"])
        context = self._get_project_context(project_id)
        with self._temp_image(project_id, "base", suffix=".jpg") as tmp_base:
            # Build generation params
            selected_products = context.selected_products or []
            trending = context.selected_trending_products or []
            favorites = context.favorite_products or []
            # Merge favorites into trending (match data_manager.py pattern)
            all_trending = list(trending)
            for fav in favorites[:2]:
                if fav not in all_trending:
                    all_trending.append(fav)
            generated_b64, prompt_used, model_used = self.gemini_client.generate_product_visualization(
                original_room_image_path=tmp_base,
                space_type=context.space_type or "room",
                selected_products=selected_products,
                inspiration_recommendations=context.inspiration_recommendations or [],
                marker_locations=context.improvement_markers or [],
                color_scheme=context.color_scheme,
                design_style=context.design_style,
                improvement_mode=context.improvement_mode,
                custom_prompt=context.generation_prompt,
                trending_products=all_trending,
            )
        # Upload generated image to Storage
        file_bytes = base64.b64decode(generated_b64)
        ts = int(time.time())
        public_url = self._replace_image_in_storage(project_id, user_id, "generated", file_bytes, f"generated_{ts}.png")
        self._save_project_fields(project_id, {
            "generation_prompt": prompt_used, "generation_model_used": model_used,
            "status": "IMAGE_GENERATED",
        })
        log_project_status_change(project_id, row["status"], "IMAGE_GENERATED")
        return {
            "project_id": project_id, "generated_image": generated_b64,
            "generated_image_url": public_url, "prompt": prompt_used,
            "model": model_used, "status": "success",
        }

    def generate_inspiration_redesign(self, project_id: str) -> Dict[str, Any]:
        """Generate a redesigned room image based on inspiration recommendations."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        user_id = str(row["user_id"])
        context = self._get_project_context(project_id)
        if not context.base_image:
            raise ValueError("No base image found")

        # Build prompt based on context (same logic as DataManager)
        has_inspiration = bool(context.inspiration_images) and not context.inspiration_images_skipped
        is_iterative = context.improvement_mode == "iterative"

        # Gather design context
        def clean(s):
            return str(s).replace("{", "{{").replace("}", "}}")

        inspiration_recs = context.inspiration_recommendations or []
        product_recs = (
            context.selected_product_recommendations
            or context.product_recommendations
            or []
        )
        markers = context.improvement_markers or []

        design_goals = []
        if inspiration_recs:
            design_goals.extend(inspiration_recs)
        if product_recs:
            design_goals.extend(product_recs)

        markers_text = ""
        if markers:
            markers_text = "\n".join([f"- {m.description}" for m in markers])

        # Color guidance: user explicit choice wins, AI analysis is secondary
        color_guidance = ""
        if context.color_scheme and isinstance(context.color_scheme, dict):
            user_palette = context.color_scheme.get("palette_name", "")
            if user_palette and user_palette != "ai_decide":
                user_colors = context.color_scheme.get("colors", [])
                color_guidance = f"Color Palette: {user_palette}, Colors: {user_colors}"
        if not color_guidance and context.color_analysis and isinstance(context.color_analysis, dict):
            palette = context.color_analysis.get("palette_name", "")
            primary = context.color_analysis.get("primary_colors", [])
            if palette:
                color_guidance = f"Color Palette: {palette}, Primary Colors: {primary}"

        # Style guidance: user explicit choice wins, AI analysis is secondary
        style_guidance = ""
        if context.design_style and isinstance(context.design_style, dict):
            user_style = context.design_style.get("style_name", "")
            if user_style and user_style != "ai_decide":
                style_guidance = f"Style: {user_style}"
        if not style_guidance and context.style_analysis and isinstance(context.style_analysis, dict):
            style_name = context.style_analysis.get("style_name", "")
            style_materials = context.style_analysis.get("materials", [])
            if style_name:
                style_guidance = f"Style: {style_name}, Materials: {style_materials}"

        selected_products = context.selected_products or []
        product_context = ""
        if selected_products:
            product_lines = [f"- {p.get('title', 'Unknown')} ({p.get('url', '')})" for p in selected_products[:3]]
            favorites = context.favorite_products or []
            if favorites:
                product_lines.extend(
                    [f"- [Favorite] {p.get('title', 'Unknown')}" for p in favorites[:2]]
                )
            product_context = "\n".join(product_lines)

        # Build the prompt
        structural_lockdown = """
STRUCTURAL LOCKDOWN (ABSOLUTE — NO EXCEPTIONS):
You are EDITING the original photograph — NOT creating a new room.
The following elements are LOCKED and must appear IDENTICAL to the original photo:
- Wall positions, angles, colors, and textures
- Ceiling height and features
- Window frames, sizes, positions, and COUNT — do NOT add or remove windows
- Door locations, sizes, and frames — do NOT add or remove doors
- Flooring material, pattern, and boundaries
- Electrical outlets, switches, baseboards, moldings, and trim
- Room dimensions and geometry — the room must be the SAME SIZE
CRITICAL: Do NOT invent, add, or hallucinate any structural element not visible in the original photo.

SPATIAL VERIFICATION (Self-Check Before Output):
- Does the room appear the same physical size as the original?
- Are all walls in the same positions and at the same angles?
- Is the window count and door count identical to the original?
- Do vanishing points and perspective lines match?

Do NOT add walls, windows, doors, arches, columns, or any architectural element not in the original.
Do NOT change room dimensions or make the room appear larger or smaller.
Do NOT assume or infer structural features — only what is VISIBLE in the photo exists."""

        if has_inspiration:
            # Build detailed DESIGN CONTEXT for VAPO-optimized inspiration prompt
            design_context_lines = []

            if inspiration_recs:
                design_context_lines.append("INSPIRATION GOALS:")
                design_context_lines.extend([f"- {clean(rec)}" for rec in inspiration_recs[:5]])
                design_context_lines.append("")

            if markers:
                design_context_lines.append("AREAS TO IMPROVE:")
                design_context_lines.extend([f"- {clean(m.description)}" for m in markers])
                design_context_lines.append("")

            if context.color_analysis and isinstance(context.color_analysis, dict):
                ca = context.color_analysis
                design_context_lines.append("COLOR GUIDELINES:")
                design_context_lines.append(f"- Palette: {clean(ca.get('palette_name', 'Custom'))}")
                if ca.get('primary_colors'):
                    p_colors = []
                    for c in ca.get('primary_colors', []):
                        if isinstance(c, dict):
                            c_str = c.get('hex', '')
                            if c.get('description'):
                                c_str += f" ({c.get('description')})"
                            p_colors.append(c_str)
                        elif isinstance(c, str):
                            p_colors.append(c)
                        else:
                            p_colors.append(str(c))
                    design_context_lines.append(f"- Primary Colors: {clean(', '.join(p_colors))}")
                design_context_lines.append(f"- Lighting Notes: {clean(ca.get('lighting_notes', 'N/A'))}")
                design_context_lines.append("")

            if context.style_analysis and isinstance(context.style_analysis, dict):
                sa = context.style_analysis
                design_context_lines.append("STYLE GUIDELINES:")
                design_context_lines.append(f"- Style: {clean(sa.get('style_name', 'Custom'))}")
                if sa.get('materials'):
                    design_context_lines.append(f"- Materials: {clean(', '.join(sa.get('materials')))}")
                design_context_lines.append(f"- Characteristics: {clean(sa.get('furniture_characteristics', 'N/A'))}")

            design_context_str = "\n".join(design_context_lines) if design_context_lines else "General Modern Upgrade"

            # Build PRODUCT UPDATES for inspiration prompt
            product_list_str = "None specified"
            selected_recs = context.selected_product_recommendations or []
            ai_recs = context.product_recommendations or []
            primary_recs = list(selected_recs) if selected_recs else []
            complementary_recs = []
            if ai_recs:
                non_selected = [r for r in ai_recs if r not in selected_recs]
                complementary_recs = non_selected[:2]

            if primary_recs or complementary_recs:
                parts = []
                if primary_recs:
                    parts.append("PRIMARY CHANGES (User Selected):\n" +
                                 "\n".join([f"- {clean(rec)}" for rec in primary_recs[:5]]))
                if complementary_recs:
                    parts.append("COMPLEMENTARY ENHANCEMENTS (AI Suggested - optional):\n" +
                                 "\n".join([f"- {clean(rec)}" for rec in complementary_recs]))
                product_list_str = "\n\n".join(parts)

            space_type = context.space_type or "living space"

            prompt = f"""### ROLE & OBJECTIVE
You are a master of Architectural Photography and Interior Restoration. Your task is to modify the provided photograph (the input image) by replacing specific furniture and decor while maintaining the exact architectural shell and original camera properties. The goal is a "Real-Life" photograph, not a digital render.

### 1. STRUCTURAL LOCKDOWN (ABSOLUTE REQUIREMENT)
You are EDITING the original room photograph - NOT creating a new room.

COMPARE EVERY GENERATED FRAME TO THE ORIGINAL:
- The room dimensions must be IDENTICAL to the input image
- Furniture scale must match the original room's proportions
- If the original shows a 12x14ft room, the generated image must show the SAME sized space

DO NOT ALTER UNDER ANY CIRCUMSTANCES:
- Wall positions, angles, colors, and textures
- Ceiling height and features
- Window frames, sizes, and positions
- Door locations, sizes, and frames
- Flooring material, pattern, and boundaries
- Electrical outlets and switches

ROOM ORIENTATION RULES:
- The camera viewpoint must be EXACTLY the same as the original
- Wall positions, angles, and distances must remain FIXED
- If a wall is 10ft away in the original, it must appear 10ft away in the output
- The vanishing points and perspective lines must align precisely with the original

SPATIAL PROPORTION CHECK:
- Before finalizing: Does a person of average height fit the same way in both images?
- Do doorways appear the same relative size?
- Are window proportions maintained?
- Is the floor area the same?

PERSPECTIVE: Maintain the exact lens focal length, camera angle, horizon line, and field of view of the original photo.

### 2. PHOTOGRAPHIC REALISM PROTOCOLS (CRITICAL)
LIGHTING PHYSICS: Do not add "magical" light sources. All illumination must come from the existing windows and any visible lamps in the original photo. Shadows must be hard-edged or soft based on the original photo's light direction.
MATERIAL AUTHENTICITY: Avoid the "plastic" AI look at all costs. Wood must show natural grain and micro-scratches; fabrics must show visible weave and realistic folding; metal must show authentic reflections of the room environment, not generic white highlights.
OPTICAL IMPERFECTIONS: Include subtle photographic traits: natural depth of field (slight blur on very foreground or background objects), realistic color grading matching the original photo's white balance, and organic shadows in corners (ambient occlusion).
CAMERA SIMULATION: Treat this as if shot on a professional full-frame DSLR with a 24-35mm lens. Emulate subtle lens characteristics like minor vignetting and natural color fringing at high-contrast edges.

### 3. DESIGN SPECIFICATIONS
SPACE TYPE: {clean(space_type)}

{design_context_str}

FURNITURE UPDATES:
{product_list_str}

IMPORTANT: Prioritize PRIMARY CHANGES (user-selected). COMPLEMENTARY ENHANCEMENTS are optional improvements to consider if they enhance the overall design cohesion.

DECOR & TEXTILES:
- If adding a rug, ensure it tucks realistically under nearby furniture legs.
- Any wall art should have appropriate frames matching the style (e.g., thin black metal for modern, ornate wood for traditional).
- Textiles (curtains, throws, pillows) must show realistic fabric draping and creasing.

DECLUTTERING: Remove all small loose items, trash, and visible cables from desks and floors to create a clean, organized, professional space.

### 4. OUTPUT REQUIREMENT
Generate a high-resolution photograph. If the image looks like a "3D concept render" or has a smooth, plastic, digital art appearance, it has FAILED. It MUST look like a "before and after" photo taken by the same camera in the same physical room. The final image should be indistinguishable from a real photograph shot for a high-end interior design magazine."""
        elif is_iterative:
            prompt = f"""SURGICAL EDIT of this {context.space_type or 'room'}. Make minimal, targeted changes:

Changes requested:
{clean(markers_text) if markers_text else clean(chr(10).join(product_recs[:4]))}

{'Products:' + chr(10) + clean(product_context) if product_context else ''}
{structural_lockdown}

IMPORTANT: Preserve camera angle, lighting, and unchanged areas. Only modify what is explicitly requested."""
        else:
            prompt = f"""COMPREHENSIVE REDESIGN of this {context.space_type or 'room'}.

Design Vision:
{clean(chr(10).join(design_goals[:6]))}

{'Improvement Areas:' + chr(10) + clean(markers_text) if markers_text else ''}
{'Color Guidelines: ' + clean(color_guidance) if color_guidance else ''}
{'Style Guidelines: ' + clean(style_guidance) if style_guidance else ''}
{'Products to incorporate:' + chr(10) + clean(product_context) if product_context else ''}
{structural_lockdown}

Create a photorealistic complete redesign of this room."""

        # Download base room image and call Gemini
        tmp_base = self._download_image_to_tempfile(
            self._get_image_url(project_id, "base"), suffix=".jpg"
        )
        # Pass product dicts directly — gemini_client downloads images itself
        product_images = [p for p in selected_products[:2] if p.get("image_url")]
        # Include user's favorite products from "Like These?" selections
        favorites = context.favorite_products or []
        if favorites:
            existing_urls = {p.get('url') for p in product_images}
            for fav in favorites[:2]:
                if fav.get('image_url') and fav.get('url') not in existing_urls:
                    product_images.append(fav)
                    existing_urls.add(fav.get('url'))
        self.logger.info(
            f"Calling generate_room_redesign(original_room_image_path=..., "
            f"product_images_count={len(product_images)})"
        )

        try:
            generated_b64, model_used = self.gemini_client.generate_room_redesign(
                original_room_image_path=tmp_base,
                prompt=prompt,
                product_images=product_images if product_images else None,
            )
        finally:
            if os.path.exists(tmp_base):
                os.unlink(tmp_base)

        # Upload to Storage
        file_bytes = base64.b64decode(generated_b64)
        ts = int(time.time())
        public_url = self._replace_image_in_storage(project_id, user_id, "inspiration_generated", file_bytes, f"inspiration_generated_{ts}.png")
        self._save_project_fields(project_id, {
            "inspiration_generation_prompt": prompt, "inspiration_model_used": model_used,
            "status": "INSPIRATION_REDESIGN_COMPLETE",
        })
        log_project_status_change(project_id, row["status"], "INSPIRATION_REDESIGN_COMPLETE")
        return {
            "project_id": project_id, "generated_image": generated_b64,
            "generated_image_url": public_url, "prompt": prompt,
            "model": model_used, "status": "success",
        }

    def retry_inspiration_redesign(self, project_id: str, feedback: str) -> Dict[str, Any]:
        """Apply user-directed modifications to the existing generated image."""
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        user_id = str(row["user_id"])
        context = self._get_project_context(project_id)
        # Get current inspiration_generated image
        current_url = self._get_image_url(project_id, "inspiration_generated")
        if not current_url:
            raise ValueError("No generated inspiration image found to edit")
        if not feedback or not feedback.strip():
            raise ValueError("Feedback is required for retry")
        # Download current generated image and convert to base64
        current_bytes = self._get_image_bytes_from_storage(project_id, "inspiration_generated")
        current_b64 = base64.b64encode(current_bytes).decode("utf-8")
        # Call Gemini edit
        edited_b64, model_used, full_prompt = self.gemini_client.edit_room_with_feedback(
            generated_image_base64=current_b64,
            feedback=feedback,
            space_type=context.space_type or "room",
        )
        # Upload edited image
        file_bytes = base64.b64decode(edited_b64)
        ts = int(time.time())
        public_url = self._replace_image_in_storage(project_id, user_id, "inspiration_generated", file_bytes, f"inspiration_generated_{ts}.png")
        self._save_project_fields(project_id, {
            "inspiration_generation_prompt": full_prompt, "inspiration_model_used": model_used,
        })
        log_user_action("retry_redesign", project_id=project_id, feedback=feedback[:50])
        return {
            "project_id": project_id, "generated_image": edited_b64,
            "generated_image_url": public_url, "prompt": full_prompt,
            "model": model_used, "status": "success",
        }

    # --- Phase 4: Advanced features ---

    def _analyze_single_item(self, project_id: str, rect: Any, use_inspiration_image: bool = False) -> Dict[str, Any]:
        """Analyze a single furniture item using CLIP + SERP pipeline."""
        from PIL import Image

        # Get the appropriate image
        image_type = "inspiration_generated" if use_inspiration_image else "generated"
        pil_img, raw_bytes = self._get_pil_image_from_storage(project_id, image_type)
        width, height = pil_img.size

        # Normalize rect
        if hasattr(rect, 'x'):
            rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height
        else:
            rx, ry = rect.get("x", 0.5), rect.get("y", 0.5)
            rw, rh = rect.get("width", 0.1), rect.get("height", 0.1)
        rx = max(0, min(1, rx))
        ry = max(0, min(1, ry))
        rw = max(0.02, min(1 - rx, rw))
        rh = max(0.02, min(1 - ry, rh))

        # Convert to pixel coordinates and crop
        px1, py1 = int(rx * width), int(ry * height)
        px2, py2 = int((rx + rw) * width), int((ry + rh) * height)
        px1, py1 = max(0, px1), max(0, py1)
        px2, py2 = min(width, px2), min(height, py2)
        if px2 - px1 < 10 or py2 - py1 < 10:
            raise ValueError("Selected region is too small")
        crop = pil_img.crop((px1, py1, px2, py2))
        crop = self._prepare_crop_for_search(crop)

        # CLIP analysis
        clip_analysis = None
        search_query = "furniture"
        if self.clip_client and self.clip_client.is_available():
            try:
                crop_ratio = (px2 - px1) / max(py2 - py1, 1)
                clip_result = self.clip_client.analyze_furniture_region(crop, crop_ratio=crop_ratio)
                clip_analysis = clip_result
                search_query = clip_result.get("enhanced_search_query", "") or clip_result.get("furniture_type", "furniture")
            except Exception as e:
                self.logger.warning(f"CLIP analysis failed: {e}")

        # Save crop to temp file for ImgBB upload
        crop_buffer = BytesIO()
        crop.save(crop_buffer, format="JPEG", quality=90)
        crop_b64 = base64.b64encode(crop_buffer.getvalue()).decode()

        # Google Lens reverse image search
        products = []
        lens_products = []
        if self.serp_client:
            imgbb_url = self.upload_image_to_imgbb(crop_b64)
            if imgbb_url:
                try:
                    lens_results = self.serp_client.reverse_image_search(imgbb_url, num_results=10)
                    for i, r in enumerate(lens_results):
                        score = max(0.7, 1.0 - i * 0.03)
                        p = {
                            "title": r.get("title", ""),
                            "url": r.get("link", r.get("url", "")),
                            "thumbnail": r.get("thumbnail", ""),
                            "image_url": r.get("thumbnail", ""),
                            "source": r.get("source", ""),
                            "store": r.get("source", ""),
                            "similarity_score": score,
                            "search_method": "Google Lens",
                        }
                        products.append(p)
                        lens_products.append(p)
                except Exception as e:
                    self.logger.warning(f"Google Lens search failed: {e}")

        # Supplementary text search if Lens returned nothing
        if not lens_products:
            full_query = f"{search_query} buy online"
            if self.serp_client:
                try:
                    text_results = self.serp_client.search_and_analyze_products(query=full_query, space_type="general", num_results=8)
                    for p in text_results:
                        p["search_method"] = "text_search"
                    products.extend(text_results)
                except Exception:
                    pass

        # Deduplicate and validate
        products = self._dedupe_products_by_url(products)
        if self.exa_client and products:
            products = self._validate_product_pages_with_exa(products, max_validate=10)

        return {
            "search_query": search_query,
            "products": products[:12],
            "total_found": len(products),
            "analysis_method": "clip+lens" if clip_analysis else "lens",
            "clip_analysis": clip_analysis,
        }

    def _normalize_clip_text_value(self, value: Any, default: str = "") -> str:
        """Normalize CLIP attribute values to plain strings for API schema compatibility."""
        if value is None:
            return default
        if isinstance(value, str):
            text = value.strip()
            return text or default
        if isinstance(value, dict):
            for key in ("name", "label", "value", "description", "text"):
                raw = value.get(key)
                if isinstance(raw, str) and raw.strip():
                    return raw.strip()
            return default
        text = str(value).strip()
        return text or default

    def _safe_float(self, value: Any, default: float) -> float:
        """Parse float values without raising on bad payloads."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _extract_clip_confidence(self, clip_result: Dict[str, Any]) -> float:
        """Extract confidence from nested CLIP payloads with legacy fallback."""
        furniture_type = clip_result.get("furniture_type")
        nested = (
            self._safe_float(furniture_type.get("confidence"), 0.0)
            if isinstance(furniture_type, dict)
            else 0.0
        )
        scalar = self._safe_float(clip_result.get("confidence"), 0.0)
        return max(nested, scalar)

    def _extract_selection_id(self, selection: Any, index: int) -> str:
        """Extract stable selection id from request payload; fallback to deterministic id."""
        candidate = None
        if hasattr(selection, "id"):
            candidate = getattr(selection, "id")
        elif isinstance(selection, dict):
            candidate = selection.get("id")

        if candidate is not None:
            selection_id = str(candidate).strip()
            if selection_id:
                return selection_id

        return f"sel_{int(time.time() * 1000)}_{index}"

    def _build_furniture_analysis_item(
        self,
        *,
        selection_id: str,
        label: str,
        confidence: float,
        style: str,
        material: str,
        color: str,
        search_query: str,
        products: List[Dict[str, Any]],
        is_bed: bool = False,
        bed_components: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        click_x: Optional[float] = None,
        click_y: Optional[float] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a schema-safe furniture analysis item payload."""
        item: Dict[str, Any] = {
            "id": selection_id,
            "furniture_type": label,
            "confidence": float(confidence),
            "style": style,
            "material": material,
            "color": color,
            "search_query": search_query,
            "products": products,
            "is_bed": is_bed,
            "bed_components": bed_components if is_bed else None,
        }
        if click_x is not None and click_y is not None:
            item["click"] = {"x": click_x, "y": click_y}
        if error:
            item["error"] = error
        return item

    def _flatten_bed_component_products(
        self,
        bed_components: Optional[Dict[str, List[Dict[str, Any]]]],
        *,
        max_items: int = 12,
    ) -> List[Dict[str, Any]]:
        """Flatten bed component products into a top-level product list."""
        if not bed_components:
            return []

        flattened: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for products in bed_components.values():
            if not isinstance(products, list):
                continue
            for raw in products:
                if not isinstance(raw, dict):
                    continue
                url = str(raw.get("url") or raw.get("link") or "").strip()
                title = str(raw.get("title") or raw.get("name") or "").strip().lower()
                key = url or title
                if not key or key in seen:
                    continue
                seen.add(key)

                normalized = dict(raw)
                if "image_url" not in normalized:
                    normalized["image_url"] = normalized.get("thumbnail", "")
                if "store" not in normalized and normalized.get("source"):
                    normalized["store"] = normalized.get("source")

                flattened.append(normalized)
                if len(flattened) >= max_items:
                    return flattened

        return flattened

    def clip_search_products(self, project_id: str, rect: Any, use_inspiration_image: bool = False) -> Dict[str, Any]:
        """CLIP-based product search on a region of the generated image."""
        try:
            result = self._analyze_single_item(project_id, rect, use_inspiration_image)
            log_user_action("clip_search", project_id=project_id, results_count=len(result.get("products", [])))
            return result
        except Exception as e:
            self.logger.error(f"CLIP search failed: {e}", exc_info=True)
            raise

    def _normalize_analysis_mode(self, mode: Optional[str]) -> str:
        """Normalize API mode values while preserving backward compatibility."""
        normalized = (mode or "full").strip().lower()
        if normalized == "click":
            return "full"
        if normalized not in {"full", "fast_prefetch"}:
            return "full"
        return normalized

    def _analysis_mode_profile(self, mode: str) -> Dict[str, float]:
        """Per-mode execution budgets for bounded request latency."""
        if mode == "fast_prefetch":
            return {
                "selection_budget_s": 8.0,
                "detector_init_timeout": 0.5,
                "spatial_timeout": 0.5,
                "clip_timeout": 0.5,
                "imgbb_timeout": 3.0,
                "lens_timeout": 4.0,
                "exa_search_timeout": 0.5,
                "exa_validate_timeout": 0.5,
                "bed_components_timeout": 0.5,
            }
        return {
            "selection_budget_s": 30.0,
            "detector_init_timeout": 2.0,
            "spatial_timeout": 6.0,
            "clip_timeout": 4.0,
            "imgbb_timeout": 6.0,
            "lens_timeout": 8.0,
            "exa_search_timeout": 6.0,
            "exa_validate_timeout": 6.0,
            "bed_components_timeout": 6.0,
        }

    def _log_analysis_step(
        self,
        *,
        project_id: str,
        selection_id: Optional[str],
        mode: str,
        step: str,
        duration_ms: float,
        success: bool,
        timed_out: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Emit structured step-level telemetry for furniture analysis."""
        payload = {
            "selection_id": selection_id,
            "mode": mode,
            "step": step,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "timeout": timed_out,
        }
        if error:
            payload["error"] = error[:200]
        self.logger.info(
            "Furniture analysis step",
            extra={"project_id": project_id, "extra_data": payload},
        )

    def _run_with_timeout(
        self,
        fn: Callable[[], Any],
        timeout_s: float,
        fallback: Any,
        *,
        step: str,
        project_id: str,
        selection_id: Optional[str],
        mode: str,
        timeout_counts: Optional[Dict[str, int]] = None,
    ) -> Any:
        """Run blocking call in a thread with a hard timeout and step logging."""
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

        started = time.monotonic()
        success = False
        timed_out = False
        error_message: Optional[str] = None
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fn)
        try:
            result = future.result(timeout=max(timeout_s, 0.05))
            success = True
            return result
        except FuturesTimeoutError:
            timed_out = True
            error_message = f"{step} timed out after {timeout_s:.2f}s"
            if timeout_counts is not None:
                timeout_counts[step] = timeout_counts.get(step, 0) + 1
            future.cancel()
            return fallback
        except Exception as exc:
            error_message = str(exc)
            return fallback
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            duration_ms = (time.monotonic() - started) * 1000
            self._log_analysis_step(
                project_id=project_id,
                selection_id=selection_id,
                mode=mode,
                step=step,
                duration_ms=duration_ms,
                success=success,
                timed_out=timed_out,
                error=error_message,
            )

    def analyze_furniture_batch(
        self,
        project_id: str,
        selections: List[Any],
        image_type: str = "generated",
        mode: str = "full",
    ) -> Dict[str, Any]:
        """Analyze multiple furniture selections with bounded latency by mode."""
        batch_started = time.monotonic()
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        normalized_mode = self._normalize_analysis_mode(mode)
        profile = self._analysis_mode_profile(normalized_mode)

        use_inspiration = image_type in ("inspiration", "inspiration_generated")
        storage_type = "inspiration_generated" if use_inspiration else "generated"
        pil_img, raw_bytes = self._get_pil_image_from_storage(project_id, storage_type)
        width, height = pil_img.size

        timeout_counts: Dict[str, int] = {}
        results: List[Dict[str, Any]] = []
        detector = None
        if normalized_mode == "full":
            try:
                from spatial_utils import SpatialDetector

                detector = self._run_with_timeout(
                    lambda: SpatialDetector(),
                    profile["detector_init_timeout"],
                    None,
                    step="spatial_init",
                    project_id=project_id,
                    selection_id=None,
                    mode=normalized_mode,
                    timeout_counts=timeout_counts,
                )
            except Exception:
                detector = None

        for idx, sel in enumerate(selections):
            selection_started = time.monotonic()
            selection_id = self._extract_selection_id(sel, idx)
            click_x = 0.5
            click_y = 0.5

            if hasattr(sel, "x"):
                click_x = sel.x
                click_y = sel.y
            elif isinstance(sel, dict):
                click_x = sel.get("x", 0.5)
                click_y = sel.get("y", 0.5)
            else:
                results.append(
                    self._build_furniture_analysis_item(
                        selection_id=selection_id,
                        label="unknown",
                        confidence=0.0,
                        style="",
                        material="",
                        color="",
                        search_query="furniture buy online",
                        products=[],
                        is_bed=False,
                        click_x=0.5,
                        click_y=0.5,
                        error=f"Invalid selection format: {type(sel)}",
                    )
                )
                continue

            click_x = max(0.0, min(1.0, float(click_x)))
            click_y = max(0.0, min(1.0, float(click_y)))

            def remaining_budget() -> float:
                return profile["selection_budget_s"] - (time.monotonic() - selection_started)

            def step_timeout(step_key: str) -> float:
                return max(0.0, min(profile[step_key], remaining_budget()))

            try:
                detection = None
                if normalized_mode == "full" and detector and step_timeout("spatial_timeout") > 0.1:
                    detection = self._run_with_timeout(
                        lambda: detector.get_object_bbox(
                            raw_bytes,
                            click_x=click_x,
                            click_y=click_y,
                            image_width=width,
                            image_height=height,
                            space_type=context.space_type,
                        ),
                        step_timeout("spatial_timeout"),
                        None,
                        step="spatial_detect",
                        project_id=project_id,
                        selection_id=selection_id,
                        mode=normalized_mode,
                        timeout_counts=timeout_counts,
                    )
                    detection = self._normalize_spatial_detection(
                        detection,
                        click_x=click_x,
                        click_y=click_y,
                    )
                    if detection:
                        detection = self._validate_click_on_primary(
                            detection,
                            click_x,
                            click_y,
                        )

                label = "furniture"
                bbox_normalized = self._coerce_bbox_normalized(
                    None,
                    click_x=click_x,
                    click_y=click_y,
                    box_size=0.24 if normalized_mode == "fast_prefetch" else 0.20,
                )
                attributes: Dict[str, Any] = {"style": "", "material": "", "color": ""}
                search_query = "furniture buy online"
                confidence_score = 0.7

                if detection:
                    label = self._normalize_clip_text_value(
                        detection.get("label"),
                        default="furniture",
                    )
                    bbox_normalized = self._coerce_bbox_normalized(
                        detection.get("bbox_normalized"),
                        click_x=click_x,
                        click_y=click_y,
                    )
                    attrs = detection.get("attributes") or {}
                    attributes = {
                        "style": self._normalize_clip_text_value(attrs.get("style"), default=""),
                        "material": self._normalize_clip_text_value(
                            attrs.get("material"), default=""
                        ),
                        "color": self._normalize_clip_text_value(attrs.get("color"), default=""),
                    }
                    search_query = self._normalize_clip_text_value(
                        detection.get("search_query"),
                        default=f"{label} buy online",
                    )
                    confidence_score = self._safe_float(
                        detection.get("confidence"),
                        confidence_score,
                    )

                crop_started = time.monotonic()
                pad = 0.03 if normalized_mode == "fast_prefetch" else 0.05
                ymin, xmin, ymax, xmax = bbox_normalized
                cy1 = max(0.0, ymin - pad)
                cx1 = max(0.0, xmin - pad)
                cy2 = min(1.0, ymax + pad)
                cx2 = min(1.0, xmax + pad)
                px1, py1 = int(cx1 * width), int(cy1 * height)
                px2, py2 = int(cx2 * width), int(cy2 * height)
                if px2 - px1 < 10 or py2 - py1 < 10:
                    fallback = self._coerce_bbox_normalized(
                        None,
                        click_x=click_x,
                        click_y=click_y,
                    )
                    fy1, fx1, fy2, fx2 = fallback
                    py1, px1 = int(fy1 * height), int(fx1 * width)
                    py2, px2 = int(fy2 * height), int(fx2 * width)
                crop = pil_img.crop((px1, py1, px2, py2))
                crop = self._prepare_crop_for_search(crop)
                self._log_analysis_step(
                    project_id=project_id,
                    selection_id=selection_id,
                    mode=normalized_mode,
                    step="crop_prepare",
                    duration_ms=(time.monotonic() - crop_started) * 1000,
                    success=True,
                )

                if (
                    normalized_mode == "full"
                    and self.clip_client
                    and self.clip_client.is_available()
                    and step_timeout("clip_timeout") > 0.1
                ):
                    crop_ratio = (px2 - px1) / max(py2 - py1, 1)
                    clip_result = self._run_with_timeout(
                        lambda: self.clip_client.analyze_furniture_region(
                            crop,
                            crop_ratio=crop_ratio,
                        ),
                        step_timeout("clip_timeout"),
                        None,
                        step="clip_enrich",
                        project_id=project_id,
                        selection_id=selection_id,
                        mode=normalized_mode,
                        timeout_counts=timeout_counts,
                    )
                    if isinstance(clip_result, dict):
                        clip_confidence = self._extract_clip_confidence(clip_result)
                        if clip_confidence > 0.5:
                            clip_type = self._normalize_clip_text_value(
                                clip_result.get("furniture_type"),
                                default=label,
                            )
                            if label == "furniture":
                                label = clip_type
                            confidence_score = max(confidence_score, clip_confidence)
                            attributes = {
                                "style": self._normalize_clip_text_value(
                                    clip_result.get("style"),
                                    default=attributes.get("style", ""),
                                ),
                                "material": self._normalize_clip_text_value(
                                    clip_result.get("material"),
                                    default=attributes.get("material", ""),
                                ),
                                "color": self._normalize_clip_text_value(
                                    clip_result.get("color"),
                                    default=attributes.get("color", ""),
                                ),
                            }
                            search_query = self._normalize_clip_text_value(
                                clip_result.get("search_query"),
                                default=search_query,
                            )

                crop_buffer = BytesIO()
                crop.save(crop_buffer, format="JPEG", quality=90)
                crop_b64_search = base64.b64encode(crop_buffer.getvalue()).decode()

                search_products: List[Dict[str, Any]] = []
                lens_products: List[Dict[str, Any]] = []
                if self.serp_client and step_timeout("imgbb_timeout") > 0.1:
                    imgbb_url = self._run_with_timeout(
                        lambda: self.upload_image_to_imgbb(crop_b64_search),
                        step_timeout("imgbb_timeout"),
                        None,
                        step="imgbb_upload",
                        project_id=project_id,
                        selection_id=selection_id,
                        mode=normalized_mode,
                        timeout_counts=timeout_counts,
                    )
                    if imgbb_url and step_timeout("lens_timeout") > 0.1:
                        lens_results = self._run_with_timeout(
                            lambda: self.serp_client.reverse_image_search(
                                imgbb_url,
                                num_results=12 if normalized_mode == "full" else 8,
                            ),
                            step_timeout("lens_timeout"),
                            [],
                            step="lens_search",
                            project_id=project_id,
                            selection_id=selection_id,
                            mode=normalized_mode,
                            timeout_counts=timeout_counts,
                        )
                        for i, r in enumerate(lens_results or []):
                            product = {
                                "title": r.get("title", ""),
                                "url": r.get("link", r.get("url", "")),
                                "thumbnail": r.get("thumbnail", ""),
                                "image_url": r.get("thumbnail", ""),
                                "source": r.get("source", ""),
                                "store": r.get("source", ""),
                                "similarity_score": max(0.7, 1.0 - i * 0.025),
                            }
                            search_products.append(product)
                            lens_products.append(product)

                if (
                    normalized_mode == "full"
                    and self.exa_client
                    and attributes
                    and step_timeout("exa_search_timeout") > 0.1
                ):
                    multi_queries = self._generate_multi_queries(label, attributes)
                    for query in multi_queries[:2]:
                        if step_timeout("exa_search_timeout") <= 0.1:
                            break
                        exa_results = self._run_with_timeout(
                            lambda q=query: self.exa_client.search_and_analyze_products(
                                query=q,
                                space_type=context.space_type or "general",
                                num_results=6,
                                similar_per_seed=2,
                            ),
                            step_timeout("exa_search_timeout"),
                            [],
                            step="exa_search",
                            project_id=project_id,
                            selection_id=selection_id,
                            mode=normalized_mode,
                            timeout_counts=timeout_counts,
                        )
                        search_products.extend(exa_results or [])

                search_products = self._dedupe_products_by_url(search_products)
                if (
                    normalized_mode == "full"
                    and self.exa_client
                    and search_products
                    and step_timeout("exa_validate_timeout") > 0.1
                ):
                    search_products = self._run_with_timeout(
                        lambda: self._validate_product_pages_with_exa(
                            search_products,
                            max_validate=8,
                        ),
                        step_timeout("exa_validate_timeout"),
                        search_products,
                        step="exa_validate",
                        project_id=project_id,
                        selection_id=selection_id,
                        mode=normalized_mode,
                        timeout_counts=timeout_counts,
                    )
                search_products = search_products[:12]

                is_bed = self._is_actual_bed(label)
                bed_components = None
                if (
                    normalized_mode == "full"
                    and is_bed
                    and step_timeout("bed_components_timeout") > 0.1
                ):
                    bed_comps = self._run_with_timeout(
                        lambda: self._detect_bed_sub_components(crop_b64_search),
                        step_timeout("bed_components_timeout"),
                        {},
                        step="bed_components",
                        project_id=project_id,
                        selection_id=selection_id,
                        mode=normalized_mode,
                        timeout_counts=timeout_counts,
                    )
                    if bed_comps:
                        bed_components = self._run_with_timeout(
                            lambda: self._search_bed_components(
                                label, attributes, lens_products, context
                            ),
                            step_timeout("bed_components_timeout"),
                            None,
                            step="bed_components",
                            project_id=project_id,
                            selection_id=selection_id,
                            mode=normalized_mode,
                            timeout_counts=timeout_counts,
                        )

                if is_bed and not search_products and bed_components:
                    search_products = self._flatten_bed_component_products(
                        bed_components,
                        max_items=12,
                    )

                results.append(
                    self._build_furniture_analysis_item(
                        selection_id=selection_id,
                        label=self._normalize_clip_text_value(label, default="furniture"),
                        confidence=confidence_score,
                        style=self._normalize_clip_text_value(
                            attributes.get("style"), default=""
                        ),
                        material=self._normalize_clip_text_value(
                            attributes.get("material"), default=""
                        ),
                        color=self._normalize_clip_text_value(
                            attributes.get("color"), default=""
                        ),
                        search_query=search_query,
                        products=search_products,
                        is_bed=is_bed,
                        bed_components=bed_components,
                        click_x=click_x,
                        click_y=click_y,
                    )
                )
            except Exception as exc:
                self.logger.error(
                    f"Furniture analysis failed for selection {selection_id}: {exc}",
                    exc_info=True,
                )
                results.append(
                    self._build_furniture_analysis_item(
                        selection_id=selection_id,
                        label="unknown",
                        confidence=0.0,
                        style="",
                        material="",
                        color="",
                        search_query="furniture buy online",
                        products=[],
                        is_bed=False,
                        click_x=click_x,
                        click_y=click_y,
                        error=str(exc),
                    )
                )

        completed_count = sum(1 for item in results if not item.get("error"))
        self.logger.info(
            "Furniture analysis batch complete",
            extra={
                "project_id": project_id,
                "extra_data": {
                    "mode": normalized_mode,
                    "selection_count": len(selections),
                    "completed_count": completed_count,
                    "timeouts_by_step": timeout_counts,
                    "total_duration_ms": round((time.monotonic() - batch_started) * 1000, 2),
                },
            },
        )
        return {
            "project_id": project_id,
            "selections": results,
            "overall_analysis": (
                f"Analyzed {completed_count}/{len(selections)} furniture items "
                f"(mode={normalized_mode})"
            ),
            "status": "success",
        }

    def reverse_search_batch(self, project_id: str, selections: List[Any], image_type: str = "generated") -> Dict[str, Any]:
        """Perform Google Lens reverse image search for multiple selections."""
        from PIL import Image

        use_inspiration = image_type in ("inspiration", "inspiration_generated")
        storage_type = "inspiration_generated" if use_inspiration else "generated"
        pil_img, _ = self._get_pil_image_from_storage(project_id, storage_type)
        width, height = pil_img.size

        results = []
        for sel in selections:
            if hasattr(sel, 'x'):
                click_x, click_y = sel.x, sel.y
            elif isinstance(sel, dict):
                click_x, click_y = sel.get("x", 0.5), sel.get("y", 0.5)
            else:
                continue

            # Extract 12% crop around click
            pad = 0.06
            x1 = max(0, click_x - pad)
            y1 = max(0, click_y - pad)
            x2 = min(1, click_x + pad)
            y2 = min(1, click_y + pad)
            px1, py1 = int(x1 * width), int(y1 * height)
            px2, py2 = int(x2 * width), int(y2 * height)
            crop = pil_img.crop((px1, py1, px2, py2))

            crop_buffer = BytesIO()
            crop.save(crop_buffer, format="JPEG", quality=90)
            crop_b64 = base64.b64encode(crop_buffer.getvalue()).decode()

            matches = []
            imgbb_url = self.upload_image_to_imgbb(crop_b64)
            if imgbb_url and self.serp_client:
                try:
                    lens_results = self.serp_client.reverse_image_search(imgbb_url, num_results=10)
                    for r in lens_results:
                        matches.append({
                            "title": r.get("title", ""), "url": r.get("link", r.get("url", "")),
                            "source": r.get("source", ""), "thumbnail": r.get("thumbnail", ""),
                            "match_type": "visual_match",
                        })
                except Exception as e:
                    self.logger.warning(f"Reverse search failed: {e}")

            # Validate with Exa
            if self.exa_client and len(matches) >= 3:
                validated = self._validate_product_pages_with_exa(matches, max_validate=8)
                if len(validated) >= 3:
                    matches = validated

            results.append({
                "click": {"x": click_x, "y": click_y},
                "image_url": imgbb_url, "matches": matches,
            })

        return {"project_id": project_id, "results": results, "status": "success"}

    def _rect_iou(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        """Compute IoU for two normalized rect dicts."""
        ar = a.get("rect") or {}
        br = b.get("rect") or {}
        ax1 = float(ar.get("x", 0.0))
        ay1 = float(ar.get("y", 0.0))
        ax2 = ax1 + float(ar.get("width", 0.0))
        ay2 = ay1 + float(ar.get("height", 0.0))
        bx1 = float(br.get("x", 0.0))
        by1 = float(br.get("y", 0.0))
        bx2 = bx1 + float(br.get("width", 0.0))
        by2 = by1 + float(br.get("height", 0.0))
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        area_a = max(0.0, (ax2 - ax1) * (ay2 - ay1))
        area_b = max(0.0, (bx2 - bx1) * (by2 - by1))
        union = area_a + area_b - inter_area
        if union <= 0:
            return 0.0
        return inter_area / union

    def _auto_detect_with_gemini(
        self,
        pil_img: Any,
        raw_bytes: bytes,
    ) -> List[Dict[str, Any]]:
        """Gemini full-image furniture localization."""
        from pydantic import BaseModel, Field
        from typing import List as TypeList

        class GeminiObject(BaseModel):
            label: str = "furniture"
            bbox: TypeList[float] = Field(default_factory=list)
            confidence: float = 0.7

        class GeminiDetections(BaseModel):
            detections: TypeList[GeminiObject] = Field(default_factory=list)

        if not self.gemini_client:
            return []

        mime_type = "image/jpeg"
        if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
        elif raw_bytes.startswith(b"RIFF") and raw_bytes[8:12] == b"WEBP":
            mime_type = "image/webp"

        image_b64 = base64.b64encode(raw_bytes).decode("utf-8")
        prompt = (
            "Detect visible furniture and decor objects in this room image. "
            "Return up to 12 objects with labels and normalized bounding boxes. "
            "Bounding boxes must use [ymin, xmin, ymax, xmax] on a 0-1000 scale. "
            "Return only major objects users can tap for product shopping "
            "(sofa, chair, table, bed, lamp, rug, dresser, shelf, cabinet, mirror)."
        )
        response = self.gemini_client.analyze_images_with_vision(
            prompt=prompt,
            pydantic_model=GeminiDetections,
            image_parts=[
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_b64,
                    }
                }
            ],
            system_message=(
                "You are an object detector for interior design shopping. "
                "Output concise object labels and accurate boxes."
            ),
        )
        detections: List[Dict[str, Any]] = []
        for item in response.detections[:12]:
            if len(item.bbox) != 4:
                continue
            bbox_norm = [max(0.0, min(1.0, float(v) / 1000.0)) for v in item.bbox]
            ymin, xmin, ymax, xmax = self._coerce_bbox_normalized(
                bbox_norm,
                click_x=0.5,
                click_y=0.5,
            )
            width = max(0.0, xmax - xmin)
            height = max(0.0, ymax - ymin)
            if width < 0.02 or height < 0.02:
                continue
            detections.append(
                {
                    "label": self._normalize_clip_text_value(item.label, default="furniture"),
                    "rect": {
                        "x": xmin,
                        "y": ymin,
                        "width": width,
                        "height": height,
                    },
                    "center": {"x": (xmin + xmax) / 2, "y": (ymin + ymax) / 2},
                    "confidence": max(0.0, min(1.0, float(item.confidence))),
                    "source": "gemini",
                }
            )
        return detections

    def _auto_detect_with_yolo(self, pil_img: Any) -> List[Dict[str, Any]]:
        """YOLO fallback detector with normalized fields."""
        from ultralytics import YOLO

        width, height = pil_img.size
        model = YOLO("yolov8n.pt")
        raw_results = model.predict(pil_img, imgsz=640, conf=0.35, verbose=False)
        detections: List[Dict[str, Any]] = []
        for result in raw_results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = model.names.get(cls_id, "object")
                confidence = float(box.conf[0]) if hasattr(box, "conf") else 0.0
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                nx1, ny1 = max(0.0, x1 / width), max(0.0, y1 / height)
                nx2, ny2 = min(1.0, x2 / width), min(1.0, y2 / height)
                nw, nh = max(0.0, nx2 - nx1), max(0.0, ny2 - ny1)
                if nw < 0.02 or nh < 0.02:
                    continue
                detections.append(
                    {
                        "label": label,
                        "rect": {"x": nx1, "y": ny1, "width": nw, "height": nh},
                        "center": {"x": (nx1 + nx2) / 2, "y": (ny1 + ny2) / 2},
                        "confidence": max(0.0, min(1.0, confidence)),
                        "source": "yolo",
                    }
                )
        return detections

    def _merge_and_dedupe_detections(
        self,
        detections: List[Dict[str, Any]],
        iou_threshold: float = 0.55,
    ) -> List[Dict[str, Any]]:
        """Merge detections from multiple sources and remove heavy overlaps."""
        source_priority = {"gemini": 2, "yolo": 1, "synthetic_split": 0}
        ranked = sorted(
            detections,
            key=lambda d: (
                float(d.get("confidence", 0.0)),
                source_priority.get(str(d.get("source", "")), -1),
            ),
            reverse=True,
        )
        merged: List[Dict[str, Any]] = []
        for candidate in ranked:
            rect = candidate.get("rect") or {}
            if (
                float(rect.get("width", 0.0)) <= 0.0
                or float(rect.get("height", 0.0)) <= 0.0
            ):
                continue
            if any(self._rect_iou(candidate, kept) >= iou_threshold for kept in merged):
                continue
            merged.append(candidate)
        return merged

    def _synthesize_sub_hotspots_for_large_box(
        self,
        detections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Add synthetic hotspots when only one huge detection is available."""
        if len(detections) >= 4 or not detections:
            return detections

        def _area(det: Dict[str, Any]) -> float:
            rect = det.get("rect") or {}
            return float(rect.get("width", 0.0)) * float(rect.get("height", 0.0))

        largest = max(detections, key=_area)
        largest_area = _area(largest)
        if largest_area < 0.45:
            return detections

        rect = largest.get("rect") or {}
        x = float(rect.get("x", 0.0))
        y = float(rect.get("y", 0.0))
        w = float(rect.get("width", 0.0))
        h = float(rect.get("height", 0.0))
        if w <= 0 or h <= 0:
            return detections

        result = list(detections)
        base_label = str(largest.get("label", "furniture"))
        base_conf = float(largest.get("confidence", 0.5))
        anchors = [(0.32, 0.35), (0.68, 0.35), (0.50, 0.68)]
        for ax, ay in anchors:
            child_w = min(0.22, w * 0.35)
            child_h = min(0.22, h * 0.35)
            cx = max(0.0, min(1.0, x + w * ax))
            cy = max(0.0, min(1.0, y + h * ay))
            child_x = max(0.0, min(1.0 - child_w, cx - child_w / 2))
            child_y = max(0.0, min(1.0 - child_h, cy - child_h / 2))
            synthetic = {
                "label": base_label,
                "rect": {
                    "x": child_x,
                    "y": child_y,
                    "width": child_w,
                    "height": child_h,
                },
                "center": {"x": cx, "y": cy},
                "confidence": max(0.2, min(0.8, base_conf * 0.7)),
                "source": "synthetic_split",
            }
            if any(self._rect_iou(synthetic, existing) > 0.70 for existing in result):
                continue
            result.append(synthetic)
            if len(result) >= 4:
                break
        return result

    def auto_detect_furniture(
        self,
        project_id: str,
        image_type: str = "generated",
    ) -> Dict[str, Any]:
        """Auto-detect furniture with Gemini-first and YOLO fallback."""
        detect_started = time.monotonic()
        use_inspiration = image_type in ("inspiration", "inspiration_generated")
        storage_type = "inspiration_generated" if use_inspiration else "generated"
        pil_img, raw_bytes = self._get_pil_image_from_storage(project_id, storage_type)

        timeout_counts: Dict[str, int] = {}
        gemini_detections: List[Dict[str, Any]] = []
        if self.gemini_client:
            gemini_detections = self._run_with_timeout(
                lambda: self._auto_detect_with_gemini(pil_img, raw_bytes),
                10.0,
                [],
                step="gemini_full_detect",
                project_id=project_id,
                selection_id=None,
                mode="auto_detect",
                timeout_counts=timeout_counts,
            )

        yolo_detections: List[Dict[str, Any]] = []
        if len(gemini_detections) < 2:
            yolo_detections = self._run_with_timeout(
                lambda: self._auto_detect_with_yolo(pil_img),
                8.0,
                [],
                step="yolo_detect",
                project_id=project_id,
                selection_id=None,
                mode="auto_detect",
                timeout_counts=timeout_counts,
            )

        merged = self._merge_and_dedupe_detections(gemini_detections + yolo_detections)
        final_detections = self._synthesize_sub_hotspots_for_large_box(merged)
        final_detections = self._merge_and_dedupe_detections(final_detections, iou_threshold=0.65)

        self.logger.info(
            "Auto-detect furniture complete",
            extra={
                "project_id": project_id,
                "extra_data": {
                    "image_type": image_type,
                    "gemini_count": len(gemini_detections),
                    "yolo_count": len(yolo_detections),
                    "final_count": len(final_detections),
                    "timeouts_by_step": timeout_counts,
                    "total_duration_ms": round((time.monotonic() - detect_started) * 1000, 2),
                },
            },
        )
        return {"project_id": project_id, "detections": final_detections, "status": "success"}

    def process_furniture_selection(self, project_id: str, selected_products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process selected furniture products with URL resolution and affiliate cart."""
        # Step 1: URL resolution
        resolved_products = []
        for p in selected_products:
            original_url = p.get("url", "")
            resolved_url = original_url
            was_google_shopping = "google.com/shopping" in original_url.lower()
            if was_google_shopping and self.exa_client:
                try:
                    validation = self.exa_client.validate_product_urls_batch(urls=[original_url], batch_size=1, max_chars=2000)
                    if original_url in validation and validation[original_url].get("resolved_url"):
                        resolved_url = validation[original_url]["resolved_url"]
                except Exception:
                    pass
            resolved_products.append({
                "original_url": original_url, "resolved_url": resolved_url,
                "title": p.get("title", ""), "image_url": p.get("image_url", ""),
                "store": p.get("store", ""), "price_str": p.get("price_str", ""),
                "was_google_shopping": was_google_shopping,
                "affiliate_url": None, "product_id": None,
            })

        # Step 2: Generate affiliate carts
        retailer_carts = []
        if self.affiliate_client:
            try:
                urls = [p["resolved_url"] for p in resolved_products]
                cart_result = self.affiliate_client.generate_carts(urls)
                if cart_result:
                    for retailer, cart in cart_result.items():
                        retailer_carts.append({
                            "retailer": retailer, "display_name": cart.get("display_name", retailer),
                            "products": cart.get("products", []), "cart_url": cart.get("cart_url", ""),
                            "product_count": len(cart.get("products", [])),
                        })
            except Exception as e:
                self.logger.warning(f"Affiliate cart generation failed: {e}")

        return {
            "resolved_products": resolved_products, "retailer_carts": retailer_carts,
            "total_products": len(resolved_products),
            "resolved_count": sum(1 for p in resolved_products if p["resolved_url"] != p["original_url"]),
            "unresolved_count": sum(1 for p in resolved_products if p["resolved_url"] == p["original_url"] and p["was_google_shopping"]),
        }

    def replicate_segment(self, project_id: str, image_type: str = "generated", public_image_url: str = None) -> Dict[str, Any]:
        """Run segmentation for furniture detection."""
        use_inspiration = image_type in ("inspiration", "inspiration_generated")
        storage_type = "inspiration_generated" if use_inspiration else "generated"

        # Use Supabase Storage public URL directly if no URL provided
        if not public_image_url:
            public_image_url = self._get_image_url(project_id, storage_type)
        if not public_image_url:
            # Fallback to YOLO
            return self.auto_detect_furniture(project_id, image_type)

        try:
            from replicate_client import ReplicateSegmentationClient
            client = ReplicateSegmentationClient()
            raw_detections = client.segment(public_image_url)
            # Normalize pixel coordinates to 0-1
            pil_img, _ = self._get_pil_image_from_storage(project_id, storage_type)
            width, height = pil_img.size
            detections = []
            for d in raw_detections:
                bbox = d.get("bbox", {})
                x1, y1 = bbox.get("x1", 0) / width, bbox.get("y1", 0) / height
                x2, y2 = bbox.get("x2", 0) / width, bbox.get("y2", 0) / height
                detections.append({
                    "label": d.get("label", "object"),
                    "rect": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                    "center": {"x": (x1 + x2) / 2, "y": (y1 + y2) / 2},
                })
            return {"project_id": project_id, "detections": detections, "status": "success"}
        except Exception as e:
            self.logger.warning(f"Replicate segmentation failed: {e}, falling back to YOLO")
            return self.auto_detect_furniture(project_id, image_type)

    # --- Phase 5: Async methods ---

    async def search_single_recommendation_async(self, recommendation: str, context: ProjectContext, app_state) -> Dict[str, Any]:
        """Search products for a single recommendation with full parallelization."""
        from async_utils import to_thread_with_sem, gather_with_timeout, cache_key, get_or_compute, timed
        sems = app_state.sems
        search_cache = app_state.search_cache
        in_flight = app_state.in_flight
        timings = {}
        rec_lower = recommendation.lower()
        for prefix in ["add ", "change ", "replace ", "install ", "hang ", "place "]:
            if rec_lower.startswith(prefix):
                rec_lower = rec_lower[len(prefix):]
                break
        style_name = ""
        if context.style_analysis and isinstance(context.style_analysis, dict):
            style_name = context.style_analysis.get("style_name", "modern")
        query_variations = [
            f"trending {rec_lower}", f"best {rec_lower} 2025", f"popular {rec_lower}",
            f"{style_name} {rec_lower}" if style_name else f"modern {rec_lower}",
            f"buy {rec_lower} online", f"{rec_lower} furniture",
        ]
        random.shuffle(query_variations)

        async def search_single_variation(query: str) -> List[Dict]:
            full_query = f"{query} -ideas -inspiration -diy -tutorial -plans -woodworking -blueprint -project -pattern -PDF"
            async def cached_serp():
                if not self.serp_client:
                    return []
                key = cache_key(full_query, "serp")
                return await get_or_compute(in_flight, search_cache, key,
                    lambda: to_thread_with_sem(sems["serp"], self.serp_client.search_and_analyze_products, full_query, context.space_type or "general", 10), ttl=600)
            async def cached_exa():
                if not self.exa_client:
                    return []
                key = cache_key(full_query, "exa")
                return await get_or_compute(in_flight, search_cache, key,
                    lambda: to_thread_with_sem(sems["exa"], self.exa_client.search_and_analyze_products, full_query, context.space_type or "general", 8, 2), ttl=600)
            async def cached_images():
                if not self.serp_client:
                    return []
                iq = f"{rec_lower} furniture buy online"
                key = cache_key(iq, "images")
                return await get_or_compute(in_flight, search_cache, key,
                    lambda: to_thread_with_sem(sems["img_search"], self.serp_client.search_images, iq, 10), ttl=600)
            results = await gather_with_timeout([cached_serp(), cached_exa(), cached_images()], timeout=15.0)
            products = []
            serp_r = results[0] if not isinstance(results[0], Exception) else []
            exa_r = results[1] if not isinstance(results[1], Exception) else []
            img_r = results[2] if not isinstance(results[2], Exception) else []
            for p in serp_r:
                p["source_api"] = "serp"
                p["search_query"] = query
            products.extend(serp_r)
            for p in exa_r:
                p["source_api"] = "exa"
                p["search_query"] = query
            products.extend(exa_r)
            for img in img_r:
                image_url = img.get("thumbnail") or img.get("image_url") or ""
                products.append({"title": img.get("title", ""), "url": img.get("url", ""), "thumbnail": image_url, "image_url": image_url, "source": img.get("source", "Unknown"), "store": img.get("source", "Unknown"), "source_api": "google_images", "search_query": query})
            return products

        async def limited_variation(query: str):
            async with sems["variation"]:
                return await search_single_variation(query)
        async with timed("all_variations", timings):
            all_results = await asyncio.gather(*[limited_variation(q) for q in query_variations], return_exceptions=True)
        products = []
        for result in all_results:
            if isinstance(result, list):
                products.extend(result)
        products = self._dedupe_products_by_url(products)
        formatted = []
        for p in products:
            images_array = p.get("images") or []
            image_url = p.get("thumbnail") or p.get("image_url") or (images_array[0] if images_array else None) or p.get("image") or ""
            formatted.append({
                "url": p.get("url", p.get("product_link", p.get("link", ""))),
                "title": p.get("title", ""), "image_url": image_url,
                "store": p.get("store", p.get("source", "Unknown")),
                "price_str": p.get("price_str", str(p.get("price", "")) if p.get("price") else ""),
                "price": p.get("price") if isinstance(p.get("price"), (int, float)) else None,
                "similarity_score": p.get("similarity_score"),
            })
        formatted = self._filter_products_with_images(formatted, min_count=4)

        # Retry with broader query if too few products
        if len(formatted) < 4 and self.serp_client:
            fallback_query = f"{rec_lower} buy online"
            try:
                retry_images = await to_thread_with_sem(
                    sems["img_search"],
                    self.serp_client.search_images,
                    fallback_query,
                    20,
                )
                retry_products = []
                for img in retry_images:
                    image_url = img.get("thumbnail") or img.get("image_url") or ""
                    if not image_url or len(image_url) < 10:
                        continue
                    retry_products.append({
                        "url": img.get("url", ""),
                        "title": img.get("title", ""),
                        "image_url": image_url,
                        "store": img.get("source", "Unknown"),
                    })
                existing_urls = {p.get("url", "") for p in formatted}
                for p in retry_products:
                    if p["url"] and p["url"] not in existing_urls:
                        formatted.append(p)
                        existing_urls.add(p["url"])
                    if len(formatted) >= 6:
                        break
                self.logger.info(
                    f"Async retry search for '{recommendation}': now have {len(formatted)} products"
                )
            except Exception as retry_err:
                self.logger.warning(f"Async retry search failed for '{recommendation}': {retry_err}")

        if len(formatted) < 4:
            self.logger.warning(
                f"Low product count for '{recommendation}': only {len(formatted)} products"
            )

        if len(formatted) > 6:
            formatted = random.sample(formatted, 6)
        return {
            "recommendation": recommendation, "search_query": query_variations[0] if query_variations else "",
            "status": "complete", "products": formatted,
            "searched_at": datetime.now().isoformat(), "debug_timings": timings, "error_message": None,
        }

    async def search_products_for_recommendations_async(self, project_id: str, recommendations: List[str], app_state) -> Dict[str, Any]:
        """Search for products for each recommendation in parallel (async version)."""
        from async_utils import timed
        timings = {}
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")
        context = self._get_project_context(project_id)
        if len(recommendations) > 2:
            recommendations = recommendations[:2]
        rec_order = {rec: i for i, rec in enumerate(recommendations)}
        categories: List[Dict[str, Any]] = []
        async with timed("all_recommendations", timings):
            tasks = [
                asyncio.create_task(
                    self.search_single_recommendation_async(rec, context, app_state)
                )
                for rec in recommendations
            ]
            try:
                for task in asyncio.as_completed(tasks, timeout=60.0):
                    try:
                        result = await task
                    except Exception as task_err:
                        self.logger.warning(
                            f"Async recommendation search failed for one category: {task_err}",
                        )
                        continue

                    if isinstance(result, dict) and result.get("status") == "complete":
                        categories.append(result)
                        partial_sorted = sorted(
                            categories,
                            key=lambda c: rec_order.get(c.get("recommendation"), 999),
                        )
                        partial_pre_searched = {
                            cat["recommendation"]: cat
                            for cat in partial_sorted
                            if cat.get("recommendation")
                        }
                        if partial_pre_searched:
                            self._save_project_fields(
                                project_id,
                                {"pre_searched_categories": partial_pre_searched},
                            )
            except TimeoutError:
                self.logger.warning(
                    "Async recommendation search timed out at 60s; returning partial categories",
                    extra={
                        "project_id": project_id,
                        "completed_categories": len(categories),
                        "requested_categories": len(recommendations),
                    },
                )
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
        categories.sort(key=lambda c: rec_order.get(c["recommendation"], 999))
        pre_searched = {cat["recommendation"]: cat for cat in categories}
        self._save_project_fields(project_id, {"pre_searched_categories": pre_searched})
        total_products = sum(len(cat.get("products", [])) for cat in categories)
        return {
            "project_id": project_id, "categories": categories, "total_products": total_products,
            "ai_selected": len(recommendations) <= 2, "status": "success",
            "message": f"Found {total_products} products across {len(categories)} categories",
            "debug_timings": timings,
        }

    async def apply_color_and_style_parallel(
        self, project_id: str, color_let_ai_decide: bool, style_let_ai_decide: bool,
        color_palette_name: Optional[str], color_colors: Optional[List[str]],
        style_name: Optional[str], app_state,
    ) -> Dict[str, Any]:
        """Run color and style analysis in parallel."""
        from async_utils import to_thread_with_sem, gather_with_timeout, timed
        sems = app_state.sems
        timings = {}
        row = self._get_project_row(project_id)
        if not row:
            raise ValueError(f"Project {project_id} not found")

        async def run_color():
            async with timed("color_analysis", timings):
                return await to_thread_with_sem(
                    sems["llm"], self.apply_color_scheme, project_id,
                    color_palette_name or "AI Selected", color_colors or [], color_let_ai_decide,
                )

        async def run_style():
            async with timed("style_analysis", timings):
                return await to_thread_with_sem(
                    sems["llm"], self.apply_style, project_id,
                    style_name or "AI Selected", style_let_ai_decide,
                )

        async with timed("parallel_design", timings):
            results = await gather_with_timeout([run_color(), run_style()], timeout=30.0)
        color_result = results[0] if not isinstance(results[0], Exception) else None
        style_result = results[1] if not isinstance(results[1], Exception) else None
        return {"color_analysis": color_result, "style_analysis": style_result, "debug_timings": timings}

    # ImgBB upload helper (same as DataManager)
    def upload_image_to_imgbb(self, image_base64: str) -> Optional[str]:
        """Upload base64 image to ImgBB and return public URL."""
        import requests

        try:
            imgbb_key = os.getenv("IMGBB_API_KEY")
            if not imgbb_key:
                self.logger.warning("IMGBB_API_KEY not found")
                return None

            url = "https://api.imgbb.com/1/upload"
            payload = {"key": imgbb_key, "image": image_base64}
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()

            if result.get("success"):
                return result["data"]["url"]

            self.logger.warning(f"ImgBB upload failed: {result}")
            return None
        except Exception as e:
            self.logger.error(f"Error uploading to ImgBB: {e}")
            return None


# Module-level singleton (same pattern as data_manager.py)
data_manager = SupabaseDataManager()
