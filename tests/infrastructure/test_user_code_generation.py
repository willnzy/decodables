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

        Format: {YYMMDD}_{HHMMSSmmmm}_{UUUUUUU}_{RRR}
        Example: 260109_1430251234_0001234_A7X

        Parts:
        - YYMMDD: 6 digit date
        - HHMMSSmmmm: 10 digit time with sub-second precision (4 digits = microseconds/100)
        - UUUUUUU: 7 digit user count (zero-padded)
        - RRR: 3 random alphanumeric chars
        """
        # Mock Supabase client
        mock_client = MagicMock()

        # Mock user count query
        mock_count_result = MagicMock()
        mock_count_result.count = 1234
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Verify total length (29 chars: 6 + 1 + 10 + 1 + 7 + 1 + 3)
        assert len(user_code) == 29, f"Expected 29 chars, got {len(user_code)}: {user_code}"

        # Verify format: YYMMDD_HHMMSSmmmm_UUUUUUU_RRR
        pattern = r'^(\d{6})_(\d{10})_(\d{7})_([A-Z0-9]{3})$'
        match = re.match(pattern, user_code)
        assert match is not None, f"user_code '{user_code}' does not match expected format"

        date_part, time_part, count_part, random_part = match.groups()

        # Verify date part is valid (YYMMDD)
        now = datetime.now(timezone.utc)
        expected_date = now.strftime("%y%m%d")
        assert date_part == expected_date, f"Date part '{date_part}' does not match current date '{expected_date}'"

        # Verify time part format (HHMMSSmmmm)
        assert len(time_part) == 10, f"Time part should be 10 chars, got {len(time_part)}"
        hours = int(time_part[0:2])
        minutes = int(time_part[2:4])
        seconds = int(time_part[4:6])
        subsecond = int(time_part[6:10])  # 4 digits: 0-9999
        assert 0 <= hours <= 23, f"Invalid hours: {hours}"
        assert 0 <= minutes <= 59, f"Invalid minutes: {minutes}"
        assert 0 <= seconds <= 59, f"Invalid seconds: {seconds}"
        assert 0 <= subsecond <= 9999, f"Invalid subsecond: {subsecond}"

        # Verify count part (7 digits, zero-padded)
        assert count_part == "0001234", f"Count part should be '0001234', got '{count_part}'"
        assert int(count_part) == 1234, f"Count part should represent 1234 users"

        # Verify random part is alphanumeric
        assert random_part.isalnum(), f"Random part '{random_part}' should be alphanumeric"
        assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in random_part), \
            f"Random part '{random_part}' should only contain uppercase letters and digits"

    def test_user_code_zero_users(self):
        """Test user_code generation when no users exist yet (count = 0)."""
        mock_client = MagicMock()

        # Mock zero user count
        mock_count_result = MagicMock()
        mock_count_result.count = 0
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Extract count part
        parts = user_code.split('_')
        assert len(parts) == 4, f"Expected 4 parts separated by underscore, got {len(parts)}"
        count_part = parts[2]

        # Verify zero count is zero-padded to 7 digits
        assert count_part == "0000000", f"Count part for 0 users should be '0000000', got '{count_part}'"

    def test_user_code_large_user_count(self):
        """Test user_code generation with large user count (999,999)."""
        mock_client = MagicMock()

        # Mock large user count
        mock_count_result = MagicMock()
        mock_count_result.count = 999999
        mock_client.table.return_value.select.return_value.execute.return_value = mock_count_result

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Extract count part
        parts = user_code.split('_')
        count_part = parts[2]

        # Verify large count is zero-padded to 7 digits
        assert count_part == "0999999", f"Count part for 999,999 users should be '0999999', got '{count_part}'"

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
