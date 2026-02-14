"""
URLNormalizerClient - Main orchestrator for the URL normalization pipeline.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

from .models import (
    NormalizationTelemetry,
    ProcessingTiming,
    RedirectHop,
    ResolutionSource,
    ResultType,
    RetailerGroup,
    URLResolution,
    URLType,
    ValidationStatus,
)
from .domain_utils import get_root_domain, normalize_domain, should_resolve_further
from .resolver import RedirectResolver
from .canonicalizer import PageCanonicalizer
from .classifier import ProductPageClassifier

logger = logging.getLogger(__name__)


class URLNormalizerClient:
    """
    Main client for URL normalization pipeline.

    Pipeline:
    1. Classify URL type (Google Shopping, affiliate, direct)
    2. Resolve redirects with GET requests
    3. Fetch HTML and extract canonical URL
    4. Validate final URL (HTTP status)
    5. Classify as product page (confidence scoring)
    6. Group by normalized retailer domain
    """

    # Default concurrency settings
    DEFAULT_MAX_CONCURRENT = 15
    DEFAULT_MAX_PER_DOMAIN = 3
    DEFAULT_TIMEOUT_MS = 10000

    def __init__(
        self,
        serp_client=None,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        max_per_domain: int = DEFAULT_MAX_PER_DOMAIN,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        cache_manager=None,
    ):
        """
        Initialize the URL normalizer client.

        Args:
            serp_client: Optional SerpClient instance for Google Shopping resolution
            max_concurrent: Maximum total concurrent requests
            max_per_domain: Maximum concurrent requests per domain
            timeout_ms: Timeout per request in milliseconds
            cache_manager: Optional cache manager for caching results
        """
        self.serp_client = serp_client
        self.cache_manager = cache_manager
        self.max_concurrent = max_concurrent
        self.max_per_domain = max_per_domain
        self.timeout_seconds = timeout_ms / 1000

        # Initialize components
        self.resolver = RedirectResolver(timeout_seconds=self.timeout_seconds)
        self.canonicalizer = PageCanonicalizer()
        self.classifier = ProductPageClassifier()

        # Semaphores for concurrency control
        self.global_semaphore = asyncio.Semaphore(max_concurrent)
        self.domain_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._domain_lock = asyncio.Lock()

    async def normalize_urls(
        self,
        urls: List[str],
        region: str = "us",
        language: str = "en",
        prefer_domains: Optional[List[str]] = None,
        block_domains: Optional[List[str]] = None,
        google_shopping_mode: str = "serpapi",
        include_classification: bool = True,
        max_candidates_per_url: int = 3,
    ) -> Tuple[List[URLResolution], List[RetailerGroup], NormalizationTelemetry]:
        """
        Normalize a batch of URLs.

        Args:
            urls: List of URLs to normalize
            region: Target region for shopping results
            language: Target language
            prefer_domains: Preferred retailer domains (sorted first)
            block_domains: Domains to exclude from results
            google_shopping_mode: "serpapi" or "disabled"
            include_classification: Whether to run product page classification
            max_candidates_per_url: Max Google Shopping candidates to try

        Returns:
            Tuple of (resolutions, retailer_groups, telemetry)
        """
        start_time = time.time()
        prefer_domains = prefer_domains or []
        block_domains = set(d.lower() for d in (block_domains or []))

        # Initialize telemetry
        telemetry = NormalizationTelemetry(
            total_urls=len(urls),
            by_url_type={},
            by_result_type={},
        )

        # Process URLs concurrently
        tasks = [
            self._process_url_with_semaphore(
                url=url,
                region=region,
                language=language,
                google_shopping_mode=google_shopping_mode,
                include_classification=include_classification,
                max_candidates=max_candidates_per_url,
                telemetry=telemetry,
            )
            for url in urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions and build resolutions list
        resolutions: List[URLResolution] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing URL {urls[i]}: {result}")
                resolutions.append(self._create_error_result(
                    original_url=urls[i],
                    error_message=str(result)[:200],
                ))
            else:
                resolutions.append(result)

        # Filter out blocked domains
        if block_domains:
            resolutions = [
                r for r in resolutions
                if r.retailer_domain and r.retailer_domain.lower() not in block_domains
            ]

        # Group by retailer
        groups = self._group_by_retailer(resolutions, prefer_domains)

        # Update telemetry
        self._finalize_telemetry(telemetry, resolutions, start_time)

        return resolutions, groups, telemetry

    async def _process_url_with_semaphore(
        self,
        url: str,
        region: str,
        language: str,
        google_shopping_mode: str,
        include_classification: bool,
        max_candidates: int,
        telemetry: NormalizationTelemetry,
    ) -> URLResolution:
        """
        Process a single URL with semaphore-based concurrency control.
        """
        # Get domain-specific semaphore
        domain = get_root_domain(url)
        domain_sem = await self._get_domain_semaphore(domain)

        async with self.global_semaphore:
            async with domain_sem:
                return await self._process_single_url(
                    url=url,
                    region=region,
                    language=language,
                    google_shopping_mode=google_shopping_mode,
                    include_classification=include_classification,
                    max_candidates=max_candidates,
                    telemetry=telemetry,
                )

    async def _get_domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        """Get or create a semaphore for a specific domain."""
        async with self._domain_lock:
            if domain not in self.domain_semaphores:
                self.domain_semaphores[domain] = asyncio.Semaphore(self.max_per_domain)
            return self.domain_semaphores[domain]

    async def _process_single_url(
        self,
        url: str,
        region: str,
        language: str,
        google_shopping_mode: str,
        include_classification: bool,
        max_candidates: int,
        telemetry: NormalizationTelemetry,
    ) -> URLResolution:
        """
        Process a single URL through the full pipeline.
        """
        timing = ProcessingTiming()
        total_start = time.time()

        # Classify URL type
        url_type = self.resolver.classify_url_type(url)

        # Update telemetry
        type_key = url_type.value
        telemetry.by_url_type[type_key] = telemetry.by_url_type.get(type_key, 0) + 1

        # Handle Google Shopping URLs
        if url_type in (URLType.GOOGLE_SHOPPING_SEARCH, URLType.GOOGLE_SHOPPING_PRODUCT):
            if google_shopping_mode == "serpapi" and self.serp_client:
                result = await self._resolve_google_shopping(
                    url=url,
                    url_type=url_type,
                    region=region,
                    language=language,
                    include_classification=include_classification,
                    max_candidates=max_candidates,
                )
                if result:
                    result.timing.total_ms = int((time.time() - total_start) * 1000)
                    return result
            # Fall through to redirect resolution if serpapi disabled or failed

        # =====================================================================
        # Step 1: Resolve redirects
        # =====================================================================
        resolution_start = time.time()
        resolve_result = await self.resolver.resolve(url, strip_tracking=True, fetch_html=True)
        timing.resolution_ms = int((time.time() - resolution_start) * 1000)

        final_url = resolve_result.final_url
        html_content = resolve_result.html_content
        status_code = resolve_result.final_status_code
        headers = resolve_result.response_headers

        # Build redirect chain
        redirect_chain = resolve_result.hops

        # Determine initial resolution source
        resolution_source = (
            ResolutionSource.REDIRECT_CHAIN
            if len(redirect_chain) > 1
            else ResolutionSource.ORIGINAL
        )

        # Handle resolution errors
        if resolve_result.error:
            validation_status = (
                ValidationStatus.TIMEOUT
                if "timeout" in resolve_result.error.lower()
                else ValidationStatus.ERROR
            )
            return self._create_result(
                original_url=url,
                url_type=url_type,
                resolved_url=final_url,
                resolution_source=resolution_source,
                redirect_chain=redirect_chain,
                final_canonical_url=final_url,
                validation_status=validation_status,
                http_status_code=status_code,
                result_type=ResultType.ERROR,
                timing=timing,
                error_message=resolve_result.error,
            )

        # =====================================================================
        # Step 2: Extract canonical URL
        # =====================================================================
        canonical_tag_url = None
        og_url = None
        json_ld_url = None

        if html_content:
            canonical_start = time.time()
            canonical_result = self.canonicalizer.extract_canonical_info(
                html=html_content,
                base_url=final_url,
            )
            timing.canonical_ms = int((time.time() - canonical_start) * 1000)

            canonical_tag_url = canonical_result.canonical_tag
            og_url = canonical_result.og_url
            json_ld_url = canonical_result.json_ld_url
            final_canonical_url = canonical_result.selected_canonical
            resolution_source = canonical_result.source
        else:
            final_canonical_url = final_url

        # =====================================================================
        # Step 3: Validate + Classify
        # =====================================================================
        validation_status = self._determine_validation_status(status_code)
        blocked_reason = None
        classification = None
        result_type = ResultType.ERROR

        if validation_status == ValidationStatus.VALID and html_content:
            validation_start = time.time()

            if include_classification:
                classification = self.classifier.classify(
                    html=html_content,
                    url=final_canonical_url,
                    status_code=status_code,
                    headers=headers,
                )
                timing.classification_ms = int((time.time() - validation_start) * 1000)

                # Check for bot block in classification
                if classification.negative_signals:
                    for signal in classification.negative_signals:
                        if signal.name == "bot_blocked":
                            validation_status = ValidationStatus.BOT_BLOCKED
                            blocked_reason = signal.value
                            result_type = ResultType.BLOCKED
                            break

                if validation_status == ValidationStatus.VALID:
                    result_type = (
                        ResultType.PRODUCT
                        if classification.is_product_page
                        else ResultType.NON_PRODUCT
                    )
            else:
                result_type = ResultType.PRODUCT  # Assume product if not classifying

        elif validation_status == ValidationStatus.BOT_BLOCKED:
            result_type = ResultType.BLOCKED
            blocked_reason = f"HTTP {status_code}"
        elif validation_status != ValidationStatus.VALID:
            result_type = ResultType.ERROR

        # =====================================================================
        # Step 4: Normalize retailer domain
        # =====================================================================
        retailer_domain, retailer_name = normalize_domain(final_canonical_url)

        timing.total_ms = int((time.time() - total_start) * 1000)

        return self._create_result(
            original_url=url,
            url_type=url_type,
            resolved_url=final_url,
            resolution_source=resolution_source,
            redirect_chain=redirect_chain,
            canonical_tag_url=canonical_tag_url,
            og_url=og_url,
            json_ld_url=json_ld_url,
            final_canonical_url=final_canonical_url,
            validation_status=validation_status,
            http_status_code=status_code,
            blocked_reason=blocked_reason,
            result_type=result_type,
            classification=classification,
            retailer_domain=retailer_domain,
            retailer_name=retailer_name,
            timing=timing,
        )

    async def _resolve_google_shopping(
        self,
        url: str,
        url_type: URLType,
        region: str,
        language: str,
        include_classification: bool,
        max_candidates: int,
    ) -> Optional[URLResolution]:
        """
        Resolve Google Shopping URL using SerpAPI with fallback candidates.
        """
        if not self.serp_client:
            return None

        try:
            # Get candidates from SerpAPI
            products = self.serp_client.resolve_google_shopping_url(url)

            if not products:
                logger.debug(f"No products found for Google Shopping URL: {url}")
                return None

            # Extract candidate URLs
            candidates = [
                p.get("url") or p.get("link")
                for p in products
                if p.get("url") or p.get("link")
            ]

            # Filter out Google URLs
            candidates = [
                c for c in candidates
                if c and "google.com" not in c.lower()
            ]

            if not candidates:
                return None

            # Try candidates in order
            for i, candidate_url in enumerate(candidates[:max_candidates]):
                logger.debug(f"Trying Google Shopping candidate {i+1}: {candidate_url}")

                # Process the candidate URL
                result = await self._process_single_url(
                    url=candidate_url,
                    region=region,
                    language=language,
                    google_shopping_mode="disabled",  # Don't recurse
                    include_classification=include_classification,
                    max_candidates=1,
                    telemetry=NormalizationTelemetry(total_urls=1),
                )

                # Check if this candidate is valid
                if result.validation_status == ValidationStatus.VALID:
                    if result.classification and result.classification.is_product_page:
                        # Success! Update metadata
                        result.original_url = url
                        result.url_type = url_type
                        result.resolution_source = ResolutionSource.SERPAPI
                        result.fallback_candidates = candidates[:max_candidates]
                        result.candidate_index_used = i
                        return result
                    elif not include_classification:
                        # If not classifying, accept valid responses
                        result.original_url = url
                        result.url_type = url_type
                        result.resolution_source = ResolutionSource.SERPAPI
                        result.fallback_candidates = candidates[:max_candidates]
                        result.candidate_index_used = i
                        return result

                logger.debug(
                    f"Candidate {i+1} failed: status={result.validation_status}, "
                    f"is_product={result.classification.is_product_page if result.classification else 'N/A'}"
                )

            # All candidates failed
            logger.warning(f"All {len(candidates[:max_candidates])} Google Shopping candidates failed for: {url}")
            return None

        except Exception as e:
            logger.error(f"Error resolving Google Shopping URL: {e}")
            return None

    def _group_by_retailer(
        self,
        resolutions: List[URLResolution],
        prefer_domains: List[str],
    ) -> List[RetailerGroup]:
        """
        Group resolutions by normalized retailer domain.
        """
        groups: Dict[str, RetailerGroup] = {}
        prefer_domains_lower = set(d.lower() for d in prefer_domains)

        for r in resolutions:
            domain = r.retailer_domain or "unknown"

            if domain not in groups:
                groups[domain] = RetailerGroup(
                    retailer_domain=domain,
                    retailer_name=r.retailer_name or domain,
                    product_count=0,
                    valid_count=0,
                    urls=[],
                )

            groups[domain].urls.append(r)
            groups[domain].product_count += 1

            if r.validation_status == ValidationStatus.VALID:
                groups[domain].valid_count += 1

        # Calculate average confidence
        for group in groups.values():
            confidences = [
                r.classification.confidence
                for r in group.urls
                if r.classification
            ]
            group.avg_confidence = (
                round(sum(confidences) / len(confidences), 3)
                if confidences
                else 0.0
            )

        # Sort groups: preferred domains first, then by product count
        result = list(groups.values())
        result.sort(
            key=lambda g: (
                0 if g.retailer_domain.lower() in prefer_domains_lower else 1,
                -g.product_count,
            )
        )

        return result

    def _determine_validation_status(self, status_code: int) -> ValidationStatus:
        """Determine validation status from HTTP status code."""
        if status_code == 0:
            return ValidationStatus.TIMEOUT
        elif 200 <= status_code < 400:
            return ValidationStatus.VALID
        elif status_code == 404:
            return ValidationStatus.NOT_FOUND
        elif status_code in (403, 503):
            return ValidationStatus.BOT_BLOCKED
        elif status_code == 429:
            return ValidationStatus.RATE_LIMITED
        else:
            return ValidationStatus.ERROR

    def _create_result(
        self,
        original_url: str,
        url_type: URLType,
        resolved_url: str,
        resolution_source: ResolutionSource,
        final_canonical_url: str,
        validation_status: ValidationStatus,
        result_type: ResultType,
        redirect_chain: Optional[List[RedirectHop]] = None,
        canonical_tag_url: Optional[str] = None,
        og_url: Optional[str] = None,
        json_ld_url: Optional[str] = None,
        http_status_code: Optional[int] = None,
        blocked_reason: Optional[str] = None,
        classification=None,
        retailer_domain: Optional[str] = None,
        retailer_name: Optional[str] = None,
        timing: Optional[ProcessingTiming] = None,
        error_message: Optional[str] = None,
        fallback_candidates: Optional[List[str]] = None,
        candidate_index_used: Optional[int] = None,
    ) -> URLResolution:
        """Create a URLResolution result."""
        # Get retailer info if not provided
        if not retailer_domain:
            retailer_domain, retailer_name = normalize_domain(final_canonical_url)

        return URLResolution(
            original_url=original_url,
            url_type=url_type,
            resolved_url=resolved_url,
            resolution_source=resolution_source,
            redirect_chain=redirect_chain or [],
            canonical_tag_url=canonical_tag_url,
            og_url=og_url,
            json_ld_url=json_ld_url,
            final_canonical_url=final_canonical_url,
            validation_status=validation_status,
            http_status_code=http_status_code,
            blocked_reason=blocked_reason,
            result_type=result_type,
            classification=classification,
            retailer_domain=retailer_domain,
            retailer_name=retailer_name,
            timing=timing or ProcessingTiming(),
            error_message=error_message,
            fallback_candidates=fallback_candidates or [],
            candidate_index_used=candidate_index_used,
        )

    def _create_error_result(
        self,
        original_url: str,
        error_message: str,
    ) -> URLResolution:
        """Create an error URLResolution result."""
        domain, name = normalize_domain(original_url)
        return URLResolution(
            original_url=original_url,
            url_type=URLType.UNKNOWN,
            resolved_url=original_url,
            resolution_source=ResolutionSource.ORIGINAL,
            redirect_chain=[],
            final_canonical_url=original_url,
            validation_status=ValidationStatus.ERROR,
            result_type=ResultType.ERROR,
            retailer_domain=domain,
            retailer_name=name,
            error_message=error_message,
        )

    def _finalize_telemetry(
        self,
        telemetry: NormalizationTelemetry,
        resolutions: List[URLResolution],
        start_time: float,
    ) -> None:
        """Finalize telemetry with aggregated stats."""
        telemetry.total_urls = len(resolutions)

        # Count by result type
        for r in resolutions:
            type_key = r.result_type.value
            telemetry.by_result_type[type_key] = telemetry.by_result_type.get(type_key, 0) + 1

        # Count successes
        telemetry.resolution_success_count = sum(
            1 for r in resolutions
            if r.resolution_source != ResolutionSource.ORIGINAL
        )
        telemetry.validation_success_count = sum(
            1 for r in resolutions
            if r.validation_status == ValidationStatus.VALID
        )
        telemetry.product_page_count = sum(
            1 for r in resolutions
            if r.result_type == ResultType.PRODUCT
        )

        # Per-domain stats
        for r in resolutions:
            domain = r.retailer_domain or "unknown"
            if domain not in telemetry.per_domain_stats:
                telemetry.per_domain_stats[domain] = {"total": 0, "success": 0, "product": 0}
            telemetry.per_domain_stats[domain]["total"] += 1
            if r.validation_status == ValidationStatus.VALID:
                telemetry.per_domain_stats[domain]["success"] += 1
            if r.result_type == ResultType.PRODUCT:
                telemetry.per_domain_stats[domain]["product"] += 1

        # Aggregate timing
        total_ms = int((time.time() - start_time) * 1000)
        avg_resolution = sum(r.timing.resolution_ms for r in resolutions) / max(len(resolutions), 1)
        avg_canonical = sum(r.timing.canonical_ms for r in resolutions) / max(len(resolutions), 1)
        avg_classification = sum(r.timing.classification_ms for r in resolutions) / max(len(resolutions), 1)

        telemetry.timing = ProcessingTiming(
            resolution_ms=int(avg_resolution),
            canonical_ms=int(avg_canonical),
            classification_ms=int(avg_classification),
            total_ms=total_ms,
        )
