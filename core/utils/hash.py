"""
Hash Utilities - Hashing and token generation.

@module core.utils.hash
@version 1.0.0
"""

import hashlib
import secrets
from typing import Union


def md5_hash(content: Union[str, bytes]) -> str:
    """
    Generate MD5 hash of content.

    Note: MD5 is not cryptographically secure.
    Use for checksums and cache keys, not security.

    Args:
        content: String or bytes to hash

    Returns:
        Hex-encoded MD5 hash
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.md5(content).hexdigest()


def sha256_hash(content: Union[str, bytes]) -> str:
    """
    Generate SHA256 hash of content.

    Args:
        content: String or bytes to hash

    Returns:
        Hex-encoded SHA256 hash
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Length of token in characters (hex)

    Returns:
        Random hex token
    """
    # Each byte = 2 hex chars
    return secrets.token_hex(length // 2)


def generate_urlsafe_token(length: int = 32) -> str:
    """
    Generate a URL-safe random token.

    Args:
        length: Approximate length of token

    Returns:
        URL-safe base64-encoded token
    """
    return secrets.token_urlsafe(length)


def hash_for_cache(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key hash from arguments.

    Args:
        prefix: Cache key prefix
        *args: Positional arguments to include in hash
        **kwargs: Keyword arguments to include in hash

    Returns:
        Cache key in format "prefix:hash"
    """
    import json
    content = json.dumps({
        "args": args,
        "kwargs": kwargs,
    }, sort_keys=True)
    hash_part = sha256_hash(content)[:16]
    return f"{prefix}:{hash_part}"
