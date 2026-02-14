"""
Centralized logging configuration for the AI Interior Design backend.

Provides structured JSON logging, request correlation via request_id,
and timing decorators for API call monitoring.
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

# Context variable for request correlation
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set a request ID in context. Generates one if not provided."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs with request correlation."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request_id from context if available
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        # Add extra fields if present
        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id
        if hasattr(record, "project_id"):
            log_data["project_id"] = record.project_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        if hasattr(record, "api_call"):
            log_data["api_call"] = record.api_call
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        if hasattr(record, "error_id"):
            log_data["error_id"] = record.error_id
        if hasattr(record, "service"):
            log_data["service"] = record.service
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up structured logging for the application"""

    # Create logger
    logger = logging.getLogger("spaces_ai")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Use structured formatter for production, simple for development
    import os

    if os.getenv("ENVIRONMENT") == "production":
        formatter = StructuredFormatter()
    else:
        # Simpler format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s"
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def log_api_call(api_name: str):
    """Decorator to log synchronous API calls with timing."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("spaces_ai")
            start_time = time.time()

            # Extract project_id if available
            project_id = None
            if args and len(args) > 1:
                if isinstance(args[1], str) and len(args[1]) == 36:  # UUID format
                    project_id = args[1]

            try:
                logger.info(
                    f"Starting {api_name} API call",
                    extra={
                        "api_call": api_name,
                        "project_id": project_id,
                    },
                )

                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000

                logger.info(
                    f"Completed {api_name} API call successfully",
                    extra={
                        "api_call": api_name,
                        "project_id": project_id,
                        "duration_ms": duration,
                        "status": "success",
                    },
                )

                return result

            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {api_name} API call: {str(e)}",
                    extra={
                        "api_call": api_name,
                        "project_id": project_id,
                        "duration_ms": duration,
                        "status": "error",
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


# Type variable for generic async decorator
F = TypeVar('F', bound=Callable[..., Any])


def log_api_call_async(api_name: str, service: Optional[str] = None):
    """
    Decorator to log asynchronous API calls with timing and structured output.

    Logs:
    - duration_ms: Time taken in milliseconds
    - status: 'success' or 'error'
    - error_type: Exception class name on failure
    - request_id: Correlation ID from context
    - service: Optional service identifier (e.g., 'serp', 'exa', 'gemini')

    Args:
        api_name: Name of the API operation for logging
        service: Optional service name for categorization

    Example:
        @log_api_call_async("search_products", service="serp")
        async def search_products(self, query: str) -> Dict:
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger("spaces_ai")
            start_time = time.time()

            # Extract project_id from kwargs or positional args
            project_id = kwargs.get("project_id")
            if not project_id and args and len(args) > 1:
                if isinstance(args[1], str) and len(args[1]) == 36:
                    project_id = args[1]

            extra_base = {
                "api_call": api_name,
                "project_id": project_id,
            }
            if service:
                extra_base["service"] = service

            try:
                logger.debug(
                    f"Starting {api_name}",
                    extra=extra_base,
                )

                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"Completed {api_name} in {duration_ms:.0f}ms",
                    extra={
                        **extra_base,
                        "duration_ms": duration_ms,
                        "status": "success",
                    },
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_type = _classify_error_type(e)

                logger.error(
                    f"Failed {api_name} after {duration_ms:.0f}ms: {str(e)[:200]}",
                    extra={
                        **extra_base,
                        "duration_ms": duration_ms,
                        "status": "error",
                        "error_type": error_type,
                    },
                    exc_info=True,
                )
                raise

        return wrapper  # type: ignore
    return decorator


def _classify_error_type(exc: Exception) -> str:
    """
    Classify an exception into a high-level error type category.

    This helps with error aggregation and alerting in production.
    """
    exc_name = type(exc).__name__

    # Network/Connection errors
    if exc_name in ("ConnectionError", "ConnectError", "ConnectTimeout", "ReadTimeout", "Timeout"):
        return "network_error"

    # HTTP errors
    if exc_name in ("HTTPError", "HTTPStatusError"):
        return "http_error"

    # Rate limiting
    if "rate" in str(exc).lower() or "429" in str(exc):
        return "rate_limited"

    # API-specific errors
    if "api" in exc_name.lower():
        return "api_error"

    # Validation errors
    if exc_name in ("ValidationError", "ValueError", "TypeError"):
        return "validation_error"

    # File/IO errors
    if exc_name in ("FileNotFoundError", "IOError", "PermissionError"):
        return "io_error"

    # Default to the exception class name
    return exc_name


def log_project_status_change(project_id: str, old_status: str, new_status: str):
    """Log project status transitions"""
    logger = logging.getLogger("spaces_ai")
    logger.info(
        f"Project status changed: {old_status} -> {new_status}",
        extra={
            "project_id": project_id,
            "status": new_status,
            "extra_data": {
                "old_status": old_status,
                "transition": f"{old_status} -> {new_status}",
            },
        },
    )


def log_external_api_call(
    service: str,
    endpoint: str,
    duration_ms: float,
    success: bool,
    response_size: Optional[int] = None,
):
    """Log external API calls (OpenAI, Exa, etc.)"""
    logger = logging.getLogger("spaces_ai")

    extra_data = {
        "api_call": f"{service}_{endpoint}",
        "duration": duration_ms,
        "status": "success" if success else "error",
        "service": service,
        "endpoint": endpoint,
    }

    if response_size:
        extra_data["response_size_bytes"] = response_size

    if success:
        logger.info(
            f"External API call to {service} {endpoint} completed", extra=extra_data
        )
    else:
        logger.error(
            f"External API call to {service} {endpoint} failed", extra=extra_data
        )


def log_user_action(action: str, project_id: Optional[str] = None, **context):
    """Log user actions for analytics"""
    logger = logging.getLogger("spaces_ai")
    logger.info(
        f"User action: {action}",
        extra={"project_id": project_id, "extra_data": {"action": action, **context}},
    )


# Initialize logger
logger = setup_logging()


# ============================================================================
# Request ID Middleware Helper
# ============================================================================

async def request_id_middleware(request, call_next):
    """
    FastAPI middleware to set up request ID for correlation.

    Usage in main.py:
        from logger_config import request_id_middleware
        app.middleware("http")(request_id_middleware)

    Or use add_request_id_middleware(app) helper.
    """
    # Get request ID from header or generate new one
    incoming_request_id = request.headers.get("X-Request-ID")
    request_id = set_request_id(incoming_request_id)

    # Process request
    response = await call_next(request)

    # Add request ID to response headers for tracing
    response.headers["X-Request-ID"] = request_id

    return response


def add_request_id_middleware(app):
    """
    Add request ID middleware to a FastAPI app.

    Args:
        app: FastAPI application instance
    """
    from starlette.middleware.base import BaseHTTPMiddleware

    async def middleware_dispatch(request, call_next):
        incoming_request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(incoming_request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=middleware_dispatch)
