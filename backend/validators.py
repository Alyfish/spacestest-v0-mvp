"""
Request validation utilities for the AI Interior Design backend.

Provides validation functions for file uploads, space types, markers,
and other request parameters with clear error messages.
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Set
from fastapi import UploadFile

from errors import APIError, ErrorCode, validation_error


# ============================================================================
# Constants
# ============================================================================

# Maximum file size: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_FILE_SIZE_MB = MAX_FILE_SIZE_BYTES / (1024 * 1024)

# Allowed image MIME types
ALLOWED_IMAGE_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heif",
    "image/heic",
}

# Allowed image file extensions
ALLOWED_IMAGE_EXTENSIONS: Set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
}

# Magic byte signatures for image type detection
_MAGIC_SIGNATURES = [
    (b'\xff\xd8\xff', "image/jpeg"),
    (b'\x89PNG\r\n\x1a\n', "image/png"),
    (b'RIFF', "image/webp"),  # RIFF....WEBP header
]

# Valid space types for the application
VALID_SPACE_TYPES: Set[str] = {
    "bedroom",
    "living_room",
    "kitchen",
    "bathroom",
    "dining_room",
    "home_office",
    "nursery",
    "kids_room",
    "guest_room",
    "studio",
    "loft",
    "entryway",
    "hallway",
    "basement",
    "attic",
    "garage",
    "patio",
    "balcony",
    "outdoor",
    "other",
}

# Valid improvement modes
VALID_IMPROVEMENT_MODES: Set[str] = {
    "iterative",
    "complete_revamp",
    "inspiration",
}

# UUID regex pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


# ============================================================================
# Image Validation
# ============================================================================

async def validate_image_upload(
    file: UploadFile,
    max_size_bytes: int = MAX_FILE_SIZE_BYTES,
) -> bytes:
    """
    Validate an uploaded image file.

    Checks:
    - Content type is an allowed image type
    - File extension matches content type
    - File size is within limits

    Args:
        file: The uploaded file from FastAPI
        max_size_bytes: Maximum allowed file size in bytes

    Returns:
        The file content as bytes

    Raises:
        APIError: If validation fails
    """
    # Read file content first (needed for magic-byte detection and size check)
    content = await file.read()
    file_size = len(content)

    # Detect type from magic bytes (most reliable)
    detected_type = _detect_image_type(content)

    # Accept if EITHER Content-Type header OR magic bytes match an allowed type
    content_type_ok = file.content_type in ALLOWED_IMAGE_TYPES
    magic_bytes_ok = detected_type in ALLOWED_IMAGE_TYPES

    if not content_type_ok and not magic_bytes_ok:
        raise validation_error(
            code=ErrorCode.INVALID_FILE_TYPE,
            message=f"Invalid file type. Content-Type: {file.content_type}, detected: {detected_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
            details={
                "content_type": file.content_type,
                "detected_type": detected_type,
                "allowed_types": list(ALLOWED_IMAGE_TYPES),
            },
        )

    # Check file extension if filename is provided (warning only, not blocking)
    if file.filename:
        ext = _get_file_extension(file.filename)
        if ext and ext.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            # Log warning but don't block — magic bytes are more reliable
            import logging
            logging.getLogger("spaces_ai").warning(
                f"Unexpected file extension '{ext}' but magic bytes indicate {detected_type}"
            )

    # Check file size
    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        max_mb = max_size_bytes / (1024 * 1024)
        raise validation_error(
            code=ErrorCode.FILE_TOO_LARGE,
            message=f"File too large: {size_mb:.1f}MB. Maximum allowed: {max_mb:.0f}MB",
            details={"file_size_bytes": file_size, "max_size_bytes": max_size_bytes},
        )

    # Reset file position for potential re-reading
    await file.seek(0)

    return content


def validate_image_content_type(content_type: Optional[str]) -> None:
    """
    Validate that a content type is an allowed image type.

    Args:
        content_type: The MIME type to validate

    Raises:
        APIError: If validation fails
    """
    if not content_type:
        raise validation_error(
            code=ErrorCode.INVALID_FILE_TYPE,
            message="Content type is required for image uploads",
        )

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise validation_error(
            code=ErrorCode.INVALID_FILE_TYPE,
            message=f"Invalid content type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )


def _detect_image_type(content: bytes) -> Optional[str]:
    """Detect image MIME type from magic bytes."""
    if not content:
        return None
    for signature, mime_type in _MAGIC_SIGNATURES:
        if content[:len(signature)] == signature:
            # Special case: RIFF header needs WEBP check at offset 8
            if signature == b'RIFF' and len(content) >= 12:
                if content[8:12] != b'WEBP':
                    continue
            return mime_type
    # Check for HEIF/HEIC (ftyp box at offset 4)
    if len(content) >= 12 and content[4:8] == b'ftyp':
        brand = content[8:12]
        if brand in (b'heic', b'heix', b'mif1'):
            return "image/heic"
        if brand in (b'hevc', b'hevx'):
            return "image/heif"
    return None


def _get_file_extension(filename: str) -> Optional[str]:
    """Extract file extension from filename."""
    if '.' in filename:
        return '.' + filename.rsplit('.', 1)[-1]
    return None


# ============================================================================
# Space Type Validation
# ============================================================================

def validate_space_type(space_type: str) -> str:
    """
    Validate that a space type is in the allowed list.

    Args:
        space_type: The space type to validate

    Returns:
        The validated space type (lowercase)

    Raises:
        APIError: If validation fails
    """
    normalized = space_type.lower().strip()

    if not normalized:
        raise validation_error(
            code=ErrorCode.INVALID_SPACE_TYPE,
            message="Space type cannot be empty",
        )

    if normalized not in VALID_SPACE_TYPES:
        raise validation_error(
            code=ErrorCode.INVALID_SPACE_TYPE,
            message=f"Invalid space type: '{space_type}'. Valid options: {', '.join(sorted(VALID_SPACE_TYPES))}",
            details={"provided": space_type, "valid_options": sorted(VALID_SPACE_TYPES)},
        )

    return normalized


def validate_improvement_mode(mode: str) -> str:
    """
    Validate that an improvement mode is valid.

    Args:
        mode: The improvement mode to validate

    Returns:
        The validated mode

    Raises:
        APIError: If validation fails
    """
    normalized = mode.lower().strip()

    if normalized not in VALID_IMPROVEMENT_MODES:
        raise validation_error(
            code=ErrorCode.INVALID_REQUEST,
            message=f"Invalid improvement mode: '{mode}'. Valid options: {', '.join(VALID_IMPROVEMENT_MODES)}",
            details={"provided": mode, "valid_options": list(VALID_IMPROVEMENT_MODES)},
        )

    return normalized


# ============================================================================
# Marker Validation
# ============================================================================

def validate_markers(markers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate improvement markers.

    Checks:
    - Position x and y are in range [0, 1]
    - Required fields are present (position, description)

    Args:
        markers: List of marker dictionaries

    Returns:
        The validated markers list

    Raises:
        APIError: If validation fails
    """
    if not isinstance(markers, list):
        raise validation_error(
            code=ErrorCode.INVALID_REQUEST,
            message="Markers must be a list",
        )

    validated_markers = []

    for i, marker in enumerate(markers):
        if not isinstance(marker, dict):
            raise validation_error(
                code=ErrorCode.INVALID_REQUEST,
                message=f"Marker at index {i} must be an object",
            )

        # Check for position
        position = marker.get("position")
        if position is None:
            raise validation_error(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Marker at index {i} is missing required field 'position'",
            )

        # Validate position coordinates
        if isinstance(position, dict):
            x = position.get("x")
            y = position.get("y")
        else:
            raise validation_error(
                code=ErrorCode.INVALID_MARKER_POSITION,
                message=f"Marker at index {i}: 'position' must be an object with 'x' and 'y' fields",
            )

        if x is None or y is None:
            raise validation_error(
                code=ErrorCode.INVALID_MARKER_POSITION,
                message=f"Marker at index {i}: position must have 'x' and 'y' coordinates",
            )

        # Validate coordinate ranges
        try:
            x_val = float(x)
            y_val = float(y)
        except (TypeError, ValueError):
            raise validation_error(
                code=ErrorCode.INVALID_MARKER_POSITION,
                message=f"Marker at index {i}: position coordinates must be numbers",
            )

        if not (0 <= x_val <= 1) or not (0 <= y_val <= 1):
            raise validation_error(
                code=ErrorCode.INVALID_MARKER_POSITION,
                message=f"Marker at index {i}: position coordinates must be in range [0, 1]. Got x={x_val}, y={y_val}",
                details={"index": i, "x": x_val, "y": y_val},
            )

        # Check for description
        description = marker.get("description")
        if not description or not isinstance(description, str) or not description.strip():
            raise validation_error(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Marker at index {i} is missing required field 'description'",
            )

        validated_markers.append(marker)

    return validated_markers


