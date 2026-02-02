"""
Auth domain constants.

Centralized configuration for authentication rules, token expiration,
lockout thresholds, and password policies.
"""

# ---------------------------------------------------------------------------
# Token Configuration
# ---------------------------------------------------------------------------

# Access Token (JWT HS256)
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
ACCESS_TOKEN_TYPE: str = "access"
ACCESS_TOKEN_ALGORITHM: str = "HS256"

# Refresh Token (opaque UUID, SHA-256 hashed in DB)
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

# Proactive refresh: trigger refresh when access token expires within this window
ACCESS_TOKEN_REFRESH_WINDOW_SECONDS: int = 60

# JWT minimum secret key length (256-bit = 32 bytes → base64 ≈ 43 chars)
JWT_SECRET_MIN_LENGTH: int = 43

# JWT issuer and audience claims (for token validation)
JWT_ISSUER: str = "make-decodables"
JWT_AUDIENCE: str = "make-decodables-api"

# ---------------------------------------------------------------------------
# Password Rules
# ---------------------------------------------------------------------------

PASSWORD_MIN_LENGTH: int = 8
PASSWORD_MAX_LENGTH: int = 128
PASSWORD_REQUIRE_UPPERCASE: bool = True
PASSWORD_REQUIRE_LOWERCASE: bool = True
PASSWORD_REQUIRE_DIGIT: bool = True

# Common passwords blacklist (top 100 most common)
COMMON_PASSWORDS: frozenset = frozenset({
    "password", "12345678", "123456789", "1234567890", "qwerty123",
    "password1", "iloveyou", "sunshine1", "princess1", "football1",
    "charlie1", "access14", "shadow12", "master12", "michael1",
    "qwerty12", "abc12345", "trustno1", "baseball", "dragon12",
    "letmein1", "monkey12", "starwars", "whatever", "computer",
    "superman", "asdfghjk", "zxcvbnm1", "passw0rd", "p@ssw0rd",
    "1q2w3e4r", "qwertyui", "admin123", "welcome1", "password123",
    "12345678a", "1234qwer", "change_me", "test1234", "abcd1234",
})

# ---------------------------------------------------------------------------
# Account Lockout
# ---------------------------------------------------------------------------

# Number of failed login attempts before locking
MAX_FAILED_LOGIN_ATTEMPTS: int = 5

# Lockout duration in minutes
LOCKOUT_DURATION_MINUTES: int = 30

# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

# Maximum concurrent active sessions per user
MAX_ACTIVE_SESSIONS: int = 10

# Concurrent grace period for token rotation (seconds)
# If a revoked token is reused within this window, treat as concurrent request
TOKEN_ROTATION_GRACE_PERIOD_SECONDS: int = 2

# ---------------------------------------------------------------------------
# OTP (One-Time Password) Configuration
# ---------------------------------------------------------------------------

# OTP code length (6-digit numeric)
OTP_LENGTH: int = 6

# OTP expiry in minutes
OTP_EXPIRE_MINUTES: int = 10

# Maximum OTP verification attempts before invalidation
OTP_MAX_ATTEMPTS: int = 5

# Cooldown between OTP sends (seconds) — prevents spam
OTP_COOLDOWN_SECONDS: int = 60

# Valid OTP purposes (must match CHECK constraint in auth_users table)
OTP_PURPOSE_REGISTER: str = "register"
OTP_PURPOSE_CHANGE_PASSWORD: str = "change_password"
OTP_PURPOSE_DELETE_ACCOUNT: str = "delete_account"
OTP_PURPOSE_FORGOT_PASSWORD: str = "forgot_password"

VALID_OTP_PURPOSES: frozenset = frozenset({
    OTP_PURPOSE_REGISTER,
    OTP_PURPOSE_CHANGE_PASSWORD,
    OTP_PURPOSE_DELETE_ACCOUNT,
    OTP_PURPOSE_FORGOT_PASSWORD,
})

# ---------------------------------------------------------------------------
# Account Restore (Soft-Delete Recovery)
# ---------------------------------------------------------------------------

# Days within which a soft-deleted account can be restored
ACCOUNT_RESTORE_WINDOW_DAYS: int = 30

# ---------------------------------------------------------------------------
# Rate Limiting (requests per time window)
# ---------------------------------------------------------------------------

RATE_LIMIT_LOGIN: str = "10/minute"
RATE_LIMIT_REGISTER: str = "5/hour"
RATE_LIMIT_REFRESH: str = "30/minute"
RATE_LIMIT_FORGOT_PASSWORD: str = "3/hour"
RATE_LIMIT_SEND_OTP: str = "5/hour"

# ---------------------------------------------------------------------------
# Session Revocation Reasons
# ---------------------------------------------------------------------------

REVOKE_REASON_LOGOUT: str = "logout"
REVOKE_REASON_ROTATION: str = "rotation"
REVOKE_REASON_SECURITY: str = "security"
REVOKE_REASON_ADMIN: str = "admin"
REVOKE_REASON_ACCOUNT_DELETED: str = "account_deleted"
REVOKE_REASON_SESSION_LIMIT: str = "session_limit_exceeded"

VALID_REVOKE_REASONS: frozenset = frozenset({
    REVOKE_REASON_LOGOUT,
    REVOKE_REASON_ROTATION,
    REVOKE_REASON_SECURITY,
    REVOKE_REASON_ADMIN,
    REVOKE_REASON_ACCOUNT_DELETED,
    REVOKE_REASON_SESSION_LIMIT,
})

# ---------------------------------------------------------------------------
# OAuth Providers
# ---------------------------------------------------------------------------

OAUTH_PROVIDER_GOOGLE: str = "google"
OAUTH_PROVIDER_GITHUB: str = "github"
OAUTH_PROVIDER_APPLE: str = "apple"

VALID_OAUTH_PROVIDERS: frozenset = frozenset({
    OAUTH_PROVIDER_GOOGLE,
    OAUTH_PROVIDER_GITHUB,
    OAUTH_PROVIDER_APPLE,
})
