"""
Asset Upload Constants - File validation rules and limits.

@module domains.assets.constants
@version 1.0.0

WS-05: Centralized file upload security constants.
Magic bytes validation prevents MIME type spoofing attacks
(e.g., uploading a PHP file with .jpg extension).
"""

# ==========================================
# MIME Type Whitelist
# ==========================================

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/pdf",
}

# ==========================================
# Magic Bytes (File Signatures)
# ==========================================
# Used to verify actual file content matches claimed MIME type.
# Prevents attacks like: malicious.php renamed to image.jpg

MAGIC_BYTES = {
    "image/jpeg": [
        b"\xff\xd8\xff",       # JPEG/JFIF
    ],
    "image/png": [
        b"\x89PNG\r\n\x1a\n",  # PNG
    ],
    "image/gif": [
        b"GIF87a",              # GIF87a
        b"GIF89a",              # GIF89a
    ],
    "image/webp": [
        b"RIFF",                # WebP (starts with RIFF, then has WEBP at offset 8)
    ],
    # SVG is text-based, validated separately via content inspection
    # PDF uses %PDF magic bytes
    "application/pdf": [
        b"%PDF",
    ],
}

# How many bytes to read for magic byte validation
MAGIC_BYTES_READ_SIZE = 16

# ==========================================
# File Size Limits by Tier
# ==========================================

MAX_FILE_SIZE_BY_TIER = {
    "t1": 5 * 1024 * 1024,     # 5MB for free tier
    "t2": 10 * 1024 * 1024,    # 10MB for Starter
    "t3": 20 * 1024 * 1024,    # 20MB for Pro
}

DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB fallback

# ==========================================
# SVG Security
# ==========================================

# SVG elements that are dangerous and must be stripped
SVG_DANGEROUS_TAGS = {
    "script",
    "foreignObject",
    "set",
    "animate",
    "animateMotion",
    "animateTransform",
}

# SVG attributes that can contain executable content
SVG_DANGEROUS_ATTRS_PREFIXES = (
    "on",            # onclick, onload, onerror, etc.
)

SVG_DANGEROUS_ATTRS = {
    "xlink:href",    # Can contain javascript: URIs
    "href",          # Can contain javascript: URIs (in <a>, <use>)
}

# URL schemes allowed in SVG href attributes
SVG_ALLOWED_SCHEMES = {"http", "https", "data"}

# ==========================================
# SSRF Protection
# ==========================================

# Maximum number of HTTP redirects to follow
MAX_REDIRECT_HOPS = 3

# Maximum URL length
MAX_URL_LENGTH = 2048
