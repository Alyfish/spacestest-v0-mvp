import json
import logging
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import UploadFile
from logger_config import (
    log_api_call,
    log_external_api_call,
    log_project_status_change,
    log_user_action,
)
from models import ImprovementMarker, ProjectContext
from openai_client import OpenAIClient
from serp_client import SerpClient

DATA_FILE = Path("data/projects.json")
IMAGES_DIR = Path("data/images")


class DataManager:
    def __init__(self):
        self.logger = logging.getLogger("spaces_ai")
        self._ensure_data_file_exists()
        self._ensure_images_dir_exists()
        self.openai_client = OpenAIClient()

        # Initialize SERP client for product discovery
        try:
            self.serp_client = SerpClient()
            self.logger.info("Successfully initialized SERP client")
        except Exception as e:
            self.logger.warning(f"Could not initialize SERP client: {e}")
            self.serp_client = None

        # Exa client disabled - it doesn't work, gets CAPTCHA pages
        self.exa_client = None

        # Initialize Gemini client for image generation
        try:
            from gemini_client import GeminiImageClient

            self.gemini_client = GeminiImageClient()
            self.logger.info(
                "Successfully initialized Gemini client for image generation"
            )
        except Exception as e:
            self.logger.warning(f"Could not initialize Gemini client: {e}")
            self.gemini_client = None

    def _ensure_data_file_exists(self):
        """Create the data file if it doesn't exist"""
        DATA_FILE.parent.mkdir(exist_ok=True)
        if not DATA_FILE.exists():
            DATA_FILE.write_text("{}")

    def _ensure_images_dir_exists(self):
        """Create the images directory if it doesn't exist"""
        IMAGES_DIR.mkdir(exist_ok=True)

    def _load_projects(self) -> dict:
        """Load all projects from the JSON file"""
        try:
            return json.loads(DATA_FILE.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_projects(self, projects: dict):
        """Save projects to the JSON file"""
        DATA_FILE.write_text(json.dumps(projects, indent=2))

    def _check_room_emptiness(self, image_path: str) -> bool:
        """
        Check if the uploaded image shows an empty room using AI analysis

        Args:
            image_path: Path to the image file

        Returns:
            bool: True if the room appears empty, False otherwise
        """
        try:
            # Create a simple Pydantic model for the response
            from pydantic import BaseModel

            class RoomEmptinessCheck(BaseModel):
                is_empty: bool
                confidence: float
                reasoning: str

            # Analyze the image using vision API
            result = self.openai_client.analyze_image_with_vision(
                prompt="Analyze this room image and determine if it's empty. Consider furniture, decorations, and general room contents.",
                pydantic_model=RoomEmptinessCheck,
                image_path=image_path,
                system_message="You are an expert at analyzing room images. Determine if a room is empty based on the presence of furniture, decorations, or other items. Be conservative - if there's any significant furniture or decoration, consider it not empty.",
            )

            return result.is_empty

        except Exception as e:
            print(f"Error checking room emptiness: {e}")
            # Default to False (not empty) if analysis fails
            return False

    def _generate_marker_recommendations(
        self,
        space_type: str,
        markers: List[ImprovementMarker],
        labelled_image_path: str,
    ) -> List[str]:
        """
        Generate AI recommendations based on improvement markers

        Args:
            space_type: Type of space (living room, bedroom, etc.)
            markers: List of improvement markers with descriptions
            labelled_image_path: Path to the labelled image with markers

        Returns:
            List of recommendation strings
        """
        try:
            # Create a Pydantic model for the AI response
            from typing import List

            from pydantic import BaseModel

            class AIRecommendationResponse(BaseModel):
                recommendations: List[str]

            # Build the prompt with marker information
            marker_info = "\n".join(
                [
                    f"Marker {i + 1} ({marker.color}): {marker.description}"
                    for i, marker in enumerate(markers)
                ]
            )

            prompt = f"""
            Analyze this {space_type} and provide specific interior design recommendations based on the user's improvement markers.

            Space Type: {space_type}
            
            User's Improvement Requests:
            {marker_info}

            Provide specific, actionable recommendations as bullet points. Each recommendation should:
            - Be specific about what to change and where
            - Reference the marker locations in the image
            - Include practical suggestions for furniture, decor, or layout changes
            - Be written in a clear, actionable format

            Format each recommendation as a simple string that clearly states what to do and where.
            """

            # Analyze the labelled image with markers using vision API
            result = self.openai_client.analyze_image_with_vision(
                prompt=prompt,
                pydantic_model=AIRecommendationResponse,
                image_path=labelled_image_path,
                system_message="You are an expert interior designer. Provide specific, actionable recommendations for improving spaces based on user feedback. Focus on practical changes that can be easily implemented.",
            )

            return result.recommendations

        except Exception as e:
            print(f"Error generating marker recommendations: {e}")
            import traceback

            traceback.print_exc()
            # Return default recommendations if AI analysis fails
            return [
                "Add a statement piece at marker 1 to create a focal point",
                "Improve lighting in the area marked with marker 2",
                "Add texture and visual interest at marker 3",
            ]

    def _create_labelled_image(
        self, base_image_path: str, markers: List[ImprovementMarker]
    ) -> str:
        """
        Create a version of the image with visual markers

        Args:
            base_image_path: Path to the original image
            markers: List of improvement markers to draw

        Returns:
            str: Path to the created labelled image
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Load original image and create a copy
            original_img = Image.open(base_image_path)
            img = original_img.copy()  # Create a copy to avoid modifying the original
            draw = ImageDraw.Draw(img)

            # 5 distinct colors for the 5 markers
            marker_colors = [
                (239, 68, 68),  # Red
                (34, 197, 94),  # Green
                (59, 130, 246),  # Blue
                (168, 85, 247),  # Purple
                (245, 158, 11),  # Orange
            ]

            # Calculate proportional marker size based on image dimensions
            # Base size on the smaller dimension to ensure visibility
            min_dimension = min(img.width, img.height)
            marker_size = max(
                40, min_dimension // 25
            )  # Increased size for better visibility
            font_size = max(16, marker_size // 2)

            # Try to load a font, fall back to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            # Draw markers for each improvement request (max 5)
            for i, marker in enumerate(markers[:5]):
                # Convert relative coordinates to pixel coordinates
                x = int(marker.position.x * img.width)
                y = int(marker.position.y * img.height)

                # Get marker color (cycle through the 5 colors)
                color = marker_colors[i % len(marker_colors)]

                # Draw marker circle
                draw.ellipse(
                    [
                        x - marker_size // 2,
                        y - marker_size // 2,
                        x + marker_size // 2,
                        y + marker_size // 2,
                    ],
                    fill=color,
                    outline=(255, 255, 255),
                    width=max(3, marker_size // 15),
                )

                # Draw marker number
                draw.text(
                    (x, y), str(i + 1), fill=(255, 255, 255), font=font, anchor="mm"
                )

                # Draw description text (truncated for visibility)
                desc = (
                    marker.description[:40] + "..."
                    if len(marker.description) > 40
                    else marker.description
                )
                draw.text(
                    (x, y + marker_size // 2 + 15),
                    desc,
                    fill=color,
                    font=font,
                    anchor="mm",
                )

            # Save marked image with a different filename
            base_path = Path(base_image_path)
            labelled_path = str(
                base_path.parent / f"{base_path.stem}_labelled{base_path.suffix}"
            )
            print(f"Creating labelled image: {labelled_path}")
            img.save(labelled_path)
            print(f"Labelled image saved successfully: {labelled_path}")
            return labelled_path

        except Exception as e:
            print(f"Error creating labelled image: {e}")
            # Return original image path if processing fails
            return base_image_path

    @log_api_call("create_project")
    def create_project(self) -> str:
        """Create a new project and return its ID"""
        projects = self._load_projects()
        project_id = str(uuid.uuid4())

        projects[project_id] = {
            "status": "NEW",
            "created_at": datetime.now().isoformat(),  # Proper ISO timestamp
            "context": ProjectContext().model_dump(),
        }

        self._save_projects(projects)
        self.logger.info(
            "Created new project", extra={"project_id": project_id, "status": "NEW"}
        )
        log_user_action("project_created", project_id=project_id)
        return project_id

    def get_project(self, project_id: str) -> dict | None:
        """Get a project by ID"""
        projects = self._load_projects()
        return projects.get(project_id)

    def get_all_projects(self) -> dict:
        """Get all projects"""
        return self._load_projects()

    def upload_image(
        self, project_id: str, image_file: UploadFile, filename: str
    ) -> str:
        """Upload an image for a project, analyze it, and return the file path"""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        # Create project-specific image directory
        project_images_dir = IMAGES_DIR / project_id
        project_images_dir.mkdir(exist_ok=True)

        # Save the image file
        image_path = project_images_dir / filename
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)

        # Check if the room is empty using AI analysis
        is_empty_room = self._check_room_emptiness(str(image_path))

        # Update project with image path, emptiness check, and status
        current_context = ProjectContext.model_validate(projects[project_id]["context"])
        updated_context = current_context.model_copy(
            update={
                "base_image": str(image_path),
                "is_base_image_empty_room": is_empty_room,
            }
        )

        projects[project_id]["context"] = updated_context.model_dump()
        projects[project_id]["status"] = "BASE_IMAGE_UPLOADED"

        self._save_projects(projects)
        return str(image_path)

    def select_space_type(self, project_id: str, space_type: str) -> str:
        """Select space type for a project and update status"""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        # Update project with space type and status
        current_context = ProjectContext.model_validate(projects[project_id]["context"])
        updated_context = current_context.model_copy(update={"space_type": space_type})

        projects[project_id]["context"] = updated_context.model_dump()
        projects[project_id]["status"] = "SPACE_TYPE_SELECTED"

        self._save_projects(projects)
        return space_type

    def save_improvement_markers(
        self, project_id: str, markers: List[ImprovementMarker]
    ) -> str:
        """Save improvement markers, create labelled image, and generate AI recommendations"""
        try:
            print(f"Starting save_improvement_markers for project {project_id}")
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            # Get the base image path and space type
            base_image_path = projects[project_id]["context"].get("base_image")
            space_type = projects[project_id]["context"].get("space_type")

            if not base_image_path:
                raise ValueError("No base image found for this project")

            if not space_type:
                raise ValueError("No space type selected for this project")

            print(f"Creating labelled image with {len(markers)} markers")
            # Create labelled image with markers
            labelled_image_path = self._create_labelled_image(base_image_path, markers)

            # Add color information to markers and convert to proper format
            color_names = ["red", "green", "blue", "purple", "orange"]
            markers_with_colors = []
            for i, marker in enumerate(markers[:5]):
                # marker.position is already a MarkerPosition object, no need to convert
                marker_with_color = ImprovementMarker(
                    id=marker.id,
                    position=marker.position,  # Use the existing MarkerPosition object
                    description=marker.description,
                    color=color_names[i % len(color_names)],
                )
                markers_with_colors.append(marker_with_color)

            print(
                f"Generating AI recommendations for {len(markers_with_colors)} markers"
            )
            # Generate AI recommendations based on markers
            recommendations = self._generate_marker_recommendations(
                space_type,
                markers_with_colors,
                labelled_image_path,
            )

            print(
                f"Updating project context with {len(recommendations)} recommendations"
            )
            # Update project with markers, labelled image, recommendations, and status
            current_context = ProjectContext.model_validate(
                projects[project_id]["context"]
            )
            updated_context = current_context.model_copy(
                update={
                    "improvement_markers": markers_with_colors,
                    "labelled_base_image": labelled_image_path,
                    "marker_recommendations": recommendations,
                }
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "MARKER_RECOMMENDATIONS_READY"

            print("Saving projects to file")
            self._save_projects(projects)
            print("Successfully completed save_improvement_markers")
            return labelled_image_path

        except Exception as e:
            print(f"ERROR in save_improvement_markers: {e}")
            import traceback

            traceback.print_exc()
            raise

    def upload_inspiration_image(
        self, project_id: str, image_file: UploadFile, filename: str
    ) -> str:
        """Upload an inspiration image for a project"""
        try:
            print(f"Starting inspiration image upload for project {project_id}")
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            # Create project-specific inspiration images directory
            project_images_dir = IMAGES_DIR / project_id / "inspiration"
            project_images_dir.mkdir(parents=True, exist_ok=True)

            # Save the inspiration image file
            image_path = project_images_dir / filename
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)

            # Update project context with inspiration image
            current_context = ProjectContext.model_validate(
                projects[project_id]["context"]
            )
            updated_inspiration_images = current_context.inspiration_images + [
                str(image_path)
            ]

            updated_context = current_context.model_copy(
                update={"inspiration_images": updated_inspiration_images}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "INSPIRATION_IMAGES_UPLOADED"

            print(f"Successfully uploaded inspiration image: {image_path}")
            self._save_projects(projects)
            return str(image_path)

        except Exception as e:
            print(f"ERROR in upload_inspiration_image: {e}")
            import traceback

            traceback.print_exc()
            raise

    def upload_inspiration_images_batch(
        self, project_id: str, image_files: List[UploadFile]
    ) -> List[str]:
        """Upload multiple inspiration images for a project in one batch"""
        try:
            print(f"Starting batch inspiration images upload for project {project_id}")
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            # Create project-specific inspiration images directory
            project_images_dir = IMAGES_DIR / project_id / "inspiration"
            project_images_dir.mkdir(parents=True, exist_ok=True)

            # Save all inspiration image files
            uploaded_paths = []
            for i, image_file in enumerate(image_files):
                # Generate unique filename to avoid conflicts
                file_extension = (
                    Path(image_file.filename).suffix if image_file.filename else ".jpg"
                )
                filename = f"inspiration_{i + 1}_{int(time.time())}{file_extension}"
                image_path = project_images_dir / filename

                with open(image_path, "wb") as buffer:
                    shutil.copyfileobj(image_file.file, buffer)

                uploaded_paths.append(str(image_path))
                print(f"Uploaded inspiration image {i + 1}: {image_path}")

            # Update project context with all inspiration images
            current_context = ProjectContext.model_validate(
                projects[project_id]["context"]
            )
            updated_inspiration_images = (
                current_context.inspiration_images + uploaded_paths
            )

            updated_context = current_context.model_copy(
                update={"inspiration_images": updated_inspiration_images}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "INSPIRATION_IMAGES_UPLOADED"

            print(f"Successfully uploaded {len(uploaded_paths)} inspiration images")
            self._save_projects(projects)
            return uploaded_paths

        except Exception as e:
            print(f"ERROR in upload_inspiration_images_batch: {e}")
            import traceback

            traceback.print_exc()
            raise

    def generate_inspiration_recommendations(self, project_id: str) -> List[str]:
        """Generate AI recommendations based on inspiration images"""
        try:
            print(f"Generating inspiration recommendations for project {project_id}")
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            if not context.inspiration_images:
                raise ValueError("No inspiration images found for this project")

            if not context.space_type:
                raise ValueError("No space type selected for this project")

            # Create a Pydantic model for the AI response
            from typing import List

            from pydantic import BaseModel

            class AIInspirationResponse(BaseModel):
                recommendations: List[str]

            # Build the prompt with inspiration images
            inspiration_info = "\n".join(
                [
                    f"Inspiration Image {i + 1}: {img_path}"
                    for i, img_path in enumerate(context.inspiration_images)
                ]
            )

            prompt = f"""
            Analyze these inspiration images for a {context.space_type} design project and provide specific recommendations.

            Space Type: {context.space_type}
            
            Inspiration Images:
            {inspiration_info}

            Based on these inspiration images, provide specific, actionable design recommendations that:
            - Incorporate the style, colors, and design elements from the inspiration images
            - Are tailored to the {context.space_type} space type
            - Include practical suggestions for furniture, decor, colors, and layout
            - Reference specific elements from the inspiration images
            - Are written in a clear, actionable format

            Format each recommendation as a simple string that clearly states what to do and where.
            """

            # Analyze the inspiration images using vision API
            # For now, we'll analyze the first inspiration image
            # In a full implementation, you might want to analyze all images
            first_inspiration = context.inspiration_images[0]

            result = self.openai_client.analyze_image_with_vision(
                prompt=prompt,
                pydantic_model=AIInspirationResponse,
                image_path=first_inspiration,
                system_message="You are an expert interior designer. Analyze inspiration images and provide specific, actionable design recommendations that incorporate the style and elements from the inspiration while being practical for the target space type.",
            )

            # Update project with inspiration recommendations
            updated_context = context.model_copy(
                update={"inspiration_recommendations": result.recommendations}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "INSPIRATION_RECOMMENDATIONS_READY"

            print(
                f"Generated {len(result.recommendations)} inspiration recommendations"
            )
            self._save_projects(projects)
            return result.recommendations

        except Exception as e:
            print(f"ERROR in generate_inspiration_recommendations: {e}")
            import traceback

            traceback.print_exc()
            raise

    @log_api_call("generate_product_recommendations")
    def generate_product_recommendations(self, project_id: str) -> List[str]:
        """Generate AI product recommendations based on the current project context"""
        try:
            self.logger.info(
                "Starting product recommendations generation",
                extra={"project_id": project_id},
            )
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            if not context.is_ready_for_product_recommendations():
                raise ValueError("Project is not ready for product recommendations")

            # Create a Pydantic model for the AI response
            from typing import List

            from pydantic import BaseModel

            class AIProductRecommendations(BaseModel):
                recommendations: List[str]
                reasoning: str

            # Build comprehensive context for the AI
            context_info = f"""
            Space Type: {context.space_type}
            Room Status: {"Empty room" if context.is_base_image_empty_room else "Furnished room"}
            """

            if context.improvement_markers:
                markers_info = "\n".join(
                    [
                        f"- {marker.description} (at {marker.position.x:.1%}, {marker.position.y:.1%})"
                        for marker in context.improvement_markers
                    ]
                )
                context_info += f"\nImprovement Areas Identified:\n{markers_info}"

            if context.inspiration_recommendations:
                inspiration_info = "\n".join(
                    [f"- {rec}" for rec in context.inspiration_recommendations]
                )
                context_info += f"\n\nStyle Recommendations:\n{inspiration_info}"

            prompt = f"""Based on this interior design project context, generate exactly 2 specific, actionable product recommendations.

{context_info}

Requirements:
- Each recommendation should be a specific action like "change sofa", "add coffee table", "replace dining chairs", "add floor lamp", etc.
- Focus on items that would have the most visual impact for this {context.space_type}
- Consider the improvement areas and style preferences mentioned above
- Make recommendations that are realistic and achievable for most homeowners
- Keep each recommendation to 2-4 words maximum

Return exactly 2 recommendations that are distinct and complementary to each other."""

            # Log AI API call with timing
            start_time = time.time()
            result = self.openai_client.get_structured_completion(
                prompt=prompt,
                pydantic_model=AIProductRecommendations,
                system_message="You are an expert interior designer who specializes in making targeted, high-impact product recommendations for home improvement projects.",
            )
            ai_duration = (time.time() - start_time) * 1000

            log_external_api_call(
                "openai",
                "product_recommendations",
                ai_duration,
                True,
                len(str(result.recommendations)),
            )

            # Update the project context
            old_status = projects[project_id]["status"]
            updated_context = context.model_copy(
                update={"product_recommendations": result.recommendations}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "PRODUCT_RECOMMENDATIONS_READY"

            self.logger.info(
                "Generated product recommendations",
                extra={
                    "project_id": project_id,
                    "recommendations_count": len(result.recommendations),
                    "recommendations": result.recommendations,
                    "status": "PRODUCT_RECOMMENDATIONS_READY",
                },
            )
            log_project_status_change(
                project_id, old_status, "PRODUCT_RECOMMENDATIONS_READY"
            )
            log_user_action(
                "product_recommendations_generated",
                project_id=project_id,
                count=len(result.recommendations),
            )

            self._save_projects(projects)
            return result.recommendations

        except Exception as e:
            self.logger.error(
                f"Failed to generate product recommendations: {str(e)}",
                extra={"project_id": project_id, "error_type": type(e).__name__},
                exc_info=True,
            )
            log_external_api_call("openai", "product_recommendations", 0, False)
            raise

    @log_api_call("select_product_recommendation")
    def select_product_recommendation(
        self, project_id: str, selected_recommendation: str
    ) -> str:
        """Select a product recommendation and update project status"""
        try:
            self.logger.info(
                "Selecting product recommendation",
                extra={
                    "project_id": project_id,
                    "selected_recommendation": selected_recommendation,
                },
            )
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            if not context.product_recommendations:
                raise ValueError(
                    "No product recommendations available for this project"
                )

            if selected_recommendation not in context.product_recommendations:
                raise ValueError(
                    f"'{selected_recommendation}' is not a valid recommendation option"
                )

            # Update the project context
            old_status = projects[project_id]["status"]
            updated_context = context.model_copy(
                update={"selected_product_recommendation": selected_recommendation}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "PRODUCT_RECOMMENDATION_SELECTED"

            self.logger.info(
                "Selected product recommendation successfully",
                extra={
                    "project_id": project_id,
                    "selected_recommendation": selected_recommendation,
                    "status": "PRODUCT_RECOMMENDATION_SELECTED",
                },
            )
            log_project_status_change(
                project_id, old_status, "PRODUCT_RECOMMENDATION_SELECTED"
            )
            log_user_action(
                "product_recommendation_selected",
                project_id=project_id,
                recommendation=selected_recommendation,
            )

            self._save_projects(projects)
            return selected_recommendation

        except Exception as e:
            self.logger.error(
                f"Failed to select product recommendation: {str(e)}",
                extra={
                    "project_id": project_id,
                    "selected_recommendation": selected_recommendation,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    @log_api_call("search_products")
    def search_products(self, project_id: str) -> dict:
        """Search for products based on the selected recommendation using AI and Exa"""
        try:
            self.logger.info(
                "Starting product search", extra={"project_id": project_id}
            )
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            if not context.is_ready_for_product_search():
                raise ValueError("Project is not ready for product search")

            if not self.serp_client:
                raise ValueError(
                    "SERP client not available - please check SERP_API_KEY"
                )

            # Use AI to generate a specific search query
            search_query = self._generate_search_query(context)
            self.logger.info(
                "Generated search query",
                extra={
                    "project_id": project_id,
                    "search_query": search_query,
                    "selected_recommendation": context.selected_product_recommendation,
                },
            )

            # Use SERP API only - Exa doesn't work (gets CAPTCHA pages)
            search_start_time = time.time()

            if self.serp_client:
                self.logger.info("Using SERP Google Shopping for product search")
                products = self.serp_client.search_and_analyze_products(
                    query=search_query,
                    space_type=context.space_type or "general",
                    num_results=12,
                )
                search_duration = (time.time() - search_start_time) * 1000
                log_external_api_call(
                    "serp", "product_search", search_duration, True, len(products)
                )

                # Mark SERP products for frontend identification
                for product in products:
                    product["source_api"] = "serp"
                    product["search_method"] = "Google Shopping"
            else:
                self.logger.error("No SERP client available for product search")
                products = []

            # Filter and enhance results
            filtered_products = [p for p in products if p.get("is_product_page", True)][
                :8
            ]

            # Update the project context with search results
            old_status = projects[project_id]["status"]
            search_result = {
                "search_query": search_query,
                "products": filtered_products,
                "total_found": len(filtered_products),
            }

            updated_context = context.model_copy(
                update={"product_search_results": filtered_products}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "PRODUCT_SEARCH_COMPLETE"

            self.logger.info(
                "Product search completed successfully",
                extra={
                    "project_id": project_id,
                    "search_query": search_query,
                    "total_found": len(filtered_products),
                    "filtered_count": len(filtered_products),
                    "status": "PRODUCT_SEARCH_COMPLETE",
                },
            )
            log_project_status_change(project_id, old_status, "PRODUCT_SEARCH_COMPLETE")
            log_user_action(
                "product_search_completed",
                project_id=project_id,
                query=search_query,
                results_count=len(filtered_products),
            )

            self._save_projects(projects)
            return search_result

        except Exception as e:
            self.logger.error(
                f"Failed to search for products: {str(e)}",
                extra={"project_id": project_id, "error_type": type(e).__name__},
                exc_info=True,
            )
            # Log failed search call
            log_external_api_call("search", "product_search", 0, False)
            raise

    def select_product_for_generation(
        self,
        project_id: str,
        product_url: str,
        product_title: str,
        product_image_url: str,
        generation_prompt: str = None,
    ):
        """Select a product for image generation and save to project context"""
        try:
            print(f"🎯 SELECTING PRODUCT FOR PROJECT: {project_id}")
            print(f"   Product URL: {product_url}")
            print(f"   Product Title: {product_title}")
            print(f"   Image URL: {product_image_url}")
            print(f"   Custom Prompt: {generation_prompt}")

            log_user_action(
                "product_selected",
                {
                    "project_id": project_id,
                    "product_url": product_url,
                    "product_title": product_title[:50],
                },
            )

            print("📂 Loading project context...")
            # Load project
            project = self.get_project(project_id)
            if not project:
                print(f"❌ Project {project_id} not found!")
                raise ValueError(f"Project {project_id} not found")

            # Get context from project
            context = ProjectContext.model_validate(project["context"])
            print("✅ Project context loaded successfully")
            print(f"   Current status: {project['status']}")

            print("🔍 Checking if ready for product selection...")
            if not context.is_ready_for_product_selection():
                print("❌ Project not ready for product selection!")
                print(
                    f"   Ready for product search: {context.is_ready_for_product_search()}"
                )
                print(
                    f"   Product search results count: {len(context.product_search_results)}"
                )
                raise ValueError("Project is not ready for product selection")

            print("💾 Creating selected product data...")
            # Save selected product
            selected_product = {
                "url": product_url,
                "title": product_title,
                "image_url": product_image_url,
                "selected_at": datetime.now().isoformat(),
            }

            print("📝 Updating context with selected product...")
            context.selected_product = selected_product
            context.generation_prompt = generation_prompt

            print("💾 Saving project context...")
            # Save context
            projects = self._load_projects()
            projects[project_id]["context"] = context.model_dump()
            projects[project_id]["status"] = "PRODUCT_SELECTED"
            self._save_projects(projects)

            print("📊 Logging project status change...")
            log_project_status_change(
                project_id, "PRODUCT_SEARCH_COMPLETE", "PRODUCT_SELECTED"
            )

            print("✅ Product selection completed successfully!")
            return {
                "project_id": project_id,
                "selected_product": selected_product,
                "status": "success",
                "message": f"Product selected: {product_title[:50]}...",
            }

        except Exception as e:
            self.logger.error(f"Failed to select product for generation: {e}")
            raise

    def generate_product_visualization(self, project_id: str):
        """Generate a new image visualization using Gemini with the selected product"""
        try:
            log_user_action("image_generation_started", {"project_id": project_id})

            # Load project context
            project = self.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(project["context"])
            if not context.is_ready_for_image_generation():
                raise ValueError("Project is not ready for image generation")

            if not self.gemini_client:
                raise ValueError("Gemini client is not available")

            # Extract product details
            selected_product = context.selected_product
            product_image_url = selected_product["image_url"]
            product_title = selected_product["title"]
            space_type = context.space_type or "living space"
            custom_prompt = context.generation_prompt

            # Get the original room image path
            original_room_image_path = None
            if context.base_image:
                print(f"🖼️ Base image from context: {context.base_image}")

                # Handle path construction correctly
                if context.base_image.startswith("data/"):
                    # Strip the "data/" prefix since DATA_FILE.parent is already "data"
                    relative_path = context.base_image[5:]  # Remove "data/" prefix
                    original_room_image_path = DATA_FILE.parent / relative_path
                    print(
                        f"📂 Stripped 'data/' prefix, using: {original_room_image_path}"
                    )
                elif "/" in context.base_image:
                    # It's a relative path without "data/" prefix
                    original_room_image_path = DATA_FILE.parent / context.base_image
                    print(f"📂 Using relative path: {original_room_image_path}")
                else:
                    # It's just a filename, construct the full path
                    project_images_dir = DATA_FILE.parent / "images" / project_id
                    original_room_image_path = project_images_dir / context.base_image
                    print(
                        f"📂 Constructed path from filename: {original_room_image_path}"
                    )

                # Verify the file exists
                if not original_room_image_path.exists():
                    print(f"❌ File not found at: {original_room_image_path}")
                    raise ValueError(
                        f"Original room image not found: {original_room_image_path}"
                    )
                else:
                    print(
                        f"✅ Found original room image at: {original_room_image_path}"
                    )

            if not original_room_image_path:
                raise ValueError("No original room image available for integration")

            # Create project-specific directory for the generated image
            project_dir = DATA_FILE.parent / "images" / project_id

            # Generate the visualization with full context
            generated_image_base64, final_prompt = (
                self.gemini_client.generate_product_visualization(
                    original_room_image_path=str(original_room_image_path),
                    product_image_url=product_image_url,
                    space_type=space_type,
                    product_title=product_title,
                    inspiration_recommendations=context.inspiration_recommendations
                    or [],
                    marker_locations=context.improvement_markers or [],
                    custom_prompt=custom_prompt,
                    project_data_dir=project_dir,
                )
            )

            # Update context with generated image base64
            context.generated_image_base64 = generated_image_base64
            context.generation_prompt = final_prompt

            # Save context
            projects = self._load_projects()
            projects[project_id]["context"] = context.model_dump()
            projects[project_id]["status"] = "IMAGE_GENERATED"
            self._save_projects(projects)

            log_project_status_change(project_id, "PRODUCT_SELECTED", "IMAGE_GENERATED")
            log_user_action(
                "image_generation_completed",
                {
                    "project_id": project_id,
                    "generated_image_size": f"{len(generated_image_base64)} chars",
                },
            )

            return {
                "project_id": project_id,
                "selected_product": selected_product,
                "generated_image_base64": generated_image_base64,
                "generation_prompt": final_prompt,
                "status": "success",
                "message": "Image generated successfully using Gemini",
            }

        except Exception as e:
            self.logger.error(f"Failed to generate product visualization: {e}")
            # Log failed Gemini call
            log_external_api_call("gemini", "image_generation", 0, False)
            raise

    def _generate_search_query(self, context: ProjectContext) -> str:
        """Generate an optimized search query based on the project context and selected recommendation"""
        try:
            from pydantic import BaseModel

            class SearchQuery(BaseModel):
                query: str
                reasoning: str

            # Build context for AI
            context_info = f"""
            Space Type: {context.space_type}
            Selected Recommendation: {context.selected_product_recommendation}
            """

            if context.improvement_markers:
                markers_summary = ", ".join(
                    [marker.description for marker in context.improvement_markers]
                )
                context_info += f"\nImprovement Areas: {markers_summary}"

            if context.inspiration_recommendations:
                style_summary = ", ".join(context.inspiration_recommendations[:2])
                context_info += f"\nStyle Preferences: {style_summary}"

            prompt = f"""Generate a specific, optimized search query to find products for this recommendation.

{context_info}

Create a search query that:
- Is specific enough to find the right type of product
- Includes relevant style/material hints from the context
- Is optimized for e-commerce sites like Wayfair, West Elm, etc.
- Is 3-8 words maximum
- Focuses on the most important product characteristics

For example:
- If recommendation is "change sofa" and style is modern → "modern sectional sofa gray"
- If recommendation is "add coffee table" and space is small → "round coffee table wood small"
- If recommendation is "replace dining chairs" → "dining chairs set upholstered"

Generate the most effective search query for this scenario:"""

            result = self.openai_client.get_structured_completion(
                prompt=prompt,
                pydantic_model=SearchQuery,
                system_message="You are an expert at generating optimized product search queries for furniture and home decor e-commerce sites.",
            )

            return result.query

        except Exception as e:
            print(f"Error generating search query: {e}")
            # Fallback to simple query
            return f"{context.selected_product_recommendation} {context.space_type}"


# Global instance
data_manager = DataManager()
