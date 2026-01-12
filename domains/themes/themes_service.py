"""Themes Service - Business logic for holiday themes.

@module domains.themes.themes_service
@version 2.1.0

v2.1.0: Added CRUD, review workflow, and regeneration support
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from infrastructure.repositories.themes_repository import SupabaseThemesRepository
from domains.themes.constants import (
    VALID_CATEGORIES,
    VALID_REVIEW_STATUSES,
    REVIEW_STATUS_REVIEWED,
    REVIEW_STATUS_REJECTED,
    REVIEW_STATUS_AUTO_APPROVED,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_SWITCH,
)

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

    # ==========================================
    # Read Operations
    # ==========================================

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
                date_rule = theme.get("date_rule")
                if date_rule and self._is_theme_active(date_rule, check_date):
                    return theme

                # Also check if theme has a specific date field
                theme_date = theme.get("date")
                if theme_date:
                    if isinstance(theme_date, str):
                        theme_date = date.fromisoformat(theme_date)
                    if theme_date == check_date:
                        return theme

            return None

        except Exception as e:
            logger.error(f"Failed to get current active theme: {e}")
            raise

    async def get_theme_by_id(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Get a theme by its ID."""
        return await self.repository.get_by_id(theme_id)

    async def get_theme_by_date(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get a theme for a specific date."""
        return await self.repository.get_by_date(target_date)

    async def list_themes(
        self,
        offset: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        List themes with pagination and filters.

        Returns:
            Dict with themes list and total count
        """
        themes = await self.repository.list_all(offset=offset, limit=limit, filters=filters)
        total = await self.repository.count_all(filters=filters)

        return {
            "themes": themes,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    # ==========================================
    # Write Operations
    # ==========================================

    async def create_theme(
        self,
        name: str,
        target_date: Optional[date] = None,
        category: str = "holiday",
        priority: int = 50,
        description: Optional[str] = None,
        slogan: Optional[str] = None,
        theme_config: Optional[Dict[str, Any]] = None,
        name_i18n: Optional[Dict[str, str]] = None,
        slogan_i18n: Optional[Dict[str, str]] = None,
        description_i18n: Optional[Dict[str, str]] = None,
        regions: Optional[List[str]] = None,
        date_rule: Optional[Dict[str, Any]] = None,
        linked_campaign_id: Optional[str] = None,
        ai_generated: bool = False,
        ai_alternatives: Optional[List[Dict[str, Any]]] = None,
        ai_recommended_id: Optional[str] = None,
        selected_alternative_id: Optional[str] = None,
        review_status: str = "pending",
        source_url: Optional[str] = None,
        learn_more_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new theme.

        Args:
            name: Theme display name
            target_date: Specific date for the theme
            category: Theme category
            priority: Theme priority (higher = more important)
            description: Theme description
            slogan: Theme slogan
            theme_config: Visual configuration
            name_i18n: Multi-language name
            slogan_i18n: Multi-language slogan
            description_i18n: Multi-language description
            regions: Target regions
            date_rule: Date activation rules
            linked_campaign_id: Linked campaign ID
            ai_generated: Whether AI generated
            ai_alternatives: AI generated alternatives
            ai_recommended_id: AI recommended alternative ID
            selected_alternative_id: Selected alternative ID
            review_status: Review status
            source_url: Information source URL
            learn_more_url: Learn more URL

        Returns:
            Created theme dictionary
        """
        # Validate category
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {category}. Must be one of {VALID_CATEGORIES}")

        # Validate review_status
        if review_status not in VALID_REVIEW_STATUSES:
            raise ValueError(f"Invalid review_status: {review_status}. Must be one of {VALID_REVIEW_STATUSES}")

        data = {
            "name": name,
            "category": category,
            "priority": priority,
            "is_active": True,
            "status": "active",
            "review_status": review_status,
        }

        # Optional fields
        if target_date:
            data["date"] = target_date.isoformat()
        if description:
            data["description"] = description
        if slogan:
            data["slogan"] = slogan
        if theme_config:
            data["theme_config"] = theme_config
        if name_i18n:
            data["name_i18n"] = name_i18n
        if slogan_i18n:
            data["slogan_i18n"] = slogan_i18n
        if description_i18n:
            data["description_i18n"] = description_i18n
        if regions:
            data["regions"] = regions
        if date_rule:
            data["date_rule"] = date_rule
        if linked_campaign_id:
            data["linked_campaign_id"] = linked_campaign_id
        if source_url:
            data["source_url"] = source_url
        if learn_more_url:
            data["learn_more_url"] = learn_more_url

        # AI generation fields
        data["ai_generated"] = ai_generated
        if ai_alternatives:
            data["ai_alternatives"] = ai_alternatives
        if ai_recommended_id:
            data["ai_recommended_id"] = ai_recommended_id
        if selected_alternative_id:
            data["selected_alternative_id"] = selected_alternative_id

        return await self.repository.create(data)

    async def update_theme(
        self,
        theme_id: str,
        update_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing theme.

        Args:
            theme_id: Theme ID to update
            update_data: Fields to update

        Returns:
            Updated theme or None if not found
        """
        # Validate category if provided
        if "category" in update_data and update_data["category"] not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of {VALID_CATEGORIES}")

        # Validate review_status if provided
        if "review_status" in update_data and update_data["review_status"] not in VALID_REVIEW_STATUSES:
            raise ValueError(f"Invalid review_status. Must be one of {VALID_REVIEW_STATUSES}")

        # Convert date to ISO format if provided
        if "date" in update_data and isinstance(update_data["date"], date):
            update_data["date"] = update_data["date"].isoformat()

        return await self.repository.update(theme_id, update_data)

    async def delete_theme(self, theme_id: str) -> bool:
        """
        Soft delete a theme.

        Args:
            theme_id: Theme ID to delete

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(theme_id)

    # ==========================================
    # Review Operations (v2.1)
    # ==========================================

    async def review_theme(
        self,
        theme_id: str,
        action: str,
        admin_id: str,
        alternative_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Review a theme.

        Args:
            theme_id: Theme ID to review
            action: Review action (approve, reject, switch)
            admin_id: Admin user ID
            alternative_id: Alternative ID for switch action
            notes: Review notes

        Returns:
            Updated theme and message

        Raises:
            ValueError: If theme not found or invalid action
        """
        theme = await self.repository.get_by_id(theme_id)
        if not theme:
            raise ValueError("Theme not found")

        now = datetime.now(timezone.utc).isoformat()
        update_data = {
            "reviewed_by": admin_id,
            "reviewed_at": now,
        }
        if notes:
            update_data["review_notes"] = notes

        if action == REVIEW_ACTION_APPROVE:
            update_data["review_status"] = REVIEW_STATUS_REVIEWED

        elif action == REVIEW_ACTION_REJECT:
            update_data["review_status"] = REVIEW_STATUS_REJECTED

        elif action == REVIEW_ACTION_SWITCH:
            if not alternative_id:
                raise ValueError("alternative_id required for switch action")

            alternatives = theme.get("ai_alternatives", [])
            selected = None
            for alt in alternatives:
                if alt.get("id") == alternative_id:
                    selected = alt
                    break

            if not selected:
                raise ValueError(f"Alternative {alternative_id} not found")

            # Update theme content from selected alternative
            update_data.update({
                "name": selected.get("name", theme["name"]),
                "name_i18n": selected.get("name_i18n", {}),
                "category": selected.get("category", theme.get("category")),
                "priority": selected.get("priority", theme.get("priority")),
                "theme_config": selected.get("theme_config", theme.get("theme_config")),
                "slogan": selected.get("slogan"),
                "slogan_i18n": selected.get("slogan_i18n", {}),
                "selected_alternative_id": alternative_id,
                "review_status": REVIEW_STATUS_REVIEWED,
            })

        else:
            raise ValueError(f"Unknown action: {action}")

        updated = await self.repository.update(theme_id, update_data)

        # Generate proper past tense message
        action_messages = {
            REVIEW_ACTION_APPROVE: "approved",
            REVIEW_ACTION_REJECT: "rejected",
            REVIEW_ACTION_SWITCH: "switched",
        }
        action_past = action_messages.get(action, f"{action}ed")

        return {
            "theme": updated,
            "message": f"Theme {action_past} successfully",
        }

    async def regenerate_theme(
        self,
        theme_id: str,
        admin_id: str,
        new_alternatives: List[Dict[str, Any]],
        recommended_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Regenerate a theme with new alternatives.

        Args:
            theme_id: Theme ID to regenerate
            admin_id: Admin user ID
            new_alternatives: New AI-generated alternatives
            recommended_id: Recommended alternative ID
            reason: Reason for regeneration

        Returns:
            Updated theme and history count
        """
        theme = await self.repository.get_by_id(theme_id)
        if not theme:
            raise ValueError("Theme not found")

        # Save current state to history
        history_entry = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "alternatives": theme.get("ai_alternatives", []),
            "selected_id": theme.get("selected_alternative_id"),
            "reason": reason or "manual_regenerate",
            "regenerated_by": admin_id,
        }

        generation_history = theme.get("generation_history", [])
        generation_history.append(history_entry)

        # Get the recommended alternative
        recommended = None
        for alt in new_alternatives:
            if alt.get("id") == recommended_id:
                recommended = alt
                break

        if not recommended:
            recommended = new_alternatives[0] if new_alternatives else {}

        # Update theme with new alternatives
        update_data = {
            "name": recommended.get("name", theme["name"]),
            "name_i18n": recommended.get("name_i18n", {}),
            "category": recommended.get("category", theme.get("category")),
            "priority": recommended.get("priority", theme.get("priority")),
            "theme_config": recommended.get("theme_config", theme.get("theme_config")),
            "slogan": recommended.get("slogan"),
            "slogan_i18n": recommended.get("slogan_i18n", {}),
            "ai_alternatives": new_alternatives,
            "ai_recommended_id": recommended_id,
            "selected_alternative_id": recommended_id,
            "review_status": REVIEW_STATUS_AUTO_APPROVED,
            "generation_history": generation_history,
            "regenerate_count": theme.get("regenerate_count", 0) + 1,
        }

        updated = await self.repository.update(theme_id, update_data)

        return {
            "theme": updated,
            "message": "Theme regenerated successfully",
            "history_count": len(generation_history),
        }

    async def get_theme_history(self, theme_id: str) -> Dict[str, Any]:
        """
        Get theme generation history.

        Args:
            theme_id: Theme ID

        Returns:
            Theme history data
        """
        theme = await self.repository.get_by_id(theme_id)
        if not theme:
            raise ValueError("Theme not found")

        return {
            "theme_id": theme_id,
            "current": {
                "alternatives": theme.get("ai_alternatives", []),
                "selected_id": theme.get("selected_alternative_id"),
                "recommended_id": theme.get("ai_recommended_id"),
            },
            "history": theme.get("generation_history", []),
            "regenerate_count": theme.get("regenerate_count", 0),
        }

    async def batch_approve_themes(
        self,
        theme_ids: List[str],
        admin_id: str,
    ) -> Dict[str, int]:
        """
        Batch approve multiple themes.

        Args:
            theme_ids: List of theme IDs
            admin_id: Admin user ID

        Returns:
            Results with approved/failed counts
        """
        updated = await self.repository.batch_update_review_status(
            theme_ids=theme_ids,
            review_status=REVIEW_STATUS_REVIEWED,
            reviewed_by=admin_id,
        )

        return {
            "approved": updated,
            "failed": len(theme_ids) - updated,
        }

    # ==========================================
    # Statistics Operations (v2.1)
    # ==========================================

    async def get_generation_status(self, days: int = 300) -> Dict[str, Any]:
        """
        Get theme generation status overview.

        Args:
            days: Number of days to check

        Returns:
            Status overview with statistics
        """
        today = date.today()
        end_date = today + timedelta(days=days)

        # Get existing dates
        existing_dates = await self.repository.get_existing_dates(today, end_date)

        # Calculate missing dates
        all_dates = set((today + timedelta(days=i)) for i in range(days))
        missing_dates = sorted(all_dates - existing_dates)

        # Get review status stats
        stats = await self.repository.get_review_status_stats(today, end_date)

        return {
            "total_days": days,
            "generated": len(existing_dates),
            "missing": len(missing_dates),
            "review_status": stats,
            "missing_dates": [d.isoformat() for d in missing_dates[:30]],
            "recommendation": (
                "full" if len(missing_dates) > 100
                else "partial" if missing_dates
                else "complete"
            ),
        }

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
        if not date_rule:
            return False

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
