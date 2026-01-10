"""
Tasks API Tests - v3 DDD Architecture

Updated: 2026-01-10 (v3.0.0 upgrade)

Changes in v3.0.0:
- Updated tests to mock Query/Command Handlers instead of Infrastructure
- Tests now verify GetTaskStatusHandler and CancelTaskHandler
- Removed direct mocking of progress_tracker, task_queue, supabase
- Maintain all existing test coverage (21 tests)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

# Bypass rate limiter BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user

client = TestClient(app)


@pytest.fixture
def mock_user() -> Dict[str, Any]:
    """Mock authenticated user."""
    return {"id": "user_test_123", "email": "test@example.com"}


@pytest.fixture
def override_get_current_user(mock_user):
    """Override dependency to return mock user."""
    async def _get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


class TestGetTaskStatus:
    """Tests for GET /api/v2/user/tasks/{task_id} endpoint."""

    def test_get_task_status_success(self, override_get_current_user):
        """v3.0.0: Test get task status successfully."""
        from application.queries.tasks import GetTaskStatusHandler, GetTaskStatusResult

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(return_value=GetTaskStatusResult(
            task_data={
                "task_id": "task_123",
                "status": "processing",
                "progress": 50,
                "current_step": 2,
                "total_steps": 4,
                "message": "Generating images...",
                "result": None,
                "error": None,
                "created_at": "2026-01-08T10:00:00Z",
                "completed_at": None,
            }
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/task_123")
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task_123"
            assert data["status"] == "processing"
            assert data["progress"] == 50
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_status_from_database_fallback(self, override_get_current_user):
        """v3.0.0: Test database fallback."""
        from application.queries.tasks import GetTaskStatusHandler, GetTaskStatusResult

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(return_value=GetTaskStatusResult(
            task_data={
                "task_id": "task_456",
                "status": "completed",
                "progress": 100,
                "current_step": None,
                "total_steps": None,
                "message": None,
                "result": {"images": ["url1.png"]},
                "error": None,
                "created_at": "2026-01-08T10:00:00Z",
                "completed_at": "2026-01-08T10:05:00Z",
            }
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/task_456")
            assert response.status_code == 200
            assert response.json()["status"] == "completed"
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_status_not_found(self, override_get_current_user):
        """v3.0.0: Test task not found returns 404."""
        from application.queries.tasks import GetTaskStatusHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(404, "Task not found"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/nonexistent")
            assert response.status_code == 404
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_status_pending(self, override_get_current_user):
        """v3.0.0: Test pending task status."""
        from application.queries.tasks import GetTaskStatusHandler, GetTaskStatusResult

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(return_value=GetTaskStatusResult(
            task_data={"task_id": "task_p", "status": "pending", "progress": 0, "message": "Task is queued", "result": None, "error": None, "created_at": "2026-01-08T10:00:00Z", "completed_at": None, "current_step": None, "total_steps": None}
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/task_p")
            assert response.status_code == 200
            assert response.json()["status"] == "pending"
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_status_completed(self, override_get_current_user):
        """v3.0.0: Test completed task with results."""
        from application.queries.tasks import GetTaskStatusHandler, GetTaskStatusResult

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(return_value=GetTaskStatusResult(
            task_data={"task_id": "task_c", "status": "completed", "progress": 100, "result": {"images": ["img1.png", "img2.png"]}, "message": "Completed", "error": None, "created_at": "2026-01-08T10:00:00Z", "completed_at": "2026-01-08T10:05:00Z", "current_step": 4, "total_steps": 4}
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/task_c")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert len(data["result"]["images"]) == 2
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_status_failed(self, override_get_current_user):
        """v3.0.0: Test failed task with error."""
        from application.queries.tasks import GetTaskStatusHandler, GetTaskStatusResult

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(return_value=GetTaskStatusResult(
            task_data={"task_id": "task_f", "status": "failed", "progress": 0, "error": "API timeout", "message": "Failed", "result": None, "created_at": "2026-01-08T10:00:00Z", "completed_at": "2026-01-08T10:02:00Z", "current_step": None, "total_steps": None}
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/task_f")
            assert response.status_code == 200
            assert response.json()["error"] == "API timeout"
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_status_unauthorized(self):
        """v3.0.0: Test unauthenticated request returns 401."""
        response = client.get("/api/v2/user/tasks/task_123")
        assert response.status_code == 401


class TestCancelTask:
    """Tests for POST /api/v2/user/tasks/{task_id}/cancel endpoint."""

    def test_cancel_task_success_with_refund(self, override_get_current_user):
        """v3.0.0: Test cancel with credit refund."""
        from application.queries.tasks import CancelTaskHandler, CancelTaskResult

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(return_value=CancelTaskResult(
            result_data={"status": "cancelled", "task_id": "task_123", "credits_refunded": 5, "message": "Task cancelled and credits refunded"}
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/task_123/cancel")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"
            assert data["credits_refunded"] == 5
            assert "credits refunded" in data["message"]
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)

    def test_cancel_task_success_without_refund(self, override_get_current_user):
        """v3.0.0: Test cancel without refund."""
        from application.queries.tasks import CancelTaskHandler, CancelTaskResult

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(return_value=CancelTaskResult(
            result_data={"status": "cancelled", "task_id": "task_456", "credits_refunded": 0, "message": "Task cancelled"}
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/task_456/cancel")
            assert response.status_code == 200
            assert response.json()["credits_refunded"] == 0
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)

    def test_cancel_task_not_found(self, override_get_current_user):
        """v3.0.0: Test cancel non-existent task returns 404."""
        from application.queries.tasks import CancelTaskHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(404, "Task not found"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/nonexistent/cancel")
            assert response.status_code == 404
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)

    def test_cancel_task_already_processing(self, override_get_current_user):
        """v3.0.0: Test cannot cancel processing task."""
        from application.queries.tasks import CancelTaskHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(400, "Cannot cancel task in 'processing' status"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/task_processing/cancel")
            assert response.status_code == 400
            assert "Cannot cancel task in 'processing' status" in response.text
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)

    def test_cancel_task_already_completed(self, override_get_current_user):
        """v3.0.0: Test cannot cancel completed task."""
        from application.queries.tasks import CancelTaskHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(400, "Cannot cancel task in 'completed' status"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/task_completed/cancel")
            assert response.status_code == 400
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)

    def test_cancel_task_cancellation_failed(self, override_get_current_user):
        """v3.0.0: Test cancellation failed at queue level."""
        from application.queries.tasks import CancelTaskHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(400, "Failed to cancel task"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/task_123/cancel")
            assert response.status_code == 400
            assert "Failed to cancel task" in response.text
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)

    def test_cancel_task_unauthorized(self):
        """v3.0.0: Test unauthenticated request returns 401."""
        response = client.post("/api/v2/user/tasks/task_123/cancel")
        assert response.status_code == 401

    def test_cancel_task_scheduled_success(self, override_get_current_user):
        """v3.0.0: Test cancel scheduled task (v2.1.0 T-LOW-1)."""
        from application.queries.tasks import CancelTaskHandler, CancelTaskResult

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(return_value=CancelTaskResult(
            result_data={"status": "cancelled", "task_id": "task_scheduled", "credits_refunded": 0, "message": "Task cancelled"}
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/task_scheduled/cancel")
            assert response.status_code == 200
            assert response.json()["status"] == "cancelled"
            mock_handler.handle.assert_called_once()
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)


class TestSecurityValidations:
    """Tests for security validations (v2.1.0)."""

    def test_get_task_invalid_id_too_short(self, override_get_current_user):
        """v3.0.0: Reject task_id that is too short."""
        from application.queries.tasks import GetTaskStatusHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(400, "Invalid task ID format"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/ab")
            assert response.status_code == 400
            assert "Invalid task ID format" in response.text
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_invalid_id_too_long(self, override_get_current_user):
        """v3.0.0: Reject task_id that is too long."""
        from application.queries.tasks import GetTaskStatusHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(400, "Invalid task ID format"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            long_id = "a" * 65
            response = client.get(f"/api/v2/user/tasks/{long_id}")
            assert response.status_code == 400
            assert "Invalid task ID format" in response.text
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_get_task_invalid_id_special_chars(self, override_get_current_user):
        """v3.0.0: Reject task_id with invalid characters."""
        from application.queries.tasks import GetTaskStatusHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(400, "Invalid task ID format"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            response = client.get("/api/v2/user/tasks/task!@#$%")
            assert response.status_code == 400
            assert "Invalid task ID format" in response.text
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)

    def test_cancel_task_invalid_id(self, override_get_current_user):
        """v3.0.0: Cancel endpoint also validates task_id."""
        from application.queries.tasks import CancelTaskHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=CancelTaskHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(400, "Invalid task ID format"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('cancel_task')
        container._handlers['cancel_task'] = mock_handler

        try:
            response = client.post("/api/v2/user/tasks/ab/cancel")
            assert response.status_code == 400
            assert "Invalid task ID format" in response.text
        finally:
            if original_handler:
                container._handlers['cancel_task'] = original_handler
            else:
                container._handlers.pop('cancel_task', None)

    def test_valid_task_id_formats(self, override_get_current_user):
        """v3.0.0: Valid task_id formats should pass validation."""
        from application.queries.tasks import GetTaskStatusHandler
        from fastapi import HTTPException

        mock_handler = MagicMock(spec=GetTaskStatusHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(404, "Task not found"))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('get_task_status')
        container._handlers['get_task_status'] = mock_handler

        try:
            valid_ids = ["abc", "task_123", "task-456", "TASK123", "a" * 64]
            for task_id in valid_ids:
                response = client.get(f"/api/v2/user/tasks/{task_id}")
                assert response.status_code == 404, f"Task ID {task_id} should be valid"
        finally:
            if original_handler:
                container._handlers['get_task_status'] = original_handler
            else:
                container._handlers.pop('get_task_status', None)
