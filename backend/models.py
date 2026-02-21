from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


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


class ColorAssignment(BaseModel):
    """
    Model for assigning a color to a specific element in the room
    """
    model_config = ConfigDict(extra="forbid")

    element: str = Field(..., description="Element name (e.g., 'Walls', 'Sofa', 'Curtains')")
    color_hex: str = Field(..., description="HEX color code to apply")
    color_name: str = Field(..., description="Human-readable color name")
    finish: Optional[str] = Field(None, description="Finish type (e.g., 'matte', 'satin', 'glossy')")
    notes: Optional[str] = Field(None, description="Additional application notes")


class ColorSwatch(BaseModel):
    """Structured color swatch definition for schema-safe responses."""
    model_config = ConfigDict(extra="forbid")

    hex: str = Field(..., description="HEX color code")
    description: Optional[str] = Field(None, description="Short description of the color usage")


class ColorAnalysis(BaseModel):
    """
    Model for the Color Agent's structured analysis output.
    Provides comprehensive color application guidance following design principles.
    """
    model_config = ConfigDict(extra="forbid")

    # Summary
    space_summary: str = Field(..., description="Brief summary of the space, style, and desired mood")
    
    # Color selections with 60-30-10 rule
    primary_colors: List[ColorSwatch] = Field(
        ..., 
        description="Primary colors (60%) with hex codes and descriptions"
    )
    secondary_colors: List[ColorSwatch] = Field(
        ..., 
        description="Secondary colors (30%) with hex codes and descriptions"
    )
    accent_colors: List[ColorSwatch] = Field(
        ..., 
        description="Accent colors (10%) with hex codes and descriptions"
    )
    
    # Color theory approach
    color_theory_approach: str = Field(
        ..., 
        description="Color theory used: Monochromatic, Analogous, Complementary, or Triadic"
    )
    color_theory_rationale: str = Field(
        ..., 
        description="Explanation of why this approach supports the desired style and mood"
    )
    
    # Element assignments
    color_assignments: List[ColorAssignment] = Field(
        ..., 
        description="Specific color assignments for each room element"
    )
    
    # Light and texture
    lighting_notes: str = Field(
        ..., 
        description="How colors will look in daylight vs evening, and texture considerations"
    )
    
    # Cohesion and personalization
    cohesion_tips: str = Field(
        ..., 
        description="Tips for maintaining flow with adjacent rooms"
    )
    personalization_suggestions: str = Field(
        ..., 
        description="Seasonal accent swaps and personalization ideas"
    )
    
    # Agent decision notes
    palette_adaptations: Optional[str] = Field(
        None,
        description="Notes on any adaptations made to the selected palette for better fit"
    )


class ApplyColorRequest(BaseModel):
    """
    Request model for applying a color scheme to a project with AI analysis
    """
    palette_name: str = Field(..., description="Name of the selected palette")
    colors: List[str] = Field(..., description="List of HEX color codes in the palette")
    let_ai_decide: bool = Field(
        default=False, 
        description="If true, AI will choose optimal colors regardless of palette selection"
    )


class ApplyColorResponse(BaseModel):
    """
    Response model for color scheme application
    """
    project_id: str
    palette_name: str
    color_analysis: ColorAnalysis
    status: str
    message: str = "Color analysis generated successfully"


class SkipStepResponse(BaseModel):
    """
    Response model for skipping an optional analysis step
    """
    project_id: str
    status: str
    skipped_step: str
    message: str


# ==================== Style Agent Models ====================

class FurnitureRecommendation(BaseModel):
    """
    Model for a furniture or decor recommendation in the style analysis
    """
    item_type: str = Field(..., description="Type of furniture/decor (e.g., 'Sofa', 'Coffee Table', 'Rug')")
    description: str = Field(..., description="Specific style description for this item")
    materials: List[str] = Field(default_factory=list, description="Recommended materials")
    colors: List[str] = Field(default_factory=list, description="Recommended colors for this item")
    placement_notes: Optional[str] = Field(None, description="Where and how to position this item")


