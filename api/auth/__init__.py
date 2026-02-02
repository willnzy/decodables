"""
Auth API Module - Public authentication endpoints.

Endpoints:
- POST /api/v2/auth/register    - User registration
- POST /api/v2/auth/login       - User login
- POST /api/v2/auth/refresh     - Token refresh
- POST /api/v2/auth/logout      - Logout current session
- POST /api/v2/auth/logout-all  - Logout all sessions
- POST /api/v2/auth/verify-email - Email verification
- POST /api/v2/auth/resend-verification - Resend verification email
- POST /api/v2/auth/forgot-password - Request password reset
- POST /api/v2/auth/reset-password  - Reset password with token
- POST /api/v2/auth/change-password - Change password (authenticated)
- GET  /api/v2/auth/sessions       - List active sessions (authenticated)
- DELETE /api/v2/auth/sessions/{id} - Revoke a session (authenticated)
- DELETE /api/v2/auth/account       - Delete account (authenticated)
"""

from .router import router as auth_router

__all__ = ["auth_router"]
