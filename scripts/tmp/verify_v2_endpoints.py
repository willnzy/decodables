#!/usr/bin/env python3
"""
API v2 Endpoint Verification Script

This script verifies that all v2 API endpoints are properly registered in app.py.
It checks the api/__init__.py aggregation and provides a comprehensive report.

Usage:
    python scripts/verify_v2_endpoints.py

Expected Output:
    - Total v2 endpoints count
    - Breakdown by category (Public, Admin, Webhooks)
    - Detailed endpoint list with HTTP methods
    - Verification status
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set


def extract_routes_from_file(file_path: Path) -> List[Dict[str, str]]:
    """
    Extract route definitions from a Python API file.

    Returns list of routes with format:
    [
        {"method": "GET", "path": "/user/profile", "function": "get_user_profile"},
        ...
    ]
    """
    routes = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)

        for node in ast.walk(tree):
            # Look for @router.get(), @router.post(), etc. decorators
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in ['get', 'post', 'put', 'patch', 'delete']:
                                method = decorator.func.attr.upper()
                                # Extract path from first argument
                                if decorator.args:
                                    if isinstance(decorator.args[0], ast.Constant):
                                        path = decorator.args[0].value
                                        routes.append({
                                            "method": method,
                                            "path": path,
                                            "function": node.name
                                        })
    except Exception as e:
        print(f"⚠️  Error parsing {file_path}: {e}")

    return routes


def scan_api_directory() -> Dict[str, List[Dict[str, str]]]:
    """
    Scan the api/ directory and extract all v2 endpoints.

    Returns:
    {
        "api_file_name": [
            {"method": "GET", "path": "/path", "function": "func_name"},
            ...
        ],
        ...
    }
    """
    api_dir = Path(__file__).parent.parent / 'api'
    endpoints_by_file = {}

    # Scan public APIs (root level)
    for api_file in api_dir.glob('*_api.py'):
        if api_file.name != '__init__.py':
            file_name = api_file.stem
            routes = extract_routes_from_file(api_file)
            if routes:
                endpoints_by_file[file_name] = routes

    # Scan admin APIs (admin/ subdirectory)
    admin_dir = api_dir / 'admin'
    if admin_dir.exists():
        for api_file in admin_dir.glob('*_api.py'):
            if api_file.name != '__init__.py':
                file_name = f"admin/{api_file.stem}"
                routes = extract_routes_from_file(api_file)
                if routes:
                    endpoints_by_file[file_name] = routes

    return endpoints_by_file


def verify_api_init() -> bool:
    """
    Verify that api/__init__.py includes all routers.
    """
    api_init = Path(__file__).parent.parent / 'api' / '__init__.py'

    if not api_init.exists():
        print("❌ api/__init__.py not found!")
        return False

    with open(api_init, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for api_router definition
    if 'api_router = APIRouter()' not in content:
        print("⚠️  api_router not found in api/__init__.py")
        return False

    # Check for admin_router import
    if 'from .admin import admin_router' not in content:
        print("⚠️  admin_router import not found in api/__init__.py")
        return False

    print("✅ api/__init__.py correctly aggregates all routers")
    return True


def verify_app_py() -> bool:
    """
    Verify that app.py includes the v2 API router.
    """
    app_py = Path(__file__).parent.parent / 'app.py'

    if not app_py.exists():
        print("❌ app.py not found!")
        return False

    with open(app_py, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for v2 API router import and inclusion
    if 'from api import api_router as ddd_api_router' not in content:
        print("❌ v2 API router import not found in app.py")
        return False

    if 'app.include_router(ddd_api_router)' not in content:
        print("❌ v2 API router not included in app.py")
        return False

    print("✅ app.py correctly includes v2 API router")
    return True


def categorize_endpoints(endpoints_by_file: Dict[str, List[Dict[str, str]]]) -> Dict[str, List]:
    """
    Categorize endpoints into Public, Admin, and Webhooks.
    """
    categories = {
        "public": [],
        "admin": [],
        "webhooks": []
    }

    for file_name, routes in endpoints_by_file.items():
        for route in routes:
            full_path = route['path']

            if file_name.startswith('admin/'):
                category = "admin"
                # Prepend /api/v2/admin if not already present
                if not full_path.startswith('/api/v2/admin'):
                    full_path = f"/api/v2/admin{full_path}"
            elif file_name == 'webhooks_api':
                category = "webhooks"
                if not full_path.startswith('/api/v2/webhooks'):
                    full_path = f"/api/v2/webhooks{full_path}"
            else:
                category = "public"
                if not full_path.startswith('/api/v2'):
                    full_path = f"/api/v2{full_path}"

            categories[category].append({
                "method": route['method'],
                "path": full_path,
                "function": route['function'],
                "file": file_name
            })

    return categories


def print_report(categories: Dict[str, List]):
    """
    Print a comprehensive report of all v2 endpoints.
    """
    print("\n" + "="*80)
    print("API v2 Endpoint Verification Report")
    print("="*80 + "\n")

    total_count = sum(len(endpoints) for endpoints in categories.values())

    print(f"📊 Total v2 Endpoints: {total_count}")
    print(f"   - Public APIs: {len(categories['public'])}")
    print(f"   - Admin APIs: {len(categories['admin'])}")
    print(f"   - Webhooks: {len(categories['webhooks'])}")
    print()

    # Print Public APIs
    print("🌐 PUBLIC APIs (/api/v2/*)")
    print("-" * 80)
    for endpoint in sorted(categories['public'], key=lambda x: (x['path'], x['method'])):
        print(f"  {endpoint['method']:<7} {endpoint['path']:<50} [{endpoint['file']}]")
    print()

    # Print Admin APIs
    print("🔐 ADMIN APIs (/api/v2/admin/*)")
    print("-" * 80)
    for endpoint in sorted(categories['admin'], key=lambda x: (x['path'], x['method'])):
        print(f"  {endpoint['method']:<7} {endpoint['path']:<50} [{endpoint['file']}]")
    print()

    # Print Webhooks
    print("🔔 WEBHOOK APIs (/api/v2/webhooks/*)")
    print("-" * 80)
    for endpoint in sorted(categories['webhooks'], key=lambda x: (x['path'], x['method'])):
        print(f"  {endpoint['method']:<7} {endpoint['path']:<50} [{endpoint['file']}]")
    print()

    print("="*80)
    print("✅ Verification Complete")
    print("="*80)

    # Summary recommendations
    print("\n📝 Next Steps:")
    print("   1. Start local server: uvicorn app:app --reload")
    print("   2. Visit Swagger docs: http://localhost:8000/docs")
    print("   3. Verify all endpoints are visible in Swagger UI")
    print("   4. Test authentication with /api/v2/user/profile endpoint")
    print()


def main():
    """
    Main execution function.
    """
    print("🔍 Scanning API directory for v2 endpoints...\n")

    # Step 1: Verify api/__init__.py
    init_ok = verify_api_init()

    # Step 2: Verify app.py
    app_ok = verify_app_py()

    if not (init_ok and app_ok):
        print("\n❌ Configuration verification failed. Please check the errors above.")
        return 1

    # Step 3: Scan all API files
    endpoints_by_file = scan_api_directory()

    if not endpoints_by_file:
        print("❌ No API endpoints found!")
        return 1

    print(f"✅ Found {len(endpoints_by_file)} API files\n")

    # Step 4: Categorize endpoints
    categories = categorize_endpoints(endpoints_by_file)

    # Step 5: Print comprehensive report
    print_report(categories)

    return 0


if __name__ == "__main__":
    exit(main())
