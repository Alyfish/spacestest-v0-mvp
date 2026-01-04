from __future__ import annotations
import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from fastapi import UploadFile
from logger_config import (
    log_api_call,
    log_external_api_call,
    log_project_status_change,
    log_user_action,
)
from models import ImprovementMarker, ProjectContext, ClipRect
from gemini_client import GeminiClient
from serp_client import SerpClient
from exa_client import ExaClient
from claude_client import claude_client
from openai_client import OpenAIClient

DATA_FILE = Path("data/projects.json")
IMAGES_DIR = Path("data/images")
MARKERS_SAVED_STATUS = "IMPROVEMENT_MARKERS_SAVED"
STATUS_ORDER = [
    "NEW",
    "BASE_IMAGE_UPLOADED",
    "SPACE_TYPE_SELECTED",
    MARKERS_SAVED_STATUS,
    "MARKER_RECOMMENDATIONS_READY",
    "INSPIRATION_IMAGES_UPLOADED",
    "INSPIRATION_RECOMMENDATIONS_READY",
    "PRODUCT_RECOMMENDATIONS_READY",
    "PRODUCT_RECOMMENDATION_SELECTED",
    "PRODUCT_SEARCH_COMPLETE",
    "PRODUCT_SELECTED",
    "IMAGE_GENERATED",
    "INSPIRATION_REDESIGN_COMPLETE",
]