class StyleAnalysis(BaseModel):
    """
    Model for the Style Agent's structured analysis output.
    Provides comprehensive style application guidance following interior design principles.
    """
    # 1. Overview
    style_name: str = Field(..., description="Name of the selected interior design style")
    style_overview: str = Field(..., description="Brief description of the style, its roots, mood and atmosphere")
    
    # 2. Defining Characteristics
    materials: List[str] = Field(..., description="Key materials for this style")
    color_palette: List[str] = Field(..., description="Characteristic colors with hex codes")
    furniture_characteristics: str = Field(..., description="Furniture style and key pieces")
    patterns_textures: str = Field(..., description="Patterns and textures used")
    lighting_style: str = Field(..., description="Lighting fixtures and approach")
    decor_accessories: str = Field(..., description="Decor items and accessories")
    
    # 3. Layout & Spatial Principles
    layout_principles: str = Field(..., description="Flow, zoning, symmetry, and balance of space")
    
    # 4. Signature Styling Tips
    styling_tips: List[str] = Field(..., description="Practical advice and pro designer insights")
    common_mistakes: List[str] = Field(..., description="Common mistakes to avoid")
    
    # 5. Furniture Recommendations (specific to user's space)
    furniture_recommendations: List[FurnitureRecommendation] = Field(
        ..., 
        description="Specific furniture and decor recommendations for the user's space"
    )
    anchor_pieces: List[str] = Field(
        ..., 
        description="1-2 key anchor furniture items that define the style"
    )
    statement_accessory: str = Field(..., description="A statement accessory to complete the look")
    
    # 6. Application Scenario
    room_transformation: str = Field(
        ..., 
        description="Detailed description of how to transform the specific room in the image"
    )
    
    # 7. Related Styles
    related_styles: List[str] = Field(
        ..., 
        description="Related or hybrid styles and what distinguishes them"
    )
    
    # Agent notes
    style_adaptations: Optional[str] = Field(
        None,
        description="Notes on adaptations made to fit the user's specific space"
    )


class ApplyStyleRequest(BaseModel):
    """
    Request model for applying a design style to a project with AI analysis
    """
    style_name: str = Field(..., description="Name of the selected design style")
    let_ai_decide: bool = Field(
        default=False, 
        description="If true, AI will choose the optimal style for the space"
    )


class ApplyStyleResponse(BaseModel):
    """
    Response model for style application
    """
    project_id: str
    style_name: str
    style_analysis: StyleAnalysis
    status: str
    message: str = "Style analysis generated successfully"


# ==================== Preferred Stores Models ====================

class PreferredStoresRequest(BaseModel):
    """
    Request model for updating preferred stores
    """
    stores: List[str] = Field(..., description="List of preferred store names")


class PreferredStoresResponse(BaseModel):
    """
    Response model for preferred stores update
    """
    project_id: str
    stores: List[str]
    status: str
    message: str = "Preferred stores updated successfully"


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


class ProjectListItem(BaseModel):
    """Lightweight project summary for the saved spaces list view."""

    id: str
    status: str
    created_at: str
    space_type: Optional[str] = None
    improvement_mode: Optional[str] = None
    base_image: Optional[str] = None
    generated_image: Optional[str] = None
    inspiration_generated_image: Optional[str] = None


class ProjectSummariesResponse(BaseModel):
    """Response for the fast project summaries endpoint."""

    projects: List[ProjectListItem]
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


class ImprovementModeRequest(BaseModel):
    """
    Request model for setting the improvement mode of a project.

    Attributes:
        mode (str): 'iterative' or 'complete_revamp'
    """
    mode: str = Field(
        ...,
        description="'iterative' for enhancing existing setup, 'complete_revamp' for full redesign"
    )


