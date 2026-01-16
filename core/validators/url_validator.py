"""
URL Validator (v3.26 - Layer Compliance)

Provides URL validation functions for SSRF protection.
Moved from api/user/export.py to core layer for proper DDD compliance.

@module core.validators.url_validator
"""

from urllib.parse import urlparse

# Allowed domains for external URL fetching (SSRF protection)
ALLOWED_URL_DOMAINS = {
    "supabase.co",
    "supabase.com",
    "fal.media",
    "fal.ai",
    "r2.cloudflarestorage.com",
    "s3.amazonaws.com",
}


def is_allowed_url(url: str) -> bool:
    """
    Check if URL is from an allowed domain (SSRF protection).

    This function validates URLs against a whitelist of trusted domains
    to prevent Server-Side Request Forgery (SSRF) attacks.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is from an allowed domain, False otherwise

    Examples:
        >>> is_allowed_url("https://example.supabase.co/file.png")
        True
        >>> is_allowed_url("https://evil.com/malware.exe")
        False
        >>> is_allowed_url("")
        False
    """
    if not url or not url.startswith("http"):
        return False

    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        for allowed in ALLOWED_URL_DOMAINS:
            if host == allowed or host.endswith(f".{allowed}"):
                return True

        return False
    except Exception:
        return False
