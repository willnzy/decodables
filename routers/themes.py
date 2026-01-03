"""
Holiday Themes Router
Provides public API for fetching current holiday theme based on date.

@module routers/themes
"""

from fastapi import APIRouter
from datetime import date, timedelta
from typing import Optional, Dict, Any
from db_service import supabase

router = APIRouter(prefix="/api/themes", tags=["themes"])


# ============================================================
# Public API
# ============================================================

@router.get("/current")
async def get_current_theme() -> Dict[str, Any]:
    """
    Get the currently active holiday theme based on today's date.
    
    Returns the highest-priority theme that matches today's date,
    or null values if no theme is active.
    
    Returns:
        {
            "theme_id": "christmas" | null,
            "name": "Christmas" | null,
            "config": { colors, badge, decorations, banner_style } | null
        }
    """
    today = date.today()
    
    # [Why]: Fetch all active themes ordered by priority
    # Higher priority themes win when multiple overlap
    result = supabase.table('holiday_themes').select('*').eq(
        'is_active', True
    ).order('priority', desc=True).execute()
    
    if not result.data:
        return {"theme_id": None, "name": None, "config": None}
    
    # [Why]: Check each theme's date_rule to find active one
    for theme in result.data:
        if is_theme_active(theme['date_rule'], today):
            return {
                "theme_id": theme['id'],
                "name": theme['name'],
                "config": theme['theme_config']
            }
    
    return {"theme_id": None, "name": None, "config": None}


# ============================================================
# Helper Functions
# ============================================================

def is_theme_active(date_rule: dict, check_date: date) -> bool:
    """
    Check if a theme should be active on the given date.
    
    Supports two types of date rules:
    1. Fixed dates: { "type": "fixed", "start": "12-20", "end": "12-26" }
    2. Dynamic dates: { "type": "dynamic", "rule": "us_thanksgiving", "offset_start": -1, "offset_end": 1 }
    
    Args:
        date_rule: The theme's date_rule configuration
        check_date: The date to check against
        
    Returns:
        True if theme is active, False otherwise
    """
    rule_type = date_rule.get('type')
    
    if rule_type == 'fixed':
        return _check_fixed_date(date_rule, check_date)
    elif rule_type == 'dynamic':
        return _check_dynamic_date(date_rule, check_date)
    
    return False


def _check_fixed_date(date_rule: dict, check_date: date) -> bool:
    """
    Check fixed date rules (MM-DD format).
    Handles year wrap-around (e.g., Dec 31 to Jan 2).
    """
    try:
        start_str = date_rule.get('start', '')
        end_str = date_rule.get('end', '')
        
        if not start_str or not end_str:
            return False
        
        # [Why]: Parse MM-DD format and create dates for current year
        start_month, start_day = map(int, start_str.split('-'))
        end_month, end_day = map(int, end_str.split('-'))
        
        year = check_date.year
        start_date = date(year, start_month, start_day)
        end_date = date(year, end_month, end_day)
        
        # [Why]: Handle year wrap (e.g., Dec 31 - Jan 2)
        if start_date > end_date:
            # Theme spans year boundary
            # Active if: check_date >= start_date OR check_date <= end_date
            return check_date >= start_date or check_date <= end_date
        
        return start_date <= check_date <= end_date
        
    except (ValueError, TypeError):
        return False


def _check_dynamic_date(date_rule: dict, check_date: date) -> bool:
    """
    Check dynamic date rules (calculated holidays like Thanksgiving).
    """
    try:
        rule_name = date_rule.get('rule', '')
        offset_start = date_rule.get('offset_start', 0)
        offset_end = date_rule.get('offset_end', 0)
        
        # [Why]: Calculate base date for dynamic holiday
        base_date = calculate_dynamic_date(rule_name, check_date.year)
        if not base_date:
            return False
        
        start_date = base_date + timedelta(days=offset_start)
        end_date = base_date + timedelta(days=offset_end)
        
        return start_date <= check_date <= end_date
        
    except (ValueError, TypeError):
        return False


def calculate_dynamic_date(rule: str, year: int) -> Optional[date]:
    """
    Calculate dynamic US holiday dates.
    
    Supported rules:
    - us_thanksgiving: 4th Thursday of November
    - black_friday: Day after Thanksgiving
    - easter: (Not implemented - complex calculation)
    
    Args:
        rule: The rule name
        year: The year to calculate for
        
    Returns:
        The calculated date, or None if rule is unknown
    """
    if rule == 'us_thanksgiving':
        # [Why]: US Thanksgiving is the 4th Thursday of November
        nov_first = date(year, 11, 1)
        # Find first Thursday (weekday 3 in Python, 0=Monday)
        days_until_thursday = (3 - nov_first.weekday() + 7) % 7
        first_thursday = nov_first + timedelta(days=days_until_thursday)
        # Add 3 weeks to get 4th Thursday
        return first_thursday + timedelta(weeks=3)
    
    elif rule == 'black_friday':
        # [Why]: Black Friday is the day after Thanksgiving
        thanksgiving = calculate_dynamic_date('us_thanksgiving', year)
        if thanksgiving:
            return thanksgiving + timedelta(days=1)
        return None
    
    elif rule == 'easter':
        # [Why]: Easter requires the Computus algorithm
        # Can be implemented if needed; skipping for now
        return None
    
    elif rule == 'memorial_day':
        # [Why]: Last Monday of May
        # Start from May 31 and go backwards to find Monday
        may_end = date(year, 5, 31)
        days_since_monday = may_end.weekday()  # 0=Monday
        return may_end - timedelta(days=days_since_monday)
    
    elif rule == 'labor_day':
        # [Why]: First Monday of September
        sept_first = date(year, 9, 1)
        days_until_monday = (7 - sept_first.weekday()) % 7
        return sept_first + timedelta(days=days_until_monday)
    
    return None
