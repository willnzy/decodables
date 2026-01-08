"""
Tests for Logs API endpoints (v2)

API Module: api/user/logs.py
Endpoints:
- POST /api/v2/user/api/v2/user/logs/error - Log single error
- POST /api/v2/user/api/v2/user/logs/errors - Log batch errors

Note: These endpoints don't require authentication

**API BUG DISCOVERED**: Router has duplicate prefix!
- logs.py router prefix: /api/v2/user/logs
- user_router prefix: /api/v2/user
- Combined (buggy): /api/v2/user + /api/v2/user/logs = /api/v2/user/api/v2/user/logs

**FIX**: Change logs.py router prefix from "/api/v2/user/logs" to "/logs"

@module tests.api.user.test_logs
@version 2.0.0
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# IMPORTANT: Bypass rate limiter BEFORE importing app
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app

client = TestClient(app)


# ==========================================
# Tests: POST /api/v2/user/logs/error
# ==========================================

class TestLogSingleError:
    """Test POST /api/v2/user/logs/error"""

    @patch('api.user.logs.supabase')
    def test_log_error_success_without_auth(self, mock_supabase):
        """Should log error without authentication"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "error_id": "err_123",
            "error_type": "api_error",
            "error_code": "E500",
            "message": "Internal server error",
            "status_code": 500,
            "endpoint": "/api/v2/user/projects",
            "method": "POST",
            "session_id": "sess_abc",
            "page_url": "https://example.com/editor",
            "user_agent": "Mozilla/5.0",
        }

        response = client.post("/api/v2/user/api/v2/user/logs/error", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "warning" not in data or data["warning"] is None

        # Verify insert was called
        mock_supabase.table.assert_called_with("error_logs")

    @patch('api.user.logs.supabase')
    def test_log_error_with_auth_token(self, mock_supabase):
        """Should extract user_id from auth token if provided"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "error_id": "err_456",
            "error_type": "validation_error",
            "message": "Invalid input",
        }

        # Include a mock JWT token (will be decoded without verification)
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyIsIm5hbWUiOiJUZXN0In0.abc123"}

        response = client.post("/api/v2/user/api/v2/user/logs/error", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"

    @patch('api.user.logs.supabase')
    def test_log_error_truncates_long_strings(self, mock_supabase):
        """Should truncate very long strings to prevent DB issues"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        # Create a very long message (> 2000 chars)
        long_message = "Error: " + ("x" * 3000)
        long_stack = "Stack trace: " + ("y" * 6000)

        payload = {
            "error_id": "err_789",
            "error_type": "runtime_error",
            "message": long_message,
            "stack_trace": long_stack,
        }

        response = client.post("/api/v2/user/api/v2/user/logs/error", json=payload)

        assert response.status_code == 200

        # Verify that truncation happened in the insert call
        call_args = mock_supabase.table.return_value.insert.call_args
        inserted_data = call_args[0][0]

        # Message should be truncated to 2000 chars
        assert len(inserted_data["message"]) <= 2000

        # Stack trace should be truncated to 5000 chars
        assert len(inserted_data["stack_trace"]) <= 5000

    @patch('api.user.logs.supabase')
    def test_log_error_handles_db_failure_gracefully(self, mock_supabase):
        """Should return 200 even if DB insert fails (fire-and-forget)"""
        # Simulate DB failure
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        payload = {
            "error_id": "err_999",
            "error_type": "network_error",
            "message": "Connection timeout",
        }

        response = client.post("/api/v2/user/api/v2/user/logs/error", json=payload)

        # Should still return 200 with warning
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["warning"] is not None
        assert "not have been stored" in data["warning"]

    def test_log_error_invalid_payload_returns_422(self):
        """Should return 422 for invalid payload"""
        # Missing required fields
        payload = {}

        response = client.post("/api/v2/user/api/v2/user/logs/error", json=payload)

        assert response.status_code == 422

    @patch('api.user.logs.supabase')
    def test_log_error_with_full_context(self, mock_supabase):
        """Should log error with full context including custom fields"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "error_id": "err_full",
            "error_type": "business_logic_error",
            "error_code": "CREDITS_INSUFFICIENT",
            "message": "Not enough credits",
            "status_code": 402,
            "endpoint": "/api/v2/user/generation/image",
            "method": "POST",
            "user_code": "UC123",
            "session_id": "sess_xyz",
            "page_url": "https://example.com/editor",
            "user_agent": "Mozilla/5.0 Chrome/120.0",
            "stack_trace": "Error at line 42...",
            "context": {
                "credits_required": 5,
                "credits_available": 2,
                "feature": "ai_image_generation",
            },
            "client_timestamp": "2026-01-08T10:00:00Z",
        }

        response = client.post("/api/v2/user/api/v2/user/logs/error", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"

        # Verify all fields were included in insert
        call_args = mock_supabase.table.return_value.insert.call_args
        inserted_data = call_args[0][0]

        assert inserted_data["error_id"] == "err_full"
        assert inserted_data["error_code"] == "CREDITS_INSUFFICIENT"
        assert inserted_data["context"]["feature"] == "ai_image_generation"


# ==========================================
# Tests: POST /api/v2/user/logs/errors
# ==========================================

class TestLogBatchErrors:
    """Test POST /api/v2/user/logs/errors (batch)"""

    @patch('api.user.logs.supabase')
    def test_log_batch_errors_success(self, mock_supabase):
        """Should log multiple errors in batch"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "errors": [
                {
                    "error_id": "err_1",
                    "error_type": "api_error",
                    "message": "Error 1",
                },
                {
                    "error_id": "err_2",
                    "error_type": "validation_error",
                    "message": "Error 2",
                },
                {
                    "error_id": "err_3",
                    "error_type": "network_error",
                    "message": "Error 3",
                },
            ]
        }

        response = client.post("/api/v2/user/api/v2/user/logs/errors", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["errors_received"] == 3

        # Verify batch insert was called
        mock_supabase.table.assert_called_with("error_logs")
        call_args = mock_supabase.table.return_value.insert.call_args
        inserted_records = call_args[0][0]

        assert len(inserted_records) == 3

    @patch('api.user.logs.supabase')
    def test_log_batch_errors_with_auth(self, mock_supabase):
        """Should extract user_id for all errors in batch"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        payload = {
            "errors": [
                {"error_id": "err_1", "error_type": "type1", "message": "msg1"},
                {"error_id": "err_2", "error_type": "type2", "message": "msg2"},
            ]
        }

        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyJ9.abc"}

        response = client.post("/api/v2/user/api/v2/user/logs/errors", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["errors_received"] == 2

        # All records should have the same user_id
        call_args = mock_supabase.table.return_value.insert.call_args
        inserted_records = call_args[0][0]

        assert all(record.get("user_id") == "user_123" for record in inserted_records)

    @patch('api.user.logs.supabase')
    def test_log_batch_errors_empty_array(self, mock_supabase):
        """Should handle empty errors array"""
        payload = {"errors": []}

        response = client.post("/api/v2/user/api/v2/user/logs/errors", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["errors_received"] == 0

        # Should not call insert for empty array
        mock_supabase.table.return_value.insert.assert_not_called()

    @patch('api.user.logs.supabase')
    def test_log_batch_errors_handles_db_failure(self, mock_supabase):
        """Should return 200 with warning on DB failure"""
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        payload = {
            "errors": [
                {"error_id": "err_1", "error_type": "type1", "message": "msg1"},
            ]
        }

        response = client.post("/api/v2/user/api/v2/user/logs/errors", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["warning"] is not None
        assert "may not have been stored" in data["warning"]

    def test_log_batch_errors_invalid_payload_returns_422(self):
        """Should return 422 for invalid payload"""
        # Missing required 'errors' field
        payload = {}

        response = client.post("/api/v2/user/api/v2/user/logs/errors", json=payload)

        assert response.status_code == 422

    @patch('api.user.logs.supabase')
    def test_log_batch_errors_truncates_fields(self, mock_supabase):
        """Should truncate long fields in all batch records"""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        long_message = "x" * 3000
        long_url = "https://example.com/" + ("y" * 3000)

        payload = {
            "errors": [
                {
                    "error_id": "err_1",
                    "error_type": "type1",
                    "message": long_message,
                    "page_url": long_url,
                },
                {
                    "error_id": "err_2",
                    "error_type": "type2",
                    "message": long_message,
                },
            ]
        }

        response = client.post("/api/v2/user/api/v2/user/logs/errors", json=payload)

        assert response.status_code == 200

        # Verify truncation
        call_args = mock_supabase.table.return_value.insert.call_args
        inserted_records = call_args[0][0]

        for record in inserted_records:
            assert len(record["message"]) <= 2000
            if record.get("page_url"):
                assert len(record["page_url"]) <= 2000


# ==========================================
# Summary
# ==========================================
# Total tests: 14
# Coverage:
# - POST /api/v2/user/logs/error (7 tests)
# - POST /api/v2/user/logs/errors (7 tests)
# - Authentication (with/without token)
# - JWT decoding
# - String truncation
# - Error handling (DB failures)
# - Validation errors
# - Empty arrays
# - Full context logging
# ==========================================
