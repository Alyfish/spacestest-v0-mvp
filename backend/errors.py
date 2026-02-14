"""
Production-grade error taxonomy for the AI Interior Design backend.

Provides standardized error codes, custom exception classes, and
consistent error response formatting for clean client communication.
"""

from enum import Enum
from typing import Optional, Dict, Any


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""

    # Validation errors (400)
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_SPACE_TYPE = "INVALID_SPACE_TYPE"
    INVALID_MARKER_POSITION = "INVALID_MARKER_POSITION"
    INVALID_PROJECT_ID = "INVALID_PROJECT_ID"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_REQUEST = "INVALID_REQUEST"

    # Resource errors (404)
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"

    # External API errors (502/503)
    SERP_API_ERROR = "SERP_API_ERROR"
    EXA_API_ERROR = "EXA_API_ERROR"
    GEMINI_API_ERROR = "GEMINI_API_ERROR"
    CLIP_ERROR = "CLIP_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"

    # Rate limiting (429)
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    IMAGE_PROCESSING_ERROR = "IMAGE_PROCESSING_ERROR"
    GENERATION_ERROR = "GENERATION_ERROR"

    # Authentication errors (401)
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Authorization errors (403)
    FORBIDDEN = "FORBIDDEN"


class ErrorCategory(str, Enum):
    """Categories for grouping error types."""
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    EXTERNAL_API = "external_api"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"


# Mapping of error codes to their categories
ERROR_CATEGORIES: Dict[ErrorCode, ErrorCategory] = {
    ErrorCode.INVALID_FILE_TYPE: ErrorCategory.VALIDATION,
    ErrorCode.FILE_TOO_LARGE: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_SPACE_TYPE: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_MARKER_POSITION: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_PROJECT_ID: ErrorCategory.VALIDATION,
    ErrorCode.MISSING_REQUIRED_FIELD: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_REQUEST: ErrorCategory.VALIDATION,
    ErrorCode.PROJECT_NOT_FOUND: ErrorCategory.NOT_FOUND,
    ErrorCode.IMAGE_NOT_FOUND: ErrorCategory.NOT_FOUND,
    ErrorCode.JOB_NOT_FOUND: ErrorCategory.NOT_FOUND,
    ErrorCode.SERP_API_ERROR: ErrorCategory.EXTERNAL_API,
    ErrorCode.EXA_API_ERROR: ErrorCategory.EXTERNAL_API,
    ErrorCode.GEMINI_API_ERROR: ErrorCategory.EXTERNAL_API,
    ErrorCode.CLIP_ERROR: ErrorCategory.EXTERNAL_API,
    ErrorCode.EXTERNAL_API_ERROR: ErrorCategory.EXTERNAL_API,
    ErrorCode.RATE_LIMITED: ErrorCategory.RATE_LIMIT,
    ErrorCode.INTERNAL_ERROR: ErrorCategory.INTERNAL,
    ErrorCode.IMAGE_PROCESSING_ERROR: ErrorCategory.INTERNAL,
    ErrorCode.GENERATION_ERROR: ErrorCategory.INTERNAL,
    ErrorCode.UNAUTHORIZED: ErrorCategory.AUTHENTICATION,
    ErrorCode.TOKEN_EXPIRED: ErrorCategory.AUTHENTICATION,
    ErrorCode.INVALID_TOKEN: ErrorCategory.AUTHENTICATION,
    ErrorCode.FORBIDDEN: ErrorCategory.AUTHORIZATION,
}


class APIError(Exception):
    """
    Custom exception for API errors with structured response formatting.

    Attributes:
        code: The ErrorCode enum value
        message: Human-readable error message
        status_code: HTTP status code to return
        error_id: Optional unique identifier for error correlation
        details: Optional additional error details
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        error_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.error_id = error_id
        self.details = details
        super().__init__(self.message)

    @property
    def category(self) -> ErrorCategory:
        """Get the error category for this error code."""
        return ERROR_CATEGORIES.get(self.code, ErrorCategory.INTERNAL)

    def to_response(self) -> Dict[str, Any]:
        """
        Convert the error to a standardized JSON response format.

        Returns:
            Dict with 'error' key containing code, message, category, and optional error_id
        """
        error_body: Dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "category": self.category.value,
        }

        if self.error_id:
            error_body["error_id"] = self.error_id

        if self.details:
            error_body["details"] = self.details

        return {"error": error_body}


# Convenience factory functions for common errors

def validation_error(
    code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> APIError:
    """Create a validation error (400)."""
    return APIError(code=code, message=message, status_code=400, details=details)


def not_found_error(
    code: ErrorCode,
    message: str,
) -> APIError:
    """Create a not found error (404)."""
    return APIError(code=code, message=message, status_code=404)


def external_api_error(
    code: ErrorCode,
    message: str,
    error_id: Optional[str] = None,
) -> APIError:
    """Create an external API error (502)."""
    return APIError(code=code, message=message, status_code=502, error_id=error_id)


def rate_limit_error(
    message: str = "Rate limit exceeded. Please try again later.",
    retry_after: Optional[int] = None,
) -> APIError:
    """Create a rate limit error (429)."""
    details = {"retry_after_seconds": retry_after} if retry_after else None
    return APIError(
        code=ErrorCode.RATE_LIMITED,
        message=message,
        status_code=429,
        details=details,
    )


def internal_error(
    message: str = "An internal error occurred",
    error_id: Optional[str] = None,
) -> APIError:
    """Create an internal error (500)."""
    return APIError(
        code=ErrorCode.INTERNAL_ERROR,
        message=message,
        status_code=500,
        error_id=error_id,
    )


def unauthorized_error(
    message: str = "Authentication required",
    code: ErrorCode = ErrorCode.UNAUTHORIZED,
) -> APIError:
    """Create an authentication error (401)."""
    return APIError(code=code, message=message, status_code=401)


def forbidden_error(
    message: str = "Access denied",
) -> APIError:
    """Create an authorization error (403)."""
    return APIError(code=ErrorCode.FORBIDDEN, message=message, status_code=403)
