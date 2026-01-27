"""
Test JWT Generator

Generates JWT tokens for integration testing without requiring Clerk login.
Uses a dedicated RSA key pair - the public key must be configured in
Railway Staging as TEST_JWT_PUBLIC_KEY.

Usage:
    from tests.integration.staging.test_jwt_generator import generate_test_token

    token = generate_test_token(user_id="user_test_123", tier="t1")
"""

import jwt
import time
from typing import Optional

# Test RSA Private Key (for signing test JWTs)
# The corresponding public key must be configured in Railway Staging
TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDa4rLsof1v3IoY
2ps0E5WMJhG1EeZ+4xmmqCz+DeRD6mGlLf1PPVCnokxjnAGNktVfo0ItYffPqZr6
vUuvRPUJGOy7N79qp+8wmUmtAXtNVr68YCVO72Q6WfyraHNphM/JEAXTUhOyPpDa
/A2pkqeqKPA1n9GkoMt+Kbm0YTauhNxINRIvC0xd+opw4IlGGnpBsMnZcCE4zM3/
mcZ+rru+ZoN3zbvfwPb1dGzFG1uW4sRRJUBgF1vBkVkmqMlD7pzBeN1gwvJ6Dpvm
PpgNQA+pb2nXF/h8so0UNOzEmXmkdXgzeYcjn49Gpq8EYRWLOgUw0bm0bdunMvI0
lU6PdKa1AgMBAAECggEABhmAkSQq5Iw5rVtuLTA8hlUxpu3/eKeKEyeNm9JpFLsH
CvjYncKTwraJnwVkBhao61gPCiYep0LoZpz4a0M/+gefrtBTY7zK50izEZpAd673
dFcDj/F1rBCbTQi4ndPaWUjtuKFWNJN8xIJD1gCYIbkWIV05e0QSpHEaOgLmTxlB
TQzepXEQlv6AH0AvkrqYH57a9iIll6uLsN8oK02n0Dh8NwYcSNmgTSoeJSMqzxZK
GUp8taohJWXeax3MsaKyqtZpkYSlgtUOq+mOGeiesxVueZBe8BY5F2NzoLKqh2uQ
zWnJ42hnvnFz4exDpQoqWk18B0MDKNxwxJ8MXruw0QKBgQD9tbM7ZGjG1PbWMdpW
VNurbbv79laPvrF1T8ppPVrIOdq/p5ejBW3vtDuCbYRS8WMq+9xbc4Bck6IUMTC2
ulKyNWiDwIiKgS5AXIqkj+FAvO9jJeVGs3NfJdRAVay1aJn0Vsi1uQ+8uunL10vm
Ix9fOehs2Ah6IInavFXHdqb5LQKBgQDc3IXyVYu9KXy20XaH++OeCAGBrQ/EN7cL
FXxRxDgVEJSBu+WCgfFq+dfNKggbEl806kcdKzbSY9RaiKKkUE6YgyM7EEuWX26l
1Z4VAqxICKSIhadOGaf6BegmSzICP69baSkSvOanLuan25tkdkY3KUx4FYoPwI1q
zv/nZivIqQKBgAr2nxgh7qUo7sGyxcyVPijaRRVOP89WXjTDjeueSx374ggGJfdV
dLq2/xtTwDQVWkOxPoR1KUbW2lolBgXfZ1NsG2gWGdBiZK1DUnpp/UHe6DlQmefE
OWgTKmjdSulL69szJNk1dgihyxiT5SO8wM5Mok6Rx0v/u/VHzi0gY3bBAoGAUgh+
n/HyQ0Jjliva0MtYUdw7YwT6tDDVhgJm+J/fDMPpxP4bUwwctVUzOHsCI7wBLNBP
tZ/VbvOxbicN8eX6K1+Z+FgnGyU7HdFoM/mYL/E125d4+uNApvcGsSKA4qDw6wz2
OoV7TmF3PqWs4/WiQt7ODlRBwXQNkrxsBHDIlnECgYAg/JUiwPjL4T+LgmUp0X1d
LazvqQwdm3/7jrOIMkQ1Q2wlnmsfhCgIhH/kSU3h2sF2Sfb3wRmRDQdKGrGMCFTA
3JGasRoEikX7e32dgggHUM9BDJ0WpERJVjTrE81h0olCpqt7qUlGawaD1JceG+Wf
OBnHAZ/0PZC8tUlufuPkqg==
-----END PRIVATE KEY-----"""

# Test RSA Public Key (configure this in Railway Staging as TEST_JWT_PUBLIC_KEY)
TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2uKy7KH9b9yKGNqbNBOV
jCYRtRHmfuMZpqgs/g3kQ+phpS39Tz1Qp6JMY5wBjZLVX6NCLWH3z6ma+r1Lr0T1
CRjsuze/aqfvMJlJrQF7TVa+vGAlTu9kOln8q2hzaYTPyRAF01ITsj6Q2vwNqZKn
qijwNZ/RpKDLfim5tGE2roTcSDUSLwtMXfqKcOCJRhp6QbDJ2XAhOMzN/5nGfq67
vmaDd82738D29XRsxRtbluLEUSVAYBdbwZFZJqjJQ+6cwXjdYMLyeg6b5j6YDUAP
qW9p1xf4fLKNFDTsxJl5pHV4M3mHI5+PRqavBGEVizoFMNG5tG3bpzLyNJVOj3Sm
tQIDAQAB
-----END PUBLIC KEY-----"""


