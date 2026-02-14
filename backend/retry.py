"""
Production-grade retry decorators with exponential backoff.

Provides @retry_sync and @retry_async decorators for resilient
API calls with configurable backoff, jitter, and error handling.
"""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Callable, Optional, Set, Tuple, Type, Union

import httpx
import requests

logger = logging.getLogger("spaces_ai.retry")

# Default retryable exceptions for sync HTTP calls
RETRYABLE_SYNC_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    httpx.RemoteProtocolError,
)

# Default retryable exceptions for async HTTP calls
RETRYABLE_ASYNC_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)

# HTTP status codes that warrant a retry
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}


def _calculate_delay(
    attempt: int,
    base_delay: float,
    exponential_base: float,
    max_delay: float,
    jitter: bool,
) -> float:
    """
    Calculate delay with exponential backoff and optional jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        exponential_base: Multiplier for exponential growth
        max_delay: Maximum delay cap
        jitter: Whether to add random jitter

    Returns:
        Calculated delay in seconds
    """
    delay = base_delay * (exponential_base ** attempt)
    delay = min(delay, max_delay)

    if jitter:
        # Add jitter: random value between 0.5x and 1.5x the delay
        delay = delay * (0.5 + random.random())

    return delay


def _extract_retry_after(response: Union[requests.Response, httpx.Response]) -> Optional[float]:
    """
    Extract Retry-After header value from response.

    Args:
        response: HTTP response object

    Returns:
        Retry delay in seconds, or None if header not present
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            # Could be a date string - ignore for simplicity
            pass
    return None


def _should_retry_status_code(status_code: int) -> bool:
    """Check if the HTTP status code warrants a retry."""
    return status_code in RETRYABLE_STATUS_CODES


def retry_sync(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    retryable_status_codes: Optional[Set[int]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    Decorator for synchronous functions with retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        exponential_base: Multiplier for exponential backoff (delay = base_delay * exponential_base^attempt)
        max_delay: Maximum delay cap in seconds
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exception types to retry on
        retryable_status_codes: Set of HTTP status codes to retry on
        on_retry: Optional callback called on each retry (attempt, exception, delay)

    Example:
        @retry_sync(max_retries=3, base_delay=1.0)
        def call_api():
            response = requests.get("https://api.example.com")
            response.raise_for_status()
            return response.json()
    """
    if retryable_exceptions is None:
        retryable_exceptions = RETRYABLE_SYNC_EXCEPTIONS
    if retryable_status_codes is None:
        retryable_status_codes = RETRYABLE_STATUS_CODES

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Check for Response objects with retryable status codes
                    if isinstance(result, requests.Response):
                        if result.status_code in retryable_status_codes:
                            if attempt < max_retries:
                                # Use Retry-After header if present
                                retry_after = _extract_retry_after(result)
                                delay = retry_after or _calculate_delay(
                                    attempt, base_delay, exponential_base, max_delay, jitter
                                )

                                logger.warning(
                                    f"[RETRY] {func.__name__} returned {result.status_code}, "
                                    f"attempt {attempt + 1}/{max_retries + 1}, waiting {delay:.2f}s"
                                )

                                if on_retry:
                                    on_retry(attempt, None, delay)

                                time.sleep(delay)
                                continue

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = _calculate_delay(
                            attempt, base_delay, exponential_base, max_delay, jitter
                        )

                        logger.warning(
                            f"[RETRY] {func.__name__} raised {type(e).__name__}: {str(e)[:100]}, "
                            f"attempt {attempt + 1}/{max_retries + 1}, waiting {delay:.2f}s"
                        )

                        if on_retry:
                            on_retry(attempt, e, delay)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_retries + 1} attempts: "
                            f"{type(e).__name__}: {str(e)[:200]}"
                        )
                        raise

                except requests.exceptions.HTTPError as e:
                    # Check if it's a retryable HTTP error
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        if status_code in retryable_status_codes and attempt < max_retries:
                            retry_after = _extract_retry_after(e.response)
                            delay = retry_after or _calculate_delay(
                                attempt, base_delay, exponential_base, max_delay, jitter
                            )

                            logger.warning(
                                f"[RETRY] {func.__name__} HTTP {status_code}, "
                                f"attempt {attempt + 1}/{max_retries + 1}, waiting {delay:.2f}s"
                            )

                            if on_retry:
                                on_retry(attempt, e, delay)

                            time.sleep(delay)
                            continue

                    # Non-retryable HTTP error
                    raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    retryable_status_codes: Optional[Set[int]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    Decorator for asynchronous functions with retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        exponential_base: Multiplier for exponential backoff
        max_delay: Maximum delay cap in seconds
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exception types to retry on
        retryable_status_codes: Set of HTTP status codes to retry on
        on_retry: Optional callback called on each retry (attempt, exception, delay)

    Example:
        @retry_async(max_retries=3, base_delay=1.0)
        async def call_api():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com")
                response.raise_for_status()
                return response.json()
    """
    if retryable_exceptions is None:
        retryable_exceptions = RETRYABLE_ASYNC_EXCEPTIONS
    if retryable_status_codes is None:
        retryable_status_codes = RETRYABLE_STATUS_CODES

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    # Check for Response objects with retryable status codes
                    if isinstance(result, httpx.Response):
                        if result.status_code in retryable_status_codes:
                            if attempt < max_retries:
                                retry_after = _extract_retry_after(result)
                                delay = retry_after or _calculate_delay(
                                    attempt, base_delay, exponential_base, max_delay, jitter
                                )

                                logger.warning(
                                    f"[RETRY] {func.__name__} returned {result.status_code}, "
                                    f"attempt {attempt + 1}/{max_retries + 1}, waiting {delay:.2f}s"
                                )

                                if on_retry:
                                    on_retry(attempt, None, delay)

                                await asyncio.sleep(delay)
                                continue

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = _calculate_delay(
                            attempt, base_delay, exponential_base, max_delay, jitter
                        )

                        logger.warning(
                            f"[RETRY] {func.__name__} raised {type(e).__name__}: {str(e)[:100]}, "
                            f"attempt {attempt + 1}/{max_retries + 1}, waiting {delay:.2f}s"
                        )

                        if on_retry:
                            on_retry(attempt, e, delay)

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_retries + 1} attempts: "
                            f"{type(e).__name__}: {str(e)[:200]}"
                        )
                        raise

                except httpx.HTTPStatusError as e:
                    # Check if it's a retryable HTTP error
                    status_code = e.response.status_code
                    if status_code in retryable_status_codes and attempt < max_retries:
                        retry_after = _extract_retry_after(e.response)
                        delay = retry_after or _calculate_delay(
                            attempt, base_delay, exponential_base, max_delay, jitter
                        )

                        logger.warning(
                            f"[RETRY] {func.__name__} HTTP {status_code}, "
                            f"attempt {attempt + 1}/{max_retries + 1}, waiting {delay:.2f}s"
                        )

                        if on_retry:
                            on_retry(attempt, e, delay)

                        await asyncio.sleep(delay)
                        continue

                    # Non-retryable HTTP error
                    raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# Convenience aliases with common configurations

def retry_serp(func: Callable = None):
    """Retry decorator configured for SERP API calls (3 retries, 1s base delay)."""
    decorator = retry_sync(max_retries=3, base_delay=1.0, exponential_base=2.0)
    if func is not None:
        return decorator(func)
    return decorator


def retry_exa(func: Callable = None):
    """Retry decorator configured for Exa API calls (3 retries, 1s base delay)."""
    decorator = retry_sync(max_retries=3, base_delay=1.0, exponential_base=2.0)
    if func is not None:
        return decorator(func)
    return decorator


def retry_image_download(func: Callable = None):
    """Retry decorator configured for image downloads (2 retries, 0.5s base delay)."""
    decorator = retry_sync(max_retries=2, base_delay=0.5, exponential_base=2.0)
    if func is not None:
        return decorator(func)
    return decorator
