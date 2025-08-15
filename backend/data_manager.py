import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
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


# Global instance
data_manager = DataManager()
