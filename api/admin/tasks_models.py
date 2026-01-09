"""
Tasks Management API Models - Request/Response schemas.

@module api.admin.tasks_models
@version 1.0.0
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ==========================================
# Response Models
# ==========================================

class TaskRunInfo(BaseModel):
    """Single task run information."""
    started_at: str = Field(..., description="Task start timestamp (ISO format)")
    status: str = Field(..., description="Task status (success|failed|running|pending)")
    duration_ms: Optional[int] = Field(None, description="Task duration in milliseconds")


class TaskStatusInfo(BaseModel):
    """Task status aggregation."""
    last_run: Optional[str] = Field(None, description="Last run timestamp")
    last_status: Optional[str] = Field(None, description="Last run status")
    last_duration_ms: Optional[int] = Field(None, description="Last run duration (ms)")
    last_error: Optional[str] = Field(None, description="Last error message")
    recent_runs: List[TaskRunInfo] = Field(default_factory=list, description="Recent 5 runs")


class TaskStatusResponse(BaseModel):
    """Response for GET /status."""
    tasks: dict[str, TaskStatusInfo] = Field(..., description="Task status by task name")


class TaskLogEntry(BaseModel):
    """Single task log entry."""
    id: Optional[str] = Field(None, description="Log entry ID")
    task_name: str = Field(..., description="Task name")
    status: str = Field(..., description="Task status")
    started_at: str = Field(..., description="Start timestamp")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class TaskLogsResponse(BaseModel):
    """Response for GET /logs."""
    logs: List[TaskLogEntry] = Field(..., description="List of task logs")


class TaskHealthMetrics(BaseModel):
    """Task health metrics for last hour."""
    total_runs: int = Field(..., description="Total task runs in period")
    failed_runs: int = Field(..., description="Number of failed runs")
    success_rate: float = Field(..., description="Success rate percentage")


class TaskHealthResponse(BaseModel):
    """Response for GET /health."""
    status: str = Field(..., description="Overall health status (healthy|degraded|error)")
    scheduler: str = Field(..., description="Scheduler status (running|stopped|unknown)")
    last_hour: TaskHealthMetrics = Field(..., description="Last hour metrics")


class TaskTriggerResult(BaseModel):
    """Result from manual task trigger."""
    status: str = Field(..., description="Trigger status")
    task_type: str = Field(..., description="Task type that was run")


class TaskTriggerResponse(BaseModel):
    """Response for POST /{task_name}/run."""
    status: str = Field(..., description="Trigger status (triggered)")
    task: str = Field(..., description="Task name")
    result: TaskTriggerResult = Field(..., description="Execution result")
