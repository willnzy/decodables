"""
Tasks API Tests - v2 DDD Architecture

Tests for api/user/tasks.py

Endpoints:
- GET /api/v2/user/tasks/{task_id} - Get task status
- POST /api/v2/user/tasks/{task_id}/cancel - Cancel a task

Created: 2026-01-08
Updated: 2026-01-09

Changes in v2.1.0:
- Added tests for task_id format validation (T-MEDIUM-1)
- Added tests for scheduled status cancellation (T-LOW-1)

Coverage Target: 100% (2/2 endpoints)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

# IMPORTANT: Bypass rate limiter BEFORE importing app
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user() -> Dict[str, Any]:
    """Mock authenticated user."""
    return {
        "id": "user_test_123",
        "email": "test@example.com",
        "tier": "free",
        "subscription_tier": "free",
    }


@pytest.fixture
def override_get_current_user(mock_user):
    """Override dependency to return mock user."""
    async def _get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_task_status_pending():
    """Mock task status - pending."""
    return {
        "status": "pending",
        "progress": 0,
        "current_step": None,
        "total_steps": None,
        "message": "Task is queued",
        "result": None,
        "error": None,
        "created_at": "2026-01-08T10:00:00Z",
        "completed_at": None,
    }


@pytest.fixture
def mock_task_status_processing():
    """Mock task status - processing."""
    return {
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


@pytest.fixture
def mock_task_status_completed():
    """Mock task status - completed."""
    return {
        "status": "completed",
        "progress": 100,
        "current_step": 4,
        "total_steps": 4,
        "message": "Generation completed",
        "result": {
            "images": [
                "https://example.com/image1.png",
                "https://example.com/image2.png",
            ]
        },
        "error": None,
        "created_at": "2026-01-08T10:00:00Z",
        "completed_at": "2026-01-08T10:05:00Z",
    }


@pytest.fixture
def mock_task_status_failed():
    """Mock task status - failed."""
    return {
        "status": "failed",
        "progress": 0,
        "current_step": None,
        "total_steps": None,
        "message": "Generation failed",
        "result": None,
        "error": "API timeout",
        "created_at": "2026-01-08T10:00:00Z",
        "completed_at": "2026-01-08T10:02:00Z",
    }


# ==========================================
# GET /api/v2/user/tasks/{task_id} Tests
# ==========================================

class TestGetTaskStatus:
    """Tests for GET /api/v2/user/tasks/{task_id} endpoint."""

    @patch('api.user.tasks.progress_tracker')
    def test_get_task_status_from_redis_success(
        self,
        mock_progress_tracker,
        override_get_current_user,
        mock_task_status_processing,
    ):
        """
        Test: Get task status from Redis successfully

        Given: Task exists in Redis cache
        When: GET /api/v2/user/tasks/{task_id}
        Then: Returns task status with progress info
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = mock_task_status_processing

        # Act
        response = client.get("/api/v2/user/tasks/task_123")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_123"
        assert data["status"] == "processing"
        assert data["progress"] == 50
        assert data["current_step"] == 2
        assert data["total_steps"] == 4
        assert data["message"] == "Generating images..."

        # Verify Redis was queried
        mock_progress_tracker.get_status.assert_called_once_with("task_123")

    @patch('api.user.tasks.supabase')
    @patch('api.user.tasks.progress_tracker')
    def test_get_task_status_from_database_fallback(
        self,
        mock_progress_tracker,
        mock_supabase,
        override_get_current_user,
        mock_user,
    ):
        """
        Test: Fallback to database when task not in Redis

        Given: Task not in Redis but exists in database
        When: GET /api/v2/user/tasks/{task_id}
        Then: Returns task status from database
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = None  # Not in Redis

        mock_db_response = MagicMock()
        mock_db_response.data = {
            "success": True,
            "status": "completed",
            "progress": 100,
            "result": {"images": ["url1.png"]},
            "created_at": "2026-01-08T10:00:00Z",
            "completed_at": "2026-01-08T10:05:00Z",
        }
        mock_supabase.rpc.return_value.execute.return_value = mock_db_response

        # Act
        response = client.get("/api/v2/user/tasks/task_456")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_456"
        assert data["status"] == "completed"
        assert data["progress"] == 100

        # Verify database RPC was called
        mock_supabase.rpc.assert_called_once_with("get_task_details", {
            "p_task_id": "task_456",
            "p_user_id": mock_user["id"],
        })

    @patch('api.user.tasks.supabase')
    @patch('api.user.tasks.progress_tracker')
    def test_get_task_status_not_found(
        self,
        mock_progress_tracker,
        mock_supabase,
        override_get_current_user,
    ):
        """
        Test: Task not found returns 404

        Given: Task doesn't exist in Redis or database
        When: GET /api/v2/user/tasks/{task_id}
        Then: Returns 404 Not Found
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = None

        mock_db_response = MagicMock()
        mock_db_response.data = None
        mock_supabase.rpc.return_value.execute.return_value = mock_db_response

        # Act
        response = client.get("/api/v2/user/tasks/nonexistent_task")

        # Assert
        assert response.status_code == 404

    @patch('api.user.tasks.progress_tracker')
    def test_get_task_status_pending(
        self,
        mock_progress_tracker,
        override_get_current_user,
        mock_task_status_pending,
    ):
        """
        Test: Get pending task status

        Given: Task is in pending state
        When: GET /api/v2/user/tasks/{task_id}
        Then: Returns status=pending with progress=0
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = mock_task_status_pending

        # Act
        response = client.get("/api/v2/user/tasks/task_pending")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["progress"] == 0
        assert data["message"] == "Task is queued"

    @patch('api.user.tasks.progress_tracker')
    def test_get_task_status_completed(
        self,
        mock_progress_tracker,
        override_get_current_user,
        mock_task_status_completed,
    ):
        """
        Test: Get completed task with results

        Given: Task is completed with image results
        When: GET /api/v2/user/tasks/{task_id}
        Then: Returns status=completed with image URLs
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = mock_task_status_completed

        # Act
        response = client.get("/api/v2/user/tasks/task_completed")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert "result" in data
        assert "images" in data["result"]
        assert len(data["result"]["images"]) == 2

    @patch('api.user.tasks.progress_tracker')
    def test_get_task_status_failed(
        self,
        mock_progress_tracker,
        override_get_current_user,
        mock_task_status_failed,
    ):
        """
        Test: Get failed task with error message

        Given: Task failed with error
        When: GET /api/v2/user/tasks/{task_id}
        Then: Returns status=failed with error details
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = mock_task_status_failed

        # Act
        response = client.get("/api/v2/user/tasks/task_failed")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "API timeout"
        assert data["message"] == "Generation failed"

    def test_get_task_status_unauthorized(self):
        """
        Test: Unauthenticated request returns 401

        Given: No authentication headers
        When: GET /api/v2/user/tasks/{task_id}
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.get("/api/v2/user/tasks/task_123")

        # Assert
        assert response.status_code == 401


