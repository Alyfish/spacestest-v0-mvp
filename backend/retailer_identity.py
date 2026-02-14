"""
RetailerIdentityService - Maps brand names to domains and provides candidate scoring.

This is the critical piece for retailer-preserving URL resolution.
When a user clicks a "Quince" product, we need to ensure we return quince.com, not walmart.com.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetailerInfo:
    """Information about a retailer."""
    brand: str
    domains: List[str]  # Primary domain first, then alternates
    affiliate_network: Optional[str] = None  # Impact, CJ, ShareASale, Rakuten, Amazon Associates
    allow_deep_link: bool = True
    allow_cart_link: bool = False  # Most DTC retailers don't support cart links
    is_marketplace: bool = False  # Amazon, Walmart, Target are marketplaces


# Curated mapping of brand names to retailer info
# This is the source of truth for retailer identity
RETAILER_DATABASE: Dict[str, RetailerInfo] = {
    # ===== DTC / Brand Retailers (prioritize these) =====
    "quince": RetailerInfo(
        brand="Quince",
        domains=["quince.com", "onequince.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "article": RetailerInfo(
        brand="Article",
        domains=["article.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "west elm": RetailerInfo(
        brand="West Elm",
        domains=["westelm.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "westelm": RetailerInfo(
        brand="West Elm",
        domains=["westelm.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "pottery barn": RetailerInfo(
        brand="Pottery Barn",
        domains=["potterybarn.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "potterybarn": RetailerInfo(
        brand="Pottery Barn",
        domains=["potterybarn.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "crate & barrel": RetailerInfo(
        brand="Crate & Barrel",
        domains=["crateandbarrel.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "crate and barrel": RetailerInfo(
        brand="Crate & Barrel",
        domains=["crateandbarrel.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "cb2": RetailerInfo(
        brand="CB2",
        domains=["cb2.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "ikea": RetailerInfo(
        brand="IKEA",
        domains=["ikea.com"],
        affiliate_network="Awin",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "wayfair": RetailerInfo(
        brand="Wayfair",
        domains=["wayfair.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=True,
    ),
    "allmodern": RetailerInfo(
        brand="AllModern",
        domains=["allmodern.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "joss & main": RetailerInfo(
        brand="Joss & Main",
        domains=["jossandmain.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "birch lane": RetailerInfo(
        brand="Birch Lane",
        domains=["birchlane.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "overstock": RetailerInfo(
        brand="Overstock",
        domains=["overstock.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "serena & lily": RetailerInfo(
        brand="Serena & Lily",
        domains=["serenaandlily.com"],
        affiliate_network="ShareASale",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "anthropologie": RetailerInfo(
        brand="Anthropologie",
        domains=["anthropologie.com"],
        affiliate_network="Rakuten",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "urban outfitters": RetailerInfo(
        brand="Urban Outfitters",
        domains=["urbanoutfitters.com"],
        affiliate_network="Rakuten",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "room & board": RetailerInfo(
        brand="Room & Board",
        domains=["roomandboard.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "rejuvenation": RetailerInfo(
        brand="Rejuvenation",
        domains=["rejuvenation.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "etsy": RetailerInfo(
        brand="Etsy",
        domains=["etsy.com"],
        affiliate_network="Awin",
        allow_deep_link=True,
        allow_cart_link=False,
        is_marketplace=True,
    ),
    "1stdibs": RetailerInfo(
        brand="1stDibs",
        domains=["1stdibs.com"],
        affiliate_network="ShareASale",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "chairish": RetailerInfo(
        brand="Chairish",
        domains=["chairish.com"],
        affiliate_network="ShareASale",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "world market": RetailerInfo(
        brand="World Market",
        domains=["worldmarket.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "cost plus world market": RetailerInfo(
        brand="World Market",
        domains=["worldmarket.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "z gallerie": RetailerInfo(
        brand="Z Gallerie",
        domains=["zgallerie.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "parachute": RetailerInfo(
        brand="Parachute",
        domains=["parachutehome.com"],
        affiliate_network="ShareASale",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "brooklinen": RetailerInfo(
        brand="Brooklinen",
        domains=["brooklinen.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "boll & branch": RetailerInfo(
        brand="Boll & Branch",
        domains=["bollandbranch.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "casper": RetailerInfo(
        brand="Casper",
        domains=["casper.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "tuft & needle": RetailerInfo(
        brand="Tuft & Needle",
        domains=["tuftandneedle.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "floyd": RetailerInfo(
        brand="Floyd",
        domains=["floydhome.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "burrow": RetailerInfo(
        brand="Burrow",
        domains=["burrow.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "joybird": RetailerInfo(
        brand="Joybird",
        domains=["joybird.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
    ),
    "interior define": RetailerInfo(
        brand="Interior Define",
        domains=["interiordefine.com"],
        affiliate_network="ShareASale",
        allow_deep_link=True,
        allow_cart_link=False,
    ),

    # ===== Big Box / Marketplaces (lower priority when user selected a DTC brand) =====
    "amazon": RetailerInfo(
        brand="Amazon",
        domains=["amazon.com", "amazon.ca", "amazon.co.uk", "amazon.de", "amzn.to"],
        affiliate_network="Amazon Associates",
        allow_deep_link=True,
        allow_cart_link=True,
        is_marketplace=True,
    ),
    "walmart": RetailerInfo(
        brand="Walmart",
        domains=["walmart.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=True,
        is_marketplace=True,
    ),
    "target": RetailerInfo(
        brand="Target",
        domains=["target.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
        is_marketplace=True,
    ),
    "home depot": RetailerInfo(
        brand="Home Depot",
        domains=["homedepot.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
        is_marketplace=True,
    ),
    "lowe's": RetailerInfo(
        brand="Lowe's",
        domains=["lowes.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
        is_marketplace=True,
    ),
    "lowes": RetailerInfo(
        brand="Lowe's",
        domains=["lowes.com"],
        affiliate_network="Impact",
        allow_deep_link=True,
        allow_cart_link=False,
        is_marketplace=True,
    ),
    "bed bath & beyond": RetailerInfo(
        brand="Bed Bath & Beyond",
        domains=["bedbathandbeyond.com"],
        affiliate_network="CJ",
        allow_deep_link=True,
        allow_cart_link=False,
        is_marketplace=True,
    ),
    "costco": RetailerInfo(
        brand="Costco",
        domains=["costco.com"],
        affiliate_network="None",
        allow_deep_link=True,
        allow_cart_link=False,
        is_marketplace=True,
    ),
}


class RetailerIdentityService:
    """
    Service for resolving brand names to domains and scoring candidate URLs.

    This is the core of retailer-preserving resolution.
    """

    def __init__(self):
        self._brand_to_domain_cache: Dict[str, str] = {}
        self._domain_to_brand_cache: Dict[str, str] = {}
        self._build_caches()

    def _build_caches(self):
        """Build lookup caches from the retailer database."""
        for key, info in RETAILER_DATABASE.items():
            # Brand name (lowercased) -> primary domain
            self._brand_to_domain_cache[key.lower()] = info.domains[0]

            # All domains -> brand name
            for domain in info.domains:
                domain_key = domain.lower().replace("www.", "")
                self._domain_to_brand_cache[domain_key] = info.brand

    def get_retailer_info(self, brand_or_domain: str) -> Optional[RetailerInfo]:
        """
        Get retailer info by brand name or domain.

        Args:
            brand_or_domain: Either a brand name ("Quince") or domain ("quince.com")

        Returns:
            RetailerInfo or None
        """
        key = brand_or_domain.lower().strip()

        # Try direct lookup by brand name
        if key in RETAILER_DATABASE:
            return RETAILER_DATABASE[key]

        # Try lookup by domain
        domain_key = key.replace("www.", "").replace("https://", "").replace("http://", "")
        if "/" in domain_key:
            domain_key = domain_key.split("/")[0]

        brand = self._domain_to_brand_cache.get(domain_key)
        if brand:
            # Find the retailer info by brand
            for info in RETAILER_DATABASE.values():
                if info.brand == brand:
                    return info

        return None

    def resolve_brand_to_domain(self, brand_name: str) -> Optional[str]:
        """
        Resolve a brand name to its primary domain.

        Args:
            brand_name: Brand name from Google Shopping "source" field

        Returns:
            Primary domain (e.g., "quince.com") or None
        """
        if not brand_name:
            return None

        key = brand_name.lower().strip()

        # Direct lookup
        if key in self._brand_to_domain_cache:
            return self._brand_to_domain_cache[key]

        # Fuzzy matching for common variations
        # Remove common suffixes/prefixes
        normalized = re.sub(r'\s*(home|furniture|store|shop|inc\.?|llc\.?|co\.?)$', '', key, flags=re.IGNORECASE)
        normalized = normalized.strip()

        if normalized in self._brand_to_domain_cache:
            return self._brand_to_domain_cache[normalized]

        # Try partial match
        for db_key, domain in self._brand_to_domain_cache.items():
            if db_key in key or key in db_key:
                return domain

        # Last resort: guess the domain from brand name
        guessed_domain = self._guess_domain_from_brand(brand_name)
        return guessed_domain

    def _guess_domain_from_brand(self, brand_name: str) -> str:
        """
        Guess a domain from a brand name when not in database.

        This is a fallback - prefer adding retailers to the database.
        """
        # Clean up the brand name
        cleaned = brand_name.lower().strip()
        cleaned = re.sub(r'[^a-z0-9]', '', cleaned)  # Remove non-alphanumeric

        return f"{cleaned}.com"

    def domain_matches_brand(self, domain: str, brand_name: str) -> bool:
        """
        Check if a domain matches the expected brand.

        Args:
            domain: URL domain (e.g., "quince.com")
            brand_name: Expected brand name (e.g., "Quince")

        Returns:
            True if domain belongs to the brand
        """
        if not domain or not brand_name:
            return False

        # Get expected domains for the brand
        info = self.get_retailer_info(brand_name)
        if info:
            domain_lower = domain.lower().replace("www.", "")
            return any(d.lower() in domain_lower or domain_lower in d.lower() for d in info.domains)

        # Fallback: simple string matching
        brand_cleaned = re.sub(r'[^a-z0-9]', '', brand_name.lower())
        domain_cleaned = re.sub(r'[^a-z0-9]', '', domain.lower())

        return brand_cleaned in domain_cleaned or domain_cleaned in brand_cleaned

    def is_marketplace(self, domain_or_brand: str) -> bool:
        """Check if a retailer is a marketplace (Amazon, Walmart, Target, etc.)."""
        info = self.get_retailer_info(domain_or_brand)
        return info.is_marketplace if info else False

    def score_candidate_url(
        self,
        url: str,
        expected_retailer: Optional[str] = None,
        expected_domain: Optional[str] = None,
        product_title: Optional[str] = None,
    ) -> int:
        """
        Score a candidate URL for retailer-preserving resolution.

        Higher score = better match.

        Scoring rules:
        - +100: Domain matches expected retailer
        - +50: URL looks like a PDP (has /product/, /p/, /dp/, SKU, etc.)
        - +30: Title keywords appear in URL
        - -80: Domain is a marketplace when expected retailer is DTC
        - -50: URL is a Google redirect
        - -30: URL is a search/category page

        Args:
            url: Candidate URL to score
            expected_retailer: Expected retailer name (e.g., "Quince")
            expected_domain: Expected domain (e.g., "quince.com")
            product_title: Product title for keyword matching

        Returns:
            Integer score (higher = better)
        """
        if not url:
            return -1000

        score = 0
        url_lower = url.lower()

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
        except Exception:
            return -1000

        # === Positive signals ===

        # Domain matches expected retailer (+100)
        if expected_retailer and self.domain_matches_brand(domain, expected_retailer):
            score += 100
            logger.debug(f"[SCORE] +100: Domain matches expected retailer '{expected_retailer}'")
        elif expected_domain:
            expected_domain_clean = expected_domain.lower().replace("www.", "")
            if expected_domain_clean in domain or domain in expected_domain_clean:
                score += 100
                logger.debug(f"[SCORE] +100: Domain matches expected domain '{expected_domain}'")

        # URL looks like a PDP (+50)
        pdp_patterns = [
            r'/dp/', r'/gp/product/', r'/product/', r'/products/', r'/p/',
            r'/pd/', r'/pdp/', r'/item/', r'/-/A-', r'/ip/',
            r'sku=', r'product_id=', r'productid=', r'pid=',
        ]
        if any(re.search(pat, url_lower) for pat in pdp_patterns):
            score += 50
            logger.debug(f"[SCORE] +50: URL looks like a PDP")

        # Title keywords in URL (+30)
        if product_title:
            title_words = set(re.findall(r'\b[a-z]{4,}\b', product_title.lower()))
            url_words = set(re.findall(r'\b[a-z]{4,}\b', parsed.path.lower()))
            overlap = title_words & url_words
            if len(overlap) >= 2:
                score += 30
                logger.debug(f"[SCORE] +30: Title keywords in URL: {overlap}")

        # === Negative signals ===

        # Domain is marketplace when expected retailer is DTC (-80)
        if expected_retailer:
            expected_info = self.get_retailer_info(expected_retailer)
            current_info = self.get_retailer_info(domain)

            if expected_info and not expected_info.is_marketplace:
                if current_info and current_info.is_marketplace:
                    score -= 80
                    logger.debug(f"[SCORE] -80: Marketplace URL when expecting DTC retailer")

        # Google redirect (-50)
        if "google.com" in domain:
            score -= 50
            logger.debug(f"[SCORE] -50: Google redirect URL")

        # Search/category page patterns (-30)
        search_patterns = [
            r'/search', r'/s\?', r'/s/', r'/browse/', r'/collections/',
            r'/c/', r'\?q=', r'\?k=', r'/filters/', r'/sb\d+/',
            r'/keyword', r'/category/',
        ]
        if any(re.search(pat, url_lower) for pat in search_patterns):
            score -= 30
            logger.debug(f"[SCORE] -30: URL looks like search/category page")

        return score

    def select_best_candidate(
        self,
        candidates: List[Dict],
        expected_retailer: Optional[str] = None,
        expected_domain: Optional[str] = None,
        product_title: Optional[str] = None,
        strict_mode: bool = True,
    ) -> Optional[Dict]:
        """
        Select the best candidate from a list of URLs.

        Args:
            candidates: List of dicts with 'url' or 'link' key
            expected_retailer: Expected retailer name
            expected_domain: Expected domain
            product_title: Product title for matching
            strict_mode: If True, return None if best candidate doesn't match retailer

        Returns:
            Best matching candidate dict, or None if strict_mode and no match
        """
        if not candidates:
            return None

        scored_candidates = []

        for candidate in candidates:
            url = candidate.get("url") or candidate.get("link") or ""
            if not url:
                continue

            score = self.score_candidate_url(
                url=url,
                expected_retailer=expected_retailer,
                expected_domain=expected_domain,
                product_title=product_title,
            )

            scored_candidates.append({
                **candidate,
                "_score": score,
            })

        if not scored_candidates:
            return None

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x.get("_score", -1000), reverse=True)

        best = scored_candidates[0]
        best_score = best.get("_score", -1000)

        # In strict mode, only return if score indicates retailer match
        if strict_mode and best_score < 50:  # Threshold: at least looks like a PDP
            logger.warning(
                f"[RETAILER] Strict mode: No good match found. "
                f"Best score: {best_score}, expected: {expected_retailer or expected_domain}"
            )
            return None

        # Remove internal score before returning
        best.pop("_score", None)
        return best


# Global singleton instance
retailer_identity_service = RetailerIdentityService()
