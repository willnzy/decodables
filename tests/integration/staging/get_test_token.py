#!/usr/bin/env python3
"""
Get Clerk JWT Token for Integration Tests

Uses Clerk Secret Key to generate a fresh JWT token for the test user.
Token is valid for about 60 seconds, so call this before running tests.

Usage:
    # Get token and export to environment
    export TEST_USER_TOKEN=$(python tests/integration/staging/get_test_token.py)

    # Or run tests directly with token
    TEST_USER_TOKEN=$(python tests/integration/staging/get_test_token.py) \
        pytest tests/integration/staging/ -v

@module tests.integration.staging.get_test_token
"""

import os
import sys
import requests
from typing import Optional

# Clerk API credentials
# You can override these with environment variables
CLERK_SECRET_KEY = os.getenv(
    "CLERK_SECRET_KEY",
    "sk_test_CdyvwDlsciBP95hNmBf3EeMsQhmpLZcWW5hwU1bfKa"
)

# Default test user (can be overridden with TEST_USER_ID env var)
DEFAULT_TEST_USER_ID = "user_38J7ztkfxMPma40Q5FQ2ryO80eg"


def get_active_session(user_id: str) -> Optional[str]:
    """Get the most recent active session for a user."""
    response = requests.get(
        "https://api.clerk.dev/v1/sessions",
        headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
        params={"user_id": user_id, "status": "active"}
    )

    if response.status_code != 200:
        print(f"Error getting sessions: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return None

    sessions = response.json()
    if not sessions:
        print(f"No active sessions for user {user_id}", file=sys.stderr)
        print("Please login to the staging frontend first.", file=sys.stderr)
        return None

    # Return the most recent session
    return sessions[0]["id"]


def generate_token(session_id: str) -> Optional[str]:
    """Generate a JWT token from a session."""
    response = requests.post(
        f"https://api.clerk.dev/v1/sessions/{session_id}/tokens",
        headers={
            "Authorization": f"Bearer {CLERK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
    )

    if response.status_code != 200:
        print(f"Error generating token: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return None

    return response.json().get("jwt")


def get_test_token(user_id: Optional[str] = None) -> Optional[str]:
    """
    Get a fresh JWT token for the test user.

    Args:
        user_id: Clerk user ID (defaults to DEFAULT_TEST_USER_ID)

    Returns:
        JWT token string or None if failed
    """
    user_id = user_id or os.getenv("TEST_USER_ID", DEFAULT_TEST_USER_ID)

    session_id = get_active_session(user_id)
    if not session_id:
        return None

    return generate_token(session_id)


def main():
    """Main entry point - prints token to stdout."""
    token = get_test_token()
    if token:
        print(token)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