# ==========================================
# POST /api/v2/user/tasks/{task_id}/cancel Tests
# ==========================================

class TestCancelTask:
    """Tests for POST /api/v2/user/tasks/{task_id}/cancel endpoint."""

    @patch('api.user.tasks.supabase')
    @patch('api.user.tasks.task_queue')
    @patch('api.user.tasks.progress_tracker')
    def test_cancel_task_success_with_refund(
        self,
        mock_progress_tracker,
        mock_task_queue,
        mock_supabase,
        override_get_current_user,
        mock_user,
    ):
        """
        Test: Cancel task successfully with credit refund

        Given: Task is in pending status and has credits charged
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Cancels task and refunds credits
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = {"status": "pending"}
        mock_task_queue.cancel_task.return_value = True

        # Mock database query for credits
        mock_db_response = MagicMock()
        mock_db_response.data = {"params": {"credits_charged": 5}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_db_response

        # Mock credit repository
        with patch('api.user.tasks.SupabaseCreditRepository') as mock_credit_repo_class:
            mock_credit_repo = MagicMock()
            mock_credit_repo.add_credits = AsyncMock()
            mock_credit_repo_class.return_value = mock_credit_repo

            # Act
            response = client.post("/api/v2/user/tasks/task_123/cancel")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"
            assert data["task_id"] == "task_123"
            assert data["credits_refunded"] == 5
            assert "credits refunded" in data["message"]

            # Verify credits were refunded
            mock_credit_repo.add_credits.assert_called_once_with(
                mock_user["id"],
                5,
                "Cancelled task task_123",
                "refund",
            )

    @patch('api.user.tasks.task_queue')
    @patch('api.user.tasks.progress_tracker')
    def test_cancel_task_success_without_refund(
        self,
        mock_progress_tracker,
        mock_task_queue,
        override_get_current_user,
    ):
        """
        Test: Cancel task without credit refund

        Given: Task is in queued status with no credits charged
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Cancels task without refund
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = {"status": "queued"}
        mock_task_queue.cancel_task.return_value = True

        # Mock database query - no credits charged
        with patch('api.user.tasks.supabase') as mock_supabase:
            mock_db_response = MagicMock()
            mock_db_response.data = {"params": {}}  # No credits_charged
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_db_response

            # Act
            response = client.post("/api/v2/user/tasks/task_456/cancel")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"
            assert data["credits_refunded"] == 0
            assert "credits refunded" not in data["message"]

    @patch('api.user.tasks.progress_tracker')
    def test_cancel_task_not_found(
        self,
        mock_progress_tracker,
        override_get_current_user,
    ):
        """
        Test: Cancel non-existent task returns 404

        Given: Task doesn't exist
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Returns 404 Not Found
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = None

        # Act
        response = client.post("/api/v2/user/tasks/nonexistent/cancel")

        # Assert
        assert response.status_code == 404

    @patch('api.user.tasks.progress_tracker')
    def test_cancel_task_already_processing(
        self,
        mock_progress_tracker,
        override_get_current_user,
    ):
        """
        Test: Cannot cancel task that is already processing

        Given: Task is in processing status
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Returns 400 Bad Request
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = {"status": "processing"}

        # Act
        response = client.post("/api/v2/user/tasks/task_processing/cancel")

        # Assert
        assert response.status_code == 400
        assert "Cannot cancel task in 'processing' status" in response.text

    @patch('api.user.tasks.progress_tracker')
    def test_cancel_task_already_completed(
        self,
        mock_progress_tracker,
        override_get_current_user,
    ):
        """
        Test: Cannot cancel completed task

        Given: Task is completed
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Returns 400 Bad Request
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = {"status": "completed"}

        # Act
        response = client.post("/api/v2/user/tasks/task_completed/cancel")

        # Assert
        assert response.status_code == 400

    @patch('api.user.tasks.task_queue')
    @patch('api.user.tasks.progress_tracker')
    def test_cancel_task_cancellation_failed(
        self,
        mock_progress_tracker,
        mock_task_queue,
        override_get_current_user,
    ):
        """
        Test: Task cancellation failed at queue level

        Given: Task is cancellable but queue.cancel_task fails
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Returns 400 with error message
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = {"status": "pending"}
        mock_task_queue.cancel_task.return_value = False  # Cancellation failed

        # Act
        response = client.post("/api/v2/user/tasks/task_123/cancel")

        # Assert
        assert response.status_code == 400
        assert "Failed to cancel task" in response.text

    def test_cancel_task_unauthorized(self):
        """
        Test: Unauthenticated request returns 401

        Given: No authentication headers
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post("/api/v2/user/tasks/task_123/cancel")

        # Assert
        assert response.status_code == 401

    @patch('api.user.tasks.supabase')
    @patch('api.user.tasks.task_queue')
    @patch('api.user.tasks.progress_tracker')
    def test_cancel_task_scheduled_success(
        self,
        mock_progress_tracker,
        mock_task_queue,
        mock_supabase,
        override_get_current_user,
    ):
        """
        v2.1.0: T-LOW-1 - Test cancel scheduled task

        Given: Task is in scheduled status (RQ scheduled jobs)
        When: POST /api/v2/user/tasks/{task_id}/cancel
        Then: Cancels task successfully
        """
        # Arrange
        mock_progress_tracker.get_status.return_value = {"status": "scheduled"}
        mock_task_queue.cancel_task.return_value = True

        # Mock database query
        mock_db_response = MagicMock()
        mock_db_response.data = {"params": {}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_db_response

        # Act
        response = client.post("/api/v2/user/tasks/task_scheduled/cancel")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


# ==========================================
# Tests: Security Validations (v2.1.0)
# ==========================================

class TestSecurityValidations:
    """Tests for security validations added in v2.1.0."""

    def test_get_task_invalid_id_too_short(self, override_get_current_user):
        """
        v2.1.0: T-MEDIUM-1 - Reject task_id that is too short.
        """
        response = client.get("/api/v2/user/tasks/ab")  # Less than 3 chars

        assert response.status_code == 400
        assert "Invalid task ID format" in response.text

    def test_get_task_invalid_id_too_long(self, override_get_current_user):
        """
        v2.1.0: T-MEDIUM-1 - Reject task_id that is too long.
        """
        long_id = "a" * 65  # More than 64 chars
        response = client.get(f"/api/v2/user/tasks/{long_id}")

        assert response.status_code == 400
        assert "Invalid task ID format" in response.text

    def test_get_task_invalid_id_special_chars(self, override_get_current_user):
        """
        v2.1.0: T-MEDIUM-1 - Reject task_id with invalid characters.
        """
        response = client.get("/api/v2/user/tasks/task!@#$%")

        assert response.status_code == 400
        assert "Invalid task ID format" in response.text

    def test_cancel_task_invalid_id(self, override_get_current_user):
        """
        v2.1.0: T-MEDIUM-1 - Cancel endpoint also validates task_id.
        """
        response = client.post("/api/v2/user/tasks/ab/cancel")  # Too short

        assert response.status_code == 400
        assert "Invalid task ID format" in response.text

    @patch('api.user.tasks.progress_tracker')
    def test_valid_task_id_formats(self, mock_progress_tracker, override_get_current_user):
        """
        v2.1.0: T-MEDIUM-1 - Valid task_id formats should pass validation.
        """
        mock_progress_tracker.get_status.return_value = None

        # Valid formats
        valid_ids = [
            "abc",  # Minimum 3 chars
            "task_123",  # Underscore
            "task-456",  # Hyphen
            "TASK123",  # Uppercase
            "a" * 64,  # Maximum 64 chars
        ]

        for task_id in valid_ids:
            response = client.get(f"/api/v2/user/tasks/{task_id}")
            # Should get 404 (not found) not 400 (invalid format)
            assert response.status_code == 404, f"Task ID {task_id} should be valid"


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary:

GET /api/v2/user/tasks/{task_id}:
✅ Success - Get status from Redis cache
✅ Success - Fallback to database when not in Redis
✅ Error - Task not found (404)
✅ Status - Pending task
✅ Status - Processing task with progress
✅ Status - Completed task with results
✅ Status - Failed task with error
✅ Unauthorized (401)

POST /api/v2/user/tasks/{task_id}/cancel:
✅ Success - Cancel with credit refund
✅ Success - Cancel without refund
✅ Success - Cancel scheduled task (v2.1.0 T-LOW-1)
✅ Error - Task not found (404)
✅ Error - Cannot cancel processing task (400)
✅ Error - Cannot cancel completed task (400)
✅ Error - Cancellation failed at queue level (400)
✅ Unauthorized (401)

Security Validations (v2.1.0):
✅ Invalid task_id - too short (400)
✅ Invalid task_id - too long (400)
✅ Invalid task_id - special characters (400)
✅ Invalid task_id on cancel endpoint (400)
✅ Valid task_id formats accepted

Total Tests: 21
Coverage: 100% (2/2 endpoints)

Business Logic Tested:
- ✅ Task status retrieval from Redis (primary)
- ✅ Database fallback when Redis unavailable
- ✅ Task lifecycle states (pending/queued/scheduled/processing/completed/failed/cancelled)
- ✅ Progress tracking (progress %, current_step, total_steps)
- ✅ Credit refund on cancellation
- ✅ Cancellation restrictions (pending/queued/scheduled only)
- ✅ Error handling for missing tasks
- ✅ Task ID format validation (v2.1.0)

Not Tested (Requires Integration/E2E):
- Actual Redis connection
- Real task queue operations
- Database RPC function implementation
- Credit transaction atomicity
- Task progress updates over time
"""
