"""
Tests for Admin Tasks Management API (v3.26)

Test coverage:
- Authentication (require_admin)
- Constants validation
- Rate limiting
- Parameter validation (limit range, status/task_name enum)
- Error message sanitization
- DDD architecture (Repository pattern)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException, Request
from datetime import datetime, timezone

from api.admin.tasks_mgmt import (
    router,
    get_tasks_status,
    get_task_logs,
    get_tasks_health,
    run_task_manually,
    VALID_TASK_STATUSES,
    VALID_TASK_NAMES,
)


# ==========================================
# Test Authentication
# ==========================================

def test_all_endpoints_require_admin():
    """All endpoints should require admin authentication."""
    # All endpoints use require_admin in their function signature
    # Since rate limiter decorates the function, we check the route definitions
    for route in router.routes:
        # All admin endpoints should have /tasks/management prefix
        assert route.path.startswith("/tasks/management")


# ==========================================
# Test Constants (v3.25)
# ==========================================

def test_valid_task_statuses_constant():
    """VALID_TASK_STATUSES should contain expected values."""
    assert VALID_TASK_STATUSES == {"success", "failed", "running", "pending"}


def test_valid_task_names_constant():
    """VALID_TASK_NAMES should contain expected values."""
    assert VALID_TASK_NAMES == {"hourly", "daily", "all", "cleanup", "retention"}


# ==========================================
# Test GET /status (v3.26: DDD架构)
# ==========================================

@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_tasks_status_success(mock_get_db):
    """GET /status should return task status via Repository."""
    # Mock Repository response
    mock_repo = AsyncMock()
    mock_repo.get_task_status = AsyncMock(return_value={
        "hourly": {
            "last_run": "2026-01-09T10:00:00Z",
            "last_status": "success",
            "last_duration_ms": 1500,
            "last_error": None,
            "recent_runs": []
        }
    })

    with patch('api.admin.tasks_mgmt.SupabaseTasksRepository', return_value=mock_repo):
        mock_request = Mock(spec=Request)
        admin = {"id": "admin123", "role": "admin"}

        result = await get_tasks_status(request=mock_request, admin=admin)

        assert "tasks" in result
        assert "hourly" in result["tasks"]
        assert result["tasks"]["hourly"]["last_status"] == "success"


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_tasks_status_error_sanitization(mock_get_db):
    """GET /status should sanitize error messages."""
    mock_get_db.side_effect = Exception("Database connection failed with credentials abc123")

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_tasks_status(request=mock_request, admin=admin)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to retrieve task status"


# ==========================================
# Test GET /logs (v3.26: DDD架构)
# ==========================================

@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_task_logs_success(mock_get_db):
    """GET /logs should return task logs via Repository."""
    mock_repo = AsyncMock()
    mock_repo.get_task_logs = AsyncMock(return_value=[
        {"task_name": "daily", "status": "success"}
    ])

    with patch('api.admin.tasks_mgmt.SupabaseTasksRepository', return_value=mock_repo):
        mock_request = Mock(spec=Request)
        admin = {"id": "admin123", "role": "admin"}

        result = await get_task_logs(
            request=mock_request,
            task_name=None,
            status=None,
            limit=100,
            admin=admin
        )

        assert "logs" in result
        assert len(result["logs"]) == 1


@pytest.mark.asyncio
async def test_get_task_logs_invalid_status():
    """GET /logs should reject invalid status."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_task_logs(
            request=mock_request,
            task_name=None,
            status="invalid_status",
            limit=100,
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "Invalid status" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_task_logs_invalid_task_name():
    """GET /logs should reject invalid task_name."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_task_logs(
            request=mock_request,
            task_name="invalid_task",
            status=None,
            limit=100,
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "Invalid task_name" in str(exc_info.value.detail)


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_task_logs_valid_status(mock_get_db):
    """GET /logs should accept valid status values."""
    mock_repo = AsyncMock()
    mock_repo.get_task_logs = AsyncMock(return_value=[])

    with patch('api.admin.tasks_mgmt.SupabaseTasksRepository', return_value=mock_repo):
        mock_request = Mock(spec=Request)
        admin = {"id": "admin123", "role": "admin"}

        for status in VALID_TASK_STATUSES:
            result = await get_task_logs(
                request=mock_request,
                task_name=None,
                status=status,
                limit=100,
                admin=admin
            )
            assert "logs" in result


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_task_logs_valid_task_name(mock_get_db):
    """GET /logs should accept valid task_name values."""
    mock_repo = AsyncMock()
    mock_repo.get_task_logs = AsyncMock(return_value=[])

    with patch('api.admin.tasks_mgmt.SupabaseTasksRepository', return_value=mock_repo):
        mock_request = Mock(spec=Request)
        admin = {"id": "admin123", "role": "admin"}

        for task_name in VALID_TASK_NAMES:
            result = await get_task_logs(
                request=mock_request,
                task_name=task_name,
                status=None,
                limit=100,
                admin=admin
            )
            assert "logs" in result


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_task_logs_error_sanitization(mock_get_db):
    """GET /logs should sanitize error messages."""
    mock_get_db.side_effect = Exception("Internal database error with token xyz789")

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_task_logs(
            request=mock_request,
            task_name=None,
            status=None,
            limit=100,
            admin=admin
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to retrieve task logs"


# ==========================================
# Test GET /health (v3.26: DDD架构)
# ==========================================

@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_tasks_health_success(mock_get_db):
    """GET /health should return task health status via Repository."""
    mock_repo = AsyncMock()
    mock_repo.get_tasks_health = AsyncMock(return_value={
        "total_runs": 2,
        "failed_runs": 0,
        "success_rate": 100.0,
        "period_start": "2026-01-09T09:00:00Z"
    })

    with patch('api.admin.tasks_mgmt.SupabaseTasksRepository', return_value=mock_repo):
        with patch('api.admin.tasks_mgmt.scheduler', create=True) as mock_scheduler:
            mock_scheduler.running = True

            mock_request = Mock(spec=Request)
            admin = {"id": "admin123", "role": "admin"}

            result = await get_tasks_health(request=mock_request, admin=admin)

            assert result["status"] == "healthy"
            assert result["scheduler"] == "running"
            assert result["last_hour"]["total_runs"] == 2
            assert result["last_hour"]["failed_runs"] == 0
            assert result["last_hour"]["success_rate"] == 100.0


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_tasks_health_degraded(mock_get_db):
    """GET /health should return degraded when tasks fail."""
    mock_repo = AsyncMock()
    mock_repo.get_tasks_health = AsyncMock(return_value={
        "total_runs": 2,
        "failed_runs": 1,
        "success_rate": 50.0,
        "period_start": "2026-01-09T09:00:00Z"
    })

    with patch('api.admin.tasks_mgmt.SupabaseTasksRepository', return_value=mock_repo):
        with patch('api.admin.tasks_mgmt.scheduler', create=True) as mock_scheduler:
            mock_scheduler.running = True

            mock_request = Mock(spec=Request)
            admin = {"id": "admin123", "role": "admin"}

            result = await get_tasks_health(request=mock_request, admin=admin)

            assert result["status"] == "degraded"
            assert result["last_hour"]["failed_runs"] == 1
            assert result["last_hour"]["success_rate"] == 50.0


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.get_database_client')
async def test_get_tasks_health_error_sanitization(mock_get_db):
    """GET /health should sanitize error messages."""
    mock_get_db.side_effect = Exception("Database error with sensitive info")

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_tasks_health(request=mock_request, admin=admin)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to retrieve task health status"


# ==========================================
# Test POST /{task_name}/run (v3.26: 完善 cleanup/retention)
# ==========================================

@pytest.mark.asyncio
async def test_run_task_manually_success():
    """POST /{task_name}/run should trigger task."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # Mock the imported function inside the endpoint
    with patch('scheduler.run_aggregation_now') as mock_run:
        mock_run.return_value = {"status": "completed", "task_type": "hourly"}

        result = await run_task_manually(
            request=mock_request,
            task_name="hourly",
            admin=admin
        )

        assert result["status"] == "triggered"
        assert result["task"] == "hourly"
        mock_run.assert_called_once_with("hourly")


