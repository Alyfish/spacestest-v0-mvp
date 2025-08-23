from typing import Dict, List

from pydantic import BaseModel


class ProjectCreateResponse(BaseModel):
    """
    Response model for project creation endpoint.

    Attributes:
        project_id (str): Unique identifier for the created project
        status (str): Status of the project creation operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    status: str
    message: str = "Project created successfully"


class ProjectResponse(BaseModel):
    """
    Response model for retrieving a single project.

    Attributes:
        project_id (str): Unique identifier for the project
        status (str): Current status of the project
        created_at (str): Timestamp when the project was created
        context (dict): Project context and metadata
    """

    project_id: str
    status: str
    created_at: str
    context: dict


class ProjectsListResponse(BaseModel):
    """
    Response model for retrieving a list of all projects.

    Attributes:
        projects (Dict[str, dict]): Dictionary mapping project IDs to project data
        total_count (int): Total number of projects in the system
    """

    projects: Dict[str, dict]
    total_count: int


class ErrorResponse(BaseModel):
    """
    Standard error response model for API endpoints.

    Attributes:
        error (str): Error type or category
        message (str): Detailed error message
    """

    error: str
    message: str


class ImageUploadResponse(BaseModel):
    """
    Response model for image upload operations.

    Attributes:
        project_id (str): ID of the project the image was uploaded to
        image_path (str): File path where the uploaded image is stored
        status (str): Status of the upload operation
        message (str): Human-readable message describing the upload result
    """

    project_id: str
    image_path: str
    status: str
    message: str = "Image uploaded successfully"


class SpaceTypeRequest(BaseModel):
    """
    Request model for setting the space type of a project.

    Attributes:
        space_type (str): Type of space (e.g., 'bedroom', 'kitchen', 'living_room')
    """

    space_type: str


class SpaceTypeResponse(BaseModel):
    """
    Response model for space type selection operations.

    Attributes:
        project_id (str): ID of the project the space type was set for
        space_type (str): The selected space type
        status (str): Status of the space type selection operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    space_type: str
    status: str
    message: str = "Space type selected successfully"


class ImprovementMarker(BaseModel):
    """
    Model representing an improvement marker on an image.

    A marker indicates a specific area on an image that needs improvement,
    with coordinates normalized to the image dimensions (0-1 range).

    Attributes:
        id (str): Unique identifier for the marker
        position (Dict[str, float]): Normalized coordinates as {"x": 0.3, "y": 0.4}
        description (str): Description of the improvement needed at this location
    """

    id: str
    position: Dict[str, float]  # {"x": 0.3, "y": 0.4}
    description: str


class ImprovementMarkersRequest(BaseModel):
    """
    Request model for saving improvement markers to a project.

    Attributes:
        markers (List[ImprovementMarker]): List of improvement markers to save
    """

    markers: List[ImprovementMarker]


class ImprovementMarkersResponse(BaseModel):
    """
    Response model for improvement markers operations.

    Attributes:
        project_id (str): ID of the project the markers belong to
        markers (List[ImprovementMarker]): List of saved improvement markers
        labelled_image_path (str): Path to the image with markers overlaid
        status (str): Status of the markers operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    markers: List[ImprovementMarker]
    labelled_image_path: str
    status: str
    message: str = "Improvement markers saved successfully"


class MarkerRecommendationsResponse(BaseModel):
    """
    Response model for marker recommendations based on space type.

    Attributes:
        project_id (str): ID of the project recommendations are generated for
        space_type (str): Type of space the recommendations are based on
        recommendations (List[str]): List of recommended improvement suggestions
        status (str): Status of the recommendations generation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    space_type: str
    recommendations: List[str]
    status: str
    message: str = "Marker recommendations generated successfully"
