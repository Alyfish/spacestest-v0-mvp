from pathlib import Path
from typing import List

from data_manager import data_manager
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from logger_config import setup_logging
from models import (
    ImageGenerationResponse,
    ImageUploadResponse,
    ImprovementMarkersRequest,
    ImprovementMarkersResponse,
    MarkerRecommendationsResponse,
    InspirationImageGenerationResponse,
    InspirationImagesBatchUploadResponse,
    InspirationImageUploadResponse,
    InspirationRecommendationsResponse,
    ProductRecommendationSelectionRequest,
    ProductRecommendationSelectionResponse,
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
    RetailerCart,
    ApplyColorRequest,
    ApplyColorResponse,
    ApplyStyleRequest,
    ApplyStyleResponse,
    PreferredStoresRequest,
    PreferredStoresResponse,
)

load_dotenv()

# Initialize logging
logger = setup_logging()

app = FastAPI(title="AI Interior Design Agent", version="1.0.0", root_path="/api")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
async def create_project():
    """Create a new project"""
    logger.info("Received request to create new project")
    project_id = data_manager.create_project()
    project = data_manager.get_project(project_id)

    return ProjectCreateResponse(project_id=project_id, status=project["status"])


@app.get("/projects", response_model=ProjectsListResponse)
async def get_all_projects():
    """Get all projects"""
    projects_dict = data_manager.get_all_projects()

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
async def get_project(project_id: str):
    """Get a project by ID"""
    project = data_manager.get_project(project_id)

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
async def delete_project(project_id: str):
    """Delete a project"""
    if not data_manager.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"status": "success", "message": f"Project {project_id} deleted successfully"}


