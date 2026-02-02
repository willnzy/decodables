"""
Tests for PasswordService — Argon2id hashing and password strength validation.

Covers:
- Password hashing and verification
- Rehash detection
- Password strength validation rules
- Common password rejection
- Edge cases (empty, too short, too long, Unicode)
"""

import pytest

from domains.auth.password_service import PasswordService
from domains.auth.constants import (
    PASSWORD_MIN_LENGTH,
    PASSWORD_MAX_LENGTH,
    COMMON_PASSWORDS,
)


class TestHashPassword:
    """Tests for hash_password()."""

    def test_hash_returns_argon2id_string(self, password_service: PasswordService):
        result = password_service.hash_password("TestPass1")
        assert result.startswith("$argon2id$")

    def test_hash_produces_unique_hashes(self, password_service: PasswordService):
        """Same password should produce different hashes (random salt)."""
        hash1 = password_service.hash_password("TestPass1")
        hash2 = password_service.hash_password("TestPass1")
        assert hash1 != hash2

    def test_hash_different_passwords(self, password_service: PasswordService):
        hash1 = password_service.hash_password("Password1A")
        hash2 = password_service.hash_password("Password2B")
        assert hash1 != hash2


class TestVerifyPassword:
    """Tests for verify_password()."""

    def test_verify_correct_password(self, password_service: PasswordService):
        password = "TestPassword1"
        hashed = password_service.hash_password(password)
        assert password_service.verify_password(password, hashed) is True

    def test_verify_wrong_password(self, password_service: PasswordService):
        hashed = password_service.hash_password("CorrectPassword1")
        assert password_service.verify_password("WrongPassword1", hashed) is False

    def test_verify_invalid_hash_returns_false(self, password_service: PasswordService):
        """Invalid hash format should not raise, just return False."""
        assert password_service.verify_password("anypass", "not-a-valid-hash") is False

    def test_verify_empty_hash_returns_false(self, password_service: PasswordService):
        assert password_service.verify_password("anypass", "") is False

    def test_verify_case_sensitive(self, password_service: PasswordService):
        hashed = password_service.hash_password("TestPass1")
        assert password_service.verify_password("testpass1", hashed) is False
        assert password_service.verify_password("TESTPASS1", hashed) is False


class TestNeedsRehash:
    """Tests for needs_rehash()."""

    def test_fresh_hash_no_rehash(self, password_service: PasswordService):
        hashed = password_service.hash_password("TestPass1")
        assert password_service.needs_rehash(hashed) is False

    def test_old_parameters_needs_rehash(self):
        """Hash with different parameters should need rehash."""
        from argon2 import PasswordHasher

        old_hasher = PasswordHasher(time_cost=1, memory_cost=32768)
        old_hash = old_hasher.hash("TestPass1")

        # Current service uses time_cost=3, memory_cost=65536
        service = PasswordService()
        assert service.needs_rehash(old_hash) is True


class TestValidateStrength:
    """Tests for validate_strength() via PasswordStrength value object."""

    def test_valid_password(self):
        result = PasswordService.validate_strength("StrongP@ss1")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_too_short(self):
        result = PasswordService.validate_strength("Ab1")
        assert result.is_valid is False
        assert any("at least" in e for e in result.errors)

    def test_too_long(self):
        result = PasswordService.validate_strength("A" * (PASSWORD_MAX_LENGTH + 1) + "a1")
        assert result.is_valid is False
        assert any("exceed" in e.lower() for e in result.errors)

    def test_missing_uppercase(self):
        result = PasswordService.validate_strength("alllower1")
        assert result.is_valid is False
        assert any("uppercase" in e for e in result.errors)

    def test_missing_lowercase(self):
        result = PasswordService.validate_strength("ALLUPPER1")
        assert result.is_valid is False
        assert any("lowercase" in e for e in result.errors)

    def test_missing_digit(self):
        result = PasswordService.validate_strength("NoDigitsHere")
        assert result.is_valid is False
        assert any("digit" in e for e in result.errors)

    def test_common_password_rejected(self):
        """Passwords in the blacklist should be rejected."""
        result = PasswordService.validate_strength("Password1")
        # "password1" is in COMMON_PASSWORDS (case-insensitive check)
        assert result.is_valid is False
        assert any("common" in e.lower() for e in result.errors)

    def test_minimum_valid_password(self):
        """Password at exactly minimum length with all requirements."""
        result = PasswordService.validate_strength("Abcdef1x")
        assert result.is_valid is True

    def test_multiple_errors_collected(self):
        """A very weak password should collect multiple errors."""
        result = PasswordService.validate_strength("ab")
        assert result.is_valid is False
        assert len(result.errors) >= 2  # too short + missing uppercase + missing digit

    def test_unicode_password(self):
        """Unicode characters should be allowed."""
        result = PasswordService.validate_strength("Str0ng\u4e2d\u6587Pass")
        assert result.is_valid is True

    def test_exact_min_length(self):
        # Exactly PASSWORD_MIN_LENGTH chars with all requirements
        pwd = "A" + "b" * (PASSWORD_MIN_LENGTH - 2) + "1"
        result = PasswordService.validate_strength(pwd)
        assert result.is_valid is True

    def test_exact_max_length(self):
        pwd = "A" + "b" * (PASSWORD_MAX_LENGTH - 2) + "1"
        result = PasswordService.validate_strength(pwd)
        assert result.is_valid is True
