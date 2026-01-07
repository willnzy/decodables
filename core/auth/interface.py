"""
Auth Provider Interface - Abstract base for authentication implementations.

@module core.auth.interface
@version 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class AuthResult:
    """
    Result of authentication attempt.

    Attributes:
        success: Whether authentication was successful
        user_id: Unique user identifier (if successful)
        payload: Full JWT payload or provider-specific data
        error: Error message (if failed)
    """
    success: bool
    user_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if authentication was successful."""
        return self.success and self.user_id is not None


class IAuthProvider(ABC):
    """
    Abstract interface for authentication providers.

    Implementations can support different auth methods:
    - JWT-based (Clerk, Auth0, Firebase)
    - API Key
    - OAuth
    - Custom tokens
    """

    @abstractmethod
    def authenticate(self, credentials: str) -> AuthResult:
        """
        Authenticate using provided credentials.

        Args:
            credentials: Authentication credentials (token, API key, etc.)

        Returns:
            AuthResult with authentication status and user info
        """
        pass

    @abstractmethod
    def validate_token(self, token: str) -> bool:
        """
        Validate token without full authentication.

        Args:
            token: Token to validate

        Returns:
            True if token is valid
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of this auth provider."""
        pass