# Pre-defined test users for different tiers
TEST_USERS = {
    "free": {
        "user_id": "user_test_free_001",
        "email": "test-free@makedecodables.com",
        "tier": "t1",
    },
    "starter": {
        "user_id": "user_test_starter_001",
        "email": "test-starter@makedecodables.com",
        "tier": "t2",
    },
    "pro": {
        "user_id": "user_test_pro_001",
        "email": "test-pro@makedecodables.com",
        "tier": "t3",
    },
    "admin": {
        "user_id": "user_test_admin_001",
        "email": "test-admin@makedecodables.com",
        "tier": "t3",
        "role": "admin",
    },
}


def generate_test_token(
    user_id: str,
    email: Optional[str] = None,
    tier: str = "t1",
    role: Optional[str] = None,
    expires_in: int = 3600,
) -> str:
    """
    Generate a JWT token for testing.

    Args:
        user_id: The user ID (sub claim)
        email: User email (optional)
        tier: User tier (t1/t2/t3)
        role: User role (optional, e.g., "admin")
        expires_in: Token validity in seconds (default 1 hour)

    Returns:
        JWT token string
    """
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + expires_in,
    }

    if email:
        payload["email"] = email

    # These are custom claims for test tokens
    # Note: Actual user tier/role is read from database, not JWT
    # These are just for documentation/debugging purposes
    if tier:
        payload["test_tier"] = tier
    if role:
        payload["test_role"] = role

    return jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256")


def get_test_token_for_tier(tier: str) -> str:
    """
    Get a test token for a specific tier.

    Args:
        tier: One of "free", "starter", "pro", "admin"

    Returns:
        JWT token string
    """
    if tier not in TEST_USERS:
        raise ValueError(f"Unknown tier: {tier}. Available: {list(TEST_USERS.keys())}")

    user = TEST_USERS[tier]
    return generate_test_token(
        user_id=user["user_id"],
        email=user["email"],
        tier=user.get("tier", "t1"),
        role=user.get("role"),
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
    print("=== Test JWT Generator Demo ===\n")

    print("Public Key (configure in Railway TEST_JWT_PUBLIC_KEY):")
    print(TEST_PUBLIC_KEY)

    print("\n--- Sample Tokens ---\n")

    for tier_name in TEST_USERS:
        token = get_test_token_for_tier(tier_name)
        print(f"{tier_name.upper()} Token:")
        print(f"  {token[:60]}...")

        # Verify
        decoded = jwt.decode(token, TEST_PUBLIC_KEY, algorithms=["RS256"])
        print(f"  Payload: {decoded}\n")