class ImprovementModeResponse(BaseModel):
    """
    Response model for improvement mode selection.

    Attributes:
        project_id (str): ID of the project
        mode (str): The selected improvement mode
        status (str): Status of the operation
        message (str): Human-readable message
    """
    project_id: str
    mode: str
    status: str
    message: str = "Improvement mode set successfully"


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
        ..., description="Color identifier - named (red, green, blue, purple, orange) or hex code (#FF0000)"
    )


class PreSearchedProduct(BaseModel):
    """Individual product from pre-search for recommendations."""
    url: str
    title: str
    image_url: str
    store: str
    price_str: Optional[str] = None
    price: Optional[float] = None
    similarity_score: Optional[float] = None


class PreSearchedCategory(BaseModel):
    """Products found for a single recommendation category."""
    recommendation: str = Field(..., description="The recommendation this search is for, e.g. 'Add Velvet Bed'")
    search_query: str = Field(..., description="Generated search query used")
    status: str = Field(default="pending", description="pending | complete | error")
    products: List[PreSearchedProduct] = Field(default_factory=list)
    searched_at: Optional[str] = None
    error_message: Optional[str] = None


class FavoriteProduct(BaseModel):
    """User's selected product from the 'Like These?' suggestions."""
    category: str = Field(..., description="Which recommendation this product is for")
    url: str
    title: str
    image_url: str
    store: str
    price_str: Optional[str] = None


class SelectedTrendingProduct(BaseModel):
    """User's selected product from trending products for image generation."""
    category: str = Field(..., description="Which recommendation category this product is for")
    url: str
    title: str
    image_url: str
    store: str
    price_str: Optional[str] = None


