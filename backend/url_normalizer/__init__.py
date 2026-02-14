"""
Universal Product Link Normalizer

Transforms heterogeneous product URLs (Google Shopping, affiliate links, direct retailer links)
into canonical retailer PDPs with validation, confidence scoring, and retailer grouping.
"""

from .models import (
    URLType,
    ResultType,
    ValidationStatus,
    ResolutionSource,
    ProductPageSignal,
    ProductPageClassification,
    RedirectHop,
    ProcessingTiming,
    URLResolution,
    RetailerGroup,
    NormalizationTelemetry,
)
from .domain_utils import (
    normalize_domain,
    is_affiliate_network,
    is_shortener,
    get_retailer_display_name,
)
from .resolver import RedirectResolver
from .canonicalizer import PageCanonicalizer
from .classifier import ProductPageClassifier
from .client import URLNormalizerClient

__all__ = [
    # Enums
    "URLType",
    "ResultType",
    "ValidationStatus",
    "ResolutionSource",
    # Models
    "ProductPageSignal",
    "ProductPageClassification",
    "RedirectHop",
    "ProcessingTiming",
    "URLResolution",
    "RetailerGroup",
    "NormalizationTelemetry",
    # Utils
    "normalize_domain",
    "is_affiliate_network",
    "is_shortener",
    "get_retailer_display_name",
    # Classes
    "RedirectResolver",
    "PageCanonicalizer",
    "ProductPageClassifier",
    "URLNormalizerClient",
]
