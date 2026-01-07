"""
Themes API - Holiday themes endpoint (v2).

@module api.user.themes
@version 2.0.0

Endpoints:
- GET /api/v2/user/themes/current - Get current active theme
"""

from datetime import date, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

from infrastructure.db_compat import supabase

router = APIRouter(prefix="/themes", tags=["user-themes-v2"])


# ==========================================
# Response Models
# ==========================================

class ThemeConfig(BaseModel):
    """Theme configuration."""
    colors: Optional[Dict[str, str]] = None
    badge: Optional[Dict[str, Any]] = None
    decorations: Optional[Dict[str, Any]] = None
    banner_style: Optional[Dict[str, Any]] = None


class CurrentThemeResponse(BaseModel):
    """Current theme response."""
    theme_id: Optional[str] = None
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


# ==========================================
# Endpoints
# ==========================================

@router.get("/current")
async def get_current_theme() -> CurrentThemeResponse:
    """
    Get the currently active holiday theme based on today's date.

    Returns the highest-priority theme that matches today's date,
    or null values if no theme is active.
    """
    today = date.today()

    result = supabase.table("holiday_themes").select("*").eq(
        "is_active", True,
    ).order("priority", desc=True).execute()

    if not result.data:
        return CurrentThemeResponse()

    for theme in result.data:
        if _is_theme_active(theme["date_rule"], today):
            return CurrentThemeResponse(
                theme_id=theme["id"],
                name=theme["name"],
                config=theme["theme_config"],
            )

    return CurrentThemeResponse()


# ==========================================
# Helper Functions
# ==========================================

def _is_theme_active(date_rule: dict, check_date: date) -> bool:
    """Check if a theme should be active on the given date."""
    rule_type = date_rule.get("type")

    if rule_type == "fixed":
        return _check_fixed_date(date_rule, check_date)
    elif rule_type == "dynamic":
        return _check_dynamic_date(date_rule, check_date)

    return False


def _check_fixed_date(date_rule: dict, check_date: date) -> bool:
    """Check fixed date rules (MM-DD format)."""
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


def _check_dynamic_date(date_rule: dict, check_date: date) -> bool:
    """Check dynamic date rules (calculated holidays)."""
    try:
        rule_name = date_rule.get("rule", "")
        offset_start = date_rule.get("offset_start", 0)
        offset_end = date_rule.get("offset_end", 0)

        base_date = _calculate_dynamic_date(rule_name, check_date.year)
        if not base_date:
            return False

        start_date = base_date + timedelta(days=offset_start)
        end_date = base_date + timedelta(days=offset_end)

        return start_date <= check_date <= end_date

    except (ValueError, TypeError):
        return False


def _calculate_dynamic_date(rule: str, year: int) -> Optional[date]:
    """Calculate dynamic holiday dates."""
    if rule == "us_thanksgiving":
        # 4th Thursday of November
        nov_first = date(year, 11, 1)
        days_until_thursday = (3 - nov_first.weekday() + 7) % 7
        first_thursday = nov_first + timedelta(days=days_until_thursday)
        return first_thursday + timedelta(weeks=3)

    elif rule == "black_friday":
        thanksgiving = _calculate_dynamic_date("us_thanksgiving", year)
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
