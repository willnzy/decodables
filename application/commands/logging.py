"""
Logging Commands - Error logging write operations.

@module application.commands.logging
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


# ==========================================
# Create Error Log Command
# ==========================================

@dataclass
class CreateErrorLogCommand:
    """Command to create a single error log entry."""
    error_data: Dict[str, Any]


@dataclass
class CreateErrorLogResult:
    """Result of error log creation."""
    success: bool
    error_log_id: Optional[str] = None
    error: Optional[str] = None


class CreateErrorLogHandler:
    """Handler for CreateErrorLogCommand."""

    def __init__(self, logging_service):
        """
        Initialize handler with LoggingService.

        Args:
            logging_service: LoggingService instance
        """
        self._logging_service = logging_service

    async def handle(self, command: CreateErrorLogCommand) -> CreateErrorLogResult:
        """
        Execute error log creation.

        Args:
            command: CreateErrorLogCommand

        Returns:
            CreateErrorLogResult with success status
        """
        try:
            result = await self._logging_service.create_error_log(command.error_data)

            return CreateErrorLogResult(
                success=True,
                error_log_id=result.get("id"),
            )

        except Exception as e:
            return CreateErrorLogResult(
                success=False,
                error=str(e),
            )


# ==========================================
# Create Error Log Batch Command
# ==========================================

@dataclass
class CreateErrorLogBatchCommand:
    """Command to create multiple error log entries."""
    errors: List[Dict[str, Any]]


@dataclass
class CreateErrorLogBatchResult:
    """Result of batch error log creation."""
    success: bool
    count: int = 0
    error: Optional[str] = None


class CreateErrorLogBatchHandler:
    """Handler for CreateErrorLogBatchCommand."""

    def __init__(self, logging_service):
        """
        Initialize handler with LoggingService.

        Args:
            logging_service: LoggingService instance
        """
        self._logging_service = logging_service

    async def handle(self, command: CreateErrorLogBatchCommand) -> CreateErrorLogBatchResult:
        """
        Execute batch error log creation.

        Args:
            command: CreateErrorLogBatchCommand

        Returns:
            CreateErrorLogBatchResult with count of created logs
        """
        try:
            count = await self._logging_service.create_error_logs_batch(command.errors)

            return CreateErrorLogBatchResult(
                success=True,
                count=count,
            )

        except Exception as e:
            return CreateErrorLogBatchResult(
                success=False,
                count=0,
                error=str(e),
            )
