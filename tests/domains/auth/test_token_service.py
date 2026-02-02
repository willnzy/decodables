"""
Tests for TokenService — JWT access tokens, refresh tokens, and secure tokens.

Covers:
- Access token creation and verification
- Dual-key rotation support
- Token expiration
- Malformed/invalid token handling
- Refresh token generation and hashing
- Secure token (verification/reset) generation
- Startup secret validation
"""

import hashlib
import time
from uuid import UUID, uuid4

import jwt
import pytest

from domains.auth.constants import (
    ACCESS_TOKEN_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ACCESS_TOKEN_TYPE,
    JWT_SECRET_MIN_LENGTH,
)
from domains.auth.exceptions import TokenExpiredException, TokenInvalidException
from domains.auth.token_service import TokenService
from domains.auth.value_objects import AccessTokenPayload

from .conftest import TEST_JWT_SECRET, TEST_JWT_SECRET_OLD, TEST_USER_ID, TEST_EMAIL


class TestCreateAccessToken:
    """Tests for create_access_token()."""

    def test_creates_valid_jwt(self, token_service: TokenService):
        token = token_service.create_access_token(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            role="user",
            tier="t1",
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_expected_claims(self, token_service: TokenService):
        token = token_service.create_access_token(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            role="admin",
            tier="t3",
        )
        # Decode without verification to inspect claims
        payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[ACCESS_TOKEN_ALGORITHM])
        assert payload["sub"] == str(TEST_USER_ID)
        assert payload["email"] == TEST_EMAIL
        assert payload["role"] == "admin"
        assert payload["tier"] == "t3"
        assert payload["type"] == ACCESS_TOKEN_TYPE
        assert "iat" in payload
        assert "exp" in payload

    def test_token_expiry_is_correct(self, token_service: TokenService):
        token = token_service.create_access_token(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            role="user",
            tier="t1",
        )
        payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[ACCESS_TOKEN_ALGORITHM])
        expected_exp = payload["iat"] + (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        assert payload["exp"] == expected_exp


class TestVerifyAccessToken:
    """Tests for verify_access_token()."""

    def test_verify_valid_token(self, token_service: TokenService):
        token = token_service.create_access_token(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            role="user",
            tier="t2",
        )
        result = token_service.verify_access_token(token)
        assert isinstance(result, AccessTokenPayload)
        assert result.sub == TEST_USER_ID
        assert result.email == TEST_EMAIL
        assert result.role == "user"
        assert result.tier == "t2"
        assert result.token_type == ACCESS_TOKEN_TYPE

    def test_verify_expired_token_raises(self):
        """Expired token should raise TokenExpiredException."""
        service = TokenService(
            jwt_secret=TEST_JWT_SECRET,
            access_token_expire_minutes=0,  # Expire immediately
        )
        # Create token that's already expired
        payload = {
            "sub": str(TEST_USER_ID),
            "email": TEST_EMAIL,
            "role": "user",
            "tier": "t1",
            "type": ACCESS_TOKEN_TYPE,
            "iat": int(time.time()) - 120,
            "exp": int(time.time()) - 60,
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=ACCESS_TOKEN_ALGORITHM)
        with pytest.raises(TokenExpiredException):
            service.verify_access_token(token)

    def test_verify_invalid_signature_raises(self, token_service: TokenService):
        """Token signed with wrong key should raise TokenInvalidException."""
        wrong_secret = "c" * 43
        payload = {
            "sub": str(TEST_USER_ID),
            "email": TEST_EMAIL,
            "role": "user",
            "tier": "t1",
            "type": ACCESS_TOKEN_TYPE,
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,
        }
        token = jwt.encode(payload, wrong_secret, algorithm=ACCESS_TOKEN_ALGORITHM)
        with pytest.raises(TokenInvalidException):
            token_service.verify_access_token(token)

    def test_verify_malformed_token_raises(self, token_service: TokenService):
        with pytest.raises(TokenInvalidException):
            token_service.verify_access_token("not.a.valid.token")

    def test_verify_empty_token_raises(self, token_service: TokenService):
        with pytest.raises(TokenInvalidException):
            token_service.verify_access_token("")

    def test_verify_wrong_token_type_raises(self, token_service: TokenService):
        """Token with wrong type claim should raise."""
        payload = {
            "sub": str(TEST_USER_ID),
            "email": TEST_EMAIL,
            "role": "user",
            "tier": "t1",
            "type": "refresh",  # Wrong type
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=ACCESS_TOKEN_ALGORITHM)
        with pytest.raises(TokenInvalidException):
            token_service.verify_access_token(token)

    def test_verify_missing_claims_raises(self, token_service: TokenService):
        """Token missing required claims should raise."""
        payload = {
            "sub": str(TEST_USER_ID),
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,
            # Missing: email, role, tier, type
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=ACCESS_TOKEN_ALGORITHM)
        with pytest.raises((TokenInvalidException, TokenExpiredException)):
            token_service.verify_access_token(token)


class TestDualKeyRotation:
    """Tests for dual-key rotation support."""

    def test_verify_with_old_key(self):
        """Token signed with old key should still verify during rotation."""
        new_secret = "n" * 43
        old_secret = "o" * 43

        # Sign with old key
        payload = {
            "sub": str(TEST_USER_ID),
            "email": TEST_EMAIL,
            "role": "user",
            "tier": "t1",
            "type": ACCESS_TOKEN_TYPE,
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,
        }
        token = jwt.encode(payload, old_secret, algorithm=ACCESS_TOKEN_ALGORITHM)

        # Verify with service that has both keys
        service = TokenService(jwt_secret=new_secret, jwt_secret_old=old_secret)
        result = service.verify_access_token(token)
        assert result.sub == TEST_USER_ID

    def test_verify_with_current_key_preferred(self):
        """Token signed with current key should verify first."""
        new_secret = "n" * 43
        old_secret = "o" * 43

        service = TokenService(jwt_secret=new_secret, jwt_secret_old=old_secret)
        token = service.create_access_token(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            role="user",
            tier="t1",
        )
        result = service.verify_access_token(token)
        assert result.sub == TEST_USER_ID

    def test_verify_without_old_key(self, token_service_single_key: TokenService):
        """Without old key, only current key works."""
        token = token_service_single_key.create_access_token(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            role="user",
            tier="t1",
        )
        result = token_service_single_key.verify_access_token(token)
        assert result.sub == TEST_USER_ID

    def test_neither_key_matches_raises(self):
        """Token signed with unrecognized key should raise."""
        service = TokenService(jwt_secret="x" * 43, jwt_secret_old="y" * 43)
        payload = {
            "sub": str(TEST_USER_ID),
            "email": TEST_EMAIL,
            "role": "user",
            "tier": "t1",
            "type": ACCESS_TOKEN_TYPE,
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,
        }
        token = jwt.encode(payload, "z" * 43, algorithm=ACCESS_TOKEN_ALGORITHM)
        with pytest.raises(TokenInvalidException):
            service.verify_access_token(token)


class TestRefreshToken:
    """Tests for refresh token generation and hashing."""

    def test_create_refresh_token_returns_tuple(self):
        plaintext, token_hash = TokenService.create_refresh_token()
        assert isinstance(plaintext, str)
        assert isinstance(token_hash, str)
        assert len(plaintext) > 0
        assert len(token_hash) == 64  # SHA-256 hex digest length

    def test_create_refresh_token_unique(self):
        """Each call should produce a unique token."""
        t1_plain, t1_hash = TokenService.create_refresh_token()
        t2_plain, t2_hash = TokenService.create_refresh_token()
        assert t1_plain != t2_plain
        assert t1_hash != t2_hash

    def test_hash_matches_plaintext(self):
        """hash_refresh_token() should produce the same hash as create_refresh_token()."""
        plaintext, expected_hash = TokenService.create_refresh_token()
        actual_hash = TokenService.hash_refresh_token(plaintext)
        assert actual_hash == expected_hash

    def test_hash_refresh_token_deterministic(self):
        """Same plaintext should always produce the same hash."""
        h1 = TokenService.hash_refresh_token("test-token")
        h2 = TokenService.hash_refresh_token("test-token")
        assert h1 == h2

    def test_hash_refresh_token_is_sha256(self):
        plaintext = "test-token"
        expected = hashlib.sha256(plaintext.encode()).hexdigest()
        assert TokenService.hash_refresh_token(plaintext) == expected


class TestSecureToken:
    """Tests for create_secure_token() and hash_token()."""

    def test_create_secure_token_returns_tuple(self):
        plaintext, token_hash = TokenService.create_secure_token()
        assert isinstance(plaintext, str)
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64

    def test_create_secure_token_unique(self):
        t1_plain, _ = TokenService.create_secure_token()
        t2_plain, _ = TokenService.create_secure_token()
        assert t1_plain != t2_plain

    def test_hash_token_matches(self):
        plaintext, expected_hash = TokenService.create_secure_token()
        assert TokenService.hash_token(plaintext) == expected_hash


class TestValidateSecretsAtStartup:
    """Tests for validate_secrets_at_startup()."""

    def test_valid_secret(self):
        TokenService.validate_secrets_at_startup(jwt_secret="a" * 43)

    def test_empty_secret_raises(self):
        with pytest.raises(ValueError, match="required"):
            TokenService.validate_secrets_at_startup(jwt_secret="")

    def test_short_secret_raises(self):
        with pytest.raises(ValueError, match="too short"):
            TokenService.validate_secrets_at_startup(jwt_secret="a" * 42)

    def test_valid_with_old_secret(self):
        TokenService.validate_secrets_at_startup(
            jwt_secret="a" * 43,
            jwt_secret_old="b" * 43,
        )

    def test_short_old_secret_raises(self):
        with pytest.raises(ValueError, match="OLD.*too short"):
            TokenService.validate_secrets_at_startup(
                jwt_secret="a" * 43,
                jwt_secret_old="b" * 10,
            )

    def test_none_old_secret_ok(self):
        """None old secret should not raise."""
        TokenService.validate_secrets_at_startup(
            jwt_secret="a" * 43,
            jwt_secret_old=None,
        )

    def test_exact_min_length_ok(self):
        TokenService.validate_secrets_at_startup(
            jwt_secret="a" * JWT_SECRET_MIN_LENGTH,
        )
