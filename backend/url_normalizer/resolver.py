"""
HTTP GET-based redirect chain resolver with tracking parameter removal.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import httpx

from .models import RedirectHop, ResolveResult, URLType
from .domain_utils import is_affiliate_network, is_google_domain, is_shortener

logger = logging.getLogger(__name__)


# =============================================================================
# Tracking Parameters to Strip
# =============================================================================

# Parameters to always remove (tracking/analytics)
TRACKING_PARAMS_TO_REMOVE = {
    # UTM parameters
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_cid", "utm_reader", "utm_name", "utm_social", "utm_social-type",
    # Google Analytics / Ads
    "gclid", "gclsrc", "dclid", "_ga", "_gl", "_gac",
    # Facebook
    "fbclid", "fb_action_ids", "fb_action_types", "fb_source", "fb_ref",
    # Microsoft / Bing
    "msclkid",
    # General tracking
    "ref", "ref_", "referrer", "source", "src", "partner",
    "affiliate", "aff", "affid", "aff_id", "affiliate_id",
    "campaign", "cmp", "cmpid", "campaign_id",
    "track", "tracking", "trk", "trkid",
    "clickid", "click_id", "irclickid",
    # Social
    "twclid", "ttclid", "li_fat_id", "mc_cid", "mc_eid",
    # Misc
    "origin", "sref", "spref", "reflink", "srsltid",
    "zanpid", "kenshoo", "ef_id",
    # Email tracking
    "email", "email_source", "email_token",
    "mkt_tok", "sfmc_id", "_bta_tid", "_bta_c",
}

# Parameters to preserve (product identity/variants)
ESSENTIAL_PARAMS_TO_PRESERVE = {
    # Product identifiers
    "sku", "skuid", "sku_id", "asin", "item", "itemid", "item_id",
    "product", "productid", "product_id", "pid", "id",
    # Variants
    "variant", "variantid", "variant_id", "vid",
    "color", "colour", "size", "dimension",
    "option", "options", "selected",
    # Quantity
    "qty", "quantity",
    # Region/locale (important for correct product)
    "locale", "region", "country", "lang", "language",
    # IKEA specific
    "artnumber",
    # Wayfair specific
    "piid",
}


# =============================================================================
# Google Shopping URL Patterns
# =============================================================================

GOOGLE_SHOPPING_SEARCH_PATTERNS = [
    r"google\.[^/]+/search.*[?&]ibp=oshop",
    r"google\.[^/]+/search.*[?&]tbm=shop",
]

GOOGLE_SHOPPING_PRODUCT_PATTERNS = [
    r"google\.[^/]+/shopping/product/",
    r"shopping\.google\.[^/]+/",
    r"google\.[^/]+/aclk",
    r"google\.[^/]+/url\?",
]


# =============================================================================
# RedirectResolver Class
# =============================================================================

class RedirectResolver:
    """
    Resolves redirect chains using GET requests with loop detection.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    DEFAULT_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_redirects: int = 10,
        user_agent: Optional[str] = None,
        max_content_size: int = 2 * 1024 * 1024,  # 2MB
    ):
        """
        Initialize the redirect resolver.

        Args:
            timeout_seconds: Timeout for each request
            max_redirects: Maximum number of redirects to follow
            user_agent: Custom user agent string
            max_content_size: Maximum HTML content size to return
        """
        self.timeout = timeout_seconds
        self.max_redirects = max_redirects
        self.max_content_size = max_content_size

        self.headers = self.DEFAULT_HEADERS.copy()
        self.headers["User-Agent"] = user_agent or self.DEFAULT_USER_AGENT

    async def resolve(
        self,
        url: str,
        strip_tracking: bool = True,
        fetch_html: bool = True,
    ) -> ResolveResult:
        """
        Resolve URL through redirect chain.

        Args:
            url: URL to resolve
            strip_tracking: Whether to strip tracking parameters
            fetch_html: Whether to fetch HTML content of final page

        Returns:
            ResolveResult with final URL, redirect chain, and optional HTML
        """
        visited: Set[str] = set()
        hops: List[RedirectHop] = []
        current_url = url
        html_content: Optional[str] = None
        response_headers: Dict[str, str] = {}
        final_status = 0

        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=self.timeout,
            headers=self.headers,
        ) as client:
            for hop_num in range(self.max_redirects):
                # Loop detection
                normalized_url = self._normalize_for_comparison(current_url)
                if normalized_url in visited:
                    logger.warning(f"Redirect loop detected at: {current_url}")
                    return ResolveResult(
                        final_url=current_url,
                        hops=hops,
                        final_status_code=final_status or 0,
                        loop_detected=True,
                        error="Redirect loop detected",
                    )
                visited.add(normalized_url)

                try:
                    response = await client.get(current_url)
                    final_status = response.status_code
                    response_headers = dict(response.headers)

                    hop = RedirectHop(
                        url=current_url,
                        status_code=response.status_code,
                        location_header=response.headers.get("location"),
                    )
                    hops.append(hop)

                    # Check for redirect
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            logger.warning(f"Redirect without Location header: {current_url}")
                            break

                        # Resolve relative URL
                        next_url = urljoin(current_url, location)

                        # Check for same URL redirect
                        if self._normalize_for_comparison(next_url) == normalized_url:
                            logger.warning(f"Same URL redirect: {current_url}")
                            break

                        current_url = next_url
                        continue

                    # Non-redirect response - this is the final URL
                    if fetch_html and response.status_code == 200:
                        content_type = response.headers.get("content-type", "")
                        if "text/html" in content_type:
                            # Read content with size limit
                            content = response.content[:self.max_content_size]
                            # Try to decode
                            try:
                                html_content = content.decode("utf-8")
                            except UnicodeDecodeError:
                                try:
                                    html_content = content.decode("latin-1")
                                except Exception:
                                    html_content = None

                    break

                except httpx.TimeoutException:
                    logger.warning(f"Timeout resolving URL: {current_url}")
                    hops.append(RedirectHop(url=current_url, status_code=0))
                    return ResolveResult(
                        final_url=current_url,
                        hops=hops,
                        final_status_code=0,
                        error="Request timeout",
                    )

                except httpx.RequestError as e:
                    logger.warning(f"Request error resolving URL: {current_url} - {e}")
                    hops.append(RedirectHop(url=current_url, status_code=0))
                    return ResolveResult(
                        final_url=current_url,
                        hops=hops,
                        final_status_code=0,
                        error=f"Request error: {str(e)[:100]}",
                    )

                except Exception as e:
                    logger.error(f"Unexpected error resolving URL: {current_url} - {e}")
                    return ResolveResult(
                        final_url=current_url,
                        hops=hops,
                        final_status_code=0,
                        error=f"Unexpected error: {str(e)[:100]}",
                    )

        # Strip tracking parameters from final URL
        final_url = current_url
        if strip_tracking:
            final_url = self.strip_tracking_params(final_url)

        return ResolveResult(
            final_url=final_url,
            hops=hops,
            final_status_code=final_status,
            html_content=html_content,
            response_headers=response_headers,
        )

    def classify_url_type(self, url: str) -> URLType:
        """
        Classify URL type based on patterns.

        Args:
            url: URL to classify

        Returns:
            URLType enum value
        """
        url_lower = url.lower()

        # Check Google Shopping search patterns
        for pattern in GOOGLE_SHOPPING_SEARCH_PATTERNS:
            if re.search(pattern, url_lower):
                return URLType.GOOGLE_SHOPPING_SEARCH

        # Check Google Shopping product patterns
        for pattern in GOOGLE_SHOPPING_PRODUCT_PATTERNS:
            if re.search(pattern, url_lower):
                return URLType.GOOGLE_SHOPPING_PRODUCT

        # Check affiliate networks
        if is_affiliate_network(url):
            return URLType.AFFILIATE_REDIRECT

        # Check shorteners
        if is_shortener(url):
            return URLType.SHORTENER

        # Check other Google URLs that might need resolution
        if is_google_domain(url) and any(p in url_lower for p in ["/url?", "/aclk", "redirect"]):
            return URLType.AFFILIATE_REDIRECT

        return URLType.DIRECT_RETAILER

    @staticmethod
    def strip_tracking_params(url: str) -> str:
        """
        Remove known tracking parameters from URL while preserving essential ones.

        Args:
            url: URL to clean

        Returns:
            Cleaned URL
        """
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)

            # Filter parameters
            cleaned_params = {}
            for key, values in query_params.items():
                key_lower = key.lower()

                # Always preserve essential params
                if key_lower in ESSENTIAL_PARAMS_TO_PRESERVE:
                    cleaned_params[key] = values
                    continue

                # Remove tracking params
                if key_lower in TRACKING_PARAMS_TO_REMOVE:
                    continue

                # Remove params that look like tracking IDs
                if any(pattern in key_lower for pattern in ["click", "track", "ref", "campaign"]):
                    continue

                # Keep the rest
                cleaned_params[key] = values

            # Rebuild URL
            new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ""
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                "",  # Drop fragment
            ))

        except Exception as e:
            logger.warning(f"Error stripping tracking params: {e}")
            return url

    @staticmethod
    def _normalize_for_comparison(url: str) -> str:
        """
        Normalize URL for loop detection comparison.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL string for comparison
        """
        try:
            parsed = urlparse(url.lower())
            # Normalize: lowercase, remove trailing slash, remove fragment
            path = parsed.path.rstrip("/") or "/"
            return f"{parsed.scheme}://{parsed.netloc}{path}?{parsed.query}"
        except Exception:
            return url.lower()

    @staticmethod
    def extract_google_search_query(url: str) -> Optional[str]:
        """
        Extract search query from Google Shopping URL.

        Args:
            url: Google Shopping URL

        Returns:
            Search query or None
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return params.get("q", [None])[0]
        except Exception:
            return None

    @staticmethod
    def is_success_status(status_code: int) -> bool:
        """Check if status code indicates success."""
        return 200 <= status_code < 400

    @staticmethod
    def is_redirect_status(status_code: int) -> bool:
        """Check if status code indicates redirect."""
        return status_code in (301, 302, 303, 307, 308)

    @staticmethod
    def is_blocked_status(status_code: int) -> bool:
        """Check if status code indicates blocking/rate limiting."""
        return status_code in (403, 429, 503)
