from typing import Dict, List

from pydantic import BaseModel


class ProjectCreateResponse(BaseModel):
    project_id: str
    status: str
    message: str = "Project created successfully"


class ProjectResponse(BaseModel):
    project_id: str
    status: str
    created_at: str
    context: dict


class ProjectsListResponse(BaseModel):
    projects: Dict[str, dict]
    total_count: int


class ErrorResponse(BaseModel):
    error: str
    message: str


class ImageUploadResponse(BaseModel):
    project_id: str
    image_path: str
    status: str
    message: str = "Image uploaded successfully"


class SpaceTypeRequest(BaseModel):
    space_type: str


class SpaceTypeResponse(BaseModel):
    project_id: str
    space_type: str
    status: str
    message: str = "Space type selected successfully"


class ImprovementMarker(BaseModel):
    id: str
    position: Dict[str, float]  # {"x": 0.3, "y": 0.4}
    description: str


class ImprovementMarkersRequest(BaseModel):
    markers: List[ImprovementMarker]


class ImprovementMarkersResponse(BaseModel):
    project_id: str
    markers: List[ImprovementMarker]
    labelled_image_path: str
    status: str
    message: str = "Improvement markers saved successfully"


class MarkerRecommendationsResponse(BaseModel):
    project_id: str
    space_type: str
    recommendations: List[str]
    status: str
    message: str = "Marker recommendations generated successfully"
