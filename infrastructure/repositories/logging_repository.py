"""
Supabase Logging Repository Implementation.

@module infrastructure.repositories.logging_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SupabaseLoggingRepository:
    """Supabase implementation of LoggingRepository."""

    def __init__(self, supabase_client):
        """
        Initialize repository with Supabase client.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def create_error_log(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single error log entry in Supabase.

        Args:
            error_data: Error log data

        Returns:
            Created error log record

        Raises:
            Exception: If Supabase insert fails
        """
        try:
            response = await self.supabase.table("error_logs").insert(error_data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            # If no data returned, return the input with a placeholder ID
            return {**error_data, "id": "created"}

        except Exception as e:
            logger.error(f"Failed to create error log: {e}")
            raise

    async def create_error_logs_batch(self, errors: List[Dict[str, Any]]) -> int:
        """
        Create multiple error log entries in a batch.

        Args:
            errors: List of error log data dictionaries

        Returns:
            Number of error logs created

        Raises:
            Exception: If Supabase batch insert fails
        """
        if not errors:
            return 0

        try:
            response = await self.supabase.table("error_logs").insert(errors).execute()

            # Return the number of records created
            if response.data:
                return len(response.data)

            # If no data returned, assume all records were created
            return len(errors)

        except Exception as e:
            logger.error(f"Failed to create error logs batch: {e}")
            raise
