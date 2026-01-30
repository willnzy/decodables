"""
Validation Utilities - Input validation and sanitization helpers.

@module core.utils.validation
@version 2.0.0

Changes in v2.0.0 (2026-01-10):
- MASTER-P2-046: Added JSON Schema validation for canvas_data
- Integrated core.schemas module for structural validation
- Enhanced validate_canvas_data with dual-layer validation:
  1. JSON Schema validation (structure)
  2. XSS/injection validation (security)
- Maintained backward compatibility (security validation always runs)
"""

import re
from typing import Optional, List, Any, Dict
from urllib.parse import urlparse
from fastapi import HTTPException


# ==========================================
# UUID Validation (WS4: centralized)
# ==========================================

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """
    Validate a UUID string. Raises HTTPException(400) if invalid.

    Args:
        value: String to validate
        field_name: Human-readable field name for error message

    Returns:
        The validated UUID string

    Raises:
        HTTPException: 400 if format is invalid
    """
    if not UUID_PATTERN.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format")
    return value


# ==========================================
# Query / Search Sanitization (WS4)
# ==========================================

# Pagination limits
MAX_LIMIT = 100
MAX_SEARCH_LENGTH = 200

# PostgREST special characters that need escaping in search queries
_POSTGREST_SPECIAL_CHARS = re.compile(r"[%_\\]")


def sanitize_postgrest_query(query: str) -> str:
    """
    Sanitize a search query for safe use in PostgREST ILIKE patterns.

    Escapes % and _ which are SQL LIKE wildcards, and backslashes.
    This prevents users from injecting custom wildcard patterns.

    Args:
        query: Raw search string from user input

    Returns:
        Sanitized string safe for PostgREST queries
    """
    if not query:
        return query
    # Truncate to max length
    query = query[:MAX_SEARCH_LENGTH]
    # Escape special chars: \ → \\, % → \%, _ → \_
    return _POSTGREST_SPECIAL_CHARS.sub(lambda m: "\\" + m.group(0), query)


def clamp_limit(limit: int, max_limit: int = MAX_LIMIT) -> int:
    """Clamp a limit value to the allowed range [1, max_limit]."""
    return max(1, min(limit, max_limit))


# ==========================================
# URL Validation
# ==========================================

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
    max_depth: int = MAX_CANVAS_DEPTH,
    use_json_schema: bool = True
) -> tuple[bool, Optional[str]]:
    """
    Validate canvas_data with dual-layer validation (v2.0.0).

    Layer 1: JSON Schema validation (structural)
    Layer 2: XSS/injection validation (security)

    Checks:
    - JSON Schema compliance (if enabled and available)
    - Maximum nesting depth
    - No script tags or event handlers in string values
    - No excessively long strings

    Args:
        data: Canvas data dict to validate
        max_depth: Maximum allowed nesting depth
        use_json_schema: Whether to use JSON Schema validation (default True)

    Returns:
        Tuple of (is_valid, error_message)

    Note:
        - JSON Schema validation is optional (graceful degradation)
        - XSS/injection validation always runs (security critical)
    """
    if data is None:
        return True, None

    if not isinstance(data, dict):
        return False, "canvas_data must be a dictionary"

    # Layer 1: JSON Schema validation (optional, structural)
    if use_json_schema:
        try:
            from core.schemas import validate_canvas_data_schema, JSONSCHEMA_AVAILABLE

            if JSONSCHEMA_AVAILABLE:
                is_valid, schema_error = validate_canvas_data_schema(data)
                if not is_valid:
                    return False, f"Schema validation failed: {schema_error}"
        except ImportError:
            # Graceful degradation: schemas module not available
            pass
        except Exception as e:
            # Log but don't fail on schema validation errors
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"JSON Schema validation error (non-critical): {e}")

    # Layer 2: XSS/injection validation (mandatory, security)
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


# ==========================================
# Prompt Validation (for AI generation)
# ==========================================

# Maximum prompt length (characters)
MAX_PROMPT_LENGTH = 2000

# Maximum total prompts in a batch
MAX_PROMPTS_PER_REQUEST = 10


