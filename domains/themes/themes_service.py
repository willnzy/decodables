"""Themes Service - Business logic for holiday themes.

@module domains.themes.themes_service
@version 1.0.0
"""

import logging
from datetime import date, timedelta
from typing import Optional, Dict, Any

from infrastructure.repositories.themes_repository import SupabaseThemesRepository

logger = logging.getLogger(__name__)


class ThemesService:
    """Service for holiday themes business logic."""

    def __init__(self, database_client):
        """
        Initialize with database client.

        Args:
            database_client: Database client (Supabase)
        """
        self.repository = SupabaseThemesRepository(database_client)

    async def get_current_active_theme(self, check_date: date) -> Optional[Dict[str, Any]]:
        """
        Get the currently active theme for a given date.

        Business logic:
        1. Fetch all active themes (ordered by priority descending)
        2. For each theme, check if date matches date_rule
        3. Return first matching theme (highest priority)

        Args:
            check_date: Date to check theme activation

        Returns:
            Theme dict if active, None otherwise
        """
        try:
            themes = await self.repository.list_active_themes()

            if not themes:
                return None

            # Find first theme that matches current date
            for theme in themes:
                if self._is_theme_active(theme["date_rule"], check_date):
                    return theme

            return None

        except Exception as e:
            logger.error(f"Failed to get current active theme: {e}")
            raise

    # ==========================================
    # Business Logic: Date Matching
    # ==========================================

    def _is_theme_active(self, date_rule: dict, check_date: date) -> bool:
        """
        Check if a theme should be active on the given date.

        Args:
            date_rule: Date rule configuration
            check_date: Date to check

        Returns:
            True if theme is active on this date
        """
        rule_type = date_rule.get("type")

        if rule_type == "fixed":
            return self._check_fixed_date(date_rule, check_date)
        elif rule_type == "dynamic":
            return self._check_dynamic_date(date_rule, check_date)

        return False

    def _check_fixed_date(self, date_rule: dict, check_date: date) -> bool:
        """
        Check fixed date rules (MM-DD format).

        Args:
            date_rule: Fixed date rule with start/end fields
            check_date: Date to check

        Returns:
            True if date is within range
        """
        try:
            start_str = date_rule.get("start", "")
            end_str = date_rule.get("end", "")

            if not start_str or not end_str:
                return False

            start_month, start_day = map(int, start_str.split("-"))
            end_month, end_day = map(int, end_str.split("-"))

            year = check_date.year
            start_date = date(year, start_month, start_day)
            end_date = date(year, end_month, end_day)

            # Handle year wrap (e.g., Dec 31 - Jan 2)
            if start_date > end_date:
                return check_date >= start_date or check_date <= end_date

            return start_date <= check_date <= end_date

        except (ValueError, TypeError):
            return False

    def _check_dynamic_date(self, date_rule: dict, check_date: date) -> bool:
        """
        Check dynamic date rules (calculated holidays).

        Args:
            date_rule: Dynamic date rule with rule name and offsets
            check_date: Date to check

        Returns:
            True if date is within calculated range
        """
        try:
            rule_name = date_rule.get("rule", "")
            offset_start = date_rule.get("offset_start", 0)
            offset_end = date_rule.get("offset_end", 0)

            base_date = self._calculate_dynamic_date(rule_name, check_date.year)
            if not base_date:
                return False

            start_date = base_date + timedelta(days=offset_start)
            end_date = base_date + timedelta(days=offset_end)

            return start_date <= check_date <= end_date

        except (ValueError, TypeError):
            return False

    def _calculate_dynamic_date(self, rule: str, year: int) -> Optional[date]:
        """
        Calculate dynamic holiday dates.

        Supports:
        - US Thanksgiving (4th Thursday of November)
        - Black Friday (Day after Thanksgiving)
        - Mother's Day (2nd Sunday of May)
        - Father's Day (3rd Sunday of June)
        - MLK Day (3rd Monday of January)
        - Memorial Day (Last Monday of May)
        - Labor Day (First Monday of September)

        Args:
            rule: Holiday rule name
            year: Year to calculate for

        Returns:
            Calculated date or None if rule unknown
        """
        if rule == "us_thanksgiving":
            # 4th Thursday of November
            nov_first = date(year, 11, 1)
            days_until_thursday = (3 - nov_first.weekday() + 7) % 7
            first_thursday = nov_first + timedelta(days=days_until_thursday)
            return first_thursday + timedelta(weeks=3)

        elif rule == "black_friday":
            thanksgiving = self._calculate_dynamic_date("us_thanksgiving", year)
            return thanksgiving + timedelta(days=1) if thanksgiving else None

        elif rule == "mothers_day":
            # 2nd Sunday of May
            may_first = date(year, 5, 1)
            days_until_sunday = (6 - may_first.weekday() + 7) % 7
            first_sunday = may_first + timedelta(days=days_until_sunday)
            if may_first.weekday() == 6:
                first_sunday = may_first
            return first_sunday + timedelta(weeks=1)

        elif rule == "fathers_day":
            # 3rd Sunday of June
            june_first = date(year, 6, 1)
            days_until_sunday = (6 - june_first.weekday() + 7) % 7
            first_sunday = june_first + timedelta(days=days_until_sunday)
            if june_first.weekday() == 6:
                first_sunday = june_first
            return first_sunday + timedelta(weeks=2)

        elif rule == "mlk_day":
            # 3rd Monday of January
            jan_first = date(year, 1, 1)
            days_until_monday = (7 - jan_first.weekday()) % 7
            first_monday = jan_first if jan_first.weekday() == 0 else jan_first + timedelta(days=days_until_monday)
            return first_monday + timedelta(weeks=2)

        elif rule == "memorial_day":
            # Last Monday of May
            may_end = date(year, 5, 31)
            days_since_monday = may_end.weekday()
            return may_end - timedelta(days=days_since_monday)

        elif rule == "labor_day":
            # First Monday of September
            sept_first = date(year, 9, 1)
            days_until_monday = (7 - sept_first.weekday()) % 7
            if sept_first.weekday() == 0:
                return sept_first
            return sept_first + timedelta(days=days_until_monday)

        return None
