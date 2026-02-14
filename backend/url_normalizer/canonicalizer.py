"""
HTML parser for extracting canonical URLs from product pages.
"""

import json
import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .models import CanonicalResult, ResolutionSource
from .domain_utils import get_root_domain

logger = logging.getLogger(__name__)


class PageCanonicalizer:
    """
    Extract canonical product URL from HTML content with sanity checks.

    Priority order:
    1. <link rel="canonical">
    2. <meta property="og:url">
    3. JSON-LD Product URL
    4. Final URL (fallback)
    """

    # Paths that indicate homepage (reject these as canonicals)
    HOMEPAGE_PATHS = {"", "/", "/index.html", "/index.htm", "/home", "/default.aspx"}

    def __init__(self, parser: str = "lxml"):
        """
        Initialize the canonicalizer.

        Args:
            parser: BeautifulSoup parser to use ('lxml' or 'html.parser')
        """
        self.parser = parser

    def extract_canonical_info(
        self,
        html: str,
        base_url: str,
    ) -> CanonicalResult:
        """
        Extract canonical URL from multiple sources and select the best one.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            CanonicalResult with all extracted canonicals and selected one
        """
        soup = BeautifulSoup(html, self.parser)

        # Extract all potential canonicals
        canonical_tag = self._extract_canonical_tag(soup)
        og_url = self._extract_og_url(soup)
        json_ld_url = self._extract_json_ld_url(soup)

        # Select the best canonical with sanity checks
        selected, source = self._select_best_canonical(
            canonical_tag=canonical_tag,
            og_url=og_url,
            json_ld_url=json_ld_url,
            final_url=base_url,
        )

        return CanonicalResult(
            canonical_tag=canonical_tag,
            og_url=og_url,
            json_ld_url=json_ld_url,
            selected_canonical=selected,
            source=source,
        )

    def extract_all_canonicals(
        self,
        html: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract all canonical URLs without selection.

        Args:
            html: HTML content

        Returns:
            Tuple of (canonical_tag, og_url, json_ld_url)
        """
        soup = BeautifulSoup(html, self.parser)
        return (
            self._extract_canonical_tag(soup),
            self._extract_og_url(soup),
            self._extract_json_ld_url(soup),
        )

    def select_best_canonical(
        self,
        canonical_tag: Optional[str],
        og_url: Optional[str],
        json_ld_url: Optional[str],
        final_url: str,
    ) -> str:
        """
        Select the best canonical URL from candidates with sanity checks.

        Args:
            canonical_tag: URL from <link rel="canonical">
            og_url: URL from og:url meta tag
            json_ld_url: URL from JSON-LD Product schema
            final_url: The final URL after redirects (fallback)

        Returns:
            Selected canonical URL
        """
        selected, _ = self._select_best_canonical(
            canonical_tag, og_url, json_ld_url, final_url
        )
        return selected

    def _select_best_canonical(
        self,
        canonical_tag: Optional[str],
        og_url: Optional[str],
        json_ld_url: Optional[str],
        final_url: str,
    ) -> Tuple[str, ResolutionSource]:
        """
        Internal method to select canonical with source tracking.

        Sanity checks:
        1. Resolve relative URLs against base URL
        2. Reject cross-domain canonicals (different root domain)
        3. Reject homepage/empty path canonicals

        Args:
            canonical_tag: URL from <link rel="canonical">
            og_url: URL from og:url meta tag
            json_ld_url: URL from JSON-LD Product schema
            final_url: The final URL after redirects

        Returns:
            Tuple of (selected_url, source)
        """
        final_domain = get_root_domain(final_url)

        # Process candidates in priority order
        candidates = [
            (canonical_tag, ResolutionSource.CANONICAL_TAG),
            (og_url, ResolutionSource.OG_URL),
            (json_ld_url, ResolutionSource.JSON_LD),
        ]

        for candidate, source in candidates:
            if not candidate:
                continue

            # Sanity check 1: Resolve relative URLs
            if not candidate.startswith(('http://', 'https://')):
                candidate = urljoin(final_url, candidate)

            # Sanity check 2: Reject cross-domain canonicals
            candidate_domain = get_root_domain(candidate)
            if candidate_domain != final_domain:
                logger.debug(
                    f"Rejecting cross-domain canonical: {candidate} "
                    f"(domain {candidate_domain} != {final_domain})"
                )
                continue

            # Sanity check 3: Reject homepage/empty path canonicals
            parsed = urlparse(candidate)
            if parsed.path.lower().rstrip("/") in self.HOMEPAGE_PATHS or parsed.path == "":
                logger.debug(f"Rejecting homepage canonical: {candidate}")
                continue

            # Passed all checks
            return candidate, source

        # Fallback to final URL
        return final_url, ResolutionSource.REDIRECT_CHAIN

    def _extract_canonical_tag(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract URL from <link rel="canonical">.

        Args:
            soup: Parsed HTML

        Returns:
            Canonical URL or None
        """
        try:
            # Try exact match first
            link = soup.find("link", rel="canonical")
            if link and link.get("href"):
                href = link["href"].strip()
                if href:
                    return href

            # Try case-insensitive
            for link in soup.find_all("link"):
                rel = link.get("rel", [])
                if isinstance(rel, list):
                    rel = " ".join(rel)
                if "canonical" in rel.lower():
                    href = link.get("href", "").strip()
                    if href:
                        return href

        except Exception as e:
            logger.debug(f"Error extracting canonical tag: {e}")

        return None

    def _extract_og_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract URL from <meta property="og:url">.

        Args:
            soup: Parsed HTML

        Returns:
            og:url value or None
        """
        try:
            # Try property attribute
            meta = soup.find("meta", property="og:url")
            if meta and meta.get("content"):
                content = meta["content"].strip()
                if content:
                    return content

            # Try name attribute (some sites use this incorrectly)
            meta = soup.find("meta", attrs={"name": "og:url"})
            if meta and meta.get("content"):
                content = meta["content"].strip()
                if content:
                    return content

        except Exception as e:
            logger.debug(f"Error extracting og:url: {e}")

        return None

    def _extract_json_ld_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract URL from JSON-LD Product schema.

        Args:
            soup: Parsed HTML

        Returns:
            Product URL or None
        """
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                text = script.string or script.get_text()
                if not text:
                    continue

                # Clean up potential issues
                text = text.strip()

                data = json.loads(text)

                # Handle array of schemas
                if isinstance(data, list):
                    for item in data:
                        url = self._find_product_url_in_json_ld(item)
                        if url:
                            return url
                else:
                    url = self._find_product_url_in_json_ld(data)
                    if url:
                        return url

            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.debug(f"Error parsing JSON-LD: {e}")
                continue

        return None

    def _find_product_url_in_json_ld(self, data: dict) -> Optional[str]:
        """
        Recursively find Product URL in JSON-LD data.

        Args:
            data: Parsed JSON-LD dictionary

        Returns:
            Product URL or None
        """
        if not isinstance(data, dict):
            return None

        schema_type = data.get("@type", "")

        # Handle type as list
        if isinstance(schema_type, list):
            schema_type = " ".join(schema_type)

        # Check if this is a Product
        if "Product" in schema_type:
            # First check offers for URL (often more specific)
            offers = data.get("offers", {})
            if isinstance(offers, dict):
                offer_url = offers.get("url")
                if offer_url:
                    return offer_url
            elif isinstance(offers, list) and offers:
                offer_url = offers[0].get("url")
                if offer_url:
                    return offer_url

            # Then check product URL directly
            product_url = data.get("url")
            if product_url:
                return product_url

        # Check @graph for multiple schemas
        if "@graph" in data:
            graph = data["@graph"]
            if isinstance(graph, list):
                for item in graph:
                    url = self._find_product_url_in_json_ld(item)
                    if url:
                        return url

        # Check mainEntity
        main_entity = data.get("mainEntity")
        if main_entity:
            url = self._find_product_url_in_json_ld(main_entity)
            if url:
                return url

        return None

    def extract_page_title(self, html: str) -> Optional[str]:
        """
        Extract page title from HTML.

        Args:
            html: HTML content

        Returns:
            Page title or None
        """
        try:
            soup = BeautifulSoup(html, self.parser)
            title = soup.find("title")
            if title:
                return title.get_text().strip()

            # Try og:title as fallback
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                return og_title["content"].strip()

        except Exception:
            pass

        return None

    def extract_og_type(self, html: str) -> Optional[str]:
        """
        Extract og:type from HTML.

        Args:
            html: HTML content

        Returns:
            og:type value or None
        """
        try:
            soup = BeautifulSoup(html, self.parser)
            meta = soup.find("meta", property="og:type")
            if meta and meta.get("content"):
                return meta["content"].strip().lower()
        except Exception:
            pass

        return None

    def has_json_ld_product(self, html: str) -> bool:
        """
        Check if page has JSON-LD Product schema.

        Args:
            html: HTML content

        Returns:
            True if Product schema exists
        """
        try:
            soup = BeautifulSoup(html, self.parser)
            scripts = soup.find_all("script", type="application/ld+json")

            for script in scripts:
                text = script.string or script.get_text()
                if not text:
                    continue

                data = json.loads(text)

                if self._contains_product_type(data):
                    return True

        except Exception:
            pass

        return False

    def _contains_product_type(self, data) -> bool:
        """
        Recursively check for Product @type in JSON-LD.

        Args:
            data: Parsed JSON-LD data

        Returns:
            True if Product type found
        """
        if isinstance(data, dict):
            schema_type = data.get("@type", "")
            if isinstance(schema_type, list):
                if "Product" in schema_type:
                    return True
            elif schema_type == "Product":
                return True

            # Check @graph
            if "@graph" in data:
                return any(
                    self._contains_product_type(item)
                    for item in data["@graph"]
                    if isinstance(item, dict)
                )

            # Check mainEntity
            if "mainEntity" in data:
                return self._contains_product_type(data["mainEntity"])

        elif isinstance(data, list):
            return any(self._contains_product_type(item) for item in data)

        return False
