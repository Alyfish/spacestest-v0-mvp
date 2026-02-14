"""
Product page classifier with confidence scoring.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from .models import ProductPageClassification, ProductPageSignal

logger = logging.getLogger(__name__)


class ProductPageClassifier:
    """
    Classify whether a page is a product page with confidence scoring.

    Scoring Strategy:
    - JSON-LD Product is the anchor signal (+0.55)
    - Supporting signals add incremental confidence
    - Negative signals subtract (can go below 0)
    - Threshold of 0.50 for is_product_page=True
    """

    # ==========================================================================
    # Signal Weights
    # ==========================================================================

    # Positive signals (sum to ~1.0)
    POSITIVE_WEIGHTS = {
        "json_ld_product": 0.55,       # Anchor signal
        "og_type_product": 0.10,       # Supporting
        "add_to_cart_text": 0.10,      # Supporting
        "price_pattern": 0.10,         # Supporting
        "product_url_pattern": 0.08,   # Supporting
        "canonical_exists": 0.07,      # Supporting
    }

    # Negative signals (can push below threshold)
    NEGATIVE_WEIGHTS = {
        "search_category_indicators": -0.50,  # ?q=, /search, /collections
        "many_product_cards": -0.25,          # >5 H2/H3 = grid page
        "filter_sort_ui": -0.25,              # "Sort by", "Filter", "Results for"
    }

    CONFIDENCE_THRESHOLD = 0.50

    # ==========================================================================
    # Bot Block Detection Patterns
    # ==========================================================================

    BOT_BLOCK_STATUS_CODES = {403, 429, 503}

    BOT_BLOCK_HEADER_PATTERNS = [
        # Akamai
        ("server", "akamaiGhost"),
        ("x-akamai-", None),  # Any x-akamai header
        # PerimeterX
        ("x-px-", None),
        ("x-datadome", None),
        # Cloudflare
        ("cf-ray", None),
        ("cf-mitigated", None),
        # Incapsula
        ("x-iinfo", None),
        ("x-cdn", "incapsula"),
    ]

    BOT_BLOCK_HTML_PATTERNS = [
        # Generic access denied
        r"access\s+denied",
        r"403\s+forbidden",
        r"permission\s+denied",
        # Robot checks
        r"robot\s+check",
        r"captcha",
        r"recaptcha",
        r"hcaptcha",
        r"verify\s+you\s+are\s+(a\s+)?human",
        r"prove\s+you('re|\s+are)\s+(a\s+)?human",
        r"i('m|\s+am)\s+not\s+a\s+robot",
        # Traffic blocks
        r"unusual\s+traffic",
        r"automated\s+access",
        r"too\s+many\s+requests",
        r"rate\s+limit",
        # Challenge pages
        r"attention\s+required",
        r"just\s+a\s+moment",
        r"checking\s+your\s+browser",
        r"please\s+wait",
        r"one\s+more\s+step",
        r"security\s+check",
        # Specific services
        r"pardon\s+our\s+interruption",  # Akamai
        r"blocked\s+by\s+",
    ]

    # ==========================================================================
    # Product Page Detection Patterns
    # ==========================================================================

    ADD_TO_CART_PATTERNS = [
        r"add\s*to\s*cart",
        r"add\s*to\s*bag",
        r"add\s*to\s*basket",
        r"buy\s*now",
        r"purchase\s*now",
        r"add\s*to\s*wishlist",
        r"shop\s*now",
        r"buy\s*it\s*now",  # eBay
    ]

    PRICE_PATTERN = re.compile(
        r"""
        (?:
            \$\s*[\d,]+\.?\d{0,2}  |  # USD: $99.99
            £\s*[\d,]+\.?\d{0,2}  |  # GBP: £99.99
            €\s*[\d,]+\.?\d{0,2}  |  # EUR: €99.99
            [\d,]+\.?\d{0,2}\s*(?:USD|EUR|GBP)  |  # 99.99 USD
            ¥\s*[\d,]+  # JPY: ¥9999
        )
        """,
        re.VERBOSE | re.IGNORECASE
    )

    PRODUCT_URL_PATTERNS = [
        r"/p/",           # Common product path
        r"/product/",     # Explicit product
        r"/item/",        # Item path
        r"/dp/",          # Amazon
        r"/pd/",          # Some retailers
        r"/ip/",          # Walmart
        r"[?&]sku=",      # SKU parameter
        r"[?&]pid=",      # Product ID parameter
        r"[?&]item=",     # Item parameter
        r"-[A-Z0-9]{8,}", # ASIN-like patterns
    ]

    SEARCH_CATEGORY_PATTERNS = [
        r"[?&]q=",           # Search query
        r"[?&]query=",       # Search query
        r"[?&]search=",      # Search
        r"[?&]keyword",      # Keywords
        r"/search[/?]",      # Search path
        r"/s[/?]",           # Amazon search
        r"/collections/",    # Shopify collections
        r"/category/",       # Category pages
        r"/categories/",     # Categories
        r"/browse/",         # Browse pages
        r"/shop/",           # Shop listings (can be either)
        r"/c/",              # Category shorthand
    ]

    FILTER_SORT_PATTERNS = [
        r"sort\s*by",
        r"filter\s*by",
        r"refine\s*by",
        r"results\s*for",
        r"showing\s*\d+",
        r"\d+\s*results",
        r"\d+\s*items",
        r"items\s*found",
        r"products\s*found",
    ]

    def __init__(self, parser: str = "lxml"):
        """
        Initialize the classifier.

        Args:
            parser: BeautifulSoup parser to use
        """
        self.parser = parser

    def classify(
        self,
        html: str,
        url: str,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
    ) -> ProductPageClassification:
        """
        Classify page and return confidence score.

        Args:
            html: HTML content
            url: Page URL
            status_code: HTTP status code
            headers: Response headers

        Returns:
            ProductPageClassification with signals and confidence
        """
        headers = headers or {}

        # First check for bot block
        block_reason = self.detect_bot_block(html, status_code, headers)
        if block_reason:
            return ProductPageClassification(
                is_product_page=False,
                confidence=0.0,
                signals=[],
                negative_signals=[
                    ProductPageSignal(
                        name="bot_blocked",
                        weight=0,
                        present=True,
                        value=block_reason,
                    )
                ],
            )

        # Parse HTML
        soup = BeautifulSoup(html, self.parser)
        html_lower = html.lower()

        positive_signals: List[ProductPageSignal] = []
        negative_signals: List[ProductPageSignal] = []
        confidence = 0.0
        detected_product_type = None

        # =======================================================================
        # Positive Signals
        # =======================================================================

        # Signal 1: JSON-LD Product schema (ANCHOR)
        has_json_ld, product_type = self._check_json_ld_product(soup)
        positive_signals.append(ProductPageSignal(
            name="json_ld_product",
            weight=self.POSITIVE_WEIGHTS["json_ld_product"],
            present=has_json_ld,
            value=product_type,
        ))
        if has_json_ld:
            confidence += self.POSITIVE_WEIGHTS["json_ld_product"]
            detected_product_type = product_type

        # Signal 2: og:type contains product
        has_og_product = self._check_og_type_product(soup)
        positive_signals.append(ProductPageSignal(
            name="og_type_product",
            weight=self.POSITIVE_WEIGHTS["og_type_product"],
            present=has_og_product,
        ))
        if has_og_product:
            confidence += self.POSITIVE_WEIGHTS["og_type_product"]

        # Signal 3: Add to cart / Buy now text
        add_to_cart_match = self._check_add_to_cart(html_lower)
        positive_signals.append(ProductPageSignal(
            name="add_to_cart_text",
            weight=self.POSITIVE_WEIGHTS["add_to_cart_text"],
            present=add_to_cart_match is not None,
            value=add_to_cart_match,
        ))
        if add_to_cart_match:
            confidence += self.POSITIVE_WEIGHTS["add_to_cart_text"]

        # Signal 4: Price pattern (1-5 prices = single product)
        price_count = len(self.PRICE_PATTERN.findall(html))
        has_reasonable_prices = 1 <= price_count <= 5
        positive_signals.append(ProductPageSignal(
            name="price_pattern",
            weight=self.POSITIVE_WEIGHTS["price_pattern"],
            present=has_reasonable_prices,
            value=f"{price_count} prices found",
        ))
        if has_reasonable_prices:
            confidence += self.POSITIVE_WEIGHTS["price_pattern"]

        # Signal 5: Product URL pattern
        has_product_url = self._check_product_url_pattern(url)
        positive_signals.append(ProductPageSignal(
            name="product_url_pattern",
            weight=self.POSITIVE_WEIGHTS["product_url_pattern"],
            present=has_product_url,
        ))
        if has_product_url:
            confidence += self.POSITIVE_WEIGHTS["product_url_pattern"]

        # Signal 6: Canonical tag exists
        has_canonical = self._check_canonical_exists(soup)
        positive_signals.append(ProductPageSignal(
            name="canonical_exists",
            weight=self.POSITIVE_WEIGHTS["canonical_exists"],
            present=has_canonical,
        ))
        if has_canonical:
            confidence += self.POSITIVE_WEIGHTS["canonical_exists"]

        # =======================================================================
        # Negative Signals (only apply if no JSON-LD Product)
        # =======================================================================

        # Negative Signal 1: Search/category indicators in URL
        # Only apply if no JSON-LD Product (some search results have Product schema)
        has_search_indicators = self._check_search_category_url(url)
        apply_search_penalty = has_search_indicators and not has_json_ld
        negative_signals.append(ProductPageSignal(
            name="search_category_indicators",
            weight=self.NEGATIVE_WEIGHTS["search_category_indicators"],
            present=apply_search_penalty,
            value="URL contains search/category patterns" if has_search_indicators else None,
        ))
        if apply_search_penalty:
            confidence += self.NEGATIVE_WEIGHTS["search_category_indicators"]

        # Negative Signal 2: Many product cards (grid layout)
        h2_count = len(soup.find_all("h2"))
        h3_count = len(soup.find_all("h3"))
        heading_count = h2_count + h3_count
        has_many_headings = heading_count > 5
        apply_grid_penalty = has_many_headings and not has_json_ld
        negative_signals.append(ProductPageSignal(
            name="many_product_cards",
            weight=self.NEGATIVE_WEIGHTS["many_product_cards"],
            present=apply_grid_penalty,
            value=f"{heading_count} H2/H3 headings" if has_many_headings else None,
        ))
        if apply_grid_penalty:
            confidence += self.NEGATIVE_WEIGHTS["many_product_cards"]

        # Negative Signal 3: Filter/sort UI text
        has_filter_sort = self._check_filter_sort_ui(html_lower)
        apply_filter_penalty = has_filter_sort and not has_json_ld
        negative_signals.append(ProductPageSignal(
            name="filter_sort_ui",
            weight=self.NEGATIVE_WEIGHTS["filter_sort_ui"],
            present=apply_filter_penalty,
            value="Filter/sort UI detected" if has_filter_sort else None,
        ))
        if apply_filter_penalty:
            confidence += self.NEGATIVE_WEIGHTS["filter_sort_ui"]

        # =======================================================================
        # Final Classification
        # =======================================================================

        # Clamp confidence to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        is_product_page = confidence >= self.CONFIDENCE_THRESHOLD

        return ProductPageClassification(
            is_product_page=is_product_page,
            confidence=round(confidence, 3),
            signals=positive_signals,
            negative_signals=negative_signals,
            detected_product_type=detected_product_type,
        )

    def detect_bot_block(
        self,
        html: str,
        status_code: int,
        headers: Dict[str, str],
    ) -> Optional[str]:
        """
        Detect if response indicates bot blocking.

        Args:
            html: HTML content
            status_code: HTTP status code
            headers: Response headers

        Returns:
            Block reason string or None
        """
        # Check status code
        if status_code in self.BOT_BLOCK_STATUS_CODES:
            return f"HTTP {status_code}"

        # Check headers
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
        for header_key, header_value in self.BOT_BLOCK_HEADER_PATTERNS:
            if header_value is None:
                # Check if header key exists (prefix match)
                if any(k.startswith(header_key.lower()) for k in headers_lower):
                    return f"Header pattern: {header_key}"
            else:
                # Check if header exists with specific value
                if header_key.lower() in headers_lower:
                    if header_value.lower() in headers_lower[header_key.lower()]:
                        return f"Header: {header_key}={header_value}"

        # Check HTML content
        html_lower = html.lower()

        # Check title for block indicators
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_lower)
        if title_match:
            title = title_match.group(1)
            for pattern in self.BOT_BLOCK_HTML_PATTERNS[:5]:  # Check first few patterns in title
                if re.search(pattern, title, re.IGNORECASE):
                    return f"Title: {pattern}"

        # Check body for block indicators
        for pattern in self.BOT_BLOCK_HTML_PATTERNS:
            if re.search(pattern, html_lower):
                return f"Content: {pattern}"

        return None

    def _check_json_ld_product(self, soup: BeautifulSoup) -> Tuple[bool, Optional[str]]:
        """
        Check for JSON-LD Product schema.

        Returns:
            Tuple of (has_product, product_type_or_name)
        """
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                text = script.string or script.get_text()
                if not text:
                    continue

                data = json.loads(text.strip())

                result = self._find_product_in_json_ld(data)
                if result:
                    return True, result

            except (json.JSONDecodeError, Exception):
                continue

        return False, None

    def _find_product_in_json_ld(self, data) -> Optional[str]:
        """
        Recursively find Product in JSON-LD and return type/name.
        """
        if isinstance(data, dict):
            schema_type = data.get("@type", "")

            # Handle type as list
            if isinstance(schema_type, list):
                if "Product" in schema_type:
                    return data.get("name", "Product")[:50] if data.get("name") else "Product"
            elif schema_type == "Product":
                return data.get("name", "Product")[:50] if data.get("name") else "Product"

            # Check @graph
            if "@graph" in data:
                for item in data["@graph"]:
                    result = self._find_product_in_json_ld(item)
                    if result:
                        return result

            # Check mainEntity
            if "mainEntity" in data:
                result = self._find_product_in_json_ld(data["mainEntity"])
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self._find_product_in_json_ld(item)
                if result:
                    return result

        return None

    def _check_og_type_product(self, soup: BeautifulSoup) -> bool:
        """Check if og:type indicates a product."""
        try:
            meta = soup.find("meta", property="og:type")
            if meta and meta.get("content"):
                og_type = meta["content"].lower()
                return "product" in og_type
        except Exception:
            pass
        return False

    def _check_add_to_cart(self, html_lower: str) -> Optional[str]:
        """Check for add to cart / buy now text."""
        for pattern in self.ADD_TO_CART_PATTERNS:
            match = re.search(pattern, html_lower)
            if match:
                return match.group(0)
        return None

    def _check_product_url_pattern(self, url: str) -> bool:
        """Check if URL matches product page patterns."""
        url_lower = url.lower()
        for pattern in self.PRODUCT_URL_PATTERNS:
            if re.search(pattern, url_lower, re.IGNORECASE):
                return True
        return False

    def _check_canonical_exists(self, soup: BeautifulSoup) -> bool:
        """Check if canonical tag exists."""
        try:
            link = soup.find("link", rel="canonical")
            return link is not None and bool(link.get("href"))
        except Exception:
            return False

    def _check_search_category_url(self, url: str) -> bool:
        """Check if URL contains search/category indicators."""
        url_lower = url.lower()
        for pattern in self.SEARCH_CATEGORY_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        return False

    def _check_filter_sort_ui(self, html_lower: str) -> bool:
        """Check for filter/sort UI text."""
        for pattern in self.FILTER_SORT_PATTERNS:
            if re.search(pattern, html_lower):
                return True
        return False