class ProjectContext(BaseModel):
    """
    Project context that evolves through the design workflow.

    Contains the essential data needed for each step of the design process.
    """

    # Core data
    base_image: Optional[str] = None
    is_base_image_empty_room: Optional[bool] = None
    improvement_mode: Optional[str] = Field(
        default=None,
        description="'iterative' for enhancing existing setup, 'complete_revamp' for full redesign, 'inspiration' for style-match from reference image"
    )
    space_type: Optional[str] = None
    improvement_markers: List[ImprovementMarker] = Field(default_factory=list)
    labelled_base_image: Optional[str] = None
    marker_recommendations: List[str] = Field(default_factory=list)

    # Inspiration images
    inspiration_images: List[str] = Field(
        default_factory=list, description="Paths to uploaded inspiration images"
    )
    inspiration_images_skipped: bool = Field(
        default=False, description="Whether the user skipped inspiration images"
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
    selected_product_recommendations: List[str] = Field(
        default_factory=list, description="The product recommendations selected by the user"
    )
    product_search_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Exa search results for products matching the selected recommendations",
    )
    selected_products: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="The specific products selected by the user for image generation",
    )
    generated_image_base64: Optional[str] = Field(
        default=None, description="Base64 encoded Gemini-generated image"
    )
    generation_prompt: Optional[str] = Field(
        default=None, description="The prompt used for Gemini image generation"
    )
    generation_model_used: Optional[str] = Field(
        default=None, description="The Gemini model used for image generation"
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
    inspiration_model_used: Optional[str] = Field(
        default=None, description="The Gemini model used for inspiration redesign"
    )
    
    # Color Agent analysis
    color_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="Color Agent's structured analysis with color assignments and recommendations"
    )
    color_analysis_skipped: bool = Field(
        default=False, description="Whether the user skipped color analysis"
    )
    
    # Style Agent analysis
    style_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="Style Agent's structured analysis with furniture and decor recommendations"
    )
    style_analysis_skipped: bool = Field(
        default=False, description="Whether the user skipped style analysis"
    )

    # User preferences
    preferred_stores: List[str] = Field(
        default_factory=list, description="List of user's preferred retail stores"
    )

    # Pre-searched product suggestions (for "Like These?" feature)
    pre_searched_categories: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-searched products by recommendation category. Key is recommendation string."
    )

    # User's favorite products from "Like These?" screen
    favorite_products: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Products favorited by user from the 'Like These?' suggestion screen"
    )

    # User's selected trending products for image generation
    selected_trending_products: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Trending products selected by user for inclusion in image generation"
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
            and (
                len(self.inspiration_recommendations) > 0
                or self.inspiration_images_skipped
            )
        )

    def is_ready_for_product_search(self) -> bool:
        """Check if ready for product search."""
        return (
            self.is_ready_for_product_recommendations()
            and len(self.product_recommendations) > 0
            and len(self.selected_product_recommendations) > 0
        )

    def is_ready_for_product_selection(self) -> bool:
        """Check if ready for product selection."""
        return (
            self.is_ready_for_product_search() and len(self.product_search_results) > 0
        )

    def is_ready_for_image_generation(self) -> bool:
        """Check if ready for Gemini image generation."""
        return (
            self.is_ready_for_product_selection() and len(self.selected_products) > 0
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
    search_job_id: Optional[str] = None


class ProductRecommendationSelectionRequest(BaseModel):
    """
    Request model for selecting a product recommendation.

    Attributes:
        selected_recommendation (str): The product recommendation to toggle
    """

    selected_recommendation: str


class ProductRecommendationSelectionResponse(BaseModel):
    """
    Response model for product recommendation selection.

    Attributes:
        project_id (str): ID of the project
        selected_recommendations (List[str]): The current list of selected recommendations
        status (str): Status of the selection operation
        message (str): Human-readable message describing the operation result
    """

    project_id: str
    selected_recommendations: List[str]
    status: str
    message: str = "Product recommendation selected successfully"


class SetSelectedRecommendationsRequest(BaseModel):
    """Request model for atomically setting all selected product recommendations."""
    recommendations: List[str]


class SetSelectedRecommendationsResponse(BaseModel):
    """Response model for setting selected product recommendations."""
    project_id: str
    selected_recommendations: List[str]
    status: str
    message: str = "Selected recommendations updated successfully"


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
    selected_recommendations: List[str]
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
    selected_products: List[Dict[str, Any]]
    status: str
    message: str


class AutoSelectProductResponse(BaseModel):
    """
    Response model for AI auto-selection of best product.

    Attributes:
        project_id (str): ID of the project
        selected_product (Dict[str, Any]): The auto-selected product details
        selection_reason (str): Why this product was selected
        alternatives (List[Dict[str, Any]]): Other products as alternatives
        status (str): Status of the operation
        message (str): Human-readable message
    """

    project_id: str
    selected_product: Dict[str, Any]
    selection_reason: str
    alternatives: List[Dict[str, Any]]
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
    selected_products: List[Dict[str, Any]]
    generated_image_base64: str  # Return base64 string instead of URL
    generation_prompt: str
    status: str
    message: str = "Image generation completed successfully"
    model_used: Optional[str] = None  # The Gemini model used for generation


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
        model_used (str): The Gemini model used for generation
    """

    project_id: str
    generated_image_base64: str
    inspiration_prompt: str
    inspiration_recommendations: List[str]
    status: str
    message: str = "Inspiration-based image redesign completed successfully"
    model_used: Optional[str] = None  # The Gemini model used for generation


class RetryRedesignRequest(BaseModel):
    """
    Request model for retry redesign with user feedback.

    Used when a user wants to edit the existing generated image
    by providing specific modification instructions.
    """
    feedback: str = Field(..., description="User's modification request (e.g., 'remove the lamp', 'add a plant')")
    attempt_id: str = Field(..., description="Client-generated UUID for idempotent retry debit tracking")


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
    model_config = ConfigDict(extra="ignore")  # Accept unknown fields like item_type from older clients

    id: str = Field(default_factory=lambda: f"sel_{int(__import__('time').time() * 1000)}")
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
        description="Type of image: 'product', 'inspiration', or 'active'"
    )
    mode: Literal["full", "fast_prefetch", "click"] = Field(
        default="full",
        description="Analysis mode. 'click' is accepted as a legacy alias for full analysis.",
    )


class FurnitureAnalysisItem(BaseModel):
    """
    Analysis result for a single furniture item.
    When is_bed=True, bed_components contains separate product searches
    for bed_frame, bedding, throw, and pillows.
    """
    id: str
    furniture_type: str
    confidence: float
    style: str
    material: str
    color: str
    search_query: str
    products: List[Dict[str, Any]]
    is_bed: bool = False
    bed_components: Optional[Dict[str, List[Dict[str, Any]]]] = None


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
        description="Type of image: 'product', 'inspiration', or 'active'",
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
    agent_notes: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata about scoring/filtering (e.g., thresholds, counts)",
    )


# ============================================================================
# Affiliate Cart Models
# ============================================================================


class AffiliateProductItem(BaseModel):
    """
    Model for a product item with retailer context for affiliate resolution.

    This is the KEY to retailer-preserving resolution:
    - shopping_url: The Google Shopping or product URL
    - retailer_hint: The expected retailer from "source" field (e.g., "Quince")
    - expected_domain: Optional explicit domain (e.g., "quince.com")
    - title: Product title for keyword matching
    """
    shopping_url: str = Field(..., description="Google Shopping or product URL")
    retailer_hint: Optional[str] = Field(
        None,
        description="Expected retailer name from 'source' field (e.g., 'Quince', 'West Elm')"
    )
    expected_domain: Optional[str] = Field(
        None,
        description="Expected retailer domain (e.g., 'quince.com')"
    )
    title: Optional[str] = Field(None, description="Product title for keyword matching")
    image_url: Optional[str] = Field(None, description="Product image URL")
    price: Optional[float] = Field(None, description="Product price")
    price_str: Optional[str] = Field(None, description="Price string (e.g., '$169.00')")


class AffiliateCartRequest(BaseModel):
    """
    Request model for generating affiliate cart from product URLs.

    IMPORTANT: Use 'items' with retailer hints for retailer-preserving resolution.
    The old 'product_urls' field is still supported for backward compatibility,
    but will use non-strict resolution (may return marketplace alternatives).
    """
    # New API: structured items with retailer context
    items: Optional[List[AffiliateProductItem]] = Field(
        None,
        description="List of product items with retailer hints (RECOMMENDED)"
    )

    # Legacy API: simple URL list (backward compatible, non-strict)
    product_urls: Optional[List[str]] = Field(
        None,
        description="[DEPRECATED] List of product URLs - use 'items' instead for retailer-preserving resolution"
    )

    # Resolution settings
    strict_mode: bool = Field(
        default=True,
        description="If True, fail instead of returning wrong retailer. Set False to allow marketplace fallbacks."
    )


class AffiliateProduct(BaseModel):
    """
    Model for a single product with affiliate link.
    """
    original_url: str = Field(..., description="Original product URL (input)")
    resolved_url: Optional[str] = Field(None, description="Resolved retailer PDP URL")
    affiliate_url: str = Field(..., description="Affiliate version of the URL")
    product_id: str = Field(..., description="Extracted product ID")
    product_name: Optional[str] = Field(None, description="Product name if available")
    # Resolution metadata
    expected_retailer: Optional[str] = Field(None, description="Expected retailer from input hint")
    actual_retailer: Optional[str] = Field(None, description="Actual retailer from resolved URL")
    retailer_matched: Optional[bool] = Field(None, description="Whether resolved retailer matches expected")
    resolution_source: Optional[str] = Field(None, description="How the URL was resolved (direct_link, google_product_api, fallback)")


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
    # Validation metadata
    urls_processed: int = Field(default=0, description="Total URLs received")
    urls_resolved: int = Field(default=0, description="URLs successfully resolved from Google Shopping")
    urls_validated: int = Field(default=0, description="URLs that passed validation (200 status)")
    urls_failed: int = Field(default=0, description="URLs that failed validation")


# ============================================================================
# "Like These?" Product Suggestions Feature
# ============================================================================

class SearchRecommendationsRequest(BaseModel):
    """
    Request model for searching products for selected recommendations.
    """
    recommendations: List[str] = Field(
        ...,
        description="List of selected recommendations to search products for",
        min_length=1
    )


class SearchRecommendationsResponse(BaseModel):
    """
    Response model for product search by recommendations.
    """
    project_id: str
    categories: List[PreSearchedCategory] = Field(
        ...,
        description="Products found for each recommendation category"
    )
    total_products: int = Field(..., description="Total products found across all categories")
    status: str = Field(default="success")
    message: str = Field(default="Products searched successfully")


class ProductSuggestionsResponse(BaseModel):
    """
    Response model for getting pre-searched product suggestions.
    """
    project_id: str
    categories: List[PreSearchedCategory] = Field(
        default_factory=list,
        description="Pre-searched products organized by recommendation"
    )
    total_products: int = Field(default=0)
    overall_status: str = Field(
        default="pending",
        description="all_complete | some_pending | all_error | empty"
    )
    message: str


class FavoriteProductsRequest(BaseModel):
    """
    Request model for saving user's favorite products.
    """
    favorites: List[FavoriteProduct] = Field(
        ...,
        description="List of products favorited by the user"
    )


class FavoriteProductsResponse(BaseModel):
    """
    Response model after saving favorite products.
    """
    project_id: str
    favorites_count: int = Field(..., description="Total number of favorites saved")
    favorites_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of favorites per category"
    )
    status: str = Field(default="success")
    message: str = Field(default="Favorite products saved successfully")


class SelectedTrendingProductsRequest(BaseModel):
    """
    Request model for saving user's selected trending products for image generation.
    """
    products: List[SelectedTrendingProduct] = Field(
        ...,
        description="List of trending products selected by the user for image generation"
    )


class SelectedTrendingProductsResponse(BaseModel):
    """
    Response model after saving selected trending products.
    """
    project_id: str
    products_count: int = Field(..., description="Total number of products saved")
    products_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of products per category"
    )
    status: str = Field(default="success")
    message: str = Field(default="Selected trending products saved successfully")


# ============================================================================
# Flutter API Response Models
# ============================================================================

class ColorAnalysisResponse(BaseModel):
    """Response model for GET /projects/{id}/color-analysis endpoint."""
    project_id: str
    color_analysis: Optional[ColorAnalysis] = Field(
        default=None,
        description="Color analysis results with palettes and assignments"
    )
    skipped: bool = Field(default=False, description="Whether color analysis was skipped")
    status: str = Field(default="success")
    message: str = Field(default="Color analysis retrieved successfully")


class StyleAnalysisResponse(BaseModel):
    """Response model for GET /projects/{id}/style-analysis endpoint."""
    project_id: str
    style_analysis: Optional[StyleAnalysis] = Field(
        default=None,
        description="Style analysis results with materials and furniture recommendations"
    )
    skipped: bool = Field(default=False, description="Whether style analysis was skipped")
    status: str = Field(default="success")
    message: str = Field(default="Style analysis retrieved successfully")


class TrendingProductsResponse(BaseModel):
    """Response model for GET /projects/{id}/trending-products endpoint."""
    project_id: str
    categories: List[PreSearchedCategory] = Field(
        default_factory=list,
        description="Pre-searched product categories"
    )
    selected_products: List[SelectedTrendingProduct] = Field(
        default_factory=list,
        description="Products selected by the user for image generation"
    )
    favorite_products: List[FavoriteProduct] = Field(
        default_factory=list,
        description="User's favorite products"
    )
    status: str = Field(default="success")
    message: str = Field(default="Trending products retrieved successfully")


# ============================================================================
# Process Furniture Selection Models (Google Shopping URL Resolution + Affiliate Cart)
# ============================================================================

class SelectedFurnitureProduct(BaseModel):
    """A product selected by the user from furniture analysis."""
    url: str = Field(..., description="Product URL (may be Google Shopping redirect)")
    title: str = Field(..., description="Product title")
    image_url: Optional[str] = Field(default=None, description="Product image URL")
    store: Optional[str] = Field(default=None, description="Store/retailer name")
    price_str: Optional[str] = Field(default=None, description="Price as string")
    price: Optional[float] = Field(default=None, description="Price as number")
    furniture_id: Optional[str] = Field(default=None, description="ID of the furniture item this product belongs to")


class ResolvedProduct(BaseModel):
    """Product with resolved retailer URL."""
    original_url: str = Field(..., description="Original URL (possibly Google Shopping)")
    resolved_url: str = Field(..., description="Resolved direct retailer URL")
    title: str = Field(..., description="Product title")
    image_url: Optional[str] = Field(default=None, description="Product image URL")
    store: Optional[str] = Field(default=None, description="Store/retailer name")
    price_str: Optional[str] = Field(default=None, description="Price as string")
    was_google_shopping: bool = Field(default=False, description="Whether original URL was a Google Shopping redirect")
    affiliate_url: Optional[str] = Field(default=None, description="Affiliate-tagged URL")
    product_id: Optional[str] = Field(default=None, description="Extracted product ID (ASIN, SKU, etc.)")


class ProcessFurnitureSelectionRequest(BaseModel):
    """Request to process selected furniture products."""
    selected_products: List[SelectedFurnitureProduct] = Field(
        ..., description="Products selected from furniture analysis"
    )


class ProcessFurnitureSelectionResponse(BaseModel):
    """Response from processing furniture selection."""
    project_id: str
    resolved_products: List[ResolvedProduct] = Field(
        default_factory=list,
        description="Products with resolved retailer URLs"
    )
    retailer_carts: List[RetailerCart] = Field(
        default_factory=list,
        description="Products grouped by retailer with cart URLs"
    )
    total_products: int = Field(..., description="Total number of products processed")
    resolved_count: int = Field(..., description="Number of URLs successfully resolved")
    unresolved_count: int = Field(..., description="Number of URLs that could not be resolved")
    status: str = Field(default="success")
    message: str = Field(default="Products processed successfully")


# ============================================================================
# Universal Product Link Normalizer Models
# ============================================================================

class NormalizeURLsRequest(BaseModel):
    """Request model for URL normalization endpoint."""
    urls: List[str] = Field(
        ...,
        description="List of URLs to normalize",
        min_length=1,
        max_length=100,
    )

    # Configuration
    region: str = Field(default="us", description="Target region for shopping results")
    language: str = Field(default="en", description="Target language")
    prefer_domains: List[str] = Field(
        default_factory=list,
        description="Preferred retailer domains (sorted first in groups)",
    )
    block_domains: List[str] = Field(
        default_factory=list,
        description="Domains to exclude from results",
    )
    timeout_ms: int = Field(
        default=10000,
        ge=1000,
        le=30000,
        description="Per-URL timeout in milliseconds",
    )

    # Modes
    google_shopping_mode: str = Field(
        default="serpapi",
        description="How to handle Google Shopping URLs: 'serpapi' or 'disabled'",
    )
    include_classification: bool = Field(
        default=True,
        description="Whether to run product page classification",
    )

    # Advanced options
    max_candidates_per_url: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Max Google Shopping candidates to try",
    )
    max_concurrent: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum total concurrent requests",
    )
    max_per_domain: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent requests per domain",
    )


class NotifyWhenReadyRequest(BaseModel):
    """Request model for subscribing to a per-job push notification."""

    device_token: str = Field(..., min_length=16, description="FCM device token")
    platform: Literal["ios", "android"] = Field(
        ...,
        description="Client platform for push delivery",
    )


class NotifyWhenReadyResponse(BaseModel):
    """Response model for notify-when-ready subscription."""

    project_id: str
    job_id: str
    status: Literal["registered", "already_done"]
    message: str


# Note: NormalizeURLsResponse and related models (URLResolution, RetailerGroup,
# NormalizationTelemetry) are defined in url_normalizer/models.py to avoid
# circular imports. Import them directly when needed:
# from url_normalizer.models import URLResolution, RetailerGroup, NormalizationTelemetry
