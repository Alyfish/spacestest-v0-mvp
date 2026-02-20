"""
Spatial Utilities for Furniture Detection using Gemini 3.0 Flash
"""
import base64
import json
import logging
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, List
from PIL import Image
from google import genai
from google.genai import types

logger = logging.getLogger("spaces_ai.spatial")


class SpatialDetector:
    """Gemini-powered spatial object detection for furniture."""
    
    def __init__(self):
        """Initialize the Gemini client for spatial detection."""
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment")
        
        self.client = genai.Client(api_key=self.api_key)
        # Using Gemini 3 Flash for spatial detection
        self.model = "gemini-3-flash-preview"
        logger.info(f"SpatialDetector initialized with model: {self.model}")
    
    def get_object_bbox(
        self,
        image_bytes: bytes,
        click_x: float,
        click_y: float,
        image_width: int = None,
        image_height: int = None,
        space_type: str = None
    ) -> Dict[str, Any]:
        """
        Detect furniture objects at the click location.
        
        Args:
            image_bytes: Raw image bytes (PNG/JPEG)
            click_x: Normalized x coordinate (0.0 to 1.0)
            click_y: Normalized y coordinate (0.0 to 1.0)
            
        Returns:
            Dictionary with label, bbox, attributes, confidence, search_query
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            try:
                from PIL import ImageOps
                original_size = image.size
                image = ImageOps.exif_transpose(image)
                if image.mode != "RGB":
                    image = image.convert("RGB")
                if image.size != original_size:
                    logger.info(
                        f"EXIF normalization changed image: {original_size} -> {image.size}"
                    )
            except Exception:
                if image.mode != "RGB":
                    image = image.convert("RGB")
            if image_width is None:
                image_width = image.width
            if image_height is None:
                image_height = image.height
            
            click_x_pct = int(click_x * 100)
            click_y_pct = int(click_y * 100)

            _add_confidence = os.getenv("MARKERS_ADD_CONFIDENCE", "0") == "1"
            confidence_fields = (
                ',\n        "confidence": 0.0-1.0,\n'
                '        "reasoning_short": "1-sentence explanation of detection"'
                if _add_confidence else ""
            )

            prompt = f"""Analyze this interior room image. The user clicked at ({click_x_pct}% from left, {click_y_pct}% from top).

CLICK PROXIMITY RULE (CRITICAL - READ FIRST):
The PRIMARY item MUST be the object that the user's click point ({click_x_pct}%, {click_y_pct}%) is DIRECTLY on.
- If clicking on a LAMP sitting on a nightstand, primary = "table lamp", NOT "nightstand"
- If clicking on a VASE on a console table, primary = "vase", NOT "console table"
- If clicking on a PLANT on a side table, primary = "potted plant", NOT "side table"
- If clicking on a BOOK on a shelf, primary = "book", NOT "bookshelf"
- Smaller decorative items (lamps, vases, plants, sculptures, clocks, picture frames) should be PRIMARY when clicked directly on them
- Larger furniture (tables, nightstands, consoles, shelves) should only be PRIMARY if the click is NOT on a smaller item sitting on them
- The supporting furniture goes in additional_items when a smaller item is clicked

EXCEPTION - BED PRIORITY: This rule does NOT apply to beds. Clicking anywhere on a bed area (headboard, mattress, bedding, pillows) should ALWAYS return the bed frame as PRIMARY (see BED FRAME PRIORITY RULE below).

TASK: Identify ALL DISTINCT furniture and decor items at or overlapping this click location.

IMPORTANT - SEPARATE OVERLAPPING ITEMS:
- A lamp ON a nightstand = 2 items: "table lamp" (PRIMARY if clicked on lamp) AND "nightstand" (in additional_items)
- Bedding ON a bed = multiple items: "bed frame" (ALWAYS PRIMARY), "duvet/comforter" (additional), "pillows" (additional)

