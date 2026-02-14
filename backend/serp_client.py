"""
SerpAPI Client for product discovery and shopping search
Optimized for furniture and home decor product search with direct product links and images
"""

import logging
import os
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

from dotenv import load_dotenv
from serpapi import GoogleSearch
import requests
from PIL import Image

from cache_manager import cache_manager
from config import is_valid_product
from retry import retry_sync

load_dotenv()

logger = logging.getLogger("spaces_ai.serp")


class SerpClient:
    """Client for SerpAPI to find furniture products with direct links and images"""

    def __init__(self, api_key: str = None):
        """Initialize SERP client with API key"""
        if GoogleSearch is None:
            raise ImportError(
                "google-search-results package not installed. Install with: pip install google-search-results"
            )

        self.api_key = api_key or os.getenv("SERP_API_KEY")
        if not self.api_key:
            raise ValueError("SERP_API_KEY not found in environment variables")

        print(f"🔧 SERP Client initialized with API key: {self.api_key[:10]}...")

    @retry_sync(max_retries=3, base_delay=1.0, exponential_base=2.0)
    def search_products(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """
        Search for furniture products using Google Shopping (with caching)

        Args:
            query: Search query (e.g., "modern gray sectional sofa")
            num_results: Number of results to return

        Returns:
            Search results from SerpAPI Google Shopping
        """
        # Check cache first
        cached = cache_manager.get_product_search("serp", query, num_results)
        if cached is not None:
            logger.debug(f"Cache HIT for query: '{query[:40]}...'")
            return {"results": cached}

        try:
            print(f"[SERP_API] Query: '{query}' (requesting {num_results} results)")

            # Import feature flag for API selection
            from config import FeatureFlags

            # Use google_shopping_light for direct retailer URLs (preferred)
            # or fall back to legacy tbm=shop if flag is disabled
            if FeatureFlags.USE_SHOPPING_LIGHT_API:
                # google_shopping_light returns direct retailer URLs in 'link' field
                search = GoogleSearch(
                    {
                        "engine": "google_shopping_light",
                        "q": query,
                        "api_key": self.api_key,
                        "num": min(num_results, 20),
                        "hl": "en",
                        "gl": "us",
                    }
                )
                print(f"[SERP_API] Using google_shopping_light engine for direct retailer URLs")
            else:
                # Legacy: tbm=shop returns Google Shopping redirect URLs
                search = GoogleSearch(
                    {
                        "q": query,
                        "tbm": "shop",
                        "api_key": self.api_key,
                        "num": min(num_results, 20),
                        "hl": "en",
                        "gl": "us",
                    }
                )
                print(f"[SERP_API] Using legacy tbm=shop engine")

            result = search.get_dict()

            print(f"[SERP_API] Response keys: {list(result.keys())}")

            # Check for API errors first
            if "error" in result:
                print(f"[SERP_API] ERROR: {result['error']}")
                return {"error": result["error"], "results": []}

            # Get shopping results
            shopping_results = result.get("shopping_results", [])
            print(f"[SERP_API] Raw shopping_results count: {len(shopping_results)}")

            # Debug: Show first shopping result structure if available
            if shopping_results:
                first_result = shopping_results[0]
                print(f"📦 First shopping result fields: {list(first_result.keys())}")
                print(
                    f"📦 Sample: {first_result.get('title', 'No title')[:50]}... from {first_result.get('source', 'Unknown')}"
                )

                # Debug link fields to find the correct retailer URL
                print("🔗 Available link fields:")
                print(f"   - product_link: {first_result.get('product_link', 'None')}")
                print(f"   - link: {first_result.get('link', 'None')}")
                if "extensions" in first_result:
                    print(f"   - extensions: {first_result.get('extensions', [])}")
            else:
                print("❌ No shopping_results in SerpAPI response")

            # If no shopping results, try to return other relevant results
            if not shopping_results:
                print("⚠️ No shopping results, checking other result types...")
                organic_results = result.get("organic_results", [])
                images_results = result.get("images_results", [])
                print(
                    f"🔍 Organic results: {len(organic_results)}, Images: {len(images_results)}"
                )

                # Create shopping-format results from organic results as fallback
                if organic_results:
                    shopping_results = [
                        {
                            "title": item.get("title", ""),
                            "product_link": item.get(
                                "link", ""
                            ),  # Use product_link format
                            "source": item.get("displayed_link", ""),
                            "snippet": item.get("snippet", ""),
                            "price": "Check website for price",
                            "extracted_price": 0,
                            "rating": 0,
                            "reviews": 0,
                        }
                        for item in organic_results[:5]
                    ]
                    print(
                        f"🔧 Created {len(shopping_results)} fallback results from organic"
                    )

            # Build results list
            results_list = [
                {
                    # Map SerpAPI fields to our expected format
                    "url": self._extract_retailer_url(
                        item
                    ),  # Extract direct retailer URL
                    "title": item.get("title", ""),
                    "id": item.get("product_id", ""),
                    "score": 1.0,
                    "published_date": None,
                    "author": None,
                    "extract": item.get("snippet", ""),
                    "text": item.get("snippet", ""),
                    "highlights": [],
                    # SerpAPI Google Shopping specific fields
                    "price": item.get("price", ""),
                    "extracted_price": item.get("extracted_price", 0),
                    "source": item.get("source", ""),
                    "source_icon": item.get("source_icon", ""),
                    "thumbnail": item.get("thumbnail", ""),
                    "thumbnails": item.get("thumbnails", []),
                    "rating": item.get("rating", 0),
                    "reviews": item.get("reviews", 0),
                    "delivery": item.get("delivery", ""),
                    "installment": item.get(
                        "installment", {}
                    ),  # Monthly payment info
                }
                for item in shopping_results
            ]

            # Filter out plans, blueprints, PDFs - we need real furniture photos
            original_count = len(results_list)
            results_list = [r for r in results_list if is_valid_product(r.get("title", ""))]
            filtered_count = original_count - len(results_list)
            if filtered_count > 0:
                print(f"🗑️ Filtered out {filtered_count} non-product items (plans/blueprints/PDFs)")

            # Cache successful results
            if results_list:
                cache_manager.set_product_search("serp", query, num_results, results_list)

            return {"results": results_list}

        except Exception as e:
            print(f"Error searching products: {e}")
            import traceback

            traceback.print_exc()
            return {"error": str(e), "results": []}

    def get_product_details(
        self, search_results: List[Dict[str, Any]], max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract product information from SerpAPI search results

        Args:
            search_results: List of search results from SerpAPI
            max_results: Maximum number of results to process

        Returns:
            List of product details with pricing, availability, etc.
        """
        if not search_results:
            return []

        products = []
        for result in search_results[:max_results]:
            product = self._extract_product_info(result)
            if product:
                products.append(product)

        # Sort by rating and reviews (handle None values)
        products.sort(
            key=lambda x: (x.get("rating") or 0, x.get("reviews") or 0), reverse=True
        )
        return products

    @retry_sync(max_retries=3, base_delay=1.0, exponential_base=2.0)
    def search_images(
        self,
        query: str,
        num_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search Google Images for product images.

        Used for the recommended products feature to get more/better product images
        when Google Shopping returns limited results.

        Args:
            query: Search query (e.g., "modern bed frame")
            num_results: Number of results to return (max 20)

        Returns:
            List of image results with: original URL, thumbnail, title, source
        """
        # Check cache first
        cache_key = f"images_{query}_{num_results}"
        cached = cache_manager.get_product_search("serp_images", query, num_results)
        if cached is not None:
            logger.debug(f"Cache HIT for images query: '{query[:40]}...'")
            return cached

        try:
            print(f"[SERP_IMAGES] Query: '{query}' (requesting {num_results} results)")

            search = GoogleSearch({
                "q": query,
                "tbm": "isch",  # Image search
                "api_key": self.api_key,
                "num": min(num_results, 20),
                "hl": "en",
                "gl": "us",
            })

            result = search.get_dict()

            # Check for API errors
            if "error" in result:
                print(f"[SERP_IMAGES] ERROR: {result['error']}")
                return []

            images_results = result.get("images_results", [])
            print(f"[SERP_IMAGES] Raw results count: {len(images_results)}")

            results = []
            for item in images_results:
                source = item.get("source", "")

                # Filter out non-retailer sources
                source_lower = source.lower() if source else ""
                blocked_sources = [
                    "pinterest", "instagram", "youtube", "tiktok",
                    "flickr", "tumblr", "reddit", "twitter", "x.com",
                    "shutterstock", "istockphoto", "gettyimages", "alamy",
                    "stock", "depositphotos", "dreamstime", "123rf",
                    "medium.com", "wordpress", "blogspot", "wixsite",
                ]

                if any(blocked in source_lower for blocked in blocked_sources):
                    continue

                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),  # Source page URL
                    "image_url": item.get("original", ""),  # Full-size image
                    "thumbnail": item.get("thumbnail", ""),
                    "source": source,  # Domain name
                    "position": item.get("position", 0),
                })

            print(f"[SERP_IMAGES] Filtered results: {len(results)} (removed {len(images_results) - len(results)} non-retailer)")

            # Cache successful results
            if results:
                cache_manager.set_product_search("serp_images", query, num_results, results)

            return results

        except Exception as e:
            print(f"[SERP_IMAGES] Error searching images: {e}")
            import traceback
            traceback.print_exc()
            return []

    def search_and_analyze_products(
        self, query: str, space_type: str, num_results: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Complete workflow: search for products and analyze them

        Args:
            query: Product search query
            space_type: Room type (bedroom, living room, etc.)
            num_results: Number of initial search results

        Returns:
            List of analyzed products with scores and details
        """
        # Search for products
        search_results = self.search_products(query, num_results)

        if "error" in search_results:
            return []

        # Get product details from search results
        products = self.get_product_details(search_results.get("results", []))

        # Enhance with space type context
        for product in products:
            product["space_type"] = space_type
            product["search_query"] = query

        print(f"✅ Returning {len(products)} real products (no mocks)")
        return products

    # --- Store trust scoring ---
    def _get_store_trust_score(self, product: Dict[str, Any]) -> float:
        """Get trust score for a product based on its retailer.

        Args:
            product: Product dictionary with 'source' or 'store' field

        Returns:
            Trust score between 0.0 and 1.0
        """
        try:
            from config import FeatureFlags, STORE_TRUST_SCORES
            if not FeatureFlags.STORE_TRUST_SCORES:
                return 0.70  # Default neutral score when feature disabled
        except ImportError:
            return 0.70

        # Get store name from product
        store = product.get("source", "") or product.get("store", "")
        store_lower = store.lower().strip()

        # Direct lookup
        if store_lower in STORE_TRUST_SCORES:
            return STORE_TRUST_SCORES[store_lower]

        # Partial match
        for store_key, score in STORE_TRUST_SCORES.items():
            if store_key in store_lower or store_lower in store_key:
                return score

        # Default score for unknown stores
        return STORE_TRUST_SCORES.get("default", 0.70)

    # --- Multi-signal scoring ---
    def _compute_multi_signal_score(
        self,
        product: Dict[str, Any],
        visual_similarity: float,
        query: str = ""
    ) -> float:
        """Compute a weighted multi-signal score for a product.

        Args:
            product: Product dictionary
            visual_similarity: CLIP visual similarity score (0-1)
            query: Optional search query for text relevance

        Returns:
            Combined score between 0.0 and 1.0
        """
        try:
            from config import FeatureFlags
            if not FeatureFlags.MULTI_SIGNAL_RANKING:
                # Return visual similarity only when multi-signal disabled
                return visual_similarity
        except ImportError:
            return visual_similarity

        # Weights for different signals
        weights = {
            "visual_similarity": 0.50,  # CLIP image match
            "text_relevance": 0.20,     # Title matches query
            "store_trust": 0.12,        # Quality retailer
            "rating": 0.08,             # Customer reviews
            "price_available": 0.10,    # Has clear pricing
        }

        scores = {}

        # Visual similarity (already computed)
        scores["visual_similarity"] = visual_similarity

        # Text relevance - check if query terms appear in title
        if query:
            title = product.get("title", "").lower()
            query_terms = query.lower().split()
            matching_terms = sum(1 for term in query_terms if term in title)
            scores["text_relevance"] = min(1.0, matching_terms / max(len(query_terms), 1))
        else:
            scores["text_relevance"] = 0.5  # Neutral when no query

        # Store trust
        scores["store_trust"] = self._get_store_trust_score(product)

        # Rating (normalize to 0-1, assume 5-star scale)
        rating = product.get("rating", 0) or 0
        scores["rating"] = min(1.0, rating / 5.0) if rating > 0 else 0.5

        # Price available (binary signal)
        has_price = bool(product.get("price") or product.get("extracted_price") or product.get("price_str"))
        scores["price_available"] = 1.0 if has_price else 0.3

        # Compute weighted sum
        total_score = sum(scores[key] * weights[key] for key in weights)

        # Store component scores for debugging
        product["_score_components"] = scores

        return total_score

    # --- CLIP-based thumbnail scoring ---
    def score_products_with_clip(
        self,
        products: List[Dict[str, Any]],
        clip_client,
        query_image,
        drop_threshold: float = 0.70,
        boost_threshold: float = 0.85,
        timeout: float = 1.5,
        max_workers: int = 8,
        max_fetch: int = 10,
        search_query: str = "",
    ) -> Dict[str, Any]:
        """Download SERP thumbnails in parallel and re-rank using CLIP similarity.

        Args:
            products: SERP-shaped product dictionaries.
            clip_client: CLIPClient instance (must support encode_image/compute_similarity).
            query_image: PIL image or path for the cropped query region.
            drop_threshold: Similarity below which items are discarded.
            boost_threshold: Similarity above which items are prioritized.
            timeout: Per-thumbnail fetch timeout in seconds.
            max_workers: Thread pool size for concurrent fetches.
            max_fetch: Max number of products to fetch/score (rest keep order).
            search_query: Optional search query for multi-signal text relevance.

        Returns:
            Dict with products (reordered/filtered) and scoring metadata.
        """
        # Check if multi-signal ranking is enabled
        use_multi_signal = False
        try:
            from config import FeatureFlags
            use_multi_signal = FeatureFlags.MULTI_SIGNAL_RANKING
        except ImportError:
            pass

        if not clip_client or not getattr(clip_client, "is_available", lambda: False)():
            return {
                "products": products,
                "meta": {"scoring": "skipped", "reason": "clip_unavailable"},
            }

        try:
            query_embedding = clip_client.encode_image(query_image)
            if query_embedding is None:
                return {
                    "products": products,
                    "meta": {"scoring": "skipped", "reason": "no_query_embedding"},
                }
        except Exception:
            return {
                "products": products,
                "meta": {"scoring": "skipped", "reason": "encode_query_failed"},
            }

        def pick_thumbnail(prod: Dict[str, Any]) -> Optional[str]:
            if prod.get("thumbnail"):
                return prod["thumbnail"]
            if prod.get("thumbnails"):
                # thumbnails may be list of strings or dicts
                first = prod["thumbnails"][0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    return first.get("link") or first.get("thumbnail")
            images = prod.get("images") or []
            if images:
                return images[0]
            if prod.get("image"):
                return prod.get("image")
            return None

        def fetch_image(url: str):
            try:
                resp = requests.get(url, timeout=timeout)
                if resp.status_code != 200:
                    return None
                return Image.open(BytesIO(resp.content)).convert("RGB")
            except Exception:
                return None

        # Fetch thumbnails concurrently
        scored: List[Dict[str, Any]] = []
        download_jobs = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx, prod in enumerate(products[:max_fetch]):
                url = pick_thumbnail(prod)
                if not url:
                    continue
                download_jobs[executor.submit(fetch_image, url)] = (idx, prod, url)

            for future in as_completed(download_jobs):
                idx, prod, url = download_jobs[future]
                image = future.result()
                if image is None:
                    prod["similarity_score"] = 0.0
                    prod["filter_reason"] = "thumb_fetch_failed"
                    prod["thumbnail_used"] = url
                    scored.append((idx, prod))
                    continue

                try:
                    thumb_embedding = clip_client.encode_image(image)
                    if thumb_embedding is None:
                        prod["similarity_score"] = 0.0
                        prod["filter_reason"] = "thumb_encode_failed"
                    else:
                        sim = clip_client.compute_similarity(query_embedding, thumb_embedding)
                        prod["similarity_score"] = sim

                        # Apply multi-signal ranking if enabled
                        if use_multi_signal:
                            prod["combined_score"] = self._compute_multi_signal_score(
                                prod, sim, search_query
                            )
                            prod["store_trust"] = self._get_store_trust_score(prod)
                        else:
                            prod["combined_score"] = sim

                        if sim < drop_threshold:
                            prod["filter_reason"] = "dropped_low_similarity"
                        elif sim > boost_threshold:
                            prod["filter_reason"] = "boosted_high_similarity"
                        else:
                            prod["filter_reason"] = "kept_neutral"
                    prod["thumbnail_used"] = url
                except Exception:
                    prod["similarity_score"] = 0.0
                    prod["filter_reason"] = "scoring_failed"
                    prod["thumbnail_used"] = url

                scored.append((idx, prod))

        # Merge scored results with unscored tail (keep original order for tail)
        scored_indices = {idx for idx, _ in scored}
        unscored = [prod for i, prod in enumerate(products) if i not in scored_indices]

        # Apply drop/boost logic
        kept = [p for _, p in scored if p.get("similarity_score", 0) >= drop_threshold]
        dropped = [p for _, p in scored if p.get("similarity_score", 0) < drop_threshold]

        # Sort by combined_score (multi-signal) or similarity_score
        sort_key = "combined_score" if use_multi_signal else "similarity_score"
        kept.sort(key=lambda p: p.get(sort_key, 0), reverse=True)
        boosted = [p for p in kept if p.get("similarity_score", 0) > boost_threshold]

        # Append unscored items after scored ones to preserve some completeness
        final_products = kept + unscored

        meta = {
            "scoring": "completed",
            "multi_signal_ranking": use_multi_signal,
            "thresholds": {"drop": drop_threshold, "boost": boost_threshold},
            "counts": {
                "input": len(products),
                "scored": len(scored),
                "kept": len(kept),
                "dropped": len(dropped),
                "boosted": len(boosted),
            },
        }

        return {"products": final_products, "meta": meta}

    # --- Google Shopping URL detection ---
    def _is_google_shopping_url(self, url: str) -> bool:
        """Check if URL is a Google Shopping redirect or intermediate page.

        Google Lens sometimes returns Google Shopping URLs instead of direct
        retailer URLs. These should be filtered out in favor of direct links.

        Args:
            url: URL to check

        Returns:
            True if URL is a Google Shopping URL that should be filtered
        """
        if not url:
            return False
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in [
            "google.com/shopping",
            "google.com/url?",
            "google.com/aclk",
            "shopping.google.com",
            "google.com/search",
        ])

    def _is_blocked_non_retailer(self, url: str, title: str = "") -> bool:
        """Check if URL or title indicates a non-retailer result.

        Two-tier filtering:
        1. Check title for DIY/plan/tutorial patterns (fast rejection)
        2. Check domain against non-retailer blocklist

        Args:
            url: URL to check
            title: Optional title to check for non-product patterns

        Returns:
            True if result should be blocked (not from a retailer)
        """
        from config import is_blocked_domain, is_non_product_title

        # Tier 1: Check title first (fastest rejection)
        if title and is_non_product_title(title):
            return True

        # Tier 2: Check domain blocklist
        if not url:
            return True

        if is_blocked_domain(url):
            return True

        # Also catch any google.com URLs not caught by _is_google_shopping_url
        if "google.com" in url.lower():
            return True

        return False

    # --- Google Lens reverse image search support ---
    def reverse_image_search_google_lens(self, image_path: str) -> List[Dict[str, Any]]:
        """Perform Google Lens reverse image search via SerpAPI.

        SerpAPI supports Google Lens through engine=google_lens and 'url' pointing to
        a publicly accessible image. For local development we can still send the
        local file by first base64 encoding in a data URL, but many times Lens API
        requires a remote URL. This implementation uses the local path; the backend
        can be extended to upload to a public host if needed.
        """
        try:
            # For development we will reuse Google Shopping product search fallback
            # by creating a quick descriptor based on filename; however SerpAPI's
            # Google Lens generally requires a public URL. We'll attempt calling it
            # directly to allow experimentation.
            params = {
                "engine": "google_lens",
                "url": f"file://{image_path}",  # many providers require public URL; dev fallback
                "api_key": self.api_key,
            }
            search = GoogleSearch(params)
            result = search.get_dict()

            # Extract visual_matches when available
            matches = []
            visual = result.get("visual_matches") or []
            for m in visual:
                matches.append({
                    "title": m.get("title"),
                    "link": m.get("link"),
                    "source": m.get("source"),
                    "thumbnail": m.get("thumbnail"),
                    "product_link": m.get("product_link") or m.get("link"),
                })

            # Fallback to inline_images / image_results if present
            if not matches:
                for m in result.get("inline_images", [])[:10]:
                    matches.append({
                        "title": m.get("title"),
                        "link": m.get("link"),
                        "source": m.get("source"),
                        "thumbnail": m.get("thumbnail"),
                    })

            return matches

        except Exception as e:
            print(f"Error in reverse_image_search_google_lens: {e}")
            return []

    def reverse_image_search_google_lens_url(self, image_url: str) -> List[Dict[str, Any]]:
        """Enhanced Google Lens search using all result types for better matching.

        Filters out Google Shopping URLs to return only direct retailer links.

        Args:
            image_url: Publicly accessible image URL

        Returns:
            List of match dicts with priority: exact_matches > visual_matches > knowledge_graph
        """
        try:
            params = {
                "engine": "google_lens",
                "url": image_url,
                "api_key": self.api_key,
            }
            search = GoogleSearch(params)
            result = search.get_dict()

            matches: List[Dict[str, Any]] = []
            seen_urls = set()
            filtered_counts = {
                "google_shopping": 0,
                "non_retailer": 0,
                "non_product_title": 0,
            }

            def _extract_best_url(match_data: Dict[str, Any]) -> Optional[str]:
                """Extract the best direct retailer URL from a match.

                Two-tier filtering:
                1. First check title for non-product patterns (DIY plans, tutorials, etc.)
                2. Then filter Google Shopping URLs and non-retailer domains

                Returns None if result should be blocked.
                """
                nonlocal filtered_counts

                title = match_data.get("title", "")
                product_link = match_data.get("product_link", "")
                link = match_data.get("link", "")

                # Tier 1: Check title first (fastest rejection)
                from config import is_non_product_title
                if title and is_non_product_title(title):
                    filtered_counts["non_product_title"] += 1
                    print(f"[LENS] Filtered non-product title: '{title[:50]}...'")
                    return None

                # Tier 2: Check URLs
                for candidate in [product_link, link]:
                    if not candidate:
                        continue

                    # Filter Google Shopping URLs
                    if self._is_google_shopping_url(candidate):
                        filtered_counts["google_shopping"] += 1
                        continue

                    # Filter non-retailer domains (Instagram, Pinterest, blogs, etc.)
                    if self._is_blocked_non_retailer(candidate, title):
                        filtered_counts["non_retailer"] += 1
                        print(f"[LENS] Filtered non-retailer: {candidate[:60]}...")
                        continue

                    # This candidate passed all filters
                    return candidate

                return None

            # Priority 1: exact_matches (identical/near-identical products - highest value)
            exact_count = 0
            for m in result.get("exact_matches", []) or []:
                url = _extract_best_url(m)
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    matches.append({
                        "title": m.get("title"),
                        "link": url,
                        "product_link": url,
                        "source": m.get("source"),
                        "thumbnail": m.get("thumbnail"),
                        "price": m.get("price"),
                        "match_type": "exact",
                    })
                    exact_count += 1
            if exact_count > 0:
                print(f"[LENS] Found {exact_count} exact matches")

            # Priority 2: visual_matches (visually similar products)
            visual_count = 0
            for m in result.get("visual_matches", []) or []:
                url = _extract_best_url(m)
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    matches.append({
                        "title": m.get("title"),
                        "link": url,
                        "product_link": url,
                        "source": m.get("source"),
                        "thumbnail": m.get("thumbnail"),
                        "price": m.get("price"),
                        "match_type": "visual",
                    })
                    visual_count += 1
            if visual_count > 0:
                print(f"[LENS] Found {visual_count} visual matches")

            # Priority 3: knowledge_graph products (product metadata)
            kg = result.get("knowledge_graph", {})
            kg_count = 0
            for item in kg.get("products", []) or []:
                url = _extract_best_url(item)
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    matches.append({
                        "title": item.get("title") or kg.get("title"),
                        "link": url,
                        "product_link": url,
                        "source": item.get("source"),
                        "thumbnail": item.get("thumbnail"),
                        "price": item.get("price"),
                        "match_type": "knowledge_graph",
                    })
                    kg_count += 1
            if kg_count > 0:
                print(f"[LENS] Found {kg_count} knowledge graph products")

            # Fallback to inline_images if no other matches found
            if not matches:
                for m in result.get("inline_images", [])[:10]:
                    url = _extract_best_url(m)
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        matches.append({
                            "title": m.get("title"),
                            "link": url,
                            "source": m.get("source"),
                            "thumbnail": m.get("thumbnail"),
                            "match_type": "inline",
                        })

            # Log filtering summary
            total_filtered = sum(filtered_counts.values())
            if total_filtered > 0:
                print(f"[LENS] Filtered: {filtered_counts['google_shopping']} Google Shopping, "
                      f"{filtered_counts['non_retailer']} non-retailer domains, "
                      f"{filtered_counts['non_product_title']} non-product titles")

            print(f"[LENS] Total matches: {len(matches)} (filtered {total_filtered})")
            return matches
        except Exception as e:
            print(f"Error in reverse_image_search_google_lens_url: {e}")
            return []

    def reverse_image_search(
        self, image_url: str, num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Backward-compatible reverse image search wrapper.

        Legacy callers use reverse_image_search(image_url, num_results=...).
        Internally this delegates to the Google Lens URL flow.
        """
        results = self.reverse_image_search_google_lens_url(image_url)
        if num_results <= 0:
            return []
        return results[:num_results]

    def _extract_retailer_url(self, shopping_result: Dict[str, Any]) -> str:
        """Extract the direct retailer URL instead of Google Shopping intermediate page.

        Priority order:
        1. 'link' field - google_shopping_light provides direct retailer URLs here
        2. 'product_link' field - may be direct or Google Shopping redirect
        3. Fallback to empty string if nothing found

        This method filters out Google Shopping URLs to ensure users get actual
        retailer links they can click and purchase from.
        """
        # Priority 1: 'link' field (google_shopping_light primary field with direct retailer URLs)
        direct_link = shopping_result.get("link")
        if direct_link and not self._is_google_shopping_url(direct_link):
            return direct_link

        # Priority 2: 'product_link' field - check if it's a direct retailer URL
        product_link = shopping_result.get("product_link", "")
        if product_link and not self._is_google_shopping_url(product_link):
            return product_link

        # Priority 3: If product_link is a Google Shopping URL, log warning but still return it
        # (better than nothing - user can at least see product on Google Shopping)
        source = shopping_result.get("source", "unknown")
        if product_link:
            print(f"⚠️ [SERP] Only Google Shopping URL available for {source}: {product_link[:60]}...")
            return product_link

        # No URL found
        print(f"❌ [SERP] No URL found for product from {source}")
        return ""

    def _extract_product_info(
        self, search_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract structured product information from SerpAPI search result"""
        try:
            url = search_result.get("url", "")
            title = search_result.get("title", "")
            # Basic shopping signals: price or rating or source
            has_price = bool(search_result.get("price"))
            has_source = bool(search_result.get("source"))
            has_thumb = bool(search_result.get("thumbnail"))

            if not url or not title or not (has_price or has_source or has_thumb):
                return None

            # SerpAPI provides store name directly in 'source' field
            store_name = search_result.get("source", "Unknown Store")

            # SerpAPI provides thumbnail and thumbnails array
            images = []
            if search_result.get("thumbnail"):
                images.append(search_result["thumbnail"])
            # Add additional thumbnails if available
            if search_result.get("thumbnails"):
                images.extend(search_result["thumbnails"])

            # SerpAPI provides both price string and extracted numeric price
            price_str = search_result.get("price", "")
            price_value = search_result.get("extracted_price", 0)

            # Build product info matching frontend expectations
            product_info = {
                "title": title,
                "url": url,
                "store": store_name,
                "price": float(price_value) if price_value else None,
                "price_str": price_str,
                "availability": "Available" if price_str else "Check availability",
                "images": images,
                "description": search_result.get("extract", ""),
                "rating": search_result.get("rating", 0),
                "reviews": search_result.get("reviews", 0),
                "delivery": search_result.get("delivery", "Standard shipping"),
                "relevance_score": 1.0,
                "materials": [],
                "colors": [],
                "dimensions": "",
                # Additional SerpAPI fields
                "source_icon": search_result.get("source_icon", ""),
                "installment": search_result.get("installment", {}),
            }

            return product_info

        except Exception as e:
            print(f"❌ Error extracting product info: {e}")
            return None

    def _extract_store_name(self, source: str, url: str) -> str:
        """Extract store name from source or URL"""
        if source:
            return source

        # Extract from URL if source not available
        try:
            from urllib.parse import urlparse

            domain = urlparse(url).netloc.lower()

            store_mapping = {
                "wayfair.com": "Wayfair",
                "westelm.com": "West Elm",
                "cb2.com": "CB2",
                "crateandbarrel.com": "Crate & Barrel",
                "potterybarn.com": "Pottery Barn",
                "article.com": "Article",
                "ikea.com": "IKEA",
                "amazon.com": "Amazon",
                "target.com": "Target",
                "homedepot.com": "Home Depot",
                "walmart.com": "Walmart",
                "overstock.com": "Overstock",
                "allmodern.com": "AllModern",
                "ashleyfurniture.com": "Ashley Furniture",
                "roomstogo.com": "Rooms To Go",
                "livingspaces.com": "Living Spaces",
                "homegoods.com": "HomeGoods",
            }

            for domain_key, store_name in store_mapping.items():
                if domain_key in domain:
                    return store_name

            # Default to capitalized domain
            return domain.replace("www.", "").replace(".com", "").title()

        except Exception:
            return "Unknown Store"

    def _extract_price(self, price_str: str) -> Optional[float]:
        """Extract numeric price from price string"""
        if not price_str:
            return None

        try:
            import re

            # Remove currency symbols and extract numbers
            price_match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
            if price_match:
                return float(price_match.group())
        except Exception:
            pass

        return None

    def _is_pdp_url(self, url: str) -> bool:
        """
        Check if URL is a Product Detail Page (PDP), not a search/category page.

        Args:
            url: URL to validate

        Returns:
            True if URL appears to be a PDP, False if it's a search/category page
        """
        url_lower = url.lower()

        # Reject patterns (search/category pages)
        reject_patterns = [
            "/s?",           # Amazon search
            "/s/",           # Target search
            "/keyword.php",  # Wayfair search
            "/search",       # Generic search
            "/browse/",      # Category browse
            "/collections/", # Shopify collections
            "/c/",           # Category shorthand
            "?q=",           # Query parameter
            "?k=",           # Keyword parameter
            "/filters/",     # Wayfair filters
            "/sb0/",         # Wayfair browse
            "/sb1/",         # Wayfair browse
            "/sb2/",         # Wayfair browse
        ]

        if any(pattern in url_lower for pattern in reject_patterns):
            return False

        # Accept patterns (PDP indicators)
        accept_patterns = [
            "/dp/",          # Amazon
            "/gp/product/",  # Amazon alternate
            "/ip/",          # Walmart
            "/p/",           # Target, generic
            "/pd/",          # Wayfair
            "/pdp/",         # Wayfair alternate
            "/product/",     # Generic
            "/-/A-",         # Target PDP
            "/item/",        # Overstock, generic
            "sku=",          # SKU parameter
            "/products/",    # Generic
        ]

        # If URL has a PDP pattern, accept it
        if any(pattern in url_lower for pattern in accept_patterns):
            return True

        # Default: reject if we can't confirm it's a PDP
        # (conservative - better to miss than return search pages)
        return False

    def _fallback_site_search(self, query: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Fallback: Use site-specific search to find a PDP if Product API fails.

        Args:
            query: Product search query
            domain: Retailer domain to search

        Returns:
            Product dict with PDP URL, or None if not found
        """
        try:
            # Use exact match query for better results
            search = GoogleSearch({
                "q": f'"{query}" site:{domain}',
                "api_key": self.api_key,
                "num": 5,
                "hl": "en",
                "gl": "us",
            })
            result = search.get_dict()

            for item in result.get("organic_results", []):
                link = item.get("link", "")
                if link and self._is_pdp_url(link):
                    store_name = domain.replace(".com", "").title()
                    print(f"[SERP] ✅ Fallback found {store_name} PDP: {link[:70]}...")
                    return {
                        "url": link,
                        "title": item.get("title", ""),
                        "store": store_name,
                        "price_str": "",
                        "thumbnail": item.get("thumbnail", ""),
                        "source_api": "serp_fallback_site_search",
                    }

        except Exception as e:
            print(f"[SERP] Fallback site search failed for {domain}: {e}")

        return None

    def resolve_google_shopping_url(
        self,
        google_url: str,
        max_products: int = 3,
        expected_retailer: Optional[str] = None,
        expected_domain: Optional[str] = None,
        strict_mode: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Resolve a Google Shopping URL to actual retailer PDP links.

        RETAILER-PRESERVING RESOLUTION:
        When expected_retailer is provided (e.g., "Quince"), we prioritize
        returning PDPs from that specific retailer, NOT marketplace alternatives.

        Resolution Priority:
        1. Try product_link from shopping result (often already retailer's link)
        2. Filter sellers by expected retailer domain
        3. Use scoring system to pick best candidate
        4. Fallback to site-specific search on expected retailer's domain
        5. If strict_mode=True and no retailer match, return failure (not Walmart/Target)

        Args:
            google_url: Google Shopping search URL
            max_products: Maximum number of PDPs to return (default: 3)
            expected_retailer: Expected retailer name from "source" field (e.g., "Quince")
            expected_domain: Expected retailer domain (e.g., "quince.com")
            strict_mode: If True, fail instead of returning wrong retailer

        Returns:
            List of product dicts with retailer PDP URLs
        """
        from urllib.parse import urlparse, parse_qs, unquote

        # Import retailer identity service for scoring
        try:
            from retailer_identity import retailer_identity_service
        except ImportError:
            retailer_identity_service = None
            print("[SERP] ⚠️ RetailerIdentityService not available, using basic resolution")

        try:
            # Extract query from Google Shopping URL
            parsed = urlparse(google_url)
            params = parse_qs(parsed.query)

            # Get the search query
            query = params.get("q", [""])[0]
            if not query:
                print(f"[SERP] Could not extract query from Google Shopping URL")
                return []

            query = unquote(query)
            print(f"[SERP] Resolving Google Shopping URL with query: '{query}'")
            if expected_retailer:
                print(f"[SERP] 🎯 Expected retailer: '{expected_retailer}'")

            # Resolve expected_domain from expected_retailer if not provided
            if expected_retailer and not expected_domain and retailer_identity_service:
                expected_domain = retailer_identity_service.resolve_brand_to_domain(expected_retailer)
                if expected_domain:
                    print(f"[SERP] 🎯 Resolved expected domain: '{expected_domain}'")

            # Step 1: Search Google Shopping via SerpAPI to get product_ids
            search = GoogleSearch({
                "q": query,
                "tbm": "shop",
                "api_key": self.api_key,
                "num": 20,  # Fetch more to have fallback options
                "hl": "en",
                "gl": "us",
            })

            result = search.get_dict()
            shopping_results = result.get("shopping_results", [])

            print(f"[SERP] Shopping results count: {len(shopping_results)}")

            # Step 2: Extract products with product_ids, prioritizing expected retailer
            products_to_resolve = []
            for item in shopping_results[:max_products * 5]:  # Extra for fallbacks
                product_id = item.get("product_id")
                source = item.get("source", "")
                product_link = item.get("product_link", "")

                if product_id:
                    product_data = {
                        "product_id": product_id,
                        "title": item.get("title", ""),
                        "price": item.get("extracted_price"),
                        "source": source,
                        "thumbnail": item.get("thumbnail", ""),
                        "product_link": product_link,
                        "link": item.get("link", ""),  # Sometimes has direct link
                    }

                    # Prioritize products from expected retailer
                    if expected_retailer and retailer_identity_service:
                        if retailer_identity_service.domain_matches_brand(source, expected_retailer):
                            products_to_resolve.insert(0, product_data)
                            print(f"[SERP] ⭐ Prioritized product from '{source}' (matches expected)")
                        else:
                            products_to_resolve.append(product_data)
                    else:
                        products_to_resolve.append(product_data)

            print(f"[SERP] Found {len(products_to_resolve)} products with product_ids")

            # Step 3: Resolve each product to retailer PDP
            resolved_pdps = []
            seen_domains = set()

            for product in products_to_resolve:
                if len(resolved_pdps) >= max_products:
                    break

                resolved = self._resolve_product_to_retailer_pdp(
                    product=product,
                    expected_retailer=expected_retailer,
                    expected_domain=expected_domain,
                    retailer_identity_service=retailer_identity_service,
                    seen_domains=seen_domains,
                    strict_mode=strict_mode,
                )

                if resolved:
                    resolved_pdps.append(resolved)

            # Step 4: Fallback - site-specific search on expected retailer's domain
            if len(resolved_pdps) < max_products and expected_domain:
                print(f"[SERP] Trying fallback site search on {expected_domain}...")
                fallback_result = self._fallback_site_search(query, expected_domain)
                if fallback_result:
                    resolved_pdps.append(fallback_result)
                    print(f"[SERP] ✅ Fallback found PDP on {expected_domain}")

            # Step 5: If strict_mode=False and still no results, try any retailer
            if not strict_mode and len(resolved_pdps) < max_products:
                print(f"[SERP] Non-strict mode: trying any retailer as fallback...")
                fallback_domains = ["wayfair.com", "amazon.com", "target.com", "walmart.com"]

                for domain in fallback_domains:
                    if len(resolved_pdps) >= max_products:
                        break

                    domain_base = domain.replace(".com", "")
                    if domain_base.lower() in [d.replace(".com", "").lower() for d in seen_domains]:
                        continue

                    fallback_result = self._fallback_site_search(query, domain)
                    if fallback_result:
                        resolved_pdps.append(fallback_result)
                        seen_domains.add(domain)

            print(f"[SERP] Resolved to {len(resolved_pdps)} retailer PDPs")
            return resolved_pdps

        except Exception as e:
            print(f"[SERP] Error resolving Google Shopping URL: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _resolve_product_to_retailer_pdp(
        self,
        product: Dict[str, Any],
        expected_retailer: Optional[str],
        expected_domain: Optional[str],
        retailer_identity_service,
        seen_domains: set,
        strict_mode: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a single product to its retailer PDP using scoring.

        Priority:
        1. product_link / link from shopping result (often direct retailer link)
        2. Seller links filtered by expected retailer
        3. Best scoring candidate from all sellers
        """
        from urllib.parse import urlparse

        product_title = product.get("title", "")
        product_source = product.get("source", "")

        # === LAYER 1: Try direct links from shopping result ===
        direct_links = [
            product.get("product_link"),
            product.get("link"),
        ]

        for link in direct_links:
            if not link or "google.com" in link.lower():
                continue

            # Follow redirects to get final URL
            final_url = self._follow_redirect_chain(link)
            if not final_url:
                continue

            try:
                domain = urlparse(final_url).netloc.lower().replace("www.", "")
            except Exception:
                continue

            if domain in seen_domains:
                continue

            # Score this candidate
            if retailer_identity_service:
                score = retailer_identity_service.score_candidate_url(
                    url=final_url,
                    expected_retailer=expected_retailer,
                    expected_domain=expected_domain,
                    product_title=product_title,
                )

                # If matches expected retailer, use it
                if score >= 100:  # Domain match threshold
                    seen_domains.add(domain)
                    print(f"[SERP] ✅ Direct link matched retailer: {final_url[:70]}... (score={score})")
                    return self._build_pdp_result(
                        url=final_url,
                        product=product,
                        domain=domain,
                        source_api="direct_link",
                    )
            elif self._is_pdp_url(final_url):
                # No identity service, accept valid PDPs
                seen_domains.add(domain)
                return self._build_pdp_result(
                    url=final_url,
                    product=product,
                    domain=domain,
                    source_api="direct_link",
                )

        # === LAYER 2: Try Google Product API sellers ===
        try:
            product_search = GoogleSearch({
                "engine": "google_product",
                "product_id": product["product_id"],
                "api_key": self.api_key,
                "hl": "en",
                "gl": "us",
            })
            product_result = product_search.get_dict()

            sellers_data = product_result.get("sellers_results", {})
            online_sellers = sellers_data.get("online_sellers", [])

            print(f"[SERP] Product '{product_title[:40]}...' has {len(online_sellers)} sellers")

            if not online_sellers:
                return None

            # Build candidate list with scores
            candidates = []
            for seller in online_sellers:
                link = seller.get("link", "")
                if not link or "google.com" in link.lower():
                    continue

                # Follow redirects
                final_url = self._follow_redirect_chain(link) or link

                try:
                    domain = urlparse(final_url).netloc.lower().replace("www.", "")
                except Exception:
                    continue

                if domain in seen_domains:
                    continue

                if not self._is_pdp_url(final_url):
                    continue

                # Score candidate
                score = 0
                if retailer_identity_service:
                    score = retailer_identity_service.score_candidate_url(
                        url=final_url,
                        expected_retailer=expected_retailer,
                        expected_domain=expected_domain,
                        product_title=product_title,
                    )

                candidates.append({
                    "url": final_url,
                    "domain": domain,
                    "seller_name": seller.get("name", ""),
                    "price": seller.get("price", "") or seller.get("total_price", ""),
                    "score": score,
                })

            if not candidates:
                return None

            # Sort by score (highest first)
            candidates.sort(key=lambda x: x["score"], reverse=True)

            # Log candidate scores for debugging
            print(f"[SERP] Candidate scores:")
            for c in candidates[:5]:
                print(f"  - {c['domain']}: score={c['score']}")

            best = candidates[0]

            # In strict mode, only accept if score indicates retailer match
            if strict_mode and expected_retailer:
                if best["score"] < 50:  # Below PDP threshold
                    print(f"[SERP] ⚠️ Strict mode: Best candidate score too low ({best['score']})")
                    return None
                if best["score"] < 100 and retailer_identity_service:
                    # Didn't match expected retailer
                    if retailer_identity_service.is_marketplace(best["domain"]):
                        print(f"[SERP] ⚠️ Strict mode: Best candidate is marketplace, not {expected_retailer}")
                        return None

            seen_domains.add(best["domain"])
            print(f"[SERP] ✅ Selected {best['seller_name'] or best['domain']}: {best['url'][:70]}... (score={best['score']})")

            return self._build_pdp_result(
                url=best["url"],
                product=product,
                domain=best["domain"],
                source_api="google_product_api",
                price_str=best.get("price", ""),
            )

        except Exception as e:
            print(f"[SERP] Product API failed for {product['product_id']}: {e}")
            return None

    def _build_pdp_result(
        self,
        url: str,
        product: Dict[str, Any],
        domain: str,
        source_api: str,
        price_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a standardized PDP result dict."""
        store_name = domain.replace(".com", "").replace("www.", "").title()

        return {
            "url": url,
            "title": product.get("title", ""),
            "store": store_name,
            "price_str": price_str or "",
            "thumbnail": product.get("thumbnail", ""),
            "source_api": source_api,
            "product_id": product.get("product_id", ""),
            "original_source": product.get("source", ""),  # Original retailer from shopping result
        }

    def _follow_redirect_chain(self, url: str, max_redirects: int = 5) -> Optional[str]:
        """Follow redirect chain to get final URL."""
        try:
            import requests

            response = requests.head(
                url,
                allow_redirects=True,
                timeout=5,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FurnitureBot/1.0)"}
            )

            if response.status_code == 200:
                return response.url

            # Try GET if HEAD fails
            response = requests.get(
                url,
                allow_redirects=True,
                timeout=5,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FurnitureBot/1.0)"}
            )

            if response.status_code == 200:
                return response.url

            return None

        except Exception as e:
            print(f"[SERP] Redirect chain failed for {url[:50]}...: {e}")
            return None
