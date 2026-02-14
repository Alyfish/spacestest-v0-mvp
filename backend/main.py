from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import base64
import json
import os
import time
import uuid

import httpx
from dotenv import load_dotenv

# Feature flag: switch between JSON file and Supabase-backed data storage
_USE_SUPABASE_DATA = os.getenv("USE_SUPABASE_DATA", "false").lower() == "true"
if _USE_SUPABASE_DATA:
    from supabase_data_manager import data_manager
else:
    from data_manager import data_manager
from fastapi import FastAPI, File, HTTPException, UploadFile, Request, Header, BackgroundTasks, Depends, Query
from auth import get_current_user, get_optional_user, AuthenticatedUser
from fastapi.responses import JSONResponse
from job_manager import job_manager, JobType, JobInfo
from errors import APIError, ErrorCode
from background_tasks import (
    execute_generate_image,
    execute_inspiration_redesign,
    execute_search_recommendations,
)
from job_reaper import job_reaper
from supabase_client import is_supabase_configured
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from logger_config import setup_logging, add_request_id_middleware
from async_utils import TTLCache
from e2e_test_support import (
    E2ETraceStore,
    load_e2e_config,
    is_secret_valid,
    normalize_path,
    should_use_stub_mode,
)
from models import (
    AutoSelectProductResponse,
    ImageGenerationResponse,
    ImageUploadResponse,
    ImprovementMarkersRequest,
    ImprovementMarkersResponse,
    ImprovementModeRequest,
    ImprovementModeResponse,
    MarkerRecommendationsResponse,
    InspirationImageGenerationResponse,
    RetryRedesignRequest,
    InspirationImagesBatchUploadResponse,
    InspirationImageUploadResponse,
    InspirationRecommendationsResponse,
    ProductRecommendationSelectionRequest,
    ProductRecommendationSelectionResponse,
    SetSelectedRecommendationsRequest,
    SetSelectedRecommendationsResponse,
    ProductRecommendationsResponse,
    ProductSearchResponse,
    ProductSelectionRequest,
    ProductSelectionResponse,
    ProjectContext,
    ProjectCreateResponse,
    ProjectResponse,
    ProjectsListResponse,
    ProjectSummary,
    SpaceTypeRequest,
    SpaceTypeResponse,
    ClipSearchRequest,
    ClipSearchResponse,
    ClipAnalysisInfo,
    BatchFurnitureAnalysisRequest,
    BatchFurnitureAnalysisResponse,
    FurnitureAnalysisItem,
    ReverseSearchBatchRequest,
    ReverseSearchBatchResponse,
    SkipStepResponse,
    AffiliateCartRequest,
    AffiliateCartResponse,
    AffiliateProduct,
    AffiliateProductItem,
    RetailerCart,
    ApplyColorRequest,
    ApplyColorResponse,
    ApplyStyleRequest,
    ApplyStyleResponse,
    PreferredStoresRequest,
    PreferredStoresResponse,
    # "Like These?" Product Suggestions Feature
    PreSearchedCategory,
    FavoriteProduct,
    SearchRecommendationsRequest,
    SearchRecommendationsResponse,
    ProductSuggestionsResponse,
    FavoriteProductsRequest,
    FavoriteProductsResponse,
    # Selected Trending Products for image generation
    SelectedTrendingProduct,
    SelectedTrendingProductsRequest,
    SelectedTrendingProductsResponse,
    # Flutter API Response Models
    ColorAnalysisResponse,
    StyleAnalysisResponse,
    TrendingProductsResponse,
    ColorAnalysis,
    StyleAnalysis,
    # Process Furniture Selection Models
    SelectedFurnitureProduct,
    ResolvedProduct,
    ProcessFurnitureSelectionRequest,
    ProcessFurnitureSelectionResponse,
    # URL Normalizer Models
    NormalizeURLsRequest,
)

load_dotenv()

# Initialize logging
logger = setup_logging()

# Job TTL for cleanup (30 minutes)
JOB_TTL_MINUTES = 30
_E2E_STUB_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAAOb5QkAAAAASUVORK5CYII="
)


def _e2e_config_from_request(request: Optional[Request] = None):
    if request is not None and hasattr(request.app.state, "e2e_config"):
        return request.app.state.e2e_config
    return load_e2e_config()


def _is_e2e_secret_authorized(
    secret: Optional[str],
    request: Optional[Request] = None,
) -> bool:
    return is_secret_valid(_e2e_config_from_request(request), secret)


def _is_e2e_stub_enabled(
    secret: Optional[str],
    request: Optional[Request] = None,
) -> bool:
    return should_use_stub_mode(_e2e_config_from_request(request), secret)


def _e2e_stub_recommendations(space_type: Optional[str] = None) -> List[str]:
    space = (space_type or "room").replace("_", " ").strip() or "room"
    return [
        f"Replace statement sofa in {space}",
        "Add layered ambient lighting",
        "Introduce textured accent rug",
        "Upgrade wall art composition",
    ]


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "item"


