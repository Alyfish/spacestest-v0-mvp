from pathlib import Path

from data_manager import data_manager
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from models import (
    ImageUploadResponse,
    ImprovementMarkersRequest,
    ImprovementMarkersResponse,
    MarkerRecommendationsResponse,
    ProjectCreateResponse,
    ProjectResponse,
    ProjectsListResponse,
    SpaceTypeRequest,
    SpaceTypeResponse,
)

load_dotenv()

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
    project_id = data_manager.create_project()
    project = data_manager.get_project(project_id)

    return ProjectCreateResponse(project_id=project_id, status=project["status"])


@app.get("/projects", response_model=ProjectsListResponse)
async def get_all_projects():
    """Get all projects"""
    projects = data_manager.get_all_projects()
    return ProjectsListResponse(projects=projects, total_count=len(projects))


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a project by ID"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        project_id=project_id,
        status=project["status"],
        created_at=project["created_at"],
        context=project["context"],
    )


@app.post("/projects/{project_id}/upload-image", response_model=ImageUploadResponse)
async def upload_project_image(project_id: str, image: UploadFile = File(...)):
    """Upload an image for a project"""
    # Validate file type
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        image_path = data_manager.upload_image(project_id, image, image.filename)
        project = data_manager.get_project(project_id)

        return ImageUploadResponse(
            project_id=project_id, image_path=image_path, status=project["status"]
        )
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

    if "base_image" not in project["context"]:
        raise HTTPException(
            status_code=404, detail="No base image found for this project"
        )

    image_path = project["context"]["base_image"]

    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(image_path)


@app.get("/projects/{project_id}/labelled-image")
async def get_project_labelled_image(project_id: str):
    """Get the labelled image for a project"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if "labelled_base_image" not in project["context"]:
        raise HTTPException(
            status_code=404, detail="No labelled image found for this project"
        )

    image_path = project["context"]["labelled_base_image"]

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

    if "marker_recommendations" not in project["context"]:
        raise HTTPException(
            status_code=404, detail="No marker recommendations found for this project"
        )

    return MarkerRecommendationsResponse(
        project_id=project_id,
        space_type=project["context"]["space_type"],
        recommendations=project["context"]["marker_recommendations"],
        status=project["status"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
