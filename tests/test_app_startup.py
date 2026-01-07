"""
Application Startup Smoke Test.

This test verifies that the application can start without import errors.
It catches issues that would only appear in production deployment.

@module tests.test_app_startup
@version 1.0.0
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_app_imports():
    """Test that main application module imports successfully."""
    try:
        import app
        assert app is not None
    except ImportError as e:
        pytest.fail(f"Failed to import app module: {e}")


def test_api_router_imports():
    """Test that API router imports successfully."""
    try:
        from api import api_router
        assert api_router is not None
    except ImportError as e:
        pytest.fail(f"Failed to import API router: {e}")


def test_container_imports():
    """Test that dependency injection container imports successfully."""
    try:
        from container import get_container
        assert get_container is not None
    except ImportError as e:
        pytest.fail(f"Failed to import container: {e}")


def test_all_domain_imports():
    """Test that all domain modules import successfully."""
    domains = [
        'domains.billing',
        'domains.identity',
        'domains.creation',
        'domains.marketplace',
        'domains.platform',
    ]

    for domain_name in domains:
        try:
            domain = __import__(domain_name, fromlist=[''])
            assert domain is not None, f"{domain_name} imported as None"
        except ImportError as e:
            pytest.fail(f"Failed to import {domain_name}: {e}")


def test_all_application_command_imports():
    """Test that all application command modules import successfully."""
    commands = [
        'application.commands.billing',
        'application.commands.identity',
        'application.commands.creation',
        'application.commands.marketplace',
        'application.commands.platform',
    ]

    for cmd_name in commands:
        try:
            cmd = __import__(cmd_name, fromlist=[''])
            assert cmd is not None, f"{cmd_name} imported as None"
        except ImportError as e:
            pytest.fail(f"Failed to import {cmd_name}: {e}")


def test_all_application_query_imports():
    """Test that all application query modules import successfully."""
    queries = [
        'application.queries.billing',
        'application.queries.identity',
        'application.queries.creation',
        'application.queries.marketplace',
        'application.queries.platform',
    ]

    for query_name in queries:
        try:
            query = __import__(query_name, fromlist=[''])
            assert query is not None, f"{query_name} imported as None"
        except ImportError as e:
            pytest.fail(f"Failed to import {query_name}: {e}")


def test_all_api_routers_import():
    """Test that all API router modules import successfully."""
    routers = [
        'api.billing_api',
        'api.user_api',
        'api.projects_api',
        'api.marketplace_api',
        'api.platform_api',
    ]

    for router_name in routers:
        try:
            router = __import__(router_name, fromlist=[''])
            assert router is not None, f"{router_name} imported as None"
        except ImportError as e:
            pytest.fail(f"Failed to import {router_name}: {e}")


def test_core_exceptions_available():
    """Test that all core exception classes are available."""
    try:
        from core.exceptions import (
            AppException,
            ErrorCode,
            ErrorResponse,
            UnauthorizedException,
            NotFoundException,
            ValidationException,
        )
        assert all([
            AppException,
            ErrorCode,
            ErrorResponse,
            UnauthorizedException,
            NotFoundException,
            ValidationException,
        ])
    except ImportError as e:
        pytest.fail(f"Failed to import core exceptions: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
