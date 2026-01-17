#!/usr/bin/env python3
"""
Quick API Verification Script

独立运行脚本，用于快速验证 staging API 是否正常工作。
无需 pytest，直接运行即可。

Usage:
    # 方法 1: 通过环境变量设置 token
    export TEST_USER_TOKEN="your_clerk_jwt_token"
    python quick_verify.py

    # 方法 2: 通过命令行参数
    python quick_verify.py --token "your_clerk_jwt_token"

    # 方法 3: 测试所有接口
    python quick_verify.py --token "xxx" --all

@module tests.integration.staging.quick_verify
"""

import os
import sys
import argparse
import httpx
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


# ==========================================
# Configuration
# ==========================================

STAGING_BASE_URL = "https://decodables-staging.up.railway.app"
API_V2_PREFIX = "/api/v2"


@dataclass
class TestResult:
    """Test result container."""
    endpoint: str
    method: str
    success: bool
    status_code: int
    message: str
    response_preview: Optional[str] = None


# ==========================================
# Test Functions
# ==========================================

def test_health(client: httpx.Client) -> TestResult:
    """Test /health endpoint (no auth required)."""
    endpoint = "/health"
    try:
        response = client.get(f"{STAGING_BASE_URL}{endpoint}")
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=response.status_code == 200,
            status_code=response.status_code,
            message="Health check passed" if response.status_code == 200 else "Health check failed",
            response_preview=response.text[:200],
        )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            message=f"Connection error: {e}",
        )


def test_profile_me(client: httpx.Client, token: str) -> TestResult:
    """Test /api/v2/user/profile/me endpoint."""
    endpoint = f"{API_V2_PREFIX}/user/profile/me"
    try:
        response = client.get(
            f"{STAGING_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 200:
            data = response.json()
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=True,
                status_code=200,
                message=f"User: {data.get('email', 'N/A')} | Tier: {data.get('tier', 'N/A')}",
                response_preview=str(data)[:300],
            )
        else:
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=False,
                status_code=response.status_code,
                message=response.text[:200],
            )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            message=f"Error: {e}",
        )


def test_billing_credits(client: httpx.Client, token: str) -> TestResult:
    """Test /api/v2/user/billing/credits endpoint."""
    endpoint = f"{API_V2_PREFIX}/user/billing/credits"
    try:
        response = client.get(
            f"{STAGING_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 200:
            data = response.json()
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=True,
                status_code=200,
                message=f"Monthly: {data.get('credits_monthly', 'N/A')} | Permanent: {data.get('credits_permanent', 'N/A')}",
                response_preview=str(data)[:300],
            )
        else:
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=False,
                status_code=response.status_code,
                message=response.text[:200],
            )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            message=f"Error: {e}",
        )


def test_projects_list(client: httpx.Client, token: str) -> TestResult:
    """Test /api/v2/user/projects endpoint."""
    endpoint = f"{API_V2_PREFIX}/user/projects"
    try:
        response = client.get(
            f"{STAGING_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 5, "offset": 0},
        )

        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", data.get("projects", []))
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=True,
                status_code=200,
                message=f"Found {len(items)} projects",
                response_preview=str(data)[:300],
            )
        else:
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=False,
                status_code=response.status_code,
                message=response.text[:200],
            )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            message=f"Error: {e}",
        )


def test_config(client: httpx.Client, token: str) -> TestResult:
    """Test /api/v2/user/config endpoint (public configs)."""
    endpoint = f"{API_V2_PREFIX}/user/config"
    try:
        response = client.get(
            f"{STAGING_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 200:
            data = response.json()
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=True,
                status_code=200,
                message=f"Got {len(data) if isinstance(data, (list, dict)) else 'N/A'} config items",
                response_preview=str(data)[:300],
            )
        else:
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=False,
                status_code=response.status_code,
                message=response.text[:200],
            )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            message=f"Error: {e}",
        )


def test_resources(client: httpx.Client, token: str) -> TestResult:
    """Test /api/v2/user/resources endpoint."""
    endpoint = f"{API_V2_PREFIX}/user/resources"
    try:
        response = client.get(
            f"{STAGING_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 5},
        )

        if response.status_code == 200:
            data = response.json()
            items = data if isinstance(data, list) else data.get("items", data.get("resources", []))
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=True,
                status_code=200,
                message=f"Found {len(items)} resources",
                response_preview=str(data)[:300],
            )
        else:
            return TestResult(
                endpoint=endpoint,
                method="GET",
                success=False,
                status_code=response.status_code,
                message=response.text[:200],
            )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            message=f"Error: {e}",
        )


def test_unauthenticated(client: httpx.Client) -> TestResult:
    """Test that /profile/me rejects unauthenticated requests."""
    endpoint = f"{API_V2_PREFIX}/user/profile/me"
    try:
        response = client.get(f"{STAGING_BASE_URL}{endpoint}")

        return TestResult(
            endpoint=endpoint + " (no auth)",
            method="GET",
            success=response.status_code == 401,
            status_code=response.status_code,
            message="Correctly rejected" if response.status_code == 401 else "Should have returned 401",
        )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            message=f"Error: {e}",
        )


# ==========================================
# Main Runner
# ==========================================

def print_result(result: TestResult, verbose: bool = False):
    """Print test result with formatting."""
    status = "✅" if result.success else "❌"
    print(f"{status} [{result.method}] {result.endpoint}")
    print(f"   Status: {result.status_code} | {result.message}")
    if verbose and result.response_preview:
        print(f"   Response: {result.response_preview}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Quick API verification for staging environment"
    )
    parser.add_argument(
        "--token", "-t",
        help="Clerk JWT token (or set TEST_USER_TOKEN env var)",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Test all endpoints (not just profile)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show response previews",
    )
    args = parser.parse_args()

    # Get token
    token = args.token or os.getenv("TEST_USER_TOKEN")

    print("=" * 60)
    print(f"🔍 Staging API Verification")
    print(f"   Base URL: {STAGING_BASE_URL}")
    print(f"   Time: {datetime.now().isoformat()}")
    print(f"   Token: {'***' + token[-10:] if token else 'NOT SET'}")
    print("=" * 60)
    print()

    results = []

    with httpx.Client(timeout=30.0) as client:
        # 1. Health check (no auth)
        print("🏥 Testing Health Endpoint...")
        results.append(test_health(client))
        print_result(results[-1], args.verbose)

        # 2. Unauthenticated rejection test
        print("🔐 Testing Auth Rejection...")
        results.append(test_unauthenticated(client))
        print_result(results[-1], args.verbose)

        if not token:
            print("⚠️  No token provided. Skipping authenticated tests.")
            print("   Set TEST_USER_TOKEN env var or use --token argument.")
            sys.exit(1)

        # 3. Profile (requires auth)
        print("👤 Testing User Profile...")
        results.append(test_profile_me(client, token))
        print_result(results[-1], args.verbose)

        if args.all:
            # 4. Billing
            print("💰 Testing Billing Credits...")
            results.append(test_billing_credits(client, token))
            print_result(results[-1], args.verbose)

            # 5. Projects
            print("📁 Testing Projects...")
            results.append(test_projects_list(client, token))
            print_result(results[-1], args.verbose)

            # 6. Config
            print("⚙️  Testing Config...")
            results.append(test_config(client, token))
            print_result(results[-1], args.verbose)

            # 7. Resources
            print("🎨 Testing Resources...")
            results.append(test_resources(client, token))
            print_result(results[-1], args.verbose)

    # Summary
    print("=" * 60)
    passed = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    print(f"📊 Summary: {passed} passed, {failed} failed")
    print("=" * 60)

    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
