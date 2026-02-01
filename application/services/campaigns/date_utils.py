"""
日期计算工具

提供动态节假日日期计算和主题活动状态检查。
"""

from datetime import date, timedelta
from typing import Optional


def calculate_dynamic_date(rule: str, year: int) -> Optional[date]:
    """Calculate dynamic holiday dates."""
    if rule == 'us_thanksgiving':
        nov_first = date(year, 11, 1)
        days_until_thursday = (3 - nov_first.weekday() + 7) % 7
        first_thursday = nov_first + timedelta(days=days_until_thursday)
        return first_thursday + timedelta(weeks=3)
    
    elif rule == 'black_friday':
        thanksgiving = calculate_dynamic_date('us_thanksgiving', year)
        return thanksgiving + timedelta(days=1) if thanksgiving else None
    
    elif rule == 'mothers_day':
        may_first = date(year, 5, 1)
        days_until_sunday = (6 - may_first.weekday() + 7) % 7
        first_sunday = may_first + timedelta(days=days_until_sunday)
        if may_first.weekday() == 6:
            first_sunday = may_first
        return first_sunday + timedelta(weeks=1)
    
    elif rule == 'fathers_day':
        june_first = date(year, 6, 1)
        days_until_sunday = (6 - june_first.weekday() + 7) % 7
        first_sunday = june_first + timedelta(days=days_until_sunday)
        if june_first.weekday() == 6:
            first_sunday = june_first
        return first_sunday + timedelta(weeks=2)
    
    elif rule == 'mlk_day':
        jan_first = date(year, 1, 1)
        days_until_monday = (7 - jan_first.weekday()) % 7
        first_monday = jan_first if jan_first.weekday() == 0 else jan_first + timedelta(days=days_until_monday)
        return first_monday + timedelta(weeks=2)
    
    elif rule == 'memorial_day':
        may_end = date(year, 5, 31)
        return may_end - timedelta(days=may_end.weekday())
    
    elif rule == 'labor_day':
        sept_first = date(year, 9, 1)
        if sept_first.weekday() == 0:
            return sept_first
        days_until_monday = (7 - sept_first.weekday()) % 7
        return sept_first + timedelta(days=days_until_monday)
    
    return None


def is_theme_active(date_rule: dict, check_date: date) -> bool:
    """Check if a theme should be active on the given date."""
    rule_type = date_rule.get('type')
    
    if rule_type == 'fixed':
        try:
            start_str = date_rule.get('start', '')
            end_str = date_rule.get('end', '')
            if not start_str or not end_str:
                return False
            
            start_month, start_day = map(int, start_str.split('-'))
            end_month, end_day = map(int, end_str.split('-'))
            
            year = check_date.year
            start_date = date(year, start_month, start_day)
            end_date = date(year, end_month, end_day)
            
            if start_date > end_date:
                return check_date >= start_date or check_date <= end_date
            
            return start_date <= check_date <= end_date
        except (ValueError, TypeError, KeyError):
            return False
    
    elif rule_type == 'dynamic':
        try:
            rule_name = date_rule.get('rule', '')
            offset_start = date_rule.get('offset_start', 0)
            offset_end = date_rule.get('offset_end', 0)
            
            base_date = calculate_dynamic_date(rule_name, check_date.year)
            if not base_date:
                return False
            
            start_date = base_date + timedelta(days=offset_start)
            end_date = base_date + timedelta(days=offset_end)
            
            return start_date <= check_date <= end_date
        except (ValueError, TypeError, KeyError):
            return False
    
    return False
