"""
Tests for Holiday Themes date calculation.

Run with: python -m pytest tests/test_themes.py -v
Or directly: python tests/test_themes.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from routers.themes import calculate_dynamic_date, is_theme_active, _check_fixed_date

# ============================================================
# Test Dynamic Date Calculations
# ============================================================

def test_us_thanksgiving():
    """Test US Thanksgiving (4th Thursday of November)"""
    # Known Thanksgiving dates
    test_cases = [
        (2024, date(2024, 11, 28)),  # Nov 28, 2024
        (2025, date(2025, 11, 27)),  # Nov 27, 2025
        (2026, date(2026, 11, 26)),  # Nov 26, 2026
        (2023, date(2023, 11, 23)),  # Nov 23, 2023
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('us_thanksgiving', year)
        assert result == expected, f"Thanksgiving {year}: expected {expected}, got {result}"
        # Verify it's a Thursday (weekday 3)
        assert result.weekday() == 3, f"Thanksgiving {year} should be Thursday, got weekday {result.weekday()}"
    
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
        # Verify it's a Friday (weekday 4)
        assert result.weekday() == 4, f"Black Friday {year} should be Friday"
    
    print("✅ Black Friday: All tests passed")


def test_mothers_day():
    """Test Mother's Day (2nd Sunday of May)"""
    test_cases = [
        (2024, date(2024, 5, 12)),  # May 12, 2024
        (2025, date(2025, 5, 11)),  # May 11, 2025
        (2026, date(2026, 5, 10)),  # May 10, 2026
        (2023, date(2023, 5, 14)),  # May 14, 2023
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('mothers_day', year)
        assert result == expected, f"Mother's Day {year}: expected {expected}, got {result}"
        # Verify it's a Sunday (weekday 6)
        assert result.weekday() == 6, f"Mother's Day {year} should be Sunday, got weekday {result.weekday()}"
        # Verify it's in May
        assert result.month == 5, f"Mother's Day {year} should be in May"
        # Verify it's between 8th and 14th (2nd week)
        assert 8 <= result.day <= 14, f"Mother's Day {year} should be 2nd Sunday (8-14), got day {result.day}"
    
    print("✅ Mother's Day: All tests passed")


def test_fathers_day():
    """Test Father's Day (3rd Sunday of June)"""
    test_cases = [
        (2024, date(2024, 6, 16)),  # June 16, 2024
        (2025, date(2025, 6, 15)),  # June 15, 2025
        (2026, date(2026, 6, 21)),  # June 21, 2026
        (2023, date(2023, 6, 18)),  # June 18, 2023
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('fathers_day', year)
        assert result == expected, f"Father's Day {year}: expected {expected}, got {result}"
        # Verify it's a Sunday (weekday 6)
        assert result.weekday() == 6, f"Father's Day {year} should be Sunday, got weekday {result.weekday()}"
        # Verify it's in June
        assert result.month == 6, f"Father's Day {year} should be in June"
        # Verify it's between 15th and 21st (3rd week)
        assert 15 <= result.day <= 21, f"Father's Day {year} should be 3rd Sunday (15-21), got day {result.day}"
    
    print("✅ Father's Day: All tests passed")


def test_mlk_day():
    """Test MLK Day (3rd Monday of January)"""
    test_cases = [
        (2024, date(2024, 1, 15)),  # Jan 15, 2024
        (2025, date(2025, 1, 20)),  # Jan 20, 2025
        (2026, date(2026, 1, 19)),  # Jan 19, 2026
    ]
    
    for year, expected in test_cases:
        result = calculate_dynamic_date('mlk_day', year)
        assert result == expected, f"MLK Day {year}: expected {expected}, got {result}"
        # Verify it's a Monday (weekday 0)
        assert result.weekday() == 0, f"MLK Day {year} should be Monday, got weekday {result.weekday()}"
        # Verify it's between 15th and 21st (3rd week)
        assert 15 <= result.day <= 21, f"MLK Day {year} should be 3rd Monday (15-21), got day {result.day}"
    
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
        # Verify it's a Monday
        assert result.weekday() == 0, f"Memorial Day {year} should be Monday"
        # Verify it's in May
        assert result.month == 5, f"Memorial Day {year} should be in May"
        # Verify it's in the last week (25-31)
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
        # Verify it's a Monday
        assert result.weekday() == 0, f"Labor Day {year} should be Monday"
        # Verify it's in September
        assert result.month == 9, f"Labor Day {year} should be in September"
        # Verify it's in the first week (1-7)
        assert result.day <= 7, f"Labor Day {year} should be first Monday"
    
    print("✅ Labor Day: All tests passed")


# ============================================================
# Test Fixed Date Rules
# ============================================================

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
    assert _check_fixed_date(pi_rule, date(2024, 3, 14)) == True  # 3.14
    
    print("✅ Fixed Date Rules: All tests passed")


# ============================================================
# Test is_theme_active with full rules
# ============================================================

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
    
    print("✅ Theme Active Integration: All tests passed")


# ============================================================
# Test Edge Cases
# ============================================================

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


# ============================================================
# Test All New Holidays for Current Year
# ============================================================

def test_all_2025_holidays():
    """Verify all holidays for 2025"""
    print("\n📅 2025 Holiday Calendar:")
    print("-" * 50)
    
    holidays = [
        ('us_thanksgiving', 'Thanksgiving'),
        ('black_friday', 'Black Friday'),
        ('mothers_day', "Mother's Day"),
        ('fathers_day', "Father's Day"),
        ('mlk_day', 'MLK Day'),
        ('memorial_day', 'Memorial Day'),
        ('labor_day', 'Labor Day'),
    ]
    
    for rule, name in holidays:
        result = calculate_dynamic_date(rule, 2025)
        if result:
            weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][result.weekday()]
            print(f"  {name}: {result.strftime('%B %d, %Y')} ({weekday})")
        else:
            print(f"  {name}: Not calculated")
    
    print("-" * 50)


# ============================================================
# Run All Tests
# ============================================================

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
    
    # Print 2025 calendar
    test_all_2025_holidays()
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
