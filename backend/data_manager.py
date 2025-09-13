import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import UploadFile
from models import ImprovementMarker, ProjectContext
from openai_client import OpenAIClient

DATA_FILE = Path("data/projects.json")
IMAGES_DIR = Path("data/images")


class DataManager:
    def __init__(self):
        self._ensure_data_file_exists()
        self._ensure_images_dir_exists()
        self.openai_client = OpenAIClient()

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


# Global instance
data_manager = DataManager()
