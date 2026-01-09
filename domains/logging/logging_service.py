"""
Logging Service - Business logic for error logging.

@module domains.logging.logging_service
@version 1.0.0
"""

import logging
from typing import Dict, List, Any

from infrastructure.repositories.logging_repository import SupabaseLoggingRepository

logger = logging.getLogger(__name__)


class LoggingService:
    """Service for error logging operations."""

    def __init__(self, database_client):
        """
        Initialize service with database client.

        Args:
            database_client: Database client (Supabase)
        """
        self.repository = SupabaseLoggingRepository(database_client)

    async def create_error_log(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single error log with business logic.

        Args:
            error_data: Error log data

        Returns:
            Created error log record

        Raises:
            Exception: If creation fails
        """
        try:
            # Apply any business rules here (currently just pass through)
            result = await self.repository.create_error_log(error_data)

            # Log the error for server-side monitoring
            error_type = error_data.get("error_type", "UNKNOWN")
            message = error_data.get("message", "No message")
            logger.info(f"[ErrorLog] {error_type} - {message[:100]}")

            return result

        except Exception as e:
            logger.error(f"Error logging service failed: {e}")
            raise

    async def create_error_logs_batch(self, errors: List[Dict[str, Any]]) -> int:
        """
        Create multiple error logs in a batch.

        Args:
            errors: List of error log data dictionaries

        Returns:
            Number of error logs created

        Raises:
            Exception: If batch creation fails
        """
        if not errors:
            return 0

        try:
            count = await self.repository.create_error_logs_batch(errors)

            logger.info(f"[ErrorLog] Batch logged {count} errors")

            return count

        except Exception as e:
            logger.error(f"Error logging batch service failed: {e}")
            raise