CRITICAL DISTINCTIONS FOR BEDS:
- "bed frame" = the STRUCTURAL furniture piece (headboard, footboard, rails, legs) - this is FURNITURE
- "bedding/duvet/comforter" = the FABRIC covering ON TOP of the bed - this is TEXTILE
- "pillows" = cushions on the bed - these are ACCESSORIES
- An "upholstered bed" is a BED FRAME with fabric upholstery - it is NOT bedding
- Note distinctive features: tufting style (channel, button, diamond), headboard shape (wingback, panel, arched), leg material/color (gold, brass, wood, chrome)

BED FRAME PRIORITY RULE (CRITICAL - ALWAYS FOLLOW):
- If the click is ANYWHERE on or near a bed (headboard, mattress, bedding, pillows, footboard, frame rails, or any part of the bed area), the PRIMARY item MUST ALWAYS be a bed frame variant
- Use specific bed frame labels like: "platform bed", "upholstered bed frame", "panel bed", "tufted bed frame", "sleigh bed", "canopy bed", "storage bed", "channel tufted bed", "wingback bed"
- NEVER return "bedding", "duvet", "comforter", "quilt", "sheets", or "pillows" as the PRIMARY item - these MUST ONLY appear in ADDITIONAL_ITEMS
- If you see upholstered/tufted furniture that is bed-sized (large enough to sleep on), ALWAYS label it as "[style] bed frame" or "[style] bed", NOT "[style] furniture" or "[style] upholstered piece"
- The bed frame is ALWAYS the most important item when clicking on a bed, regardless of where on the bed the user clicked

BE SPECIFIC with labels:
- "channel tufted upholstered bed" not "duvet cover"
- "wingback upholstered bed frame" not "comforter"
- "brass table lamp" not "lamp"
- "tufted armchair" not "chair"

Return JSON with this EXACT structure:
{{
    "primary": {{
        "label": "most prominent/clicked item",
        "bbox": [ymin, xmin, ymax, xmax],
        "color": "primary color",
        "material": "main material (wood, upholstered fabric, metal, etc)",
        "style": "design style (modern, art deco, traditional, etc)",
        "search_query": "4-6 word shopping query for finding this exact item"{confidence_fields}
    }},
    "additional_items": [
        {{
            "label": "another distinct item at this location",
            "bbox": [ymin, xmin, ymax, xmax],
            "color": "color",
            "material": "material",
            "search_query": "shopping query"
        }}
    ]
}}

