"""
Core Auth Layer - Framework level authentication abstractions.

This module provides:
- IAuthProvider: Abstract interface for authentication providers
- JWTConfig: JWT configuration dataclass
- decode_jwt: Generic JWT decoding utility
- AuthContext: Request-scoped authentication context

@package core.auth
@version 1.0.0

Design Principles:
- NO business logic here (no user creation, no profile fetching)
- All code should be reusable in any FastAPI project
- Business-specific auth logic goes to shared/auth/ or dependencies.py
"""

from .interface import IAuthProvider, AuthResult
from .jwt_utils import JWTConfig, decode_jwt, JWTError
from .context import AuthContext, get_auth_context

__all__ = [
    # Interface
    'IAuthProvider',
    'AuthResult',
    # JWT Utils
    'JWTConfig',
    'decode_jwt',
    'JWTError',
    # Context
    'AuthContext',
    'get_auth_context',
]
