from __future__ import annotations
import hashlib
import json
import logging
import os
import random
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from cache_manager import cache_manager

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
from affiliate_client import AffiliateClient

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
        """Deduplicate products by product_id (preferred) or normalized URL.

        Uses product_id as primary key since Google Shopping returns redirect URLs
        that all normalize to similar bases, causing false duplicates.
        """
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
            # Prefer product_id for deduplication (unique per product from SERP)
            product_id = p.get("id") or p.get("product_id") or ""
            if product_id:
                key = f"pid:{product_id}"
            else:
                # Fallback to URL normalization + title for uniqueness
                url = p.get("url") or ""
                title = p.get("title", "")[:50]  # First 50 chars of title
                key = f"{normalize(url)}|{title.lower()}"

            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped.append(p)
        return deduped

    def _validate_product_pages_with_exa(
        self,
        products: List[Dict[str, Any]],
        max_validate: int = 15,
        min_valid_threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Validate that product URLs are actual product pages using Exa.

        Uses Exa's get_contents() to fetch pages and check for shopping signals.
        Filters out non-product pages (blogs, category pages, search results).

        IMPORTANT: Never falls back to unfiltered results. Returns fewer results
        rather than non-retailer URLs.

        Args:
            products: List of product dicts with 'url' field
            max_validate: Maximum URLs to validate (rest pass through)
            min_valid_threshold: Minimum valid products (informational only)

        Returns:
            Filtered list with only validated product pages from real retailers
        """
        from config import is_blocked_domain

        if not products:
            return products

        # Pre-filter: Remove blocked non-retailer domains BEFORE Exa validation
        pre_filtered = []
        blocked_count = 0
        for p in products:
            url = p.get("url", "")
            if is_blocked_domain(url):
                blocked_count += 1
                self.logger.debug(f"Pre-filtered blocked domain: {url[:60]}...")
            else:
                pre_filtered.append(p)

        if blocked_count > 0:
            self.logger.info(f"Pre-filtered {blocked_count} blocked non-retailer domains")

        products = pre_filtered

        if not self.exa_client:
            self.logger.warning("Exa client not available, returning domain-filtered results only")
            return products

        if not products:
            return products

        to_validate = products[:max_validate]
        remainder = products[max_validate:]

        # Extract URLs for batch validation
        urls_to_check = [p.get("url", "") for p in to_validate if p.get("url")]

        if not urls_to_check:
            return products

        try:
            # Use Exa's batch validation
            validation_results = self.exa_client.validate_product_urls_batch(
                urls=urls_to_check,
                batch_size=5,
                max_chars=2000
            )

            # Filter products based on validation results
            validated = []
            for product in to_validate:
                url = product.get("url", "")
                if url in validation_results:
                    result = validation_results[url]
                    if result.get("is_valid"):
                        product["exa_validated"] = True
                        product["has_shopping_signals"] = result.get("has_shopping_signals", False)
                        validated.append(product)
                    else:
                        # Log why it failed
                        self.logger.debug(
                            f"URL failed Exa validation: {url[:60]}... "
                            f"(is_product={result.get('is_product_page')}, "
                            f"valid_retailer={result.get('is_valid_retailer')}, "
                            f"shopping_signals={result.get('has_shopping_signals')})"
                        )
                else:
                    # URL wasn't checked (shouldn't happen), include with warning
                    product["exa_validated"] = False
                    validated.append(product)

            # CHANGED: Never fallback to unfiltered results
            # Better to show fewer results than Instagram/blogs
            if len(validated) < min_valid_threshold:
                self.logger.warning(
                    f"Only {len(validated)}/{len(to_validate)} URLs passed Exa validation "
                    f"(below threshold of {min_valid_threshold}). "
                    f"Returning {len(validated)} validated results (NOT falling back to unfiltered)."
                )

            self.logger.info(
                f"Exa validation: {len(validated)}/{len(to_validate)} URLs passed as valid product pages"
            )

            # Add remainder (unvalidated but domain-filtered) at the end
            return validated + remainder

        except Exception as e:
            self.logger.error(f"Exa validation failed entirely: {e}")
            # Even on error, don't return products without domain filtering
            # The products are already domain-filtered from pre-filtering above
            return products

    def _prepare_crop_for_search(self, crop, target_size: int = 512):
        """Prepare crop for optimal reverse image search quality.

        Args:
            crop: PIL Image crop of the furniture item
            target_size: Minimum dimension for Google Lens (recommended 512px)

        Returns:
            Optimized PIL Image ready for reverse image search
        """
        from PIL import Image, ImageEnhance

        # 1. Ensure minimum size for Google Lens (recommended 512px)
        w, h = crop.size
        if max(w, h) < target_size:
            scale = target_size / max(w, h)
            crop = crop.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            print(f"   📐 Upscaled crop from {w}x{h} to {crop.size[0]}x{crop.size[1]}")

        # 2. Convert to RGB (remove alpha channel if present)
        if crop.mode != 'RGB':
            crop = crop.convert('RGB')

        # 3. Enhance contrast slightly for better feature detection
        enhancer = ImageEnhance.Contrast(crop)
        crop = enhancer.enhance(1.1)  # Subtle 10% contrast boost

        return crop

    def _pil_to_base64(self, image: "Image.Image", format: str = "PNG") -> str:
        """Convert PIL Image to base64 string.

        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)

        Returns:
            Base64 encoded string of the image
        """
        from io import BytesIO
        import base64

        buffer = BytesIO()
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

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

    def _generate_multi_queries(self, label: str, attributes: Dict) -> List[str]:
        """Generate multiple search queries for better coverage of distinctive items.

        Args:
            label: The detected furniture label (e.g., "upholstered bed")
            attributes: Detected attributes dict with color, material, style

        Returns:
            List of 1-3 search queries for the item
        """
        queries = []
        label_lower = label.lower()

        color = attributes.get("color", "")
        material = attributes.get("material", "")
        style = attributes.get("style", "")

        # Query 1: Full descriptive (existing behavior)
        full_parts = [p for p in [color, material, style, label] if p]
        full_query = " ".join(full_parts).strip()
        if full_query:
            queries.append(full_query)

        # Query 2: Feature-focused (for distinctive items like beds)
        if "bed" in label_lower and "bedding" not in label_lower:
            features = []
            # Extract distinctive features from label and material
            if "upholstered" in label_lower or "fabric" in material.lower() if material else False:
                features.append("upholstered")
            if "wingback" in label_lower or "wing" in label_lower:
                features.append("wingback")
            if "tufted" in label_lower or "channel" in label_lower:
                features.append("channel tufted")
            if "canopy" in label_lower:
                features.append("canopy")
            if "platform" in label_lower:
                features.append("platform")

            if features and color:
                feature_query = f"{color} {' '.join(features)} bed frame"
                if feature_query not in queries:
                    queries.append(feature_query)

        # Query 3: Style + type (e.g., "modern art deco bed")
        if style and style.lower() not in full_query.lower():
            style_query = f"{style} {label}"
            if color:
                style_query = f"{color} {style_query}"
            if style_query not in queries:
                queries.append(style_query)

        # Query 4: Simplified (color + type only) as fallback
        simple_query = f"{color} {label}".strip() if color else label
        if simple_query not in queries:
            queries.append(simple_query)

        # Deduplicate and limit to 3 queries
        seen = set()
        unique_queries = []
        for q in queries:
            q_normalized = " ".join(q.lower().split())
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q)

        return unique_queries[:3]

    def _type_guard(self, title: str, target_type: str) -> bool:
        """Allow only titles that match the target type family and reject decor/how-to.

        Uses enhanced synonym matching and hard negative filtering when feature flag is enabled.
        """
        t = title.lower()
        tt = target_type.lower()

        # Check feature flag for enhanced type guard
        try:
            from config import FeatureFlags, FURNITURE_SYNONYMS, HARD_NEGATIVES
            use_enhanced = FeatureFlags.ENHANCED_TYPE_GUARD
        except ImportError:
            use_enhanced = False
            FURNITURE_SYNONYMS = {}
            HARD_NEGATIVES = []

        if use_enhanced:
            # Enhanced hard negative filtering
            if any(neg in t for neg in HARD_NEGATIVES):
                return False

            # Extended category mapping with comprehensive synonyms
            type_map = {
                "shelf": ["shelf", "shelving", "bookcase", "bookshelf", "wall shelf", "floating shelf", "etagere", "étagère"],
                "console table": ["console table", "sofa table", "entry table", "hallway table", "entryway table", "console"],
                "table": ["table", "dining table", "coffee table", "cocktail table", "side table", "end table", "accent table", "desk"],
                "coffee table": ["coffee table", "cocktail table", "tea table"],
                "side table": ["side table", "end table", "accent table", "lamp table"],
                "nightstand": ["nightstand", "bedside table", "night table", "bedside stand"],
                "bench": ["bench", "ottoman", "entry bench", "settee", "banquette", "footstool", "pouf"],
                "ottoman": ["ottoman", "footstool", "pouf", "hassock", "footrest"],
                "chair": ["chair", "armchair", "accent chair", "dining chair", "desk chair", "lounge chair", "club chair", "recliner"],
                "armchair": ["armchair", "accent chair", "lounge chair", "club chair", "arm chair"],
                "sofa": ["sofa", "couch", "sectional", "loveseat", "settee", "sleeper sofa", "sofa bed"],
                "sectional": ["sectional", "sectional sofa", "modular sofa", "l-shaped sofa"],
                "bed": ["bed", "platform bed", "bed frame", "headboard", "bedframe", "sleigh bed", "canopy bed"],
                "lamp": ["lamp", "floor lamp", "table lamp", "desk lamp", "sconce", "light", "lighting"],
                "floor lamp": ["floor lamp", "standing lamp", "torchiere", "arc lamp"],
                "table lamp": ["table lamp", "desk lamp", "bedside lamp"],
                "dresser": ["dresser", "chest of drawers", "bureau", "chest", "highboy", "lowboy"],
                "cabinet": ["cabinet", "sideboard", "buffet", "credenza", "hutch", "cupboard", "armoire"],
                "storage": ["cabinet", "dresser", "sideboard", "buffet", "storage", "credenza", "chest"],
                "tv stand": ["tv stand", "media console", "entertainment center", "media cabinet", "tv console", "media stand"],
                "rug": ["rug", "area rug", "runner", "carpet", "mat"],
                "desk": ["desk", "writing desk", "computer desk", "work desk", "secretary desk", "office desk"],
                "stool": ["stool", "bar stool", "counter stool", "barstool"],
            }

            # Add dynamic synonyms from config
            for key, synonyms in FURNITURE_SYNONYMS.items():
                if key not in type_map:
                    type_map[key] = [key] + synonyms
                else:
                    # Merge with existing
                    existing = set(type_map[key])
                    existing.update(synonyms)
                    type_map[key] = list(existing)

        else:
            # Original implementation (fallback)
            negatives = ["decor", "how to", "ideas", "tutorial", "guide", "inspiration", "poster", "print"]
            if any(neg in t for neg in negatives):
                return False

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
            from PIL import Image, ImageDraw, ImageFont, ImageOps

            # Load original image and create a copy
            original_img = Image.open(base_image_path)
            original_img = ImageOps.exif_transpose(original_img)
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
    def create_project(self, user_id: str | None = None) -> str:
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

    def get_project(self, project_id: str, user_id: str | None = None) -> dict | None:
        """Get a project by ID"""
        projects = self._load_projects()
        return projects.get(project_id)

    def get_all_projects(self, user_id: str | None = None) -> dict:
        """Get all projects"""
        return self._load_projects()

    def delete_project(self, project_id: str, user_id: str | None = None) -> bool:
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

        # Normalize EXIF orientation so downstream code sees upright pixels
        try:
            from PIL import Image, ImageOps
            with Image.open(image_path) as img:
                original_size = img.size
                transposed = ImageOps.exif_transpose(img)
                if transposed is not None and transposed is not img:
                    # Determine format from file extension
                    ext = str(image_path).rsplit('.', 1)[-1].lower()
                    if ext in ('jpg', 'jpeg'):
                        if transposed.mode in ('RGBA', 'P'):
                            transposed = transposed.convert('RGB')
                        transposed.save(image_path, format='JPEG', quality=95)
                    else:
                        transposed.save(image_path)
                    self.logger.info(
                        f"EXIF transpose: {original_size} -> {transposed.size}"
                    )
                else:
                    self.logger.info(f"EXIF transpose: no rotation needed ({original_size})")
        except Exception as e:
            self.logger.warning(f"EXIF transpose at upload failed (non-fatal): {e}")

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

    def set_improvement_mode(self, project_id: str, mode: str) -> str:
        """Set the improvement mode for a project (iterative or complete_revamp)"""
        projects = self._load_projects()

        if project_id not in projects:
            raise ValueError(f"Project {project_id} not found")

        # Validate mode
        if mode not in ("iterative", "complete_revamp"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'iterative' or 'complete_revamp'")

        # Update project with improvement mode
        current_context = ProjectContext.model_validate(projects[project_id]["context"])
        updated_context = current_context.model_copy(update={"improvement_mode": mode})

        projects[project_id]["context"] = updated_context.model_dump()
        # Status stays the same - this is just a preference setting

        self._save_projects(projects)

        # Clear logging for debugging
        print("\n" + "="*70)
        print("🎛️ IMPROVEMENT MODE SET")
        print("="*70)
        print(f"📋 Project ID: {project_id}")
        print(f"✅ Mode set to: '{mode}'")
        if mode == "iterative":
            print("   → Will use ITERATIVE prompt (surgical edits, no color/style changes)")
        else:
            print("   → Will use INTEGRATION prompt (full redesign with color/style)")
        print("="*70 + "\n")

        self.logger.info(f"Set improvement mode to '{mode}' for project {project_id}")
        return mode

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
                # Filter out products without valid images
                images = p.get("images", [])
                if not images or len(images) == 0:
                    continue
                # Check first image is valid (not placeholder)
                first_image = images[0] if images else ""
                bad_patterns = ["placeholder", ".svg", "no-image", "default", "blank", "empty", "missing"]
                if any(pat in first_image.lower() for pat in bad_patterns):
                    continue
                filtered_products.append(p)

            # Limit to 4 quality products with images
            filtered_products = filtered_products[:4]

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

    # ========================================================================
    # "Like These?" Product Suggestions Feature
    # ========================================================================

    # Decor-specific search templates for better product results
    DECOR_SEARCH_TEMPLATES = {
        "wall art": "{style} wall art canvas print framed artwork home decor",
        "art": "{style} wall art canvas print framed artwork home decor",
        "geometric art": "{style} geometric wall art canvas print abstract modern",
        "rug": "{style} area rug carpet floor mat {color}",
        "geometric rug": "{style} geometric pattern area rug modern carpet",
        "vase": "{style} decorative vase ceramic glass flower vase home decor",
        "lamp": "{style} lamp lighting fixture {color}",
        "floor lamp": "{style} floor lamp standing lamp modern lighting",
        "table lamp": "{style} table lamp desk lamp bedside lighting",
        "mirror": "{style} wall mirror decorative mirror home decor",
        "plant": "artificial plant faux greenery indoor plant decor",
        "throw pillow": "{style} throw pillow decorative cushion {color}",
        "curtain": "{style} curtain drapes window treatment {color}",
        "shelf": "{style} wall shelf floating shelf storage decor",
        "clock": "{style} wall clock decorative clock modern",
    }

    def _select_best_recommendations(
        self,
        context: ProjectContext,
        max_count: int = 2
    ) -> List[str]:
        """
        Auto-select the best recommendations based on style analysis.
        Prioritizes items that match the selected design style.

        Args:
            context: Project context with recommendations and analysis
            max_count: Maximum recommendations to select (default 2)

        Returns:
            List of top recommendations based on style match
        """
        recommendations = context.product_recommendations or []
        if len(recommendations) <= max_count:
            return recommendations

        # Get style furniture recommendations if available
        style_items = []
        if context.style_analysis and isinstance(context.style_analysis, dict):
            furniture_recs = context.style_analysis.get("furniture_recommendations", [])
            for rec in furniture_recs:
                if isinstance(rec, dict):
                    item_type = rec.get("item_type", "").lower()
                    if item_type:
                        style_items.append(item_type)

        # Score each recommendation
        scored = []
        for rec in recommendations:
            rec_lower = rec.lower()
            score = 0

            # Check if matches style furniture recommendations
            for style_item in style_items:
                if style_item in rec_lower:
                    score += 10  # High priority for style match

            # Boost high-impact furniture items
            high_impact = ["sofa", "bed", "table", "desk", "chair", "bookcase", "dresser"]
            for item in high_impact:
                if item in rec_lower:
                    score += 5

            # Boost decor items for visual interest
            decor_items = ["art", "lamp", "rug", "mirror", "plant"]
            for item in decor_items:
                if item in rec_lower:
                    score += 3

            scored.append((rec, score))

        # Sort by score descending and take top N
        scored.sort(key=lambda x: x[1], reverse=True)
        return [rec for rec, score in scored[:max_count]]

    def _validate_product_links(self, products: List[Dict], max_validate: int = 5) -> List[Dict]:
        """Validate that product URLs lead to actual product pages."""
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def check_link(product):
            url = product.get("url", "")
            if not url:
                return product, False
            try:
                # Quick HEAD request to check if URL works
                resp = requests.head(url, timeout=3, allow_redirects=True)
                # Check for valid response and not error page
                is_valid = resp.status_code == 200
                product["link_validated"] = is_valid
                return product, is_valid
            except:
                product["link_validated"] = False
                return product, False

        validated = []
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(check_link, p): p for p in products[:max_validate]}
                for future in as_completed(futures, timeout=10):
                    try:
                        product, is_valid = future.result()
                        if is_valid:
                            validated.append(product)
                    except:
                        pass
        except:
            # If validation fails entirely, return original products
            return products

        # Add remaining unvalidated products
        validated.extend(products[max_validate:])
        return validated

    def _filter_products_with_images(
        self,
        products: List[Dict[str, Any]],
        min_count: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Filter products ensuring they have valid images.
        Checks multiple image fields and normalizes to image_url.
        Always returns at least min_count products, supplementing with
        non-image products if needed.
        """
        def get_image(p):
            """Get best available image from multiple possible fields."""
            return (
                p.get("image_url") or
                p.get("thumbnail") or
                (p.get("images") or [None])[0] or
                p.get("image")
            )

        # Categorize products by image quality
        with_good_images = []
        with_any_images = []
        without_images = []

        bad_patterns = [
            "placeholder", ".svg", "no-image", "default",
            "blank", "empty", "missing"
        ]

        for p in products:
            img = get_image(p)
            if img and len(img) > 10:
                # Normalize to image_url for consistent frontend access
                p["image_url"] = img
                is_bad = any(pat in img.lower() for pat in bad_patterns)
                if not is_bad:
                    with_good_images.append(p)
                else:
                    with_any_images.append(p)
            else:
                without_images.append(p)

        # Log image quality breakdown
        print(f"[IMAGE_FILTER] Input: {len(products)} products")
        print(f"[IMAGE_FILTER]   - Good images: {len(with_good_images)}")
        print(f"[IMAGE_FILTER]   - Bad pattern images: {len(with_any_images)}")
        print(f"[IMAGE_FILTER]   - No images: {len(without_images)}")

        # Build result list prioritizing good images
        result = with_good_images[:min_count]

        # If we need more, add from other categories
        if len(result) < min_count:
            needed = min_count - len(result)
            result.extend(with_any_images[:needed])

        # Don't add products without images - they show as placeholders in the UI
        if len(result) < min_count:
            print(f"[IMAGE_FILTER] ⚠️ Only {len(result)} products with images available (requested {min_count})")

        print(f"[IMAGE_FILTER] Output: {len(result)} products (min_count={min_count})")
        return result

    def _curate_products_with_ai(
        self,
        products: List[Dict[str, Any]],
        category: str,
        style: str = "",
        room_type: str = "",
        max_products: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Use Gemini Vision to evaluate and rank products by visual quality and aesthetics.
        
        Evaluates:
        1. Visual quality - Image clarity, professional photography
        2. Design aesthetic - Modern, premium look vs generic
        3. Style match - How well it fits the requested style/room
        
        Args:
            products: List of product dicts with image_url
            category: Product category (e.g., "accent chair", "wall art")
            style: Requested style (e.g., "modern", "mid-century")
            room_type: Room type for context (e.g., "living room", "bedroom")
            max_products: Maximum products to return
            
        Returns:
            Products sorted by AI quality score, filtered below threshold
        """
        from config import AI_PRODUCT_CURATION, QUALITY_RETAILER_SCORES
        import requests
        from io import BytesIO
        from PIL import Image
        import base64
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        if not AI_PRODUCT_CURATION.get("enabled", True):
            self.logger.info("AI product curation disabled, returning unfiltered products")
            return products[:max_products]
        
        if not products:
            return []
        
        # Limit products to evaluate (cost control)
        max_eval = AI_PRODUCT_CURATION.get("max_products_to_evaluate", 16)
        products_to_eval = products[:max_eval]
        
        self.logger.info(f"AI curation: evaluating {len(products_to_eval)} products for '{category}'")
        print(f"[AI_CURATION] Starting AI curation for {len(products_to_eval)} products")
        print(f"[AI_CURATION]   Category: {category}, Style: {style}, Room: {room_type}")
        
        # Step 1: Download product images in parallel
        def download_image(product: Dict) -> tuple:
            """Download and encode product image."""
            image_url = product.get("image_url", "") or ""
            if not image_url or len(image_url) < 10:
                return product, None
            try:
                response = requests.get(image_url, timeout=5)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    # Skip tiny images
                    min_dim = AI_PRODUCT_CURATION.get("min_image_dimension", 200)
                    if img.width < min_dim or img.height < min_dim:
                        return product, None
                    # Resize to save bandwidth
                    img.thumbnail((400, 400))
                    buffer = BytesIO()
                    img.convert("RGB").save(buffer, format="JPEG", quality=80)
                    img_b64 = base64.b64encode(buffer.getvalue()).decode()
                    return product, img_b64
            except Exception as e:
                self.logger.warning(f"Failed to download image {image_url[:50]}: {e}")
            return product, None
        
        # Download images in parallel
        products_with_images = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(download_image, p): p for p in products_to_eval}
            for future in as_completed(futures):
                product, img_b64 = future.result()
                if img_b64:
                    products_with_images.append((product, img_b64))
        
        if not products_with_images:
            self.logger.warning("AI curation: No products had valid images, returning original list")
            return products[:max_products]
        
        print(f"[AI_CURATION] Downloaded {len(products_with_images)} product images")
        
        # Step 2: Get store quality scores as initial boost
        for product, _ in products_with_images:
            store = (product.get("store") or "").lower()
            store_score = QUALITY_RETAILER_SCORES.get(store, QUALITY_RETAILER_SCORES.get("default", 0.7))
            product["_store_quality"] = store_score
        
        # Step 3: Use Gemini to evaluate batches
        batch_size = AI_PRODUCT_CURATION.get("batch_size", 8)
        all_scored = []
        
        for batch_start in range(0, len(products_with_images), batch_size):
            batch = products_with_images[batch_start:batch_start + batch_size]
            
            try:
                scored_batch = self._evaluate_product_batch_with_gemini(
                    batch, category, style, room_type
                )
                all_scored.extend(scored_batch)
            except Exception as e:
                self.logger.error(f"Gemini batch evaluation failed: {e}")
                # Fallback: use store quality score only
                for product, _ in batch:
                    product["_ai_score"] = product.get("_store_quality", 0.7)
                    all_scored.append(product)
        
        # Step 4: Sort by combined score and filter
        min_score = AI_PRODUCT_CURATION.get("min_quality_score", 0.5)
        
        def get_final_score(p):
            ai_score = p.get("_ai_score", 0.5)
            store_score = p.get("_store_quality", 0.7)
            # Weighted combination: AI 70%, Store 30%
            return ai_score * 0.7 + store_score * 0.3
        
        # Add final score and sort
        for p in all_scored:
            p["_final_score"] = get_final_score(p)
        
        all_scored.sort(key=lambda p: p.get("_final_score", 0), reverse=True)
        
        # Filter and limit
        filtered = [p for p in all_scored if p.get("_final_score", 0) >= min_score]
        
        # Ensure minimum products (don't filter too aggressively)
        if len(filtered) < 3 and len(all_scored) >= 3:
            filtered = all_scored[:max(3, len(filtered))]
        
        result = filtered[:max_products]
        
        # Clean up internal score fields from output (optional)
        for p in result:
            p.pop("_store_quality", None)
            p.pop("_ai_score", None)
            p.pop("_final_score", None)
        
        print(f"[AI_CURATION] Final result: {len(result)} curated products")
        self.logger.info(f"AI curation complete: {len(result)} products returned")
        
        return result
    
    def _evaluate_product_batch_with_gemini(
        self,
        batch: List[tuple],  # List of (product, img_b64) tuples
        category: str,
        style: str,
        room_type: str
    ) -> List[Dict[str, Any]]:
        """
        Evaluate a batch of products using Gemini Vision.
        
        Returns products with _ai_score added.
        """
        from pydantic import BaseModel, Field
        from typing import List as TypeList
        
        if not batch:
            return []
        
        # Build prompt with product info
        class ProductScore(BaseModel):
            index: int = Field(description="Product index (0-based)")
            quality_score: float = Field(
                description="Visual/design quality score 0.0-1.0. Consider: image clarity, "
                "professional photography, modern/premium aesthetic, uniqueness"
            )
            style_match: float = Field(
                description="How well it matches the requested style 0.0-1.0"
            )
            reasoning: str = Field(description="Brief reason for scores")
        
        class ProductEvaluationResponse(BaseModel):
            scores: TypeList[ProductScore]
        
        # Prepare images and product info for prompt
        image_parts = []
        product_info = []
        for i, (product, img_b64) in enumerate(batch):
            image_parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": img_b64
                }
            })
            title = product.get("title", "Unknown")[:80]
            store = product.get("store", "Unknown")
            product_info.append(f"Product {i}: {title} (from {store})")
        
        style_desc = style if style else "modern, aesthetic"
        room_desc = room_type if room_type else "any room"
        
        prompt = f"""Evaluate these {len(batch)} product images for a {category} in a {room_desc}.
Requested style: {style_desc}

Products:
{chr(10).join(product_info)}

For each product, score:
1. quality_score (0.0-1.0): Visual quality - professional photography, image clarity, premium/modern look, not generic/cheap-looking
2. style_match (0.0-1.0): How well it matches the "{style_desc}" style and would fit in a {room_desc}

Score honestly - reject poor quality images (blurry, amateur), generic/basic designs, items that don't match the style.
Prefer: Clear photos, unique designs, trending aesthetics, professional product shots.
"""
        
        try:
            result = self.gemini_client.analyze_images_with_vision(
                prompt=prompt,
                pydantic_model=ProductEvaluationResponse,
                image_parts=image_parts,
                system_message="You are an expert interior designer evaluating product quality and style. Be critical - only high-quality, aesthetically pleasing products deserve scores above 0.7."
            )
            
            # Map scores back to products
            score_map = {s.index: s for s in result.scores}
            scored_products = []
            
            for i, (product, _) in enumerate(batch):
                if i in score_map:
                    score_data = score_map[i]
                    # Combine quality and style match
                    from config import AI_PRODUCT_CURATION
                    weights = AI_PRODUCT_CURATION.get("score_weights", {})
                    quality_weight = weights.get("visual_quality", 0.35) + weights.get("design_aesthetic", 0.35)
                    style_weight = weights.get("style_match", 0.30)
                    
                    combined = (score_data.quality_score * quality_weight + 
                               score_data.style_match * style_weight)
                    product["_ai_score"] = combined
                    print(f"[AI_CURATION]   Product {i}: quality={score_data.quality_score:.2f}, "
                          f"style={score_data.style_match:.2f}, combined={combined:.2f}")
                else:
                    product["_ai_score"] = 0.5  # Default if not scored
                
                scored_products.append(product)
            
            return scored_products
            
        except Exception as e:
            self.logger.error(f"Gemini product evaluation failed: {e}")
            # Fallback: return with default scores
            for product, _ in batch:
                product["_ai_score"] = 0.5
            return [p for p, _ in batch]

    def auto_select_best_product(
        self,
        project_id: str,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Auto-select the best product from search results based on scoring criteria:
        - CLIP similarity score (visual match to room)
        - Image availability and quality
        - Store trust rating
        - Price availability

        Returns the selected product and alternatives.
        """
        if not products:
            raise ValueError("No products to select from")

        # Score each product
        scored_products = []
        for p in products:
            score = 0.0
            reasons = []

            # 1. CLIP similarity score (highest weight)
            similarity = p.get("similarity_score", 0) or p.get("relevance_score", 0.5)
            score += similarity * 50  # Up to 50 points
            if similarity >= 0.8:
                reasons.append("high visual match")

            # 2. Image availability (required)
            images = p.get("images", [])
            if images and len(images) > 0 and len(images[0]) > 10:
                score += 20  # 20 points for having image
                reasons.append("clear product image")
            else:
                score -= 100  # Heavily penalize no image

            # 3. Store trust rating
            store_trust = p.get("store_trust", 0.5)
            score += store_trust * 15  # Up to 15 points
            if store_trust >= 0.85:
                reasons.append("trusted retailer")

            # 4. Price availability
            price = p.get("price")
            if price and price > 0:
                score += 10  # 10 points for having price
                reasons.append("price available")

            # 5. Rating bonus
            rating = p.get("rating", 0)
            if rating and rating >= 4.0:
                score += 5
                reasons.append(f"highly rated ({rating})")

            scored_products.append({
                "product": p,
                "score": score,
                "reasons": reasons
            })

        # Sort by score descending
        scored_products.sort(key=lambda x: x["score"], reverse=True)

        # Best product is first
        best = scored_products[0]
        selected_product = best["product"]
        selection_reason = ", ".join(best["reasons"]) if best["reasons"] else "best overall match"

        # Alternatives are the rest
        alternatives = [sp["product"] for sp in scored_products[1:4]]  # Up to 3 alternatives

        # Store selection in project context
        projects = self._load_projects()
        if project_id in projects:
            context = projects[project_id].get("context", {})
            context["auto_selected_product"] = selected_product
            context["auto_selected_reason"] = selection_reason
            projects[project_id]["context"] = context
            self._save_projects(projects)

        return {
            "selected_product": selected_product,
            "selection_reason": selection_reason,
            "alternatives": alternatives
        }

    @log_api_call("search_products_for_recommendations")
    def search_products_for_recommendations(
        self,
        project_id: str,
        recommendations: List[str]
    ) -> Dict[str, Any]:
        """
        Search for real products for each selected recommendation.
        Uses SERP API / Exa to find products from the web in parallel.
        Auto-selects top 2 recommendations if more are provided.

        Args:
            project_id: The project ID
            recommendations: List of recommendations like ["Add Velvet Bed", "Hang Geometric Art"]

        Returns:
            Dict with categories, each containing products
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
        from datetime import datetime

        try:
            self.logger.info(
                "Starting product search for recommendations",
                extra={"project_id": project_id, "recommendations": recommendations}
            )

            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            if not self.serp_client and not self.exa_client:
                raise ValueError(
                    "No product search client available - configure SERP_API_KEY or EXA_API_KEY"
                )

            # Limit to 2 categories, auto-select best if more provided
            if len(recommendations) > 2:
                recommendations = self._select_best_recommendations(context, max_count=2)
                self.logger.info(f"Auto-selected top 2 recommendations: {recommendations}")

            # Search for products for each recommendation in parallel
            categories = []
            MAX_WORKERS = 4
            MAX_PRODUCTS_TO_FETCH = 30  # Fetch more to ensure 4+ survive filtering
            MIN_PRODUCTS_WITH_IMAGES = 4

            def search_single_recommendation(recommendation: str) -> Dict[str, Any]:
                """Search products for a single recommendation using multiple query variations."""
                try:
                    t_rec_start = time.time()
                    # Clean up the recommendation for query building
                    rec_lower = recommendation.lower()
                    for prefix in ["add ", "change ", "replace ", "install ", "hang ", "place "]:
                        if rec_lower.startswith(prefix):
                            rec_lower = rec_lower[len(prefix):]
                            break

                    # Get style name for queries
                    style_name = ""
                    if context.style_analysis and isinstance(context.style_analysis, dict):
                        style_name = context.style_analysis.get("style_name", "modern")

                    # Generate multiple query variations for better coverage
                    query_variations = [
                        f"trending {rec_lower}",
                        f"best {rec_lower} 2025",
                        f"popular {rec_lower}",
                        f"{style_name} {rec_lower}" if style_name else f"modern {rec_lower}",
                        f"buy {rec_lower} online",  # More product-focused
                        f"{rec_lower} furniture",  # Retail-focused
                    ]

                    # Shuffle query variations for variety in results
                    random.shuffle(query_variations)
                    query_variations = query_variations[:3]  # Cap at 3 for performance
                    print(f"[PRODUCT_SEARCH] 🔀 Shuffled and capped to {len(query_variations)} query variations")

                    products: List[Dict[str, Any]] = []
                    primary_query = query_variations[0]  # For logging (now randomized)

                    # Helpers for parallel execution per variation
                    def _run_serp(serp_client, full_query, space_type, query_label):
                        """Run SERP search in a thread."""
                        results = []
                        try:
                            serp_products = serp_client.search_and_analyze_products(
                                query=full_query,
                                space_type=space_type,
                                num_results=10,
                            )
                            print(f"[PRODUCT_SEARCH] SERP returned {len(serp_products)} products for variation: '{query_label}'")
                            for product in serp_products:
                                product["source_api"] = "serp"
                                product["search_query"] = query_label
                            results.extend(serp_products)
                        except Exception as e:
                            print(f"[PRODUCT_SEARCH] SERP failed for '{query_label}': {e}")
                        return results

                    def _run_exa(exa_client, full_query, space_type, query_label):
                        """Run Exa search in a thread."""
                        results = []
                        try:
                            exa_products = exa_client.search_and_analyze_products(
                                query=full_query,
                                space_type=space_type,
                                num_results=8,
                                similar_per_seed=2,
                            )
                            print(f"[PRODUCT_SEARCH] Exa returned {len(exa_products)} products for variation: '{query_label}'")
                            for product in exa_products:
                                product["source_api"] = "exa"
                                product["search_query"] = query_label
                            results.extend(exa_products)
                        except Exception as e:
                            print(f"[PRODUCT_SEARCH] Exa failed for '{query_label}': {e}")
                        return results

                    def _run_images(serp_client, rec_lower_str, query_label):
                        """Run Google Images search in a thread."""
                        results = []
                        try:
                            image_query = f"{rec_lower_str} furniture buy online"
                            image_results = serp_client.search_images(
                                query=image_query,
                                num_results=10,
                            )
                            print(f"[PRODUCT_SEARCH] Google Images returned {len(image_results)} for '{image_query}'")
                            for img in image_results:
                                image_url = img.get("thumbnail") or img.get("image_url") or ""
                                results.append({
                                    "title": img.get("title", ""),
                                    "url": img.get("url", ""),
                                    "thumbnail": image_url,
                                    "image_url": image_url,
                                    "source": img.get("source", "Unknown"),
                                    "store": img.get("source", "Unknown"),
                                    "source_api": "google_images",
                                    "search_query": image_query,
                                })
                        except Exception as e:
                            self.logger.warning(f"[PRODUCT_SEARCH] Google Images failed for '{rec_lower_str}': {e}")
                        return results

                    # Search with each query variation (SERP + Exa + Images in parallel)
                    with ThreadPoolExecutor(max_workers=3) as var_executor:
                        for query in query_variations:
                            t_var = time.time()
                            full_query = f"{query} -ideas -inspiration -diy -tutorial -plans -woodworking -blueprint -project -pattern -PDF"

                            futures = []
                            if self.serp_client:
                                futures.append(var_executor.submit(
                                    _run_serp, self.serp_client, full_query,
                                    context.space_type or "general", query))
                            if self.exa_client:
                                futures.append(var_executor.submit(
                                    _run_exa, self.exa_client, full_query,
                                    context.space_type or "general", query))
                            if self.serp_client:
                                futures.append(var_executor.submit(
                                    _run_images, self.serp_client, rec_lower, query))

                            try:
                                for f in as_completed(futures, timeout=15):
                                    try:
                                        products.extend(f.result())
                                    except Exception as e:
                                        self.logger.warning(f"[PRODUCT_SEARCH] Parallel task failed for '{query}': {e}")
                            except FuturesTimeoutError:
                                self.logger.warning(f"[PRODUCT_SEARCH] Timeout waiting for futures for variation '{query[:30]}'")

                            self.logger.info(f"[TIMING] var '{query[:30]}': {time.time() - t_var:.1f}s (parallel)")

                    # Log product collection stats
                    with_images = sum(1 for p in products if p.get("images") or p.get("thumbnail") or p.get("image_url") or p.get("image"))
                    self.logger.info(f"[PRODUCT_SEARCH] === Summary for '{recommendation}' ===")
                    self.logger.info(f"[PRODUCT_SEARCH] Total collected: {len(products)} products from {len(query_variations)} query variations")
                    self.logger.info(f"[PRODUCT_SEARCH] Products with images: {with_images}/{len(products)}")

                    # Deduplicate
                    before_dedup = len(products)
                    products = self._dedupe_products_by_url(products)
                    self.logger.info(f"[PRODUCT_SEARCH] After dedup: {len(products)} (removed {before_dedup - len(products)} duplicates)")

                    # Convert to PreSearchedProduct format with better image extraction
                    formatted_products = []
                    for p in products:
                        # Try multiple image sources - prioritize thumbnail (SERP primary field)
                        images_array = p.get("images") or []
                        image_url = (
                            p.get("thumbnail") or      # SERP primary image
                            p.get("image_url") or      # Already normalized
                            (images_array[0] if images_array else None) or  # Exa images array
                            p.get("image") or          # Fallback field
                            ""
                        )

                        formatted_products.append({
                            "url": p.get("url", p.get("product_link", p.get("link", ""))),
                            "title": p.get("title", ""),
                            "image_url": image_url,
                            "store": p.get("store", p.get("source", "Unknown")),
                            "price_str": p.get("price_str", str(p.get("price", "")) if p.get("price") else ""),
                            "price": p.get("price") if isinstance(p.get("price"), (int, float)) else None,
                            "similarity_score": p.get("similarity_score"),
                        })

                    # Filter to products with valid images
                    before_filter = len(formatted_products)
                    formatted_products = self._filter_products_with_images(
                        formatted_products,
                        min_count=4  # Lowered from 8 to return more results
                    )
                    print(f"[PRODUCT_SEARCH] After image filter: {len(formatted_products)} (from {before_filter} formatted)")
                    self.logger.info(f"  - After image filter: {len(formatted_products)} (from {before_filter} formatted)")

                    # RETRY LOGIC: If 0 results, try a simpler fallback query
                    if len(formatted_products) == 0:
                        print(f"[PRODUCT_SEARCH] 🔄 Retrying with simpler fallback query for '{recommendation}'")
                        fallback_queries = [
                            rec_lower,  # Just the item name
                            f"{rec_lower} shop",
                            f"{rec_lower} store",
                        ]
                        fallback_products = []
                        for fallback_query in fallback_queries:
                            if self.serp_client:
                                try:
                                    serp_fallback = self.serp_client.search_and_analyze_products(
                                        query=fallback_query,
                                        space_type=context.space_type or "general",
                                        num_results=15,
                                    )
                                    print(f"[PRODUCT_SEARCH] Fallback SERP returned {len(serp_fallback)} for '{fallback_query}'")
                                    fallback_products.extend(serp_fallback)
                                except Exception as e:
                                    print(f"[PRODUCT_SEARCH] Fallback SERP failed: {e}")

                        if fallback_products:
                            # Format and filter fallback products
                            fallback_formatted = []
                            for p in fallback_products:
                                images_array = p.get("images") or []
                                image_url = (
                                    p.get("thumbnail") or
                                    p.get("image_url") or
                                    (images_array[0] if images_array else None) or
                                    p.get("image") or
                                    ""
                                )
                                fallback_formatted.append({
                                    "url": p.get("url", p.get("product_link", p.get("link", ""))),
                                    "title": p.get("title", ""),
                                    "image_url": image_url,
                                    "store": p.get("store", p.get("source", "Unknown")),
                                    "price_str": p.get("price_str", str(p.get("price", "")) if p.get("price") else ""),
                                    "price": p.get("price") if isinstance(p.get("price"), (int, float)) else None,
                                    "similarity_score": p.get("similarity_score"),
                                })
                            formatted_products = self._filter_products_with_images(fallback_formatted, min_count=4)
                            print(f"[PRODUCT_SEARCH] Fallback produced {len(formatted_products)} products with images")

                    # Shuffle products before AI curation for variety each time
                    random.shuffle(formatted_products)
                    print(f"[PRODUCT_SEARCH] 🔀 Shuffled {len(formatted_products)} products before AI curation")

                    # AI Curation: Use Gemini to score and rank products by visual quality
                    try:
                        from config import AI_PRODUCT_CURATION
                        if AI_PRODUCT_CURATION.get("enabled", True) and len(formatted_products) >= 4:
                            print(f"[AI_CURATION] Curating {len(formatted_products)} products for '{recommendation}'")
                            curated_products = self._curate_products_with_ai(
                                products=formatted_products,
                                category=rec_lower,
                                style=style_name,
                                room_type=context.space_type or "room",
                                max_products=6  # Return up to 6 curated options
                            )
                            if curated_products and len(curated_products) >= 2:
                                # Add variety: if we have more than 6 products, randomly sample from top candidates
                                if len(curated_products) > 6:
                                    # Take top 10 (or all if fewer), then randomly pick 6
                                    top_candidates = curated_products[:min(10, len(curated_products))]
                                    formatted_products = random.sample(top_candidates, min(6, len(top_candidates)))
                                    # Shuffle the final selection so order varies too
                                    random.shuffle(formatted_products)
                                    print(f"[AI_CURATION] ✅ Randomly selected {len(formatted_products)} from top {len(top_candidates)} curated products")
                                else:
                                    formatted_products = curated_products
                                    random.shuffle(formatted_products)  # Still shuffle order
                                    print(f"[AI_CURATION] ✅ AI curation returned {len(formatted_products)} products (shuffled)")
                            else:
                                print(f"[AI_CURATION] ⚠️ AI curation returned insufficient products, using original list")
                                formatted_products = formatted_products[:6]
                                random.shuffle(formatted_products)
                        else:
                            formatted_products = formatted_products[:6]
                            random.shuffle(formatted_products)
                    except Exception as ai_err:
                        print(f"[AI_CURATION] ❌ AI curation failed: {ai_err}, using original products")
                        self.logger.warning(f"AI curation failed: {ai_err}")
                        formatted_products = formatted_products[:6]
                        random.shuffle(formatted_products)

                    # Ensure minimum 4 products
                    if len(formatted_products) < 4:
                        print(f"[PRODUCT_SEARCH] ⚠️ Only {len(formatted_products)} products, need at least 4")
                        # Products were already filtered, just warn
                    
                    t_rec_end = time.time()
                    print(f"[TIMING] search_recommendation '{recommendation[:40]}': {t_rec_end - t_rec_start:.1f}s total")
                    print(f"[PRODUCT_SEARCH] FINAL: {len(formatted_products)} products for '{recommendation}'")
                    print(f"[PRODUCT_SEARCH] ========================================")
                    self.logger.info(f"  - Final products for '{recommendation}': {len(formatted_products)}")

                    return {
                        "recommendation": recommendation,
                        "search_query": primary_query,
                        "status": "complete",
                        "products": formatted_products,
                        "searched_at": datetime.now().isoformat(),
                        "error_message": None,
                    }

                except Exception as e:
                    self.logger.error(f"Search failed for recommendation '{recommendation}': {e}")
                    return {
                        "recommendation": recommendation,
                        "search_query": "",
                        "status": "error",
                        "products": [],
                        "searched_at": datetime.now().isoformat(),
                        "error_message": str(e),
                    }

            # Execute searches in parallel
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(search_single_recommendation, rec): rec
                    for rec in recommendations
                }

                for future in as_completed(futures):
                    result = future.result()
                    categories.append(result)

            # Sort categories to match input order
            rec_order = {rec: i for i, rec in enumerate(recommendations)}
            categories.sort(key=lambda c: rec_order.get(c["recommendation"], 999))

            # Store in context
            pre_searched = {cat["recommendation"]: cat for cat in categories}
            updated_context = context.model_copy(
                update={"pre_searched_categories": pre_searched}
            )
            projects[project_id]["context"] = updated_context.model_dump()
            self._save_projects(projects)

            total_products = sum(len(cat["products"]) for cat in categories)

            self.logger.info(
                "Product search for recommendations completed",
                extra={
                    "project_id": project_id,
                    "categories": len(categories),
                    "total_products": total_products,
                }
            )

            return {
                "project_id": project_id,
                "categories": categories,
                "total_products": total_products,
                "ai_selected": len(recommendations) <= 2,  # Indicates AI selection was used
                "status": "success",
                "message": f"Found {total_products} products across {len(categories)} categories",
            }

        except Exception as e:
            self.logger.error(
                f"Failed to search products for recommendations: {str(e)}",
                extra={"project_id": project_id},
                exc_info=True,
            )
            raise

    def _generate_search_query_for_recommendation(
        self,
        context: ProjectContext,
        recommendation: str
    ) -> str:
        """
        Generate a search query for a single recommendation.
        Uses decor templates for better results on decor items.
        Uses context (color scheme, style) to optimize the query.
        """
        # Clean up the recommendation
        rec_lower = recommendation.lower()
        for prefix in ["add ", "change ", "replace ", "install ", "hang ", "place "]:
            if rec_lower.startswith(prefix):
                rec_lower = rec_lower[len(prefix):]
                break

        # Get style name for templates
        style_name = ""
        if context.style_analysis and isinstance(context.style_analysis, dict):
            style_name = context.style_analysis.get("style_name", "modern")

        # Get color for templates
        color = ""
        if context.color_analysis and isinstance(context.color_analysis, dict):
            accent_colors = context.color_analysis.get("accent_colors", [])
            if accent_colors and isinstance(accent_colors, list) and len(accent_colors) > 0:
                first_color = accent_colors[0]
                if isinstance(first_color, dict):
                    color = first_color.get("description", "")[:15]

        # Check if this is a decor item with a template
        search_query = None
        for item_key, template in self.DECOR_SEARCH_TEMPLATES.items():
            if item_key in rec_lower:
                search_query = template.format(
                    style=style_name,
                    color=color,
                    size="",
                    type=""
                ).strip()
                # Clean up double spaces
                while "  " in search_query:
                    search_query = search_query.replace("  ", " ")
                break

        # If no template matched, use default approach
        if not search_query:
            query_parts = [rec_lower]
            if style_name:
                query_parts.insert(0, style_name.lower())
            if color:
                query_parts.append(color.lower())
            search_query = " ".join(query_parts)

        # Add "trending" prefix for better product discovery
        search_query = f"trending {search_query}"

        # Add negative keywords to filter out non-products
        # More aggressive filtering for decor items
        negative_keywords = " -ideas -inspiration -\"how to\" -diy -tutorial -book -magazine -pattern"
        search_query += negative_keywords

        self.logger.info(f"Generated search query for '{recommendation}': {search_query}")

        return search_query[:120]  # Limit query length

    def get_pre_searched_suggestions(self, project_id: str) -> Dict[str, Any]:
        """
        Get all pre-searched product suggestions organized by category.

        Returns:
            Dict with categories, status, and message
        """
        try:
            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            pre_searched = context.pre_searched_categories or {}

            if not pre_searched:
                return {
                    "project_id": project_id,
                    "categories": [],
                    "total_products": 0,
                    "overall_status": "empty",
                    "message": "No products have been searched yet",
                }

            categories = list(pre_searched.values())
            total_products = sum(len(cat.get("products", [])) for cat in categories)

            # Determine overall status
            statuses = [cat.get("status", "pending") for cat in categories]
            if all(s == "complete" for s in statuses):
                overall_status = "all_complete"
            elif all(s == "error" for s in statuses):
                overall_status = "all_error"
            elif any(s == "pending" for s in statuses):
                overall_status = "some_pending"
            else:
                overall_status = "mixed"

            return {
                "project_id": project_id,
                "categories": categories,
                "total_products": total_products,
                "overall_status": overall_status,
                "message": f"Found {total_products} products across {len(categories)} categories",
            }

        except Exception as e:
            self.logger.error(
                f"Failed to get pre-searched suggestions: {str(e)}",
                extra={"project_id": project_id},
                exc_info=True,
            )
            raise

    def set_favorite_products(
        self,
        project_id: str,
        favorites: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Save user's selected favorite products from the 'Like These?' screen.
        These will be used in image generation and purchase flow.

        Args:
            project_id: The project ID
            favorites: List of favorite product dicts with category, url, title, image_url, store

        Returns:
            Confirmation with counts
        """
        try:
            self.logger.info(
                "Saving favorite products",
                extra={"project_id": project_id, "count": len(favorites)}
            )

            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            # Validate and store favorites
            validated_favorites = []
            for fav in favorites:
                validated_favorites.append({
                    "category": fav.get("category", ""),
                    "url": fav.get("url", ""),
                    "title": fav.get("title", ""),
                    "image_url": fav.get("image_url", ""),
                    "store": fav.get("store", ""),
                    "price_str": fav.get("price_str"),
                })

            updated_context = context.model_copy(
                update={"favorite_products": validated_favorites}
            )
            projects[project_id]["context"] = updated_context.model_dump()
            self._save_projects(projects)

            # Count by category
            favorites_by_category: Dict[str, int] = {}
            for fav in validated_favorites:
                cat = fav.get("category", "unknown")
                favorites_by_category[cat] = favorites_by_category.get(cat, 0) + 1

            self.logger.info(
                "Favorite products saved successfully",
                extra={
                    "project_id": project_id,
                    "count": len(validated_favorites),
                    "by_category": favorites_by_category,
                }
            )

            return {
                "project_id": project_id,
                "favorites_count": len(validated_favorites),
                "favorites_by_category": favorites_by_category,
                "status": "success",
                "message": f"Saved {len(validated_favorites)} favorite products",
            }

        except Exception as e:
            self.logger.error(
                f"Failed to save favorite products: {str(e)}",
                extra={"project_id": project_id},
                exc_info=True,
            )
            raise

    def set_selected_trending_products(
        self,
        project_id: str,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Save user's selected trending products for image generation.
        These products' images will be passed to Gemini for visual representation.

        Args:
            project_id: The project ID
            products: List of product dicts with category, url, title, image_url, store

        Returns:
            Confirmation with counts
        """
        try:
            self.logger.info(
                "Saving selected trending products",
                extra={"project_id": project_id, "count": len(products)}
            )

            projects = self._load_projects()
            if project_id not in projects:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(projects[project_id]["context"])

            # Validate and store selected trending products
            validated_products = []
            for prod in products:
                validated_products.append({
                    "category": prod.get("category", ""),
                    "url": prod.get("url", ""),
                    "title": prod.get("title", ""),
                    "image_url": prod.get("image_url", ""),
                    "store": prod.get("store", ""),
                    "price_str": prod.get("price_str"),
                })

            updated_context = context.model_copy(
                update={"selected_trending_products": validated_products}
            )
            projects[project_id]["context"] = updated_context.model_dump()
            self._save_projects(projects)

            # Count by category
            products_by_category: Dict[str, int] = {}
            for prod in validated_products:
                cat = prod.get("category", "unknown")
                products_by_category[cat] = products_by_category.get(cat, 0) + 1

            self.logger.info(
                "Selected trending products saved successfully",
                extra={
                    "project_id": project_id,
                    "count": len(validated_products),
                    "by_category": products_by_category,
                }
            )

            return {
                "project_id": project_id,
                "products_count": len(validated_products),
                "products_by_category": products_by_category,
                "status": "success",
                "message": f"Saved {len(validated_products)} trending products for image generation",
            }

        except Exception as e:
            self.logger.error(
                f"Failed to save selected trending products: {str(e)}",
                extra={"project_id": project_id},
                exc_info=True,
            )
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

            # Calculate crop ratio for size-based furniture type deprioritization
            # Small crops (<15% of image) are unlikely to be large furniture (beds, sofas)
            crop_area = w * h  # Normalized coordinates (0-1 scale)
            crop_ratio = crop_area  # Since full image area is 1.0 in normalized coords

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
                    clip_analysis = self.clip_client.analyze_furniture_region(crop, crop_ratio=crop_ratio)
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

            # ============================================================
            # VISUAL-FIRST PRODUCT SEARCH
            # Primary: Google Lens (true visual search) -> direct retailer URLs
            # Secondary: Text search (supplementary results)
            # ============================================================
            products: List[Dict[str, Any]] = []
            lens_products: List[Dict[str, Any]] = []
            text_products: List[Dict[str, Any]] = []

            # Upload crop to ImgBB for Google Lens (requires public URL)
            crop_base64 = self._pil_to_base64(crop)
            public_url = self.upload_image_to_imgbb(crop_base64)

            # ============================================================
            # PRIMARY: Google Lens Reverse Image Search (8-10 results)
            # Returns direct retailer URLs (not Google Shopping redirects)
            # ============================================================
            if public_url and self.serp_client:
                try:
                    self.logger.info(f"🔍 Running Google Lens search with public URL...")
                    lens_results = self.serp_client.reverse_image_search_google_lens_url(public_url)
                    for i, match in enumerate(lens_results[:10]):
                        lens_products.append({
                            "title": match.get("title", "Unknown Product"),
                            "url": match.get("link") or match.get("product_link", ""),
                            "store": match.get("source", "Unknown"),
                            "source": match.get("source", "Unknown"),
                            "thumbnail": match.get("thumbnail", ""),
                            "image_url": match.get("thumbnail", ""),
                            "images": [match.get("thumbnail")] if match.get("thumbnail") else [],
                            "price": None,
                            "price_str": str(match.get("price") or ""),
                            "source_api": "google_lens",
                            "match_type": match.get("match_type", "visual"),
                            "relevance_score": 1.0 - (i * 0.03),  # Higher base for Lens
                            "search_method": "Google Lens",
                        })
                    self.logger.info(f"✅ Google Lens returned {len(lens_products)} results")
                except Exception as e:
                    self.logger.warning(f"Google Lens search failed: {e}")
            else:
                if not public_url:
                    self.logger.warning("ImgBB upload failed, skipping Google Lens search")

            # ============================================================
            # SECONDARY: Text Search (2-3 supplementary results)
            # Fallback expands if Google Lens returns nothing
            # ============================================================
            text_search_limit = 3 if lens_products else 8  # Expand if Lens failed
            if search_query and self.serp_client:
                try:
                    serp_products = self.serp_client.search_and_analyze_products(
                        query=search_query,
                        space_type=context.space_type or "general",
                        num_results=text_search_limit + 2,  # Fetch a bit more, then trim
                    )
                    for product in serp_products[:text_search_limit]:
                        product["source_api"] = "serp_text"
                        product["search_method"] = "Google Shopping (Text)"
                        product["relevance_score"] = product.get("relevance_score", 0.7)
                    text_products.extend(serp_products[:text_search_limit])
                    self.logger.info(f"✅ Text search returned {len(text_products)} supplementary results")
                except Exception as e:
                    self.logger.warning(f"Text search failed: {e}")

            # Combine: Lens results first (primary), then text (secondary)
            products = lens_products + text_products
            self.logger.info(f"📦 Combined {len(lens_products)} Lens + {len(text_products)} Text = {len(products)} total")

            # Deduplicate before scoring
            products = self._dedupe_products_by_url(products)

            # ============================================================
            # EXA VALIDATION: Filter to only real product pages
            # ============================================================
            if self.exa_client and products:
                products = self._validate_product_pages_with_exa(products, max_validate=15, min_valid_threshold=3)

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
                    search_query=search_query,  # Enable multi-signal ranking
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

            # Calculate crop ratio for size-based furniture type deprioritization
            # Small crops (<15% of image) are unlikely to be large furniture (beds, sofas)
            crop_area = w * h  # Normalized coordinates (0-1 scale)
            crop_ratio = crop_area  # Since full image area is 1.0 in normalized coords

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
                    clip_analysis = self.clip_client.analyze_furniture_region(crop, crop_ratio=crop_ratio)
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

            # ============================================================
            # VISUAL-FIRST PRODUCT SEARCH
            # Primary: Google Lens (true visual search) -> direct retailer URLs
            # Secondary: Text search (supplementary results)
            # ============================================================
            products: List[Dict[str, Any]] = []
            lens_products: List[Dict[str, Any]] = []
            text_products: List[Dict[str, Any]] = []

            # Upload crop to ImgBB for Google Lens (requires public URL)
            crop_base64 = self._pil_to_base64(crop)
            public_url = self.upload_image_to_imgbb(crop_base64)

            # ============================================================
            # PRIMARY: Google Lens Reverse Image Search (8-10 results)
            # Returns direct retailer URLs (not Google Shopping redirects)
            # ============================================================
            if public_url and self.serp_client:
                try:
                    self.logger.info(f"🔍 Running Google Lens search with public URL...")
                    lens_results = self.serp_client.reverse_image_search_google_lens_url(public_url)
                    for i, match in enumerate(lens_results[:10]):
                        lens_products.append({
                            "title": match.get("title", "Unknown Product"),
                            "url": match.get("link") or match.get("product_link", ""),
                            "store": match.get("source", "Unknown"),
                            "source": match.get("source", "Unknown"),
                            "thumbnail": match.get("thumbnail", ""),
                            "image_url": match.get("thumbnail", ""),
                            "images": [match.get("thumbnail")] if match.get("thumbnail") else [],
                            "price": None,
                            "price_str": str(match.get("price") or ""),
                            "source_api": "google_lens",
                            "match_type": match.get("match_type", "visual"),
                            "relevance_score": 1.0 - (i * 0.03),  # Higher base for Lens
                            "search_method": "Google Lens",
                        })
                    self.logger.info(f"✅ Google Lens returned {len(lens_products)} results")
                except Exception as e:
                    self.logger.warning(f"Google Lens search failed: {e}")
            else:
                if not public_url:
                    self.logger.warning("ImgBB upload failed, skipping Google Lens search")

            # ============================================================
            # SECONDARY: Text Search (2-3 supplementary results)
            # Fallback expands if Google Lens returns nothing
            # ============================================================
            text_search_limit = 3 if lens_products else 8  # Expand if Lens failed
            if search_query and self.serp_client:
                try:
                    serp_products = self.serp_client.search_and_analyze_products(
                        query=search_query,
                        space_type=context.space_type or "general",
                        num_results=text_search_limit + 2,  # Fetch a bit more, then trim
                    )
                    for product in serp_products[:text_search_limit]:
                        product["source_api"] = "serp_text"
                        product["search_method"] = "Google Shopping (Text)"
                        product["relevance_score"] = product.get("relevance_score", 0.7)
                    text_products.extend(serp_products[:text_search_limit])
                    self.logger.info(f"✅ Text search returned {len(text_products)} supplementary results")
                except Exception as e:
                    self.logger.warning(f"Text search failed: {e}")

            # Combine: Lens results first (primary), then text (secondary)
            products = lens_products + text_products
            self.logger.info(f"📦 Combined {len(lens_products)} Lens + {len(text_products)} Text = {len(products)} total")

            # Deduplicate before scoring
            products = self._dedupe_products_by_url(products)

            # ============================================================
            # EXA VALIDATION: Filter to only real product pages
            # ============================================================
            if self.exa_client and products:
                products = self._validate_product_pages_with_exa(products, max_validate=15, min_valid_threshold=3)

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
                    search_query=search_query,  # Enable multi-signal ranking
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
            # Pass improvement_mode to determine which prompt to use
            improvement_mode = getattr(context, 'improvement_mode', None)
            print(f"📋 Improvement mode: {improvement_mode or 'complete_revamp (default)'}")

            # Get trending products for iterative mode styling suggestions
            trending_products = []
            if improvement_mode == "iterative":
                # Collect trending products from context for additional styling recommendations
                if hasattr(context, 'selected_trending_products') and context.selected_trending_products:
                    trending_products.extend(context.selected_trending_products[:2])
                    print(f"📈 Including {len(trending_products)} trending products for styling suggestions")
                if hasattr(context, 'favorite_products') and context.favorite_products:
                    # Add favorites that aren't already selected
                    for fav in context.favorite_products[:2]:
                        if fav not in trending_products:
                            trending_products.append(fav)
                    print(f"⭐ Total styling suggestions: {len(trending_products)}")

            generated_image_base64, final_prompt, model_used = (
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
                    improvement_mode=improvement_mode,
                    trending_products=trending_products,
                )
            )

            # Update context with generated image base64
            context.generated_image_base64 = generated_image_base64
            context.generation_prompt = final_prompt
            context.generation_model_used = model_used

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
                    "model_used": model_used,
                },
            )

            return {
                "project_id": project_id,
                "selected_products": selected_products,
                "generated_image_base64": generated_image_base64,
                "generation_prompt": final_prompt,
                "status": "success",
                "message": "Image generated successfully using Gemini",
                "model_used": model_used,
            }

        except Exception as e:
            self.logger.error(f"Failed to generate product visualization: {e}")
            # Log failed Gemini call
            log_external_api_call("gemini", "image_generation", 0, False)
            raise

    def generate_inspiration_redesign(self, project_id: str):
        """Generate a redesigned room image based on inspiration recommendations using Gemini"""
        try:
            t_start = time.time()
            log_user_action("inspiration_redesign_started", {"project_id": project_id})

            # Load project context
            project = self.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            t_context = time.time()
            context = ProjectContext.model_validate(project["context"])
            print(f"[TIMING] inspiration_redesign.context_load: {t_context - t_start:.2f}s")
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

            # Determine which prompt to use based on:
            # 1. Has inspiration images uploaded? -> Use inspiration prompt
            # 2. Otherwise, check improvement_mode: iterative vs complete_revamp
            improvement_mode = getattr(context, 'improvement_mode', None)
            has_inspiration_images = len(context.inspiration_images or []) > 0

            # ========================================
            # DETAILED LOGGING FOR PROMPT SELECTION
            # ========================================
            print("\n" + "="*70)
            print("🎯 PROMPT SELECTION DEBUG INFO")
            print("="*70)
            print(f"📋 improvement_mode value: '{improvement_mode}' (type: {type(improvement_mode).__name__})")
            print(f"📸 has_inspiration_images: {has_inspiration_images}")
            print(f"   - inspiration_images count: {len(context.inspiration_images or [])}")
            print(f"   - inspiration_images_skipped: {getattr(context, 'inspiration_images_skipped', 'not set')}")
            print(f"📝 Selected product recommendations: {context.selected_product_recommendations}")
            print(f"🎨 Color scheme: {context.color_scheme}")
            print(f"🪑 Style analysis: {context.style_analysis.get('style_name') if context.style_analysis else 'None'}")
            print(f"📍 Improvement markers: {len(context.improvement_markers or [])} markers")
            for i, marker in enumerate(context.improvement_markers or []):
                print(f"   - Marker {i+1}: {marker.description}")
            print("-"*70)

            # Determine which prompt will be used
            if has_inspiration_images:
                prompt_type = "INSPIRATION"
                prompt_reason = "Inspiration images were uploaded"
            elif improvement_mode == "iterative":
                prompt_type = "ITERATIVE"
                prompt_reason = "User selected 'iterative' mode - surgical edits only"
            else:
                prompt_type = "INTEGRATION (REVAMP)"
                prompt_reason = f"User selected '{improvement_mode or 'complete_revamp (default)'}' mode - full redesign"

            print(f"✅ PROMPT TYPE SELECTED: {prompt_type}")
            print(f"   Reason: {prompt_reason}")
            print("="*70 + "\n")

            # Get selected trending products for all prompt types
            selected_trending = context.selected_trending_products or []

            # Branch based on inspiration images and improvement mode
            if has_inspiration_images:
                # ============================================
                # INSPIRATION PROMPT (photorealistic redesign)
                # Only used when actual inspiration images were uploaded
                # ============================================
                print("🎨 Using INSPIRATION prompt (photorealistic redesign with uploaded images)")

                # 1. Build DESIGN CONTEXT for inspiration prompt
                design_context_lines = []

                # Inspiration
                if context.inspiration_recommendations and len(context.inspiration_recommendations) > 0:
                    design_context_lines.append("INSPIRATION GOALS:")
                    design_context_lines.extend([f"- {clean(rec)}" for rec in context.inspiration_recommendations[:5]])
                    design_context_lines.append("")

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

                    if ca.get('primary_colors'):
                        p_colors = []
                        for c in ca.get('primary_colors', []):
                            if isinstance(c, dict):
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

                design_context_str = "\n".join(design_context_lines) if design_context_lines else "General Modern Upgrade"

                # 2. Build PRODUCT UPDATES
                product_list_str = "None specified"
                selected_recs = context.selected_product_recommendations or []
                ai_recs = context.product_recommendations or []
                primary_recs = list(selected_recs) if selected_recs else []
                complementary_recs = []
                if ai_recs:
                    non_selected = [r for r in ai_recs if r not in selected_recs]
                    complementary_recs = non_selected[:2]

                if primary_recs or complementary_recs:
                    parts = []
                    if primary_recs:
                        parts.append("PRIMARY CHANGES (User Selected):\n" +
                                     "\n".join([f"- {clean(rec)}" for rec in primary_recs[:5]]))
                    if complementary_recs:
                        parts.append("COMPLEMENTARY ENHANCEMENTS (AI Suggested - optional):\n" +
                                     "\n".join([f"- {clean(rec)}" for rec in complementary_recs]))
                    product_list_str = "\n\n".join(parts)

                # 3. Inspiration Prompt - PHOTOREALISM FOCUSED
                prompt = f"""### ROLE & OBJECTIVE
You are a master of Architectural Photography and Interior Restoration. Your task is to modify the provided photograph (the input image) by replacing specific furniture and decor while maintaining the exact architectural shell and original camera properties. The goal is a "Real-Life" photograph, not a digital render.

### 1. STRUCTURAL LOCKDOWN (ABSOLUTE REQUIREMENT)
You are EDITING the original room photograph - NOT creating a new room.

COMPARE EVERY GENERATED FRAME TO THE ORIGINAL:
- The room dimensions must be IDENTICAL to the input image
- Furniture scale must match the original room's proportions
- If the original shows a 12x14ft room, the generated image must show the SAME sized space

DO NOT ALTER UNDER ANY CIRCUMSTANCES:
- Wall positions, angles, colors, and textures
- Ceiling height and features
- Window frames, sizes, and positions
- Door locations, sizes, and frames
- Flooring material, pattern, and boundaries
- Electrical outlets and switches

ROOM ORIENTATION RULES:
- The camera viewpoint must be EXACTLY the same as the original
- Wall positions, angles, and distances must remain FIXED
- If a wall is 10ft away in the original, it must appear 10ft away in the output
- The vanishing points and perspective lines must align precisely with the original

SPATIAL PROPORTION CHECK:
- Before finalizing: Does a person of average height fit the same way in both images?
- Do doorways appear the same relative size?
- Are window proportions maintained?
- Is the floor area the same?

PERSPECTIVE: Maintain the exact lens focal length, camera angle, horizon line, and field of view of the original photo.

### 2. PHOTOGRAPHIC REALISM PROTOCOLS (CRITICAL)
LIGHTING PHYSICS: Do not add "magical" light sources. All illumination must come from the existing windows and any visible lamps in the original photo. Shadows must be hard-edged or soft based on the original photo's light direction.
MATERIAL AUTHENTICITY: Avoid the "plastic" AI look at all costs. Wood must show natural grain and micro-scratches; fabrics must show visible weave and realistic folding; metal must show authentic reflections of the room environment, not generic white highlights.
OPTICAL IMPERFECTIONS: Include subtle photographic traits: natural depth of field (slight blur on very foreground or background objects), realistic color grading matching the original photo's white balance, and organic shadows in corners (ambient occlusion).
CAMERA SIMULATION: Treat this as if shot on a professional full-frame DSLR with a 24-35mm lens. Emulate subtle lens characteristics like minor vignetting and natural color fringing at high-contrast edges.

### 3. DESIGN SPECIFICATIONS
SPACE TYPE: {clean(space_type)}

{design_context_str}

FURNITURE UPDATES:
{product_list_str}

IMPORTANT: Prioritize PRIMARY CHANGES (user-selected). COMPLEMENTARY ENHANCEMENTS are optional improvements to consider if they enhance the overall design cohesion.

DECOR & TEXTILES:
- If adding a rug, ensure it tucks realistically under nearby furniture legs.
- Any wall art should have appropriate frames matching the style (e.g., thin black metal for modern, ornate wood for traditional).
- Textiles (curtains, throws, pillows) must show realistic fabric draping and creasing.

DECLUTTERING: Remove all small loose items, trash, and visible cables from desks and floors to create a clean, organized, professional space.

### 4. OUTPUT REQUIREMENT
Generate a high-resolution photograph. If the image looks like a "3D concept render" or has a smooth, plastic, digital art appearance, it has FAILED. It MUST look like a "before and after" photo taken by the same camera in the same physical room. The final image should be indistinguishable from a real photograph shot for a high-end interior design magazine."""

            elif improvement_mode == "iterative":
                # ============================================
                # ITERATIVE PROMPT (surgical edits only)
                # No color/style enforcement, minimal changes
                # ============================================
                print("🔧 Using ITERATIVE prompt (surgical edits, no color/style enforcement)")

                # Format selected products for iterative prompt
                selected_products_formatted = []
                for p in selected_trending:
                    selected_products_formatted.append({
                        'title': p.get('title', 'Unknown product'),
                        'store': p.get('store', 'Unknown'),
                    })

                # Use the iterative prompt from gemini_client
                prompt = self.gemini_client._create_iterative_prompt(
                    selected_products=selected_products_formatted,
                    marker_locations=context.improvement_markers or [],
                )

            else:
                # ============================================
                # INTEGRATION/REVAMP PROMPT (comprehensive redesign)
                # Full color/style enforcement, AI-coordinated design
                # ============================================
                print("🎨 Using INTEGRATION prompt (full redesign with color/style enforcement)")

                # Prepare product titles for integration prompt
                product_titles = []
                for p in selected_trending:
                    if p.get('title'):
                        product_titles.append(p.get('title'))

                # Add selected recommendations if no trending products
                if not product_titles:
                    product_titles = context.selected_product_recommendations or []

                # Use the integration prompt from gemini_client
                prompt = self.gemini_client._create_integration_prompt(
                    space_type=space_type,
                    product_titles=product_titles,
                    inspiration_recommendations=context.inspiration_recommendations or [],
                    marker_locations=context.improvement_markers or [],
                    custom_prompt=None,
                    color_scheme=context.color_scheme,
                    design_style=context.style_analysis,
                )

            # ========================================
            # FINAL PROMPT VERIFICATION
            # ========================================
            actual_prompt_type = 'INSPIRATION' if has_inspiration_images else ('ITERATIVE' if improvement_mode == 'iterative' else 'INTEGRATION')
            print("\n" + "="*70)
            print("📝 FINAL PROMPT VERIFICATION")
            print("="*70)
            print(f"✅ Prompt type used: {actual_prompt_type}")
            print(f"📏 Prompt length: {len(prompt)} characters")

            # Show the role line to verify correct prompt
            first_lines = prompt.split('\n')[:5]
            print(f"📄 Prompt starts with:")
            for line in first_lines:
                if line.strip():
                    print(f"   {line[:100]}...")
                    break

            # Check for key indicators of each prompt type
            if "Elite Interior Design Visualizer" in prompt:
                print("🔍 DETECTED: INTEGRATION/REVAMP prompt (Elite Interior Design Visualizer)")
                print("   ✓ Should apply full color/style enforcement")
                print("   ✓ Should auto-generate matching accessories")
                print("   ✓ Should create cohesive high-end look")
            elif "High-End Virtual Stager" in prompt:
                print("🔍 DETECTED: ITERATIVE prompt (High-End Virtual Stager)")
                print("   ✓ Should make surgical edits only")
                print("   ✓ Should NOT change color/style")
                print("   ✓ Should keep room mostly the same")
            elif "master of Architectural Photography" in prompt:
                print("🔍 DETECTED: INSPIRATION prompt (Architectural Photography)")
                print("   ✓ Should create photorealistic result")
                print("   ✓ Should use inspiration images as reference")
            else:
                print("⚠️ WARNING: Could not detect prompt type from content!")

            # Verify mode matches prompt
            if improvement_mode == "iterative" and "Elite Interior Design Visualizer" in prompt:
                print("❌ ERROR: Mode is 'iterative' but using INTEGRATION prompt!")
            elif improvement_mode != "iterative" and "High-End Virtual Stager" in prompt:
                print("❌ ERROR: Mode is NOT 'iterative' but using ITERATIVE prompt!")
            else:
                print("✅ Mode and prompt type MATCH correctly")

            print("="*70 + "\n")

            # Prepare product images for Gemini (selected_trending already declared above)
            product_images_for_gemini = None
            if selected_trending:
                product_images_for_gemini = [
                    {"image_url": p.get("image_url", ""), "title": p.get("title", "")}
                    for p in selected_trending
                    if p.get("image_url")
                ]
                self.logger.info(
                    f"Passing {len(product_images_for_gemini)} trending product images to Gemini"
                )

            # Call Gemini API using the new method
            t_prompt = time.time()
            print(f"[TIMING] inspiration_redesign.prompt_build: {t_prompt - t_start:.2f}s")
            generated_image_base64, model_used = self.gemini_client.generate_room_redesign(
                original_room_image_path=original_room_image_path,
                prompt=prompt,
                product_images=product_images_for_gemini
            )
            t_gemini = time.time()
            print(f"[TIMING] inspiration_redesign.gemini_call: {t_gemini - t_prompt:.2f}s")

            # Update context with generated image
            context.inspiration_generated_image_base64 = generated_image_base64
            context.inspiration_generation_prompt = prompt
            context.inspiration_model_used = model_used

            # Save context
            projects = self._load_projects()
            projects[project_id]["context"] = context.model_dump()
            projects[project_id]["status"] = "INSPIRATION_REDESIGN_COMPLETE"
            self._save_projects(projects)
            t_saved = time.time()
            print(f"[TIMING] inspiration_redesign.save: {t_saved - t_gemini:.2f}s")
            print(f"[TIMING] inspiration_redesign.total: {t_saved - t_start:.2f}s")

            log_project_status_change(
                project_id, project["status"], "INSPIRATION_REDESIGN_COMPLETE"
            )
            log_user_action(
                "inspiration_redesign_completed",
                {
                    "project_id": project_id,
                    "image_size": f"{len(generated_image_base64)} chars",
                    "model_used": model_used,
                },
            )

            return {
                "project_id": project_id,
                "generated_image_base64": generated_image_base64,
                "inspiration_prompt": prompt,
                "inspiration_recommendations": context.inspiration_recommendations,
                "status": "success",
                "message": "Inspiration-based redesign completed successfully",
                "model_used": model_used,
            }

        except Exception as e:
            self.logger.error(f"Failed to generate inspiration redesign: {e}")
            log_external_api_call("gemini", "inspiration_redesign", 0, False)
            raise

    def retry_inspiration_redesign(self, project_id: str, feedback: str):
        """
        Apply user-directed modifications to the existing generated image.

        This is a SURGICAL EDIT operation - takes the last generated image
        and applies only the specific changes the user requested.

        Args:
            project_id: The project ID
            feedback: User's modification request (e.g., "remove the lamp")

        Returns:
            Dict with edited image and metadata
        """
        try:
            log_user_action("retry_redesign_started", {
                "project_id": project_id,
                "feedback": feedback[:100]
            })

            # Load project context
            project = self.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            context = ProjectContext.model_validate(project["context"])

            # Check that we have a generated image to edit
            if not context.inspiration_generated_image_base64:
                raise ValueError(
                    "No generated image available to edit. Please generate an image first."
                )

            if not self.gemini_client:
                raise ValueError("Gemini client is not available")

            if not feedback or not feedback.strip():
                raise ValueError("Feedback cannot be empty")

            print(f"✏️ Retry redesign: Applying user feedback to existing image")
            print(f"   Feedback: '{feedback[:100]}...'")

            # Call Gemini to edit the image (returns image, model, and full prompt)
            edited_image_base64, model_used, full_prompt = self.gemini_client.edit_room_with_feedback(
                generated_image_base64=context.inspiration_generated_image_base64,
                user_feedback=feedback.strip()
            )

            # Update context with edited image and full prompt
            context.inspiration_generated_image_base64 = edited_image_base64
            context.inspiration_generation_prompt = full_prompt  # Store full prompt for debugging
            context.inspiration_model_used = model_used

            # Save context
            projects = self._load_projects()
            projects[project_id]["context"] = context.model_dump()
            self._save_projects(projects)

            log_user_action(
                "retry_redesign_completed",
                {
                    "project_id": project_id,
                    "feedback": feedback[:100],
                    "model_used": model_used,
                },
            )

            return {
                "project_id": project_id,
                "generated_image_base64": edited_image_base64,
                "inspiration_prompt": full_prompt,  # Return full prompt for UI display
                "inspiration_recommendations": context.inspiration_recommendations or [],
                "status": "success",
                "message": "Image edited successfully based on your feedback",
                "model_used": model_used,
            }

        except Exception as e:
            self.logger.error(f"Failed to retry redesign: {e}")
            log_external_api_call("gemini", "retry_redesign", 0, False)
            raise

    def _validate_click_on_primary(
        self,
        click_x: float,
        click_y: float,
        detection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that the primary item contains the click point.
        If not, swap with a better candidate from additional_items.

        This fixes issues where clicking on a small item (lamp) on a larger item
        (nightstand) returns the larger item as primary.

        Scoring based on:
        1. Click containment (is click inside bbox?) - 100 points
        2. Smaller area preferred (more specific) - up to 50 points
        3. Closer to click center - up to 10 points

        Args:
            click_x: Normalized x coordinate (0-1)
            click_y: Normalized y coordinate (0-1)
            detection: Detection result from Gemini spatial detector

        Returns:
            Updated detection dict with potentially swapped primary/additional items
        """
        additional = detection.get("additional_items", [])

        if not additional:
            return detection  # Nothing to swap with

        # Build list of all candidate items
        primary = {
            "label": detection["label"],
            "bbox_normalized": detection.get("bbox_normalized", [0, 0, 1, 1]),
            "color": detection.get("attributes", {}).get("color", "unknown"),
            "material": detection.get("attributes", {}).get("material", "unknown"),
            "style": detection.get("attributes", {}).get("style", "unknown"),
            "search_query": detection.get("search_query", detection["label"]),
        }

        all_items = [primary] + additional
        scored = []

        for item in all_items:
            bbox = item.get("bbox_normalized", [0, 0, 1, 1])

            # Handle both [ymin, xmin, ymax, xmax] and ensure we have 4 values
            if len(bbox) != 4:
                bbox = [0, 0, 1, 1]

            ymin, xmin, ymax, xmax = bbox

            # Sanity check - swap if reversed
            if ymin > ymax:
                ymin, ymax = ymax, ymin
            if xmin > xmax:
                xmin, xmax = xmax, xmin

            # Check if click is inside this bbox
            click_inside = (ymin <= click_y <= ymax and xmin <= click_x <= xmax)

            # Calculate distance from click to item center
            center_x = (xmin + xmax) / 2
            center_y = (ymin + ymax) / 2
            distance = ((click_x - center_x) ** 2 + (click_y - center_y) ** 2) ** 0.5

            # Calculate area (smaller = more specific, preferred for overlapping items)
            area = (ymax - ymin) * (xmax - xmin)

            # Score calculation
            score = 0
            if click_inside:
                score += 100  # Major bonus for containment
                score += 50 * (1 - min(area, 1))  # Smaller area = higher score
                score += 10 * (1 - min(distance, 1))  # Closer center = higher score
            else:
                # Not inside - only give distance bonus (weak candidate)
                score += 10 * (1 - min(distance, 1))

            item["_selection_score"] = score
            scored.append(item)

        # Sort by score descending
        scored.sort(key=lambda x: x.get("_selection_score", 0), reverse=True)
        best = scored[0]

        # If best is different from original primary, swap
        original_label = detection["label"]
        if best.get("label") != original_label:
            print(f"   🔄 Click validation: Switching '{original_label}' → '{best['label']}' (score: {best.get('_selection_score', 0):.1f})")

            detection["label"] = best["label"]
            detection["bbox_normalized"] = best.get("bbox_normalized", detection.get("bbox_normalized"))
            detection["search_query"] = best.get("search_query", best["label"])
            detection["attributes"] = {
                "color": best.get("color", "unknown"),
                "material": best.get("material", "unknown"),
                "style": best.get("style", detection.get("attributes", {}).get("style", "unknown")),
            }

            # Update additional_items to exclude the new primary and include old primary
            new_additional = []
            for item in scored[1:]:
                item.pop("_selection_score", None)
                if item.get("label") != best.get("label"):
                    new_additional.append(item)
            detection["additional_items"] = new_additional

        # Clean up scores from items
        for item in scored:
            item.pop("_selection_score", None)

        return detection

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
            from PIL import Image, ImageOps
            image_bytes = base64.b64decode(image_base64)
            full_image = Image.open(BytesIO(image_bytes))
            full_image = ImageOps.exif_transpose(full_image)
            full_image = full_image.convert("RGB")
            width, height = full_image.size

            # Compute image hash for caching (used to detect if image changed)
            image_hash = hashlib.md5(image_bytes).hexdigest()[:16]

            # Initialize Utilities
            from spatial_utils import SpatialDetector, smart_crop
            spatial_detector = SpatialDetector()
            
            print(f"🔎 analyze_furniture_batch (Gemini Spatial) - Processing {len(selections)} selections")
            print(f"   Image size: {width}x{height}, Type: {image_type}")
            
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
                    # CACHE CHECK: Skip expensive analysis if result is cached
                    # Cache key based on (project, image hash, click location)
                    # ============================================================
                    bbox_cache_key = f"{round(x, 2):.2f}_{round(y, 2):.2f}"
                    cached_analysis = cache_manager.get_furniture_analysis(
                        project_id, image_hash, bbox_cache_key
                    )
                    if cached_analysis:
                        print(f"   💾 Cache HIT for furniture at ({x:.2f}, {y:.2f})")
                        analysis_results.append(cached_analysis)
                        continue  # Skip to next selection

                    # ============================================================
                    # STEP 1: Gemini Spatial Detection (Object + Bounding Box)
                    # ============================================================
                    detection = spatial_detector.get_object_bbox(
                        image_bytes,
                        click_x=x,
                        click_y=y,
                        image_width=width,
                        image_height=height,
                        space_type=context.space_type  # Pass space_type for smarter fallback
                    )

                    # ============================================================
                    # CLICK VALIDATION: Ensure primary item contains click point
                    # Fixes lamp-on-nightstand issue where larger item is returned
                    # ============================================================
                    detection = self._validate_click_on_primary(x, y, detection)

                    # ============================================================
                    # SMART ITEM SELECTION: Prefer smaller items when overlapping
                    # E.g., lamp ON sidetable - user clicking lamp should get lamp
                    # ============================================================
                    label = detection["label"]
                    attributes = detection.get("attributes", {})
                    search_query = detection.get("search_query", label)
                    bbox_norm = detection.get("bbox_normalized", [0.3, 0.3, 0.7, 0.7])

                    additional_items = detection.get("additional_items", [])
                    if additional_items:
                        print(f"   🔄 Found {len(additional_items)} additional items: {[a['label'] for a in additional_items]}")

                        # Calculate primary bbox area and center distance
                        primary_ymin, primary_xmin, primary_ymax, primary_xmax = bbox_norm
                        primary_area = (primary_ymax - primary_ymin) * (primary_xmax - primary_xmin)

                        # Enhanced smart selection with weighted scoring
                        best_candidate = None
                        best_score = 0

                        for item in additional_items:
                            item_bbox = item.get("bbox_normalized", [0, 0, 1, 1])
                            item_ymin, item_xmin, item_ymax, item_xmax = item_bbox
                            item_area = (item_ymax - item_ymin) * (item_xmax - item_xmin)

                            # Check if click is inside this item's bbox
                            click_in_item = (item_ymin <= y <= item_ymax and item_xmin <= x <= item_xmax)

                            if not click_in_item:
                                continue

                            # Score based on: smaller area + closer to click center
                            area_score = 1.0 - min(item_area / max(primary_area, 0.001), 1.0)
                            item_center = ((item_xmin + item_xmax) / 2, (item_ymin + item_ymax) / 2)
                            distance = ((x - item_center[0]) ** 2 + (y - item_center[1]) ** 2) ** 0.5
                            distance_score = 1.0 - min(distance, 1.0)

                            # Weight: 70% area preference (smaller = better), 30% distance
                            score = 0.7 * area_score + 0.3 * distance_score

                            if score > best_score:
                                best_score = score
                                best_candidate = item

                        # Switch to best candidate if found a good match
                        if best_candidate and best_score > 0.2:
                            print(f"   ✨ Switching to '{best_candidate['label']}' (score: {best_score:.2f})")
                            label = best_candidate.get("label", label)
                            attributes = {
                                "color": best_candidate.get("color", "unknown"),
                                "material": best_candidate.get("material", "unknown"),
                                "style": attributes.get("style", "unknown"),
                            }
                            search_query = best_candidate.get("search_query", label)
                            bbox_norm = best_candidate.get("bbox_normalized", bbox_norm)
                    
                    print(f"   📍 Click at ({x:.2f}, {y:.2f}) -> Detected: '{label}'")
                    print(f"   📦 BBox: {bbox_norm}")
                    print(f"   🔍 Search query: {search_query}")
                    self.logger.info(f"Gemini detected: {label} {bbox_norm}")
                    
                    # ============================================================
                    # STEP 2: Smart Crop using Gemini Bounding Box
                    # ============================================================
                    crop = smart_crop(full_image, bbox_norm, padding=0.05)

                    # Prepare crop for optimal reverse image search quality
                    crop = self._prepare_crop_for_search(crop, target_size=512)

                    # Store crop as high-quality JPEG base64 for ImgBB/Google Lens
                    crop_buffer = BytesIO()
                    crop.save(crop_buffer, format='JPEG', quality=95)  # Higher quality for better matching
                    crop_base64 = base64.b64encode(crop_buffer.getvalue()).decode('utf-8')

                    # ============================================================
                    # STEP 2b: CLIP Fallback when Gemini Detection Failed
                    # ============================================================
                    if detection.get("fallback") and self.clip_client and self.clip_client.is_available():
                        print(f"   🔍 Gemini fallback triggered - using CLIP to classify crop...")
                        try:
                            # Calculate crop_ratio from normalized bounding box
                            # bbox_norm format: [x1, y1, x2, y2]
                            crop_ratio = (bbox_norm[2] - bbox_norm[0]) * (bbox_norm[3] - bbox_norm[1])
                            clip_analysis = self.clip_client.analyze_furniture_region(crop, crop_ratio=crop_ratio)
                            if clip_analysis and "error" not in clip_analysis:
                                furniture_type = clip_analysis.get("furniture_type", {})
                                clip_confidence = furniture_type.get("confidence", 0)
                                if clip_confidence > 0.50:
                                    label = furniture_type.get("name", label)
                                    # Also update attributes from CLIP
                                    attributes = {
                                        "color": clip_analysis.get("color", {}).get("name", "unknown"),
                                        "material": clip_analysis.get("material", {}).get("name", "unknown"),
                                        "style": clip_analysis.get("style", {}).get("name", "unknown"),
                                    }
                                    # Generate better search query
                                    search_query = self.clip_client.generate_enhanced_search_query(crop) or label
                                    print(f"   ✅ CLIP detected: '{label}' (conf: {clip_confidence:.2f})")
                                    print(f"   🎨 Attributes: {attributes}")
                                else:
                                    print(f"   ⚠️ CLIP confidence too low ({clip_confidence:.2f}), keeping '{label}'")
                            else:
                                print(f"   ⚠️ CLIP analysis failed: {clip_analysis.get('error', 'unknown error')}")
                        except Exception as e:
                            print(f"   ❌ CLIP fallback error: {e}")

                    # ============================================================
                    # STEP 3: Parallel Search (Google Lens + Exa)
                    # ============================================================
                    all_products = []
                    
                    # --- 3A: Google Lens Reverse Image Search ---
                    if self.serp_client:
                        # Upload crop to ImgBB for public URL
                        print(f"   🔍 Uploading to ImgBB for Google Lens search...")
                        public_url = self.upload_image_to_imgbb(crop_base64)

                        if public_url:
                            print(f"   ✅ ImgBB upload successful: {public_url[:50]}...")
                            self.logger.info(f"Searching Google Lens with public URL: {public_url}")
                            lens_results = self.serp_client.reverse_image_search_google_lens_url(public_url)
                            # Use rank-based scoring instead of hardcoded 1.0
                            for i, lens_match in enumerate(lens_results[:12]):
                                # Map to internal product format
                                all_products.append({
                                    "title": lens_match.get("title", "Unknown Product"),
                                    "url": lens_match.get("product_link") or lens_match.get("link", ""),
                                    "store": lens_match.get("source", "Unknown"),
                                    "thumbnail": lens_match.get("thumbnail", ""),
                                    "image_url": lens_match.get("thumbnail", ""),  # Normalize image field
                                    "price": None,
                                    "price_str": str(lens_match.get("price") or ""),
                                    "description": lens_match.get("title", ""),
                                    "source_api": "google_lens",
                                    "relevance_score": 1.0 - (i * 0.05),  # Rank-based: 1.0, 0.95, 0.90...
                                    "search_method": "Google Lens",
                                    "images": [lens_match.get("thumbnail")] if lens_match.get("thumbnail") else []
                                })
                        else:
                            print(f"   ⚠️ ImgBB upload failed, skipping Google Lens")
                            self.logger.warning("ImgBB upload failed, skipping Google Lens URL search")

                    # --- 3B: Exa Neural Search with Multi-Query Strategy ---
                    # Generate multiple search queries for better coverage
                    try:
                        from search_utils import search_exa_products

                        # Generate multiple queries for distinctive items
                        search_queries = self._generate_multi_queries(label, attributes)
                        print(f"   🔎 Multi-query search: {search_queries}")

                        for query in search_queries:
                            self.logger.info(f"Searching Exa with query: {query}")
                            try:
                                # Fewer results per query since we're doing multiple
                                results_per_query = max(4, 12 // len(search_queries))
                                exa_results = search_exa_products(query, num_results=results_per_query)
                                all_products.extend(exa_results)
                            except Exception as query_err:
                                self.logger.warning(f"Exa query '{query}' failed: {query_err}")
                    except Exception as e:
                        self.logger.warning(f"Exa search failed: {e}")

                    # Deduplicate
                    all_products = self._dedupe_products_by_url(all_products)

                    # ============================================================
                    # STEP 4: CLIP Validation and Reranking
                    # ============================================================
                    if self.clip_client and self.clip_client.is_available() and all_products:
                        # Step 4A: Text-to-image validation (filter by label relevance)
                        self.logger.info(f"Validating {len(all_products)} products with CLIP against label: '{label}'")
                        validated_products = self.clip_client.validate_products_by_label(
                            label=label,
                            products=all_products,
                            threshold=0.40,  # Higher threshold to reduce false positives
                            top_k=16  # Keep more for visual reranking
                        )
                        # Only replace if validation didn't empty results aggressively
                        if validated_products:
                            all_products = validated_products

                        # Step 4B: Image-to-image visual similarity reranking
                        # This finds products that look most like the actual furniture crop
                        self.logger.info(f"Reranking {len(all_products)} products by visual similarity")
                        all_products = self.clip_client.rerank_products_by_visual_similarity(
                            query_image=crop,
                            products=all_products,
                            top_k=12,
                            min_similarity=0.25  # Lower threshold, let visual ranking sort
                        )
                        print(f"   📊 Visual similarity reranking complete")

                    # Validate product links work
                    all_products = self._validate_product_links(all_products, max_validate=8)

                    # Limit final results
                    all_products = all_products[:12]

                    # ============================================================
                    # STEP 5: Bed Component Expansion
                    # If detected furniture is a bed, search for additional components
                    # Uses two-stage filtering to avoid false positives (e.g., "bedside lamp")
                    # ============================================================
                    bed_components = None
                    is_bed = self._is_actual_bed(label)

                    if is_bed:
                        print(f"   🛏️ Detected bed (label: '{label}') - expanding to search for components")
                        self.logger.info(f"Bed detected: label='{label}', searching for bed components")
                        
                        # Step 1: Use Gemini Vision to detect visible sub-components
                        detected_components = {}
                        try:
                            detected_components = self._detect_bed_sub_components(crop)
                        except Exception as detect_err:
                            self.logger.warning(f"Bed component detection failed: {detect_err}")
                        
                        # Step 2: Search for products using component-specific attributes
                        bed_components = self._search_bed_components(
                            attributes=attributes,
                            style=attributes.get("style", ""),
                            color=attributes.get("color", ""),
                            material=attributes.get("material", ""),
                            detected_components=detected_components,  # Pass detected components
                            main_products=all_products,  # Pass Google Lens visual results for bed_frame
                        )
                        # Log bed component results
                        if bed_components:
                            for comp_key, comp_products in bed_components.items():
                                print(f"   📦 {comp_key}: {len(comp_products)} products")
                    else:
                        print(f"   ℹ️ Not a bed (label: '{label}') - skipping bed components")

                    # Create FurnitureAnalysisItem result
                    from models import FurnitureAnalysisItem

                    # Map to FurnitureAnalysisItem structure with bed components
                    analysis_item = FurnitureAnalysisItem(
                        id=f"item_{int(time.time())}_{x}",
                        furniture_type=label,
                        confidence=detection.get("confidence", 0.9),
                        style=attributes.get("style", ""),
                        material=attributes.get("material", ""),
                        color=attributes.get("color", ""),
                        search_query=search_query,
                        products=all_products,
                        is_bed=is_bed,
                        bed_components=bed_components if is_bed else None
                    )

                    # Cache the analysis result before appending
                    analysis_dict = analysis_item.model_dump()
                    cache_manager.set_furniture_analysis(
                        project_id, image_hash, bbox_cache_key, analysis_dict
                    )

                    analysis_results.append(analysis_dict)

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

    def _is_actual_bed(self, label: str) -> bool:
        """
        Determine if a furniture label refers to a bed or bed region (including bedding items).

        This function has been expanded to recognize that clicking on bedding items
        (duvet, comforter, pillows, sheets) on a bed should trigger the full bed
        component search.

        Uses a multi-stage approach:
        1. First check compound exclusions (bedside lamp, nightstand, etc.)
        2. Then check for bed indicators
        3. Also check for bedding items that are part of a bed

        Args:
            label: The detected furniture label from Gemini/CLIP

        Returns:
            True if this is a bed or bed region (should trigger component search), False otherwise
        """
        from config import (
            BED_PRIMARY_INDICATORS,
            NOT_BED_COMPOUND_TERMS,
        )

        label_lower = label.lower().strip()

        # Step 1: Check compound exclusions first (most specific, fastest rejection)
        # These are items that are clearly NOT part of a bed even if "bed" appears
        for not_bed_term in NOT_BED_COMPOUND_TERMS:
            if not_bed_term in label_lower:
                self.logger.debug(f"Bed check: '{label}' excluded by compound term '{not_bed_term}'")
                return False

        # Step 2: Explicit NON-bed furniture types (these should never trigger bed search)
        non_bed_furniture = [
            "lamp", "light", "chandelier", "sconce", "fixture",
            "table", "desk", "console", "chair", "sofa", "couch",
            "dresser", "cabinet", "shelf", "bookcase", "wardrobe",
            "rug", "carpet", "curtain", "mirror", "clock", "art",
            "nightstand", "side table", "end table",
        ]
        for exclusion in non_bed_furniture:
            if exclusion in label_lower:
                self.logger.debug(f"Bed check: '{label}' excluded by furniture term '{exclusion}'")
                return False

        # Step 3: Check primary bed indicators (bed, bed frame, etc.)
        for bed_term in BED_PRIMARY_INDICATORS:
            if bed_term in label_lower:
                self.logger.debug(f"Bed check: '{label}' matched primary indicator '{bed_term}'")
                return True

        # Step 4: Check simple "bed" term
        if "bed" in label_lower:
            self.logger.debug(f"Bed check: '{label}' matched simple bed term")
            return True

        # Step 5: NEW - Check for bedding items that are ON a bed
        # When someone clicks on a duvet/comforter/pillows on a bed, we should
        # search for all bed components
        bedding_indicators = [
            "duvet", "duvet cover", "comforter", "quilt", "bedspread",
            "bedding", "bed sheet", "sheet set", "fitted sheet",
            "pillow", "cushion", "throw blanket", "throw",
            "coverlet", "bed cover", "bed linen",
        ]
        for bedding_term in bedding_indicators:
            if bedding_term in label_lower:
                self.logger.info(f"Bed check: '{label}' is bedding item '{bedding_term}' - treating as bed region")
                print(f"   🛏️ Detected bedding item '{label}' - will search for ALL bed components")
                return True

        # Step 6: Check for bed-like contextual patterns that Gemini might return
        # These patterns suggest bed-sized upholstered furniture
        bed_contextual_patterns = [
            ("tufted", "upholstered"),    # "tufted upholstered" furniture is often a bed
            ("channel", "tufted"),         # "channel tufted" furniture is often a bed
            ("wingback", "upholstered"),   # "wingback upholstered" is often a bed headboard
            ("button", "tufted"),          # "button tufted" large furniture is often a bed
            ("velvet", "upholstered"),     # Large velvet upholstered furniture may be a bed
        ]
        for pattern in bed_contextual_patterns:
            if all(p in label_lower for p in pattern):
                self.logger.info(f"Bed check: '{label}' matched contextual bed pattern {pattern}")
                print(f"   🛏️ Detected bed-like pattern '{pattern}' in '{label}' - treating as bed")
                return True

        return False

    def _detect_bed_sub_components(
        self,
        bed_crop: Image.Image,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Use Gemini Vision to detect visible sub-components within a bed image.
        
        Analyzes the bed crop to identify:
        - Visible pillows (decorative, sleeping) with colors/patterns
        - Bedding/duvet/comforter with colors/patterns
        - Throw blanket if visible with colors/materials
        - Bed frame/headboard with material/style
        
        Args:
            bed_crop: PIL Image of the cropped bed region
            
        Returns:
            Dict of detected components with their attributes, e.g.:
            {
                "pillows": {"visible": True, "color": "cream", "style": "textured", "count": 4},
                "bedding": {"visible": True, "color": "white", "pattern": "solid", "material": "linen"},
                "throw": {"visible": True, "color": "beige", "material": "knit"},
                "bed_frame": {"visible": True, "material": "wood", "color": "walnut", "style": "modern"}
            }
        """
        from pydantic import BaseModel, Field
        from typing import Optional as OptionalType
        import base64
        from io import BytesIO
        
        try:
            # Convert crop to base64
            buffer = BytesIO()
            bed_crop.convert("RGB").save(buffer, format="JPEG", quality=85)
            crop_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            class BedComponent(BaseModel):
                visible: bool = Field(description="Whether this component is visible in the image")
                color: OptionalType[str] = Field(default=None, description="Primary color of the component")
                secondary_color: OptionalType[str] = Field(default=None, description="Secondary/accent color if present")
                pattern: OptionalType[str] = Field(default=None, description="Pattern: solid, striped, textured, floral, geometric, etc.")
                material: OptionalType[str] = Field(default=None, description="Material: linen, cotton, velvet, knit, wood, upholstered, etc.")
                style: OptionalType[str] = Field(default=None, description="Style: modern, traditional, bohemian, minimalist, etc.")
                count: OptionalType[int] = Field(default=None, description="Count if applicable (e.g., number of pillows)")
            
            class BedComponentsResponse(BaseModel):
                pillows: BedComponent = Field(description="Decorative or sleeping pillows on the bed")
                bedding: BedComponent = Field(description="Main bedding - duvet, comforter, or bedspread")
                throw: BedComponent = Field(description="Throw blanket or decorative blanket if present")
                bed_frame: BedComponent = Field(description="Bed frame or headboard")
            
            prompt = """Analyze this bed image and identify the visible components.

For each component, describe:
1. pillows: All visible pillows (decorative and sleeping). Note color, pattern, count.
2. bedding: The main bedding (duvet/comforter/bedspread). Note color, pattern, material.
3. throw: Any throw blanket visible at foot of bed or draped. Note color and material.
4. bed_frame: The bed frame/headboard. Note material (wood/upholstered/metal), color, style.

Be specific about colors (e.g., "cream", "sage green", "charcoal gray" not just "white" or "green").
Be specific about materials (e.g., "linen", "velvet", "knit wool" not just "fabric").
If a component is not visible or unclear, set visible=false.
"""
            
            # Call Gemini with the bed crop
            result = self.gemini_client.analyze_images_with_vision(
                prompt=prompt,
                pydantic_model=BedComponentsResponse,
                image_parts=[{
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": crop_b64
                    }
                }],
                system_message="You are an interior design expert analyzing bedroom styling. Be specific about colors, patterns, and materials to help find matching products."
            )
            
            # Convert to dict
            components = result.model_dump()
            
            # Log what was detected
            visible_components = [k for k, v in components.items() if v.get("visible")]
            print(f"   🔍 Detected bed components: {', '.join(visible_components)}")
            for comp_name, comp_data in components.items():
                if comp_data.get("visible"):
                    attrs = [f"{k}={v}" for k, v in comp_data.items() if v and k != "visible"]
                    print(f"      - {comp_name}: {', '.join(attrs[:4])}")
            
            return components
            
        except Exception as e:
            self.logger.warning(f"Bed sub-component detection failed: {e}")
            print(f"   ⚠️ Bed component detection failed: {e}, using default search")
            # Return empty dict to fall back to default behavior
            return {}

    def _search_bed_components(
        self,
        attributes: Dict[str, Any],
        style: str = "",
        color: str = "",
        material: str = "",
        detected_components: Dict[str, Dict[str, Any]] = None,
        main_products: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for bed component products (frame, bedding, throw, pillows).
        Returns 4 products for each component category.

        Args:
            attributes: Detected attributes from Gemini
            style: Detected style (e.g., "modern", "traditional")
            color: Detected color (e.g., "white", "gray")
            material: Detected material (e.g., "wood", "upholstered")
            detected_components: Component-specific attributes from Gemini Vision

        Returns:
            Dict with keys: bed_frame, bedding, throw, pillows
            Each value is a list of up to 4 products
        """
        from config import BED_COMPONENTS
        from concurrent.futures import ThreadPoolExecutor, as_completed

        components_results = {}
        detected_components = detected_components or {}

        # For bed_frame: Use main Google Lens visual search results
        # These are from searching the actual bed image, not text queries
        if main_products:
            bed_keywords = ["bed", "frame", "headboard", "platform", "upholstered"]
            bed_frame_products = [
                p for p in main_products
                if any(kw in (p.get("title") or "").lower() for kw in bed_keywords)
            ][:4]

            if bed_frame_products:
                # Format products to match expected structure
                formatted_bed_frame = []
                for p in bed_frame_products:
                    image_url = ""
                    images = p.get("images", [])
                    if images and len(images) > 0:
                        image_url = images[0]
                    elif p.get("thumbnail"):
                        image_url = p.get("thumbnail")
                    elif p.get("image"):
                        image_url = p.get("image")
                    elif p.get("image_url"):
                        image_url = p.get("image_url")

                    formatted_bed_frame.append({
                        "url": p.get("url", p.get("product_link", p.get("link", ""))),
                        "title": p.get("title", ""),
                        "image_url": image_url,
                        "store": p.get("store", p.get("source", "Unknown")),
                        "price_str": p.get("price_str", str(p.get("price", "")) if p.get("price") else ""),
                        "price": p.get("price") if isinstance(p.get("price"), (int, float)) else None,
                    })

                components_results["bed_frame"] = formatted_bed_frame
                print(f"   🛏️ bed_frame: Using {len(formatted_bed_frame)} products from visual search")

        def search_component(component_key: str, component_config: Dict) -> tuple:
            """Search for a single bed component."""
            try:
                search_terms = component_config.get("search_terms", [component_key])
                # Build search query with style/color context
                base_query = search_terms[0] if search_terms else component_key

                # Use component-specific attributes if detected, otherwise fall back to bed's overall attributes
                comp_attrs = detected_components.get(component_key, {})

                # Don't use bed frame attributes for textile components
                textile_components = {"bedding", "throw", "pillows"}
                if component_key in textile_components:
                    # Textiles should use their own detected attributes, not bed frame's
                    comp_color = comp_attrs.get("color", "white")  # Default to neutral
                    comp_material = comp_attrs.get("material", "cotton")  # Default to common textile
                else:
                    comp_color = comp_attrs.get("color") or color
                    comp_material = comp_attrs.get("material") or material
                comp_style = comp_attrs.get("style") or style
                comp_pattern = comp_attrs.get("pattern", "")
                
                # Build query with detected attributes
                query_parts = []
                if comp_color:
                    query_parts.append(comp_color)
                if comp_pattern and comp_pattern != "solid":
                    query_parts.append(comp_pattern)
                if comp_material:
                    query_parts.append(comp_material)
                if comp_style:
                    query_parts.append(comp_style)
                query_parts.append(base_query)

                search_query = " ".join(query_parts)
                self.logger.info(f"Searching bed component '{component_key}': {search_query}")

                products = []
                serp_count = 0
                exa_count = 0

                # Search via SERP
                if self.serp_client:
                    try:
                        serp_results = self.serp_client.search_and_analyze_products(
                            query=search_query,
                            space_type="bedroom",
                            num_results=10
                        )
                        serp_count = len(serp_results)
                        for p in serp_results:
                            p["source_api"] = "serp"
                        products.extend(serp_results)
                        self.logger.info(f"  {component_key} SERP: {serp_count} products")
                    except Exception as e:
                        self.logger.warning(f"SERP search failed for {component_key}: {e}")
                else:
                    self.logger.warning(f"  {component_key}: SERP client not available")

                # Search via Exa
                if self.exa_client:
                    try:
                        exa_results = self.exa_client.search_and_analyze_products(
                            query=search_query,
                            space_type="bedroom",
                            num_results=8,
                            similar_per_seed=2
                        )
                        exa_count = len(exa_results)
                        for p in exa_results:
                            p["source_api"] = "exa"
                        products.extend(exa_results)
                        self.logger.info(f"  {component_key} Exa: {exa_count} products")
                    except Exception as e:
                        self.logger.warning(f"Exa search failed for {component_key}: {e}")
                else:
                    self.logger.info(f"  {component_key}: Exa client not available")

                self.logger.info(f"  {component_key} total raw: {len(products)} (SERP: {serp_count}, Exa: {exa_count})")

                # Deduplicate
                before_dedup = len(products)
                products = self._dedupe_products_by_url(products)
                self.logger.info(f"  {component_key} after dedup: {len(products)} (removed {before_dedup - len(products)})")

                # Format products with improved image extraction
                formatted = []
                for p in products:
                    # Try multiple image sources
                    image_url = ""
                    images = p.get("images", [])
                    if images and len(images) > 0:
                        image_url = images[0]
                    elif p.get("thumbnail"):
                        image_url = p.get("thumbnail")
                    elif p.get("image"):
                        image_url = p.get("image")
                    elif p.get("image_url"):
                        image_url = p.get("image_url")

                    formatted.append({
                        "url": p.get("url", p.get("product_link", p.get("link", ""))),
                        "title": p.get("title", ""),
                        "image_url": image_url,
                        "store": p.get("store", p.get("source", "Unknown")),
                        "price_str": p.get("price_str", str(p.get("price", "")) if p.get("price") else ""),
                        "price": p.get("price") if isinstance(p.get("price"), (int, float)) else None,
                    })

                # Filter to those with images and limit to 4
                before_filter = len(formatted)
                formatted = self._filter_products_with_images(formatted, min_count=4)[:4]
                self.logger.info(f"  {component_key} final: {len(formatted)} products (filtered from {before_filter})")

                return (component_key, formatted)

            except Exception as e:
                self.logger.error(f"Failed to search bed component {component_key}: {e}")
                return (component_key, [])

        # Search all components in parallel (skip bed_frame if already populated from visual search)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(search_component, key, config): key
                for key, config in BED_COMPONENTS.items()
                if key not in components_results  # Skip if already populated (e.g., bed_frame from visual search)
            }

            for future in as_completed(futures):
                component_key, products = future.result()
                components_results[component_key] = products

        # Log results
        total_products = sum(len(prods) for prods in components_results.values())
        self.logger.info(f"Bed component search complete: {total_products} products across {len(components_results)} categories")

        return components_results

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

                sel_id = sel.id if hasattr(sel, 'id') else sel.get('id', 'sel')

                # Upload crop to ImgBB for public URL (required for Google Lens)
                crop_base64 = self._pil_to_base64(crop)
                public_url = self.upload_image_to_imgbb(crop_base64)

                # Perform Google Lens search
                matches = []
                if self.serp_client and public_url:
                    try:
                        serp_results = self.serp_client.reverse_image_search_google_lens_url(public_url)
                        # Normalize results
                        for m in serp_results[:10]:
                            matches.append({
                                "title": m.get("title"),
                                "url": m.get("link") or m.get("product_link", ""),
                                "source": m.get("source"),
                                "thumbnail": m.get("thumbnail"),
                                "match_type": m.get("match_type", "visual"),
                            })
                    except Exception as e:
                        self.logger.warning(f"Reverse search failed for {sel_id}: {e}")
                elif not public_url:
                    self.logger.warning(f"ImgBB upload failed for {sel_id}, skipping Google Lens")

                # Validate matches with Exa (filter non-product pages)
                if self.exa_client and matches:
                    urls_to_validate = [m.get("url") for m in matches if m.get("url")]
                    if urls_to_validate:
                        validation_results = self.exa_client.validate_product_urls_batch(
                            urls=urls_to_validate,
                            batch_size=5,
                            max_chars=2000
                        )
                        # Filter to only valid product pages
                        validated_matches = []
                        for m in matches:
                            url = m.get("url", "")
                            if url in validation_results:
                                if validation_results[url].get("is_valid"):
                                    m["exa_validated"] = True
                                    validated_matches.append(m)
                            else:
                                # URL wasn't validated, include with warning
                                m["exa_validated"] = False
                                validated_matches.append(m)

                        # Fallback: if fewer than 3 pass, return original
                        if len(validated_matches) >= 3 or len(matches) < 3:
                            matches = validated_matches
                        else:
                            self.logger.warning(f"Only {len(validated_matches)} matches passed Exa validation, returning unfiltered")

                results.append({
                    "id": sel_id,
                    "image_url": public_url,
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

            return {
                "detections": detections,
                "source_image_width": width,
                "source_image_height": height,
            }

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

    # =========================================================================
    # Process Furniture Selection (URL Resolution + Affiliate Cart)
    # =========================================================================

    def process_furniture_selection(
        self,
        project_id: str,
        selected_products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process selected furniture products:
        1. Resolve any Google Shopping URLs using Exa
        2. Group by retailer using AffiliateClient
        3. Generate affiliate links and cart URLs

        Args:
            project_id: The project ID
            selected_products: List of products selected by the user

        Returns:
            Dict with resolved_products, retailer_carts, and stats
        """
        from urllib.parse import urlparse

        if not selected_products:
            return {
                "resolved_products": [],
                "retailer_carts": [],
                "total_products": 0,
                "resolved_count": 0,
                "unresolved_count": 0
            }

        # Step 1: Extract URLs and resolve Google Shopping URLs
        urls = [p.get("url", "") for p in selected_products if p.get("url")]
        resolution_results = {}

        if self.exa_client:
            try:
                resolution_results = self.exa_client.resolve_urls_batch(urls)
            except Exception as e:
                logging.error(f"URL resolution failed: {e}")
                # Fall back to using original URLs
                for url in urls:
                    resolution_results[url] = {
                        "is_google_shopping": False,
                        "resolved_url": url,
                        "resolution_success": True
                    }

        # Step 2: Build resolved products list
        resolved_products = []
        for product in selected_products:
            original_url = product.get("url", "")
            resolution = resolution_results.get(original_url, {})

            resolved_url = resolution.get("resolved_url") or original_url
            was_google_shopping = resolution.get("is_google_shopping", False)

            resolved_products.append({
                "original_url": original_url,
                "resolved_url": resolved_url,
                "title": product.get("title", ""),
                "image_url": product.get("image_url", ""),
                "store": product.get("store", ""),
                "price_str": product.get("price_str", ""),
                "was_google_shopping": was_google_shopping,
                "affiliate_url": None,
                "product_id": None,
            })

        # Step 3: Group by retailer and generate affiliate carts
        affiliate_client = AffiliateClient()
        resolved_urls = [p["resolved_url"] for p in resolved_products if p["resolved_url"]]

        # Process URLs through affiliate client
        grouped = affiliate_client.process_urls(resolved_urls)

        # Step 4: Build retailer carts and update resolved products with affiliate info
        retailer_carts = []
        url_to_affiliate_info = {}

        for retailer, products in grouped.items():
            product_ids = []
            cart_domain = None

            for prod in products:
                url_to_affiliate_info[prod["original_url"]] = {
                    "affiliate_url": prod["affiliate_url"],
                    "product_id": prod["product_id"],
                }
                if prod["product_id"] and prod["product_id"] != "unknown":
                    product_ids.append(prod["product_id"])

                # Preserve domain for regional Amazon
                if retailer == "amazon" and not cart_domain:
                    parsed = urlparse(prod["original_url"])
                    if parsed.netloc and "amazon." in parsed.netloc:
                        cart_domain = parsed.netloc

            # Generate cart URL
            cart_url = affiliate_client.generate_cart_url(
                retailer, product_ids, domain=cart_domain
            ) if product_ids else None

            retailer_carts.append({
                "retailer": retailer,
                "retailer_display_name": affiliate_client.get_retailer_display_name(retailer),
                "products": products,
                "cart_url": cart_url,
                "product_count": len(products)
            })

        # Update resolved products with affiliate info
        for rp in resolved_products:
            affiliate_info = url_to_affiliate_info.get(rp["resolved_url"], {})
            rp["affiliate_url"] = affiliate_info.get("affiliate_url")
            rp["product_id"] = affiliate_info.get("product_id")

        # Calculate stats
        resolved_count = sum(
            1 for r in resolution_results.values()
            if r.get("resolution_success")
        )

        return {
            "resolved_products": resolved_products,
            "retailer_carts": retailer_carts,
            "total_products": len(selected_products),
            "resolved_count": resolved_count,
            "unresolved_count": len(urls) - resolved_count
        }


# Global instance
data_manager = DataManager()
