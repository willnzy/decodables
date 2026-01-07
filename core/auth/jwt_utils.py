"""
JWT Utilities - Generic JWT handling for authentication.

@module core.auth.jwt_utils
@version 1.0.0
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class JWTError(Exception):
    """Base exception for JWT-related errors."""
    pass


class JWTExpiredError(JWTError):
    """Token has expired."""
    pass


class JWTInvalidError(JWTError):
    """Token is invalid."""
    pass


@dataclass
class JWTConfig:
    """
    JWT configuration.

    Attributes:
        public_key: PEM-encoded public key for verification
        algorithms: Allowed algorithms (default: RS256)
        verify_audience: Whether to verify audience claim
        verify_expiration: Whether to verify expiration
        issuer: Expected issuer (optional)
        audience: Expected audience (optional)
    """
    public_key: Optional[str] = None
    algorithms: List[str] = None
    verify_audience: bool = False
    verify_expiration: bool = True
    issuer: Optional[str] = None
    audience: Optional[str] = None

    def __post_init__(self):
        if self.algorithms is None:
            self.algorithms = ["RS256"]

    @property
    def is_secure(self) -> bool:
        """Check if secure verification is enabled."""
        return bool(self.public_key)


def decode_jwt(
    token: str,
    config: JWTConfig = None,
    fallback_insecure: bool = False
) -> Dict[str, Any]:
    """
    Decode and verify JWT token.

    Args:
        token: JWT token string
        config: JWT configuration
        fallback_insecure: Allow insecure decoding if no key configured

    Returns:
        Decoded payload

    Raises:
        JWTExpiredError: If token has expired
        JWTInvalidError: If token is invalid
        JWTError: For other JWT-related errors
    """
    try:
        import jwt
    except ImportError:
        raise JWTError("PyJWT package not installed")

    cfg = config or JWTConfig()

    # Secure mode: verify signature
    if cfg.public_key:
        try:
            options = {
                "verify_aud": cfg.verify_audience,
                "verify_exp": cfg.verify_expiration,
            }
            payload = jwt.decode(
                token,
                cfg.public_key,
                algorithms=cfg.algorithms,
                options=options,
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise JWTExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise JWTInvalidError(f"Invalid token: {e}")

    # Insecure mode: decode without verification (development only)
    if fallback_insecure:
        logger.warning("[Auth] Decoding JWT without verification - UNSAFE")
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            raise JWTInvalidError(f"Invalid token format: {e}")

    raise JWTError("No public key configured and insecure fallback disabled")


def extract_user_id(payload: Dict[str, Any], claim: str = "sub") -> Optional[str]:
    """
    Extract user ID from JWT payload.

    Args:
        payload: Decoded JWT payload
        claim: Claim name containing user ID

    Returns:
        User ID or None
    """
    return payload.get(claim)


def extract_claims(
    payload: Dict[str, Any],
    claims: List[str]
) -> Dict[str, Any]:
    """
    Extract specific claims from JWT payload.

    Args:
        payload: Decoded JWT payload
        claims: List of claim names to extract

    Returns:
        Dict of extracted claims
    """
    return {claim: payload.get(claim) for claim in claims if claim in payload}
