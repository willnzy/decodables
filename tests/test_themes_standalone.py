"""
Standalone Tests for Holiday Themes date calculation.
No external dependencies required.

Run with: python tests/test_themes_standalone.py
"""

from datetime import date, timedelta
from typing import Optional

# ============================================================
# Copy of calculation functions for standalone testing
# ============================================================

def calculate_dynamic_date(rule: str, year: int) -> Optional[date]:
    """
    Calculate dynamic holiday dates.
    """
    if rule == 'us_thanksgiving':
        # US Thanksgiving is the 4th Thursday of November
        nov_first = date(year, 11, 1)
        days_until_thursday = (3 - nov_first.weekday() + 7) % 7
        first_thursday = nov_first + timedelta(days=days_until_thursday)
        return first_thursday + timedelta(weeks=3)
    
    elif rule == 'black_friday':
        thanksgiving = calculate_dynamic_date('us_thanksgiving', year)
        if thanksgiving:
            return thanksgiving + timedelta(days=1)
        return None
    
    elif rule == 'mothers_day':
        # Mother's Day is the 2nd Sunday of May
        may_first = date(year, 5, 1)
        days_until_sunday = (6 - may_first.weekday() + 7) % 7
        first_sunday = may_first + timedelta(days=days_until_sunday)
        if may_first.weekday() == 6:
            first_sunday = may_first
        return first_sunday + timedelta(weeks=1)
    
    elif rule == 'fathers_day':
        # Father's Day is the 3rd Sunday of June
        june_first = date(year, 6, 1)
        days_until_sunday = (6 - june_first.weekday() + 7) % 7
        first_sunday = june_first + timedelta(days=days_until_sunday)
        if june_first.weekday() == 6:
            first_sunday = june_first
        return first_sunday + timedelta(weeks=2)
    
    elif rule == 'mlk_day':
        # MLK Day is the 3rd Monday of January
        jan_first = date(year, 1, 1)
        days_until_monday = (7 - jan_first.weekday()) % 7
        if jan_first.weekday() == 0:
            first_monday = jan_first
        else:
            first_monday = jan_first + timedelta(days=days_until_monday)
        return first_monday + timedelta(weeks=2)
    
    elif rule == 'memorial_day':
        # Last Monday of May
        may_end = date(year, 5, 31)
        days_since_monday = may_end.weekday()
        return may_end - timedelta(days=days_since_monday)
    
    elif rule == 'labor_day':
        # First Monday of September
        sept_first = date(year, 9, 1)
        days_until_monday = (7 - sept_first.weekday()) % 7
        if sept_first.weekday() == 0:
            return sept_first
        return sept_first + timedelta(days=days_until_monday)
    
    return None


def _check_fixed_date(date_rule: dict, check_date: date) -> bool:
    """Check fixed date rules (MM-DD format)."""
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
        
    except (ValueError, TypeError):
        return False


def is_theme_active(date_rule: dict, check_date: date) -> bool:
    """Check if a theme should be active on the given date."""
    rule_type = date_rule.get('type')
    
    if rule_type == 'fixed':
        return _check_fixed_date(date_rule, check_date)
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
            
        except (ValueError, TypeError):
            return False
    
    return False


# ============================================================
# Test Functions
# ============================================================

