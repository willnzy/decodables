"""
Auth domain value objects.

Immutable objects representing authentication concepts with built-in validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from .constants import (
    PASSWORD_MIN_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_REQUIRE_DIGIT,
    PASSWORD_REQUIRE_LOWERCASE,
    PASSWORD_REQUIRE_UPPERCASE,
    COMMON_PASSWORDS,
    VALID_OAUTH_PROVIDERS,
)


# ---------------------------------------------------------------------------
# Email Value Object
# ---------------------------------------------------------------------------

# RFC 5322 simplified pattern — covers 99%+ of real-world emails
# Requires at least one dot in domain with 2+ char TLD
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*"
    r"\.[a-zA-Z]{2,}$"
)


@dataclass(frozen=True)
class Email:
    """
    Validated, normalized email address.

    Always stored as lowercase, stripped of whitespace.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Email cannot be empty")

        # Normalize: strip + lowercase
        normalized = self.value.strip().lower()
        # frozen=True 不允许直接赋值，使用 object.__setattr__
        object.__setattr__(self, "value", normalized)

        if len(normalized) > 254:
            raise ValueError("Email exceeds maximum length of 254 characters")

        if not _EMAIL_PATTERN.match(normalized):
            raise ValueError(f"Invalid email format: {normalized}")

    @property
    def domain(self) -> str:
        """Extract domain part of email."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part (before @) of email."""
        return self.value.split("@")[0]

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Password Value Object (for validation only, never stores plaintext)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PasswordStrength:
    """
    Result of password strength validation.

    This object does NOT store the password itself — only the validation result.
    """

    is_valid: bool
    errors: tuple[str, ...]

    @classmethod
    def validate(cls, password: str) -> PasswordStrength:
        """
        Validate password strength against configured rules.

        Args:
            password: Plaintext password to validate.

        Returns:
            PasswordStrength with validation result and any error messages.
        """
        errors: list[str] = []

        if len(password) < PASSWORD_MIN_LENGTH:
            errors.append(
                f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
            )

        if len(password) > PASSWORD_MAX_LENGTH:
            errors.append(
                f"Password must not exceed {PASSWORD_MAX_LENGTH} characters"
            )

        if PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if password.lower() in COMMON_PASSWORDS:
            errors.append("This password is too common. Please choose a stronger one")

        return cls(is_valid=len(errors) == 0, errors=tuple(errors))


# ---------------------------------------------------------------------------
# Token Payload Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AccessTokenPayload:
    """
    Decoded access token payload.

    Represents the claims extracted from a verified JWT.
    """

    sub: UUID           # user_id
    email: str
    role: str           # "user" | "admin"
    tier: str           # "t1" | "t2" | "t3" | "t4"
    token_type: str     # "access"
    iat: int            # issued at (unix timestamp)
    exp: int            # expires at (unix timestamp)

    def __post_init__(self) -> None:
        if self.token_type != "access":
            raise ValueError(f"Expected token type 'access', got '{self.token_type}'")


# ---------------------------------------------------------------------------
# OAuth Provider Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OAuthProvider:
    """Validated OAuth provider identifier."""

    value: str

    def __post_init__(self) -> None:
        if self.value not in VALID_OAUTH_PROVIDERS:
            raise ValueError(
                f"Invalid OAuth provider: {self.value}. "
                f"Valid providers: {', '.join(sorted(VALID_OAUTH_PROVIDERS))}"
            )

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Device Info Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeviceInfo:
    """
    Device information extracted from request context.

    Used for session identification and user-facing device display.
    """

    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    device_name: Optional[str] = None

    @classmethod
    def from_request(
        cls,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> DeviceInfo:
        """
        Create DeviceInfo from HTTP request data.

        Parses user_agent to extract a human-readable device name.
        """
        device_name = cls._parse_device_name(user_agent) if user_agent else None
        return cls(
            user_agent=user_agent,
            ip_address=ip_address,
            device_name=device_name,
        )

    @staticmethod
    def _parse_device_name(user_agent: str) -> str:
        """
        Extract a human-readable device name from User-Agent string.

        Examples:
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)..." → "Mac OS X - Chrome"
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0...)..." → "iPhone - Safari"
        """
        ua_lower = user_agent.lower()

        # Detect OS
        if "iphone" in ua_lower:
            os_name = "iPhone"
        elif "ipad" in ua_lower:
            os_name = "iPad"
        elif "android" in ua_lower:
            os_name = "Android"
        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            os_name = "Mac"
        elif "windows" in ua_lower:
            os_name = "Windows"
        elif "linux" in ua_lower:
            os_name = "Linux"
        else:
            os_name = "Unknown Device"

        # Detect browser
        if "edg/" in ua_lower or "edge/" in ua_lower:
            browser = "Edge"
        elif "chrome/" in ua_lower and "safari/" in ua_lower:
            browser = "Chrome"
        elif "firefox/" in ua_lower:
            browser = "Firefox"
        elif "safari/" in ua_lower:
            browser = "Safari"
        else:
            browser = "Unknown Browser"

        return f"{os_name} - {browser}"
