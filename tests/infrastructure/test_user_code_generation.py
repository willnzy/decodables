"""
Unit tests for user_code generation logic.

Tests for infrastructure/repositories/user_repository.py:generate_user_code()

Created: 2026-01-09
Updated: 2026-01-09 - Corrected format to YYMMDD_HHMMSSmmmm_UUUUUUU_RRR

Purpose: Verify user_code format includes:
1. Registration timestamp (date + time with milliseconds)
2. Total user count at registration time
3. Random suffix for additional uniqueness
"""

import re
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from infrastructure.repositories.user_repository import SupabaseUserRepository


class TestUserCodeGeneration:
    """Test user_code generation with correct format."""

    def test_user_code_format_complete(self):
        """
        Test that generated user_code matches the correct format.

        Format: YYMMDDHHMMSSmmmm UUUUUUURRRFormat (26 digits, NO separators):
        Example: 26010914305278900123456789

        Parts:
        - YYMMDD: 6 digit date
        - HHMMSS: 6 digit time
        - mmmm: 4 digit milliseconds (0.1ms precision)
        - UUUUUUU: 7 digit user count (zero-padded)
        - RRR: 3 random digits
        """
        # Mock Supabase client
        mock_client = MagicMock()

        # Mock user count query
        mock_count_result = MagicMock()
        mock_count_result.count = 1234

        # Mock for uniqueness check (should return no existing data)
        mock_exists_result = MagicMock()
        mock_exists_result.data = []

        # Set up mock to handle both count query and uniqueness check
        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value

        # First call: count query
        mock_select.execute.return_value = mock_count_result

        # Second call: uniqueness check (via .eq().execute())
        mock_eq = mock_select.eq.return_value
        mock_eq.execute.return_value = mock_exists_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Verify total length (26 digits: 6 + 6 + 4 + 7 + 3)
        assert len(user_code) == 26, f"Expected 26 digits, got {len(user_code)}: {user_code}"

        # Verify format: YYMMDDHHMMSS + mmmm + UUUUUUU + RRR (all digits, no separators)
        pattern = r'^(\d{6})(\d{6})(\d{4})(\d{7})(\d{3})$'
        match = re.match(pattern, user_code)
        assert match is not None, f"user_code '{user_code}' does not match expected format"

        date_part, time_part, ms_part, count_part, random_part = match.groups()

        # Verify date part is valid (YYMMDD)
        now = datetime.now(timezone.utc)
        expected_date = now.strftime("%y%m%d")
        assert date_part == expected_date, f"Date part '{date_part}' does not match current date '{expected_date}'"

        # Verify time part format (HHMMSS)
        assert len(time_part) == 6, f"Time part should be 6 digits, got {len(time_part)}"
        hours = int(time_part[0:2])
        minutes = int(time_part[2:4])
        seconds = int(time_part[4:6])
        assert 0 <= hours <= 23, f"Invalid hours: {hours}"
        assert 0 <= minutes <= 59, f"Invalid minutes: {minutes}"
        assert 0 <= seconds <= 59, f"Invalid seconds: {seconds}"

        # Verify millisecond part (4 digits: 0-9999, 0.1ms precision)
        assert len(ms_part) == 4, f"Millisecond part should be 4 digits, got {len(ms_part)}"
        milliseconds = int(ms_part)
        assert 0 <= milliseconds <= 9999, f"Invalid milliseconds: {milliseconds}"

        # Verify count part (7 digits, zero-padded, +1 for the user being created)
        assert count_part == "0001235", f"Count part should be '0001235' (1234+1), got '{count_part}'"
        assert int(count_part) == 1235, f"Count part should represent user #1235 (count was 1234, +1)"

        # Verify random part is all digits (3 digits: 000-999)
        assert random_part.isdigit(), f"Random part '{random_part}' should be all digits"
        assert len(random_part) == 3, f"Random part should be 3 digits"
        random_value = int(random_part)
        assert 0 <= random_value <= 999, f"Random value should be 0-999, got {random_value}"

    def test_user_code_zero_users(self):
        """Test user_code generation when no users exist yet (count = 0)."""
        mock_client = MagicMock()

        # Mock zero user count
        mock_count_result = MagicMock()
        mock_count_result.count = 0

        # Mock for uniqueness check
        mock_exists_result = MagicMock()
        mock_exists_result.data = []

        # Set up mock to handle both queries
        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_select.execute.return_value = mock_count_result
        mock_select.eq.return_value.execute.return_value = mock_exists_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Extract count part (characters 16-23: 7 digits)
        count_part = user_code[16:23]

        # Verify zero count (+1 for new user) is zero-padded to 7 digits
        assert count_part == "0000001", f"Count part for first user should be '0000001', got '{count_part}'"

    def test_user_code_large_user_count(self):
        """Test user_code generation with large user count (999,999)."""
        mock_client = MagicMock()

        # Mock large user count
        mock_count_result = MagicMock()
        mock_count_result.count = 999999

        # Mock for uniqueness check
        mock_exists_result = MagicMock()
        mock_exists_result.data = []

        # Set up mock to handle both queries
        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_select.execute.return_value = mock_count_result
        mock_select.eq.return_value.execute.return_value = mock_exists_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Extract count part (characters 16-23: 7 digits)
        count_part = user_code[16:23]

        # Verify large count (+1) is zero-padded to 7 digits
        assert count_part == "1000000", f"Count part for user #1,000,000 should be '1000000', got '{count_part}'"

    def test_user_code_max_user_count(self):
        """Test user_code generation with maximum 7-digit user count (9,999,999)."""
        mock_client = MagicMock()

        # Mock maximum 7-digit user count
        mock_count_result = MagicMock()
        mock_count_result.count = 9999999
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Extract count part
        parts = user_code.split('_')
        count_part = parts[2]

        # Verify max count fits in 7 digits
        assert count_part == "9999999", f"Count part for 9,999,999 users should be '9999999', got '{count_part}'"

    def test_user_code_none_count_fallback(self):
        """Test user_code generation when count query returns None."""
        mock_client = MagicMock()

        # Mock None count (query failure)
        mock_count_result = MagicMock()
        mock_count_result.count = None
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Extract count part
        parts = user_code.split('_')
        count_part = parts[2]

        # Verify fallback to 0 when count is None
        assert count_part == "0000000", f"Count part should fallback to '0000000' when count is None, got '{count_part}'"

    def test_user_code_timestamp_readability(self):
        """
        Test that admin can easily parse registration time and user count from user_code.

        This is the core purpose of the format.
        """
        mock_client = MagicMock()

        mock_count_result = MagicMock()
        mock_count_result.count = 12345
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Split into parts
        parts = user_code.split('_')
        assert len(parts) == 4, f"Expected 4 parts, got {len(parts)}"

        date_part, time_part, count_part, random_part = parts

        # Parse date
        year = 2000 + int(date_part[:2])
        month = int(date_part[2:4])
        day = int(date_part[4:6])

        # Parse time
        hour = int(time_part[:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6])
        subsecond = int(time_part[6:10])  # 4 digits: 0-9999

        # Parse user count
        user_count = int(count_part)

        # Verify parsed values are reasonable
        now = datetime.now(timezone.utc)
        assert year == now.year, f"Parsed year {year} should match current year {now.year}"
        assert 1 <= month <= 12, f"Invalid month: {month}"
        assert 1 <= day <= 31, f"Invalid day: {day}"
        assert 0 <= hour <= 23, f"Invalid hour: {hour}"
        assert 0 <= minute <= 59, f"Invalid minute: {minute}"
        assert 0 <= second <= 59, f"Invalid second: {second}"
        assert 0 <= subsecond <= 9999, f"Invalid subsecond: {subsecond}"
        assert user_count == 12345, f"User count should be 12,345, got {user_count}"

        print(f"✅ Admin can read: user_code '{user_code}'")
        print(f"   = {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}.{subsecond:04d}")
        print(f"   = User #{user_count:,} registered")

    def test_user_code_uniqueness_with_milliseconds(self):
        """
        Test that millisecond precision + user count + random suffix ensures uniqueness.

        Even if two users register in the same second, they should get different codes due to:
        1. Different millisecond values
        2. Different user counts
        3. Different random suffixes
        """
        mock_client = MagicMock()

        # Simulate two users registering close together
        mock_count_result_1 = MagicMock()
        mock_count_result_1.count = 100

        mock_count_result_2 = MagicMock()
        mock_count_result_2.count = 101

        repo = SupabaseUserRepository(mock_client)

        # First user
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result_1
        code1 = repo.generate_user_code()

        # Second user (slightly later, different count)
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result_2
        code2 = repo.generate_user_code()

        # Verify codes are different
        assert code1 != code2, f"Two user_codes should be different: '{code1}' vs '{code2}'"

        # Verify count parts are different
        count1 = code1.split('_')[2]
        count2 = code2.split('_')[2]
        assert count1 == "0000100", f"First user count should be 100, got {count1}"
        assert count2 == "0000101", f"Second user count should be 101, got {count2}"
