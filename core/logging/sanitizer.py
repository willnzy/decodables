"""
Sensitive Data Sanitizer - PII masking for logs and error reports.

@module core.logging.sanitizer
@version 1.0.0

WS-07: Centralized PII sanitization layer.

Provides:
1. SensitiveDataFilter — logging.Filter that masks PII in log messages
2. mask_email() — Mask email addresses (u***@***.com)
3. mask_user_id() — Mask user IDs to last 4 chars
4. sanitize_dict() — Recursively sanitize dictionary values
"""

import re
import logging
from typing import Any, Dict, Optional


# ==========================================
# Masking Functions
# ==========================================

# Pre-compiled regex patterns
_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)
_PHONE_PATTERN = re.compile(
    r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
_TOKEN_PATTERN = re.compile(
    r"\b(sk-[a-zA-Z0-9]{20,}|whsec_[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9._-]{20,})\b"
)

# Sensitive dictionary keys (case-insensitive matching)
_SENSITIVE_KEYS = frozenset({
    "password", "secret", "token", "api_key", "apikey",
    "authorization", "credit_card", "card_number", "cvv",
    "ssn", "social_security",
})


def mask_email(email: str) -> str:
    """
    Mask an email address for safe logging.

    Examples:
        john.doe@example.com → j***@***.com
        a@b.co → a***@***.co

    Args:
        email: Email address string

    Returns:
        Masked email string
    """
    if not email or "@" not in email:
        return email

    local, domain = email.rsplit("@", 1)
    parts = domain.rsplit(".", 1)
    tld = parts[-1] if len(parts) > 1 else ""

    masked_local = local[0] + "***" if local else "***"
    masked_domain = "***." + tld if tld else "***"

    return f"{masked_local}@{masked_domain}"


def mask_user_id(user_id: str) -> str:
    """
    Mask a user ID, keeping only last 4 characters.

    Examples:
        user_2abc3def4ghi → user_...4ghi
        short → short (no masking if <= 8 chars)

    Args:
        user_id: User ID string

    Returns:
        Masked user ID
    """
    if not user_id or len(user_id) <= 8:
        return user_id

    # Keep prefix (user_) and last 4 chars
    if user_id.startswith("user_"):
        return f"user_...{user_id[-4:]}"

    return f"...{user_id[-4:]}"


def mask_phone(phone: str) -> str:
    """
    Mask a phone number, keeping last 4 digits.

    Examples:
        +1-234-567-8901 → ***-8901
        (234) 567-8901 → ***-8901

    Args:
        phone: Phone number string

    Returns:
        Masked phone string
    """
    if not phone:
        return phone

    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 4:
        return f"***-{digits[-4:]}"
    return "***"


def sanitize_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 5) -> Dict[str, Any]:
    """
    Recursively sanitize dictionary values, masking sensitive fields.

    Args:
        data: Dictionary to sanitize
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        Sanitized dictionary copy
    """
    if depth >= max_depth:
        return data

    result = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Check if key is sensitive
        if key_lower in _SENSITIVE_KEYS:
            result[key] = "[REDACTED]"
        elif key_lower in ("email", "user_email", "invited_email"):
            result[key] = mask_email(str(value)) if value else value
        elif key_lower in ("user_id", "owner_id", "reporter_id"):
            result[key] = mask_user_id(str(value)) if value else value
        elif key_lower in ("phone", "phone_number"):
            result[key] = mask_phone(str(value)) if value else value
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, depth + 1, max_depth)
        else:
            result[key] = value

    return result


def _mask_emails_in_text(text: str) -> str:
    """Replace email addresses in a text string with masked versions."""
    def _replace(match):
        return mask_email(match.group(0))
    return _EMAIL_PATTERN.sub(_replace, text)


def _mask_tokens_in_text(text: str) -> str:
    """Replace tokens/API keys in a text string with [REDACTED]."""
    return _TOKEN_PATTERN.sub("[REDACTED]", text)


def _mask_phones_in_text(text: str) -> str:
    """Replace phone numbers in a text string with masked versions."""
    def _replace(match):
        return mask_phone(match.group(0))
    return _PHONE_PATTERN.sub(_replace, text)


# ==========================================
# Logging Filter
# ==========================================

class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that masks PII in log messages.

    Masks:
    - Email addresses → j***@***.com
    - API tokens/keys → [REDACTED]
    - Phone numbers → ***-1234

    Usage:
        logger = logging.getLogger()
        logger.addFilter(SensitiveDataFilter())

    Or attach to a handler:
        handler.addFilter(SensitiveDataFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Process log record, masking sensitive data.

        Always returns True (never filters out records).
        """
        # Sanitize the log message
        if record.msg and isinstance(record.msg, str):
            record.msg = _mask_emails_in_text(record.msg)
            record.msg = _mask_tokens_in_text(record.msg)
            record.msg = _mask_phones_in_text(record.msg)

        # Sanitize args if they contain strings
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _mask_emails_in_text(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _mask_emails_in_text(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )

        return True
