"""
CLIP Client for Image-based Furniture Search

This module provides CLIP (Contrastive Language-Image Pre-training) functionality
for enhanced image-to-product matching and reverse image search.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Type
from pathlib import Path
import base64
from io import BytesIO

from retry import retry_sync

try:
    import torch
    from PIL import Image, ImageOps
    from transformers import CLIPProcessor, CLIPModel
    import numpy as np
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logging.warning("CLIP dependencies not available. Install with: pip install transformers torch pillow")


class CLIPClient:
    """Client for CLIP-based image analysis and similarity matching"""

    def __init__(self, model_name: str = None):
        """
        Initialize CLIP client with specified model

        Args:
            model_name: HuggingFace model identifier for CLIP. If None, uses
                       feature flag to select between base and large models.
        """
        self.logger = logging.getLogger("spaces_ai.clip")

        if not CLIP_AVAILABLE:
            self.logger.error("CLIP dependencies not available")
            self.model = None
            self.processor = None
            return

        # Select model based on feature flag if not explicitly provided
        if model_name is None:
            try:
                from config import FeatureFlags
                if FeatureFlags.USE_CLIP_LARGE:
                    model_name = "openai/clip-vit-large-patch14"
                else:
                    model_name = "openai/clip-vit-base-patch32"
            except ImportError:
                # Fallback to base model if config not available
                model_name = "openai/clip-vit-base-patch32"

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
                    # Handle file path (could be user photo)
                    img = Image.open(image_input)
                    img = ImageOps.exif_transpose(img)
                    image = img.convert("RGB")
            elif isinstance(image_input, Path):
                img = Image.open(image_input)
                img = ImageOps.exif_transpose(img)
                image = img.convert("RGB")
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
    
    def analyze_furniture_region(self, image_input, crop_ratio: float = None) -> Dict[str, Any]:
        """
        Analyze a furniture region and generate descriptive attributes

        Args:
            image_input: Image to analyze (PIL Image, path, or base64)
            crop_ratio: Size of crop relative to full image (0.0-1.0).
                        Used to deprioritize large furniture if crop is small.
                        A side table crop is typically ~5-10% of image area,
                        while a bed would be ~30-50%.

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

            # Check feature flag for vocabulary selection
            try:
                from config import FeatureFlags, FURNITURE_TYPES_EXPANDED, STYLES_EXPANDED, MATERIALS_EXPANDED, COLORS_EXPANDED
                use_expanded = FeatureFlags.EXPANDED_VOCABULARY
            except ImportError:
                use_expanded = False

            if use_expanded:
                # Expanded vocabulary for better matching accuracy
                furniture_types = FURNITURE_TYPES_EXPANDED
                styles = STYLES_EXPANDED
                materials = MATERIALS_EXPANDED
                colors = COLORS_EXPANDED
            else:
                # Original vocabulary (fallback)
                furniture_types = [
                    "sofa", "chair", "table", "lamp", "cabinet", "bed",
                    "desk", "shelf", "dresser", "couch", "ottoman", "bench",
                    "coffee table", "dining table", "side table", "nightstand"
                ]
                styles = [
                    "modern", "contemporary", "traditional", "rustic", "industrial",
                    "minimalist", "mid-century", "scandinavian", "vintage", "bohemian"
                ]
                materials = [
                    "wood", "wooden", "leather", "fabric", "metal", "glass",
                    "velvet", "linen", "rattan", "marble", "concrete"
                ]
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

            # Size-based deprioritization: If crop is small (<15% of image),
            # deprioritize large furniture types that are unlikely to fit
            # in such a small area (e.g., bed, sofa, sectional, dining table)
            LARGE_FURNITURE = {
                "bed", "trundle bed", "sofa", "sectional", "dining table",
                "sectional sofa", "king bed", "queen bed", "sleeper sofa",
                "l-shaped sectional", "u-shaped sectional"
            }
            if crop_ratio is not None and crop_ratio < 0.15:
                self.logger.debug(
                    f"Small crop detected (ratio={crop_ratio:.3f}), "
                    f"deprioritizing large furniture types"
                )
                adjusted_scores = []
                for name, score in furniture_scores:
                    if name.lower() in LARGE_FURNITURE:
                        # Halve confidence for large furniture in small crops
                        adjusted_score = score * 0.5
                        self.logger.debug(
                            f"  Deprioritized '{name}': {score:.3f} -> {adjusted_score:.3f}"
                        )
                        adjusted_scores.append((name, adjusted_score))
                    else:
                        adjusted_scores.append((name, score))
                # Re-sort after adjustment
                furniture_scores = sorted(adjusted_scores, key=lambda x: x[1], reverse=True)

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
    
    def generate_enhanced_search_query(
        self,
        image_input,
        vision_client=None,
        context: Optional[str] = None,
        max_len: int = 80,
        negative_keywords: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a concise search query with negatives: {Color} {Material} {Style} {Type} -decor -ideas.

        - Primary: use provided vision_client (e.g., Gemini/OpenAI) to extract keywords.
        - Fallback: use CLIP attribute analysis.
        """
        def truncate(q: str) -> str:
            return q[:max_len]

        neg_suffix = ""
        if negative_keywords:
            neg_suffix = " " + " ".join(f"-{k}" for k in negative_keywords)

        # Primary: structured extraction via vision client if provided
        if vision_client:
            try:
                from pydantic import BaseModel

                class ClipQueryParts(BaseModel):
                    color: str
                    material: str
                    item_type: str
                    style: Optional[str] = ""

                prompt = (
                    "Extract four concise keywords from this product crop: color, material, style, item type. "
                    "Keep each to 1-2 words. Return JSON with color, material, style, item_type."
                )

                parsed = vision_client.analyze_image_with_vision(  # type: ignore[attr-defined]
                    prompt=prompt,
                    pydantic_model=ClipQueryParts,
                    image_path=image_input if isinstance(image_input, (str, Path)) else None,
                    image=image_input if not isinstance(image_input, (str, Path)) else None,
                )

                parts = [
                    parsed.color.strip(),
                    parsed.material.strip(),
                    (parsed.style or "").strip(),
                    parsed.item_type.strip(),
                ]
                if context:
                    parts.insert(0, context)
                return truncate(" ".join([p for p in parts if p]) + neg_suffix or "furniture")
            except Exception as e:
                self.logger.warning(f"Vision query extraction failed, fallback to CLIP: {e}")

        # Fallback: CLIP attribute analysis
        if not self.is_available():
            return "furniture"

        try:
            analysis = self.analyze_furniture_region(image_input)

            if "error" in analysis:
                return "furniture"

            query_parts = []

            if analysis["color"]["confidence"] > 0.6:
                query_parts.append(analysis["color"]["name"])

            if analysis["material"]["confidence"] > 0.6:
                query_parts.append(analysis["material"]["name"])

            if analysis["style"]["confidence"] > 0.5:
                query_parts.append(analysis["style"]["name"])

            query_parts.append(analysis["furniture_type"]["name"])

            if context:
                query_parts.insert(0, context)

            return truncate(" ".join(query_parts) + neg_suffix) or "furniture"

        except Exception as e:
            self.logger.error(f"Failed to generate enhanced query: {e}")
            return "furniture"

    def validate_products_by_label(self, label: str, products: List[Dict[str, Any]], threshold: float = 0.40, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Validate and re-rank candidate products against a text label using CLIP.
        
        Args:
            label: The text label to validate against (e.g. "modern grey sofa")
            products: List of product dicts
            threshold: Minimum similarity score to keep a product
            top_k: Max products to return
            
        Returns:
            Filtered and sorted list of products
        """
        if not self.is_available():
            return products[:top_k]
            
        try:
            # 1. Encode the LABEL (text) to get a "ideal concept" vector
            text_embedding = self.encode_text(label)
            if text_embedding is None:
                return products[:top_k]
            
            validated = []
            
            for product in products:
                # 2. Get product thumbnail
                # Get best available image URL
                image_url = product.get('thumbnail') 
                if not image_url and product.get('images'):
                    image_url = product['images'][0]
                if not image_url: 
                    continue
                    
                # 3. Download and Encode product image
                # This needs a helper to download generic URLs
                image = self._download_image_from_url(image_url)
                if not image:
                    continue
                    
                img_embedding = self.encode_image(image)
                if img_embedding is None:
                    continue
                
                # 4. Compute similarity
                score = self.compute_similarity(text_embedding, img_embedding)
                
                product['clip_validation_score'] = score
                if score > threshold:
                    validated.append(product)
            
            # Sort by score
            validated.sort(key=lambda x: x.get('clip_validation_score', 0), reverse=True)
            return validated[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error in validate_products_by_label: {e}")
            return products[:top_k]

    @retry_sync(max_retries=2, base_delay=0.5, exponential_base=2.0)
    def _download_image_from_url(self, url: str) -> Optional[Image.Image]:
        """Helper to download image from URL safely with retry."""
        import requests
        try:
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                return Image.open(BytesIO(resp.content)).convert("RGB")
            # Return None for non-200 responses (don't retry these)
            return None
        except requests.exceptions.RequestException:
            # Let retry decorator handle connection/timeout errors
            raise
        except Exception:
            # PIL/image parsing errors - don't retry
            return None

    def rerank_products_by_visual_similarity(
        self,
        query_image: Image.Image,
        products: List[Dict[str, Any]],
        top_k: int = 12,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Re-rank products by image-to-image visual similarity to the query image.

        This provides more accurate matching than text-to-image similarity for
        finding visually similar products.

        Args:
            query_image: PIL Image of the furniture crop
            products: List of product dicts with thumbnail/image_url
            top_k: Maximum number of products to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            Products sorted by visual_similarity descending
        """
        if not self.is_available():
            return products[:top_k]

        try:
            # Encode query image
            query_embedding = self.encode_image(query_image)
            if query_embedding is None:
                self.logger.warning("Failed to encode query image")
                return products[:top_k]

            scored_products = []
            for product in products:
                # Get best available image URL
                img_url = (
                    product.get("thumbnail") or
                    product.get("image_url") or
                    (product.get("images") or [None])[0]
                )

                if not img_url:
                    product["visual_similarity"] = 0.0
                    scored_products.append(product)
                    continue

                try:
                    product_image = self._download_image_from_url(img_url)
                    if product_image:
                        product_embedding = self.encode_image(product_image)
                        if product_embedding is not None:
                            similarity = self.compute_similarity(query_embedding, product_embedding)
                            product["visual_similarity"] = float(similarity)
                        else:
                            product["visual_similarity"] = 0.0
                    else:
                        product["visual_similarity"] = 0.0
                except Exception as e:
                    self.logger.debug(f"Error scoring product: {e}")
                    product["visual_similarity"] = 0.0

                scored_products.append(product)

            # Sort by visual similarity descending
            scored_products.sort(key=lambda p: p.get("visual_similarity", 0), reverse=True)

            # Filter by minimum similarity if specified
            if min_similarity > 0:
                scored_products = [
                    p for p in scored_products
                    if p.get("visual_similarity", 0) >= min_similarity or
                    p.get("match_type") == "exact"  # Keep exact matches regardless
                ]

            # Log top matches for debugging
            top_3 = scored_products[:3]
            if top_3:
                self.logger.info(f"Top visual matches: {[(p.get('title', 'N/A')[:30], p.get('visual_similarity', 0)) for p in top_3]}")

            return scored_products[:top_k]

        except Exception as e:
            self.logger.error(f"Visual similarity reranking failed: {e}")
            return products[:top_k]

    # ===== ASYNC METHODS (Production-Ready Parallelization) =====

    async def rerank_products_async(
        self,
        query_image: "Image.Image",
        products: List[Dict[str, Any]],
        app_state,
        top_k: int = 12,
        min_similarity: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Async version of rerank_products_by_visual_similarity.

        Features:
        - Downloads images in parallel using async httpx
        - Batches CLIP encoding for GPU efficiency
        - Uses CLIP semaphore to avoid GPU thrash

        Args:
            query_image: PIL Image of the query/furniture crop
            products: List of product dicts with thumbnail/image_url
            app_state: FastAPI app.state with sems, http, clip_cache
            top_k: Maximum number of products to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            Products sorted by visual_similarity descending
        """
        import asyncio

        if not self.is_available():
            return products[:top_k]

        try:
            http = app_state.http
            sems = app_state.sems

            # Encode query image first (sync, but fast for single image)
            query_embedding = self.encode_image(query_image)
            if query_embedding is None:
                self.logger.warning("Failed to encode query image")
                return products[:top_k]

            # Extract image URLs
            url_to_product = {}
            for product in products:
                img_url = (
                    product.get("thumbnail")
                    or product.get("image_url")
                    or (product.get("images") or [None])[0]
                )
                if img_url:
                    url_to_product[img_url] = product

            if not url_to_product:
                return products[:top_k]

            # Download images in parallel
            from async_utils import download_image_safe

            urls = list(url_to_product.keys())
            download_tasks = [
                download_image_safe(http, sems["img_download"], url)
                for url in urls
            ]
            image_bytes_list = await asyncio.gather(*download_tasks)

            # Prepare valid images for batch encoding
            valid_images = []
            valid_urls = []
            for url, img_bytes in zip(urls, image_bytes_list):
                if img_bytes:
                    try:
                        img = Image.open(BytesIO(img_bytes)).convert("RGB")
                        valid_images.append(img)
                        valid_urls.append(url)
                    except Exception:
                        pass

            if not valid_images:
                # No valid images, return products with 0 similarity
                for product in products:
                    product["visual_similarity"] = 0.0
                return products[:top_k]

            # Batch encode all images using CLIP semaphore
            async with sems["clip"]:
                embeddings = await asyncio.to_thread(
                    self._batch_encode_images, valid_images
                )

            # Compute similarities and update products
            for url, embedding in zip(valid_urls, embeddings):
                if embedding is not None:
                    similarity = self.compute_similarity(query_embedding, embedding)
                    url_to_product[url]["visual_similarity"] = float(similarity)
                else:
                    url_to_product[url]["visual_similarity"] = 0.0

            # Set 0 for products without images
            for product in products:
                if "visual_similarity" not in product:
                    product["visual_similarity"] = 0.0

            # Sort by similarity
            products.sort(key=lambda p: p.get("visual_similarity", 0), reverse=True)

            # Filter by minimum similarity
            if min_similarity > 0:
                products = [
                    p for p in products
                    if p.get("visual_similarity", 0) >= min_similarity
                    or p.get("match_type") == "exact"
                ]

            return products[:top_k]

        except Exception as e:
            self.logger.error(f"Async visual reranking failed: {e}")
            return products[:top_k]

    def _batch_encode_images(self, images: List["Image.Image"]) -> List[Optional[np.ndarray]]:
        """
        Batch encode multiple images in a single GPU pass.

        Args:
            images: List of PIL Images

        Returns:
            List of embeddings (numpy arrays) or None for failed images
        """
        if not self.is_available() or not images:
            return [None] * len(images)

        try:
            with torch.no_grad():
                inputs = self.processor(
                    images=images,
                    return_tensors="pt",
                    padding=True,
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                embeddings = self.model.get_image_features(**inputs)
                embeddings = embeddings.cpu().numpy()

                # Normalize embeddings
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / (norms + 1e-8)

                return list(embeddings)
        except Exception as e:
            self.logger.error(f"Batch encoding failed: {e}")
            return [None] * len(images)