# ============================================================================
# ID Validation
# ============================================================================

def validate_project_id(project_id: str) -> str:
    """
    Validate that a project ID is a valid UUID format.

    Args:
        project_id: The project ID to validate

    Returns:
        The validated project ID

    Raises:
        APIError: If validation fails
    """
    if not project_id:
        raise validation_error(
            code=ErrorCode.INVALID_PROJECT_ID,
            message="Project ID cannot be empty",
        )

    if not UUID_PATTERN.match(project_id):
        raise validation_error(
            code=ErrorCode.INVALID_PROJECT_ID,
            message=f"Invalid project ID format: '{project_id}'. Must be a valid UUID",
            details={"provided": project_id},
        )

    return project_id


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """
    Validate that a value is a valid UUID format.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        The validated value

    Raises:
        APIError: If validation fails
    """
    if not value:
        raise validation_error(
            code=ErrorCode.INVALID_REQUEST,
            message=f"{field_name} cannot be empty",
        )

    if not UUID_PATTERN.match(value):
        raise validation_error(
            code=ErrorCode.INVALID_REQUEST,
            message=f"Invalid {field_name} format: '{value}'. Must be a valid UUID",
        )

    return value


# ============================================================================
# General Validation Helpers
# ============================================================================

def validate_required_field(
    value: Any,
    field_name: str,
    allow_empty: bool = False,
) -> Any:
    """
    Validate that a required field is present and optionally non-empty.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        allow_empty: Whether to allow empty strings/lists

    Returns:
        The validated value

    Raises:
        APIError: If validation fails
    """
    if value is None:
        raise validation_error(
            code=ErrorCode.MISSING_REQUIRED_FIELD,
            message=f"Missing required field: '{field_name}'",
        )

    if not allow_empty:
        if isinstance(value, str) and not value.strip():
            raise validation_error(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Field '{field_name}' cannot be empty",
            )
        if isinstance(value, (list, dict)) and len(value) == 0:
            raise validation_error(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Field '{field_name}' cannot be empty",
            )

    return value


def validate_list_length(
    value: List[Any],
    field_name: str,
    min_length: int = 0,
    max_length: Optional[int] = None,
) -> List[Any]:
    """
    Validate that a list has an acceptable length.

    Args:
        value: The list to validate
        field_name: Name of the field for error messages
        min_length: Minimum allowed length
        max_length: Maximum allowed length (None for no limit)

    Returns:
        The validated list

    Raises:
        APIError: If validation fails
    """
    if not isinstance(value, list):
        raise validation_error(
            code=ErrorCode.INVALID_REQUEST,
            message=f"Field '{field_name}' must be a list",
        )

    if len(value) < min_length:
        raise validation_error(
            code=ErrorCode.INVALID_REQUEST,
            message=f"Field '{field_name}' must have at least {min_length} items",
            details={"current_length": len(value), "min_length": min_length},
        )

    if max_length is not None and len(value) > max_length:
        raise validation_error(
            code=ErrorCode.INVALID_REQUEST,
            message=f"Field '{field_name}' cannot have more than {max_length} items",
            details={"current_length": len(value), "max_length": max_length},
        )

    return value
