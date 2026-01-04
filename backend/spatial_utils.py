import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from google import genai
from google.genai import types

class SpatialDetector:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logging.warning("GOOGLE_API_KEY not found in environment variables")
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash"  # Best available spatial detection model
        
    def get_object_bbox(self, image_bytes: bytes, click_x: float, click_y: float, image_width: int = None, image_height: int = None) -> Dict[str, Any]:
        """
        Detect furniture objects at click location using Gemini Vision.
        Returns: label, bbox, attributes, confidence.
        
        Args:
            image_bytes: Raw image bytes
            click_x: Normalized x coordinate (0-1)
            click_y: Normalized y coordinate (0-1)
            image_width: Original image width (optional, for logging)
            image_height: Original image height (optional, for logging)
            
        Returns:
            Dict containing detection details
        """
        try:
            click_x_pct = int(click_x * 100)
            click_y_pct = int(click_y * 100)
            
            prompt = f"""Analyze this interior room image. The user clicked at ({click_x_pct}% from left, {click_y_pct}% from top).
            
            TASK: Identify ALL DISTINCT furniture and decor items at or overlapping this click location.
             Focus specifically on the item the user likely intended to select (e.g. sofa, chair, table, lamp).
            
            Return JSON with this EXACT structure:
            {{
                "primary": {{
                    "label": "most prominent/clicked item",
                    "bbox": [ymin, xmin, ymax, xmax],
                    "attributes": {{
                        "color": "primary color",
                        "material": "main material",
                        "style": "design style"
                    }},
                    "search_query": "4-6 word shopping query"
                }}
            }}
            BBOX: Use 0-1000 scale (ymin, xmin, ymax, xmax).
            """
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                            types.Part.from_text(text=prompt),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1, 
                    max_output_tokens=2048
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini")
                
            result = json.loads(response.text)
            primary = result.get("primary", {})
            
            # Normalize bbox from 0-1000 to 0-1
            raw_bbox = primary.get("bbox", [0, 0, 1000, 1000])
            bbox_normalized = [x / 1000.0 for x in raw_bbox]
            
            return {
                "label": primary.get("label", "furniture"),
                "bbox_normalized": bbox_normalized,
                "attributes": primary.get("attributes", {}),
                "search_query": primary.get("search_query", ""),
                "confidence": 0.95 # Gemini is usually confident
            }
            
        except Exception as e:
            logging.error(f"Error in Gemini Spatial Detection: {e}")
            # Fallback for error cases
            return {
                "label": "furniture",
                "bbox_normalized": [0.2, 0.2, 0.8, 0.8], # Fallback fast crop
                "attributes": {},
                "search_query": "furniture",
                "confidence": 0.0
            }

def smart_crop(image: Image.Image, bbox_normalized: List[float], padding: float = 0.05) -> Image.Image:
    """
    Crop image based on normalized bbox [ymin, xmin, ymax, xmax] with padding.
    
    Args:
        image: PIL Image object
        bbox_normalized: List of [ymin, xmin, ymax, xmax] (0-1 range)
        padding: Padding percentage to add around the box (default 0.05 = 5%)
        
    Returns:
        Cropped PIL Image
    """
    width, height = image.size
    
    # Unpack bbox (Gemini returns [ymin, xmin, ymax, xmax])
    ymin, xmin, ymax, xmax = bbox_normalized
    
    # Expand box by padding
    ymin_pad = max(0, ymin - padding)
    xmin_pad = max(0, xmin - padding)
    ymax_pad = min(1, ymax + padding)
    xmax_pad = min(1, xmax + padding)
    
    # Convert to pixels
    left = int(xmin_pad * width)
    top = int(ymin_pad * height)
    right = int(xmax_pad * width)
    bottom = int(ymax_pad * height)
    
    # Ensure dimensions are valid
    if right <= left or bottom <= top:
        # Fallback to center crop if box is invalid
        return image.crop((
            int(width * 0.25), 
            int(height * 0.25), 
            int(width * 0.75), 
            int(height * 0.75)
        ))
    
    return image.crop((left, top, right, bottom))
