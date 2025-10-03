"""
CLIP Client for Image-based Furniture Search

This module provides CLIP (Contrastive Language-Image Pre-training) functionality
for enhanced image-to-product matching and reverse image search.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import base64
from io import BytesIO

try:
    import torch
    from PIL import Image
    from transformers import CLIPProcessor, CLIPModel
    import numpy as np
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logging.warning("CLIP dependencies not available. Install with: pip install transformers torch pillow")


class CLIPClient:
    """Client for CLIP-based image analysis and similarity matching"""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initialize CLIP client with specified model
        
        Args:
            model_name: HuggingFace model identifier for CLIP
        """
        self.logger = logging.getLogger("spaces_ai.clip")
        
        if not CLIP_AVAILABLE:
            self.logger.error("CLIP dependencies not available")
            self.model = None
            self.processor = None
            return
        
        try:
            self.logger.info(f"Loading CLIP model: {model_name}")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model.eval()  # Set to evaluation mode
            self.logger.info(f"CLIP model loaded successfully on {self.device}")
        except Exception as e:
            self.logger.error(f"Failed to load CLIP model: {e}")
            self.model = None
            self.processor = None
    
    def is_available(self) -> bool:
        """Check if CLIP client is ready to use"""
        return self.model is not None and self.processor is not None
    
    def encode_image(self, image_input) -> Optional[np.ndarray]:
        """
        Encode an image into a CLIP embedding vector
        
        Args:
            image_input: Can be a PIL Image, file path (str/Path), or base64 string
            
        Returns:
            Numpy array of image embeddings, or None if encoding fails
        """
        if not self.is_available():
            self.logger.warning("CLIP model not available")
            return None
        
        try:
            # Convert input to PIL Image
            if isinstance(image_input, str):
                if image_input.startswith("data:image"):
                    # Handle base64 data URL
                    base64_str = image_input.split(",")[1]
                    image_bytes = base64.b64decode(base64_str)
                    image = Image.open(BytesIO(image_bytes)).convert("RGB")
                else:
                    # Handle file path
                    image = Image.open(image_input).convert("RGB")
            elif isinstance(image_input, Path):
                image = Image.open(image_input).convert("RGB")
            elif isinstance(image_input, Image.Image):
                image = image_input.convert("RGB")
            else:
                self.logger.error(f"Unsupported image input type: {type(image_input)}")
                return None
            
            # Process and encode
            with torch.no_grad():
                inputs = self.processor(images=image, return_tensors="pt").to(self.device)
                image_features = self.model.get_image_features(**inputs)
                
                # Normalize embeddings
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
                return image_features.cpu().numpy().flatten()
        
        except Exception as e:
            self.logger.error(f"Failed to encode image: {e}")
            return None
    
    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """
        Encode text into a CLIP embedding vector
        
        Args:
            text: Text description to encode
            
        Returns:
            Numpy array of text embeddings, or None if encoding fails
        """
        if not self.is_available():
            self.logger.warning("CLIP model not available")
            return None
        
        try:
            with torch.no_grad():
                inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)
                text_features = self.model.get_text_features(**inputs)
                
                # Normalize embeddings
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                return text_features.cpu().numpy().flatten()
        
        except Exception as e:
            self.logger.error(f"Failed to encode text: {e}")
            return None
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            # Convert to 0-1 range (from -1 to 1 range)
            return float((similarity + 1) / 2)
        except Exception as e:
            self.logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    def analyze_furniture_region(self, image_input) -> Dict[str, Any]:
        """
        Analyze a furniture region and generate descriptive attributes
        
        Args:
            image_input: Image to analyze (PIL Image, path, or base64)
            
        Returns:
            Dictionary with furniture attributes and descriptions
        """
        if not self.is_available():
            return {"error": "CLIP model not available"}
        
        try:
            # Get image embedding
            image_embedding = self.encode_image(image_input)
            if image_embedding is None:
                return {"error": "Failed to encode image"}
            
            # Furniture categories to check
            furniture_types = [
                "sofa", "chair", "table", "lamp", "cabinet", "bed", 
                "desk", "shelf", "dresser", "couch", "ottoman", "bench",
                "coffee table", "dining table", "side table", "nightstand"
            ]
            
            # Style attributes to check
            styles = [
                "modern", "contemporary", "traditional", "rustic", "industrial",
                "minimalist", "mid-century", "scandinavian", "vintage", "bohemian"
            ]
            
            # Material attributes
            materials = [
                "wood", "wooden", "leather", "fabric", "metal", "glass",
                "velvet", "linen", "rattan", "marble", "concrete"
            ]
            
            # Color attributes
            colors = [
                "white", "black", "gray", "brown", "beige", "blue",
                "green", "navy", "cream", "tan", "natural"
            ]
            
            # Score each category
            def score_categories(categories: List[str]) -> List[Tuple[str, float]]:
                scores = []
                for category in categories:
                    text_embedding = self.encode_text(category)
                    if text_embedding is not None:
                        similarity = self.compute_similarity(image_embedding, text_embedding)
                        scores.append((category, similarity))
                scores.sort(key=lambda x: x[1], reverse=True)
                return scores
            
            furniture_scores = score_categories(furniture_types)
            style_scores = score_categories(styles)
            material_scores = score_categories(materials)
            color_scores = score_categories(colors)
            
            # Get top matches
            top_furniture = furniture_scores[0] if furniture_scores else ("furniture", 0.5)
            top_style = style_scores[0] if style_scores else ("modern", 0.5)
            top_material = material_scores[0] if material_scores else ("wood", 0.5)
            top_color = color_scores[0] if color_scores else ("neutral", 0.5)
            
            # Generate search query
            search_query = f"{top_color[0]} {top_material[0]} {top_style[0]} {top_furniture[0]}"
            
            return {
                "search_query": search_query,
                "furniture_type": {
                    "name": top_furniture[0],
                    "confidence": float(top_furniture[1]),
                    "top_3": furniture_scores[:3]
                },
                "style": {
                    "name": top_style[0],
                    "confidence": float(top_style[1]),
                    "top_3": style_scores[:3]
                },
                "material": {
                    "name": top_material[0],
                    "confidence": float(top_material[1]),
                    "top_3": material_scores[:3]
                },
                "color": {
                    "name": top_color[0],
                    "confidence": float(top_color[1]),
                    "top_3": color_scores[:3]
                },
                "embedding": image_embedding.tolist()  # For future similarity searches
            }
        
        except Exception as e:
            self.logger.error(f"Failed to analyze furniture region: {e}", exc_info=True)
            return {"error": str(e)}
    
    def rank_products_by_image_similarity(
        self,
        query_image,
        products: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank products by visual similarity to query image
        
        Args:
            query_image: Query image (PIL Image, path, or base64)
            products: List of product dictionaries (must have 'image_url' or 'images' field)
            top_k: Return only top K results (None = all results)
            
        Returns:
            Products sorted by similarity score (highest first)
        """
        if not self.is_available():
            self.logger.warning("CLIP model not available, returning original order")
            return products
        
        try:
            # Encode query image
            query_embedding = self.encode_image(query_image)
            if query_embedding is None:
                return products
            
            # Score each product
            scored_products = []
            for product in products:
                try:
                    # Get product image URL
                    image_url = None
                    if "image_url" in product:
                        image_url = product["image_url"]
                    elif "images" in product and product["images"]:
                        image_url = product["images"][0]
                    
                    if not image_url:
                        # No image to compare
                        product["similarity_score"] = 0.0
                        scored_products.append(product)
                        continue
                    
                    # For now, we can't encode remote URLs directly
                    # This would require downloading the image first
                    # TODO: Add image downloading capability
                    product["similarity_score"] = 0.5  # Neutral score
                    scored_products.append(product)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to score product: {e}")
                    product["similarity_score"] = 0.0
                    scored_products.append(product)
            
            # Sort by similarity score
            scored_products.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            
            # Return top K if specified
            if top_k is not None:
                scored_products = scored_products[:top_k]
            
            return scored_products
        
        except Exception as e:
            self.logger.error(f"Failed to rank products: {e}")
            return products
    
    def generate_enhanced_search_query(self, image_input, context: Optional[str] = None) -> str:
        """
        Generate an enhanced search query using CLIP analysis
        
        Args:
            image_input: Image to analyze
            context: Optional additional context (room type, style preferences, etc.)
            
        Returns:
            Enhanced search query string
        """
        if not self.is_available():
            return "furniture"
        
        try:
            analysis = self.analyze_furniture_region(image_input)
            
            if "error" in analysis:
                return "furniture"
            
            # Build query from analysis
            query_parts = []
            
            # Add high-confidence attributes
            if analysis["color"]["confidence"] > 0.6:
                query_parts.append(analysis["color"]["name"])
            
            if analysis["material"]["confidence"] > 0.6:
                query_parts.append(analysis["material"]["name"])
            
            if analysis["style"]["confidence"] > 0.5:
                query_parts.append(analysis["style"]["name"])
            
            # Always add furniture type
            query_parts.append(analysis["furniture_type"]["name"])
            
            # Add context if provided
            if context:
                query_parts.insert(0, context)
            
            return " ".join(query_parts)
        
        except Exception as e:
            self.logger.error(f"Failed to generate enhanced query: {e}")
            return "furniture"

