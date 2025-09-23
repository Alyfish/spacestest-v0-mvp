"""
Centralized logging configuration for the AI Interior Design backend
"""

import json
import logging
import sys
import time
from datetime import datetime
from functools import wraps
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "project_id"):
            log_data["project_id"] = record.project_id
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        if hasattr(record, "api_call"):
            log_data["api_call"] = record.api_call
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
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
    """Decorator to log API calls with timing"""

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
                        "duration": duration,
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
                        "duration": duration,
                        "status": "error",
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


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
