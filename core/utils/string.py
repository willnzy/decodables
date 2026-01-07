"""
String Utilities - String manipulation helpers.

@module core.utils.string
@version 1.0.0
"""

import re
import unicodedata
from typing import Optional


def slugify(text: str, max_length: int = 100) -> str:
    """
    Convert text to URL-friendly slug.

    - Converts to lowercase
    - Replaces spaces with hyphens
    - Removes non-alphanumeric characters
    - Collapses multiple hyphens

    Args:
        text: Text to slugify
        max_length: Maximum length of slug

    Returns:
        URL-friendly slug
    """
    if not text:
        return ""

    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Convert to lowercase
    text = text.lower()

    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)

    # Remove non-alphanumeric characters (except hyphens)
    text = re.sub(r'[^a-z0-9-]', '', text)

    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)

    # Strip leading/trailing hyphens
    text = text.strip('-')

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')

    return text


def truncate(text: str, length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length.

    Args:
        text: Text to truncate
        length: Maximum length (including suffix)
        suffix: Suffix to append if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= length:
        return text

    # Account for suffix length
    cut_length = length - len(suffix)
    if cut_length <= 0:
        return text[:length]

    # Try to cut at word boundary
    truncated = text[:cut_length]
    last_space = truncated.rfind(' ')

    if last_space > cut_length * 0.7:  # Only if space is reasonably close
        truncated = truncated[:last_space]

    return truncated + suffix


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for safe file system use.

    Removes/replaces characters that are problematic on various file systems.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Safe filename
    """
    if not filename:
        return "unnamed"

    # Characters not allowed in filenames on Windows
    unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'

    # Replace unsafe characters with underscore
    safe = re.sub(unsafe_chars, '_', filename)

    # Remove leading/trailing dots and spaces
    safe = safe.strip('. ')

    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)

    # Ensure not empty
    if not safe:
        safe = "unnamed"

    # Truncate if too long (preserve extension if present)
    if len(safe) > max_length:
        name, ext = split_filename(safe)
        max_name_len = max_length - len(ext) - 1 if ext else max_length
        safe = name[:max_name_len] + ('.' + ext if ext else '')

    return safe


def split_filename(filename: str) -> tuple:
    """
    Split filename into name and extension.

    Args:
        filename: Filename to split

    Returns:
        Tuple of (name, extension) - extension without dot
    """
    if not filename:
        return ("", "")

    if '.' not in filename:
        return (filename, "")

    # Handle hidden files (like .gitignore)
    if filename.startswith('.') and filename.count('.') == 1:
        return (filename, "")

    parts = filename.rsplit('.', 1)
    return (parts[0], parts[1] if len(parts) > 1 else "")


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.

    Example: "user@example.com" -> "u***@example.com"

    Args:
        email: Email address to mask

    Returns:
        Masked email
    """
    if not email or '@' not in email:
        return email

    local, domain = email.rsplit('@', 1)

    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***' + local[-1]

    return f"{masked_local}@{domain}"
