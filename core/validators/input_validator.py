"""
Input Validator - Common input validation and sanitization utilities.

@module core.validators.input_validator
@version 1.0.0

WS-08: Centralized input validation to prevent injection attacks.

Provides:
1. validate_uuid() — UUID format validation
2. escape_like_wildcards() — ILIKE/LIKE wildcard escaping
3. validate_pagination() — Pagination parameter bounds checking
4. sanitize_tag_name() — Tag name XSS prevention
"""

import re
import uuid
from typing import Tuple


# Pre-compiled patterns
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# XSS-dangerous patterns in text fields
_XSS_PATTERN = re.compile(r"<[^>]*script|javascript:|on\w+=", re.IGNORECASE)


def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Validate that a string is a valid UUID format.

    Args:
        value: String to validate
        field_name: Field name for error messages

    Returns:
        Validated UUID string (lowercased)

    Raises:
        ValueError: If not a valid UUID
    """
    if not value or not isinstance(value, str):
        raise ValueError(f"Invalid {field_name}: must be a non-empty string")

    value = value.strip().lower()

    if not _UUID_PATTERN.match(value):
        raise ValueError(f"Invalid {field_name}: must be a valid UUID format")

    return value


def escape_like_wildcards(value: str) -> str:
    """
    Escape SQL LIKE/ILIKE wildcard characters in a search term.

    Prevents wildcard injection where user input like "%" or "_"
    would match unintended patterns.

    Escapes: % → \\%, _ → \\_, \\ → \\\\

    Args:
        value: Raw search term from user

    Returns:
        Escaped search term safe for LIKE/ILIKE queries

    Example:
        >>> escape_like_wildcards("100%")
        '100\\\\%'
        >>> escape_like_wildcards("user_name")
        'user\\\\_name'
    """
    if not value:
        return value

    # Order matters: escape backslash first, then wildcards
    value = value.replace("\\", "\\\\")
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")

    return value


def validate_pagination(
    offset: int = 0,
    limit: int = 20,
    max_limit: int = 100,
) -> Tuple[int, int]:
    """
    Validate and normalize pagination parameters.

    Args:
        offset: Requested offset (must be >= 0)
        limit: Requested limit (1 <= limit <= max_limit)
        max_limit: Maximum allowed limit

    Returns:
        Tuple of (validated_offset, validated_limit)

    Raises:
        ValueError: If parameters are out of bounds
    """
    if offset < 0:
        raise ValueError("offset must be >= 0")

    if limit < 1:
        raise ValueError("limit must be >= 1")

    if limit > max_limit:
        raise ValueError(f"limit must be <= {max_limit}")

    return offset, limit


def sanitize_tag_name(name: str, max_length: int = 50) -> str:
    """
    Sanitize a tag name, preventing XSS and enforcing length.

    Args:
        name: Raw tag name
        max_length: Maximum allowed length

    Returns:
        Sanitized tag name

    Raises:
        ValueError: If name is empty, too long, or contains XSS patterns
    """
    if not name or not isinstance(name, str):
        raise ValueError("Tag name cannot be empty")

    name = name.strip()

    if not name:
        raise ValueError("Tag name cannot be empty")

    if len(name) > max_length:
        raise ValueError(f"Tag name cannot exceed {max_length} characters")

    # Check for XSS patterns
    if _XSS_PATTERN.search(name):
        raise ValueError("Tag name contains invalid characters")

    # Strip HTML tags as extra safety
    clean = re.sub(r"<[^>]*>", "", name).strip()
    if not clean:
        raise ValueError("Tag name cannot be empty after sanitization")

    return clean
