"""
Logging Repository Interface.

@module domains.logging.repository
@version 1.0.0
"""

from typing import Protocol, Dict, List, Any


class LoggingRepository(Protocol):
    """Repository interface for error logging operations."""

    async def create_error_log(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single error log entry.

        Args:
            error_data: Error log data containing:
                - error_id: str
                - error_type: str
                - error_code: Optional[str]
                - message: Optional[str]
                - status_code: Optional[int]
                - endpoint: Optional[str]
                - method: Optional[str]
                - user_id: Optional[str]
                - user_code: Optional[str]
                - session_id: Optional[str]
                - page_url: Optional[str]
                - user_agent: Optional[str]
                - stack_trace: Optional[str]
                - context: Dict[str, Any]
                - client_timestamp: Optional[str]

        Returns:
            Created error log record with id

        Raises:
            Exception: If database operation fails
        """
        ...

    async def create_error_logs_batch(self, errors: List[Dict[str, Any]]) -> int:
        """
        Create multiple error log entries in a batch.

        Args:
            errors: List of error log data dictionaries

        Returns:
            Number of error logs created

        Raises:
            Exception: If database operation fails
        """
        ...
