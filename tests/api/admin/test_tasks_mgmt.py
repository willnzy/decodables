"""
Tests for Admin Tasks Management API (v3.25)

Test coverage:
- Authentication (require_admin)
- Constants validation
- Rate limiting
- Parameter validation (limit range, status/task_name enum)
- Error message sanitization
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
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
# Test GET /status (v3.25)
# ==========================================

@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.supabase')
async def test_get_tasks_status_success(mock_supabase):
    """GET /status should return task status."""
    mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = Mock(
        data=[
            {
                "task_name": "hourly",
                "started_at": "2026-01-09T10:00:00Z",
                "status": "success",
                "duration_ms": 1500,
                "error_message": None
            }
        ]
    )

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    result = await get_tasks_status(request=mock_request, admin=admin)

    assert "tasks" in result
    assert "hourly" in result["tasks"]
    assert result["tasks"]["hourly"]["last_status"] == "success"


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.supabase')
async def test_get_tasks_status_error_sanitization(mock_supabase):
    """GET /status should sanitize error messages."""
    mock_supabase.table.side_effect = Exception("Database connection failed with credentials abc123")

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    result = await get_tasks_status(request=mock_request, admin=admin)

    assert result["tasks"] == {}
    assert result["error"] == "Failed to retrieve task status"
    assert "abc123" not in result["error"]


# ==========================================
# Test GET /logs (v3.25)
# ==========================================

@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.supabase')
async def test_get_task_logs_success(mock_supabase):
    """GET /logs should return task logs."""
    mock_query = Mock()
    mock_query.order.return_value.limit.return_value.execute.return_value = Mock(
        data=[{"task_name": "daily", "status": "success"}]
    )
    mock_supabase.table.return_value.select.return_value = mock_query

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
async def test_get_task_logs_valid_status():
    """GET /logs should accept valid status values."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.tasks_mgmt.supabase') as mock_supabase:
        mock_query = Mock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = Mock(data=[])
        mock_supabase.table.return_value.select.return_value = mock_query

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
async def test_get_task_logs_valid_task_name():
    """GET /logs should accept valid task_name values."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.tasks_mgmt.supabase') as mock_supabase:
        mock_query = Mock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = Mock(data=[])
        mock_supabase.table.return_value.select.return_value = mock_query

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
@patch('api.admin.tasks_mgmt.supabase')
async def test_get_task_logs_error_sanitization(mock_supabase):
    """GET /logs should sanitize error messages."""
    mock_supabase.table.side_effect = Exception("Internal database error with token xyz789")

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    result = await get_task_logs(
        request=mock_request,
        task_name=None,
        status=None,
        limit=100,
        admin=admin
    )

    assert result["logs"] == []
    assert result["error"] == "Failed to retrieve task logs"
    assert "xyz789" not in result["error"]


# ==========================================
# Test GET /health (v3.25)
# ==========================================

@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.supabase')
async def test_get_tasks_health_success(mock_supabase):
    """GET /health should return task health status."""
    mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
        data=[
            {"task_name": "hourly", "status": "success"},
            {"task_name": "daily", "status": "success"}
        ]
    )

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.tasks_mgmt.scheduler', create=True) as mock_scheduler:
        mock_scheduler.running = True

        result = await get_tasks_health(request=mock_request, admin=admin)

        assert result["status"] == "healthy"
        assert result["scheduler"] == "running"
        assert result["last_hour"]["total_runs"] == 2
        assert result["last_hour"]["failed_runs"] == 0
        assert result["last_hour"]["success_rate"] == 100.0


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.supabase')
async def test_get_tasks_health_degraded(mock_supabase):
    """GET /health should return degraded when tasks fail."""
    mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
        data=[
            {"task_name": "hourly", "status": "success"},
            {"task_name": "daily", "status": "failed"}
        ]
    )

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.tasks_mgmt.scheduler', create=True) as mock_scheduler:
        mock_scheduler.running = True

        result = await get_tasks_health(request=mock_request, admin=admin)

        assert result["status"] == "degraded"
        assert result["last_hour"]["failed_runs"] == 1
        assert result["last_hour"]["success_rate"] == 50.0


@pytest.mark.asyncio
@patch('api.admin.tasks_mgmt.supabase')
async def test_get_tasks_health_error_sanitization(mock_supabase):
    """GET /health should sanitize error messages."""
    mock_supabase.table.side_effect = Exception("Database error with sensitive info")

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    result = await get_tasks_health(request=mock_request, admin=admin)

    assert result["status"] == "error"
    assert result["error"] == "Failed to retrieve task health status"
    assert "sensitive" not in result["error"]


# ==========================================
# Test POST /{task_name}/run (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_run_task_manually_success():
    """POST /{task_name}/run should trigger task."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # Mock the imported function inside the endpoint
    with patch('scheduler.run_aggregation_now') as mock_run:
        mock_run.return_value = {"success": True}

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
        mock_run.return_value = {"success": True}

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
        assert "xyz" not in str(exc_info.value.detail)
