"""
Tests for Analytics API endpoints (v2)

API Module: api/user/analytics.py
Endpoints:
- POST /api/v2/user/analytics/events - Log analytics events (batch)

@module tests.api.user.test_analytics
@version 2.1.0

Changes in v2.1.0:
- Updated tests for batch INSERT optimization
- Removed SupabaseAdminStatsRepository mock (now uses direct supabase batch insert)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# IMPORTANT: Bypass rate limiter BEFORE importing app
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user_optional

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_free_user():
    """Mock free tier user"""
    return {
        "id": "user_free_123",
        "email": "free@test.com",
        "tier": "free",
        "subscription_status": None,
        "credits_monthly": 0,
        "credits_permanent": 50,
    }


@pytest.fixture
def mock_request_with_headers(mocker):
    """Mock FastAPI Request with headers"""
    request = MagicMock()
    request.headers.get = MagicMock(side_effect=lambda key, default="unknown": {
        "CF-Connecting-IP": "203.0.113.1",
        "CF-IPCountry": "US",
        "CF-IPCity": "San Francisco",
        "CF-IPRegion": "CA",
        "CF-IPTimezone": "America/Los_Angeles",
        "User-Agent": "Mozilla/5.0 Test",
        "Accept-Language": "en-US,en;q=0.9",
    }.get(key, default))
    request.client = MagicMock(host="203.0.113.1")
    return request


@pytest.fixture
def override_get_current_user_optional_free(mock_free_user):
    """Override dependency to return free user"""
    async def _get_current_user_optional():
        return mock_free_user
    app.dependency_overrides[get_current_user_optional] = _get_current_user_optional
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_get_current_user_optional_none():
    """Override dependency to return None (anonymous)"""
    async def _get_current_user_optional():
        return None
    app.dependency_overrides[get_current_user_optional] = _get_current_user_optional
    yield
    app.dependency_overrides.clear()


# ==========================================
# Tests: POST /api/v2/user/analytics/events
# ==========================================

class TestLogAnalyticsEvents:
    """Test POST /api/v2/user/analytics/events"""

    @patch('api.user.analytics.supabase')
    def test_log_single_event_success(
        self,
        mock_supabase,
        override_get_current_user_optional_free,
    ):
        """Should successfully log a single analytics event via batch insert"""
        # Mock batch insert for all tables
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "events": [
                {
                    "event_type": "page_view",
                    "event_id": "evt_123",
                    "event_level": "info",
                    "timestamp": "2026-01-08T10:00:00Z",
                    "session_id": "sess_abc",
                    "properties": {"page": "/editor"},
                    "env": {"browser": "Chrome", "os": "macOS"},
                    "user_properties": {"user_tier": "free"},
                }
            ]
        }

        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["count"] == 1
        assert data["ip"] is not None
        assert data["country"] is not None

        # Verify batch insert was called for user_events and analytics_events
        assert mock_supabase.table.call_count >= 2

    @patch('api.user.analytics.supabase')
    def test_log_batch_events_success(
        self,
        mock_supabase,
        override_get_current_user_optional_free,
    ):
        """Should successfully log multiple analytics events via batch insert"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "events": [
                {
                    "event_type": "page_view",
                    "properties": {},
                    "env": {},
                    "user_properties": {},
                },
                {
                    "event_type": "button_click",
                    "properties": {"button_id": "submit"},
                    "env": {},
                    "user_properties": {},
                },
                {
                    "event_type": "form_submit",
                    "properties": {"form_id": "contact"},
                    "env": {},
                    "user_properties": {},
                },
            ]
        }

        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["count"] == 3

        # Verify batch insert was called (not individual inserts)
        # Should be 2 calls: user_events and analytics_events (no activity_logs for these events)
        insert_calls = mock_supabase.table.return_value.insert.call_args_list
        assert len(insert_calls) == 2

        # Verify each insert received a list of 3 rows
        for call in insert_calls:
            rows = call[0][0]  # First positional argument
            assert isinstance(rows, list)
            assert len(rows) == 3

    @patch('api.user.analytics.supabase')
    def test_log_event_as_anonymous_user(
        self,
        mock_supabase,
        override_get_current_user_optional_none,
    ):
        """Should log events for anonymous users (no authentication required)"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "events": [
                {
                    "event_type": "page_view",
                    "properties": {"page": "/landing"},
                    "env": {},
                    "user_properties": {},
                }
            ]
        }

        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["count"] == 1

        # Verify user_id is None in the inserted rows
        insert_calls = mock_supabase.table.return_value.insert.call_args_list
        for call in insert_calls:
            rows = call[0][0]
            assert rows[0]["user_id"] is None

    @patch('api.user.analytics.supabase')
    def test_log_activity_mirroring_for_project_events(
        self,
        mock_supabase,
        override_get_current_user_optional_free,
    ):
        """Should mirror certain events to activity_logs via batch insert"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        # Test events that should be mirrored to activity_logs
        mirrored_events = [
            "project_print",
            "project_export_pdf",
            "project_export_zip",
            "project_preview",
            "project_delete",
            "project_create_complete",
        ]

        payload = {
            "events": [
                {
                    "event_type": event_type,
                    "properties": {"project_id": "proj_123"},
                    "env": {},
                    "user_properties": {},
                }
                for event_type in mirrored_events
            ]
        }

        response = client.post("/api/v2/user/analytics/events", json=payload)
        assert response.status_code == 200

        # Verify activity_logs batch insert was called
        table_calls = [call[0][0] for call in mock_supabase.table.call_args_list]
        assert "activity_logs" in table_calls

        # Find the activity_logs insert call
        for i, table_name in enumerate(table_calls):
            if table_name == "activity_logs":
                insert_call = mock_supabase.table.return_value.insert.call_args_list[i]
                activity_rows = insert_call[0][0]
                assert len(activity_rows) == len(mirrored_events)
                break

    @patch('api.user.analytics.supabase')
    def test_enriches_with_server_side_info(
        self,
        mock_supabase,
        override_get_current_user_optional_free,
    ):
        """Should enrich events with server-side IP, geo, and device info"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "events": [
                {
                    "event_type": "page_view",
                    "properties": {},
                    "env": {"browser": "Chrome", "os": "macOS"},
                    "user_properties": {},
                }
            ]
        }

        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 200

        # Find user_events insert and verify enriched properties
        insert_calls = mock_supabase.table.return_value.insert.call_args_list
        user_events_rows = insert_calls[0][0][0]  # First table insert, first arg, first row

        enriched_props = user_events_rows[0]["properties"]

        # Should have server-side info
        assert "server_ip" in enriched_props
        assert "server_country" in enriched_props
        assert "server_user_agent" in enriched_props

        # Should have client-side info
        assert enriched_props["client_browser"] == "Chrome"
        assert enriched_props["client_os"] == "macOS"

    def test_invalid_payload_returns_422(self):
        """Should return 422 for invalid request payload"""
        # Missing required field 'events'
        payload = {}

        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 422

    def test_empty_events_array(
        self,
        override_get_current_user_optional_free,
    ):
        """Should handle empty events array"""
        payload = {"events": []}

        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["count"] == 0

    @patch('api.user.analytics.supabase')
    def test_handles_batch_insert_failure(
        self,
        mock_supabase,
        override_get_current_user_optional_free,
    ):
        """Should gracefully handle batch insert failures"""
        # Simulate batch insert failure for all tables
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        payload = {
            "events": [
                {
                    "event_type": "page_view",
                    "properties": {},
                    "env": {},
                    "user_properties": {},
                }
            ]
        }

        # Should still return 200 (fire-and-forget logging)
        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestBatchInsertOptimization:
    """Test batch INSERT optimization (v2.1.0)"""

    @patch('api.user.analytics.supabase')
    def test_batch_insert_reduces_db_calls(
        self,
        mock_supabase,
        override_get_current_user_optional_free,
    ):
        """
        Should use batch INSERT to reduce DB calls.
        10 events → 2-3 DB calls (instead of 30)
        """
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        # Send 10 events
        payload = {
            "events": [
                {
                    "event_type": f"event_{i}",
                    "properties": {"index": i},
                    "env": {},
                    "user_properties": {},
                }
                for i in range(10)
            ]
        }

        response = client.post("/api/v2/user/analytics/events", json=payload)

        assert response.status_code == 200
        assert response.json()["count"] == 10

        # Verify only 2 batch inserts (user_events + analytics_events)
        # Not 20+ individual inserts
        insert_calls = mock_supabase.table.return_value.insert.call_args_list
        assert len(insert_calls) == 2

        # Each batch should contain 10 rows
        for call in insert_calls:
            rows = call[0][0]
            assert len(rows) == 10

    @patch('api.user.analytics.supabase')
    def test_partial_batch_failure_isolation(
        self,
        mock_supabase,
        override_get_current_user_optional_free,
    ):
        """
        Should isolate failures between different table batches.
        If user_events batch fails, analytics_events should still be attempted.
        """
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("user_events batch failed")
            return MagicMock()

        mock_supabase.table.return_value.insert.return_value.execute.side_effect = side_effect

        payload = {
            "events": [
                {"event_type": "test", "properties": {}, "env": {}, "user_properties": {}}
            ]
        }

        response = client.post("/api/v2/user/analytics/events", json=payload)

        # Should still return 200
        assert response.status_code == 200

        # Should have attempted both batches
        assert call_count[0] >= 2


# ==========================================
# Summary
# ==========================================
# Total tests: 10
# Coverage:
# - POST /api/v2/user/analytics/events (all scenarios)
# - Authentication (authenticated + anonymous)
# - Batch INSERT optimization (v2.1.0)
# - Activity mirroring
# - Server-side enrichment
# - Error handling (partial failure isolation)
# ==========================================