@app.post("/projects/{project_id}/upload-image", response_model=ImageUploadResponse)
async def upload_project_image(project_id: str, image: UploadFile = File(...)):
    """Upload an image for a project"""
    # Validate file type
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        data_manager.upload_image(project_id, image, image.filename)
        project = data_manager.get_project(project_id)

        return ImageUploadResponse(project_id=project_id, status=project["status"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@app.get("/projects/{project_id}/base-image")
async def get_project_base_image(project_id: str):
    """Get the base image for a project"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    if context.base_image is None:
        raise HTTPException(
            status_code=404, detail="No base image found for this project"
        )

    image_path = context.base_image

    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(image_path)


@app.get("/projects/{project_id}/labelled-image")
async def get_project_labelled_image(project_id: str):
    """Get the labelled image for a project"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    if context.labelled_base_image is None:
        raise HTTPException(
            status_code=404, detail="No labelled image found for this project"
        )

    image_path = context.labelled_base_image

    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Labelled image file not found")

    return FileResponse(image_path)


@app.post("/projects/{project_id}/space-type", response_model=SpaceTypeResponse)
async def select_project_space_type(
    project_id: str, space_type_request: SpaceTypeRequest
):
    """Select space type for a project"""
    try:
        space_type = data_manager.select_space_type(
            project_id, space_type_request.space_type
        )
        project = data_manager.get_project(project_id)

        return SpaceTypeResponse(
            project_id=project_id, space_type=space_type, status=project["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to select space type: {str(e)}"
        )


@app.post(
    "/projects/{project_id}/improvement-markers",
    response_model=ImprovementMarkersResponse,
)
async def save_improvement_markers(
    project_id: str, markers_request: ImprovementMarkersRequest
):
    """Save improvement markers for a project"""
    try:
        labelled_image_path = data_manager.save_improvement_markers(
            project_id, markers_request.markers
        )
        project = data_manager.get_project(project_id)

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
async def get_marker_recommendations(project_id: str):
    """Get AI-generated recommendations for improvement markers"""
    project = data_manager.get_project(project_id)

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
async def generate_marker_recommendations(project_id: str):
    """Generate marker-based AI recommendations when the project is ready (color/style/stores set)."""
    try:
        recs = data_manager.trigger_marker_recommendations(project_id)
        project = data_manager.get_project(project_id)
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
async def upload_inspiration_image(project_id: str, image: UploadFile = File(...)):
    """Upload an inspiration image for a project"""
    # Validate file type
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        image_path = data_manager.upload_inspiration_image(
            project_id, image, image.filename
        )
        project = data_manager.get_project(project_id)

        return InspirationImageUploadResponse(
            project_id=project_id, image_path=image_path, status=project["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload inspiration image: {str(e)}"
        )


@app.post(
    "/projects/{project_id}/inspiration-images-batch",
    response_model=InspirationImagesBatchUploadResponse,
)
async def upload_inspiration_images_batch(
    project_id: str, images: List[UploadFile] = File(...)
):
    """Upload multiple inspiration images for a project in one batch"""
    # Validate all files are images
    for image in images:
        if not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail=f"File {image.filename} is not an image"
            )

    try:
        image_paths = data_manager.upload_inspiration_images_batch(project_id, images)
        project = data_manager.get_project(project_id)

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
async def get_inspiration_image(project_id: str, image_index: int):
    """Get an inspiration image for a project by index"""
    project = data_manager.get_project(project_id)

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

    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Inspiration image file not found")

    return FileResponse(image_path)


@app.post(
    "/projects/{project_id}/inspiration-recommendations",
    response_model=InspirationRecommendationsResponse,
)
async def generate_inspiration_recommendations(project_id: str):
    """Generate AI recommendations based on inspiration images"""
    project = data_manager.get_project(project_id)

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
        project = data_manager.get_project(project_id)
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
    response_model=InspirationImageGenerationResponse,
)
async def generate_inspiration_redesign(project_id: str):
    """Generate a redesigned room image based on inspiration recommendations"""
    logger.info(
        "API request: generate inspiration redesign",
        extra={"project_id": project_id},
    )
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if project has inspiration recommendations OR product recommendations
    context = ProjectContext.model_validate(project["context"])
    has_inspiration_recs = (
        context.inspiration_recommendations 
        and len(context.inspiration_recommendations) > 0
    )
    has_product_recs = (
        context.product_recommendations
        and len(context.product_recommendations) > 0
    )
    
    if not has_inspiration_recs and not has_product_recs:
        logger.warning(
            "Project has no inspiration or product recommendations",
            extra={
                "project_id": project_id,
                "current_status": project["status"],
                "has_inspiration_recs": False,
                "has_product_recs": False,
            },
        )
        raise HTTPException(
            status_code=400,
            detail="Project must have either inspiration or product recommendations first.",
        )

    try:
        logger.info(
            "Starting inspiration redesign",
            extra={
                "project_id": project_id,
                "current_status": project["status"],
            },
        )
        result = data_manager.generate_inspiration_redesign(project_id)

        logger.info(
            "Inspiration redesign generated successfully",
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
        )
    except ValueError as e:
        logger.error(
            "Inspiration redesign failed: ValueError",
            extra={"project_id": project_id, "error": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(
            "Inspiration redesign failed: Unexpected error",
            extra={
                "project_id": project_id,
                "error": str(e),
                "trace": traceback.format_exc(),
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate inspiration redesign: {str(e)}",
        )


@app.post(
    "/projects/{project_id}/apply-color-scheme",
    response_model=ApplyColorResponse,
)
async def apply_color_scheme(project_id: str, color_request: ApplyColorRequest):
    """Apply a color scheme to the project using the Color Agent for analysis"""
    logger.info(
        "API request: apply color scheme",
        extra={
            "project_id": project_id,
            "palette_name": color_request.palette_name,
            "let_ai_decide": color_request.let_ai_decide,
        },
    )
    project = data_manager.get_project(project_id)

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
async def apply_style(project_id: str, style_request: ApplyStyleRequest):
    """Apply an interior design style to the project using the Style Agent for analysis"""
    logger.info(
        "API request: apply style",
        extra={
            "project_id": project_id,
            "style_name": style_request.style_name,
            "let_ai_decide": style_request.let_ai_decide,
        },
    )
    project = data_manager.get_project(project_id)

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
async def skip_color_analysis(project_id: str):
    """Skip color analysis to unblock downstream steps."""
    project = data_manager.get_project(project_id)

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
        project = data_manager.get_project(project_id)
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
async def skip_style_analysis(project_id: str):
    """Skip style analysis to unblock downstream steps."""
    project = data_manager.get_project(project_id)

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
        project = data_manager.get_project(project_id)
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
async def skip_inspiration_images(project_id: str):
    """Skip inspiration images to unblock downstream steps."""
    project = data_manager.get_project(project_id)

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
        project = data_manager.get_project(project_id)
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
    project_id: str, store_request: PreferredStoresRequest
):
    """Update user's preferred retail stores in the project context"""
    logger.info(
        "API request: update preferred stores",
        extra={
            "project_id": project_id,
            "stores": store_request.stores,
        },
    )
    project = data_manager.get_project(project_id)

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
async def generate_product_recommendations(project_id: str):
    """Generate AI product recommendations based on project context"""
    logger.info(
        "API request: generate product recommendations",
        extra={"project_id": project_id},
    )
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        logger.info(
            "Generating product recommendations",
            extra={"project_id": project_id, "current_status": project["status"]},
        )

        recommendations = data_manager.generate_product_recommendations(project_id)
        project = data_manager.get_project(project_id)
        context = ProjectContext.model_validate(project["context"])

        logger.info(
            "Product recommendations generated successfully",
            extra={
                "project_id": project_id,
                "recommendations_count": len(recommendations),
                "new_status": project["status"],
            },
        )

        return ProductRecommendationsResponse(
            project_id=project_id,
            space_type=context.space_type or "unknown",
            recommendations=recommendations,
            status=project["status"],
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
    project_id: str, selection_request: ProductRecommendationSelectionRequest
):
    """Select a product recommendation option"""
    project = data_manager.get_project(project_id)

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
        project = data_manager.get_project(project_id)

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


@app.post(
    "/projects/{project_id}/product-search",
    response_model=ProductSearchResponse,
)
async def search_products(project_id: str):
    """Search for products based on selected recommendation using AI and Exa"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["status"] != "PRODUCT_RECOMMENDATION_SELECTED":
        raise HTTPException(
            status_code=400,
            detail="Project must have a selected product recommendation first",
        )

    try:
        search_result = data_manager.search_products(project_id)
        project = data_manager.get_project(project_id)
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
    "/projects/{project_id}/product-selection",
    response_model=ProductSelectionResponse,
)
async def select_product_for_generation(
    project_id: str, selection_request: ProductSelectionRequest
):
    """Select a product for Gemini image generation"""
    project = data_manager.get_project(project_id)

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
    response_model=ImageGenerationResponse,
)
async def generate_product_visualization(project_id: str):
    """Generate a new image visualization using Gemini with the selected product"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["status"] != "PRODUCT_SELECTED":
        raise HTTPException(
            status_code=400,
            detail="Project must have a selected product first",
        )

    try:
        generation_result = data_manager.generate_product_visualization(project_id)

        return ImageGenerationResponse(
            project_id=project_id,
            selected_products=generation_result["selected_products"],
            generated_image_base64=generation_result["generated_image_base64"],
            generation_prompt=generation_result["generation_prompt"],
            status="success",
            message=generation_result["message"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate image: {str(e)}"
        )


@app.get("/projects/{project_id}/generated-image")
async def get_generated_image(project_id: str):
    """Serve the generated image for a project"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    context = ProjectContext.model_validate(project["context"])

    if not context.generated_image_path:
        raise HTTPException(
            status_code=404, detail="No generated image found for this project"
        )

    image_path = Path(context.generated_image_path)

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Generated image file not found")

    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=f"generated_visualization_{project_id}.png",
    )


@app.post(
    "/projects/{project_id}/clip-search",
    response_model=ClipSearchResponse,
)
async def clip_search_products(project_id: str, req: ClipSearchRequest):
    """Perform a product search based on a clipped region of the generated image."""
    project = data_manager.get_project(project_id)
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
async def analyze_furniture_batch(project_id: str, req: BatchFurnitureAnalysisRequest):
    """Analyze multiple furniture items in a batch using CLIP and AI."""
    project = data_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Call data manager to analyze all selections
        analysis_results = data_manager.analyze_furniture_batch(
            project_id,
            req.selections,
            image_type=req.image_type
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
    "/projects/{project_id}/reverse-search-batch",
    response_model=ReverseSearchBatchResponse,
)
async def reverse_search_batch(project_id: str, req: ReverseSearchBatchRequest):
    """Perform Google Lens reverse image search on multiple selections."""
    project = data_manager.get_project(project_id)
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
async def auto_detect(project_id: str, image_type: str = "product"):
    """Auto-detect furniture objects (YOLO if available)."""
    project = data_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = data_manager.auto_detect_furniture(project_id, image_type=image_type)
        return {"project_id": project_id, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Auto-detect failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Auto-detect failed: {str(e)}")


@app.get("/projects/{project_id}/replicate-segment")
async def replicate_segment(project_id: str, image_type: str = "product", image_url: str | None = None):
    """Segment with Replicate (Mask2Former). If image_url is None, fallback to YOLO."""
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
async def generate_affiliate_cart(request: AffiliateCartRequest):
    """
    Generate affiliate cart from product URLs.
    Groups products by retailer and creates cart URLs.
    """
    logger.info(f"API request: generate affiliate cart for {len(request.product_urls)} URLs")
    
    try:
        from affiliate_client import AffiliateClient
        
        affiliate_client = AffiliateClient()
        
        # Process URLs and group by retailer
        grouped_products = affiliate_client.process_urls(request.product_urls)
        
        # Build response with retailer carts
        carts = []
        total_products = 0
        
        for retailer, products in grouped_products.items():
            # Convert to AffiliateProduct models
            affiliate_products = [
                AffiliateProduct(
                    original_url=p["original_url"],
                    affiliate_url=p["affiliate_url"],
                    product_id=p["product_id"],
                )
                for p in products
            ]
            
            # Generate cart URL for all products from this retailer
            product_ids = [p["product_id"] for p in products if p["product_id"] != "unknown"]

            # For Amazon, preserve original regional domain per group (e.g., amazon.ca vs amazon.com)
            cart_domain = None
            if retailer == "amazon":
                try:
                    # Extract domain from the first product's original URL
                    from urllib.parse import urlparse
                    first_url = products[0]["original_url"]
                    parsed = urlparse(first_url)
                    if parsed.netloc and "amazon." in parsed.netloc:
                        cart_domain = parsed.netloc
                except Exception:
                    cart_domain = None

            cart_url = affiliate_client.generate_cart_url(retailer, product_ids, domain=cart_domain)
            
            # Create retailer cart
            retailer_cart = RetailerCart(
                retailer=retailer,
                retailer_display_name=affiliate_client.get_retailer_display_name(retailer),
                products=affiliate_products,
                cart_url=cart_url,
                product_count=len(affiliate_products),
            )
            
            carts.append(retailer_cart)
            total_products += len(affiliate_products)
        
        logger.info(f"Generated {len(carts)} retailer carts with {total_products} total products")
        
        return AffiliateCartResponse(
            carts=carts,
            total_products=total_products,
            total_retailers=len(carts),
            status="success",
            message=f"Generated {len(carts)} affiliate cart(s) with {total_products} product(s)",
        )
        
    except Exception as e:
        logger.error(f"Failed to generate affiliate cart: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate affiliate cart: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
