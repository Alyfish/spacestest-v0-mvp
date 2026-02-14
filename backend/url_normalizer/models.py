"""
Pydantic models for the Universal Product Link Normalizer.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class URLType(str, Enum):
    """Classification of input URL type."""
    GOOGLE_SHOPPING_SEARCH = "google_shopping_search"    # ?ibp=oshop&q=...
    GOOGLE_SHOPPING_PRODUCT = "google_shopping_product"  # /shopping/product/...
    AFFILIATE_REDIRECT = "affiliate_redirect"            # linksynergy, rstyle, etc.
    SHORTENER = "shortener"                              # bit.ly, amzn.to
    DIRECT_RETAILER = "direct_retailer"                  # Final destination
    UNKNOWN = "unknown"


class ResultType(str, Enum):
    """Final result type for UI handling."""
    PRODUCT = "product"          # Valid PDP
    NON_PRODUCT = "non_product"  # Valid page but not a PDP
    BLOCKED = "blocked"          # Bot blocked
    ERROR = "error"              # Network/timeout error


class ValidationStatus(str, Enum):
    """HTTP validation status."""
    VALID = "valid"
    BOT_BLOCKED = "bot_blocked"
    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    ERROR = "error"


class ResolutionSource(str, Enum):
    """Source of the final resolved URL."""
    CANONICAL_TAG = "canonical_tag"
    OG_URL = "og_url"
    JSON_LD = "json_ld"
    REDIRECT_CHAIN = "redirect_chain"
    SERPAPI = "serpapi"
    ORIGINAL = "original"


# =============================================================================
# Core Models
# =============================================================================

class ProductPageSignal(BaseModel):
    """Individual signal contributing to product page classification."""
    name: str
    weight: float
    present: bool
    value: Optional[str] = None


class ProductPageClassification(BaseModel):
    """Result of product page classification with confidence scoring."""
    is_product_page: bool
    confidence: float = Field(ge=0.0, le=1.0)
    signals: List[ProductPageSignal] = Field(default_factory=list)
    negative_signals: List[ProductPageSignal] = Field(default_factory=list)
    detected_product_type: Optional[str] = None


class RedirectHop(BaseModel):
    """Single hop in redirect chain."""
    url: str
    status_code: int
    location_header: Optional[str] = None


class ProcessingTiming(BaseModel):
    """Timing breakdown for debugging."""
    resolution_ms: int = 0
    canonical_ms: int = 0
    validation_ms: int = 0
    classification_ms: int = 0
    total_ms: int = 0


class URLResolution(BaseModel):
    """Complete resolution result for a single URL."""
    # Input
    original_url: str
    url_type: URLType

    # Resolution
    resolved_url: str
    resolution_source: ResolutionSource
    redirect_chain: List[RedirectHop] = Field(default_factory=list)

    # Canonical (all 3 for debugging)
    canonical_tag_url: Optional[str] = None
    og_url: Optional[str] = None
    json_ld_url: Optional[str] = None
    final_canonical_url: str  # Selected canonical after sanity checks

    # Validation
    validation_status: ValidationStatus
    http_status_code: Optional[int] = None
    blocked_reason: Optional[str] = None

    # Classification
    result_type: ResultType
    classification: Optional[ProductPageClassification] = None

    # Retailer
    retailer_domain: Optional[str] = None
    retailer_name: Optional[str] = None

    # Metadata
    timing: ProcessingTiming = Field(default_factory=ProcessingTiming)
    from_cache: bool = False
    cache_keys_hit: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

    # Google Shopping specific
    fallback_candidates: List[str] = Field(default_factory=list)
    candidate_index_used: Optional[int] = None


class RetailerGroup(BaseModel):
    """Group of products from the same retailer."""
    retailer_domain: str
    retailer_name: str
    product_count: int
    valid_count: int = 0
    urls: List[URLResolution] = Field(default_factory=list)
    avg_confidence: float = 0.0


class NormalizationTelemetry(BaseModel):
    """Telemetry for the normalization request."""
    total_urls: int
    by_url_type: Dict[str, int] = Field(default_factory=dict)
    by_result_type: Dict[str, int] = Field(default_factory=dict)
    resolution_success_count: int = 0
    validation_success_count: int = 0
    product_page_count: int = 0
    cache_hit_count: int = 0
    timing: ProcessingTiming = Field(default_factory=ProcessingTiming)
    per_domain_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)


# =============================================================================
# Internal Models (used within the module)
# =============================================================================

class ResolveResult(BaseModel):
    """Internal result from RedirectResolver."""
    final_url: str
    hops: List[RedirectHop] = Field(default_factory=list)
    final_status_code: int
    html_content: Optional[str] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None
    loop_detected: bool = False


class CanonicalResult(BaseModel):
    """Internal result from PageCanonicalizer."""
    canonical_tag: Optional[str] = None
    og_url: Optional[str] = None
    json_ld_url: Optional[str] = None
    selected_canonical: str
    source: ResolutionSource
