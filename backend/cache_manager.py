"""
Caching layer for expensive API calls (SerpAPI, Exa, Furniture Analysis).

Supports:
- In-memory TTL cache (fast, lost on restart)
- Optional disk cache (slower, survives restart)

Cache keys are generated from query parameters to ensure deterministic lookups.
"""

import hashlib
import json
import os
import logging
from typing import Any, Optional, Dict, List
from threading import Lock

logger = logging.getLogger("spaces_ai.cache")


class CacheStats:
    """Track cache hit/miss statistics for monitoring."""

    def __init__(self):
        self._lock = Lock()
        self._stats: Dict[str, Dict[str, int]] = {}

    def record(self, cache_name: str, hit: bool):
        with self._lock:
            if cache_name not in self._stats:
                self._stats[cache_name] = {"hits": 0, "misses": 0}
            key = "hits" if hit else "misses"
            self._stats[cache_name][key] += 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            result = {}
            for name, counts in self._stats.items():
                total = counts["hits"] + counts["misses"]
                ratio = counts["hits"] / total if total > 0 else 0.0
                result[name] = {**counts, "hit_ratio": f"{ratio:.2%}"}
            return result


# Global stats tracker
cache_stats = CacheStats()


def _generate_cache_key(*args, **kwargs) -> str:
    """Generate a deterministic cache key from arguments using SHA256."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(key_data.encode()).hexdigest()[:32]


class CacheManager:
    """
    Centralized cache manager for API calls.

    Provides separate caches for:
    - Product searches (SerpAPI, Exa) - 24 hour TTL
    - Furniture analysis (per image region) - 7 day TTL
    - URL Normalizer caches:
      - Redirect resolution - 1 day TTL
      - Canonical extraction - 7 day TTL
      - Validation result - 12 hour TTL
      - Shopping candidates - 3 day TTL
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize cache manager.

        Args:
            config: Optional configuration dict with:
                - product_search_ttl: TTL for product searches (default: 24 hours)
                - furniture_analysis_ttl: TTL for furniture analysis (default: 7 days)
                - url_redirect_ttl: TTL for URL redirect resolution (default: 1 day)
                - url_canonical_ttl: TTL for canonical extraction (default: 7 days)
                - url_validation_ttl: TTL for validation results (default: 12 hours)
                - url_shopping_ttl: TTL for shopping candidates (default: 3 days)
                - max_size: Maximum entries per cache (default: 1000)
                - use_disk_cache: Whether to enable disk persistence (default: False)
                - disk_cache_dir: Directory for disk cache (default: data/cache)
        """
        self.config = config or {}

        # Default configuration
        self.product_search_ttl = self.config.get("product_search_ttl", 24 * 60 * 60)
        self.furniture_analysis_ttl = self.config.get("furniture_analysis_ttl", 7 * 24 * 60 * 60)
        self.max_size = self.config.get("max_size", 1000)
        self.use_disk_cache = self.config.get("use_disk_cache", False)
        self.disk_cache_dir = self.config.get("disk_cache_dir", "data/cache")

        # URL Normalizer TTLs
        self.url_redirect_ttl = self.config.get("url_redirect_ttl", 24 * 60 * 60)  # 1 day
        self.url_canonical_ttl = self.config.get("url_canonical_ttl", 7 * 24 * 60 * 60)  # 7 days
        self.url_validation_ttl = self.config.get("url_validation_ttl", 12 * 60 * 60)  # 12 hours
        self.url_shopping_ttl = self.config.get("url_shopping_ttl", 3 * 24 * 60 * 60)  # 3 days

        # Initialize in-memory caches
        self._use_ttl_cache = False
        try:
            from cachetools import TTLCache
            self._product_cache = TTLCache(maxsize=self.max_size, ttl=self.product_search_ttl)
            self._furniture_cache = TTLCache(maxsize=self.max_size, ttl=self.furniture_analysis_ttl)
            # URL Normalizer caches
            self._url_redirect_cache = TTLCache(maxsize=self.max_size, ttl=self.url_redirect_ttl)
            self._url_canonical_cache = TTLCache(maxsize=self.max_size, ttl=self.url_canonical_ttl)
            self._url_validation_cache = TTLCache(maxsize=self.max_size, ttl=self.url_validation_ttl)
            self._url_shopping_cache = TTLCache(maxsize=self.max_size, ttl=self.url_shopping_ttl)
            self._use_ttl_cache = True
            logger.info(f"Memory cache initialized with TTL (max_size={self.max_size})")
        except ImportError:
            logger.warning("cachetools not installed, using simple dict cache (no TTL)")
            self._product_cache = {}
            self._furniture_cache = {}
            self._url_redirect_cache = {}
            self._url_canonical_cache = {}
            self._url_validation_cache = {}
            self._url_shopping_cache = {}

        # Initialize disk cache if enabled
        self._disk_cache = None
        if self.use_disk_cache:
            try:
                import diskcache
                os.makedirs(self.disk_cache_dir, exist_ok=True)
                self._disk_cache = diskcache.Cache(self.disk_cache_dir)
                logger.info(f"Disk cache initialized at {self.disk_cache_dir}")
            except ImportError:
                logger.warning("diskcache not installed, disk caching disabled")

        self._lock = Lock()

    # ==================== Product Search Caching ====================

    def get_product_search(
        self,
        api: str,
        query: str,
        num_results: int,
        extra_params: Optional[Dict] = None
    ) -> Optional[List[Dict]]:
        """
        Get cached product search results.

        Args:
            api: API identifier ("serp" or "exa")
            query: Search query string
            num_results: Number of results requested
            extra_params: Additional parameters that affect results

        Returns:
            Cached results list if found, None otherwise
        """
        key = f"product:{api}:{_generate_cache_key(query, num_results, extra_params)}"

        with self._lock:
            # Try memory cache first
            if key in self._product_cache:
                cache_stats.record(f"product_{api}", hit=True)
                logger.debug(f"Memory cache HIT: {api} - {query[:30]}...")
                return self._product_cache[key]

            # Try disk cache
            if self._disk_cache and key in self._disk_cache:
                result = self._disk_cache[key]
                # Promote to memory cache
                self._product_cache[key] = result
                cache_stats.record(f"product_{api}", hit=True)
                logger.debug(f"Disk cache HIT: {api} - {query[:30]}...")
                return result

        cache_stats.record(f"product_{api}", hit=False)
        return None

    def set_product_search(
        self,
        api: str,
        query: str,
        num_results: int,
        results: List[Dict],
        extra_params: Optional[Dict] = None
    ):
        """
        Cache product search results.

        Args:
            api: API identifier ("serp" or "exa")
            query: Search query string
            num_results: Number of results requested
            results: List of product results to cache
            extra_params: Additional parameters that affect results
        """
        if not results:
            return  # Don't cache empty results

        key = f"product:{api}:{_generate_cache_key(query, num_results, extra_params)}"

        with self._lock:
            # Store in memory cache
            self._product_cache[key] = results

            # Store in disk cache
            if self._disk_cache:
                self._disk_cache.set(key, results, expire=self.product_search_ttl)

        logger.info(f"Cached {len(results)} products for {api}: {query[:40]}...")

    # ==================== Furniture Analysis Caching ====================

    def get_furniture_analysis(
        self,
        project_id: str,
        image_hash: str,
        bbox_key: str
    ) -> Optional[Dict]:
        """
        Get cached furniture analysis for a specific image region.

        Args:
            project_id: Project identifier
            image_hash: Hash of the image bytes (for change detection)
            bbox_key: String representation of bounding box

        Returns:
            Cached analysis dict if found, None otherwise
        """
        key = f"furniture:{project_id}:{image_hash}:{bbox_key}"

        with self._lock:
            if key in self._furniture_cache:
                cache_stats.record("furniture_analysis", hit=True)
                logger.debug(f"Furniture cache HIT: {bbox_key}")
                return self._furniture_cache[key]

            if self._disk_cache and key in self._disk_cache:
                result = self._disk_cache[key]
                self._furniture_cache[key] = result
                cache_stats.record("furniture_analysis", hit=True)
                return result

        cache_stats.record("furniture_analysis", hit=False)
        return None

    def set_furniture_analysis(
        self,
        project_id: str,
        image_hash: str,
        bbox_key: str,
        analysis: Dict
    ):
        """
        Cache furniture analysis for a specific image region.

        Args:
            project_id: Project identifier
            image_hash: Hash of the image bytes
            bbox_key: String representation of bounding box
            analysis: Analysis result dict to cache
        """
        key = f"furniture:{project_id}:{image_hash}:{bbox_key}"

        with self._lock:
            self._furniture_cache[key] = analysis

            if self._disk_cache:
                self._disk_cache.set(key, analysis, expire=self.furniture_analysis_ttl)

        logger.debug(f"Cached furniture analysis for {bbox_key}")

    # ==================== URL Normalizer Caching ====================

    def get_redirect_resolution(self, url: str) -> Optional[Dict]:
        """
        Get cached redirect resolution for a URL.

        Args:
            url: Original URL

        Returns:
            Cached resolution dict if found, None otherwise
        """
        key = f"url_redirect:{_generate_cache_key(url)}"

        with self._lock:
            if key in self._url_redirect_cache:
                cache_stats.record("url_redirect", hit=True)
                return self._url_redirect_cache[key]

            if self._disk_cache and key in self._disk_cache:
                result = self._disk_cache[key]
                self._url_redirect_cache[key] = result
                cache_stats.record("url_redirect", hit=True)
                return result

        cache_stats.record("url_redirect", hit=False)
        return None

    def set_redirect_resolution(self, url: str, resolution: Dict):
        """
        Cache redirect resolution for a URL.

        Args:
            url: Original URL
            resolution: Resolution dict to cache
        """
        key = f"url_redirect:{_generate_cache_key(url)}"

        with self._lock:
            self._url_redirect_cache[key] = resolution
            if self._disk_cache:
                self._disk_cache.set(key, resolution, expire=self.url_redirect_ttl)

    def get_canonical_extraction(self, url: str) -> Optional[Dict]:
        """
        Get cached canonical extraction for a URL.

        Args:
            url: Final URL (after redirects)

        Returns:
            Cached canonical dict if found, None otherwise
        """
        key = f"url_canonical:{_generate_cache_key(url)}"

        with self._lock:
            if key in self._url_canonical_cache:
                cache_stats.record("url_canonical", hit=True)
                return self._url_canonical_cache[key]

            if self._disk_cache and key in self._disk_cache:
                result = self._disk_cache[key]
                self._url_canonical_cache[key] = result
                cache_stats.record("url_canonical", hit=True)
                return result

        cache_stats.record("url_canonical", hit=False)
        return None

    def set_canonical_extraction(self, url: str, canonical: Dict):
        """
        Cache canonical extraction for a URL.

        Args:
            url: Final URL (after redirects)
            canonical: Canonical extraction dict to cache
        """
        key = f"url_canonical:{_generate_cache_key(url)}"

        with self._lock:
            self._url_canonical_cache[key] = canonical
            if self._disk_cache:
                self._disk_cache.set(key, canonical, expire=self.url_canonical_ttl)

    def get_validation_result(self, url: str) -> Optional[Dict]:
        """
        Get cached validation result for a URL.

        Args:
            url: URL to check

        Returns:
            Cached validation dict if found, None otherwise
        """
        key = f"url_validation:{_generate_cache_key(url)}"

        with self._lock:
            if key in self._url_validation_cache:
                cache_stats.record("url_validation", hit=True)
                return self._url_validation_cache[key]

            if self._disk_cache and key in self._disk_cache:
                result = self._disk_cache[key]
                self._url_validation_cache[key] = result
                cache_stats.record("url_validation", hit=True)
                return result

        cache_stats.record("url_validation", hit=False)
        return None

    def set_validation_result(self, url: str, validation: Dict):
        """
        Cache validation result for a URL.

        Args:
            url: URL that was validated
            validation: Validation result dict to cache
        """
        key = f"url_validation:{_generate_cache_key(url)}"

        with self._lock:
            self._url_validation_cache[key] = validation
            if self._disk_cache:
                self._disk_cache.set(key, validation, expire=self.url_validation_ttl)

    def get_shopping_candidates(self, query: str) -> Optional[List[Dict]]:
        """
        Get cached Google Shopping candidates for a query.

        Args:
            query: Search query or Google Shopping URL

        Returns:
            Cached candidates list if found, None otherwise
        """
        key = f"url_shopping:{_generate_cache_key(query)}"

        with self._lock:
            if key in self._url_shopping_cache:
                cache_stats.record("url_shopping", hit=True)
                return self._url_shopping_cache[key]

            if self._disk_cache and key in self._disk_cache:
                result = self._disk_cache[key]
                self._url_shopping_cache[key] = result
                cache_stats.record("url_shopping", hit=True)
                return result

        cache_stats.record("url_shopping", hit=False)
        return None

    def set_shopping_candidates(self, query: str, candidates: List[Dict]):
        """
        Cache Google Shopping candidates for a query.

        Args:
            query: Search query or Google Shopping URL
            candidates: List of candidate products to cache
        """
        if not candidates:
            return  # Don't cache empty results

        key = f"url_shopping:{_generate_cache_key(query)}"

        with self._lock:
            self._url_shopping_cache[key] = candidates
            if self._disk_cache:
                self._disk_cache.set(key, candidates, expire=self.url_shopping_ttl)

    # ==================== Cache Management ====================

    def clear_project_cache(self, project_id: str):
        """
        Clear all cached data for a specific project.

        Args:
            project_id: Project to clear cache for
        """
        with self._lock:
            # Clear from memory cache
            keys_to_remove = [k for k in self._furniture_cache if project_id in k]
            for key in keys_to_remove:
                del self._furniture_cache[key]

            # Clear from disk cache
            if self._disk_cache:
                for key in list(self._disk_cache):
                    if project_id in key:
                        del self._disk_cache[key]

        logger.info(f"Cleared cache for project {project_id}")

    def clear_all(self):
        """Clear all caches."""
        with self._lock:
            self._product_cache.clear()
            self._furniture_cache.clear()
            self._url_redirect_cache.clear()
            self._url_canonical_cache.clear()
            self._url_validation_cache.clear()
            self._url_shopping_cache.clear()
            if self._disk_cache:
                self._disk_cache.clear()
        logger.info("Cleared all caches")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "memory_product_count": len(self._product_cache),
            "memory_furniture_count": len(self._furniture_cache),
            "memory_url_redirect_count": len(self._url_redirect_cache),
            "memory_url_canonical_count": len(self._url_canonical_cache),
            "memory_url_validation_count": len(self._url_validation_cache),
            "memory_url_shopping_count": len(self._url_shopping_cache),
            "disk_enabled": self._disk_cache is not None,
            "ttl_enabled": self._use_ttl_cache,
            "hit_miss_stats": cache_stats.get_stats()
        }


# Global cache manager instance
# Configuration can be overridden via environment variables
cache_manager = CacheManager(config={
    "product_search_ttl": int(os.getenv("CACHE_PRODUCT_TTL", 24 * 60 * 60)),
    "furniture_analysis_ttl": int(os.getenv("CACHE_FURNITURE_TTL", 7 * 24 * 60 * 60)),
    "max_size": int(os.getenv("CACHE_MAX_SIZE", 1000)),
    "use_disk_cache": os.getenv("USE_DISK_CACHE", "false").lower() == "true",
    "disk_cache_dir": os.getenv("CACHE_DIR", "data/cache"),
    # URL Normalizer cache TTLs
    "url_redirect_ttl": int(os.getenv("CACHE_URL_REDIRECT_TTL", 24 * 60 * 60)),  # 1 day
    "url_canonical_ttl": int(os.getenv("CACHE_URL_CANONICAL_TTL", 7 * 24 * 60 * 60)),  # 7 days
    "url_validation_ttl": int(os.getenv("CACHE_URL_VALIDATION_TTL", 12 * 60 * 60)),  # 12 hours
    "url_shopping_ttl": int(os.getenv("CACHE_URL_SHOPPING_TTL", 3 * 24 * 60 * 60)),  # 3 days
})