def test_us_thanksgiving():
    """Test US Thanksgiving (4th Thursday of November)"""
    test_cases = [
        (2024, date(2024, 11, 28)),
        (2025, date(2025, 11, 27)),
        (2026, date(2026, 11, 26)),
        (2023, date(2023, 11, 23)),
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('us_thanksgiving', year)
        assert result == expected, f"Thanksgiving {year}: expected {expected}, got {result}"
        assert result.weekday() == 3, f"Thanksgiving {year} should be Thursday"
    
    print("✅ US Thanksgiving: All tests passed")


def test_black_friday():
    """Test Black Friday (day after Thanksgiving)"""
    test_cases = [
        (2024, date(2024, 11, 29)),
        (2025, date(2025, 11, 28)),
        (2026, date(2026, 11, 27)),
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('black_friday', year)
        assert result == expected, f"Black Friday {year}: expected {expected}, got {result}"
        assert result.weekday() == 4, f"Black Friday {year} should be Friday"
    
    print("✅ Black Friday: All tests passed")


def test_mothers_day():
    """Test Mother's Day (2nd Sunday of May)"""
    test_cases = [
        (2024, date(2024, 5, 12)),
        (2025, date(2025, 5, 11)),
        (2026, date(2026, 5, 10)),
        (2023, date(2023, 5, 14)),
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('mothers_day', year)
        assert result == expected, f"Mother's Day {year}: expected {expected}, got {result}"
        assert result.weekday() == 6, f"Mother's Day {year} should be Sunday"
        assert result.month == 5, f"Mother's Day {year} should be in May"
        assert 8 <= result.day <= 14, f"Mother's Day {year} should be 2nd Sunday (8-14)"
    
    print("✅ Mother's Day: All tests passed")


def test_fathers_day():
    """Test Father's Day (3rd Sunday of June)"""
    test_cases = [
        (2024, date(2024, 6, 16)),
        (2025, date(2025, 6, 15)),
        (2026, date(2026, 6, 21)),
        (2023, date(2023, 6, 18)),
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('fathers_day', year)
        assert result == expected, f"Father's Day {year}: expected {expected}, got {result}"
        assert result.weekday() == 6, f"Father's Day {year} should be Sunday"
        assert result.month == 6, f"Father's Day {year} should be in June"
        assert 15 <= result.day <= 21, f"Father's Day {year} should be 3rd Sunday (15-21)"
    
    print("✅ Father's Day: All tests passed")


def test_mlk_day():
    """Test MLK Day (3rd Monday of January)"""
    test_cases = [
        (2024, date(2024, 1, 15)),
        (2025, date(2025, 1, 20)),
        (2026, date(2026, 1, 19)),
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('mlk_day', year)
        assert result == expected, f"MLK Day {year}: expected {expected}, got {result}"
        assert result.weekday() == 0, f"MLK Day {year} should be Monday"
        assert 15 <= result.day <= 21, f"MLK Day {year} should be 3rd Monday (15-21)"
    
    print("✅ MLK Day: All tests passed")


def test_memorial_day():
    """Test Memorial Day (last Monday of May)"""
    test_cases = [
        (2024, date(2024, 5, 27)),
        (2025, date(2025, 5, 26)),
        (2026, date(2026, 5, 25)),
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('memorial_day', year)
        assert result == expected, f"Memorial Day {year}: expected {expected}, got {result}"
        assert result.weekday() == 0, f"Memorial Day {year} should be Monday"
        assert result.month == 5, f"Memorial Day {year} should be in May"
        assert result.day >= 25, f"Memorial Day {year} should be last Monday"
    
    print("✅ Memorial Day: All tests passed")


def test_labor_day():
    """Test Labor Day (first Monday of September)"""
    test_cases = [
        (2024, date(2024, 9, 2)),
        (2025, date(2025, 9, 1)),
        (2026, date(2026, 9, 7)),
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('labor_day', year)
        assert result == expected, f"Labor Day {year}: expected {expected}, got {result}"
        assert result.weekday() == 0, f"Labor Day {year} should be Monday"
        assert result.month == 9, f"Labor Day {year} should be in September"
        assert result.day <= 7, f"Labor Day {year} should be first Monday"
    
    print("✅ Labor Day: All tests passed")


def test_fixed_date_rules():
    """Test fixed date rule parsing"""
    
    # Christmas (Dec 20-26)
    christmas_rule = {"type": "fixed", "start": "12-20", "end": "12-26"}
    assert _check_fixed_date(christmas_rule, date(2024, 12, 25)) == True
    assert _check_fixed_date(christmas_rule, date(2024, 12, 20)) == True
    assert _check_fixed_date(christmas_rule, date(2024, 12, 26)) == True
    assert _check_fixed_date(christmas_rule, date(2024, 12, 19)) == False
    assert _check_fixed_date(christmas_rule, date(2024, 12, 27)) == False
    
    # Valentine's Day (Feb 12-15)
    valentine_rule = {"type": "fixed", "start": "02-12", "end": "02-15"}
    assert _check_fixed_date(valentine_rule, date(2024, 2, 14)) == True
    assert _check_fixed_date(valentine_rule, date(2024, 2, 11)) == False
    
    # New Year (Year wrap: Dec 30 - Jan 2)
    newyear_rule = {"type": "fixed", "start": "12-30", "end": "01-02"}
    assert _check_fixed_date(newyear_rule, date(2024, 12, 31)) == True
    assert _check_fixed_date(newyear_rule, date(2024, 1, 1)) == True
    assert _check_fixed_date(newyear_rule, date(2024, 1, 2)) == True
    assert _check_fixed_date(newyear_rule, date(2024, 12, 29)) == False
    assert _check_fixed_date(newyear_rule, date(2024, 1, 3)) == False
    
    # Earth Day (Apr 21-23)
    earth_rule = {"type": "fixed", "start": "04-21", "end": "04-23"}
    assert _check_fixed_date(earth_rule, date(2024, 4, 22)) == True
    assert _check_fixed_date(earth_rule, date(2024, 4, 20)) == False
    
    # Pi Day (Mar 13-15)
    pi_rule = {"type": "fixed", "start": "03-13", "end": "03-15"}
    assert _check_fixed_date(pi_rule, date(2024, 3, 14)) == True
    
    # International Women's Day (Mar 7-9)
    womens_rule = {"type": "fixed", "start": "03-07", "end": "03-09"}
    assert _check_fixed_date(womens_rule, date(2024, 3, 8)) == True
    
    # Gandhi Day (Oct 1-3)
    gandhi_rule = {"type": "fixed", "start": "10-01", "end": "10-03"}
    assert _check_fixed_date(gandhi_rule, date(2024, 10, 2)) == True
    
    # Mandela Day (Jul 17-19)
    mandela_rule = {"type": "fixed", "start": "07-17", "end": "07-19"}
    assert _check_fixed_date(mandela_rule, date(2024, 7, 18)) == True
    
    print("✅ Fixed Date Rules: All tests passed")


def test_theme_active_integration():
    """Test is_theme_active with both fixed and dynamic rules"""
    
    # Fixed rule - Christmas
    christmas = {"type": "fixed", "start": "12-20", "end": "12-26"}
    assert is_theme_active(christmas, date(2024, 12, 25)) == True
    assert is_theme_active(christmas, date(2024, 6, 15)) == False
    
    # Dynamic rule - Thanksgiving with offsets
    thanksgiving = {"type": "dynamic", "rule": "us_thanksgiving", "offset_start": -1, "offset_end": 1}
    # 2024 Thanksgiving is Nov 28, so active Nov 27-29
    assert is_theme_active(thanksgiving, date(2024, 11, 27)) == True
    assert is_theme_active(thanksgiving, date(2024, 11, 28)) == True
    assert is_theme_active(thanksgiving, date(2024, 11, 29)) == True
    assert is_theme_active(thanksgiving, date(2024, 11, 26)) == False
    assert is_theme_active(thanksgiving, date(2024, 11, 30)) == False
    
    # Dynamic rule - Mother's Day with offsets
    mothers = {"type": "dynamic", "rule": "mothers_day", "offset_start": -1, "offset_end": 0}
    # 2024 Mother's Day is May 12, so active May 11-12
    assert is_theme_active(mothers, date(2024, 5, 11)) == True
    assert is_theme_active(mothers, date(2024, 5, 12)) == True
    assert is_theme_active(mothers, date(2024, 5, 13)) == False
    
    # Dynamic rule - Father's Day
    fathers = {"type": "dynamic", "rule": "fathers_day", "offset_start": -1, "offset_end": 0}
    # 2024 Father's Day is June 16
    assert is_theme_active(fathers, date(2024, 6, 15)) == True
    assert is_theme_active(fathers, date(2024, 6, 16)) == True
    assert is_theme_active(fathers, date(2024, 6, 17)) == False
    
    print("✅ Theme Active Integration: All tests passed")


def test_edge_cases():
    """Test edge cases and error handling"""
    
    # Unknown dynamic rule
    result = calculate_dynamic_date('unknown_rule', 2024)
    assert result is None, "Unknown rule should return None"
    
    # Invalid fixed date rule
    invalid_rule = {"type": "fixed", "start": "", "end": ""}
    assert _check_fixed_date(invalid_rule, date(2024, 1, 1)) == False
    
    # Invalid type
    invalid_type = {"type": "invalid"}
    assert is_theme_active(invalid_type, date(2024, 1, 1)) == False
    
    # Empty rule
    assert is_theme_active({}, date(2024, 1, 1)) == False
    
    print("✅ Edge Cases: All tests passed")


def print_holiday_calendar():
    """Print holiday calendar for 2025 and 2026"""
    print("\n" + "=" * 60)
    print("📅 Holiday Calendar 2025-2026")
    print("=" * 60)
    
    holidays = [
        ('mlk_day', '🎖️ MLK Day'),
        ('mothers_day', '💐 Mother\'s Day'),
        ('memorial_day', '🇺🇸 Memorial Day'),
        ('fathers_day', '👔 Father\'s Day'),
        ('labor_day', '✊ Labor Day'),
        ('us_thanksgiving', '🦃 Thanksgiving'),
        ('black_friday', '🖤 Black Friday'),
    ]
    
    for year in [2025, 2026]:
        print(f"\n📆 {year}:")
        print("-" * 40)
        for rule, name in holidays:
            result = calculate_dynamic_date(rule, year)
            if result:
                weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][result.weekday()]
                print(f"  {name}: {result.strftime('%B %d')} ({weekday})")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 Holiday Themes Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        test_us_thanksgiving,
        test_black_friday,
        test_mothers_day,
        test_fathers_day,
        test_mlk_day,
        test_memorial_day,
        test_labor_day,
        test_fixed_date_rules,
        test_theme_active_integration,
        test_edge_cases,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: ERROR - {e}")
            failed += 1
    
    print_holiday_calendar()
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
