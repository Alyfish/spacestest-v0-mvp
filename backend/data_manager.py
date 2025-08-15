import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import UploadFile
from models import ImprovementMarker
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
                x = int(marker.position["x"] * img.width)
                y = int(marker.position["y"] * img.height)

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
            "context": {},
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
        projects[project_id]["context"]["base_image"] = str(image_path)
        projects[project_id]["context"]["is_base_image_empty_room"] = is_empty_room
        projects[project_id]["status"] = "BASE_IMAGE_UPLOADED"

        self._save_projects(projects)
        return str(image_path)

    def select_space_type(self, project_id: str, space_type: str) -> str:
        """Select space type for a project and update status"""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        # Update project with space type and status
        projects[project_id]["context"]["space_type"] = space_type
        projects[project_id]["status"] = "SPACE_TYPE_SELECTED"

        self._save_projects(projects)
        return space_type

    def save_improvement_markers(
        self, project_id: str, markers: List[ImprovementMarker]
    ) -> str:
        """Save improvement markers and create labelled image"""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        # Get the base image path
        base_image_path = projects[project_id]["context"].get("base_image")
        if not base_image_path:
            raise ValueError("No base image found for this project")

        # Create labelled image with markers
        labelled_image_path = self._create_labelled_image(base_image_path, markers)

        # Add color information to markers
        color_names = ["red", "green", "blue", "purple", "orange"]
        markers_with_colors = []
        for i, marker in enumerate(markers[:5]):
            marker_data = marker.model_dump()
            marker_data["color"] = color_names[i % len(color_names)]
            markers_with_colors.append(marker_data)

        # Update project with markers, labelled image, and status
        projects[project_id]["context"]["improvement_markers"] = markers_with_colors
        projects[project_id]["context"]["labelled_base_image"] = labelled_image_path
        projects[project_id]["status"] = "IMPROVEMENT_MARKERS_ADDED"

        self._save_projects(projects)
        return labelled_image_path


# Global instance
data_manager = DataManager()
