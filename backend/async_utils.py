"""
Async utilities for production-ready parallelization.

Provides:
- TTLCache: Thread-safe cache with max size + LRU eviction
- Semaphore helpers: to_thread_with_sem, gather_with_timeout
- In-flight dedupe: get_or_compute (singleflight pattern)
- Safe image download: download_image_safe with size/type guards
- Timing: timed() context manager for debug timing
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, TypeVar

import httpx

T = TypeVar("T")

# ===== SEMAPHORE HELPERS =====


async def to_thread_with_sem(
    sem: asyncio.Semaphore, func: Callable[..., T], *args, **kwargs
) -> T:
    """Run blocking function in thread with semaphore limit.

    Args:
        sem: Semaphore to limit concurrency
        func: Synchronous function to run
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result of func(*args, **kwargs)
    """
    async with sem:
        return await asyncio.to_thread(func, *args, **kwargs)


async def gather_with_timeout(
    tasks: List, timeout: float = 30.0, return_exceptions: bool = True
) -> List:
    """Gather tasks with per-task timeout.

    Args:
        tasks: List of coroutines to run
        timeout: Timeout in seconds for each task
        return_exceptions: If True, exceptions are returned instead of raised

    Returns:
        List of results (or exceptions if return_exceptions=True)
    """

    async def with_timeout(coro):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            return TimeoutError(f"Task timed out after {timeout}s")
        except Exception as e:
            if return_exceptions:
                return e
            raise

    return await asyncio.gather(
        *[with_timeout(t) for t in tasks], return_exceptions=return_exceptions
    )


# ===== CACHING =====


class TTLCache:
    """Thread-safe TTL cache with max size + LRU eviction.

    Features:
    - Async-safe with lock
    - Max size with LRU eviction (oldest first)
    - TTL expiration
    - Move-to-end on access (LRU behavior)
    """

    def __init__(self, max_size: int = 500, default_ttl: int = 600):
        """Initialize cache.

        Args:
            max_size: Maximum number of items (default 500)
            default_ttl: Default TTL in seconds (default 600 = 10 min)
        """
        self._cache: Dict[str, tuple] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    # Move to end (LRU: most recently used)
                    self._cache[key] = self._cache.pop(key)
                    return value
                # Expired - remove it
                del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if not specified)
        """
        async with self._lock:
            # Evict oldest items if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

            self._cache[key] = (value, time.time() + (ttl or self._default_ttl))

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all items from cache."""
        async with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        """Current number of items in cache."""
        return len(self._cache)


def normalize_query(query: str) -> str:
    """Normalize query for cache key (aggressive normalization).

    - Lowercase
    - Strip whitespace
    - Collapse multiple spaces
    - Remove punctuation

    Args:
        query: Raw query string

    Returns:
        Normalized query string
    """
    q = query.lower().strip()
    q = re.sub(r"\s+", " ", q)  # Collapse whitespace
    q = re.sub(r"[^\w\s]", "", q)  # Remove punctuation
    return q


def cache_key(query: str, source: str) -> str:
    """Generate cache key from normalized query + source.

    Args:
        query: Search query
        source: Source identifier (e.g., 'serp', 'exa', 'images')

    Returns:
        MD5 hash of normalized query with source prefix
    """
    normalized = normalize_query(query)
    return hashlib.md5(f"{source}:{normalized}".encode()).hexdigest()


# ===== IN-FLIGHT DEDUPE (Singleflight Pattern) =====


async def get_or_compute(
    in_flight: Dict[str, asyncio.Future],
    cache: TTLCache,
    key: str,
    compute_fn: Callable,
    ttl: int = 600,
) -> Any:
    """Get from cache, or compute once (even if N concurrent requests).

    Implements the "singleflight" pattern:
    - First request computes and caches
    - Concurrent requests wait for the first
    - Prevents "retry storm" from hammering APIs

    Args:
        in_flight: Dict tracking in-progress computations
        cache: TTLCache to store results
        key: Cache key
        compute_fn: Async callable that computes the value
        ttl: Cache TTL in seconds

    Returns:
        Cached or computed value

    Raises:
        Exception from compute_fn if computation fails
    """
    # Check cache first
    cached = await cache.get(key)
    if cached is not None:
        return cached

    # Check if already computing
    if key in in_flight:
        return await in_flight[key]

    # Create future for this computation
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    # Prevent "Future exception was never retrieved" noise when the creator
    # sets an exception but no concurrent waiter actually awaits this future.
    future.add_done_callback(
        lambda f: f.exception() if not f.cancelled() else None
    )
    in_flight[key] = future

    try:
        result = await compute_fn()
        await cache.set(key, result, ttl)
        future.set_result(result)
        return result
    except Exception as e:
        future.set_exception(e)
        raise
    finally:
        in_flight.pop(key, None)


# ===== IMAGE DOWNLOAD WITH GUARDS =====

MAX_IMAGE_SIZE = 8 * 1024 * 1024  # 8MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


async def download_image_safe(
    http_client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
    max_size: int = MAX_IMAGE_SIZE,
) -> Optional[bytes]:
    """Download image with size/type guards.

    - HEAD request first to check content-type and size
    - Only downloads allowed image types
    - Rejects images larger than max_size
    - Uses semaphore for concurrency control

    Args:
        http_client: Shared httpx AsyncClient
        sem: Semaphore for concurrency limit
        url: Image URL to download
        max_size: Maximum allowed size in bytes

    Returns:
        Image bytes or None if failed/rejected
    """
    async with sem:
        try:
            # HEAD first to check size/type (fast rejection)
            head = await http_client.head(url, timeout=5.0)
            content_type = head.headers.get("content-type", "").split(";")[0].strip()
            content_length = int(head.headers.get("content-length", 0))

            if content_type not in ALLOWED_CONTENT_TYPES:
                return None
            if content_length > max_size:
                return None

            # GET the actual content
            response = await http_client.get(url, timeout=10.0)
            response.raise_for_status()

            # Double-check size after download
            if len(response.content) > max_size:
                return None

            return response.content
        except Exception:
            return None


async def download_images_batch(
    http_client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    urls: List[str],
    max_size: int = MAX_IMAGE_SIZE,
) -> List[Optional[bytes]]:
    """Download multiple images in parallel.

    Args:
        http_client: Shared httpx AsyncClient
        sem: Semaphore for concurrency limit
        urls: List of image URLs
        max_size: Maximum allowed size per image

    Returns:
        List of image bytes (or None for failed downloads)
    """
    tasks = [download_image_safe(http_client, sem, url, max_size) for url in urls]
    return await asyncio.gather(*tasks)


# ===== TIMING =====


@asynccontextmanager
async def timed(name: str, timings: Dict[str, float]):
    """Context manager to track timing in milliseconds.

    Usage:
        timings = {}
        async with timed("my_operation", timings):
            await do_something()
        print(timings)  # {"my_operation": 123.45}

    Args:
        name: Name for this timing
        timings: Dict to store timing (modified in place)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        timings[name] = round((time.perf_counter() - start) * 1000, 2)


def format_timings(timings: Dict[str, float]) -> str:
    """Format timings dict for logging.

    Args:
        timings: Dict of {name: milliseconds}

    Returns:
        Formatted string like "color: 1234ms, style: 567ms"
    """
    return ", ".join(f"{k}: {v}ms" for k, v in timings.items())
