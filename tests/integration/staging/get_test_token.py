#!/usr/bin/env python3
"""
Get Test Token from Clerk Backend API

使用 Clerk Backend API 获取测试用户的 JWT token。

Usage:
    # 设置 Clerk Secret Key
    export CLERK_SECRET_KEY="sk_test_xxx"

    # 获取 token (使用已有 session)
    python get_test_token.py --session-id "sess_xxx"

    # 或者列出用户的所有 sessions
    python get_test_token.py --user-id "user_xxx" --list-sessions

    # 获取 token 并直接运行测试
    python get_test_token.py --session-id "sess_xxx" --run-tests

@module tests.integration.staging.get_test_token
"""

import os
import sys
import argparse
import httpx
import json
from datetime import datetime


CLERK_API_BASE = "https://api.clerk.com/v1"


def get_clerk_secret_key() -> str:
    """Get Clerk Secret Key from environment."""
    key = os.getenv("CLERK_SECRET_KEY")
    if not key:
        print("❌ CLERK_SECRET_KEY not set")
        print("   Please set it: export CLERK_SECRET_KEY='sk_test_xxx'")
        print("   Get it from: https://dashboard.clerk.com/ → API Keys")
        sys.exit(1)
    return key


def list_users(secret_key: str, limit: int = 10):
    """List users in the Clerk application."""
    response = httpx.get(
        f"{CLERK_API_BASE}/users",
        headers={"Authorization": f"Bearer {secret_key}"},
        params={"limit": limit},
    )

    if response.status_code != 200:
        print(f"❌ Failed to list users: {response.status_code}")
        print(f"   {response.text}")
        return

    users = response.json()
    print(f"\n📋 Found {len(users)} users:\n")
    for user in users:
        email = user.get("email_addresses", [{}])[0].get("email_address", "N/A")
        print(f"   ID: {user['id']}")
        print(f"   Email: {email}")
        print(f"   Created: {user.get('created_at')}")
        print()


def list_sessions(secret_key: str, user_id: str):
    """List active sessions for a user."""
    response = httpx.get(
        f"{CLERK_API_BASE}/users/{user_id}/sessions",
        headers={"Authorization": f"Bearer {secret_key}"},
    )

    if response.status_code != 200:
        print(f"❌ Failed to list sessions: {response.status_code}")
        print(f"   {response.text}")
        return

    sessions = response.json()
    print(f"\n📋 Found {len(sessions)} sessions for {user_id}:\n")
    for session in sessions:
        print(f"   Session ID: {session['id']}")
        print(f"   Status: {session.get('status')}")
        print(f"   Last Active: {session.get('last_active_at')}")
        print(f"   Expire At: {session.get('expire_at')}")
        print()

    return sessions


def get_session_token(secret_key: str, session_id: str) -> str:
    """
    Get a JWT token for a session.

    Note: Clerk Backend API 的 /sessions/{id}/tokens 端点
    可以生成新的 JWT token。
    """
    response = httpx.post(
        f"{CLERK_API_BASE}/sessions/{session_id}/tokens",
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        },
        json={},  # Empty body but with JSON content type
    )

    if response.status_code != 200:
        print(f"❌ Failed to get token: {response.status_code}")
        print(f"   {response.text}")
        return None

    data = response.json()
    token = data.get("jwt")

    if token:
        # Decode payload to show expiration
        import base64
        payload_b64 = token.split(".")[1]
        # Add padding if needed
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        exp_time = datetime.fromtimestamp(payload.get("exp", 0))
        iat_time = datetime.fromtimestamp(payload.get("iat", 0))

        print(f"\n✅ Token generated successfully!")
        print(f"   Issued at: {iat_time}")
        print(f"   Expires at: {exp_time}")
        print(f"   Valid for: {(exp_time - datetime.now()).seconds} seconds")
        print(f"\n   Token:\n   {token}\n")

        return token

    return None


def create_test_session(secret_key: str, user_id: str) -> str:
    """
    Create a new session for a user (requires Clerk Pro plan).

    This is useful for automated testing.
    """
    response = httpx.post(
        f"{CLERK_API_BASE}/sessions",
        headers={"Authorization": f"Bearer {secret_key}"},
        json={"user_id": user_id},
    )

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create session: {response.status_code}")
        print(f"   {response.text}")
        print("\n   Note: Creating sessions via API may require Clerk Pro plan.")
        return None

    session = response.json()
    print(f"\n✅ Session created: {session['id']}")
    return session["id"]


def run_tests_with_token(token: str):
    """Run the quick verify tests with the token."""
    import subprocess

    script_path = os.path.join(os.path.dirname(__file__), "quick_verify.py")
    result = subprocess.run(
        [sys.executable, script_path, "--token", token, "--all", "--verbose"],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Get test token from Clerk Backend API")

    parser.add_argument("--list-users", action="store_true", help="List all users")
    parser.add_argument("--user-id", help="User ID to work with")
    parser.add_argument("--list-sessions", action="store_true", help="List sessions for a user")
    parser.add_argument("--session-id", help="Session ID to get token for")
    parser.add_argument("--create-session", action="store_true", help="Create new session for user")
    parser.add_argument("--run-tests", action="store_true", help="Run tests after getting token")

    args = parser.parse_args()

    secret_key = get_clerk_secret_key()
    print(f"🔑 Using Clerk Secret Key: ***{secret_key[-8:]}")

    if args.list_users:
        list_users(secret_key)
        return

    if args.list_sessions:
        if not args.user_id:
            print("❌ --user-id required with --list-sessions")
            sys.exit(1)
        list_sessions(secret_key, args.user_id)
        return

    if args.create_session:
        if not args.user_id:
            print("❌ --user-id required with --create-session")
            sys.exit(1)
        session_id = create_test_session(secret_key, args.user_id)
        if session_id and args.run_tests:
            token = get_session_token(secret_key, session_id)
            if token:
                run_tests_with_token(token)
        return

    if args.session_id:
        token = get_session_token(secret_key, args.session_id)
        if token and args.run_tests:
            run_tests_with_token(token)
        return

    # Default: show help
    print("\n📖 Usage examples:")
    print()
    print("   # 1. 列出所有用户")
    print("   python get_test_token.py --list-users")
    print()
    print("   # 2. 列出某用户的 sessions")
    print("   python get_test_token.py --user-id user_xxx --list-sessions")
    print()
    print("   # 3. 获取某 session 的 token")
    print("   python get_test_token.py --session-id sess_xxx")
    print()
    print("   # 4. 获取 token 并运行测试")
    print("   python get_test_token.py --session-id sess_xxx --run-tests")
    print()
    print("   从你的 JWT 中提取的信息:")
    print("   - User ID: user_38J7ztkfxMPma40Q5FQ2ryO80eg")
    print("   - Session ID: sess_38J7zsBRioQ25vJRE6K3pogvU6K")
    print()
    print("   快速开始:")
    print("   python get_test_token.py --session-id sess_38J7zsBRioQ25vJRE6K3pogvU6K --run-tests")


if __name__ == "__main__":
    main()
