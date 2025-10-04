"""
SerpAPI Client for product discovery and shopping search
Optimized for furniture and home decor product search with direct product links and images
"""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()


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

    def search_products(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """
        Search for furniture products using Google Shopping

        Args:
            query: Search query (e.g., "modern gray sectional sofa")
            num_results: Number of results to return

        Returns:
            Search results from SerpAPI Google Shopping
        """
        try:
            print(f"🔍 Searching Google Shopping for: '{query}'")

            # Use Google Shopping search - simple and direct
            search = GoogleSearch(
                {
                    "q": query,
                    "tbm": "shop",
                    "api_key": self.api_key,
                    "num": min(num_results, 10),
                    "hl": "en",
                    "gl": "us",
                }
            )

            result = search.get_dict()

            print(f"🔍 SERP API Response Keys: {list(result.keys())}")

            # Check for API errors first
            if "error" in result:
                print(f"❌ SERP API Error: {result['error']}")
                return {"error": result["error"], "results": []}

            # Get shopping results
            shopping_results = result.get("shopping_results", [])
            print(f"🔍 Found {len(shopping_results)} shopping results")

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

            return {
                "results": [
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
            }

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

    def _extract_retailer_url(self, shopping_result: Dict[str, Any]) -> str:
        """Extract the direct retailer URL instead of Google Shopping intermediate page"""

        # Check for direct retailer link in extensions (preferred)
        extensions = shopping_result.get("extensions", [])
        for ext in extensions:
            if isinstance(ext, str) and ("Shop at" in ext or "Buy from" in ext):
                # Sometimes extensions contain direct retailer links
                continue

        # Try the 'link' field first (direct retailer link)
        direct_link = shopping_result.get("link")
        if direct_link and not direct_link.startswith(
            "https://www.google.com/shopping"
        ):
            return direct_link

        # Fall back to product_link (Google Shopping page)
        product_link = shopping_result.get("product_link", "")

        # If we only have Google Shopping link, try to construct direct retailer URL
        # This is a fallback - the user will still get working links to Google Shopping
        source = shopping_result.get("source", "").lower()
        if product_link and source:
            print(
                f"⚠️ Using Google Shopping link for {source} - may redirect to retailer"
            )

        return product_link

    def _extract_product_info(
        self, search_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract structured product information from SerpAPI search result"""
        try:
            url = search_result.get("url", "")
            title = search_result.get("title", "")

            if not url or not title:
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
