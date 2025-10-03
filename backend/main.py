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
    InspirationImageGenerationResponse,
    InspirationImagesBatchUploadResponse,
    InspirationImageUploadResponse,
    InspirationRecommendationsResponse,
    MarkerRecommendationsResponse,
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

    # Check if project has inspiration recommendations (regardless of status)
    context = ProjectContext.model_validate(project["context"])
    has_inspiration_recs = (
        context.inspiration_recommendations 
        and len(context.inspiration_recommendations) > 0
    )
    
    if not has_inspiration_recs:
        logger.warning(
            "Project has no inspiration recommendations",
            extra={
                "project_id": project_id,
                "current_status": project["status"],
                "has_inspiration_recs": False,
            },
        )
        raise HTTPException(
            status_code=400,
            detail="Project must have inspiration recommendations first. Upload inspiration images and generate recommendations.",
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

    if project["status"] != "PRODUCT_RECOMMENDATIONS_READY":
        raise HTTPException(
            status_code=400,
            detail="Project must have product recommendations ready first",
        )

    try:
        selected = data_manager.select_product_recommendation(
            project_id, selection_request.selected_recommendation
        )
        project = data_manager.get_project(project_id)

        return ProductRecommendationSelectionResponse(
            project_id=project_id,
            selected_recommendation=selected,
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
            selected_recommendation=context.selected_product_recommendation or "",
            search_query=search_result["search_query"],
            products=search_result["products"],
            total_found=search_result["total_found"],
            status=project["status"],
            message=f"Found {search_result['total_found']} products for '{context.selected_product_recommendation}'",
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

    if project["status"] != "PRODUCT_SEARCH_COMPLETE":
        raise HTTPException(
            status_code=400,
            detail="Project must have completed product search first",
        )

    try:
        selected = data_manager.select_product_for_generation(
            project_id,
            selection_request.product_url,
            selection_request.product_title,
            selection_request.product_image_url,
            selection_request.generation_prompt,
        )

        return ProductSelectionResponse(
            project_id=project_id,
            selected_product=selected["selected_product"],
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
            selected_product=generation_result["selected_product"],
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
        search_result = data_manager.clip_search_products(project_id, req.rect)
        return ClipSearchResponse(
            project_id=project_id,
            rect=req.rect,
            search_query=search_result["search_query"],
            products=search_result["products"],
            total_found=search_result["total_found"],
            status="success",
            message=f"Found {search_result['total_found']} products for clipped region",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed clip-search: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
