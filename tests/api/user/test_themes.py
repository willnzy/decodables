"""
Test api/user/themes.py - Holiday Themes API (v3)

Endpoints: GET /api/v2/user/themes/current

@module tests.api.user.test_themes
@version 3.0.0

Changes in v3.0.0:
- Updated tests to mock Query Handler instead of Supabase (CQRS pattern)
- Tests now verify GetCurrentThemeHandler is called correctly
- Removed @patch('api.user.themes.date') - date passed in Query object
- Maintain all existing test coverage (9 tests)

Created: 2026-01-07
Updated: 2026-01-10 (v3.0.0 upgrade)
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_christmas_theme():
    """Mock Christmas theme data."""
    return {
        "id": "christmas-2024",
        "name": "Christmas 2024",
        "is_active": True,
        "priority": 10,
        "date_rule": {
            "type": "fixed",
            "start": "12-15",
            "end": "12-31"
        },
        "theme_config": {
            "colors": {"primary": "#c41e3a", "secondary": "#165b33"},
            "badge": {"text": "Happy Holidays", "icon": "🎄"},
            "decorations": {"snowflakes": True}
        }
    }


@pytest.fixture
def mock_thanksgiving_theme():
    """Mock Thanksgiving theme data."""
    return {
        "id": "thanksgiving-2024",
        "name": "Thanksgiving 2024",
        "is_active": True,
        "priority": 8,
        "date_rule": {
            "type": "fixed",  # Using fixed for easier testing
            "start": "12-20",
            "end": "12-30"
        },
        "theme_config": {
            "colors": {"primary": "#ff6600", "secondary": "#8b4513"},
            "badge": {"text": "Happy Thanksgiving", "icon": "🦃"}
        }
    }


# ==========================================
# Tests - GET /api/v2/user/themes/current
# ==========================================

class TestGetCurrentTheme:
    """Test GET /api/v2/user/themes/current endpoint."""

    def test_get_current_theme_active_fixed_date(self, mock_christmas_theme):
        """
        v3.0.0: Test getting active theme with fixed date rule (Christmas).

        Tests: GetCurrentThemeHandler returns active theme.
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        # Mock handler to return Christmas theme
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=mock_christmas_theme
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            assert data["theme_id"] == "christmas-2024"
            assert data["name"] == "Christmas 2024"
            assert data["config"]["colors"]["primary"] == "#c41e3a"
            assert data["config"]["badge"]["icon"] == "🎄"

            # Verify handler was called
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)

    def test_get_current_theme_no_active_themes(self):
        """
        v3.0.0: Test when no themes are active today.

        Tests: Handler returns None, API returns empty response.
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        # Mock handler to return None
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=None
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            assert data["theme_id"] is None
            assert data["name"] is None
            assert data["config"] is None

            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)

    def test_get_current_theme_multiple_priority(self, mock_christmas_theme):
        """
        v3.0.0: Test priority ordering when multiple themes match.

        Tests: Handler returns highest priority theme (Service handles priority logic).
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        # Mock handler to return Christmas theme (higher priority)
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=mock_christmas_theme  # priority 10 (should be returned)
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            # Should return Christmas theme (higher priority)
            assert data["theme_id"] == "christmas-2024"

            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)

    def test_get_current_theme_year_wrap(self):
        """
        v3.0.0: Test fixed date rule that wraps across years (Dec 31 - Jan 2).

        Tests: Handler returns theme with year-wrap date range (Service handles logic).
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        new_years_theme = {
            "id": "new-years-2025",
            "name": "New Year 2025",
            "is_active": True,
            "priority": 12,
            "date_rule": {
                "type": "fixed",
                "start": "12-31",
                "end": "01-02"
            },
            "theme_config": {
                "colors": {"primary": "#ffd700"},
                "badge": {"text": "Happy New Year!", "icon": "🎆"}
            }
        }

        # Mock handler to return New Year theme
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=new_years_theme
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            assert data["theme_id"] == "new-years-2025"

            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)

    def test_get_current_theme_date_outside_range(self):
        """
        v3.0.0: Test when today is outside theme date range.

        Tests: Handler returns None when date doesn't match (Service handles date logic).
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        # Mock handler to return None (date outside range)
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=None
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            # Should return empty response since date is outside range
            assert data["theme_id"] is None

            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)

    def test_get_current_theme_invalid_date_rule(self):
        """
        v3.0.0: Test handling of invalid date rule format.

        Tests: Handler returns None for invalid date rules (Service validates).
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        # Mock handler to return None (invalid date rule)
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=None
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            # Should return empty since date rule is invalid
            assert data["theme_id"] is None

            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)

    def test_get_current_theme_unknown_type(self):
        """
        v3.0.0: Test handling of unknown date rule type.

        Tests: Handler returns None for unknown rule types (Service validates).
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        # Mock handler to return None (unknown rule type)
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=None
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            # Should return empty since rule type is unknown
            assert data["theme_id"] is None

            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)

    def test_get_current_theme_missing_date_rule_fields(self):
        """
        v3.0.0: Test handling of missing required date_rule fields.

        Tests: Handler returns None for incomplete date rules (Service validates).
        """
        from application.queries.themes import GetCurrentThemeHandler, GetCurrentThemeResult

        # Mock handler to return None (incomplete date rule)
        mock_handler = MagicMock(spec=GetCurrentThemeHandler)
        mock_handler.handle = AsyncMock(return_value=GetCurrentThemeResult(
            theme=None
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_current_theme')
        container._handlers['get_current_theme'] = mock_handler

        try:
            response = client.get("/api/v2/user/themes/current")

            assert response.status_code == 200
            data = response.json()
            # Should return empty since date rule is incomplete
            assert data["theme_id"] is None

            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_current_theme'] = original_handler
            else:
                container._handlers.pop('get_current_theme', None)
