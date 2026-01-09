"""
Events Domain Service

Core business logic for Events domain.

@module domains.events.service
@version 1.0.0 (created for v3.27 refactor)
@version 1.1.0 (2026-01-09: Added security validation)
"""

from typing import Optional, Dict, Any
from .constants import (
    VALID_GROUP_BY,
    VALID_STAT_TYPES,
    DATE_PATTERN,
)
from .entities import UserEvent
from .security import (
    validate_user_id,
    validate_event_type,
    sanitize_event_data,
    sanitize_sql_input,
)


class EventsDomainService:
    """
    Domain service for Events business rules.

    This service contains pure business logic without infrastructure dependencies.
    """

    @staticmethod
    def validate_group_by(group_by: str) -> None:
        """
        Validate group_by parameter.

        Args:
            group_by: Group by field

        Raises:
            ValueError: If group_by is invalid
        """
        if group_by not in VALID_GROUP_BY:
            raise ValueError(
                f"Invalid group_by '{group_by}'. "
                f"Must be one of: {', '.join(VALID_GROUP_BY)}"
            )

    @staticmethod
    def validate_stat_type(stat_type: str) -> None:
        """
        Validate stat_type parameter.

        Args:
            stat_type: Statistic type

        Raises:
            ValueError: If stat_type is invalid
        """
        if stat_type not in VALID_STAT_TYPES:
            raise ValueError(
                f"Invalid stat_type '{stat_type}'. "
                f"Must be one of: {', '.join(VALID_STAT_TYPES)}"
            )

    @staticmethod
    def validate_date_format(date_str: Optional[str], field_name: str) -> None:
        """
        Validate date string format.

        Args:
            date_str: Date string to validate (can be None)
            field_name: Name of the field (for error messages)

        Raises:
            ValueError: If date format is invalid
        """
        if date_str is None:
            return

        if not DATE_PATTERN.match(date_str):
            raise ValueError(
                f"Invalid {field_name} format. "
                f"Must be YYYY-MM-DD or ISO 8601 format"
            )

    @staticmethod
    def validate_pagination(offset: int, limit: int, max_limit: int = 100) -> None:
        """
        Validate pagination parameters.

        Args:
            offset: Pagination offset
            limit: Page size
            max_limit: Maximum allowed limit

        Raises:
            ValueError: If pagination parameters are invalid
        """
        if offset < 0:
            raise ValueError("offset must be >= 0")

        if limit < 1:
            raise ValueError("limit must be >= 1")

        if limit > max_limit:
            raise ValueError(f"limit must be <= {max_limit}")

    @staticmethod
    def validate_event(event: UserEvent) -> None:
        """
        Validate user event before creation.

        ✅ Enhanced: Now includes security validation (SQL injection, format check)

        Args:
            event: UserEvent to validate

        Raises:
            ValueError: If event is invalid or contains malicious input
        """
        if not event.user_id:
            raise ValueError("user_id is required")

        if not event.event_type:
            raise ValueError("event_type is required")

        # Security validation
        try:
            event.user_id = validate_user_id(event.user_id)
            event.event_type = validate_event_type(event.event_type)
        except ValueError as e:
            raise ValueError(f"Security validation failed: {e}")

    @staticmethod
    def sanitize_event_data(event_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Sanitize event data to prevent XSS and injection attacks.

        ✅ Implemented: Now uses security module for comprehensive sanitization

        Args:
            event_data: Event data dictionary

        Returns:
            Sanitized event data (sensitive fields masked)
        """
        if event_data is None:
            return None

        # Use security module for sanitization
        return sanitize_event_data(event_data)