BBOX: Use 0-1000 scale (0=top/left, 1000=bottom/right).
Return ONLY valid JSON, no markdown."""

            # Determine mime type
            image_format = image.format or "JPEG"
            mime_type = f"image/{image_format.lower()}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"
            
            print(f"🔎 SpatialDetector: Analyzing click at ({click_x:.2f}, {click_y:.2f})")
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            types.Part.from_text(text=prompt),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )
            
            raw_text = response.text.strip() if response.text else ""
            print(f"📝 SpatialDetector raw response (first 500 chars): {raw_text[:500]}")
            
            result = self._parse_gemini_response(raw_text)
            
            if not result:
                print(f"⚠️ SpatialDetector: Failed to parse response, using fallback. Raw: {raw_text[:200]}")
                return self._fallback_detection(click_x, click_y, space_type)

            primary = result.get("primary", {})
            if not primary or not primary.get("label"):
                print(f"⚠️ SpatialDetector: No primary detection in result: {result}. Using fallback")
                return self._fallback_detection(click_x, click_y, space_type)
            
            # Parse bbox
            bbox = primary.get("bbox", [0, 0, 1000, 1000])
            try:
                bbox = [int(b) for b in bbox]
            except (ValueError, TypeError):
                bbox = [0, 0, 1000, 1000]
            
            bbox_normalized = [b / 1000.0 for b in bbox]
            
            # Parse additional items
            additional_items = []
            for item in result.get("additional_items", []):
                if item and item.get("label"):
                    item_bbox = item.get("bbox", [0, 0, 1000, 1000])
                    try:
                        item_bbox = [int(b) for b in item_bbox]
                        item_bbox_norm = [b / 1000.0 for b in item_bbox]
                    except (ValueError, TypeError):
                        item_bbox_norm = [0, 0, 1, 1]
                    
                    additional_items.append({
                        "label": item.get("label"),
                        "bbox_normalized": item_bbox_norm,
                        "color": item.get("color", "unknown"),
                        "material": item.get("material", "unknown"),
                        "search_query": item.get("search_query", item.get("label")),
                    })
            
            detected_label = primary.get("label", "furniture")
            print(f"✅ SpatialDetector: Detected '{detected_label}' at bbox {bbox_normalized}")
            
            detection_confidence = 0.90
            reasoning_short = ""
            if _add_confidence:
                try:
                    detection_confidence = float(primary.get("confidence", 0.7))
                except (ValueError, TypeError):
                    detection_confidence = 0.7
                reasoning_short = str(primary.get("reasoning_short", ""))

            result_dict = {
                "label": detected_label,
                "bbox": bbox,
                "bbox_normalized": bbox_normalized,
                "attributes": {
                    "color": primary.get("color", "unknown"),
                    "material": primary.get("material", "unknown"),
                    "style": primary.get("style", "unknown"),
                },
                "confidence": detection_confidence,
                "search_query": primary.get("search_query", primary.get("label", "furniture")),
                "click_point": {"x": click_x, "y": click_y},
                "additional_items": additional_items,
            }
            if _add_confidence and reasoning_short:
                result_dict["reasoning_short"] = reasoning_short
            return result_dict
            
        except Exception as e:
            logger.error(f"Spatial detection failed: {e}", exc_info=True)
            print(f"❌ SpatialDetector error: {e}")
            return self._fallback_detection(click_x, click_y, space_type)

    def _parse_gemini_response(self, response_text: str) -> Optional[Dict]:
        """Parse Gemini response, handling various formats."""
        # Strip markdown code blocks if present
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON object from text
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _fallback_detection(self, click_x: float, click_y: float, space_type: str = None) -> Dict[str, Any]:
        """Return a fallback detection when Gemini fails.

        Returns generic "furniture" - the caller should use CLIP to classify
        the cropped region for accurate furniture type detection.
        """
        box_size = 0.20  # 20% box around click point
        bbox_normalized = [
            max(0, click_y - box_size / 2),  # ymin
            max(0, click_x - box_size / 2),  # xmin
            min(1, click_y + box_size / 2),  # ymax
            min(1, click_x + box_size / 2),  # xmax
        ]

        print(f"⚠️ Using fallback detection (space_type={space_type}, click=({click_x:.2f}, {click_y:.2f}))")
        print(f"   ℹ️ CLIP will be used to classify the cropped region")

        return {
            "label": "furniture",  # Generic - CLIP will refine this
            "bbox": [int(b * 1000) for b in bbox_normalized],
            "bbox_normalized": bbox_normalized,
            "attributes": {"color": "unknown", "material": "unknown", "style": "unknown"},
            "confidence": 0.3,
            "search_query": "furniture",
            "click_point": {"x": click_x, "y": click_y},
            "additional_items": [],
            "fallback": True,
        }


def smart_crop(image: Image.Image, bbox_normalized: list, padding: float = 0.05) -> Image.Image:
    """Crop image using normalized bbox [ymin, xmin, ymax, xmax] with padding."""
    width, height = image.size
    ymin, xmin, ymax, xmax = bbox_normalized
    
    # Apply padding
    ymin = max(0, ymin - padding)
    xmin = max(0, xmin - padding)
    ymax = min(1, ymax + padding)
    xmax = min(1, xmax + padding)
    
    # Convert to pixels
    left = int(xmin * width)
    top = int(ymin * height)
    right = int(xmax * width)
    bottom = int(ymax * height)
    
    # Ensure valid dimensions
    if right <= left:
        right = left + 50
    if bottom <= top:
        bottom = top + 50
    
    print(f"📐 smart_crop: bbox={bbox_normalized} -> pixels=({left}, {top}, {right}, {bottom})")
    
    return image.crop((left, top, right, bottom))
