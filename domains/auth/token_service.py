"""
TokenService — JWT Access Token and opaque Refresh Token management.

Access Token: HS256 JWT, 15-minute expiry.
Refresh Token: Opaque UUID, SHA-256 hashed before storage.
Supports dual-key rotation for zero-downtime secret changes.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt

from .constants import (
    ACCESS_TOKEN_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ACCESS_TOKEN_TYPE,
    JWT_SECRET_MIN_LENGTH,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from .exceptions import TokenExpiredException, TokenInvalidException
from .value_objects import AccessTokenPayload


class TokenService:
    """
    Domain service for token operations.

    Responsibilities:
    - Create and verify HS256 JWT access tokens
    - Generate opaque refresh tokens + SHA-256 hashes
    - Support dual-key rotation (try new key, fallback to old key)
    - Validate secret key strength at startup
    """

    def __init__(
        self,
        jwt_secret: str,
        jwt_secret_old: Optional[str] = None,
        access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    ) -> None:
        """
        Initialize TokenService.

        Args:
            jwt_secret: Current JWT signing secret (≥43 chars).
            jwt_secret_old: Previous JWT secret for dual-key rotation (optional).
            access_token_expire_minutes: Access token lifetime in minutes.
            refresh_token_expire_days: Refresh token lifetime in days.
        """
        self._jwt_secret = jwt_secret
        self._jwt_secret_old = jwt_secret_old
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    # -------------------------------------------------------------------
    # Startup Validation
    # -------------------------------------------------------------------

    @staticmethod
    def validate_secrets_at_startup(
        jwt_secret: str,
        jwt_secret_old: Optional[str] = None,
    ) -> None:
        """
        Validate JWT secret strength at application startup.

        Raises ValueError if secrets are too short (< 43 characters).

        Args:
            jwt_secret: Current JWT secret.
            jwt_secret_old: Old JWT secret (optional, only during rotation).

        Raises:
            ValueError: If any secret is too short.
        """
        if not jwt_secret:
            raise ValueError("AUTH_JWT_SECRET is required but not set")

        if len(jwt_secret) < JWT_SECRET_MIN_LENGTH:
            raise ValueError(
                f"AUTH_JWT_SECRET too short: {len(jwt_secret)} chars, "
                f"minimum {JWT_SECRET_MIN_LENGTH} required "
                f"(256-bit key as base64)"
            )

        if jwt_secret_old and len(jwt_secret_old) < JWT_SECRET_MIN_LENGTH:
            raise ValueError(
                f"AUTH_JWT_SECRET_OLD too short: {len(jwt_secret_old)} chars, "
                f"minimum {JWT_SECRET_MIN_LENGTH} required"
            )

    # -------------------------------------------------------------------
    # Access Token (JWT)
    # -------------------------------------------------------------------

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: str,
        tier: str,
    ) -> str:
        """
        Create a signed JWT access token.

        Args:
            user_id: User's UUID (becomes 'sub' claim).
            email: User's email.
            role: User's role (e.g., "user", "admin").
            tier: User's subscription tier (e.g., "t1", "t2").

        Returns:
            Encoded JWT string.
        """
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "tier": tier,
            "type": ACCESS_TOKEN_TYPE,
            "iat": now,
            "exp": now + (self._access_token_expire_minutes * 60),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm=ACCESS_TOKEN_ALGORITHM)

    def verify_access_token(self, token: str) -> AccessTokenPayload:
        """
        Verify and decode a JWT access token.

        Supports dual-key rotation: tries current secret first,
        then falls back to old secret during rotation period.

        Args:
            token: Encoded JWT string.

        Returns:
            Decoded AccessTokenPayload value object.

        Raises:
            TokenExpiredException: If token has expired.
            TokenInvalidException: If token is invalid or signature fails.
        """
        # Try current secret
        payload = self._decode_jwt(token, self._jwt_secret)

        # Fallback to old secret during rotation
        if payload is None and self._jwt_secret_old:
            payload = self._decode_jwt(token, self._jwt_secret_old)

        if payload is None:
            raise TokenInvalidException()

        # Validate token type
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise TokenInvalidException(message="Invalid token type")

        try:
            return AccessTokenPayload(
                sub=UUID(payload["sub"]),
                email=payload["email"],
                role=payload["role"],
                tier=payload["tier"],
                token_type=payload["type"],
                iat=payload["iat"],
                exp=payload["exp"],
            )
        except (KeyError, ValueError) as e:
            raise TokenInvalidException(
                message=f"Malformed token payload: {e}"
            )

    def _decode_jwt(
        self,
        token: str,
        secret: str,
    ) -> Optional[dict]:
        """
        Attempt to decode a JWT with the given secret.

        Returns None if decoding fails (instead of raising),
        to allow fallback to alternative secrets.
        """
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=[ACCESS_TOKEN_ALGORITHM],
                options={"require": ["sub", "email", "role", "tier", "type", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredException()
        except (jwt.InvalidTokenError, jwt.DecodeError):
            return None

    # -------------------------------------------------------------------
    # Refresh Token (opaque UUID + SHA-256)
    # -------------------------------------------------------------------

    @staticmethod
    def create_refresh_token() -> tuple[str, str]:
        """
        Generate a new opaque refresh token.

        Returns:
            Tuple of (plaintext_token, sha256_hash).
            - plaintext_token: Sent to client (stored in httpOnly cookie).
            - sha256_hash: Stored in auth_sessions.refresh_token_hash.
        """
        plaintext = secrets.token_urlsafe(48)  # 384-bit entropy
        token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        return plaintext, token_hash

    @staticmethod
    def hash_refresh_token(plaintext: str) -> str:
        """
        Hash a plaintext refresh token for lookup.

        Args:
            plaintext: The plaintext refresh token from the client.

        Returns:
            SHA-256 hex digest for database comparison.
        """
        return hashlib.sha256(plaintext.encode()).hexdigest()

    # -------------------------------------------------------------------
    # Email Verification / Password Reset Tokens
    # -------------------------------------------------------------------

    @staticmethod
    def create_secure_token() -> tuple[str, str]:
        """
        Generate a secure token for email verification or password reset.

        Returns:
            Tuple of (plaintext_token, sha256_hash).
            - plaintext_token: Included in the email link.
            - sha256_hash: Stored in auth_users table.
        """
        plaintext = secrets.token_urlsafe(32)  # 256-bit entropy
        token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        return plaintext, token_hash

    @staticmethod
    def hash_token(plaintext: str) -> str:
        """Hash a token for comparison against stored hash."""
        return hashlib.sha256(plaintext.encode()).hexdigest()
