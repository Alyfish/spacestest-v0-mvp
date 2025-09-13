from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
        context (ProjectContext): Project context and metadata
    """

    project_id: str
    status: str
    created_at: str
    context: "ProjectContext"


class ProjectSummary(BaseModel):
    """
    Summary model for projects in the list view.

    Attributes:
        status (str): Current status of the project
        created_at (str): Timestamp when the project was created
        context (ProjectContext): Project context and metadata
    """

    status: str
    created_at: str
    context: "ProjectContext"


class ProjectsListResponse(BaseModel):
    """
    Response model for retrieving a list of all projects.

    Attributes:
        projects (Dict[str, ProjectSummary]): Dictionary mapping project IDs to project summaries
        total_count (int): Total number of projects in the system
    """

    projects: Dict[str, ProjectSummary]
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
        status (str): Status of the upload operation
        message (str): Human-readable message describing the upload result
    """

    project_id: str
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


class MarkerPosition(BaseModel):
    """
    Model representing the position of a marker on an image.

    Coordinates are normalized to the image dimensions (0-1 range).

    Attributes:
        x (float): X coordinate (0-1 range)
        y (float): Y coordinate (0-1 range)
    """

    x: float = Field(..., ge=0.0, le=1.0, description="X coordinate (0-1 range)")
    y: float = Field(..., ge=0.0, le=1.0, description="Y coordinate (0-1 range)")


class ImprovementMarker(BaseModel):
    """
    Model representing an improvement marker on an image.

    A marker indicates a specific area on an image that needs improvement,
    with coordinates normalized to the image dimensions (0-1 range).

    Attributes:
        id (str): Unique identifier for the marker
        position (MarkerPosition): Normalized coordinates
        description (str): Description of the improvement needed at this location
        color (str): Visual color identifier for the marker
    """

    id: str
    position: MarkerPosition
    description: str
    color: str = Field(
        ..., description="Color identifier (red, green, blue, purple, orange)"
    )


class ProjectContext(BaseModel):
    """
    Project context that evolves through the design workflow.

    Contains the essential data needed for each step of the design process.
    """

    # Core data
    base_image: Optional[str] = None
    is_base_image_empty_room: Optional[bool] = None
    space_type: Optional[str] = None
    improvement_markers: List[ImprovementMarker] = Field(default_factory=list)
    labelled_base_image: Optional[str] = None
    marker_recommendations: List[str] = Field(default_factory=list)

    # Inspiration images
    inspiration_images: List[str] = Field(
        default_factory=list, description="Paths to uploaded inspiration images"
    )
    inspiration_recommendations: List[str] = Field(
        default_factory=list,
        description="AI recommendations based on inspiration images",
    )

    def is_ready_for_markers(self) -> bool:
        """Check if ready for marker placement."""
        return (
            self.base_image is not None
            and self.space_type is not None
            and self.is_base_image_empty_room is False
        )

    def is_ready_for_recommendations(self) -> bool:
        """Check if ready for AI recommendations."""
        return (
            self.base_image is not None
            and self.space_type is not None
            and len(self.improvement_markers) > 0
            and self.labelled_base_image is not None
        )

    def is_ready_for_inspiration(self) -> bool:
        """Check if ready for inspiration image upload."""
        return (
            self.base_image is not None
            and self.space_type is not None
            and len(self.improvement_markers) > 0
            and self.labelled_base_image is not None
        )


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


class InspirationImageUploadResponse(BaseModel):
    """
    Response model for inspiration image upload operations.

    Attributes:
        project_id (str): ID of the project the image was uploaded to
        image_path (str): File path where the uploaded inspiration image is stored
        status (str): Status of the upload operation
        message (str): Human-readable message describing the upload result
    """

    project_id: str
    image_path: str
    status: str
    message: str = "Inspiration image uploaded successfully"


class InspirationImagesBatchUploadResponse(BaseModel):
    """
    Response model for batch inspiration images upload operations.

    Attributes:
        project_id (str): ID of the project the images were uploaded to
        image_paths (List[str]): File paths where the uploaded inspiration images are stored
        uploaded_count (int): Number of images successfully uploaded
        status (str): Status of the upload operation
        message (str): Human-readable message describing the upload result
    """

    project_id: str
    image_paths: List[str]
    uploaded_count: int
    status: str
    message: str = "Inspiration images uploaded successfully"


class InspirationRecommendationsResponse(BaseModel):
    """
    Response model for inspiration-based recommendations.

    Attributes:
        project_id (str): ID of the project recommendations are generated for
        space_type (str): Type of space the recommendations are based on
        recommendations (List[str]): List of inspiration-based design suggestions
        status (str): Status of the recommendations generation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    space_type: str
    recommendations: List[str]
    status: str
    message: str = "Inspiration recommendations generated successfully"