def _e2e_stub_categories(recommendations: Optional[List[str]] = None):
    source = [r.strip() for r in (recommendations or []) if r and r.strip()]
    if not source:
        source = _e2e_stub_recommendations()[:2]
    categories = []
    for rec in source[:2]:
        slug = _slugify(rec)
        categories.append(
            {
                "recommendation": rec,
                "search_query": f"modern {slug.replace('_', ' ')}",
                "status": "complete",
                "products": [
                    {
                        "url": f"https://example.com/{slug}/1",
                        "title": f"{rec} Option 1",
                        "image_url": f"https://example.com/images/{slug}-1.jpg",
                        "store": "Target",
                        "price_str": "$129",
                        "price": 129.0,
                        "similarity_score": 0.92,
                    },
                    {
                        "url": f"https://example.com/{slug}/2",
                        "title": f"{rec} Option 2",
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
    return categories


def _e2e_stub_trending(project_id: str):
    categories = _e2e_stub_categories()
    return {
        "project_id": project_id,
        "categories": categories,
        "selected_products": [],
        "favorite_products": [],
        "status": "success",
        "message": "Stub trending products generated for E2E",
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: Initialize shared resources at startup, cleanup at shutdown."""
    # ===== STARTUP =====
    logger.info("Starting up: Initializing shared resources...")

    # Shared HTTP client with connection pooling
    app.state.http = httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        limits=httpx.Limits(
            max_connections=50,
            max_keepalive_connections=20
        )
    )

    # Per-category semaphores (configurable via env)
    app.state.sems = {
        "llm": asyncio.Semaphore(int(os.getenv("SEM_LLM", "2"))),
        "serp": asyncio.Semaphore(int(os.getenv("SEM_SERP", "3"))),
        "exa": asyncio.Semaphore(int(os.getenv("SEM_EXA", "3"))),
        "img_search": asyncio.Semaphore(int(os.getenv("SEM_IMG_SEARCH", "4"))),
        "img_download": asyncio.Semaphore(int(os.getenv("SEM_IMG_DL", "12"))),
        "variation": asyncio.Semaphore(int(os.getenv("SEM_VARIATION", "3"))),
        "clip": asyncio.Semaphore(int(os.getenv("SEM_CLIP", "1"))),
    }

    # In-memory job store (single worker only; use Redis for multi-worker)
    app.state.jobs: Dict[str, Dict[str, Any]] = {}

    # In-memory caches with TTL + LRU
    app.state.search_cache = TTLCache(max_size=500, default_ttl=600)  # 10 min
    app.state.image_cache = TTLCache(max_size=200, default_ttl=3600)  # 1 hour
    app.state.clip_cache = TTLCache(max_size=1000, default_ttl=86400)  # 24 hours

    # In-flight dedupe (prevents duplicate concurrent requests)
    app.state.in_flight: Dict[str, asyncio.Future] = {}

    # E2E test harness state (disabled unless env flags are set)
    app.state.e2e_config = load_e2e_config()
    app.state.e2e_trace_store = E2ETraceStore(
        max_runs=app.state.e2e_config.max_runs,
        max_events_per_run=app.state.e2e_config.max_events_per_run,
    )
    if app.state.e2e_config.enabled:
        logger.info(
            "E2E test mode enabled",
            extra={
                "stub_mode": app.state.e2e_config.stub_mode,
                "max_runs": app.state.e2e_config.max_runs,
                "max_events_per_run": app.state.e2e_config.max_events_per_run,
            },
        )

    # Initialize Supabase-backed job system
    if is_supabase_configured():
        logger.info("Supabase configured - using persistent job storage")
        # Start the job reaper for stale job recovery
        await job_reaper.start()
    else:
        logger.warning("Supabase not configured - using in-memory job fallback")

    logger.info("Startup complete: Shared resources initialized")

    yield

    # ===== SHUTDOWN =====
    logger.info("Shutting down: Cleaning up resources...")

    # Stop the job reaper
    await job_reaper.stop()

    # Close HTTP client
    await app.state.http.aclose()

    # Cancel any pending jobs (legacy in-memory jobs)
    for job_id, job in app.state.jobs.items():
        if job.get("task") and not job["task"].done():
            job["task"].cancel()
            logger.info(f"Cancelled pending job: {job_id}")

    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Interior Design Agent",
    version="1.0.0",
    root_path="/api",
    lifespan=lifespan
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID middleware for correlation
add_request_id_middleware(app)


@app.middleware("http")
async def e2e_trace_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)

    config = _e2e_config_from_request(request)
    if not config.enabled:
        return response

    if normalize_path(request.url.path).startswith("/e2e/"):
        return response

    run_id = request.headers.get("X-E2E-Run-ID", "").strip()
    if not run_id:
        return response

    if not _is_e2e_secret_authorized(
        request.headers.get("X-E2E-Test-Secret"),
        request=request,
    ):
        return response

    trace_store = getattr(request.app.state, "e2e_trace_store", None)
    if trace_store is None:
        return response

    trace_store.record(
        run_id,
        method=request.method,
        path=request.url.path,
        query=dict(request.query_params),
        status_code=response.status_code,
        duration_ms=(time.perf_counter() - start) * 1000,
        request_id=response.headers.get("X-Request-ID")
        or request.headers.get("X-Request-ID"),
    )
    return response


def _require_e2e_access(
    *,
    request: Request,
    provided_secret: Optional[str],
) -> Optional[JSONResponse]:
    config = _e2e_config_from_request(request)
    if not config.enabled:
        return JSONResponse(
            status_code=403,
            content={
                "status": "disabled",
                "reason": "E2E_TEST_MODE is not enabled",
            },
        )
    if not _is_e2e_secret_authorized(provided_secret, request=request):
        return JSONResponse(
            status_code=401,
            content={
                "status": "denied",
                "reason": "Invalid E2E test secret",
            },
        )
    return None


@app.get("/e2e/status")
async def e2e_status(
    request: Request,
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    denied = _require_e2e_access(
        request=request,
        provided_secret=x_e2e_test_secret,
    )
    if denied is not None:
        return denied

    config = _e2e_config_from_request(request)
    trace_store = request.app.state.e2e_trace_store
    return {
        "status": "ok",
        "enabled": config.enabled,
        "stub_mode": config.stub_mode,
        "trace_limits": trace_store.stats(),
        "server_time": datetime.utcnow().isoformat(),
    }


@app.get("/e2e/traces/{run_id}")
async def e2e_get_traces(
    run_id: str,
    request: Request,
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    denied = _require_e2e_access(
        request=request,
        provided_secret=x_e2e_test_secret,
    )
    if denied is not None:
        return denied

    traces = request.app.state.e2e_trace_store.list(run_id)
    return {
        "status": "ok",
        "run_id": run_id,
        "count": len(traces),
        "traces": traces,
    }


@app.delete("/e2e/traces/{run_id}")
async def e2e_clear_traces(
    run_id: str,
    request: Request,
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    denied = _require_e2e_access(
        request=request,
        provided_secret=x_e2e_test_secret,
    )
    if denied is not None:
        return denied

    deleted = request.app.state.e2e_trace_store.clear(run_id)
    return {
        "status": "ok",
        "run_id": run_id,
        "deleted": deleted,
    }


# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """
    Handle custom APIError exceptions with structured JSON responses.
    No stack traces are exposed to clients.
    """
    logger.warning(
        f"APIError: {exc.code.value} - {exc.message}",
        extra={
            "error_type": exc.code.value,
            "status_code": exc.status_code,
            "error_id": exc.error_id,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle FastAPI HTTPException with consistent JSON format.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "category": "http",
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Handle unhandled exceptions.
    - Logs full stack trace for debugging
    - Returns sanitized error to client (no stack trace)
    - Generates error_id for correlation
    """
    error_id = str(uuid.uuid4())[:8]

    logger.error(
        f"Unhandled exception [{error_id}]: {type(exc).__name__}: {str(exc)}",
        extra={
            "error_id": error_id,
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred. Please try again later.",
                "category": "internal",
                "error_id": error_id,
            }
        },
    )


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "message": "AI Interior Design Agent is running"}


@app.get("/")
async def root():
    """Root API endpoint"""
    return {"message": "Welcome to AI Interior Design Agent API"}


@app.post("/projects", response_model=ProjectCreateResponse)
async def create_project(user: AuthenticatedUser = Depends(get_current_user)):
    """Create a new project"""
    logger.info("Received request to create new project", extra={"user_id": user.id})
    project_id = data_manager.create_project(user_id=user.id)
    project = data_manager.get_project(project_id, user_id=user.id)

    return ProjectCreateResponse(project_id=project_id, status=project["status"])


@app.get("/projects", response_model=ProjectsListResponse)
async def get_all_projects(user: AuthenticatedUser = Depends(get_current_user)):
    """Get all projects for the authenticated user"""
    projects_dict = data_manager.get_all_projects(user_id=user.id)

    # Convert each project to use ProjectContext and ProjectSummary
    projects = {}
    for project_id, project_data in projects_dict.items():
        context = ProjectContext.model_validate(project_data["context"])
        projects[project_id] = ProjectSummary(
            status=project_data["status"],
            created_at=project_data["created_at"],
            context=context,
        )

    return ProjectsListResponse(projects=projects, total_count=len(projects))


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Get a project by ID"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Parse the context from dict to ProjectContext object
    context = ProjectContext.model_validate(project["context"])

    return ProjectResponse(
        project_id=project_id,
        status=project["status"],
        created_at=project["created_at"],
        context=context,
    )


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Delete a project"""
    if not data_manager.delete_project(project_id, user_id=user.id):
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": "success", "message": f"Project {project_id} deleted successfully"}


@app.post("/projects/{project_id}/upload-image", response_model=ImageUploadResponse)
async def upload_project_image(project_id: str, image: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user)):
    """Upload an image for a project with validation."""
    from validators import validate_image_upload

    # Validate file type, size, and read content
    await validate_image_upload(image)

    # Verify project ownership first
    data_manager.get_project(project_id, user_id=user.id)

    try:
        data_manager.upload_image(project_id, image, image.filename)
        project = data_manager.get_project(project_id, user_id=user.id)

        return ImageUploadResponse(project_id=project_id, status=project["status"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/projects/{project_id}/base-image")
async def get_project_base_image(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Get the base image for a project"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    if context.base_image is None:
        raise HTTPException(
            status_code=404, detail="No base image found for this project"
        )

    image_path = context.base_image

    # Support Supabase Storage URLs (redirect) or local file paths (serve)
    if image_path.startswith("http"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=image_path)

    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(image_path)


@app.get("/projects/{project_id}/labelled-image")
async def get_project_labelled_image(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Get the labelled image for a project"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    if context.labelled_base_image is None:
        raise HTTPException(
            status_code=404, detail="No labelled image found for this project"
        )

    image_path = context.labelled_base_image

    if image_path.startswith("http"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=image_path)

    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Labelled image file not found")

    return FileResponse(image_path)


@app.post("/projects/{project_id}/space-type", response_model=SpaceTypeResponse)
async def select_project_space_type(
    project_id: str, space_type_request: SpaceTypeRequest, user: AuthenticatedUser = Depends(get_current_user)
):
    """Select space type for a project with validation."""
    from validators import validate_space_type

    # Verify project ownership first
    data_manager.get_project(project_id, user_id=user.id)

    # Validate space type is in allowed list
    validated_space_type = validate_space_type(space_type_request.space_type)

    try:
        space_type = data_manager.select_space_type(project_id, validated_space_type)
        project = data_manager.get_project(project_id, user_id=user.id)

        return SpaceTypeResponse(
            project_id=project_id, space_type=space_type, status=project["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to select space type: {str(e)}"
        )


@app.post("/projects/{project_id}/improvement-mode", response_model=ImprovementModeResponse)
async def set_improvement_mode(project_id: str, request: ImprovementModeRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Set the improvement mode for a project (iterative or complete_revamp)"""
    # Verify project ownership first
    data_manager.get_project(project_id, user_id=user.id)

    try:
        mode = data_manager.set_improvement_mode(project_id, request.mode)
        project = data_manager.get_project(project_id, user_id=user.id)

        return ImprovementModeResponse(
            project_id=project_id, mode=mode, status=project["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to set improvement mode: {str(e)}"
        )


@app.post(
    "/projects/{project_id}/improvement-markers",
    response_model=ImprovementMarkersResponse,
)
async def save_improvement_markers(
    project_id: str, markers_request: ImprovementMarkersRequest, user: AuthenticatedUser = Depends(get_current_user)
):
    """Save improvement markers for a project"""
    # Verify project ownership first
    data_manager.get_project(project_id, user_id=user.id)

    try:
        labelled_image_path = data_manager.save_improvement_markers(
            project_id, markers_request.markers
        )
        project = data_manager.get_project(project_id, user_id=user.id)

        return ImprovementMarkersResponse(
            project_id=project_id,
            markers=markers_request.markers,
            labelled_image_path=labelled_image_path,
            status=project["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save improvement markers: {str(e)}"
        )


@app.get(
    "/projects/{project_id}/marker-recommendations",
    response_model=MarkerRecommendationsResponse,
)
async def get_marker_recommendations(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Get AI-generated recommendations for improvement markers"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["status"] != "MARKER_RECOMMENDATIONS_READY":
        raise HTTPException(
            status_code=400, detail="Project is not ready for recommendations"
        )

    context = ProjectContext.model_validate(project["context"])

    if not context.marker_recommendations:
        raise HTTPException(
            status_code=404, detail="No marker recommendations found for this project"
        )

    return MarkerRecommendationsResponse(
        project_id=project_id,
        space_type=context.space_type or "unknown",
        recommendations=context.marker_recommendations,
        status=project["status"],
    )


@app.post(
    "/projects/{project_id}/marker-recommendations",
    response_model=MarkerRecommendationsResponse,
)
async def generate_marker_recommendations(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Generate marker-based AI recommendations when the project is ready (color/style/stores set)."""
    # Verify project ownership first
    data_manager.get_project(project_id, user_id=user.id)

    try:
        recs = data_manager.trigger_marker_recommendations(project_id)
        project = data_manager.get_project(project_id, user_id=user.id)
        context = ProjectContext.model_validate(project["context"])
        return MarkerRecommendationsResponse(
            project_id=project_id,
            space_type=context.space_type or "unknown",
            recommendations=recs,
            status=project["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate marker recommendations: {str(e)}")


@app.post(
    "/projects/{project_id}/inspiration-image",
    response_model=InspirationImageUploadResponse,
)
async def upload_inspiration_image(project_id: str, image: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user)):
    """Upload an inspiration image for a project with validation."""
    from validators import validate_image_upload

    # Verify project ownership first
    data_manager.get_project(project_id, user_id=user.id)

    # Validate file type, size, and read content
    await validate_image_upload(image)

    try:
        image_path = data_manager.upload_inspiration_image(
            project_id, image, image.filename
        )
        project = data_manager.get_project(project_id, user_id=user.id)

        return InspirationImageUploadResponse(
            project_id=project_id, image_path=image_path, status=project["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post(
    "/projects/{project_id}/inspiration-images-batch",
    response_model=InspirationImagesBatchUploadResponse,
)
async def upload_inspiration_images_batch(
    project_id: str, images: List[UploadFile] = File(...), user: AuthenticatedUser = Depends(get_current_user)
):
    """Upload multiple inspiration images for a project in one batch with validation."""
    from validators import validate_image_upload

    # Verify project ownership first
    data_manager.get_project(project_id, user_id=user.id)

    # Validate all files
    for image in images:
        await validate_image_upload(image)

    try:
        image_paths = data_manager.upload_inspiration_images_batch(project_id, images)
        project = data_manager.get_project(project_id, user_id=user.id)

        return InspirationImagesBatchUploadResponse(
            project_id=project_id,
            image_paths=image_paths,
            uploaded_count=len(image_paths),
            status=project["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload inspiration images: {str(e)}"
        )


@app.get("/projects/{project_id}/inspiration-image/{image_index}")
async def get_inspiration_image(project_id: str, image_index: int, user: AuthenticatedUser = Depends(get_current_user)):
    """Get an inspiration image for a project by index"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    if not context.inspiration_images:
        raise HTTPException(
            status_code=404, detail="No inspiration images found for this project"
        )

    if image_index >= len(context.inspiration_images):
        raise HTTPException(
            status_code=404, detail="Inspiration image index out of range"
        )

    image_path = context.inspiration_images[image_index]

    if image_path.startswith("http"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=image_path)

    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Inspiration image file not found")

    return FileResponse(image_path)


@app.post(
    "/projects/{project_id}/inspiration-recommendations",
    response_model=InspirationRecommendationsResponse,
)
async def generate_inspiration_recommendations(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Generate AI recommendations based on inspiration images"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["status"] not in [
        "INSPIRATION_IMAGES_UPLOADED",
        "INSPIRATION_RECOMMENDATIONS_READY",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Project is not ready for inspiration recommendations",
        )

    try:
        recommendations = data_manager.generate_inspiration_recommendations(project_id)
        project = data_manager.get_project(project_id, user_id=user.id)
        context = ProjectContext.model_validate(project["context"])

        return InspirationRecommendationsResponse(
            project_id=project_id,
            space_type=context.space_type or "unknown",
            recommendations=recommendations,
            status=project["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate inspiration recommendations: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/inspiration-redesign",
    response_model=Dict[str, Any],
)
async def generate_inspiration_redesign(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """
    Start background inspiration redesign, returns job_id for polling.

    Poll GET /projects/{project_id}/job-status/{job_id} for progress and result.
    """
    logger.info(
        "API request: generate inspiration redesign (background)",
        extra={"project_id": project_id, "user_id": user.id},
    )
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    use_stub = _is_e2e_stub_enabled(x_e2e_test_secret, request=request)

    # Check if project has inspiration images, inspiration recs, OR product recs
    context = ProjectContext.model_validate(project["context"])
    has_inspiration_recs = (
        context.inspiration_recommendations
        and len(context.inspiration_recommendations) > 0
    )
    has_product_recs = (
        context.product_recommendations
        and len(context.product_recommendations) > 0
    )
    has_inspiration_images = (
        context.inspiration_images
        and len(context.inspiration_images) > 0
    )

    if (
        not use_stub
        and not has_inspiration_recs
        and not has_product_recs
        and not has_inspiration_images
    ):
        logger.warning(
            "Project has no inspiration images, inspiration recs, or product recs",
            extra={
                "project_id": project_id,
                "current_status": project["status"],
                "has_inspiration_recs": False,
                "has_product_recs": False,
                "has_inspiration_images": False,
            },
        )
        raise HTTPException(
            status_code=400,
            detail="Project must have inspiration images, inspiration recommendations, or product recommendations first.",
        )

    # Create job in Supabase (idempotent)
    job_id = await job_manager.create_job(
        project_id=project_id,
        job_type=JobType.INSPIRATION_REDESIGN,
        user_id=user.id,
        idempotency_key=x_idempotency_key,
    )

    # Schedule background execution
    background_tasks.add_task(
        execute_inspiration_redesign,
        job_id=job_id,
        project_id=project_id,
        use_stub=use_stub,
    )

    logger.info(
        "Inspiration redesign job started",
        extra={"project_id": project_id, "job_id": job_id},
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Inspiration redesign started. Poll /projects/{project_id}/job-status/{job_id} for updates.",
    }


@app.post(
    "/projects/{project_id}/retry-redesign",
    response_model=InspirationImageGenerationResponse,
)
async def retry_redesign(project_id: str, request: RetryRedesignRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Apply user-directed modifications to the existing generated image.

    This is a SURGICAL EDIT operation - takes the last generated image
    and applies only the specific changes the user requested.

    Examples:
        - "remove the lamp on the nightstand"
        - "add a plant in the corner"
        - "replace the blue sofa with a grey one"
    """
    logger.info(
        "API request: retry redesign",
        extra={"project_id": project_id, "feedback": request.feedback[:100], "user_id": user.id},
    )
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if project has a generated image to edit
    context = ProjectContext.model_validate(project["context"])
    if not context.inspiration_generated_image_base64:
        raise HTTPException(
            status_code=400,
            detail="No generated image available to edit. Please generate an image first.",
        )

    try:
        logger.info(
            "Starting retry redesign",
            extra={
                "project_id": project_id,
                "feedback": request.feedback[:100],
            },
        )
        result = data_manager.retry_inspiration_redesign(project_id, request.feedback)

        logger.info(
            "Retry redesign completed successfully",
            extra={
                "project_id": project_id,
                "image_len": len(result.get("generated_image_base64", "")),
            },
        )
        return InspirationImageGenerationResponse(
            project_id=project_id,
            generated_image_base64=result["generated_image_base64"],
            inspiration_prompt=result["inspiration_prompt"],
            inspiration_recommendations=result["inspiration_recommendations"],
            status=result["status"],
            message=result["message"],
            model_used=result.get("model_used"),
        )
    except ValueError as e:
        logger.error(
            "Retry redesign failed: ValueError",
            extra={"project_id": project_id, "error": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(
            "Retry redesign failed: Unexpected error",
            extra={
                "project_id": project_id,
                "error": str(e),
                "trace": traceback.format_exc(),
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to edit image: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/apply-color-scheme",
    response_model=ApplyColorResponse,
)
async def apply_color_scheme(project_id: str, color_request: ApplyColorRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Apply a color scheme to the project using the Color Agent for analysis"""
    logger.info(
        "API request: apply color scheme",
        extra={
            "project_id": project_id,
            "palette_name": color_request.palette_name,
            "let_ai_decide": color_request.let_ai_decide,
            "user_id": user.id,
        },
    )
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    # Need at least a base image and space type
    if not context.base_image or not context.space_type:
        raise HTTPException(
            status_code=400,
            detail="Project must have a base image and space type selected first",
        )

    try:
        # Fast-path: when AI decides, skip Gemini analysis entirely (saves 20-40s)
        if color_request.let_ai_decide:
            logger.info(
                "Skipping Color Agent (let_ai_decide=true) — fast path",
                extra={"project_id": project_id},
            )
            data_manager.skip_color_analysis(project_id)
            from starlette.responses import JSONResponse
            return JSONResponse(content={
                "project_id": project_id,
                "palette_name": "AI Selected",
                "status": "success",
                "message": "Color analysis skipped (AI will decide during generation)",
                "color_analysis_skipped": True,
            })

        logger.info(
            "Starting Color Agent analysis",
            extra={
                "project_id": project_id,
                "palette_name": color_request.palette_name,
            },
        )

        color_analysis = data_manager.apply_color_scheme(
            project_id,
            color_request.palette_name,
            color_request.colors,
            color_request.let_ai_decide,
        )

        logger.info(
            "Color Agent analysis complete",
            extra={"project_id": project_id},
        )

        from models import ColorAnalysis
        return ApplyColorResponse(
            project_id=project_id,
            palette_name=color_request.palette_name,
            color_analysis=ColorAnalysis.model_validate(color_analysis),
            status="success",
        )
    except ValueError as e:
        logger.error(
            "Color scheme application failed: ValueError",
            extra={"project_id": project_id, "error": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(
            "Color scheme application failed: Unexpected error",
            extra={
                "project_id": project_id,
                "error": str(e),
                "trace": traceback.format_exc(),
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply color scheme: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/apply-style",
    response_model=ApplyStyleResponse,
)
async def apply_style(project_id: str, style_request: ApplyStyleRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Apply an interior design style to the project using the Style Agent for analysis"""
    logger.info(
        "API request: apply style",
        extra={
            "project_id": project_id,
            "style_name": style_request.style_name,
            "let_ai_decide": style_request.let_ai_decide,
            "user_id": user.id,
        },
    )
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    # Need at least a base image and space type
    if not context.base_image or not context.space_type:
        raise HTTPException(
            status_code=400,
            detail="Project must have a base image and space type selected first",
        )

    try:
        # Fast-path: when AI decides, skip Gemini analysis entirely (saves 20-40s)
        if style_request.let_ai_decide:
            logger.info(
                "Skipping Style Agent (let_ai_decide=true) — fast path",
                extra={"project_id": project_id},
            )
            data_manager.skip_style_analysis(project_id)
            from starlette.responses import JSONResponse
            return JSONResponse(content={
                "project_id": project_id,
                "style_name": "AI Selected",
                "status": "success",
                "message": "Style analysis skipped (AI will decide during generation)",
                "style_analysis_skipped": True,
            })

        logger.info(
            "Starting Style Agent analysis",
            extra={
                "project_id": project_id,
                "style_name": style_request.style_name,
            },
        )

        style_analysis = data_manager.apply_style(
            project_id,
            style_request.style_name,
            style_request.let_ai_decide,
        )

        logger.info(
            "Style Agent analysis complete",
            extra={"project_id": project_id},
        )

        from models import StyleAnalysis
        return ApplyStyleResponse(
            project_id=project_id,
            style_name=style_request.style_name,
            style_analysis=StyleAnalysis.model_validate(style_analysis),
            status="success",
        )
    except ValueError as e:
        logger.error(
            "Style application failed: ValueError",
            extra={"project_id": project_id, "error": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(
            "Style application failed: Unexpected error",
            extra={
                "project_id": project_id,
                "error": str(e),
                "trace": traceback.format_exc(),
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply style: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/skip-color-analysis",
    response_model=SkipStepResponse,
)
async def skip_color_analysis(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Skip color analysis to unblock downstream steps."""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])
    if not context.base_image or not context.space_type:
        raise HTTPException(
            status_code=400,
            detail="Project must have a base image and space type selected first",
        )

    try:
        data_manager.skip_color_analysis(project_id)
        project = data_manager.get_project(project_id, user_id=user.id)
        return SkipStepResponse(
            project_id=project_id,
            status=project["status"],
            skipped_step="color_analysis",
            message="Color analysis skipped",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to skip color analysis: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/skip-style-analysis",
    response_model=SkipStepResponse,
)
async def skip_style_analysis(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Skip style analysis to unblock downstream steps."""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])
    if not context.base_image or not context.space_type:
        raise HTTPException(
            status_code=400,
            detail="Project must have a base image and space type selected first",
        )

    try:
        data_manager.skip_style_analysis(project_id)
        project = data_manager.get_project(project_id, user_id=user.id)
        return SkipStepResponse(
            project_id=project_id,
            status=project["status"],
            skipped_step="style_analysis",
            message="Style analysis skipped",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to skip style analysis: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/skip-inspiration-images",
    response_model=SkipStepResponse,
)
async def skip_inspiration_images(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Skip inspiration images to unblock downstream steps."""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])
    if not context.base_image or not context.space_type:
        raise HTTPException(
            status_code=400,
            detail="Project must have a base image and space type selected first",
        )

    try:
        data_manager.skip_inspiration_images(project_id)
        project = data_manager.get_project(project_id, user_id=user.id)
        return SkipStepResponse(
            project_id=project_id,
            status=project["status"],
            skipped_step="inspiration_images",
            message="Inspiration images skipped",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to skip inspiration images: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/preferred-stores",
    response_model=PreferredStoresResponse,
)
async def update_preferred_stores(
    project_id: str, store_request: PreferredStoresRequest, user: AuthenticatedUser = Depends(get_current_user)
):
    """Update user's preferred retail stores in the project context"""
    logger.info(
        "API request: update preferred stores",
        extra={
            "project_id": project_id,
            "stores": store_request.stores,
            "user_id": user.id,
        },
    )
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        updated_stores = data_manager.update_preferred_stores(
            project_id, store_request.stores
        )

        return PreferredStoresResponse(
            project_id=project_id,
            stores=updated_stores,
            status="success",
        )
    except Exception as e:
        import traceback
        logger.error(
            "Update preferred stores failed: Unexpected error",
            extra={
                "project_id": project_id,
                "error": str(e),
                "trace": traceback.format_exc(),
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferred stores: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/product-recommendations",
    response_model=ProductRecommendationsResponse,
)
async def generate_product_recommendations(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    auto_search: bool = Query(False, description="Auto-start product search after generating recommendations"),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """Generate AI product recommendations based on project context"""
    logger.info(
        "API request: generate product recommendations",
        extra={"project_id": project_id, "user_id": user.id, "auto_search": auto_search},
    )
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    use_stub = _is_e2e_stub_enabled(x_e2e_test_secret, request=request)

    try:
        logger.info(
            "Generating product recommendations",
            extra={
                "project_id": project_id,
                "current_status": project["status"],
                "use_stub": use_stub,
            },
        )

        if use_stub:
            context = ProjectContext.model_validate(project["context"])
            recommendations = _e2e_stub_recommendations(context.space_type)
        else:
            recommendations = data_manager.generate_product_recommendations(project_id)
            project = data_manager.get_project(project_id, user_id=user.id)
        context = ProjectContext.model_validate(project["context"])

        logger.info(
            "Product recommendations generated successfully",
            extra={
                "project_id": project_id,
                "recommendations_count": len(recommendations),
                "new_status": project["status"],
            },
        )

        # Auto-start search job if requested (non-fatal on failure)
        search_job_id = None
        if auto_search and recommendations:
            try:
                import re
                # Take first 2 unique recommendations (matches Flutter's _visibleLikeTheseRecommendations)
                seen = set()
                visible = []
                for r in recommendations:
                    trimmed = r.strip()
                    if not trimmed:
                        continue
                    normalized = trimmed.lower()
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    visible.append(trimmed)
                    if len(visible) == 2:
                        break

                if visible:
                    # Replicate Flutter's _buildSearchIdempotencyKey exactly
                    sorted_recs = sorted(set(r.strip().lower() for r in visible if r.strip()))
                    compact = "_".join(sorted_recs)
                    compact = re.sub(r"[^a-z0-9_]+", "_", compact)
                    suffix = "default" if not compact else (compact[:80] if len(compact) > 80 else compact)
                    idempotency_key = f"{project_id}_search_{suffix}"

                    search_job_id = await job_manager.create_job(
                        project_id=project_id,
                        job_type=JobType.SEARCH_RECOMMENDATIONS,
                        user_id=user.id,
                        idempotency_key=idempotency_key,
                        request_data={"recommendations": visible},
                    )

                    background_tasks.add_task(
                        execute_search_recommendations,
                        job_id=search_job_id,
                        project_id=project_id,
                        recommendations=visible,
                        app_state=request.app.state,
                        use_stub=use_stub,
                    )

                    logger.info(
                        "Auto-search job started from recommendations endpoint",
                        extra={
                            "project_id": project_id,
                            "search_job_id": search_job_id,
                            "search_recs": visible,
                        },
                    )
            except Exception as e:
                logger.warning(
                    "Auto-search failed (non-fatal)",
                    extra={"project_id": project_id, "error": str(e)},
                )

        return ProductRecommendationsResponse(
            project_id=project_id,
            space_type=context.space_type or "unknown",
            recommendations=recommendations,
            status=project.get("status", "PRODUCT_RECOMMENDATIONS_READY"),
            search_job_id=search_job_id,
        )
    except ValueError as e:
        logger.error(
            "Product recommendations generation failed: ValueError",
            extra={"project_id": project_id, "error": str(e)},
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "Product recommendations generation failed: Unexpected error",
            extra={
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate product recommendations: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/product-recommendation-selection",
    response_model=ProductRecommendationSelectionResponse,
)
async def select_product_recommendation(
    project_id: str, selection_request: ProductRecommendationSelectionRequest, user: AuthenticatedUser = Depends(get_current_user)
):
    """Select a product recommendation option"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    allowed_statuses = [
        "PRODUCT_RECOMMENDATIONS_READY",
        "INSPIRATION_RECOMMENDATIONS_READY",
        "PRODUCT_RECOMMENDATION_SELECTED",
        "PRODUCT_SEARCH_COMPLETE",
        "PRODUCT_SELECTED",
        "IMAGE_GENERATED",
        "INSPIRATION_REDESIGN_COMPLETE"
    ]

    if project["status"] not in allowed_statuses:
        # Fallback: check if we actually have recommendations in context, if so, we might allow it (legacy projects/weird states)
        context = ProjectContext.model_validate(project["context"])
        has_recs = (context.product_recommendations and len(context.product_recommendations) > 0) or \
                   (context.inspiration_recommendations and len(context.inspiration_recommendations) > 0)

        if not has_recs:
             raise HTTPException(
                status_code=400,
                detail="Project must have product or inspiration recommendations ready first",
            )

    try:
        selected = data_manager.select_product_recommendation(
            project_id, selection_request.selected_recommendation
        )
        project = data_manager.get_project(project_id, user_id=user.id)

        return ProductRecommendationSelectionResponse(
            project_id=project_id,
            selected_recommendations=selected,
            status=project["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to select product recommendation: {str(e)}",
        )


@app.put(
    "/projects/{project_id}/selected-product-recommendations",
    response_model=SetSelectedRecommendationsResponse,
)
async def set_selected_product_recommendations(
    project_id: str,
    request: SetSelectedRecommendationsRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Atomically set the full list of selected product recommendations."""
    project = data_manager.get_project(project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        selected = data_manager.set_selected_product_recommendations(
            project_id, request.recommendations
        )
        project = data_manager.get_project(project_id, user_id=user.id)
        return SetSelectedRecommendationsResponse(
            project_id=project_id,
            selected_recommendations=selected,
            status=project["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set selected recommendations: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/product-search",
    response_model=ProductSearchResponse,
)
async def search_products(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Search for products based on selected recommendation using AI and Exa"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["status"] != "PRODUCT_RECOMMENDATION_SELECTED":
        raise HTTPException(
            status_code=400,
            detail="Project must have a selected product recommendation first",
        )

    try:
        search_result = data_manager.search_products(project_id)
        project = data_manager.get_project(project_id, user_id=user.id)
        context = ProjectContext.model_validate(project["context"])

        return ProductSearchResponse(
            project_id=project_id,
            selected_recommendations=context.selected_product_recommendations,
            search_query=search_result["search_query"],
            products=search_result["products"],
            total_found=search_result["total_found"],
            status=project["status"],
            message=f"Found {search_result['total_found']} products for your selections",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search for products: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/auto-select-product",
    response_model=AutoSelectProductResponse,
)
async def auto_select_product(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Auto-select the best product from search results based on:
    - CLIP similarity score (visual match)
    - Image quality/availability
    - Store trust rating
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])
    products = context.product_search_results or []

    if not products:
        raise HTTPException(
            status_code=400,
            detail="No products available. Run product search first.",
        )

    try:
        result = data_manager.auto_select_best_product(project_id, products)
        return AutoSelectProductResponse(
            project_id=project_id,
            selected_product=result["selected_product"],
            selection_reason=result["selection_reason"],
            alternatives=result["alternatives"],
            status="PRODUCT_AUTO_SELECTED",
            message=f"Auto-selected: {result['selected_product'].get('title', 'Unknown')}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to auto-select product: {str(e)}",
        )


# ============================================================================
# "Like These?" Product Suggestions Feature
# ============================================================================

@app.post(
    "/projects/{project_id}/search-recommendations",
    response_model=Dict[str, Any],
)
async def search_products_for_recommendations(
    project_id: str,
    payload: SearchRecommendationsRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """
    Start background product search, returns job_id for polling.

    Poll GET /projects/{project_id}/job-status/{job_id} for progress and result.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    use_stub = _is_e2e_stub_enabled(x_e2e_test_secret, request=request)

    # Create job in Supabase (idempotent)
    job_id = await job_manager.create_job(
        project_id=project_id,
        job_type=JobType.SEARCH_RECOMMENDATIONS,
        user_id=user.id,
        idempotency_key=x_idempotency_key,
        request_data={"recommendations": payload.recommendations},
    )

    # Schedule background execution
    background_tasks.add_task(
        execute_search_recommendations,
        job_id=job_id,
        project_id=project_id,
        recommendations=payload.recommendations,
        app_state=request.app.state,
        use_stub=use_stub,
    )

    logger.info(
        "Product search job started",
        extra={
            "project_id": project_id,
            "job_id": job_id,
            "recommendations_count": len(payload.recommendations),
        },
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Product search started. Poll /projects/{project_id}/job-status/{job_id} for updates.",
    }


@app.get(
    "/projects/{project_id}/product-suggestions",
    response_model=ProductSuggestionsResponse,
)
async def get_product_suggestions(
    project_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """
    Get pre-searched products organized by recommendation category.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if _is_e2e_stub_enabled(x_e2e_test_secret, request=request):
        categories = _e2e_stub_categories()
        return ProductSuggestionsResponse(
            project_id=project_id,
            categories=[PreSearchedCategory(**cat) for cat in categories],
            total_products=sum(len(cat["products"]) for cat in categories),
            overall_status="all_complete",
            message="Stub product suggestions for E2E",
        )

    try:
        result = data_manager.get_pre_searched_suggestions(project_id)

        return ProductSuggestionsResponse(
            project_id=project_id,
            categories=[PreSearchedCategory(**cat) for cat in result["categories"]],
            total_products=result["total_products"],
            overall_status=result["overall_status"],
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get product suggestions: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/favorite-products",
    response_model=FavoriteProductsResponse,
)
async def set_favorite_products(
    project_id: str,
    request: FavoriteProductsRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Save user's favorite product selections from the 'Like These?' screen.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = data_manager.set_favorite_products(
            project_id,
            [fav.model_dump() for fav in request.favorites]
        )

        return FavoriteProductsResponse(
            project_id=project_id,
            favorites_count=result["favorites_count"],
            favorites_by_category=result["favorites_by_category"],
            status=result["status"],
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save favorite products: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/selected-trending-products",
    response_model=SelectedTrendingProductsResponse,
)
async def set_selected_trending_products(
    project_id: str,
    request: SelectedTrendingProductsRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Save user's selected trending products for image generation.
    These product images will be passed to Gemini for visual representation.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = data_manager.set_selected_trending_products(
            project_id,
            [prod.model_dump() for prod in request.products]
        )

        return SelectedTrendingProductsResponse(
            project_id=project_id,
            products_count=result["products_count"],
            products_by_category=result["products_by_category"],
            status=result["status"],
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save selected trending products: {str(e)}",
        )


# ============================================================================
# Flutter API GET Endpoints
# ============================================================================

@app.get(
    "/projects/{project_id}/color-analysis",
    response_model=ColorAnalysisResponse,
)
async def get_color_analysis(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get color analysis results for Flutter app.
    Returns the ColorAnalysis object with palettes, assignments, and tips.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        context = ProjectContext.model_validate(project["context"])

        color_analysis = None
        if context.color_analysis:
            color_analysis = ColorAnalysis.model_validate(context.color_analysis)

        status = "success"
        message = "Color analysis retrieved successfully"
        if context.color_analysis_skipped:
            status = "skipped"
            message = "Color analysis was skipped by user"
        elif not color_analysis:
            status = "not_available"
            message = "Color analysis has not been performed yet"

        return ColorAnalysisResponse(
            project_id=project_id,
            color_analysis=color_analysis,
            skipped=context.color_analysis_skipped,
            status=status,
            message=message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get color analysis: {str(e)}",
        )


@app.get(
    "/projects/{project_id}/style-analysis",
    response_model=StyleAnalysisResponse,
)
async def get_style_analysis(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get style analysis results for Flutter app.
    Returns the StyleAnalysis object with materials, furniture recommendations, and styling tips.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        context = ProjectContext.model_validate(project["context"])

        style_analysis = None
        if context.style_analysis:
            style_analysis = StyleAnalysis.model_validate(context.style_analysis)

        status = "success"
        message = "Style analysis retrieved successfully"
        if context.style_analysis_skipped:
            status = "skipped"
            message = "Style analysis was skipped by user"
        elif not style_analysis:
            status = "not_available"
            message = "Style analysis has not been performed yet"

        return StyleAnalysisResponse(
            project_id=project_id,
            style_analysis=style_analysis,
            skipped=context.style_analysis_skipped,
            status=status,
            message=message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get style analysis: {str(e)}",
        )


@app.get(
    "/projects/{project_id}/trending-products",
    response_model=TrendingProductsResponse,
)
async def get_trending_products(
    project_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """
    Get trending products data for Flutter app.
    Returns pre-searched categories, selected trending products, and favorite products.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if _is_e2e_stub_enabled(x_e2e_test_secret, request=request):
        stub = _e2e_stub_trending(project_id)
        return TrendingProductsResponse(
            project_id=project_id,
            categories=[PreSearchedCategory(**cat) for cat in stub["categories"]],
            selected_products=[],
            favorite_products=[],
            status="success",
            message=stub["message"],
        )

    try:
        context = ProjectContext.model_validate(project["context"])

        # Convert pre_searched_categories dict to list
        categories = []
        if context.pre_searched_categories:
            for cat_data in context.pre_searched_categories.values():
                categories.append(PreSearchedCategory.model_validate(cat_data))

        # Convert selected_trending_products
        selected_products = []
        if context.selected_trending_products:
            for prod in context.selected_trending_products:
                selected_products.append(SelectedTrendingProduct.model_validate(prod))

        # Convert favorite_products
        favorite_products = []
        if context.favorite_products:
            for prod in context.favorite_products:
                favorite_products.append(FavoriteProduct.model_validate(prod))

        return TrendingProductsResponse(
            project_id=project_id,
            categories=categories,
            selected_products=selected_products,
            favorite_products=favorite_products,
            status="success",
            message="Trending products retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trending products: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/product-selection",
    response_model=ProductSelectionResponse,
)
async def select_product_for_generation(
    project_id: str, selection_request: ProductSelectionRequest, user: AuthenticatedUser = Depends(get_current_user)
):
    """Select a product for Gemini image generation"""
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Do not hard-block on project status here; the data manager will validate
    # that the context is ready for product selection (has search results, etc.).

    try:
        selected = data_manager.select_product_for_generation(
            project_id,
            selection_request.product_url,
            selection_request.product_title,
            selection_request.product_image_url,
            selection_request.generation_prompt,
            selection_request.color_scheme,
            selection_request.design_style,
        )

        return ProductSelectionResponse(
            project_id=project_id,
            selected_products=selected["selected_products"],
            status="success",
            message=selected["message"],
        )

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"❌ PRODUCT SELECTION ERROR: {str(e)}")
        print(f"❌ FULL TRACEBACK:\n{error_details}")
        logger.error(f"Product selection failed for project {project_id}: {str(e)}")
        logger.error(f"Full traceback: {error_details}")
        raise HTTPException(
            status_code=500, detail=f"Failed to select product: {str(e)}"
        )


@app.post(
    "/projects/{project_id}/generate-image",
    response_model=Dict[str, Any],
)
async def generate_product_visualization(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """
    Start background image generation, returns job_id for polling.

    Poll GET /projects/{project_id}/job-status/{job_id} for progress and result.
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    use_stub = _is_e2e_stub_enabled(x_e2e_test_secret, request=request)

    if not use_stub and project["status"] != "PRODUCT_SELECTED":
        raise HTTPException(
            status_code=400,
            detail="Project must have a selected product first",
        )

    # Create job in Supabase (idempotent)
    job_id = await job_manager.create_job(
        project_id=project_id,
        job_type=JobType.GENERATE_IMAGE,
        user_id=user.id,
        idempotency_key=x_idempotency_key,
    )

    # Schedule background execution
    background_tasks.add_task(
        execute_generate_image,
        job_id=job_id,
        project_id=project_id,
        use_stub=use_stub,
    )

    logger.info(
        "Image generation job started",
        extra={"project_id": project_id, "job_id": job_id},
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Image generation started. Poll /projects/{project_id}/job-status/{job_id} for updates.",
    }


@app.get("/projects/{project_id}/generated-image")
async def get_generated_image(
    project_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """Serve the generated image for a project.

    Handles three storage formats:
      - Supabase Storage URL (http/https) → RedirectResponse
      - Base64 encoded data → decode and return as image/png
      - Local file path → FileResponse
    Checks inspiration_generated first (redesign flow), then generated (standard flow).
    """
    project = data_manager.get_project(project_id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if _is_e2e_stub_enabled(x_e2e_test_secret, request=request):
        from fastapi.responses import Response

        return Response(
            content=base64.b64decode(_E2E_STUB_PNG_BASE64),
            media_type="image/png",
            headers={
                "Content-Disposition": f'inline; filename="generated_visualization_{project_id}.png"'
            },
        )

    context = ProjectContext.model_validate(project["context"])

    # Try inspiration redesign image first, then standard generated image
    image_data = context.inspiration_generated_image_base64 or context.generated_image_base64

    if not image_data:
        raise HTTPException(
            status_code=404, detail="No generated image found for this project"
        )

    # Supabase Storage URL → redirect
    if image_data.startswith("http"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=image_data)

    # Local file path
    image_path = Path(image_data)
    if image_path.exists():
        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=f"generated_visualization_{project_id}.png",
        )

    # Base64 encoded data → decode and return as bytes
    import base64
    from fastapi.responses import Response
    try:
        image_bytes = base64.b64decode(image_data)
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f'inline; filename="generated_visualization_{project_id}.png"'},
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decode generated image")


@app.post(
    "/projects/{project_id}/clip-search",
    response_model=ClipSearchResponse,
)
async def clip_search_products(project_id: str, req: ClipSearchRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Perform a product search based on a clipped region of the generated image."""
    project = data_manager.get_project(project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        search_result = data_manager.clip_search_products(
            project_id, 
            req.rect,
            use_inspiration_image=req.use_inspiration_image or False
        )
        
        # Construct CLIP analysis info if available
        clip_analysis_info = None
        if "clip_analysis" in search_result and search_result["clip_analysis"]:
            clip_analysis_info = ClipAnalysisInfo(**search_result["clip_analysis"])
        
        return ClipSearchResponse(
            project_id=project_id,
            rect=req.rect,
            search_query=search_result["search_query"],
            products=search_result["products"],
            total_found=search_result["total_found"],
            status="success",
            message=f"Found {search_result['total_found']} products for clipped region",
            analysis_method=search_result.get("analysis_method", "vision"),
            clip_analysis=clip_analysis_info,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed clip-search: {str(e)}")


@app.post(
    "/projects/{project_id}/analyze-furniture-batch",
    response_model=BatchFurnitureAnalysisResponse,
)
async def analyze_furniture_batch(
    project_id: str,
    req: BatchFurnitureAnalysisRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """Analyze multiple furniture items in a batch using CLIP and AI."""
    project = data_manager.get_project(project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if _is_e2e_stub_enabled(x_e2e_test_secret, request=request):
        return BatchFurnitureAnalysisResponse(
            project_id=project_id,
            selections=[
                {
                    "id": item.id or f"sel_{idx}",
                    "furniture_type": item.label or "furniture",
                    "confidence": 0.91,
                    "style": "modern",
                    "material": "wood",
                    "color": "neutral",
                    "search_query": f"{item.label or 'furniture'} modern decor",
                    "products": [
                        {
                            "url": f"https://example.com/{_slugify(item.label or 'furniture')}/1",
                            "title": f"Stub {item.label or 'furniture'} 1",
                            "image_url": "https://example.com/images/furniture-1.jpg",
                            "store": "Target",
                            "price_str": "$149",
                        }
                    ],
                    "is_bed": False,
                    "bed_components": None,
                }
                for idx, item in enumerate(req.selections)
            ],
            overall_analysis="Stub furniture analysis for E2E",
            total_items=len(req.selections),
            status="success",
            message=f"Analyzed {len(req.selections)} furniture items (stub)",
        )

    try:
        # Call data manager to analyze all selections
        analysis_results = data_manager.analyze_furniture_batch(
            project_id,
            req.selections,
            image_type=req.image_type,
            mode=req.mode,
        )
        
        return BatchFurnitureAnalysisResponse(
            project_id=project_id,
            selections=analysis_results["selections"],
            overall_analysis=analysis_results.get("overall_analysis", ""),
            total_items=len(analysis_results["selections"]),
            status="success",
            message=f"Analyzed {len(analysis_results['selections'])} furniture items"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to analyze furniture batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze furniture: {str(e)}")


@app.post(
    "/projects/{project_id}/process-furniture-selection",
    response_model=ProcessFurnitureSelectionResponse,
)
async def process_furniture_selection(
    project_id: str,
    request: ProcessFurnitureSelectionRequest,
    raw_request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """
    Process selected furniture products:
    - Resolve Google Shopping URLs to direct retailer URLs using Exa
    - Group products by retailer
    - Generate affiliate links and cart URLs

    This endpoint is called after furniture analysis when user selects products
    and clicks "Process Selected".
    """
    project = data_manager.get_project(project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if _is_e2e_stub_enabled(x_e2e_test_secret, request=raw_request):
        resolved_products = [
            {
                "original_url": prod.url,
                "resolved_url": prod.url,
                "title": prod.title,
                "image_url": prod.image_url,
                "store": prod.store,
                "price_str": prod.price_str,
                "was_google_shopping": "google.com" in (prod.url or ""),
                "affiliate_url": f"https://affiliate.example.com/redirect?u={idx}",
                "product_id": prod.furniture_id or f"prod_{idx}",
            }
            for idx, prod in enumerate(request.selected_products)
        ]
        return ProcessFurnitureSelectionResponse(
            project_id=project_id,
            resolved_products=[ResolvedProduct(**prod) for prod in resolved_products],
            retailer_carts=[],
            total_products=len(resolved_products),
            resolved_count=len(resolved_products),
            unresolved_count=0,
            status="success",
            message=f"Processed {len(resolved_products)} products (stub)",
        )

    try:
        result = data_manager.process_furniture_selection(
            project_id,
            [p.model_dump() for p in request.selected_products]
        )

        return ProcessFurnitureSelectionResponse(
            project_id=project_id,
            resolved_products=[ResolvedProduct(**p) for p in result["resolved_products"]],
            retailer_carts=[RetailerCart(**c) for c in result["retailer_carts"]],
            total_products=result["total_products"],
            resolved_count=result["resolved_count"],
            unresolved_count=result["unresolved_count"],
            status="success",
            message=f"Processed {result['total_products']} products into {len(result['retailer_carts'])} retailer cart(s)"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process furniture selection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process furniture selection: {str(e)}"
        )


@app.post(
    "/projects/{project_id}/reverse-search-batch",
    response_model=ReverseSearchBatchResponse,
)
async def reverse_search_batch(project_id: str, req: ReverseSearchBatchRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Perform Google Lens reverse image search on multiple selections."""
    project = data_manager.get_project(project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = data_manager.reverse_search_batch(
            project_id,
            req.selections,
            image_type=req.image_type,
        )
        return ReverseSearchBatchResponse(
            project_id=project_id,
            results=result["results"],
            total_items=len(result["results"]),
            status="success",
            message=f"Reverse searched {len(result['results'])} items",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed reverse-search-batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed reverse-search: {str(e)}")


@app.get("/projects/{project_id}/auto-detect")
async def auto_detect(
    project_id: str,
    request: Request,
    image_type: str = "product",
    user: AuthenticatedUser = Depends(get_current_user),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """Auto-detect furniture objects (YOLO if available)."""
    project = data_manager.get_project(project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if _is_e2e_stub_enabled(x_e2e_test_secret, request=request):
        return {
            "project_id": project_id,
            "status": "success",
            "detections": [
                {
                    "id": "stub_hotspot_1",
                    "label": "chair",
                    "confidence": 0.91,
                    "bbox": {"x1": 0.2, "y1": 0.2, "x2": 0.45, "y2": 0.65},
                    "x": 0.325,
                    "y": 0.425,
                }
            ],
            "image_type": image_type,
            "resolved_image_type": image_type,
        }

    try:
        result = data_manager.auto_detect_furniture(project_id, image_type=image_type)
        payload = {"project_id": project_id, **result}
        payload.setdefault("resolved_image_type", image_type)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Auto-detect failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Auto-detect failed: {str(e)}")


@app.get("/projects/{project_id}/replicate-segment")
async def replicate_segment(project_id: str, image_type: str = "product", image_url: Optional[str] = None, user: AuthenticatedUser = Depends(get_current_user)):
    """Segment with Replicate (Mask2Former). If image_url is None, fallback to YOLO."""
    # Verify project ownership
    data_manager.get_project(project_id, user_id=user.id)
    try:
        result = data_manager.replicate_segment(project_id, image_type=image_type, public_image_url=image_url)
        return {"project_id": project_id, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Replicate segment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Replicate segment failed: {str(e)}")


# ============================================================================
# Affiliate Cart Endpoints
# ============================================================================


@app.post("/affiliate/generate-cart", response_model=AffiliateCartResponse)
async def generate_affiliate_cart(
    request: AffiliateCartRequest,
    raw_request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    x_e2e_test_secret: Optional[str] = Header(None, alias="X-E2E-Test-Secret"),
):
    """
    Generate affiliate cart from product URLs with RETAILER-PRESERVING resolution.

    KEY BEHAVIOR:
    - When user selects a "Quince" product, we return quince.com PDP (not Walmart/Target)
    - Uses retailer identity scoring to select best candidate
    - In strict_mode (default), fails instead of returning wrong retailer

    API Options:
    1. NEW (recommended): Use 'items' with retailer_hint for retailer-preserving resolution
    2. LEGACY: Use 'product_urls' for backward compatibility (non-strict resolution)
    """
    from urllib.parse import urlparse

    try:
        if _is_e2e_stub_enabled(x_e2e_test_secret, request=raw_request):
            input_items = request.items or []
            if not input_items and request.product_urls:
                input_items = [
                    AffiliateProductItem(
                        shopping_url=url,
                        retailer_hint="Stub Store",
                        title=f"Stub Product {idx + 1}",
                    )
                    for idx, url in enumerate(request.product_urls)
                ]
            if not input_items:
                input_items = [
                    AffiliateProductItem(
                        shopping_url="https://example.com/stub-product",
                        retailer_hint="Stub Store",
                        title="Stub Product",
                    )
                ]

            products = []
            for idx, item in enumerate(input_items):
                base_url = item.shopping_url or f"https://example.com/product/{idx}"
                products.append(
                    AffiliateProduct(
                        original_url=base_url,
                        resolved_url=base_url,
                        affiliate_url=f"https://affiliate.example.com/redirect?u={idx}",
                        product_id=f"stub_{idx}",
                        product_name=item.title or f"Stub Product {idx + 1}",
                        expected_retailer=item.retailer_hint,
                        actual_retailer=item.retailer_hint or "Stub Store",
                        retailer_matched=True,
                        resolution_source="e2e_stub",
                    )
                )

            cart = RetailerCart(
                retailer="stub_store",
                retailer_display_name="Stub Store",
                products=products,
                cart_url=f"https://affiliate.example.com/cart/{uuid.uuid4().hex[:8]}",
                product_count=len(products),
            )

            return AffiliateCartResponse(
                carts=[cart],
                total_products=len(products),
                total_retailers=1,
                status="success",
                message="Affiliate carts generated successfully (stub)",
                urls_processed=len(input_items),
                urls_resolved=len(input_items),
                urls_validated=len(input_items),
                urls_failed=0,
            )

        from affiliate_client import AffiliateClient
        from serp_client import SerpClient

        affiliate_client = AffiliateClient()
        serp_client = None

        # Try to load retailer identity service
        try:
            from retailer_identity import retailer_identity_service
        except ImportError:
            retailer_identity_service = None
            logger.warning("[AFFILIATE] RetailerIdentityService not available")

        # ============================================================
        # Determine input mode: new 'items' API vs legacy 'product_urls'
        # ============================================================
        use_items_api = request.items and len(request.items) > 0
        strict_mode = request.strict_mode

        if use_items_api:
            items = request.items
            logger.info(f"[AFFILIATE] Using items API with {len(items)} items (strict_mode={strict_mode})")
        else:
            # Legacy mode: convert product_urls to items without retailer hints
            product_urls = request.product_urls or []
            items = [
                type('obj', (object,), {
                    'shopping_url': url,
                    'retailer_hint': None,
                    'expected_domain': None,
                    'title': None,
                })()
                for url in product_urls
            ]
            # Legacy mode uses non-strict by default
            strict_mode = False
            logger.info(f"[AFFILIATE] Using legacy product_urls API with {len(items)} URLs (strict_mode=False)")

        # ============================================================
        # STEP 1: Resolve URLs with retailer-preserving logic
        # ============================================================
        resolved_products = []  # List of {original_url, resolved_url, expected_retailer, actual_retailer, ...}
        resolution_stats = {
            "total": len(items),
            "google_shopping_count": 0,
            "resolved_count": 0,
            "retailer_matched_count": 0,
            "failed_count": 0,
        }

        for item in items:
            url = item.shopping_url.strip() if hasattr(item, 'shopping_url') else str(item).strip()
            if not url:
                continue

            retailer_hint = getattr(item, 'retailer_hint', None)
            expected_domain = getattr(item, 'expected_domain', None)
            product_title = getattr(item, 'title', None)

            # Resolve domain from retailer hint if not provided
            if retailer_hint and not expected_domain and retailer_identity_service:
                expected_domain = retailer_identity_service.resolve_brand_to_domain(retailer_hint)

            logger.info(f"[AFFILIATE] Processing: {url[:60]}... (expected: {retailer_hint or expected_domain or 'any'})")

            # Check if it's a Google Shopping URL
            is_google_shopping = (
                "ibp=oshop" in url.lower() or
                ("google.com/search" in url.lower() and "tbm=shop" in url.lower()) or
                "google.com/shopping" in url.lower()
            )

            if is_google_shopping:
                resolution_stats["google_shopping_count"] += 1

                # Initialize SerpClient lazily
                if serp_client is None:
                    try:
                        serp_client = SerpClient()
                    except Exception as e:
                        logger.error(f"[AFFILIATE] Failed to initialize SerpClient: {e}")
                        resolution_stats["failed_count"] += 1
                        continue

                try:
                    # Use retailer-preserving resolution
                    products = serp_client.resolve_google_shopping_url(
                        google_url=url,
                        max_products=1,  # One PDP per input URL
                        expected_retailer=retailer_hint,
                        expected_domain=expected_domain,
                        strict_mode=strict_mode,
                    )

                    if products and len(products) > 0:
                        resolved = products[0]
                        resolved_url = resolved.get("url")
                        actual_store = resolved.get("store", "")

                        # Check if retailer matched
                        retailer_matched = False
                        if retailer_hint and retailer_identity_service:
                            try:
                                domain = urlparse(resolved_url).netloc.lower().replace("www.", "")
                                retailer_matched = retailer_identity_service.domain_matches_brand(domain, retailer_hint)
                            except Exception:
                                pass

                        if retailer_matched:
                            resolution_stats["retailer_matched_count"] += 1
                            logger.info(f"[AFFILIATE] ✅ Retailer MATCHED: {retailer_hint} -> {resolved_url[:60]}...")
                        else:
                            logger.info(f"[AFFILIATE] ⚠️ Retailer not matched: expected {retailer_hint}, got {actual_store}")

                        resolved_products.append({
                            "original_url": url,
                            "resolved_url": resolved_url,
                            "expected_retailer": retailer_hint,
                            "actual_retailer": actual_store,
                            "retailer_matched": retailer_matched,
                            "title": resolved.get("title", product_title),
                            "resolution_source": resolved.get("source_api", "serpapi"),
                        })
                        resolution_stats["resolved_count"] += 1
                    else:
                        logger.warning(f"[AFFILIATE] No PDP resolved for: {url[:60]}...")
                        resolution_stats["failed_count"] += 1

                except Exception as e:
                    logger.error(f"[AFFILIATE] Resolution failed: {e}")
                    resolution_stats["failed_count"] += 1

            else:
                # Direct retailer URL - just validate and use
                resolved_products.append({
                    "original_url": url,
                    "resolved_url": url,
                    "expected_retailer": retailer_hint,
                    "actual_retailer": None,  # Will be determined from URL
                    "retailer_matched": None,
                    "title": product_title,
                    "resolution_source": "direct",
                })
                resolution_stats["resolved_count"] += 1

        logger.info(
            f"[AFFILIATE] Resolution complete: {resolution_stats['resolved_count']}/{resolution_stats['total']} resolved, "
            f"{resolution_stats['retailer_matched_count']} retailer-matched, "
            f"{resolution_stats['failed_count']} failed"
        )

        # ============================================================
        # STEP 2: Validate resolved URLs
        # ============================================================
        urls_to_validate = [p["resolved_url"] for p in resolved_products if p.get("resolved_url")]
        logger.info(f"[AFFILIATE] Validating {len(urls_to_validate)} URLs...")

        validation_results = affiliate_client.validate_urls(urls_to_validate)

        # Filter to valid products
        valid_products = []
        for product in resolved_products:
            resolved_url = product.get("resolved_url")
            if resolved_url and validation_results.get(resolved_url, {}).get("valid", False):
                valid_products.append(product)
            else:
                logger.warning(f"[AFFILIATE] URL failed validation: {resolved_url[:60] if resolved_url else 'None'}...")

        invalid_count = len(resolved_products) - len(valid_products)

        # ============================================================
        # STEP 3: Process valid URLs and group by retailer
        # ============================================================
        valid_urls = [p["resolved_url"] for p in valid_products]
        grouped_products = affiliate_client.process_urls(valid_urls)

        # Build mapping from resolved_url back to product metadata
        url_to_product = {p["resolved_url"]: p for p in valid_products}

        # Build response with retailer carts
        carts = []
        total_products = 0

        for retailer, products in grouped_products.items():
            affiliate_products = []

            for p in products:
                original_meta = url_to_product.get(p["original_url"], {})

                affiliate_products.append(
                    AffiliateProduct(
                        original_url=original_meta.get("original_url", p["original_url"]),
                        resolved_url=p["original_url"],  # This is actually the resolved URL
                        affiliate_url=p["affiliate_url"],
                        product_id=p["product_id"],
                        product_name=original_meta.get("title"),
                        expected_retailer=original_meta.get("expected_retailer"),
                        actual_retailer=retailer,
                        retailer_matched=original_meta.get("retailer_matched"),
                        resolution_source=original_meta.get("resolution_source"),
                    )
                )

            # Generate cart URL
            product_ids = [p["product_id"] for p in products if p["product_id"] != "unknown"]

            # For Amazon, preserve regional domain
            cart_domain = None
            if retailer == "amazon":
                try:
                    first_url = products[0]["original_url"]
                    parsed = urlparse(first_url)
                    if parsed.netloc and "amazon." in parsed.netloc:
                        cart_domain = parsed.netloc
                except Exception:
                    pass

            cart_url = affiliate_client.generate_cart_url(retailer, product_ids, domain=cart_domain)

            retailer_cart = RetailerCart(
                retailer=retailer,
                retailer_display_name=affiliate_client.get_retailer_display_name(retailer),
                products=affiliate_products,
                cart_url=cart_url,
                product_count=len(affiliate_products),
            )

            carts.append(retailer_cart)
            total_products += len(affiliate_products)

        logger.info(f"[AFFILIATE] Generated {len(carts)} retailer carts with {total_products} products")

        return AffiliateCartResponse(
            carts=carts,
            total_products=total_products,
            total_retailers=len(carts),
            status="success",
            message=f"Generated {len(carts)} affiliate cart(s) with {total_products} product(s). "
                    f"Retailer match rate: {resolution_stats['retailer_matched_count']}/{resolution_stats['google_shopping_count']} Google Shopping URLs.",
            urls_processed=resolution_stats["total"],
            urls_resolved=resolution_stats["resolved_count"],
            urls_validated=len(valid_products),
            urls_failed=invalid_count + resolution_stats["failed_count"],
        )

    except Exception as e:
        logger.error(f"Failed to generate affiliate cart: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate affiliate cart: {str(e)}"
        )


# =============================================================================
# Universal Product Link Normalizer
# =============================================================================

@app.post("/normalize-urls")
async def normalize_urls(request: NormalizeURLsRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Normalize product URLs to canonical retailer PDPs.

    Handles:
    - Google Shopping URLs (extracts retailer links via SerpAPI)
    - Affiliate/tracking redirect URLs (follows redirect chain)
    - Direct retailer URLs (validates and extracts canonical)

    Returns normalized URLs grouped by retailer with validation and classification.
    """
    try:
        # Import url_normalizer module (lazy import to avoid startup issues)
        from url_normalizer.client import URLNormalizerClient
        from url_normalizer.models import (
            URLResolution,
            RetailerGroup,
            NormalizationTelemetry,
        )

        # Initialize client with optional SerpClient
        serp_client = None
        if request.google_shopping_mode == "serpapi":
            try:
                from serp_client import SerpClient
                serp_client = SerpClient()
            except Exception as e:
                logger.warning(f"SerpClient not available for URL normalizer: {e}")

        # Create client
        client = URLNormalizerClient(
            serp_client=serp_client,
            max_concurrent=request.max_concurrent,
            max_per_domain=request.max_per_domain,
            timeout_ms=request.timeout_ms,
        )

        # Normalize URLs
        resolutions, groups, telemetry = await client.normalize_urls(
            urls=request.urls,
            region=request.region,
            language=request.language,
            prefer_domains=request.prefer_domains,
            block_domains=request.block_domains,
            google_shopping_mode=request.google_shopping_mode,
            include_classification=request.include_classification,
            max_candidates_per_url=request.max_candidates_per_url,
        )

        return {
            "results": [r.model_dump() for r in resolutions],
            "groups": [g.model_dump() for g in groups],
            "telemetry": telemetry.model_dump(),
            "status": "success",
            "message": f"Normalized {len(resolutions)} URLs into {len(groups)} retailer groups",
        }

    except ImportError as e:
        logger.error(f"URL Normalizer module not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="URL Normalizer service not available. Check dependencies."
        )
    except Exception as e:
        logger.error(f"Failed to normalize URLs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to normalize URLs: {str(e)}"
        )


# ===== JOB MANAGEMENT ENDPOINTS =====


async def _cleanup_job_after_ttl(jobs: dict, job_id: str, ttl_minutes: int):
    """Remove job from memory after TTL."""
    await asyncio.sleep(ttl_minutes * 60)
    if job_id in jobs:
        del jobs[job_id]
        logger.info(f"Cleaned up expired job: {job_id}")


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(request: Request, job_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Cancel a running job."""
    jobs = request.app.state.jobs
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    if job.get("status") in ("complete", "error", "cancelled"):
        return {"status": job["status"], "message": "Job already finished"}

    # Cancel the task
    if job.get("task") and not job["task"].done():
        job["task"].cancel()

    job["status"] = "cancelled"
    logger.info(f"Job cancelled: {job_id}")
    return {"status": "cancelled"}


@app.get("/jobs/{job_id}/events")
async def job_events(request: Request, job_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """SSE stream for job progress.

    Sends events:
    - started: Initial event with seq=0
    - progress: Updates with progress %, phase, and complete status
    - error: If job not found

    Mobile-friendly:
    - Immediate first event (no waiting)
    - seq field for reconnection handling
    - Periodic updates (300ms)
    """
    jobs = request.app.state.jobs

    async def event_generator():
        seq = 0
        # Send first event immediately (don't wait)
        yield {"event": "started", "data": json.dumps({"seq": seq, "progress": 0})}
        seq += 1

        while True:
            job = jobs.get(job_id)

            if not job:
                yield {"event": "error", "data": json.dumps({"error": "Job not found", "seq": seq})}
                break

            yield {
                "event": "progress",
                "data": json.dumps({
                    "seq": seq,
                    "progress": job.get("progress", 0),
                    "phase": job.get("phase", ""),
                    "complete": job.get("status") in ("complete", "error", "cancelled")
                })
            }
            seq += 1

            if job.get("status") in ("complete", "error", "cancelled"):
                break

            await asyncio.sleep(0.3)

    return EventSourceResponse(event_generator())


@app.get("/jobs/{job_id}")
async def get_job_result(request: Request, job_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Fetch job status and result.

    Returns:
        status: started, running, complete, error, cancelled
        progress: 0-100
        phase: Current phase description
        result: Final result (if complete)
        error: Error message (if error)
    """
    job = request.app.state.jobs.get(job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "status": job["status"],
        "progress": job.get("progress", 0),
        "phase": job.get("phase", ""),
        "result": job.get("result"),
        "error": job.get("error")
    }


# ============================================================================
# Project-scoped Job Status Endpoints (Supabase-backed)
# ============================================================================

@app.get("/projects/{project_id}/job-status/{job_id}")
async def get_project_job_status(
    project_id: str,
    job_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get status of a specific job for a project.

    Returns:
        job_id: The job identifier
        status: queued | processing | done | error | cancelled
        progress_pct: 0-100
        phase: Current operation phase
        result: Final result data (if done)
        error: Error message (if error)
        error_code: Error code (if error)
    """
    # Verify project ownership
    data_manager.get_project(project_id, user_id=user.id)

    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    if job.project_id != project_id:
        raise HTTPException(404, "Job not found for this project")

    # Verify user_id matches for security
    if job.user_id and job.user_id != user.id:
        raise HTTPException(403, "Not authorized to view this job")

    return {
        "job_id": job.id,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "phase": job.phase,
        "result": job.result if job.status == "done" else None,
        "error": job.error if job.status == "error" else None,
        "error_code": job.error_code if job.status == "error" else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@app.get("/projects/{project_id}/jobs")
async def list_project_jobs(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 20,
):
    """List all jobs for a project."""
    # Verify project ownership
    data_manager.get_project(project_id, user_id=user.id)

    jobs = await job_manager.get_project_jobs(project_id, user.id, limit)

    return {
        "project_id": project_id,
        "jobs": [
            {
                "job_id": j.id,
                "job_type": j.job_type,
                "status": j.status,
                "progress_pct": j.progress_pct,
                "phase": j.phase,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
        "total": len(jobs),
    }


@app.post("/projects/{project_id}/jobs/{job_id}/cancel")
async def cancel_project_job(
    project_id: str,
    job_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Cancel a job if it's still queued or processing.

    Returns:
        cancelled: True if job was cancelled, False if already done/error
    """
    # Verify project ownership
    data_manager.get_project(project_id, user_id=user.id)

    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    if job.project_id != project_id:
        raise HTTPException(404, "Job not found for this project")

    if job.user_id and job.user_id != user.id:
        raise HTTPException(403, "Not authorized to cancel this job")

    cancelled = await job_manager.cancel_job(job_id)

    return {
        "job_id": job_id,
        "cancelled": cancelled,
        "message": "Job cancelled" if cancelled else "Job already completed or cancelled",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