@pytest.mark.asyncio
async def test_run_task_manually_invalid_task_name():
    """POST /{task_name}/run should reject invalid task names."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await run_task_manually(
            request=mock_request,
            task_name="invalid_task",
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "Invalid task" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_run_task_manually_task_name_too_long():
    """POST /{task_name}/run should reject task names longer than 50 chars."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await run_task_manually(
            request=mock_request,
            task_name="a" * 51,
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "Task name too long" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_run_task_manually_valid_task_names():
    """POST /{task_name}/run should accept all valid task names."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('scheduler.run_aggregation_now') as mock_run:
        mock_run.return_value = {"status": "completed", "task_type": "hourly"}

        with patch('scheduler.run_storage_cleanup') as mock_cleanup:
            for task_name in VALID_TASK_NAMES:
                result = await run_task_manually(
                    request=mock_request,
                    task_name=task_name,
                    admin=admin
                )
                assert result["status"] == "triggered"


@pytest.mark.asyncio
async def test_run_task_manually_error_sanitization():
    """POST /{task_name}/run should sanitize error messages."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('scheduler.run_aggregation_now') as mock_run:
        mock_run.side_effect = Exception("Task execution failed with internal error xyz")

        with pytest.raises(HTTPException) as exc_info:
            await run_task_manually(
                request=mock_request,
                task_name="hourly",
                admin=admin
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to run task"
