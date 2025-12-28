"""
Exa API Client for product discovery and web crawling
Ported from old project with enhancements for interior design recommendations
"""

import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()


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

    def search_products(
        self,
        query: str,
        num_results: int = 10,
        similar_per_seed: int = 3,
    ) -> Dict[str, Any]:
        """
        Search for furniture products using Exa search + contents, and expand with similar links.

        Returns:
            Dict with results compatible with downstream parsing.
        """
        trusted_domains = [
            "wayfair.com",
            "westelm.com",
            "cb2.com",
            "crateandbarrel.com",
            "potterybarn.com",
            "article.com",
            "ikea.com",
            "amazon.com",
            "target.com",
            "homedepot.com",
            "walmart.com",
            "overstock.com",
            "allmodern.com",
            "ashleyfurniture.com",
            "roomstogo.com",
            "livingspaces.com",
            "pier1.com",
            "homegoods.com",
        ]

        try:
            print(f"\n🔍 EXA: search '{query}' (base={num_results}, similar={similar_per_seed})")

            base_result = self.exa.search(
                query=query,
                num_results=num_results,
                use_autoprompt=True,
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
                    }
                )

            print(f"🔍 EXA: converted {len(converted_results['results'])} results")
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
