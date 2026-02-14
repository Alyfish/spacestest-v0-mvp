"""
Exa API Client for product discovery and web crawling
Ported from old project with enhancements for interior design recommendations
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from exa_py import Exa

from cache_manager import cache_manager
from retry import retry_sync

load_dotenv()

logger = logging.getLogger("spaces_ai.exa")


class ExaClient:
    """Client for Exa API to find and analyze furniture products online"""

    def __init__(self, api_key: str = None):
        """Initialize Exa client with API key"""
        if Exa is None:
            raise ImportError(
                "exa-py package not installed. Install with: pip install exa-py"
            )

        self.api_key = api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY not found in environment variables")

        self.exa = Exa(self.api_key)

    @retry_sync(max_retries=3, base_delay=1.0, exponential_base=2.0)
    def search_products(
        self,
        query: str,
        num_results: int = 10,
        similar_per_seed: int = 3,
    ) -> Dict[str, Any]:
        """
        Search for furniture products using Exa search + contents, and expand with similar links (with caching).

        Returns:
            Dict with results compatible with downstream parsing.
        """
        # Check cache first
        cached = cache_manager.get_product_search(
            "exa", query, num_results,
            extra_params={"similar_per_seed": similar_per_seed}
        )
        if cached is not None:
            logger.debug(f"Cache HIT for query: '{query[:40]}...'")
            return {"results": cached}

        trusted_domains = [
            # Original quality furniture retailers
            "wayfair.com",
            "westelm.com",
            "cb2.com",
            "crateandbarrel.com",
            "potterybarn.com",
            "article.com",
            "ikea.com",
            "allmodern.com",
            "overstock.com",
            # Art & Wall Decor Specialists
            "drool.com",
            "olivergal.com",
            "art.com",
            "minted.com",
            "society6.com",
            "icanvas.com",
            "saatchiart.com",
            # Premium Curated
            "anthropologie.com",
            "urbanoutfitters.com",
            "designwithinreach.com",
            "roomandboard.com",
            "serenaandlily.com",
            "rejuvenation.com",
            "burkedecor.com",
            "lumens.com",
            # Specialty
            "etsy.com",
            "1stdibs.com",
            "chairish.com",
            "worldmarket.com",
            "zgallerie.com",
            # General with good selection
            "amazon.com",
            "target.com",
            "homedepot.com",
            "walmart.com",
            "houzz.com",
        ]

        try:
            print(f"\n🔍 EXA: search '{query}' (base={num_results}, similar={similar_per_seed})")

            base_result = self.exa.search(
                query=query,
                num_results=num_results,
                type="keyword",
                include_domains=trusted_domains,
            )
            base_results = list(base_result.results or [])
            print(f"🔍 EXA: base results {len(base_results)}")

            # Fetch content for a few top results
            content_map: Dict[str, Any] = {}
            try:
                if base_results:
                    contents = self.exa.get_contents(
                        urls=[r.url for r in base_results[:5]],
                        text={"max_characters": 4000, "include_html_tags": True},
                    )
                    if contents and contents.results:
                        content_map.update({item.url: item for item in contents.results})
                        print(f"🔍 EXA: contents fetched for {len(contents.results)}")
            except Exception as e:
                print(f"⚠️ EXA: get_contents failed: {e}")

            # Expand with find_similar for a couple of seeds (pipeline synergy)
            expanded_results = list(base_results)
            seen_urls = {r.url for r in base_results}
            for seed in base_results[:2]:
                try:
                    similar = self.exa.find_similar(
                        url=seed.url,
                        num_results=similar_per_seed,
                        include_domains=trusted_domains,
                        exclude_source_domain=True,
                    )
                    if similar and similar.results:
                        added = 0
                        for res in similar.results:
                            if res.url in seen_urls:
                                continue
                            seen_urls.add(res.url)
                            expanded_results.append(res)
                            added += 1
                        print(f"🔍 EXA: similar for {seed.url} added {added}")
                except Exception as e:
                    print(f"⚠️ EXA: find_similar failed for {seed.url}: {e}")

            # Fetch content for any new URLs we don't have text for
            missing_urls = [r.url for r in expanded_results if r.url not in content_map][:5]
            if missing_urls:
                try:
                    contents = self.exa.get_contents(
                        urls=missing_urls,
                        text={"max_characters": 3000, "include_html_tags": True},
                    )
                    if contents and contents.results:
                        content_map.update({item.url: item for item in contents.results})
                        print(f"🔍 EXA: extra contents fetched for {len(contents.results)}")
                except Exception as e:
                    print(f"⚠️ EXA: extra get_contents failed: {e}")

            converted_results = {"results": []}
            for item in expanded_results:
                content_item = content_map.get(item.url)
                # Drop if no shopping signals in content (price/add-to-cart/stock) within first 1000 chars
                has_shopping_signals = False
                if content_item:
                    text_sample = (getattr(content_item, "text", "") or "")[:1000].lower()
                    if any(tok in text_sample for tok in ["$", "add to cart", "add-to-cart", "in stock", "buy now"]):
                        has_shopping_signals = True

                converted_results["results"].append(
                    {
                        "url": item.url,
                        "title": item.title,
                        "id": getattr(item, "id", ""),
                        "published_date": getattr(item, "published_date", None),
                        "author": getattr(item, "author", None),
                        "extract": getattr(content_item, "extract", "")
                        if content_item
                        else getattr(item, "text", "") if hasattr(item, "text") else "",
                        "text": getattr(content_item, "text", "")
                        if content_item
                        else getattr(item, "text", "") if hasattr(item, "text") else "",
                        "highlights": getattr(content_item, "highlights", [])
                        if content_item
                        else getattr(item, "highlights", []),
                        "score": getattr(item, "score", None),
                        "shopping_signals": has_shopping_signals,
                        "image": (getattr(content_item, "image", "") if content_item else "") or getattr(item, "image", "") or "",
                    }
                )

            print(f"🔍 EXA: converted {len(converted_results['results'])} results")

            # Cache successful results
            if converted_results.get("results"):
                cache_manager.set_product_search(
                    "exa", query, num_results,
                    converted_results["results"],
                    extra_params={"similar_per_seed": similar_per_seed}
                )

            return converted_results

        except Exception as e:
            print(f"Error searching products: {e}")
            return {"error": str(e), "results": []}

    def get_product_details(
        self, search_results: List[Dict[str, Any]], max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get detailed product information from search results

        Args:
            search_results: List of search results from Exa
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

        return products

    def search_and_analyze_products(
        self, query: str, space_type: str, num_results: int = 15, similar_per_seed: int = 3
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
        search_results = self.search_products(query, num_results=num_results, similar_per_seed=similar_per_seed)

        if "error" in search_results:
            return []

        # Get product details from search results
        products = self.get_product_details(search_results.get("results", []))

        # Enhance with space type context
        for product in products:
            product["space_type"] = space_type
            product["search_query"] = query

        return products

    def _extract_product_info(
        self, content_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract structured product information from content"""
        try:
            url = content_result.get("url", "")
            title = content_result.get("title", "")
            text = content_result.get("text", "")
            shopping_signals = content_result.get("shopping_signals", False)

            if not text or not shopping_signals:
                return None

            # Extract store name
            store_name = self._extract_store_name(url, title)

            # Extract price
            price_info = self._extract_price(text)

            # Extract availability
            availability = self._extract_availability(text)

            # Extract shipping info
            shipping = self._extract_shipping_info(text)

            # Extract product details
            details = self._extract_product_details(text)

            # Extract product images
            images = self._extract_product_images(text, url, store_name)

            # Fallback: use EXA's native page image (og:image) if HTML extraction fails
            if not images:
                exa_image = content_result.get("image", "")
                if exa_image and len(exa_image) > 10:
                    images = [exa_image]

            # Format to match frontend expectations (same as SERP client)
            product = {
                # Core fields
                "title": title,
                "url": url,
                "store": store_name,  # Frontend expects "store", not "store_name"
                "price": self._parse_price_to_float(price_info["price"]),
                "price_str": price_info["price"],
                "availability": availability,
                "images": images,
                "description": content_result.get("extract", "")[:300],
                "rating": details["rating"],
                "reviews": details["reviews_count"],
                "delivery": shipping,
                # Additional fields
                "materials": details["materials"],
                "colors": details["colors"],
                "dimensions": details["dimensions"],
                # Compatibility fields
                "space_type": "",  # Will be set later
                "search_query": "",  # Will be set later
                "is_product_page": self._is_likely_product_page(url, text),
            }

            return product

        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None

    def _extract_store_name(self, url: str, title: str) -> str:
        """Extract store name from URL and title"""
        known_stores = {
            "amazon.com": "Amazon",
            "wayfair.com": "Wayfair",
            "ikea.com": "IKEA",
            "westelm.com": "West Elm",
            "cb2.com": "CB2",
            "crateandbarrel.com": "Crate & Barrel",
            "potterybarn.com": "Pottery Barn",
            "article.com": "Article",
            "allmodern.com": "AllModern",
            "homedepot.com": "Home Depot",
            "target.com": "Target",
            "walmart.com": "Walmart",
            "overstock.com": "Overstock",
            "ashleyfurniture.com": "Ashley Furniture",
        }

        url_lower = url.lower()
        for domain, store_name in known_stores.items():
            if domain in url_lower:
                return store_name

        # Extract from URL hostname
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if hostname.startswith("www."):
                hostname = hostname[4:]
            parts = hostname.split(".")
            if len(parts) >= 2:
                return parts[0].title()
        except Exception:
            pass

        return "Unknown Store"

    def _extract_price(self, text: str) -> Dict[str, str]:
        """Extract pricing information"""
        price_patterns = [
            r"\$[\d,]+\.?\d*",
            r"USD\s*[\d,]+\.?\d*",
            r"Price:\s*\$[\d,]+\.?\d*",
            r"Sale Price:\s*\$[\d,]+\.?\d*",
        ]

        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prices.extend(matches)

        # Look for sale/discount indicators
        original_price = None
        current_price = prices[0] if prices else "Price not available"
        discount = None

        if "was" in text.lower() and "now" in text.lower():
            was_match = re.search(r"was\s*(\$[\d,]+\.?\d*)", text, re.IGNORECASE)
            now_match = re.search(r"now\s*(\$[\d,]+\.?\d*)", text, re.IGNORECASE)
            if was_match and now_match:
                original_price = was_match.group(1)
                current_price = now_match.group(1)

        # Look for discount percentage
        discount_match = re.search(r"(\d+)%\s*off", text, re.IGNORECASE)
        if discount_match:
            discount = f"{discount_match.group(1)}% off"

        return {
            "price": current_price,
            "original_price": original_price,
            "discount": discount,
        }

    def _extract_availability(self, text: str) -> str:
        """Extract availability information"""
        text_lower = text.lower()

        if "in stock" in text_lower:
            return "In Stock"
        elif "out of stock" in text_lower:
            return "Out of Stock"
        elif "limited availability" in text_lower:
            return "Limited Availability"
        elif re.search(r"ships? in \d+ days?", text_lower):
            match = re.search(r"ships? in (\d+) days?", text_lower)
            return f"Ships in {match.group(1)} days" if match else "Check availability"
        elif "ready to ship" in text_lower:
            return "Ready to Ship"
        else:
            return "Check availability"

    def _extract_shipping_info(self, text: str) -> str:
        """Extract shipping information"""
        text_lower = text.lower()
        shipping_info = []

        if "free shipping" in text_lower:
            shipping_info.append("Free shipping")
        if "free delivery" in text_lower:
            shipping_info.append("Free delivery")

        # Look for shipping time
        shipping_match = re.search(r"delivery in (\d+[-\s]?\d*)\s*days?", text_lower)
        if shipping_match:
            days = shipping_match.group(1)
            shipping_info.append(f"Delivery in {days} days")

        return " | ".join(shipping_info) if shipping_info else "Standard shipping"

    def _extract_product_details(self, text: str) -> Dict[str, Any]:
        """Extract detailed product information"""
        text_lower = text.lower()

        # Materials
        materials = [
            "wood",
            "metal",
            "fabric",
            "leather",
            "glass",
            "plastic",
            "velvet",
            "cotton",
            "steel",
            "iron",
            "oak",
            "pine",
        ]
        found_materials = [mat for mat in materials if mat in text_lower]

        # Colors
        colors = [
            "red",
            "blue",
            "green",
            "yellow",
            "black",
            "white",
            "gray",
            "brown",
            "beige",
            "navy",
            "teal",
            "charcoal",
            "cream",
        ]
        found_colors = [col for col in colors if col in text_lower]

        # Dimensions
        dimensions = []
        dimension_patterns = [
            r'\d+["\']?\s*[xX×]\s*\d+["\']?\s*[xX×]\s*\d+["\']?',
            r'\d+\.\d+["\']?\s*[xX×]\s*\d+\.\d+["\']?\s*[xX×]\s*\d+\.\d+["\']?',
            r'\d+["\']?\s*[wW]\s*[xX×]\s*\d+["\']?\s*[dD]\s*[xX×]\s*\d+["\']?\s*[hH]',
        ]
        for pattern in dimension_patterns:
            matches = re.findall(pattern, text)
            dimensions.extend(matches)

        # Features (look for bullet points or key features)
        features = []
        if "features:" in text_lower:
            features_section = text.lower().split("features:")[1].split("\n")[:5]
            features = [f.strip("- •").strip() for f in features_section if f.strip()]

        # Rating
        rating = None
        rating_match = re.search(
            r"(\d+\.?\d*)\s*out of 5|(\d+\.?\d*)/5\s*stars?", text_lower
        )
        if rating_match:
            rating = rating_match.group(1) or rating_match.group(2)

        # Reviews count
        reviews_count = None
        reviews_match = re.search(r"(\d+[,\d]*)\s*reviews?", text_lower)
        if reviews_match:
            reviews_count = reviews_match.group(1)

        return {
            "materials": found_materials[:3],  # Top 3 materials
            "colors": found_colors[:3],  # Top 3 colors
            "dimensions": dimensions[:2],  # Top 2 dimension sets
            "features": features[:5],  # Top 5 features
            "rating": rating,
            "reviews_count": reviews_count,
        }

    def _extract_product_images(
        self, text: str, url: str, store_name: str
    ) -> List[str]:
        """Extract product image URLs from HTML content"""
        images = []

        print(f"🔍 DEBUG: Extracting images from {store_name} page")
        print(f"  - Page URL: {url}")
        print(f"  - Content length: {len(text)} chars")

        # Common image URL patterns in HTML - MORE COMPREHENSIVE
        img_patterns = [
            # Standard img tags
            r'<img[^>]*src=["\'](https?://[^"\']*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\']*)?)["\'][^>]*>',
            # Lazy loading attributes
            r'data-src=["\'](https?://[^"\']*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\']*)?)["\']',
            r'data-lazy-src=["\'](https?://[^"\']*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\']*)?)["\']',
            r'data-original=["\'](https?://[^"\']*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\']*)?)["\']',
            # Srcset (responsive images)
            r'srcset=["\'](https?://[^"\']*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"\']*)?)["\']',
            # JSON-LD structured data (often contains high-quality images)
            r'"image":\s*"(https?://[^"]*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"]*)?)"',
            r'"url":\s*"(https?://[^"]*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"]*)?)"',
            # CSS background images
            r'background-image:\s*url\(["\']?(https?://[^)\'\"]*\.(?:jpg|jpeg|png|webp|gif)(?:\?[^)\'\"]*)?)["\']?\)',
            # Amazon specific patterns (try to get CDN URLs)
            r'(https://[^"\']*\.ssl-images-amazon\.com/images/[^"\']*\.(?:jpg|jpeg|png|webp))',
            r'(https://m\.media-amazon\.com/images/[^"\']*\.(?:jpg|jpeg|png|webp))',
        ]

        # Extract all potential image URLs
        for pattern in img_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            print(f"  - Pattern found {len(matches)} matches: {pattern[:50]}...")
            images.extend(matches)

        # Filter and clean images
        filtered_images = []
        for img_url in images:
            # Skip thumbnails, icons, and non-product images
            if any(
                skip_word in img_url.lower()
                for skip_word in [
                    "logo",
                    "icon",
                    "banner",
                    "header",
                    "footer",
                    "nav",
                    "thumb",
                    "avatar",
                    "profile",
                    "badge",
                    "arrow",
                    "button",
                    "spacer",
                    "1x1",
                    "pixel",
                    "tracking",
                ]
            ):
                continue

            # Look for product-like images
            if any(
                product_word in img_url.lower()
                for product_word in [
                    "product",
                    "item",
                    "furniture",
                    "chair",
                    "sofa",
                    "table",
                    "bed",
                    "desk",
                    "cabinet",
                    "shelf",
                    "lamp",
                ]
            ):
                filtered_images.append(img_url)
            # Include images from product image directories
            elif any(
                dir_word in img_url.lower()
                for dir_word in [
                    "/products/",
                    "/items/",
                    "/catalog/",
                    "/images/p/",
                    "/img/p/",
                ]
            ):
                filtered_images.append(img_url)
            # Include larger images (likely product photos)
            elif any(
                size in img_url.lower()
                for size in [
                    "400",
                    "500",
                    "600",
                    "800",
                    "1000",
                    "large",
                    "medium",
                    "main",
                ]
            ):
                filtered_images.append(img_url)

        # Store-specific image patterns
        if "wayfair" in store_name.lower():
            # Wayfair typically has product images in specific formats
            wayfair_patterns = [
                r'https://secure\.img\d*-.*?\.wfcdn\.com/[^"\s]*\.jpg',
                r'https://assets\.wfcdn\.com/[^"\s]*\.jpg',
            ]
            for pattern in wayfair_patterns:
                matches = re.findall(pattern, text)
                filtered_images.extend(matches)

        elif "ikea" in store_name.lower():
            # IKEA image patterns
            ikea_patterns = [
                r'https://www\.ikea\.com/[^"\s]*\.jpg',
                r'https://d2xjmi1k71iy2m\.cloudfront\.net/[^"\s]*\.jpg',
            ]
            for pattern in ikea_patterns:
                matches = re.findall(pattern, text)
                filtered_images.extend(matches)

        elif "amazon" in store_name.lower():
            # Amazon image patterns
            amazon_patterns = [
                r'https://m\.media-amazon\.com/images/[^"\s]*\.jpg',
                r'https://images-na\.ssl-images-amazon\.com/[^"\s]*\.jpg',
            ]
            for pattern in amazon_patterns:
                matches = re.findall(pattern, text)
                filtered_images.extend(matches)

        # Remove duplicates and return top 3 images
        unique_images = list(dict.fromkeys(filtered_images))
        final_images = unique_images[:3]

        print("🔍 DEBUG: Image extraction summary:")
        print(f"  - Total URLs found: {len(images)}")
        print(f"  - After filtering: {len(filtered_images)}")
        print(f"  - Unique images: {len(unique_images)}")
        print(f"  - Final images: {len(final_images)}")

        for i, img_url in enumerate(final_images):
            print(f"  - Image {i + 1}: {img_url}")

        return final_images

    def _parse_price_to_float(self, price_str: str) -> Optional[float]:
        """Parse price string to float for frontend compatibility"""
        if not price_str or price_str == "Price not available":
            return None

        try:
            # Remove currency symbols and extract numeric value
            import re

            numeric_match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
            if numeric_match:
                return float(numeric_match.group())
        except Exception:
            pass

        return None

    def _is_likely_product_page(self, url: str, text: str) -> bool:
        """Determine if this is likely a product page vs search results"""
        # Check for product page URL patterns
        product_patterns = ["/p/", "/product/", "/item/", "/pd/", "/dp/", "sku="]
        url_lower = url.lower()

        if any(pattern in url_lower for pattern in product_patterns):
            return True

        # Check for single product indicators in text
        text_lower = text.lower()
        if "add to cart" in text_lower or "buy now" in text_lower:
            return True

        # Check for multiple prices (indicates search results)
        price_count = len(re.findall(r"\$\d+", text))
        if price_count > 5:
            return False

        return True

    # =========================================================================
    # Google Shopping URL Resolution
    # =========================================================================

    def is_google_shopping_url(self, url: str) -> bool:
        """Check if URL is a Google Shopping redirect URL."""
        patterns = [
            "google.com/shopping",
            "google.com/url?",
            "shopping.google.com",
            "google.com/aclk",
            "ibp=oshop",  # Google Shopping search results
            "google.com/search?ibp=oshop",  # Explicit shopping search pattern
        ]
        url_lower = url.lower()
        return any(p in url_lower for p in patterns)

    def resolve_google_shopping_url(self, google_shopping_url: str) -> Optional[str]:
        """
        Resolve a Google Shopping URL to the actual retailer URL.
        Uses Exa's get_contents to fetch the page and extract the retailer link.
        """
        try:
            print(f"🔍 EXA: Resolving Google Shopping URL: {google_shopping_url[:60]}...")

            contents = self.exa.get_contents(
                urls=[google_shopping_url],
                text={"max_characters": 8000, "include_html_tags": True}
            )

            if not contents or not contents.results:
                print(f"⚠️ EXA: No content returned for Google Shopping URL")
                return None

            html_content = getattr(contents.results[0], "text", "") or ""
            resolved = self._extract_retailer_from_google_shopping(html_content, google_shopping_url)

            if resolved:
                print(f"✅ EXA: Resolved to retailer URL: {resolved[:60]}...")
            else:
                print(f"⚠️ EXA: Could not extract retailer URL from content")

            return resolved

        except Exception as e:
            print(f"❌ EXA: Failed to resolve Google Shopping URL: {e}")
            return None

    def _extract_retailer_from_google_shopping(
        self, html_content: str, original_url: str
    ) -> Optional[str]:
        """Extract the actual retailer URL from Google Shopping page HTML."""
        from urllib.parse import unquote, urlparse, parse_qs

        # First, try to extract from the original URL if it contains redirect params
        try:
            parsed = urlparse(original_url)
            query_params = parse_qs(parsed.query)

            # Check common redirect parameters
            for param in ["url", "q", "adurl", "dest"]:
                if param in query_params:
                    candidate = unquote(query_params[param][0])
                    if candidate.startswith("http") and "google.com" not in candidate.lower():
                        return candidate
        except Exception:
            pass

        # Patterns to extract retailer URLs from HTML content
        patterns = [
            # Visit site/store links
            r'href="(https?://(?!.*google\.com)[^"]+)"[^>]*>[^<]*(?:Visit|Shop|Buy|View)[^<]*(?:site|store|now|product)',
            # Data attributes with merchant URLs
            r'data-merchant-url="([^"]+)"',
            r'data-url="(https?://(?!.*google\.com)[^"]+)"',
            r'data-href="(https?://(?!.*google\.com)[^"]+)"',
            # JSON-LD structured data
            r'"url"\s*:\s*"(https?://(?!.*google\.com)[^"]+)"',
            r'"offers"[^}]*"url"\s*:\s*"(https?://[^"]+)"',
            # Direct product links
            r'href="(https?://(?:www\.)?(?:amazon|wayfair|ikea|target|walmart|homedepot|lowes|westelm|cb2|potterybarn|crateandbarrel|overstock|allmodern|article)\.[^"]+)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                candidate = unquote(matches[0])
                # Validate it's a real retailer URL
                if self._is_valid_retailer_url(candidate):
                    return candidate

        return None

    def _is_valid_retailer_url(self, url: str) -> bool:
        """Check if a URL is a valid retailer product URL.

        Uses config.NON_RETAILER_BLOCKLIST to reject non-retailer domains
        and checks for common non-product URL patterns.
        """
        if not url or not url.startswith("http"):
            return False

        url_lower = url.lower()

        # Check blocklist for non-retailer domains (Instagram, Pinterest, blogs, etc.)
        try:
            from config import is_blocked_domain
            if is_blocked_domain(url):
                return False
        except ImportError:
            pass

        # Exclude Google URLs
        if "google.com" in url_lower:
            return False

        # Exclude common non-product URLs
        exclude_patterns = [
            "/search", "/results", "/browse", "/category",
            "javascript:", "mailto:", "#",
            # Blog/article patterns
            "/blog/", "/article/", "/news/", "/stories/",
            "/how-to/", "/guide/", "/tips/", "/ideas/",
            "/inspiration/", "/tutorial/", "/diy/",
            # Social patterns
            "/post/", "/status/", "/reel/",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def validate_product_urls_batch(
        self,
        urls: List[str],
        batch_size: int = 5,
        max_chars: int = 2000
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch validate URLs to ensure they are actual product pages.

        Uses Exa get_contents() to fetch page content and checks for:
        - Product page URL patterns (/product/, /p/, /dp/, etc.)
        - Valid retailer URL (not Google redirect, not search/category)
        - Shopping signals ($, add to cart, buy now, in stock)

        Args:
            urls: List of URLs to validate
            batch_size: Number of URLs per Exa API call
            max_chars: Maximum characters to fetch per URL

        Returns:
            Dict mapping URL -> {
                "is_valid": bool,
                "is_product_page": bool,
                "has_shopping_signals": bool,
                "error": str or None
            }
        """
        results = {}

        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]

            try:
                contents = self.exa.get_contents(
                    urls=batch,
                    text={"max_characters": max_chars, "include_html_tags": True}
                )

                fetched_urls = set()
                for content in (contents.results if contents else []):
                    text = getattr(content, "text", "") or ""
                    text_lower = text[:1500].lower()

                    is_product = self._is_likely_product_page(content.url, text)
                    is_valid_retailer = self._is_valid_retailer_url(content.url)
                    has_shopping = any(
                        tok in text_lower
                        for tok in ["$", "add to cart", "add-to-cart", "in stock", "buy now", "add to bag"]
                    )

                    results[content.url] = {
                        "is_valid": is_product and is_valid_retailer and has_shopping,
                        "is_product_page": is_product,
                        "is_valid_retailer": is_valid_retailer,
                        "has_shopping_signals": has_shopping,
                        "error": None
                    }
                    fetched_urls.add(content.url)

                # Mark URLs that weren't fetched as errors
                for url in batch:
                    if url not in fetched_urls and url not in results:
                        results[url] = {
                            "is_valid": False,
                            "is_product_page": False,
                            "is_valid_retailer": False,
                            "has_shopping_signals": False,
                            "error": "fetch_failed"
                        }

            except Exception as e:
                # Mark all URLs in failed batch as errors
                for url in batch:
                    if url not in results:
                        results[url] = {
                            "is_valid": False,
                            "is_product_page": False,
                            "is_valid_retailer": False,
                            "has_shopping_signals": False,
                            "error": str(e)
                        }

        valid_count = sum(1 for r in results.values() if r.get("is_valid"))
        print(f"🔍 EXA Validation: {valid_count}/{len(urls)} URLs are valid product pages")

        return results

    def resolve_urls_batch(
        self,
        urls: List[str],
        resolve_google_shopping: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch resolve URLs - identifies and resolves Google Shopping URLs.

        Args:
            urls: List of product URLs to process
            resolve_google_shopping: Whether to resolve Google Shopping URLs

        Returns:
            Dict mapping original URL -> {
                "resolved_url": str or None,
                "is_google_shopping": bool,
                "resolution_success": bool
            }
        """
        results = {}
        google_shopping_urls = []

        for url in urls:
            if self.is_google_shopping_url(url):
                google_shopping_urls.append(url)
                results[url] = {
                    "is_google_shopping": True,
                    "resolved_url": None,
                    "resolution_success": False
                }
            else:
                results[url] = {
                    "is_google_shopping": False,
                    "resolved_url": url,
                    "resolution_success": True
                }

        # Resolve Google Shopping URLs
        if resolve_google_shopping and google_shopping_urls:
            print(f"🔍 EXA: Resolving {len(google_shopping_urls)} Google Shopping URL(s)...")

            for gs_url in google_shopping_urls:
                resolved = self.resolve_google_shopping_url(gs_url)
                if resolved:
                    results[gs_url]["resolved_url"] = resolved
                    results[gs_url]["resolution_success"] = True
                else:
                    # Fall back to original URL if resolution fails
                    results[gs_url]["resolved_url"] = gs_url

        resolved_count = sum(1 for r in results.values() if r.get("resolution_success"))
        print(f"🔍 EXA: Resolved {resolved_count}/{len(urls)} URLs successfully")

        return results
