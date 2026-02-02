"""
PasswordService — Argon2id hashing and password strength validation.

Uses argon2-cffi for OWASP 2024 recommended argon2id hashing.
All operations are synchronous (CPU-bound); callers should use
run_in_threadpool() in async contexts.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

from .value_objects import PasswordStrength


class PasswordService:
    """
    Domain service for password operations.

    Responsibilities:
    - Hash passwords using argon2id
    - Verify passwords against stored hashes (time-safe)
    - Validate password strength against configured rules
    """

    def __init__(self) -> None:
        # argon2-cffi defaults: memory=65536 KB, iterations=3, parallelism=4
        # Target: 0.5-1s per hash on Railway instance
        self._hasher = PasswordHasher(
            time_cost=3,        # iterations
            memory_cost=65536,  # 64 MB
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash_password(self, password: str) -> str:
        """
        Hash a plaintext password using argon2id.

        Args:
            password: Plaintext password.

        Returns:
            Argon2id hash string (e.g., $argon2id$v=19$m=65536,t=3,p=4$salt$hash).
        """
        return self._hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a plaintext password against a stored argon2id hash.

        Uses time-safe comparison (built into argon2-cffi).

        Args:
            password: Plaintext password to verify.
            password_hash: Stored argon2id hash.

        Returns:
            True if password matches, False otherwise.
        """
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHash):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """
        Check if a stored hash needs rehashing (e.g., after parameter change).

        Args:
            password_hash: Stored argon2id hash.

        Returns:
            True if hash parameters differ from current config.
        """
        return self._hasher.check_needs_rehash(password_hash)

    @staticmethod
    def validate_strength(password: str) -> PasswordStrength:
        """
        Validate password strength against configured rules.

        Args:
            password: Plaintext password to validate.

        Returns:
            PasswordStrength value object with validation results.
        """
        return PasswordStrength.validate(password)
