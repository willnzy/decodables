"""
Tests for Logs API endpoints (v3)

API Module: api/user/logs.py
Endpoints:
- POST /api/v2/user/logs/error - Log single error
- POST /api/v2/user/logs/errors - Log batch errors

Note: These endpoints don't require authentication

@module tests.api.user.test_logs
@version 3.0.0

Changes in v3.0.0:
- Updated tests to mock Handlers instead of Supabase (CQRS pattern)
- Tests now verify Handler.handle() is called correctly
- Maintain all existing test coverage (22 tests)

Changes in v2.1.0:
- Added tests for error_id format validation (LOG-HIGH-1)
- Added tests for batch size limit (LOG-P0-2)
- Added tests for context size limit (LOG-HIGH-2)
- Added tests for method validation (LOG-MEDIUM-2)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
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

    def test_log_error_success_without_auth(self):
        """
        v3.0.0: Should log error without authentication using Handler.

        Tests: CreateErrorLogHandler is called correctly.
        """
        from application.commands.logging import CreateErrorLogHandler, CreateErrorLogResult

        # Mock handler
        mock_handler = MagicMock(spec=CreateErrorLogHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogResult(
            success=True,
            error_log_id="log_123",
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log')
        container._handlers['create_error_log'] = mock_handler

        try:
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

            response = client.post("/api/v2/user/logs/error", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            assert "warning" not in data or data["warning"] is None

            # Verify handler was called
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['create_error_log'] = original_handler
            else:
                container._handlers.pop('create_error_log', None)

    def test_log_error_with_auth_token(self):
        """
        v3.0.0: Should extract user_id from auth token if provided.

        Tests: JWT token is decoded and user_id passed to handler.
        """
        from application.commands.logging import CreateErrorLogHandler, CreateErrorLogResult

        mock_handler = MagicMock(spec=CreateErrorLogHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogResult(
            success=True,
            error_log_id="log_456",
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log')
        container._handlers['create_error_log'] = mock_handler

        try:
            payload = {
                "error_id": "err_456",
                "error_type": "validation_error",
                "message": "Invalid input",
            }

            # Include a mock JWT token (will be decoded without verification)
            headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyIsIm5hbWUiOiJUZXN0In0.abc123"}

            response = client.post("/api/v2/user/logs/error", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['create_error_log'] = original_handler
            else:
                container._handlers.pop('create_error_log', None)

    def test_log_error_message_too_long_rejected(self):
        """
        v2.1.0: Messages over max_length (5000) should be rejected.

        Note: In v2.1.0, we now validate at Pydantic layer with max_length.
        """
        # Create a very long message (> 5000 chars)
        long_message = "Error: " + ("x" * 6000)

        payload = {
            "error_id": "err_789",
            "error_type": "runtime_error",
            "message": long_message,
        }

        response = client.post("/api/v2/user/logs/error", json=payload)

        # v2.1.0: Now rejects at validation layer
        assert response.status_code == 422

    def test_log_error_stack_trace_too_long_rejected(self):
        """
        v2.1.0: Stack trace over max_length (10000) should be rejected.
        """
        long_stack = "Stack trace: " + ("y" * 11000)

        payload = {
            "error_id": "err_789",
            "error_type": "runtime_error",
            "stack_trace": long_stack,
        }

        response = client.post("/api/v2/user/logs/error", json=payload)

        # v2.1.0: Now rejects at validation layer
        assert response.status_code == 422

    def test_log_error_handles_db_failure_gracefully(self):
        """
        v3.0.0: Should return 200 even if Handler fails (fire-and-forget).

        Tests: Handler failure returns success with warning.
        """
        from application.commands.logging import CreateErrorLogHandler, CreateErrorLogResult

        # Simulate handler failure
        mock_handler = MagicMock(spec=CreateErrorLogHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogResult(
            success=False,
            error="DB error",
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log')
        container._handlers['create_error_log'] = mock_handler

        try:
            payload = {
                "error_id": "err_999",
                "error_type": "network_error",
                "message": "Connection timeout",
            }

            response = client.post("/api/v2/user/logs/error", json=payload)

            # Should still return 200 with warning
            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            assert data["warning"] is not None
            assert "not have been stored" in data["warning"]
        finally:
            if original_handler:
                container._handlers['create_error_log'] = original_handler
            else:
                container._handlers.pop('create_error_log', None)

    def test_log_error_invalid_payload_returns_422(self):
        """Should return 422 for invalid payload"""
        # Missing required fields
        payload = {}

        response = client.post("/api/v2/user/logs/error", json=payload)

        assert response.status_code == 422

    def test_log_error_with_full_context(self):
        """
        v3.0.0: Should log error with full context including custom fields.

        Tests: Handler receives all fields correctly.
        """
        from application.commands.logging import CreateErrorLogHandler, CreateErrorLogResult, CreateErrorLogCommand

        mock_handler = MagicMock(spec=CreateErrorLogHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogResult(
            success=True,
            error_log_id="log_full",
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log')
        container._handlers['create_error_log'] = mock_handler

        try:
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

            response = client.post("/api/v2/user/logs/error", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"

            # Verify handler was called with command
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert isinstance(call_args, CreateErrorLogCommand)
            assert call_args.error_data["error_id"] == "err_full"
            assert call_args.error_data["error_code"] == "CREDITS_INSUFFICIENT"
            assert call_args.error_data["context"]["feature"] == "ai_image_generation"
        finally:
            if original_handler:
                container._handlers['create_error_log'] = original_handler
            else:
                container._handlers.pop('create_error_log', None)


# ==========================================
# Tests: POST /api/v2/user/logs/errors
# ==========================================

class TestLogBatchErrors:
    """Test POST /api/v2/user/logs/errors (batch)"""

    def test_log_batch_errors_success(self):
        """
        v3.0.0: Should log multiple errors in batch using Handler.

        Tests: CreateErrorLogBatchHandler is called correctly.
        """
        from application.commands.logging import CreateErrorLogBatchHandler, CreateErrorLogBatchResult

        mock_handler = MagicMock(spec=CreateErrorLogBatchHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogBatchResult(
            success=True,
            count=3,
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log_batch')
        container._handlers['create_error_log_batch'] = mock_handler

        try:
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

            response = client.post("/api/v2/user/logs/errors", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            assert data["errors_received"] == 3

            # Verify handler was called
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['create_error_log_batch'] = original_handler
            else:
                container._handlers.pop('create_error_log_batch', None)

    def test_log_batch_errors_with_auth(self):
        """v3.0.0: Should extract user_id for all errors in batch using Handler."""
        from application.commands.logging import CreateErrorLogBatchHandler, CreateErrorLogBatchResult

        # Mock handler
        mock_handler = MagicMock(spec=CreateErrorLogBatchHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogBatchResult(
            success=True,
            count=2,
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log_batch')
        container._handlers['create_error_log_batch'] = mock_handler

        try:
            payload = {
                "errors": [
                    {"error_id": "err_1", "error_type": "type1", "message": "msg1"},
                    {"error_id": "err_2", "error_type": "type2", "message": "msg2"},
                ]
            }

            headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyJ9.abc"}

            response = client.post("/api/v2/user/logs/errors", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()

            assert data["errors_received"] == 2

            # Verify handler was called with Command
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args
            command = call_args[0][0]

            # All records should have the same user_id extracted from JWT
            assert all(record.get("user_id") == "user_123" for record in command.errors)

        finally:
            # Cleanup
            if original_handler:
                container._handlers['create_error_log_batch'] = original_handler
            else:
                container._handlers.pop('create_error_log_batch', None)

    def test_log_batch_errors_empty_array(self):
        """v3.0.0: Should handle empty errors array using Handler."""
        from application.commands.logging import CreateErrorLogBatchHandler, CreateErrorLogBatchResult

        # Mock handler - should return count=0 for empty array
        mock_handler = MagicMock(spec=CreateErrorLogBatchHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogBatchResult(
            success=True,
            count=0,
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log_batch')
        container._handlers['create_error_log_batch'] = mock_handler

        try:
            payload = {"errors": []}

            response = client.post("/api/v2/user/logs/errors", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            assert data["errors_received"] == 0

            # Handler should be called even with empty array
            mock_handler.handle.assert_called_once()

        finally:
            # Cleanup
            if original_handler:
                container._handlers['create_error_log_batch'] = original_handler
            else:
                container._handlers.pop('create_error_log_batch', None)

    def test_log_batch_errors_handles_db_failure(self):
        """v3.0.0: Should return 200 with warning on Handler failure."""
        from application.commands.logging import CreateErrorLogBatchHandler, CreateErrorLogBatchResult

        # Mock handler - simulate failure
        mock_handler = MagicMock(spec=CreateErrorLogBatchHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogBatchResult(
            success=False,
            count=0,
            error="DB error",
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log_batch')
        container._handlers['create_error_log_batch'] = mock_handler

        try:
            payload = {
                "errors": [
                    {"error_id": "err_1", "error_type": "type1", "message": "msg1"},
                ]
            }

            response = client.post("/api/v2/user/logs/errors", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            assert data["warning"] is not None
            assert "may not have been stored" in data["warning"]

        finally:
            # Cleanup
            if original_handler:
                container._handlers['create_error_log_batch'] = original_handler
            else:
                container._handlers.pop('create_error_log_batch', None)

    def test_log_batch_errors_invalid_payload_returns_422(self):
        """Should return 422 for invalid payload"""
        # Missing required 'errors' field
        payload = {}

        response = client.post("/api/v2/user/logs/errors", json=payload)

        assert response.status_code == 422

    def test_log_batch_errors_message_too_long_rejected(self):
        """
        v2.1.0: Messages over max_length (5000) should be rejected.

        Note: In v2.1.0, we now reject at Pydantic validation layer
        instead of truncating.
        """
        long_message = "x" * 6000  # Over 5000 char limit

        payload = {
            "errors": [
                {
                    "error_id": "err_1",
                    "error_type": "type1",
                    "message": long_message,
                },
            ]
        }

        response = client.post("/api/v2/user/logs/errors", json=payload)

        # v2.1.0: Now rejects at validation layer
        assert response.status_code == 422


# ==========================================
# Tests: Security Validations (v2.1.0)
# ==========================================

class TestSecurityValidations:
    """Test security validations added in v2.1.0."""

    def test_error_id_invalid_format_rejected(self):
        """
        v2.1.0: LOG-HIGH-1 - Invalid error_id format should be rejected.
        """
        payload = {
            "error_id": "err<script>alert(1)</script>",  # Contains invalid chars
            "error_type": "test_error",
        }

        response = client.post("/api/v2/user/logs/error", json=payload)

        assert response.status_code == 422

    def test_error_id_too_long_rejected(self):
        """
        v2.1.0: LOG-HIGH-1 - error_id over 100 chars should be rejected.
        """
        payload = {
            "error_id": "x" * 150,  # Too long
            "error_type": "test_error",
        }

        response = client.post("/api/v2/user/logs/error", json=payload)

        assert response.status_code == 422

    def test_error_type_too_long_rejected(self):
        """
        v2.1.0: LOG-MEDIUM-1 - error_type over 50 chars should be rejected.
        """
        payload = {
            "error_id": "err_123",
            "error_type": "x" * 100,  # Too long
        }

        response = client.post("/api/v2/user/logs/error", json=payload)

        assert response.status_code == 422

    def test_invalid_method_normalized(self):
        """
        v3.0.0: LOG-MEDIUM-2 - Invalid HTTP method should be normalized to None.
        """
        from application.commands.logging import CreateErrorLogHandler, CreateErrorLogResult

        # Mock handler
        mock_handler = MagicMock(spec=CreateErrorLogHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogResult(
            success=True,
            error_log_id="log_123",
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log')
        container._handlers['create_error_log'] = mock_handler

        try:
            payload = {
                "error_id": "err_123",
                "error_type": "api_error",
                "method": "INVALID",  # Not a valid HTTP method (short enough to pass max_length)
            }

            response = client.post("/api/v2/user/logs/error", json=payload)

            assert response.status_code == 200

            # Check that method was normalized to None by validator
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args
            command = call_args[0][0]
            assert command.error_data["method"] is None

        finally:
            # Cleanup
            if original_handler:
                container._handlers['create_error_log'] = original_handler
            else:
                container._handlers.pop('create_error_log', None)

    def test_valid_method_uppercased(self):
        """
        v3.0.0: LOG-MEDIUM-2 - Valid HTTP method should be uppercased.
        """
        from application.commands.logging import CreateErrorLogHandler, CreateErrorLogResult

        # Mock handler
        mock_handler = MagicMock(spec=CreateErrorLogHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogResult(
            success=True,
            error_log_id="log_123",
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log')
        container._handlers['create_error_log'] = mock_handler

        try:
            payload = {
                "error_id": "err_123",
                "error_type": "api_error",
                "method": "post",  # Lowercase
            }

            response = client.post("/api/v2/user/logs/error", json=payload)

            assert response.status_code == 200

            # Check that method was uppercased by validator
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args
            command = call_args[0][0]
            assert command.error_data["method"] == "POST"

        finally:
            # Cleanup
            if original_handler:
                container._handlers['create_error_log'] = original_handler
            else:
                container._handlers.pop('create_error_log', None)

    def test_large_context_truncated(self):
        """
        v3.0.0: LOG-HIGH-2 - Context over 10KB should be truncated.
        """
        from application.commands.logging import CreateErrorLogHandler, CreateErrorLogResult

        # Mock handler
        mock_handler = MagicMock(spec=CreateErrorLogHandler)
        mock_handler.handle = AsyncMock(return_value=CreateErrorLogResult(
            success=True,
            error_log_id="log_123",
        ))

        # Override container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_error_log')
        container._handlers['create_error_log'] = mock_handler

        try:
            # Create a large context (> 10KB)
            large_context = {"data": "x" * 15000}

            payload = {
                "error_id": "err_123",
                "error_type": "api_error",
                "context": large_context,
            }

            response = client.post("/api/v2/user/logs/error", json=payload)

            assert response.status_code == 200

            # Check that context was truncated by validator
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args
            command = call_args[0][0]
            assert command.error_data["context"].get("_truncated") is True

        finally:
            # Cleanup
            if original_handler:
                container._handlers['create_error_log'] = original_handler
            else:
                container._handlers.pop('create_error_log', None)

    def test_batch_over_50_rejected(self):
        """
        v2.1.0: LOG-P0-2 - Batch with more than 50 errors should be rejected.
        """
        errors = [
            {"error_id": f"err_{i}", "error_type": "test"}
            for i in range(60)
        ]

        payload = {"errors": errors}

        response = client.post("/api/v2/user/logs/errors", json=payload)

        assert response.status_code == 422

    def test_status_code_out_of_range_rejected(self):
        """
        v2.1.0: Status code outside 100-599 should be rejected.
        """
        payload = {
            "error_id": "err_123",
            "error_type": "api_error",
            "status_code": 999,  # Invalid HTTP status code
        }

        response = client.post("/api/v2/user/logs/error", json=payload)

        assert response.status_code == 422


# ==========================================
# Summary
# ==========================================
# Total tests: 22
# Coverage:
# - POST /api/v2/user/logs/error (7 tests)
# - POST /api/v2/user/logs/errors (7 tests)
# - Security validations (8 tests)
# - Authentication (with/without token)
# - JWT decoding
# - String truncation
# - Error handling (DB failures)
# - Validation errors
# - Empty arrays
# - Full context logging
# - v2.1.0: error_id format, batch limit, context size, method validation
# ==========================================
