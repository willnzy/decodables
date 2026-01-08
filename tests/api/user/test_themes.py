"""
Test api/user/themes.py - Holiday Themes API

Endpoints: GET /api/v2/user/themes/current

Created: 2026-01-07
Updated: 2026-01-08 (Complete rewrite with 9 comprehensive tests)
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock
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

    @patch('api.user.themes.date')
    @patch('api.user.themes.supabase')
    def test_get_current_theme_active_fixed_date(self, mock_supabase, mock_date, mock_christmas_theme):
        """Test getting active theme with fixed date rule (Christmas)."""
        # Mock today's date to be during Christmas period
        mock_date.today.return_value = date(2024, 12, 25)
        # Make date() constructor still work for helper functions
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw) if args else None

        # Mock Supabase response
        mock_result = MagicMock()
        mock_result.data = [mock_christmas_theme]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        assert data["theme_id"] == "christmas-2024"
        assert data["name"] == "Christmas 2024"
        assert data["config"]["colors"]["primary"] == "#c41e3a"
        assert data["config"]["badge"]["icon"] == "🎄"

    @patch('api.user.themes.supabase')
    def test_get_current_theme_no_active_themes(self, mock_supabase):
        """Test when no themes are active today."""
        # Mock Supabase with no data
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        assert data["theme_id"] is None
        assert data["name"] is None
        assert data["config"] is None

    @patch('api.user.themes.date')
    @patch('api.user.themes.supabase')
    def test_get_current_theme_multiple_priority(self, mock_supabase, mock_date, mock_christmas_theme, mock_thanksgiving_theme):
        """Test priority ordering when multiple themes match."""
        # Mock date to be during both themes' active period
        mock_date.today.return_value = date(2024, 12, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw) if args else None

        # Mock both themes active but Christmas has higher priority (10 vs 8)
        mock_result = MagicMock()
        mock_result.data = [
            mock_christmas_theme,  # priority 10 (should be returned)
            mock_thanksgiving_theme  # priority 8
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        # Should return Christmas theme (higher priority)
        assert data["theme_id"] == "christmas-2024"

    @patch('api.user.themes.date')
    @patch('api.user.themes.supabase')
    def test_get_current_theme_year_wrap(self, mock_supabase, mock_date):
        """Test fixed date rule that wraps across years (Dec 31 - Jan 2)."""
        # Mock date to Jan 1st
        mock_date.today.return_value = date(2025, 1, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw) if args else None

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

        mock_result = MagicMock()
        mock_result.data = [new_years_theme]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        assert data["theme_id"] == "new-years-2025"

    @patch('api.user.themes.date')
    @patch('api.user.themes.supabase')
    def test_get_current_theme_date_outside_range(self, mock_supabase, mock_date, mock_christmas_theme):
        """Test when today is outside theme date range."""
        # Mock date to be in summer (outside Christmas range)
        mock_date.today.return_value = date(2024, 7, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw) if args else None

        mock_result = MagicMock()
        mock_result.data = [mock_christmas_theme]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        # Should return empty response since date is outside range
        assert data["theme_id"] is None

    @patch('api.user.themes.supabase')
    def test_get_current_theme_invalid_date_rule(self, mock_supabase):
        """Test handling of invalid date rule format."""
        invalid_theme = {
            "id": "invalid-theme",
            "name": "Invalid Theme",
            "is_active": True,
            "priority": 5,
            "date_rule": {
                "type": "fixed",
                "start": "invalid",
                "end": "also-invalid"
            },
            "theme_config": {}
        }

        mock_result = MagicMock()
        mock_result.data = [invalid_theme]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        # Should return empty since date rule is invalid
        assert data["theme_id"] is None

    @patch('api.user.themes.supabase')
    def test_get_current_theme_unknown_type(self, mock_supabase):
        """Test handling of unknown date rule type."""
        unknown_type_theme = {
            "id": "unknown-type",
            "name": "Unknown Type Theme",
            "is_active": True,
            "priority": 5,
            "date_rule": {
                "type": "unknown_type"
            },
            "theme_config": {}
        }

        mock_result = MagicMock()
        mock_result.data = [unknown_type_theme]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        # Should return empty since rule type is unknown
        assert data["theme_id"] is None

    @patch('api.user.themes.supabase')
    def test_get_current_theme_missing_date_rule_fields(self, mock_supabase):
        """Test handling of missing required date_rule fields."""
        incomplete_theme = {
            "id": "incomplete-theme",
            "name": "Incomplete Theme",
            "is_active": True,
            "priority": 5,
            "date_rule": {
                "type": "fixed"
                # Missing "start" and "end"
            },
            "theme_config": {}
        }

        mock_result = MagicMock()
        mock_result.data = [incomplete_theme]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/themes/current")

        assert response.status_code == 200
        data = response.json()
        # Should return empty since date rule is incomplete
        assert data["theme_id"] is None
