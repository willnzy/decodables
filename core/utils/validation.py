"""
Validation Utilities - Input validation and sanitization helpers.

@module core.utils.validation
@version 1.0.0
"""

import re
from typing import Optional, List, Any, Dict
from urllib.parse import urlparse


# Allowed URL schemes for thumbnail URLs
ALLOWED_URL_SCHEMES = {"https"}

# Allowed hosts for thumbnail URLs (trusted CDNs)
ALLOWED_THUMBNAIL_HOSTS = {
    # Supabase storage
    "supabase.co",
    # Common CDNs that might be used
    "cdn.makedecodables.com",
    "storage.googleapis.com",
    "cloudflare-ipfs.com",
    # Add your actual CDN domains here
}

# Maximum depth for canvas_data nested objects
MAX_CANVAS_DEPTH = 20

# Maximum size for canvas_data string values (to prevent memory exhaustion)
MAX_STRING_VALUE_LENGTH = 1_000_000  # 1MB


def validate_thumbnail_url(url: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate thumbnail URL to prevent SSRF attacks.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if url is None:
        return True, None

    if not isinstance(url, str):
        return False, "URL must be a string"

    if not url.strip():
        return True, None  # Empty string is OK (clear thumbnail)

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Check scheme
    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        return False, f"URL scheme must be one of: {', '.join(ALLOWED_URL_SCHEMES)}"

    # Check for empty host
    if not parsed.netloc:
        return False, "URL must have a valid host"

    # Extract host (handle subdomains)
    host = parsed.netloc.lower()

    # Remove port if present
    if ":" in host:
        host = host.split(":")[0]

    # Check if host matches allowed list (including subdomains)
    host_allowed = False
    for allowed_host in ALLOWED_THUMBNAIL_HOSTS:
        if host == allowed_host or host.endswith("." + allowed_host):
            host_allowed = True
            break

    if not host_allowed:
        return False, "URL host not in allowed list"

    # Block localhost and private IPs
    if _is_private_host(host):
        return False, "URL host not allowed"

    return True, None


def _is_private_host(host: str) -> bool:
    """
    Check if host is localhost or private IP range.

    Args:
        host: Hostname or IP address

    Returns:
        True if host is private/local
    """
    # Localhost variations
    localhost_patterns = {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
    }

    if host in localhost_patterns:
        return True

    # Check for localhost subdomains
    if host.endswith(".localhost"):
        return True

    # Private IP patterns (simplified check)
    private_patterns = [
        r"^10\.",  # 10.0.0.0/8
        r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",  # 172.16.0.0/12
        r"^192\.168\.",  # 192.168.0.0/16
        r"^169\.254\.",  # Link-local
        r"^127\.",  # Loopback
    ]

    for pattern in private_patterns:
        if re.match(pattern, host):
            return True

    return False


def validate_canvas_data(
    data: Optional[Dict[str, Any]],
    max_depth: int = MAX_CANVAS_DEPTH
) -> tuple[bool, Optional[str]]:
    """
    Validate canvas_data to prevent XSS and injection attacks.

    Checks:
    - Maximum nesting depth
    - No script tags or event handlers in string values
    - No excessively long strings

    Args:
        data: Canvas data dict to validate
        max_depth: Maximum allowed nesting depth

    Returns:
        Tuple of (is_valid, error_message)
    """
    if data is None:
        return True, None

    if not isinstance(data, dict):
        return False, "canvas_data must be a dictionary"

    # Check depth and content recursively
    try:
        _validate_canvas_recursive(data, current_depth=0, max_depth=max_depth)
        return True, None
    except ValueError as e:
        return False, str(e)


def _validate_canvas_recursive(
    obj: Any,
    current_depth: int,
    max_depth: int,
    path: str = "root"
) -> None:
    """
    Recursively validate canvas data object.

    Raises:
        ValueError: If validation fails
    """
    if current_depth > max_depth:
        raise ValueError(f"Maximum nesting depth ({max_depth}) exceeded at {path}")

    if isinstance(obj, dict):
        for key, value in obj.items():
            # Validate key
            if not isinstance(key, str):
                raise ValueError(f"Dictionary key must be string at {path}")

            # Check for dangerous patterns in keys
            if _contains_dangerous_pattern(key):
                raise ValueError(f"Potentially dangerous key at {path}.{key}")

            _validate_canvas_recursive(
                value,
                current_depth + 1,
                max_depth,
                f"{path}.{key}"
            )

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate_canvas_recursive(
                item,
                current_depth + 1,
                max_depth,
                f"{path}[{i}]"
            )

    elif isinstance(obj, str):
        # Check string length
        if len(obj) > MAX_STRING_VALUE_LENGTH:
            raise ValueError(
                f"String value too long at {path} "
                f"(max {MAX_STRING_VALUE_LENGTH} chars)"
            )

        # Check for dangerous content in strings
        if _contains_dangerous_pattern(obj):
            raise ValueError(f"Potentially dangerous content at {path}")

    # Numbers, booleans, None are safe


def _contains_dangerous_pattern(value: str) -> bool:
    """
    Check if string contains potentially dangerous XSS patterns.

    Args:
        value: String to check

    Returns:
        True if dangerous pattern found
    """
    if not value:
        return False

    # Normalize for comparison
    lower_value = value.lower()

    # Dangerous patterns (case-insensitive)
    dangerous_patterns = [
        "<script",
        "javascript:",
        "vbscript:",
        "data:text/html",
        "onerror=",
        "onload=",
        "onclick=",
        "onmouseover=",
        "onfocus=",
        "onblur=",
        "onchange=",
        "onsubmit=",
        "eval(",
        "expression(",
        "url(javascript:",
    ]

    for pattern in dangerous_patterns:
        if pattern in lower_value:
            return True

    return False


def validate_title(title: Optional[str], max_length: int = 500) -> tuple[bool, Optional[str]]:
    """
    Validate project title.

    Args:
        title: Title to validate
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if title is None:
        return True, None

    if not isinstance(title, str):
        return False, "Title must be a string"

    # Check length
    if len(title) > max_length:
        return False, f"Title too long (max {max_length} characters)"

    # Check for dangerous content
    if _contains_dangerous_pattern(title):
        return False, "Title contains invalid characters"

    return True, None
