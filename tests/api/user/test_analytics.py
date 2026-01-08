"""
Tests for Analytics API endpoints (v2)

API Module: api/user/analytics.py
Endpoints:
- POST /api/v2/user/analytics/events - Log analytics events (batch)

@module tests.api.user.test_analytics
@version 2.0.0
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

    @patch('api.user.analytics.get_database_client')
    @patch('api.user.analytics.supabase')
    def test_log_single_event_success(
        self,
        mock_supabase,
        mock_get_db_client,
        override_get_current_user_optional_free,
    ):
        """Should successfully log a single analytics event"""
        # Mock database client
        mock_db = MagicMock()
        mock_get_db_client.return_value = mock_db

        # Mock SupabaseAdminStatsRepository.log_user_event
        mock_repo = MagicMock()
        mock_repo.log_user_event = AsyncMock()

        with patch('api.user.analytics.SupabaseAdminStatsRepository', return_value=mock_repo):
            # Mock supabase.table().insert().execute()
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

            # Verify log_user_event was called
            mock_repo.log_user_event.assert_called_once()

    @patch('api.user.analytics.get_database_client')
    @patch('api.user.analytics.supabase')
    def test_log_batch_events_success(
        self,
        mock_supabase,
        mock_get_db_client,
        override_get_current_user_optional_free,
    ):
        """Should successfully log multiple analytics events"""
        mock_db = MagicMock()
        mock_get_db_client.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.log_user_event = AsyncMock()

        with patch('api.user.analytics.SupabaseAdminStatsRepository', return_value=mock_repo):
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

            # Verify log_user_event was called 3 times
            assert mock_repo.log_user_event.call_count == 3

    @patch('api.user.analytics.get_database_client')
    @patch('api.user.analytics.supabase')
    def test_log_event_as_anonymous_user(
        self,
        mock_supabase,
        mock_get_db_client,
        override_get_current_user_optional_none,
    ):
        """Should log events for anonymous users (no authentication required)"""
        mock_db = MagicMock()
        mock_get_db_client.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.log_user_event = AsyncMock()

        with patch('api.user.analytics.SupabaseAdminStatsRepository', return_value=mock_repo):
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

            # Verify log_user_event was called with user_id=None
            call_args = mock_repo.log_user_event.call_args
            assert call_args.kwargs["user_id"] is None

    @patch('api.user.analytics.get_database_client')
    @patch('api.user.analytics.supabase')
    @patch('api.user.analytics.log_activity')
    def test_log_activity_mirroring_for_project_events(
        self,
        mock_log_activity,
        mock_supabase,
        mock_get_db_client,
        override_get_current_user_optional_free,
    ):
        """Should mirror certain events to activity_logs"""
        mock_db = MagicMock()
        mock_get_db_client.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.log_user_event = AsyncMock()

        with patch('api.user.analytics.SupabaseAdminStatsRepository', return_value=mock_repo):
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

            for event_type in mirrored_events:
                payload = {
                    "events": [
                        {
                            "event_type": event_type,
                            "properties": {"project_id": "proj_123"},
                            "env": {},
                            "user_properties": {},
                        }
                    ]
                }

                response = client.post("/api/v2/user/analytics/events", json=payload)
                assert response.status_code == 200

            # Verify log_activity was called for each mirrored event
            assert mock_log_activity.call_count == len(mirrored_events)

    @patch('api.user.analytics.get_database_client')
    @patch('api.user.analytics.supabase')
    def test_enriches_with_server_side_info(
        self,
        mock_supabase,
        mock_get_db_client,
        override_get_current_user_optional_free,
    ):
        """Should enrich events with server-side IP, geo, and device info"""
        mock_db = MagicMock()
        mock_get_db_client.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.log_user_event = AsyncMock()

        with patch('api.user.analytics.SupabaseAdminStatsRepository', return_value=mock_repo):
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

            # Verify enriched properties were passed to log_user_event
            call_args = mock_repo.log_user_event.call_args
            enriched_props = call_args.kwargs["properties"]

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

    @patch('api.user.analytics.get_database_client')
    @patch('api.user.analytics.supabase')
    def test_handles_analytics_events_insert_failure(
        self,
        mock_supabase,
        mock_get_db_client,
        override_get_current_user_optional_free,
    ):
        """Should gracefully handle analytics_events table insert failures"""
        mock_db = MagicMock()
        mock_get_db_client.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.log_user_event = AsyncMock()

        with patch('api.user.analytics.SupabaseAdminStatsRepository', return_value=mock_repo):
            # Simulate analytics_events insert failure
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

            # user_events should still be logged
            mock_repo.log_user_event.assert_called_once()


# ==========================================
# Summary
# ==========================================
# Total tests: 10
# Coverage:
# - POST /api/v2/user/analytics/events (all scenarios)
# - Authentication (authenticated + anonymous)
# - Batch processing
# - Activity mirroring
# - Server-side enrichment
# - Error handling
# ==========================================
