"""
Test JWT Generator — Self-hosted HS256 tokens.

Generates JWT tokens for integration testing using the same HS256 algorithm
as the production TokenService. No Clerk dependency required.

Usage:
    from tests.integration.staging.test_jwt_generator import generate_test_token

    token = generate_test_token(user_id="user_test_123", tier="t1")
"""

import os
import time
from typing import Optional
from uuid import UUID

import jwt

# Use AUTH_JWT_SECRET from environment, or a test default
# In CI/staging, this should be set to match the deployed backend's secret
TEST_JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "test_jwt_secret_for_integration_testing_43chars")


# Pre-defined test users for different tiers
TEST_USERS = {
    "free": {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "test-free@makedecodables.com",
        "tier": "t1",
        "role": "user",
    },
    "starter": {
        "user_id": "00000000-0000-0000-0000-000000000002",
        "email": "test-starter@makedecodables.com",
        "tier": "t2",
        "role": "user",
    },
    "pro": {
        "user_id": "00000000-0000-0000-0000-000000000003",
        "email": "test-pro@makedecodables.com",
        "tier": "t3",
        "role": "user",
    },
    "admin": {
        "user_id": "00000000-0000-0000-0000-000000000099",
        "email": "test-admin@makedecodables.com",
        "tier": "t3",
        "role": "admin",
    },
}


def generate_test_token(
    user_id: str,
    email: Optional[str] = None,
    tier: str = "t1",
    role: str = "user",
    expires_in: int = 3600,
) -> str:
    """
    Generate an HS256 JWT token for testing.

    Produces tokens compatible with TokenService.verify_access_token().

    Args:
        user_id: The user UUID string (sub claim).
        email: User email.
        tier: User tier (t1/t2/t3).
        role: User role ("user" or "admin").
        expires_in: Token validity in seconds (default 1 hour).

    Returns:
        JWT token string.
    """
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email or f"test-{tier}@makedecodables.com",
        "role": role,
        "tier": tier,
        "type": "access",
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


def get_test_token_for_tier(tier: str) -> str:
    """
    Get a test token for a specific tier.

    Args:
        tier: One of "free", "starter", "pro", "admin"

    Returns:
        HS256 JWT token string.
    """
    if tier not in TEST_USERS:
        raise ValueError(f"Unknown tier: {tier}. Available: {list(TEST_USERS.keys())}")

    user = TEST_USERS[tier]
    return generate_test_token(
        user_id=user["user_id"],
        email=user["email"],
        tier=user.get("tier", "t1"),
        role=user.get("role", "user"),
    )


# Quick access tokens
def get_free_token() -> str:
    """Get a token for free tier user."""
    return get_test_token_for_tier("free")


def get_starter_token() -> str:
    """Get a token for starter tier user."""
    return get_test_token_for_tier("starter")


def get_pro_token() -> str:
    """Get a token for pro tier user."""
    return get_test_token_for_tier("pro")


def get_admin_token() -> str:
    """Get a token for admin user."""
    return get_test_token_for_tier("admin")


if __name__ == "__main__":
    # Demo: generate and verify tokens
    print("=== Self-hosted HS256 Test JWT Generator ===\n")
    print(f"Using secret: {TEST_JWT_SECRET[:10]}... ({len(TEST_JWT_SECRET)} chars)\n")

    print("--- Sample Tokens ---\n")

    for tier_name in TEST_USERS:
        token = get_test_token_for_tier(tier_name)
        print(f"{tier_name.upper()} Token:")
        print(f"  {token[:60]}...")

        # Verify
        decoded = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
        print(f"  Payload: {decoded}\n")