def validate_prompt(prompt: str, max_length: int = MAX_PROMPT_LENGTH) -> tuple[bool, Optional[str]]:
    """
    Validate a single prompt for AI generation.

    Checks:
    - Length limits
    - No dangerous injection patterns
    - No null bytes or control characters

    Args:
        prompt: Prompt string to validate
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(prompt, str):
        return False, "Prompt must be a string"

    if not prompt.strip():
        return False, "Prompt cannot be empty"

    if len(prompt) > max_length:
        return False, f"Prompt too long (max {max_length} characters)"

    # Check for null bytes and control characters (except newline/tab)
    if any(ord(c) < 32 and c not in '\n\t\r' for c in prompt):
        return False, "Prompt contains invalid control characters"

    # Check for potential injection patterns
    if _contains_injection_pattern(prompt):
        return False, "Prompt contains invalid patterns"

    return True, None


def validate_prompts(
    prompts: List[str],
    max_prompts: int = MAX_PROMPTS_PER_REQUEST,
    max_prompt_length: int = MAX_PROMPT_LENGTH
) -> tuple[bool, Optional[str]]:
    """
    Validate a list of prompts for AI generation.

    Args:
        prompts: List of prompt strings
        max_prompts: Maximum number of prompts allowed
        max_prompt_length: Maximum length per prompt

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not prompts:
        return False, "At least one prompt is required"

    if not isinstance(prompts, list):
        return False, "Prompts must be a list"

    if len(prompts) > max_prompts:
        return False, f"Maximum {max_prompts} prompts allowed per request"

    for i, prompt in enumerate(prompts):
        is_valid, error = validate_prompt(prompt, max_prompt_length)
        if not is_valid:
            return False, f"Prompt {i + 1}: {error}"

    return True, None


def _contains_injection_pattern(value: str) -> bool:
    """
    Check for prompt injection patterns.

    Args:
        value: String to check

    Returns:
        True if injection pattern found
    """
    if not value:
        return False

    lower_value = value.lower()

    # System prompt injection patterns
    injection_patterns = [
        "ignore previous",
        "ignore all previous",
        "disregard previous",
        "forget previous",
        "new instructions:",
        "system prompt:",
        "you are now",
        "act as if",
        "pretend you are",
        "jailbreak",
        "dan mode",
        "developer mode",
    ]

    for pattern in injection_patterns:
        if pattern in lower_value:
            return True

    return False


# ==========================================
# Reference Image URL Validation (SSRF Prevention)
# ==========================================

# Allowed hosts for reference images (AI generation)
ALLOWED_REFERENCE_IMAGE_HOSTS = {
    # Supabase storage
    "supabase.co",
    # Common CDNs
    "cdn.makedecodables.com",
    "storage.googleapis.com",
    "cloudflare-ipfs.com",
    # FAL.ai CDN (for generated images as reference)
    "fal.media",
    "v3.fal.media",
    # User may paste from common image hosts
    "imgur.com",
    "i.imgur.com",
}

# Maximum URL length
MAX_REFERENCE_URL_LENGTH = 2048


def validate_reference_image_url(url: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate reference image URL to prevent SSRF attacks.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if url is None:
        return True, None

    if not isinstance(url, str):
        return False, "Reference image URL must be a string"

    # Empty string is OK (no reference)
    if not url.strip():
        return True, None

    # Check for base64 encoded image (allowed)
    if url.startswith("data:image/"):
        # Validate base64 image format
        if not _is_valid_base64_image(url):
            return False, "Invalid base64 image format"
        return True, None

    # URL validation
    if len(url) > MAX_REFERENCE_URL_LENGTH:
        return False, f"URL too long (max {MAX_REFERENCE_URL_LENGTH} characters)"

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

    # Extract host
    host = parsed.netloc.lower()

    # Remove port if present
    if ":" in host:
        host = host.split(":")[0]

    # Block localhost and private IPs
    if _is_private_host(host):
        return False, "URL host not allowed"

    # Check if host matches allowed list (including subdomains)
    host_allowed = False
    for allowed_host in ALLOWED_REFERENCE_IMAGE_HOSTS:
        if host == allowed_host or host.endswith("." + allowed_host):
            host_allowed = True
            break

    if not host_allowed:
        return False, f"Reference image host not in allowed list. Allowed: {', '.join(sorted(ALLOWED_REFERENCE_IMAGE_HOSTS))}"

    return True, None


def _is_valid_base64_image(data_url: str) -> bool:
    """
    Validate base64 image data URL format.

    Args:
        data_url: Data URL to validate

    Returns:
        True if valid base64 image
    """
    import base64

    # Expected format: data:image/png;base64,xxxxx
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]

    try:
        # Extract mime type and data
        if not data_url.startswith("data:"):
            return False

        header, data = data_url.split(",", 1)

        # Check mime type
        mime_part = header.replace("data:", "").replace(";base64", "")
        if mime_part not in allowed_types:
            return False

        # Validate base64 (just check it's valid, don't decode full image)
        # Limit check to first 100 chars to avoid DoS
        base64.b64decode(data[:100] + "==")  # Add padding for partial decode
        return True

    except Exception:
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