class DataManager:
    def __init__(self):
        self.logger = logging.getLogger("spaces_ai")
        self._ensure_data_file_exists()
        self._ensure_images_dir_exists()
        self.gemini_client = GeminiClient()

        # Initialize SERP client for product discovery
        try:
            self.serp_client = SerpClient()
            self.logger.info("Successfully initialized SERP client")
        except Exception as e:
            self.logger.warning(f"Could not initialize SERP client: {e}")
            self.serp_client = None
        
        # Initialize Exa client for enhanced product search
        try:
            self.exa_client = ExaClient()
            self.logger.info("Successfully initialized Exa client")
        except Exception as e:
            self.logger.warning(f"Exa client not available: {e}")
            self.exa_client = None

        # Initialize Gemini client for image generation
        # Gemini client is now the main client, initialized above

        # Initialize CLIP client for enhanced image-based search
        try:
            from clip_client import CLIPClient

            self.clip_client = CLIPClient()
            if self.clip_client.is_available():
                self.logger.info(
                    "Successfully initialized CLIP client for image-based search"
                )
            else:
                self.logger.warning("CLIP client initialized but model not available")
                self.clip_client = None
        except Exception as e:
            self.logger.warning(f"Could not initialize CLIP client: {e}")
            self.clip_client = None

        # OpenAI client for vision (used in clip search query generation fallback)
        try:
            self.openai_client = OpenAIClient()
        except Exception as e:
            self.logger.warning(f"OpenAI client not available: {e}")
            self.openai_client = None

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
            result = self.gemini_client.analyze_image_with_vision(
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
        context: ProjectContext,
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

            color_palette = context.color_analysis.get("palette_name") if context.color_analysis else None
            primary_colors = context.color_analysis.get("primary_colors") if context.color_analysis else None
            style_name = context.style_analysis.get("style_name") if context.style_analysis else None
            style_materials = context.style_analysis.get("materials") if context.style_analysis else None
            preferred_stores = context.preferred_stores or []

            # Build the prompt with marker information
            marker_info = "\n".join(
                [
                    f"Marker {i + 1} ({marker.color}): {marker.description}"
                    for i, marker in enumerate(markers)
                ]
            )

            prompt = f"""
            Analyze the BASE ROOM IMAGE and provide specific interior design recommendations based on the user's improvement markers.

            Space Type: {space_type}
            Color Palette: {color_palette or "Not provided"}
            Primary Colors (guidance): {primary_colors or "Not provided"}
            Design Style: {style_name or "Not provided"}
            Style Materials: {style_materials or "Not provided"}
            Preferred Stores: {preferred_stores or "Not provided"}
            
            User's Improvement Requests:
            {marker_info}

            Provide specific, actionable recommendations as bullet points. Each recommendation should:
            - Be specific about what to change and where
            - Reference the marker locations in the image
            - Include practical suggestions for furniture, decor, or layout changes
            - Align with the given color palette and design style
            - Favor items that could realistically be sourced from the preferred stores listed
            - Be written in a clear, actionable format
            - Keep outputs concise (1–2 sentences each)

            IMPORTANT: Return exactly 6 recommendations, each as a simple string that clearly states what to do and where.
            """

            # Analyze the labelled image with markers using vision API
            result = self.gemini_client.analyze_image_with_vision(
                prompt=prompt,
                pydantic_model=AIRecommendationResponse,
                image_path=labelled_image_path,
                system_message="You are an expert interior designer. Provide specific, actionable recommendations for improving spaces based on user feedback. Focus on practical changes that can be easily implemented, aligned to the provided color palette, design style, and preferred stores. Always return exactly 4 recommendations.",
            )

            recs = (result.recommendations or [])[:6]
            while len(recs) < 6:
                recs.append("Add a cohesive accent that matches the selected style and palette")

            return recs

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

    def _dedupe_products_by_url(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate products by normalized URL (drop query params/fragments)."""
        from urllib.parse import urlparse, urlunparse

        def normalize(u: str) -> str:
            try:
                parsed = urlparse(u)
                cleaned = parsed._replace(query="", fragment="")
                return urlunparse(cleaned).lower()
            except Exception:
                return u.split("?")[0].lower()

        seen = set()
        deduped: List[Dict[str, Any]] = []
        for p in products:
            url = p.get("url") or ""
            key = normalize(url)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped.append(p)
        return deduped

    def upload_image_to_imgbb(self, image_base64: str) -> Optional[str]:
        """Upload base64 image to ImgBB and return public URL."""
        import requests
        
        try:
            imgbb_key = os.getenv("IMGBB_API_KEY")
            if not imgbb_key:
                self.logger.warning("IMGBB_API_KEY not found")
                return None
            
            url = "https://api.imgbb.com/1/upload"
            payload = {
                "key": imgbb_key,
                "image": image_base64,
            }
            
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            
            if result.get("success"):
                return result["data"]["url"]
            
            self.logger.warning(f"ImgBB upload failed: {result}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error uploading to ImgBB: {e}")
            return None


    def _type_guard(self, title: str, target_type: str) -> bool:
        """Allow only titles that match the target type family and reject decor/how-to."""
        t = title.lower()
        tt = target_type.lower()
        # Negative keywords for decor/how-to
        negatives = ["decor", "how to", "ideas", "tutorial", "guide", "inspiration", "poster", "print"]
        if any(neg in t for neg in negatives):
            return False

        # Core category mapping
        type_map = {
            "shelf": ["shelf", "shelving", "bookcase", "wall shelf"],
            "console table": ["console table", "sofa table", "entry table"],
            "table": ["table", "dining table", "coffee table", "side table", "end table", "desk"],
            "bench": ["bench", "ottoman", "entry bench"],
            "chair": ["chair", "armchair", "accent chair", "dining chair", "desk chair"],
            "sofa": ["sofa", "couch", "sectional", "loveseat"],
            "bed": ["bed", "platform bed", "bed frame", "headboard"],
            "lamp": ["lamp", "floor lamp", "table lamp", "sconce"],
            "storage": ["cabinet", "dresser", "sideboard", "buffet", "storage"],
            "rug": ["rug", "runner"],
        }

        # Find matched family
        for family, keywords in type_map.items():
            if tt in family or tt in " ".join(keywords):
                return any(k in t for k in keywords)

        # Default: require target_type substring
        return tt in t

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

    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project and its associated files
        
        Args:
            project_id: ID of the project to delete
            
        Returns:
            bool: True if project was deleted, False if not found
        """
        projects = self._load_projects()
        
        if project_id not in projects:
            return False
            
        # Delete project images directory
        project_images_dir = IMAGES_DIR / project_id
        if project_images_dir.exists():
            shutil.rmtree(project_images_dir)
            self.logger.info(f"Deleted images directory for project {project_id}")
            
        # Remove from projects dictionary
        del projects[project_id]
        
        # Save updated projects
        self._save_projects(projects)
        
        self.logger.info(f"Deleted project {project_id}")
        log_user_action("project_deleted", project_id=project_id)
        
        return True

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

            # Update project with markers and labelled image; recommendations generated later when design context is ready
            current_context = ProjectContext.model_validate(
                projects[project_id]["context"]
            )
            updated_context = current_context.model_copy(
                update={
                    "improvement_markers": markers_with_colors,
                    "labelled_base_image": labelled_image_path,
                    "marker_recommendations": [],
                }
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = MARKERS_SAVED_STATUS

            print("Saving projects to file")
            self._save_projects(projects)
            # Attempt generation if design context is already present
            self._try_generate_marker_recommendations(project_id)
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
                update={
                    "inspiration_images": updated_inspiration_images,
                    "inspiration_images_skipped": False,
                }
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
                update={
                    "inspiration_images": updated_inspiration_images,
                    "inspiration_images_skipped": False,
                }
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
                if context.inspiration_images_skipped:
                    raise ValueError(
                        "Inspiration images were skipped. Upload images to generate recommendations."
                    )
                raise ValueError("No inspiration images found for this project")

            if not context.base_image:
                raise ValueError("No base image found for this project")

            if not context.space_type:
                raise ValueError("No space type selected for this project")
            
            # Require color and style context (or explicit skips) before generating
            if not context.color_analysis and not context.color_analysis_skipped:
                raise ValueError("Please select a color palette or skip color analysis before generating recommendations")
            
            if not context.style_analysis and not context.style_analysis_skipped:
                raise ValueError("Please select a design style or skip style analysis before generating recommendations")
            
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

            # Extract color and style information
            color_name = (
                context.color_analysis.get("palette_name", "Custom")
                if context.color_analysis
                else "Not provided"
            )
            color_overview = (
                context.color_analysis.get("design_brief", "")
                if context.color_analysis
                else ""
            )
            style_name = (
                context.style_analysis.get("style_name", "Modern")
                if context.style_analysis
                else "Not provided"
            )
            style_overview = (
                context.style_analysis.get("style_overview", "")
                if context.style_analysis
                else ""
            )
            materials = (
                ", ".join(context.style_analysis.get("materials", [])[:5])
                if context.style_analysis
                else ""
            )
            preferred_stores = ", ".join(context.preferred_stores or [])
            
            # Format improvement markers if they exist
            markers_text = ""
            if context.improvement_markers:
                markers_list = [f"- {m.description}" for m in context.improvement_markers]
                markers_text = "\nUser's Specific Improvement Requests (High Priority):\n" + "\n".join(markers_list)

            prompt = f"""
            Analyze the attached base room image along with the inspiration images for this {context.space_type} project and provide exactly 6 specific recommendations.
            
            Space Type: {context.space_type}
            
            Selected Color Palette: {color_name}
            Color Guidance: {color_overview}
            
            Selected Style: {style_name}
            Style Overview: {style_overview}
            Key Materials: {materials}
            
            Preferred Stores (prioritize these if possible): {preferred_stores}
            {markers_text}
            
            Inspiration Images:
            {inspiration_info}

            Use the BASE ROOM IMAGE as the primary context for feasibility and layout.
            
            Based on the base room image, the inspiration images, the selected color palette, the chosen design style, AND the user's specific improvement requests (if any), provide exactly 4 specific, actionable design recommendations that:
            1. DIRECTLY ADDRESS user's improvement requests if present (these are highest priority).
            2. Incorporate the user's selected color palette throughout the recommendations.
            3. Follow the principles of the user's chosen {style_name} design style.
            4. Are tailored to the {context.space_type} space type.
            5. Respect the room's existing layout, lighting, and architectural constraints visible in the base image.
            6. Include practical suggestions for furniture, decor, and layout.
            7. Are written in a clear, actionable format.
            
            IMPORTANT: Provide exactly 4 recommendations. Each recommendation should be a complete, standalone suggestion.
            Format each recommendation as a simple string that clearly states what to do and where.
            """

            # Resolve base image path
            base_path = Path(context.base_image)
            # If path logic is tricky, just check if it exists as is (relative to CWD)
            if not base_path.exists():
                # Try fallback relative to data dir if needed, but context.base_image usually has full relative path
                candidate = DATA_FILE.parent / base_path
                if candidate.exists():
                    base_path = candidate
                elif not base_path.is_absolute():
                     # Last ditch: try without any leading directories if they were duplicated
                     # But most likely it's just relative to root.
                     pass

            if not base_path.exists():
                raise ValueError(f"Base image not found at {base_path}")

            # Use the first inspiration image as an additional visual reference
            first_inspiration = context.inspiration_images[0]
            first_inspiration_path = Path(first_inspiration)
            
            if not first_inspiration_path.exists():
                 candidate = DATA_FILE.parent / first_inspiration_path
                 if candidate.exists():
                     first_inspiration_path = candidate

            if not first_inspiration_path.exists():
                raise ValueError(f"Inspiration image not found at {first_inspiration_path}")

            result = self.gemini_client.analyze_image_with_vision(
                prompt=prompt,
                pydantic_model=AIInspirationResponse,
                image_path=str(base_path),
                additional_image_paths=[str(first_inspiration_path)],
                system_message="You are an expert interior designer. Analyze inspiration images and provide specific, actionable design recommendations that incorporate the user's selected color palette and design style while being practical for the target space type. Always provide exactly 4 recommendations.",
            )

            # Ensure we have exactly 4 recommendations
            recommendations = result.recommendations[:4]
            if len(recommendations) < 4:
                # Pad if needed (shouldn't happen but just in case)
                while len(recommendations) < 4:
                    recommendations.append(f"Consider adding decorative accents that complement your {style_name} style")

            # Update project with inspiration recommendations
            updated_context = context.model_copy(
                update={"inspiration_recommendations": recommendations}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            projects[project_id]["status"] = "INSPIRATION_RECOMMENDATIONS_READY"

            print(
                f"Generated {len(recommendations)} inspiration recommendations"
            )
            self._save_projects(projects)
            return recommendations

        except Exception as e:
            print(f"ERROR in generate_inspiration_recommendations: {e}")
            import traceback

            traceback.print_exc()
            raise

    def apply_color_scheme(
        self, 
        project_id: str, 
        palette_name: str, 
        colors: List[str],
        let_ai_decide: bool = False
    ) -> Dict[str, Any]:
        """Apply a color scheme using the Color Agent for intelligent color application guidance"""
        try:
            print(f"🎨 Applying color scheme for project {project_id}")
            print(f"   Palette: {palette_name}, Colors: {colors}, AI Decide: {let_ai_decide}")
            
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            if not context.base_image:
                raise ValueError("No base image found for this project")
            
            if not context.space_type:
                raise ValueError("No space type selected for this project")

            # Call the Color Agent to analyze and provide guidance
            color_analysis = self.gemini_client.analyze_color_application(
                image_path=context.base_image,
                palette_name=palette_name,
                palette_colors=colors,
                space_type=context.space_type,
                let_ai_decide=let_ai_decide,
            )

            # Update project context with the color analysis
            # Also update color_scheme for backward compatibility with image generation
            color_scheme_data = {
                "palette_name": palette_name,
                "colors": colors,
                "let_ai_decide": let_ai_decide,
            }
            
            updated_context = context.model_copy(
                update={
                    "color_analysis": color_analysis,
                    "color_scheme": color_scheme_data,
                    "color_analysis_skipped": False,
                }
            )

            projects[project_id]["context"] = updated_context.model_dump()
            # Note: We don't change the project status here as color selection is optional
            # and doesn't block the workflow

            print(f"✅ Color Agent analysis saved for project {project_id}")
            self._save_projects(projects)
            # Trigger marker recommendations if all prerequisites are met
            self._try_generate_marker_recommendations(project_id)
            return color_analysis

        except Exception as e:
            print(f"❌ ERROR in apply_color_scheme: {e}")
            import traceback
            traceback.print_exc()
            raise

    def apply_style(
        self, 
        project_id: str, 
        style_name: str, 
        let_ai_decide: bool = False
    ) -> Dict[str, Any]:
        """Apply an interior design style using the Style Agent for comprehensive guidance"""
        try:
            print(f"🎨 Applying style for project {project_id}")
            print(f"   Style: {style_name}, AI Decide: {let_ai_decide}")
            
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            if not context.base_image:
                raise ValueError("No base image found for this project")
            
            if not context.space_type:
                raise ValueError("No space type selected for this project")

            # Get any existing color scheme to coordinate
            color_scheme = context.color_scheme

            # Call the Style Agent to analyze and provide guidance
            style_analysis = self.gemini_client.analyze_style_application(
                image_path=context.base_image,
                style_name=style_name,
                space_type=context.space_type,
                color_scheme=color_scheme,
                let_ai_decide=let_ai_decide,
            )

            # Update project context with the style analysis
            # Also update design_style for backward compatibility with image generation
            design_style_data = {
                "style_name": style_name,
                "let_ai_decide": let_ai_decide,
            }
            
            updated_context = context.model_copy(
                update={
                    "style_analysis": style_analysis,
                    "design_style": design_style_data,
                    "style_analysis_skipped": False,
                }
            )

            projects[project_id]["context"] = updated_context.model_dump()

            print(f"✅ Style Agent analysis saved for project {project_id}")
            self._save_projects(projects)
            # Trigger marker recommendations if all prerequisites are met
            self._try_generate_marker_recommendations(project_id)
            return style_analysis

        except Exception as e:
            print(f"❌ ERROR in apply_style: {e}")
            import traceback
            traceback.print_exc()
            raise

    def skip_color_analysis(self, project_id: str) -> None:
        """Skip color analysis for a project to unblock downstream steps."""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        context = ProjectContext.model_validate(projects[project_id]["context"])
        updated_context = context.model_copy(
            update={
                "color_analysis": None,
                "color_scheme": None,
                "color_analysis_skipped": True,
            }
        )

        projects[project_id]["context"] = updated_context.model_dump()
        self._save_projects(projects)
        self._try_generate_marker_recommendations(project_id)

    def skip_style_analysis(self, project_id: str) -> None:
        """Skip style analysis for a project to unblock downstream steps."""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        context = ProjectContext.model_validate(projects[project_id]["context"])
        updated_context = context.model_copy(
            update={
                "style_analysis": None,
                "design_style": None,
                "style_analysis_skipped": True,
            }
        )

        projects[project_id]["context"] = updated_context.model_dump()
        self._save_projects(projects)
        self._try_generate_marker_recommendations(project_id)

    def skip_inspiration_images(self, project_id: str) -> None:
        """Skip inspiration images to unblock downstream steps."""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        context = ProjectContext.model_validate(projects[project_id]["context"])
        updated_context = context.model_copy(
            update={
                "inspiration_images": [],
                "inspiration_recommendations": [],
                "inspiration_images_skipped": True,
            }
        )

        projects[project_id]["context"] = updated_context.model_dump()
        self._save_projects(projects)

    def update_preferred_stores(self, project_id: str, stores: List[str]) -> List[str]:
        """Update the list of preferred retail stores in the project context"""
        try:
            print(f"🛒 Updating preferred stores for project {project_id}: {stores}")
            projects = self._load_projects()

            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])
            
            updated_context = context.model_copy(
                update={"preferred_stores": stores}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            self._save_projects(projects)
            # Trigger marker recommendations if all prerequisites are met
            self._try_generate_marker_recommendations(project_id)
            
            return stores

        except Exception as e:
            print(f"❌ ERROR in update_preferred_stores: {e}")
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

            if context.color_analysis:
                ca = context.color_analysis
                color_info = f"\n\nColor Analysis (Guidelines to follow):\n- Primary: {ca.get('primary_colors', [])}\n- Palette: {ca.get('palette_name', 'Custom')}\n- Lighting/Texture: {ca.get('lighting_notes', 'N/A')}"
                context_info += color_info

            if context.style_analysis:
                sa = context.style_analysis
                style_info = f"\n\nStyle Analysis (Guidelines to follow):\n- Style: {sa.get('style_name', 'Custom')}\n- Materials: {sa.get('materials', [])}\n- Characteristics: {sa.get('furniture_characteristics', 'N/A')}"
                context_info += style_info

            if context.inspiration_recommendations:
                inspiration_info = "\n".join(
                    [f"- {rec}" for rec in context.inspiration_recommendations]
                )
                context_info += f"\n\nStyle Recommendations from Inspiration:\n{inspiration_info}"

            prompt = f"""Based on this comprehensive interior design project context, generate exactly 6 specific, actionable product recommendations.

{context_info}

Requirements:
- Each recommendation should be a specific action like "change sofa", "add coffee table", "replace dining chairs", "add floor lamp", etc.
- Focus on items that would have the most visual impact and align perfectly with the detected style and color guidelines.
- Consider the improvement areas and style preferences mentioned above.
- Make recommendations that are realistic and achievable for most homeowners.
- Keep each recommendation to 2-4 words maximum.

Return exactly 6 recommendations that are distinct and complementary to each other."""

            # Log AI API call with timing
            start_time = time.time()
            result = self.gemini_client.get_structured_completion(
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

            # Check if recommendation exists in either product or inspiration recommendations
            is_product_rec = context.product_recommendations and selected_recommendation in context.product_recommendations
            is_inspiration_rec = context.inspiration_recommendations and selected_recommendation in context.inspiration_recommendations

            if not (is_product_rec or is_inspiration_rec):
                raise ValueError(
                    f"'{selected_recommendation}' is not a valid recommendation option"
                )

            # Update the project context - Toggle selection (multi-select)
            current_selections = getattr(context, 'selected_product_recommendations', [])
            # Ensure current_selections is a mutable list
            current_selections = list(current_selections)

            if selected_recommendation in current_selections:
                current_selections.remove(selected_recommendation)
            else:
                current_selections.append(selected_recommendation)

            old_status = projects[project_id]["status"]
            updated_context = context.model_copy(
                update={"selected_product_recommendations": current_selections}
            )

            projects[project_id]["context"] = updated_context.model_dump()
            
            # Update status if we have a selection
            if current_selections:
                projects[project_id]["status"] = "PRODUCT_RECOMMENDATION_SELECTED"
            elif context.product_recommendations:
                 # Revert to product recs ready if we had them
                projects[project_id]["status"] = "PRODUCT_RECOMMENDATIONS_READY"
            elif context.inspiration_recommendations:
                # Revert to inspiration recs ready
                projects[project_id]["status"] = "INSPIRATION_RECOMMENDATIONS_READY"

            self.logger.info(
                "Updated product recommendation selections",
                extra={
                    "project_id": project_id,
                    "selected_recommendations": current_selections,
                    "status": projects[project_id]["status"],
                },
            )
            log_project_status_change(
                project_id, old_status, projects[project_id]["status"]
            )
            log_user_action(
                "product_recommendation_selected",
                project_id=project_id,
                recommendation=selected_recommendation,
            )

            self._save_projects(projects)
            return current_selections

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

            if not self.serp_client and not self.exa_client:
                raise ValueError(
                    "No product search client available - configure SERP_API_KEY or EXA_API_KEY"
                )

            # Use AI to generate a specific search query
            search_query = self._generate_search_query(context)
            self.logger.info(
                "Generated search query",
                extra={
                    "project_id": project_id,
                    "search_query": search_query,
                    "selected_recommendations": context.selected_product_recommendations,
                },
            )

            search_start_time = time.time()
            products: List[Dict[str, Any]] = []

            # SERP Google Shopping
            if self.serp_client:
                self.logger.info("Using SERP Google Shopping for product search")
                serp_products = self.serp_client.search_and_analyze_products(
                    query=search_query,
                    space_type=context.space_type or "general",
                    num_results=12,
                )
                search_duration = (time.time() - search_start_time) * 1000
                log_external_api_call(
                    "serp", "product_search", search_duration, True, len(serp_products)
                )
                for product in serp_products:
                    product["source_api"] = "serp"
                    product["search_method"] = "Google Shopping"
                products.extend(serp_products)

            # Exa semantic search + contents
            if self.exa_client:
                try:
                    exa_start = time.time()
                    exa_products = self.exa_client.search_and_analyze_products(
                        query=search_query,
                        space_type=context.space_type or "general",
                        num_results=10,
                        similar_per_seed=3,
                    )
                    exa_duration = (time.time() - exa_start) * 1000
                    log_external_api_call(
                        "exa", "product_search", exa_duration, True, len(exa_products)
                    )
                    for product in exa_products:
                        product["source_api"] = "exa"
                        product["search_method"] = "Exa Semantic"
                    products.extend(exa_products)
                except Exception as e:
                    self.logger.warning(f"Exa product search failed: {e}")
                    log_external_api_call("exa", "product_search", 0, False)

            # Deduplicate, type-guard, and limit
            products = self._dedupe_products_by_url(products)

            # Use the first recommendation to set a target type guard if multiple
            target_type = ""
            if context.selected_product_recommendations:
                target_type = context.selected_product_recommendations[0].split()[0]

            filtered_products: List[Dict[str, Any]] = []
            for p in products:
                title = p.get("title", "")
                if target_type and not self._type_guard(title, target_type):
                    continue
                if not p.get("is_product_page", True):
                    continue
                filtered_products.append(p)

            filtered_products = filtered_products[:8]

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
                    "selected_recommendations": context.selected_product_recommendations,
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

    def _analyze_single_item(self, project_id: str, rect: ClipRect, use_inspiration_image: bool = False) -> dict:
        """Internal helper to analyze a single furniture item using YOLO -> CLIP -> SERP pipeline."""
        try:
            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            project = projects[project_id]
            context = ProjectContext.model_validate(project["context"])

            # Choose which image to use for clip-search
            if use_inspiration_image:
                image_base64 = context.inspiration_generated_image_base64
                if not image_base64:
                    raise ValueError("No inspiration redesign image available to clip-search")
            else:
                image_base64 = context.generated_image_base64
                if not image_base64:
                    raise ValueError("No generated image available to clip-search")

            if not self.serp_client:
                raise ValueError("SERP client not available - please check SERP_API_KEY")

            # Decode base64 image
            import base64
            from io import BytesIO
            from PIL import Image

            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            width, height = image.size

            # Smart crop -------------------------------------------------
            x = max(0.0, min(1.0, rect.x))
            y = max(0.0, min(1.0, rect.y))
            w = max(0.0, min(1.0, rect.width))
            h = max(0.0, min(1.0, rect.height))
            if w <= 0 or h <= 0:
                raise ValueError("Clip rectangle has zero area")

            # Try YOLO snap if available
            snapped = False
            pad_ratio_yolo = 0.05
            if hasattr(self, "auto_detect_furniture"):
                try:
                    detections = self.auto_detect_furniture(project_id, image_type="inspiration" if use_inspiration_image else "product").get("detections", [])
                    for det in detections:
                        box = det.get("rect", {})
                        bx, by, bw, bh = box.get("x", 0), box.get("y", 0), box.get("width", 0), box.get("height", 0)
                        # Compute IoU with user rect
                        inter_left = max(x, bx)
                        inter_top = max(y, by)
                        inter_right = min(x + w, bx + bw)
                        inter_bottom = min(y + h, by + bh)
                        inter_w = max(0.0, inter_right - inter_left)
                        inter_h = max(0.0, inter_bottom - inter_top)
                        inter_area = inter_w * inter_h
                        user_area = w * h
                        box_area = bw * bh
                        if user_area > 0 and box_area > 0:
                            iou_user = inter_area / user_area
                            if iou_user > 0.5:
                                # Snap to YOLO box with small padding
                                x = max(0.0, bx - pad_ratio_yolo * bw)
                                y = max(0.0, by - pad_ratio_yolo * bh)
                                w = min(1.0, bw * (1 + 2 * pad_ratio_yolo))
                                h = min(1.0, bh * (1 + 2 * pad_ratio_yolo))
                                snapped = True
                                break
                except Exception as e:
                    self.logger.warning(f"YOLO snap failed, fallback to padding: {e}")

            if not snapped:
                # Square and pad
                max_dim = max(w, h)
                pad_ratio = 0.10
                w = h = max_dim * (1 + pad_ratio * 2)
                # Center around original rect
                x = x + (rect.width - w) / 2
                y = y + (rect.height - h) / 2
                # Clamp
                x = max(0.0, min(1.0 - w, x))
                y = max(0.0, min(1.0 - h, y))
                w = min(1.0, w)
                h = min(1.0, h)

            left = int(x * width)
            top = int(y * height)
            right = int(min(1.0, x + w) * width)
            bottom = int(min(1.0, y + h) * height)

            if right <= left or bottom <= top:
                raise ValueError("Invalid clip rectangle after conversion")

            crop = image.crop((left, top, right, bottom))

            # Save crop temporarily to analyze with vision
            temp_dir = DATA_FILE.parent / "images" / project_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            crop_path = temp_dir / f"clip_search_optimized_{uuid.uuid4().hex[:8]}.png" # Unique name for concurrency
            crop.save(crop_path)

            # Query generation
            clip_analysis = None
            search_query = None
            target_type = None
            if self.clip_client and self.clip_client.is_available():
                try:
                    clip_analysis = self.clip_client.analyze_furniture_region(crop)
                    target_type = (
                        clip_analysis.get("furniture_type", {}).get("name")
                        if clip_analysis and not clip_analysis.get("error")
                        else None
                    )
                    negative_keywords = ["decor", "ideas", "how to"]
                    search_query = self.clip_client.generate_enhanced_search_query(
                        crop,
                        vision_client=self.openai_client,
                        context=None,
                        negative_keywords=negative_keywords,
                    )
                except Exception as e:
                    self.logger.warning(f"CLIP query generation failed, fallback: {e}")

            if not search_query:
                search_query = (
                    context.selected_product["title"]
                    if context.selected_product
                    else (context.selected_product_recommendations[0] if context.selected_product_recommendations else "furniture")
                )

            # Execute SERP product search
            products: List[Dict[str, Any]] = []

            # SERP
            serp_products = self.serp_client.search_and_analyze_products(
                query=search_query,
                space_type=context.space_type or "general",
                num_results=12,
            )
            for product in serp_products:
                product["source_api"] = "serp"
                product["search_method"] = "Google Shopping"
            products.extend(serp_products)

            # Exa (semantic) if available
            if self.exa_client:
                try:
                    exa_products = self.exa_client.search_and_analyze_products(
                        query=search_query,
                        space_type=context.space_type or "general",
                        num_results=10,
                        similar_per_seed=3,
                    )
                    for product in exa_products:
                        product["source_api"] = "exa"
                        product["search_method"] = "Exa Semantic"
                    products.extend(exa_products)
                except Exception as e:
                    self.logger.warning(f"Exa clip-search fetch failed: {e}")

            # Deduplicate before scoring
            products = self._dedupe_products_by_url(products)

            # Type guard: filter decor/how-to mismatches using target_type if available
            filtered_products: List[Dict[str, Any]] = []
            for p in products:
                title = p.get("title", "")
                if target_type and not self._type_guard(title, target_type):
                    continue
                filtered_products.append(p)
            products = filtered_products

            # Re-rank/filter with CLIP similarity against the optimized crop
            scoring_meta = {}
            if products:
                scored = self.serp_client.score_products_with_clip(
                    products,
                    clip_client=self.clip_client,
                    query_image=crop,
                    drop_threshold=0.70,
                    boost_threshold=0.85,
                    timeout=1.5,
                    max_workers=8,
                    max_fetch=10,
                )
                products = scored.get("products", products)
                scoring_meta = scored.get("meta", {})

            result = {
                "search_query": search_query,
                "products": products,
                "total_found": len(products),
                "analysis_method": "clip" if clip_analysis else "vision",
                "clip_analysis": clip_analysis if clip_analysis and not clip_analysis.get("error") else None,
                "agent_notes": scoring_meta,
            }
            
            # Add CLIP analysis details if available
            if clip_analysis and not clip_analysis.get("error"):
                result["clip_analysis"] = {
                    "furniture_type": clip_analysis.get("furniture_type", {}).get("name"),
                    "furniture_confidence": clip_analysis.get("furniture_type", {}).get("confidence"),
                    "style": clip_analysis.get("style", {}).get("name"),
                    "material": clip_analysis.get("material", {}).get("name"),
                    "color": clip_analysis.get("color", {}).get("name"),
                }

            return result

        except Exception as e:
            self.logger.error(f"Single item analysis failed: {e}", exc_info=True)
            raise

    @log_api_call("analyze_furniture_batch")
    def analyze_furniture_batch(self, project_id: str, selections: List[Dict[str, Any]], image_type: str = "product") -> Dict[str, Any]:
        """
        Batch analyze multiple furniture selections efficiently using the YOLO -> CLIP -> SERP pipeline.
        Input selections contain {id, x, y, label} (center points).
        """
        results = []
        
        # Determine image source
        use_inspiration = (image_type == "inspiration")
        
        print(f"🔄 Processing batch analysis for {len(selections)} items (Type: {image_type})")

        for sel in selections:
            try:
                # Create a small seed rect around the point to help the YOLO snapper
                # The _analyze_single_item logic will snap this to the full object
                box_size = 0.1 # 10% initial box
                cx, cy = sel.get("x", 0.5), sel.get("y", 0.5)
                
                rect = ClipRect(
                    x=cx - (box_size / 2),
                    y=cy - (box_size / 2),
                    width=box_size,
                    height=box_size
                )
                
                # Analyze
                analysis = self._analyze_single_item(project_id, rect, use_inspiration_image=use_inspiration)
                
                # Format for frontend
                results.append({
                    "id": sel.get("id", "unknown"),
                    "furniture_type": analysis.get("clip_analysis", {}).get("furniture_type") or "Furniture",
                    "confidence": analysis.get("clip_analysis", {}).get("furniture_confidence") or 0.0,
                    "style": analysis.get("clip_analysis", {}).get("style") or "Unknown",
                    "material": analysis.get("clip_analysis", {}).get("material") or "Unknown",
                    "color": analysis.get("clip_analysis", {}).get("color") or "Unknown",
                    "search_query": analysis.get("search_query", ""),
                    "products": analysis.get("products", [])
                })
                
            except Exception as e:
                self.logger.error(f"Failed to analyze item {sel.get('id')}: {e}")
                # Add failed placeholder so UI doesn't break
                results.append({
                    "id": sel.get("id"),
                    "furniture_type": "Analysis Failed",
                    "confidence": 0,
                    "style": "-",
                    "material": "-",
                    "color": "-",
                    "search_query": "",
                    "products": []
                })

        return {
            "selections": results,
            "overall_analysis": f"Successfully identified {len(results)} items."
        }

    def _analyze_single_item(self, project_id: str, rect: ClipRect, use_inspiration_image: bool = False) -> dict:
        """Internal helper to analyze a single furniture item using YOLO -> CLIP -> SERP pipeline."""
        try:
            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            project = projects[project_id]
            context = ProjectContext.model_validate(project["context"])

            # Choose which image to use for clip-search
            if use_inspiration_image:
                image_base64 = context.inspiration_generated_image_base64
                if not image_base64:
                    raise ValueError("No inspiration redesign image available to clip-search")
            else:
                image_base64 = context.generated_image_base64
                if not image_base64:
                    raise ValueError("No generated image available to clip-search")

            if not self.serp_client:
                raise ValueError("SERP client not available - please check SERP_API_KEY")

            # Decode base64 image
            import base64
            from io import BytesIO
            from PIL import Image

            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            width, height = image.size

            # Smart crop -------------------------------------------------
            x = max(0.0, min(1.0, rect.x))
            y = max(0.0, min(1.0, rect.y))
            w = max(0.0, min(1.0, rect.width))
            h = max(0.0, min(1.0, rect.height))
            if w <= 0 or h <= 0:
                raise ValueError("Clip rectangle has zero area")

            # Try YOLO snap if available
            snapped = False
            pad_ratio_yolo = 0.05
            if hasattr(self, "auto_detect_furniture"):
                try:
                    detections = self.auto_detect_furniture(project_id, image_type="inspiration" if use_inspiration_image else "product").get("detections", [])
                    for det in detections:
                        box = det.get("rect", {})
                        bx, by, bw, bh = box.get("x", 0), box.get("y", 0), box.get("width", 0), box.get("height", 0)
                        # Compute IoU with user rect
                        inter_left = max(x, bx)
                        inter_top = max(y, by)
                        inter_right = min(x + w, bx + bw)
                        inter_bottom = min(y + h, by + bh)
                        inter_w = max(0.0, inter_right - inter_left)
                        inter_h = max(0.0, inter_bottom - inter_top)
                        inter_area = inter_w * inter_h
                        user_area = w * h
                        box_area = bw * bh
                        if user_area > 0 and box_area > 0:
                            iou_user = inter_area / user_area
                            if iou_user > 0.5:
                                # Snap to YOLO box with small padding
                                x = max(0.0, bx - pad_ratio_yolo * bw)
                                y = max(0.0, by - pad_ratio_yolo * bh)
                                w = min(1.0, bw * (1 + 2 * pad_ratio_yolo))
                                h = min(1.0, bh * (1 + 2 * pad_ratio_yolo))
                                snapped = True
                                break
                except Exception as e:
                    self.logger.warning(f"YOLO snap failed, fallback to padding: {e}")

            if not snapped:
                # Square and pad
                max_dim = max(w, h)
                pad_ratio = 0.10
                w = h = max_dim * (1 + pad_ratio * 2)
                # Center around original rect
                x = x + (rect.width - w) / 2
                y = y + (rect.height - h) / 2
                # Clamp
                x = max(0.0, min(1.0 - w, x))
                y = max(0.0, min(1.0 - h, y))
                w = min(1.0, w)
                h = min(1.0, h)

            left = int(x * width)
            top = int(y * height)
            right = int(min(1.0, x + w) * width)
            bottom = int(min(1.0, y + h) * height)

            if right <= left or bottom <= top:
                raise ValueError("Invalid clip rectangle after conversion")

            crop = image.crop((left, top, right, bottom))

            # Save crop temporarily to analyze with vision
            temp_dir = DATA_FILE.parent / "images" / project_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            crop_path = temp_dir / f"clip_search_optimized_{uuid.uuid4().hex[:8]}.png" # Unique name for concurrency
            crop.save(crop_path)

            # Query generation
            clip_analysis = None
            search_query = None
            target_type = None
            if self.clip_client and self.clip_client.is_available():
                try:
                    clip_analysis = self.clip_client.analyze_furniture_region(crop)
                    target_type = (
                        clip_analysis.get("furniture_type", {}).get("name")
                        if clip_analysis and not clip_analysis.get("error")
                        else None
                    )
                    negative_keywords = ["decor", "ideas", "how to"]
                    search_query = self.clip_client.generate_enhanced_search_query(
                        crop,
                        vision_client=self.openai_client,
                        context=None,
                        negative_keywords=negative_keywords,
                    )
                except Exception as e:
                    self.logger.warning(f"CLIP query generation failed, fallback: {e}")

            if not search_query:
                search_query = (
                    context.selected_product["title"]
                    if context.selected_product
                    else (context.selected_product_recommendations[0] if context.selected_product_recommendations else "furniture")
                )

            # Execute SERP product search
            products: List[Dict[str, Any]] = []

            # SERP
            serp_products = self.serp_client.search_and_analyze_products(
                query=search_query,
                space_type=context.space_type or "general",
                num_results=12,
            )
            for product in serp_products:
                product["source_api"] = "serp"
                product["search_method"] = "Google Shopping"
            products.extend(serp_products)

            # Exa (semantic) if available
            if self.exa_client:
                try:
                    exa_products = self.exa_client.search_and_analyze_products(
                        query=search_query,
                        space_type=context.space_type or "general",
                        num_results=10,
                        similar_per_seed=3,
                    )
                    for product in exa_products:
                        product["source_api"] = "exa"
                        product["search_method"] = "Exa Semantic"
                    products.extend(exa_products)
                except Exception as e:
                    self.logger.warning(f"Exa clip-search fetch failed: {e}")

            # Deduplicate before scoring
            products = self._dedupe_products_by_url(products)

            # Type guard: filter decor/how-to mismatches using target_type if available
            filtered_products: List[Dict[str, Any]] = []
            for p in products:
                title = p.get("title", "")
                if target_type and not self._type_guard(title, target_type):
                    continue
                filtered_products.append(p)
            products = filtered_products

            # Re-rank/filter with CLIP similarity against the optimized crop
            scoring_meta = {}
            if products:
                scored = self.serp_client.score_products_with_clip(
                    products,
                    clip_client=self.clip_client,
                    query_image=crop,
                    drop_threshold=0.70,
                    boost_threshold=0.85,
                    timeout=1.5,
                    max_workers=8,
                    max_fetch=10,
                )
                products = scored.get("products", products)
                scoring_meta = scored.get("meta", {})

            result = {
                "search_query": search_query,
                "products": products,
                "total_found": len(products),
                "analysis_method": "clip" if clip_analysis else "vision",
                "clip_analysis": clip_analysis if clip_analysis and not clip_analysis.get("error") else None,
                "agent_notes": scoring_meta,
            }
            
            # Add CLIP analysis details if available
            if clip_analysis and not clip_analysis.get("error"):
                result["clip_analysis"] = {
                    "furniture_type": clip_analysis.get("furniture_type", {}).get("name"),
                    "furniture_confidence": clip_analysis.get("furniture_type", {}).get("confidence"),
                    "style": clip_analysis.get("style", {}).get("name"),
                    "material": clip_analysis.get("material", {}).get("name"),
                    "color": clip_analysis.get("color", {}).get("name"),
                }

            return result

        except Exception as e:
            self.logger.error(f"Single item analysis failed: {e}", exc_info=True)
            raise

    @log_api_call("analyze_furniture_batch")
    def analyze_furniture_batch(self, project_id: str, selections: List[Dict[str, Any]], image_type: str = "product") -> Dict[str, Any]:
        """
        Batch analyze multiple furniture selections efficiently using the YOLO -> CLIP -> SERP pipeline.
        Input selections contain {id, x, y, label} (center points).
        """
        results = []
        
        # Determine image source
        use_inspiration = (image_type == "inspiration")
        
        print(f"🔄 Processing batch analysis for {len(selections)} items (Type: {image_type})")

        for sel in selections:
            try:
                # Create a small seed rect around the point to help the YOLO snapper
                # The _analyze_single_item logic will snap this to the full object
                box_size = 0.1 # 10% initial box
                cx, cy = sel.get("x", 0.5), sel.get("y", 0.5)
                
                rect = ClipRect(
                    x=cx - (box_size / 2),
                    y=cy - (box_size / 2),
                    width=box_size,
                    height=box_size
                )
                
                # Analyze
                analysis = self._analyze_single_item(project_id, rect, use_inspiration_image=use_inspiration)
                
                # Format for frontend
                results.append({
                    "id": sel.get("id", "unknown"),
                    "furniture_type": analysis.get("clip_analysis", {}).get("furniture_type") or "Furniture",
                    "confidence": analysis.get("clip_analysis", {}).get("furniture_confidence") or 0.0,
                    "style": analysis.get("clip_analysis", {}).get("style") or "Unknown",
                    "material": analysis.get("clip_analysis", {}).get("material") or "Unknown",
                    "color": analysis.get("clip_analysis", {}).get("color") or "Unknown",
                    "search_query": analysis.get("search_query", ""),
                    "products": analysis.get("products", [])
                })
                
            except Exception as e:
                self.logger.error(f"Failed to analyze item {sel.get('id')}: {e}")
                # Add failed placeholder so UI doesn't break
                results.append({
                    "id": sel.get("id"),
                    "furniture_type": "Analysis Failed",
                    "confidence": 0,
                    "style": "-",
                    "material": "-",
                    "color": "-",
                    "search_query": "",
                    "products": []
                })

        return {
            "selections": results,
            "overall_analysis": f"Successfully identified {len(results)} items."
        }

    @log_api_call("clip_search_products")
    def clip_search_products(self, project_id: str, rect: ClipRect, use_inspiration_image: bool = False) -> dict:
        """Crop generated image, build a rich query, and re-rank SERP with CLIP visual filtering."""
        try:
            result = self._analyze_single_item(project_id, rect, use_inspiration_image)

            log_user_action(
                "clip_product_search_completed",
                project_id=project_id,
                results_count=len(result.get("products", [])),
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Failed clip-based product search: {e}",
                extra={"project_id": project_id},
                exc_info=True,
            )
            raise

    def select_product_for_generation(
        self,
        project_id: str,
        product_url: str,
        product_title: str,
        product_image_url: str,
        generation_prompt: str = None,
        color_scheme: Dict[str, Any] = None,
        design_style: Dict[str, Any] = None,
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

            print("💾 Creating selected product storage...")
            # Get existing selected products or empty list
            current_products = getattr(context, 'selected_products', [])
            current_products = list(current_products) # Ensure mutable

            # Check if product already selected (by URL)
            exists = any(p.get('url') == product_url for p in current_products)
            
            if not exists:
                # Save selected product
                selected_product = {
                    "url": product_url,
                    "title": product_title,
                    "image_url": product_image_url,
                    "selected_at": datetime.now().isoformat(),
                }
                current_products.append(selected_product)
                print(f"✅ Added product to selection: {product_title}")
            else:
                print(f"ℹ️ Product already in selection: {product_title}")

            print("📝 Updating context with selection list...")
            context.selected_products = current_products
            context.generation_prompt = generation_prompt
            
            # Save color scheme if provided
            if color_scheme:
                print(f"🎨 Saving color scheme: {color_scheme.get('palette_name', 'Custom')}")
                context.color_scheme = color_scheme
            
            # Save design style if provided
            if design_style:
                print(f"🏛️ Saving design style: {design_style.get('style_name', 'Custom')}")
                context.design_style = design_style

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
                "selected_products": current_products,
                "status": "success",
                "message": f"Added to selection: {product_title[:50]}...",
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
            selected_products = context.selected_products
            if not selected_products:
                raise ValueError("No products selected for visualization")
            
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

            # Generate the visualization with multi-product context
            generated_image_base64, final_prompt = (
                self.gemini_client.generate_product_visualization(
                    original_room_image_path=str(original_room_image_path),
                    selected_products=selected_products,
                    space_type=space_type,
                    inspiration_recommendations=context.inspiration_recommendations
                    or [],
                    marker_locations=context.improvement_markers or [],
                    custom_prompt=custom_prompt,
                    project_data_dir=project_dir,
                    color_scheme=getattr(context, 'color_scheme', None),
                    design_style=getattr(context, 'design_style', None),
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
                "selected_products": selected_products,
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

    def generate_inspiration_redesign(self, project_id: str):
        """Generate a redesigned room image based on inspiration recommendations using Gemini"""
        try:
            log_user_action("inspiration_redesign_started", {"project_id": project_id})

            # Load project context
            project = self.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(project["context"])
            # Detailed readiness logging
            # Check readiness: needs base image, space type, and EITHER inspiration OR product recs
            has_inspiration = context.inspiration_recommendations and len(context.inspiration_recommendations) > 0
            has_products = context.product_recommendations and len(context.product_recommendations) > 0
            ready = context.base_image and context.space_type and (has_inspiration or has_products)
            
            self.logger.info(
                "Checking readiness for inspiration redesign",
                extra={
                    "project_id": project_id,
                    "has_base_image": context.base_image is not None,
                    "has_space_type": context.space_type is not None,
                    "num_inspiration_recs": len(context.inspiration_recommendations or []),
                    "num_product_recs": len(context.product_recommendations or []),
                    "project_status": project["status"],
                },
            )
            if not ready:
                missing = []
                if not context.base_image:
                    missing.append("base_image")
                if not context.space_type:
                    missing.append("space_type")
                if not (has_inspiration or has_products):
                    missing.append("inspiration_or_product_recommendations")
                raise ValueError(
                    f"Project is not ready for redesign; missing: {', '.join(missing)}"
                )

            if not self.gemini_client:
                raise ValueError("Gemini client is not available")

            # Get the original room image path
            original_room_image_path = None
            if context.base_image:
                print(f"🖼️ Base image from context: {context.base_image}")

                # Handle path construction correctly
                if context.base_image.startswith("data/"):
                    relative_path = context.base_image[5:]
                    original_room_image_path = DATA_FILE.parent / relative_path
                elif "/" in context.base_image:
                    original_room_image_path = DATA_FILE.parent / context.base_image
                else:
                    project_images_dir = DATA_FILE.parent / "images" / project_id
                    original_room_image_path = project_images_dir / context.base_image

                if not original_room_image_path.exists():
                    raise ValueError(
                        f"Original room image not found: {original_room_image_path}"
                    )

            if not original_room_image_path:
                raise ValueError("No original room image available")

            # --- Helper to prevent f-string crashes ---
            def clean(text):
                """Escapes curly braces so Python f-strings don't break."""
                if not text: return ""
                return str(text).replace("{", "{{").replace("}", "}}")

            # Get space type for prompt
            space_type = context.space_type or "living space"

            # 1. Build DESIGN CONTEXT
            design_context_lines = []
            
            # Inspiration
            if context.inspiration_recommendations and len(context.inspiration_recommendations) > 0:
                design_context_lines.append("INSPIRATION GOALS:")
                # We clean every string we inject
                design_context_lines.extend([f"- {clean(rec)}" for rec in context.inspiration_recommendations[:5]])
                design_context_lines.append("") # Blank line for spacing
            
            # Improvement Markers
            if context.improvement_markers:
                design_context_lines.append("AREAS TO IMPROVE:")
                design_context_lines.extend([f"- {clean(m.description)}" for m in context.improvement_markers])
                design_context_lines.append("")

            # Color Analysis
            if context.color_analysis:
                ca = context.color_analysis
                design_context_lines.append("COLOR GUIDELINES:")
                design_context_lines.append(f"- Palette: {clean(ca.get('palette_name', 'Custom'))}")
                
                # Fix: primary_colors is a list of ColorSwatch dicts, not strings
                if ca.get('primary_colors'):
                    # Handle both list of strings (legacy) and list of dicts (ColorSwatch)
                    p_colors = []
                    for c in ca.get('primary_colors', []):
                        if isinstance(c, dict):
                            # Extract hex and description
                            c_str = c.get('hex', '')
                            if c.get('description'):
                                c_str += f" ({c.get('description')})"
                            p_colors.append(c_str)
                        elif isinstance(c, str):
                            p_colors.append(c)
                        else:
                            p_colors.append(str(c))
                    
                    design_context_lines.append(f"- Primary Colors: {clean(', '.join(p_colors))}")
                
                design_context_lines.append(f"- Lighting Notes: {clean(ca.get('lighting_notes', 'N/A'))}")
                design_context_lines.append("")

            # Style Analysis
            if context.style_analysis:
                sa = context.style_analysis
                design_context_lines.append("STYLE GUIDELINES:")
                design_context_lines.append(f"- Style: {clean(sa.get('style_name', 'Custom'))}")
                if sa.get('materials'):
                    design_context_lines.append(f"- Materials: {clean(', '.join(sa.get('materials')))}")
                design_context_lines.append(f"- Characteristics: {clean(sa.get('furniture_characteristics', 'N/A'))}")
                
            # Join and ensure we don't return an empty block if no data exists
            design_context_str = "\n".join(design_context_lines) if design_context_lines else "General Modern Upgrade"

            # 2. Build PRODUCT UPDATES
            product_list_str = "None specified"
            
            # Logic: Using existing has_products flag or re-deriving
            selected_recs = context.selected_product_recommendations or []
            ai_recs = context.product_recommendations or []
            product_source = selected_recs if len(selected_recs) > 0 else ai_recs
            
            if product_source:
                product_list_str = "\n".join([f"- {clean(rec)}" for rec in product_source[:5]])

            # 3. Final Prompt Construction - PHOTOREALISM FOCUSED
            prompt = f"""### ROLE & OBJECTIVE
You are a master of Architectural Photography and Interior Restoration. Your task is to modify the provided photograph (the input image) by replacing specific furniture and decor while maintaining the exact architectural shell and original camera properties. The goal is a "Real-Life" photograph, not a digital render.

### 1. STRUCTURAL LOCKDOWN (NON-NEGOTIABLE)
DO NOT ALTER: The position of walls, ceiling height, window frames, door locations, flooring material, or electrical outlets.
SPATIAL DYNAMICS: New furniture must occupy the same 3D coordinate space as the items they replace. Ensure the scale of new items matches the realistic dimensions of the room's footprint.
PERSPECTIVE: Maintain the exact lens focal length and camera angle of the original photo.

### 2. PHOTOGRAPHIC REALISM PROTOCOLS (CRITICAL)
LIGHTING PHYSICS: Do not add "magical" light sources. All illumination must come from the existing windows and any visible lamps in the original photo. Shadows must be hard-edged or soft based on the original photo's light direction.
MATERIAL AUTHENTICITY: Avoid the "plastic" AI look at all costs. Wood must show natural grain and micro-scratches; fabrics must show visible weave and realistic folding; metal must show authentic reflections of the room environment, not generic white highlights.
OPTICAL IMPERFECTIONS: Include subtle photographic traits: natural depth of field (slight blur on very foreground or background objects), realistic color grading matching the original photo's white balance, and organic shadows in corners (ambient occlusion).
CAMERA SIMULATION: Treat this as if shot on a professional full-frame DSLR with a 24-35mm lens. Emulate subtle lens characteristics like minor vignetting and natural color fringing at high-contrast edges.

### 3. DESIGN SPECIFICATIONS
SPACE TYPE: {clean(space_type)}

{design_context_str}

FURNITURE REPLACEMENTS:
{product_list_str}

DECOR & TEXTILES:
- If adding a rug, ensure it tucks realistically under nearby furniture legs.
- Any wall art should have appropriate frames matching the style (e.g., thin black metal for modern, ornate wood for traditional).
- Textiles (curtains, throws, pillows) must show realistic fabric draping and creasing.

DECLUTTERING: Remove all small loose items, trash, and visible cables from desks and floors to create a clean, organized, professional space.

### 4. OUTPUT REQUIREMENT
Generate a high-resolution photograph. If the image looks like a "3D concept render" or has a smooth, plastic, digital art appearance, it has FAILED. It MUST look like a "before and after" photo taken by the same camera in the same physical room. The final image should be indistinguishable from a real photograph shot for a high-end interior design magazine."""

            print(f"🎨 Inspiration redesign prompt: {prompt[:200]}...")

            # Call Gemini API using the new method
            generated_image_base64 = self.gemini_client.generate_room_redesign(
                original_room_image_path=original_room_image_path,
                prompt=prompt
            )

            # Assign to generated_image_base64 for the rest of the function to use
            # (which already expects this variable name)


            # Update context with generated image
            context.inspiration_generated_image_base64 = generated_image_base64
            context.inspiration_generation_prompt = prompt

            # Save context
            projects = self._load_projects()
            projects[project_id]["context"] = context.model_dump()
            projects[project_id]["status"] = "INSPIRATION_REDESIGN_COMPLETE"
            self._save_projects(projects)

            log_project_status_change(
                project_id, project["status"], "INSPIRATION_REDESIGN_COMPLETE"
            )
            log_user_action(
                "inspiration_redesign_completed",
                {
                    "project_id": project_id,
                    "image_size": f"{len(generated_image_base64)} chars",
                },
            )

            return {
                "project_id": project_id,
                "generated_image_base64": generated_image_base64,
                "inspiration_prompt": prompt,
                "inspiration_recommendations": context.inspiration_recommendations,
                "status": "success",
                "message": "Inspiration-based redesign completed successfully",
            }

        except Exception as e:
            self.logger.error(f"Failed to generate inspiration redesign: {e}")
            log_external_api_call("gemini", "inspiration_redesign", 0, False)
            raise

    @log_api_call("analyze_furniture_batch")
    def analyze_furniture_batch(
        self, 
        project_id: str, 
        selections: List,
        image_type: str = "product",
        mode: str = "full"
    ) -> Dict[str, Any]:
        """
        Analyze multiple furniture selections using Gemini 3.0 spatial detection, ImgBB, and CLIP.
        """
        try:
            # Load Project
            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")
            
            project = projects[project_id]
            context = ProjectContext.model_validate(project["context"])
            
            # 1. Get Image
            if image_type == "inspiration":
                image_base64 = context.inspiration_generated_image_base64
                if not image_base64:
                    raise ValueError("No inspiration redesign image available")
            else:
                image_base64 = context.generated_image_base64
                if not image_base64:
                    # Fallback to base image if generated image not available
                    if context.base_image and os.path.exists(context.base_image):
                         with open(context.base_image, "rb") as f:
                            image_base64 = base64.b64encode(f.read()).decode('utf-8')
                    else:
                        raise ValueError("No image available for analysis")
            
            # Decode image for processing
            import base64
            from io import BytesIO
            from PIL import Image
            image_bytes = base64.b64decode(image_base64)
            full_image = Image.open(BytesIO(image_bytes)).convert("RGB")
            width, height = full_image.size
            
            # Initialize Utilities
            from spatial_utils import SpatialDetector, smart_crop
            spatial_detector = SpatialDetector()
            
            analysis_results = []
            
            for selection in selections:
                try:
                    # Extract click coordinates
                    # Handle both Pydantic objects and dicts
                    if hasattr(selection, 'x') and hasattr(selection, 'y'):
                        # Pydantic object (FurnitureSelection)
                        x = selection.x
                        y = selection.y
                    elif isinstance(selection, dict):
                        # Dict format
                        x = selection.get("x")
                        y = selection.get("y")
                    else:
                        self.logger.warning(f"Unknown selection format: {type(selection)}")
                        continue

                    if x is None or y is None:
                        self.logger.warning(f"Skipping selection without coordinates: {selection}")
                        continue
                        
                    self.logger.info(f"Analyzing selection at {x}, {y}")
                    
                    # ============================================================
                    # STEP 1: Gemini Spatial Detection (Object + Bounding Box)
                    # ============================================================
                    detection = spatial_detector.get_object_bbox(
                        image_bytes, 
                        click_x=x, 
                        click_y=y,
                        image_width=width,
                        image_height=height
                    )
                    
                    label = detection["label"]
                    attributes = detection.get("attributes", {})
                    search_query = detection.get("search_query", label)
                    bbox_norm = detection.get("bbox_normalized", [0.3, 0.3, 0.7, 0.7])
                    
                    self.logger.info(f"Gemini detected: {label} {bbox_norm}")
                    
                    # ============================================================
                    # STEP 2: Smart Crop using Gemini Bounding Box
                    # ============================================================
                    crop = smart_crop(full_image, bbox_norm, padding=0.05)
                    
                    # Store crop as base64 for returning to UI if needed
                    crop_buffer = BytesIO()
                    crop.save(crop_buffer, format='PNG')
                    crop_base64 = base64.b64encode(crop_buffer.getvalue()).decode('utf-8')
                    
                    # ============================================================
                    # STEP 3: Parallel Search (Google Lens + Exa)
                    # ============================================================
                    all_products = []
                    
                    # --- 3A: Google Lens Reverse Image Search ---
                    if self.serp_client:
                        # Upload crop to ImgBB for public URL
                        public_url = self.upload_image_to_imgbb(crop_base64)
                        
                        if public_url:
                            self.logger.info(f"Searching Google Lens with public URL: {public_url}")
                            lens_results = self.serp_client.reverse_image_search_google_lens_url(public_url)
                            for lens_match in lens_results[:12]:
                                # Map to internal product format
                                all_products.append({
                                    "title": lens_match.get("title", "Unknown Product"),
                                    "url": lens_match.get("product_link") or lens_match.get("link", ""),
                                    "store": lens_match.get("source", "Unknown"),
                                    "thumbnail": lens_match.get("thumbnail", ""),
                                    "price": None,
                                    "price_str": str(lens_match.get("price") or ""),
                                    "description": lens_match.get("title", ""),
                                    "source_api": "google_lens",
                                    "relevance_score": 1.0,
                                    "images": [lens_match.get("thumbnail")] if lens_match.get("thumbnail") else []
                                })
                        else:
                            self.logger.warning("ImgBB upload failed, skipping Google Lens URL search")
                    
                    # --- 3B: Exa Neural Search ---
                    # Use dedicated search_utils for Exa (as per plan)
                    try:
                        from search_utils import search_exa_products
                        # Construct rich query from Gemini attributes
                        color = attributes.get("color", "")
                        material = attributes.get("material", "")
                        style = attributes.get("style", "")
                        exa_query = f"{color} {material} {style} {label}".strip()
                        self.logger.info(f"Searching Exa with query: {exa_query}")
                        
                        exa_results = search_exa_products(exa_query, num_results=8)
                        all_products.extend(exa_results)
                    except Exception as e:
                        self.logger.warning(f"Exa search failed: {e}")

                    # Deduplicate
                    all_products = self._dedupe_products_by_url(all_products)

                    # ============================================================
                    # STEP 4: CLIP Validation and Reranking
                    # ============================================================
                    if self.clip_client and self.clip_client.is_available() and all_products:
                        self.logger.info(f"Validating {len(all_products)} products with CLIP against label: '{label}'")
                        validated_products = self.clip_client.validate_products_by_label(
                            label=label,
                            products=all_products,
                            threshold=0.15, # Slightly lower threshold to be safe
                            top_k=8
                        )
                        # Only replace if validation didn't empty results aggressively
                        if validated_products:
                           all_products = validated_products
                    
                    # Limit final results
                    all_products = all_products[:12]
                    
                    # Create FurnitureAnalysisItem result
                    from models import FurnitureAnalysisItem
                    
                    # Map to FurnitureAnalysisItem structure (must match model exactly)
                    analysis_item = FurnitureAnalysisItem(
                        id=f"item_{int(time.time())}_{x}",
                        furniture_type=label,
                        confidence=detection.get("confidence", 0.9),
                        style=attributes.get("style", ""),
                        material=attributes.get("material", ""),
                        color=attributes.get("color", ""),
                        search_query=search_query,
                        products=all_products
                    )
                    
                    analysis_results.append(analysis_item.model_dump())
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing selection {selection}: {e}", exc_info=True)
                    # Continue to next selection even if one fails
            
            # Update Context (Optional depending on how frontend uses it)
            # We assume frontend just takes the response for now
            
            return {
                "project_id": project_id,
                "selections": analysis_results,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Batch furniture analysis failed: {e}", exc_info=True)
            log_external_api_call("batch", "analyze_furniture", 0, False)
            raise




    def upload_image_to_imgbb(self, image_base64: str) -> Optional[str]:
        """Upload a base64 image to ImgBB and return the public URL.
        
        Args:
            image_base64: Base64-encoded image data (without data:image prefix)
            
        Returns:
            Public URL of the uploaded image, or None if upload fails
        """
        import requests
        
        imgbb_key = os.getenv("IMGBB_API_KEY")
        if not imgbb_key:
            self.logger.warning("IMGBB_API_KEY not found in environment")
            return None
        
        try:
            # ImgBB API endpoint
            url = "https://api.imgbb.com/1/upload"
            
            # Prepare the payload
            payload = {
                "key": imgbb_key,
                "image": image_base64,
            }
            
            # Make the request
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            
            # Extract the URL
            result = response.json()
            if result.get("success"):
                image_url = result["data"]["url"]
                self.logger.info(f"✅ Uploaded image to ImgBB: {image_url}")
                return image_url
            else:
                self.logger.warning(f"ImgBB upload failed: {result}")
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to upload to ImgBB: {e}")
            return None

    def _format_reverse_search_results_for_claude(self, results: List[Dict]) -> str:
        """Format reverse search results for Claude analysis"""
        formatted = []
        for i, result in enumerate(results[:5]):  # Limit to top 5 for Claude
            formatted.append(f"""
            Result {i+1}:
            - Title: {result.get('title', 'Unknown')}
            - URL: {result.get('url', 'Unknown')}
            - Source: {result.get('source', 'Unknown')}
            - Price: {result.get('price', 'Unknown')}
            - Description: {result.get('description', 'No description')[:200]}...
            """)
        return "\n".join(formatted)

    def _parse_claude_enhanced_products(self, claude_response: str, original_results: List[Dict]) -> List[Dict]:
        """Parse Claude's enhanced product analysis and merge with original results"""
        try:
            import json
            
            # Try to extract JSON from Claude's response
            if "```json" in claude_response:
                json_str = claude_response.split("```json")[1].split("```")[0].strip()
            elif "```" in claude_response:
                json_str = claude_response.split("```")[1].split("```")[0].strip()
            else:
                json_str = claude_response
            
            enhanced_data = json.loads(json_str)
            
            # Merge enhanced data with original results
            enhanced_products = []
            for i, original in enumerate(original_results[:len(enhanced_data.get('products', []))]):
                enhanced = original.copy()
                
                if i < len(enhanced_data.get('products', [])):
                    claude_product = enhanced_data['products'][i]
                    
                    # Add Claude's enhancements
                    enhanced.update({
                        'claude_analysis': claude_product.get('analysis', ''),
                        'relevance_score': claude_product.get('relevance_score', 0.5),
                        'enhanced_description': claude_product.get('enhanced_description', enhanced.get('description', '')),
                        'recommended_features': claude_product.get('recommended_features', []),
                        'enhanced_by': 'claude'
                    })
                
                enhanced_products.append(enhanced)
            
            return enhanced_products
            
        except Exception as e:
            self.logger.warning(f"Failed to parse Claude enhanced products: {e}")
            # Return original results if parsing fails
            for result in original_results:
                result['enhanced_by'] = 'fallback'
            return original_results

    @log_api_call("reverse_search_batch")
    def reverse_search_batch(
        self,
        project_id: str,
        selections: List,
        image_type: str = "product",
    ) -> Dict[str, Any]:
        """Perform Google Lens reverse image search for each selection via SerpAPI.

        Steps:
        - Extract small crop around each selection
        - Upload crop to temporary file (local)
        - Optionally upload to imgbb-like service (skipped here); use local URL fallback
        - Call SerpAPI with engine=google_lens and url=<public or local url>
        - Return top matches per selection
        """
        try:
            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            project = projects[project_id]
            context = ProjectContext.model_validate(project["context"])

            # Choose source image
            if image_type == "inspiration":
                image_base64 = context.inspiration_generated_image_base64
            else:
                image_base64 = context.generated_image_base64

            if not image_base64:
                raise ValueError("No image available for reverse search")

            # Decode base64
            import base64
            from io import BytesIO
            from PIL import Image

            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            width, height = image.size

            results = []
            for sel in selections:
                # Crop 12% box around click
                box_size = 0.12
                x = sel.x if hasattr(sel, 'x') else sel.get('x', 0.5)
                y = sel.y if hasattr(sel, 'y') else sel.get('y', 0.5)
                left = max(0, int((x - box_size/2) * width))
                top = max(0, int((y - box_size/2) * height))
                right = min(width, int((x + box_size/2) * width))
                bottom = min(height, int((y + box_size/2) * height))
                crop = image.crop((left, top, right, bottom))

                # Save temporary crop
                temp_dir = DATA_FILE.parent / "images" / project_id / "reverse"
                temp_dir.mkdir(parents=True, exist_ok=True)
                sel_id = sel.id if hasattr(sel, 'id') else sel.get('id', 'sel')
                crop_path = temp_dir / f"lens_{sel_id}.png"
                crop.save(crop_path)

                # Prepare SerpAPI Google Lens call
                matches = []
                if self.serp_client:
                    try:
                        # Reuse serp_client but switch engine inside client method
                        from serp_client import SerpClient
                        serp = self.serp_client  # already configured
                        serp_results = serp.reverse_image_search_google_lens(str(crop_path))
                        # Normalize
                        for m in serp_results[:10]:
                            matches.append({
                                "title": m.get("title"),
                                "url": m.get("link") or m.get("product_link") or m.get("source") or None,
                                "source": m.get("source"),
                                "thumbnail": m.get("thumbnail"),
                            })
                    except Exception as e:
                        self.logger.warning(f"Reverse search failed for {sel_id}: {e}")

                results.append({
                    "id": sel_id,
                    "image_url": None,  # Could integrate imgbb for public URL
                    "matches": matches,
                })

            return {"results": results}

        except Exception as e:
            self.logger.error(f"Failed reverse_search_batch: {e}")
            raise

    @log_api_call("auto_detect_furniture")
    def auto_detect_furniture(
        self,
        project_id: str,
        image_type: str = "product",
    ) -> Dict[str, Any]:
        """Auto-detect furniture-like objects using YOLOv8 if available.

        Returns an array of normalized boxes and optional labels.
        """
        try:
            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            project = projects[project_id]
            context = ProjectContext.model_validate(project["context"])

            image_base64 = (
                context.inspiration_generated_image_base64
                if image_type == "inspiration"
                else context.generated_image_base64
            )
            if not image_base64:
                raise ValueError("No image available for auto detection")

            # Decode
            import base64
            from io import BytesIO
            from PIL import Image

            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            width, height = image.size

            detections: List[Dict[str, Any]] = []

            try:
                # Optional dependency
                from ultralytics import YOLO  # type: ignore

                # Use a lightweight model by default
                model = YOLO("yolov8n.pt")
                results = model.predict(image, imgsz=640, conf=0.35, verbose=False)
                if results:
                    r = results[0]
                    boxes = getattr(r, "boxes", None)
                    names = getattr(r, "names", None) or {}
                    if boxes is not None:
                        for b in boxes:
                            xyxy = b.xyxy[0].tolist()
                            cls = int(b.cls[0].item()) if hasattr(b, "cls") else -1
                            label = names.get(cls, "object") if isinstance(names, dict) else "object"
                            x1, y1, x2, y2 = xyxy
                            detections.append(
                                {
                                    "label": label,
                                    "rect": {
                                        "x": max(0.0, x1 / width),
                                        "y": max(0.0, y1 / height),
                                        "width": max(0.0, (x2 - x1) / width),
                                        "height": max(0.0, (y2 - y1) / height),
                                    },
                                    "center": {
                                        "x": ((x1 + x2) / 2) / width,
                                        "y": ((y1 + y2) / 2) / height,
                                    },
                                }
                            )
            except Exception as e:
                # Graceful fallback: no detections
                self.logger.warning(f"YOLO not available or failed: {e}")

            return {"detections": detections}

        except Exception as e:
            self.logger.error(f"Failed auto_detect_furniture: {e}")
            raise

    @log_api_call("replicate_segment")
    def replicate_segment(
        self,
        project_id: str,
        image_type: str = "product",
        public_image_url: str | None = None,
    ) -> Dict[str, Any]:
        """Run Mask2Former via Replicate and return normalized boxes.

        If public_image_url is not provided, we fall back to auto-detect YOLO.
        """
        try:
            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            from replicate_client import ReplicateSegmentationClient

            if not public_image_url:
                # Attempt to upload the current image to ImgBB to obtain a public URL
                try:
                    import base64
                    from io import BytesIO
                    from PIL import Image
                    import requests
                    imgbb_key = os.getenv("IMGBB_API_KEY")
                    if imgbb_key:
                        project = projects[project_id]
                        context = ProjectContext.model_validate(project["context"])
                        image_base64 = (
                            context.inspiration_generated_image_base64
                            if image_type == "inspiration"
                            else context.generated_image_base64
                        )
                        if not image_base64:
                            raise ValueError("No image available for Replicate upload")
                        # Build multipart form for imgbb
                        resp = requests.post(
                            "https://api.imgbb.com/1/upload",
                            data={"key": imgbb_key, "image": image_base64},
                            timeout=60,
                        )
                        if resp.ok:
                            payload = resp.json()
                            public_image_url = payload.get("data", {}).get("url")
                except Exception as e:
                    self.logger.warning(f"ImgBB upload failed, falling back to YOLO: {e}")
                    public_image_url = None
                if not public_image_url:
                    # Fallback: return YOLO detections
                    return self.auto_detect_furniture(project_id, image_type=image_type)

            client = ReplicateSegmentationClient()
            boxes = client.segment(public_image_url)

            # Normalize boxes (pixel -> 0..1)
            # We need image dimensions; load current image
            project = projects[project_id]
            context = ProjectContext.model_validate(project["context"])
            import base64
            from io import BytesIO
            from PIL import Image

            image_base64 = (
                context.inspiration_generated_image_base64
                if image_type == "inspiration"
                else context.generated_image_base64
            )
            if not image_base64:
                raise ValueError("No image available")
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            width, height = image.size

            detections: List[Dict[str, Any]] = []
            for b in boxes:
                bb = b.get("bbox")
                label = b.get("label", "object")
                if isinstance(bb, (list, tuple)) and len(bb) == 4:
                    x1, y1, x2, y2 = [float(v) for v in bb]
                    detections.append(
                        {
                            "label": label,
                            "rect": {
                                "x": max(0.0, x1 / width),
                                "y": max(0.0, y1 / height),
                                "width": max(0.0, (x2 - x1) / width),
                                "height": max(0.0, (y2 - y1) / height),
                            },
                            "center": {"x": ((x1 + x2) / 2) / width, "y": ((y1 + y2) / 2) / height},
                        }
                    )

            return {"detections": detections}

        except Exception as e:
            self.logger.error(f"Failed replicate segmentation: {e}")
            # Fallback to YOLO if Replicate fails
            try:
                return self.auto_detect_furniture(project_id, image_type=image_type)
            except Exception:
                return {"detections": []}

    def _find_best_box_for_click(
        self, click_x: float, click_y: float, detections: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching YOLO detection for a click point.
        
        Args:
            click_x: Normalized X coordinate (0-1)
            click_y: Normalized Y coordinate (0-1)
            detections: List of detection dicts with 'rect' keys
            
        Returns:
            The best matching detection or None.
            Prioritizes the smallest bounding box containing the point 
            (to select specific items like pillows over sofas).
        """
        matches = []
        for d in detections:
            r = d.get("rect")
            if not r:
                continue
            
            # Check if point is inside rect
            # rect: x, y, width, height (normalized)
            rx, ry, rw, rh = r["x"], r["y"], r["width"], r["height"]
            
            if (rx <= click_x <= rx + rw) and (ry <= click_y <= ry + rh):
                # Calculate area for sorting
                area = rw * rh
                matches.append((area, d))
        
        if not matches:
            return None
        
        # Sort by area ascending (smallest first)
        matches.sort(key=lambda x: x[0])
        return matches[0][1]

    def _generate_search_query(self, context: ProjectContext) -> str:
        """Generate an optimized search query based on the project context and selected recommendation"""
        try:
            from pydantic import BaseModel

            class SearchQuery(BaseModel):
                query: str
                reasoning: str

            # Build context for AI
            recs_text = ", ".join(context.selected_product_recommendations) if context.selected_product_recommendations else "furniture"
            context_info = f"""
            Space Type: {context.space_type}
            Selected Recommendations: {recs_text}
            """

            if context.improvement_markers:
                markers_summary = ", ".join(
                    [marker.description for marker in context.improvement_markers]
                )
                context_info += f"\nImprovement Areas: {markers_summary}"

            if context.inspiration_recommendations:
                style_summary = ", ".join(context.inspiration_recommendations[:2])
                context_info += f"\nStyle Preferences: {style_summary}"
            
            # Add color and style preferences
            if context.color_analysis:
                palette_name = context.color_analysis.get("palette_name", "")
                if palette_name:
                    context_info += f"\nColor Palette: {palette_name}"
            
            if context.style_analysis:
                style_name = context.style_analysis.get("style_name", "")
                if style_name:
                    context_info += f"\nDesign Style: {style_name}"
            
            # Add preferred stores
            if context.preferred_stores:
                context_info += f"\nPreferred Stores: {', '.join(context.preferred_stores[:3])}"

            prompt = f"""Generate a specific, optimized shopping search query to find products for this recommendation.

{context_info}

Create a search query that:
- Is specific enough to find the right type of product
- Includes relevant style/material hints from the context
- Is optimized for e-commerce sites like Wayfair, West Elm, etc.
- Is 3-8 words maximum
- Focuses on the most important product characteristics
- Avoids decor-only results (e.g., '-decor -ideas -how to style')
- Prefer furniture/product pages (tables, chairs, shelves, sofas, lamps, rugs, beds)

For example:
- If recommendation is "change sofa" and style is modern → "modern sectional sofa gray"
- If recommendation is "add coffee table" and space is small → "round coffee table wood small"
- If recommendation is "replace dining chairs" → "dining chairs set upholstered"

Generate the most effective search query for this scenario:"""

            result = self.gemini_client.get_structured_completion(
                prompt=prompt,
                pydantic_model=SearchQuery,
            )

            return f"{result.query} -decor -ideas"

        except Exception as e:
            print(f"Error generating search query: {e}")
            # Fallback to simple query
            recs_text = ", ".join(context.selected_product_recommendations) if context.selected_product_recommendations else "furniture"
            return f"{recs_text} {context.space_type} -decor -ideas"


    def _resolve_path(self, path_str: str) -> Path:
        """Resolve stored relative paths safely (handles leading data/)."""
        p = Path(path_str)
        if p.is_absolute():
            return p
        if path_str.startswith("data/"):
            return DATA_FILE.parent / path_str[5:]
        return DATA_FILE.parent / p

    def _ready_for_marker_recommendations(self, context: ProjectContext) -> bool:
        """Check if we have enough design context to generate marker recommendations."""
        return (
            context.base_image is not None
            and context.space_type is not None
            and len(context.improvement_markers) > 0
            and context.labelled_base_image is not None
            and (bool(context.color_analysis) or context.color_analysis_skipped)
            and (bool(context.style_analysis) or context.style_analysis_skipped)
            and bool(context.preferred_stores)
        )

    def _status_rank(self, status: str) -> int:
        """Return ordering index for statuses; unknown statuses rank last."""
        try:
            return STATUS_ORDER.index(status)
        except ValueError:
            return len(STATUS_ORDER)

    def _try_generate_marker_recommendations(self, project_id: str) -> None:
        """Generate marker recommendations once style/color/stores are set."""
        projects = self._load_projects()
        if project_id not in projects:
            return

        project = projects[project_id]
        context = ProjectContext.model_validate(project["context"])

        # Already generated
        if project["status"] == "MARKER_RECOMMENDATIONS_READY" and context.marker_recommendations:
            return

        # Avoid downgrading projects that have progressed beyond marker recommendations
        allowed_statuses = {
            "SPACE_TYPE_SELECTED",
            MARKERS_SAVED_STATUS,
            "MARKER_RECOMMENDATIONS_READY",
        }
        if project["status"] not in allowed_statuses:
            return

        if not self._ready_for_marker_recommendations(context):
            return

        # Ensure labelled image path exists
        labelled_path = self._resolve_path(context.labelled_base_image)
        if not labelled_path.exists():
            self.logger.warning(f"Labelled image not found at {labelled_path}")
            return

        # Generate recommendations
        recs = self._generate_marker_recommendations(
            context.space_type or "space",
            context.improvement_markers,
            str(labelled_path),
            context,
        )

        updated_context = context.model_copy(
            update={"marker_recommendations": recs}
        )
        projects[project_id]["context"] = updated_context.model_dump()
        projects[project_id]["status"] = "MARKER_RECOMMENDATIONS_READY"
        self._save_projects(projects)

    def trigger_marker_recommendations(self, project_id: str) -> List[str]:
        """Explicitly generate marker-based recommendations after gating criteria are met."""
        projects = self._load_projects()
        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        project = projects[project_id]
        context = ProjectContext.model_validate(project["context"])

        if not self._ready_for_marker_recommendations(context):
            raise ValueError("Project is not ready for marker recommendations. Please ensure base image, space type, labelled markers, color analysis, style analysis, and preferred stores are set.")

        labelled_path = self._resolve_path(context.labelled_base_image)
        if not labelled_path.exists():
            raise ValueError(f"Labelled image not found at {labelled_path}")

        recs = self._generate_marker_recommendations(
            context.space_type or "space",
            context.improvement_markers,
            str(labelled_path),
            context,
        )

        updated_context = context.model_copy(update={"marker_recommendations": recs})
        projects[project_id]["context"] = updated_context.model_dump()

        current_rank = self._status_rank(project["status"])
        marker_rank = self._status_rank("MARKER_RECOMMENDATIONS_READY")
        if current_rank < marker_rank:
            projects[project_id]["status"] = "MARKER_RECOMMENDATIONS_READY"
        self._save_projects(projects)
        return recs


# Global instance
data_manager = DataManager()
