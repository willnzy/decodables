"""
Unit tests for user_code generation logic.

Tests for infrastructure/repositories/user_repository.py:generate_user_code()

Created: 2026-01-09
Purpose: Verify user_code format includes registration timestamp (YYMMDD+HHMM+random)
"""

import re
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from infrastructure.repositories.user_repository import SupabaseUserRepository


class TestUserCodeGeneration:
    """Test user_code generation with timestamp format."""

    def test_user_code_format_with_timestamp(self):
        """
        Test that generated user_code includes timestamp in format YYMMDD+HHMM+3random.

        Format: {YYMMDD}{HHMM}{RND}
        Example: 260109143X7Y (registered on 2026-01-09 14:30)

        Length: 13 chars (6 + 4 + 3)
        """
        # Mock Supabase client
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Verify length (13 chars: YYMMDD + HHMM + 3 random)
        assert len(user_code) == 13, f"Expected 13 chars, got {len(user_code)}"

        # Verify format: YYMMDD (6 digits) + HHMM (4 digits) + 3 random alphanumeric
        pattern = r'^(\d{6})(\d{4})([A-Z0-9]{3})$'
        match = re.match(pattern, user_code)
        assert match is not None, f"user_code '{user_code}' does not match expected format YYMMDDHHMMRRR"

        date_part, time_part, random_part = match.groups()

        # Verify date part is valid (YYMMDD)
        now = datetime.now(timezone.utc)
        expected_date = now.strftime("%y%m%d")
        assert date_part == expected_date, f"Date part '{date_part}' does not match current date '{expected_date}'"

        # Verify time part is valid (HHMM) - within 1 minute tolerance
        expected_time = now.strftime("%H%M")
        time_diff = abs(int(time_part) - int(expected_time))
        assert time_diff <= 1, f"Time part '{time_part}' differs from expected '{expected_time}' by more than 1 minute"

        # Verify random part is alphanumeric
        assert random_part.isalnum(), f"Random part '{random_part}' should be alphanumeric"
        assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in random_part), \
            f"Random part '{random_part}' should only contain uppercase letters and digits"

    def test_user_code_uniqueness_check(self):
        """Test that generate_user_code() checks for uniqueness in database."""
        # Mock Supabase client with first code collision, second code unique
        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_execute.execute.side_effect = [
            MagicMock(data=["existing_user"]),  # First attempt: collision
            MagicMock(data=[]),  # Second attempt: unique
        ]
        mock_client.table.return_value.select.return_value.eq.return_value = mock_execute

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Verify it checked twice (first collision, second success)
        assert mock_execute.execute.call_count == 2

        # Verify final code is still valid format
        assert len(user_code) == 13
        assert re.match(r'^\d{10}[A-Z0-9]{3}$', user_code)

    def test_user_code_fallback_to_14_chars(self):
        """Test that after 10 collisions, it falls back to 14-char code (4 random chars)."""
        # Mock Supabase client with 10 collisions
        mock_client = MagicMock()
        mock_execute = MagicMock()

        # First 10 attempts: collision (no success)
        collision_responses = [MagicMock(data=["existing"]) for _ in range(10)]
        mock_execute.execute.side_effect = collision_responses
        mock_client.table.return_value.select.return_value.eq.return_value = mock_execute

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Verify it checked 10 times (then gave up and returned fallback without check)
        assert mock_execute.execute.call_count == 10

        # Verify fallback code is 14 chars (YYMMDD + HHMM + 4 random)
        assert len(user_code) == 14, f"Fallback code should be 14 chars, got {len(user_code)}"
        assert re.match(r'^\d{10}[A-Z0-9]{4}$', user_code), \
            f"Fallback code '{user_code}' should be YYMMDDHHMMRRRR format"

    def test_user_code_timestamp_readability(self):
        """
        Test that admin can easily parse registration time from user_code.

        This is the core purpose of the timestamp-based format.
        """
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        repo = SupabaseUserRepository(mock_client)
        user_code = repo.generate_user_code()

        # Extract timestamp parts
        date_part = user_code[:6]  # YYMMDD
        time_part = user_code[6:10]  # HHMM

        # Verify admin can parse registration date
        year = 2000 + int(date_part[:2])
        month = int(date_part[2:4])
        day = int(date_part[4:6])
        hour = int(time_part[:2])
        minute = int(time_part[2:4])

        # Verify parsed values are reasonable
        now = datetime.now(timezone.utc)
        assert year == now.year
        assert 1 <= month <= 12
        assert 1 <= day <= 31
        assert 0 <= hour <= 23
        assert 0 <= minute <= 59

        print(f"✅ Admin can read: user_code '{user_code}' = {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}")
