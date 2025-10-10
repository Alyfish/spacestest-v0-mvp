from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ColorPalette(BaseModel):
    """
    Model for color palette selection
    """
    name: str
    colors: List[str]  # List of hex color codes
    description: Optional[str] = None


class ColorSchemeRequest(BaseModel):
    """
    Request model for setting color scheme for a project
    """
    project_id: str
    palette_name: str
    colors: List[str]  # List of hex color codes
    keep_original: bool = False  # If true, use original image colors


class StyleOption(BaseModel):
    """
    Model for design style selection
    """
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None  # Preview image for the style


class StyleSelectionRequest(BaseModel):
    """
    Request model for setting design style for a project
    """
    project_id: str
    style_name: str
    keep_original: bool = False  # If true, maintain original room style


class GenerateWithProductRequest(BaseModel):
    """
    Request model for generating image with product and color scheme
    """
    project_id: str
    product_url: str
    product_title: str
    color_scheme: Optional[ColorSchemeRequest] = None
    use_original_colors: bool = False


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

    # Product recommendations
    product_recommendations: List[str] = Field(
        default_factory=list,
        description="AI-generated product recommendations (e.g., 'change sofa', 'add photo frame')",
    )
    selected_product_recommendation: Optional[str] = Field(
        default=None, description="The product recommendation selected by the user"
    )
    product_search_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Exa search results for products matching the selected recommendation",
    )
    selected_product: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The specific product selected by the user for image generation",
    )
    generated_image_base64: Optional[str] = Field(
        default=None, description="Base64 encoded Gemini-generated image"
    )
    generation_prompt: Optional[str] = Field(
        default=None, description="The prompt used for Gemini image generation"
    )
    color_scheme: Optional[Dict[str, Any]] = Field(
        default=None, description="Selected color scheme for image generation"
    )
    design_style: Optional[Dict[str, Any]] = Field(
        default=None, description="Selected design style for image generation"
    )
    
    # Inspiration-based image generation
    inspiration_generated_image_base64: Optional[str] = Field(
        default=None, description="Base64 encoded inspiration-redesigned image"
    )
    inspiration_generation_prompt: Optional[str] = Field(
        default=None, description="The prompt used for inspiration-based generation"
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

    def is_ready_for_product_recommendations(self) -> bool:
        """Check if ready for product recommendations."""
        return (
            self.base_image is not None
            and self.space_type is not None
            and len(self.inspiration_recommendations) > 0
        )

    def is_ready_for_product_search(self) -> bool:
        """Check if ready for product search."""
        return (
            self.is_ready_for_product_recommendations()
            and len(self.product_recommendations) > 0
            and self.selected_product_recommendation is not None
        )

    def is_ready_for_product_selection(self) -> bool:
        """Check if ready for product selection."""
        return (
            self.is_ready_for_product_search() and len(self.product_search_results) > 0
        )

    def is_ready_for_image_generation(self) -> bool:
        """Check if ready for Gemini image generation."""
        return (
            self.is_ready_for_product_selection() and self.selected_product is not None
        )
    
    def is_ready_for_inspiration_redesign(self) -> bool:
        """Check if ready for inspiration-based image redesign."""
        return (
            self.base_image is not None
            and self.space_type is not None
            and len(self.inspiration_recommendations) > 0
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


class ProductRecommendationsResponse(BaseModel):
    """
    Response model for product recommendations generation.

    Attributes:
        project_id (str): ID of the project recommendations are generated for
        space_type (str): Type of space the recommendations are based on
        recommendations (List[str]): List of product recommendation options
        status (str): Status of the recommendations generation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    space_type: str
    recommendations: List[str]
    status: str
    message: str = "Product recommendations generated successfully"


class ProductRecommendationSelectionRequest(BaseModel):
    """
    Request model for selecting a product recommendation.

    Attributes:
        selected_recommendation (str): The product recommendation selected by the user
    """

    selected_recommendation: str


class ProductRecommendationSelectionResponse(BaseModel):
    """
    Response model for product recommendation selection.

    Attributes:
        project_id (str): ID of the project
        selected_recommendation (str): The selected recommendation
        status (str): Status of the selection operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    selected_recommendation: str
    status: str
    message: str = "Product recommendation selected successfully"


class ProductSearchResponse(BaseModel):
    """
    Response model for product search results.

    Attributes:
        project_id (str): ID of the project
        selected_recommendation (str): The recommendation that was searched for
        search_query (str): The AI-generated search query used
        products (List[Dict[str, Any]]): List of found products with details
        total_found (int): Total number of products found
        status (str): Status of the search operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    selected_recommendation: str
    search_query: str
    products: List[Dict[str, Any]]
    total_found: int
    status: str
    message: str


class ProductSelectionRequest(BaseModel):
    """
    Request model for selecting a product for image generation.

    Attributes:
        product_url (str): URL of the selected product
        product_title (str): Title of the selected product
        product_image_url (str): Image URL of the selected product
        generation_prompt (str): Custom prompt for image generation (optional)
        color_scheme (dict): Color scheme selection (optional)
        design_style (dict): Design style selection (optional)
    """

    product_url: str
    product_title: str
    product_image_url: str
    generation_prompt: Optional[str] = None
    color_scheme: Optional[Dict[str, Any]] = None
    design_style: Optional[Dict[str, Any]] = None


class ProductSelectionResponse(BaseModel):
    """
    Response model for product selection.

    Attributes:
        project_id (str): ID of the project
        selected_product (Dict[str, Any]): Details of the selected product
        status (str): Status of the selection operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    selected_product: Dict[str, Any]
    status: str
    message: str


class ImageGenerationResponse(BaseModel):
    """
    Response model for Gemini image generation.

    Attributes:
        project_id (str): ID of the project
        selected_product (Dict[str, Any]): Details of the product used for generation
        generated_image_base64 (str): Base64 encoded generated image
        generation_prompt (str): The prompt used for image generation
        status (str): Status of the generation operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    selected_product: Dict[str, Any]
    generated_image_base64: str  # Return base64 string instead of URL
    generation_prompt: str
    status: str
    message: str = "Image generation completed successfully"


class InspirationImageGenerationResponse(BaseModel):
    """
    Response model for inspiration-based image redesign.

    Attributes:
        project_id (str): The unique identifier for the project
        generated_image_base64 (str): Base64 encoded redesigned image
        inspiration_prompt (str): The prompt used for inspiration-based generation
        inspiration_recommendations (List[str]): The inspiration recommendations used
        status (str): Status of the generation operation
        message (str): Human-readable message about the result
    """

    project_id: str
    generated_image_base64: str
    inspiration_prompt: str
    inspiration_recommendations: List[str]
    status: str
    message: str = "Inspiration-based image redesign completed successfully"


class ClipRect(BaseModel):
    """
    Normalized rectangle describing a selection on an image.

    Coordinates are normalized to the image dimensions (0-1 range).
    """

    x: float = Field(..., ge=0.0, le=1.0, description="Top-left X (0-1)")
    y: float = Field(..., ge=0.0, le=1.0, description="Top-left Y (0-1)")
    width: float = Field(..., ge=0.0, le=1.0, description="Width (0-1)")
    height: float = Field(..., ge=0.0, le=1.0, description="Height (0-1)")


class ClipSearchRequest(BaseModel):
    """
    Request model for clip-based product search on the generated image.
    """

    rect: ClipRect
    use_inspiration_image: Optional[bool] = Field(
        default=False,
        description="If true, use inspiration redesign image instead of product visualization"
    )


class ClipAnalysisInfo(BaseModel):
    """
    CLIP analysis information for a searched region.
    """
    furniture_type: Optional[str] = None
    furniture_confidence: Optional[float] = None
    style: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None


class FurnitureSelection(BaseModel):
    """
    Represents a single furniture selection on an image.
    """
    id: str
    x: float = Field(..., ge=0.0, le=1.0, description="X coordinate (0-1 range)")
    y: float = Field(..., ge=0.0, le=1.0, description="Y coordinate (0-1 range)")
    label: Optional[str] = None


class BatchFurnitureAnalysisRequest(BaseModel):
    """
    Request model for batch furniture analysis.
    """
    selections: List[FurnitureSelection]
    image_type: str = Field(
        default="product", 
        description="Type of image: 'product' or 'inspiration'"
    )


class FurnitureAnalysisItem(BaseModel):
    """
    Analysis result for a single furniture item.
    """
    id: str
    furniture_type: str
    confidence: float
    style: str
    material: str
    color: str
    search_query: str
    products: List[Dict[str, Any]]


class BatchFurnitureAnalysisResponse(BaseModel):
    """
    Response model for batch furniture analysis.
    """
    project_id: str
    selections: List[FurnitureAnalysisItem]
    overall_analysis: str
    total_items: int
    status: str
    message: str


class ReverseSearchBatchRequest(BaseModel):
    """
    Request model for reverse image search on multiple selections.
    """
    selections: List[FurnitureSelection]
    image_type: str = Field(
        default="product",
        description="Type of image: 'product' or 'inspiration'",
    )


class ReverseSearchMatch(BaseModel):
    """
    A single match returned by Google Lens via SerpAPI.
    """
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    thumbnail: Optional[str] = None


class ReverseSearchItemResult(BaseModel):
    id: str
    image_url: Optional[str] = None
    matches: List[ReverseSearchMatch]


class ReverseSearchBatchResponse(BaseModel):
    project_id: str
    results: List[ReverseSearchItemResult]
    total_items: int
    status: str
    message: str


class ClipSearchResponse(BaseModel):
    """
    Response model for clip-based product search results.
    """

    project_id: str
    rect: ClipRect
    search_query: str
    products: List[Dict[str, Any]]
    total_found: int
    status: str
    message: str
    analysis_method: Optional[str] = Field(
        default="vision", description="Method used for analysis: 'clip' or 'vision'"
    )
    clip_analysis: Optional[ClipAnalysisInfo] = Field(
        default=None, description="CLIP-based analysis results if available"
    )


# ============================================================================
# Affiliate Cart Models
# ============================================================================


class AffiliateCartRequest(BaseModel):
    """
    Request model for generating affiliate cart from product URLs.
    """
    product_urls: List[str] = Field(
        ..., description="List of product URLs to convert to affiliate links"
    )


class AffiliateProduct(BaseModel):
    """
    Model for a single product with affiliate link.
    """
    original_url: str = Field(..., description="Original product URL")
    affiliate_url: str = Field(..., description="Affiliate version of the URL")
    product_id: str = Field(..., description="Extracted product ID")
    product_name: Optional[str] = Field(None, description="Product name if available")


class RetailerCart(BaseModel):
    """
    Model for a retailer-specific cart with multiple products.
    """
    retailer: str = Field(..., description="Retailer identifier (e.g., 'amazon', 'ikea')")
    retailer_display_name: str = Field(..., description="Display name for the retailer")
    products: List[AffiliateProduct] = Field(..., description="List of products from this retailer")
    cart_url: str = Field(..., description="Single URL to add all products to cart")
    product_count: int = Field(..., description="Number of products in this cart")


class AffiliateCartResponse(BaseModel):
    """
    Response model for affiliate cart generation.
    """
    carts: List[RetailerCart] = Field(..., description="List of retailer-specific carts")
    total_products: int = Field(..., description="Total number of products processed")
    total_retailers: int = Field(..., description="Number of different retailers")
    status: str = Field(default="success", description="Status of the operation")
    message: str = Field(default="Affiliate carts generated successfully")
