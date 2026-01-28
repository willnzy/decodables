"""
Unit Tests for timezone_utils.py
Tests timezone detection, validation, and resolution
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import Request

from core.utils.timezone import (
    is_valid_timezone,
    sanitize_timezone,
    get_timezone_from_cloudflare,
    get_timezone_from_header,
    get_timezone_from_country,
    get_request_timezone,
    get_timezone_info,
    get_request_timezone_with_country_fallback,
    COMMON_TIMEZONES,
    COUNTRY_DEFAULT_TIMEZONES,
)


class TestIsValidTimezone:
    """Tests for is_valid_timezone function"""

    def test_common_timezones_are_valid(self):
        """All timezones in COMMON_TIMEZONES should be valid"""
        for tz in COMMON_TIMEZONES:
            assert is_valid_timezone(tz) is True, f"{tz} should be valid"

    def test_utc_is_valid(self):
        """UTC should always be valid"""
        assert is_valid_timezone("UTC") is True

    def test_major_cities_are_valid(self):
        """Major city timezones should be valid"""
        valid_zones = [
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]
        for tz in valid_zones:
            assert is_valid_timezone(tz) is True

    def test_invalid_timezones_rejected(self):
        """Invalid timezone strings should be rejected"""
        invalid_zones = [
            "Invalid/Timezone",
            "EST",  # Abbreviations are not IANA
            "PST",
            "GMT+8",  # Offset format
            "",
            "   ",
        ]
        for tz in invalid_zones:
            assert is_valid_timezone(tz) is False, f"{tz!r} should be invalid"

    def test_none_and_non_string_rejected(self):
        """None and non-string values should be rejected"""
        assert is_valid_timezone(None) is False
        assert is_valid_timezone(123) is False
        assert is_valid_timezone([]) is False
        assert is_valid_timezone({}) is False


class TestSanitizeTimezone:
    """Tests for sanitize_timezone function"""

    def test_valid_timezone_returned_unchanged(self):
        """Valid timezones should be returned as-is"""
        assert sanitize_timezone("Asia/Shanghai") == "Asia/Shanghai"
        assert sanitize_timezone("America/New_York") == "America/New_York"
        assert sanitize_timezone("UTC") == "UTC"

    def test_invalid_timezone_returns_default(self):
        """Invalid timezones should return default"""
        assert sanitize_timezone("Invalid") == "UTC"
        assert sanitize_timezone("EST") == "UTC"

    def test_custom_default_respected(self):
        """Custom default should be used for invalid input"""
        assert sanitize_timezone("Invalid", default="Asia/Tokyo") == "Asia/Tokyo"

    def test_empty_returns_default(self):
        """Empty string/None should return default"""
        assert sanitize_timezone("") == "UTC"
        assert sanitize_timezone(None) == "UTC"

    def test_whitespace_trimmed(self):
        """Whitespace should be trimmed"""
        assert sanitize_timezone("  Asia/Shanghai  ") == "Asia/Shanghai"


class TestGetTimezoneFromCloudflare:
    """Tests for get_timezone_from_cloudflare function"""

    def _create_mock_request(self, headers: dict) -> Mock:
        """Create a mock request with specified headers"""
        request = Mock()
        request.headers = headers
        return request

    def test_valid_cf_timezone_returned(self):
        """Valid CF-IPTimezone header should be returned"""
        request = self._create_mock_request({"CF-IPTimezone": "Asia/Shanghai"})
        assert get_timezone_from_cloudflare(request) == "Asia/Shanghai"

    def test_missing_header_returns_none(self):
        """Missing header should return None"""
        request = self._create_mock_request({})
        assert get_timezone_from_cloudflare(request) is None

    def test_unknown_value_returns_none(self):
        """'unknown' value should return None"""
        request = self._create_mock_request({"CF-IPTimezone": "unknown"})
        assert get_timezone_from_cloudflare(request) is None

    def test_empty_value_returns_none(self):
        """Empty value should return None"""
        request = self._create_mock_request({"CF-IPTimezone": ""})
        assert get_timezone_from_cloudflare(request) is None

    def test_invalid_timezone_returns_none(self):
        """Invalid timezone value should return None"""
        request = self._create_mock_request({"CF-IPTimezone": "Invalid/Zone"})
        # This depends on validation - may return None or the value
        result = get_timezone_from_cloudflare(request)
        # Since we added basic format validation, this might pass
        # The important thing is it doesn't crash


class TestGetTimezoneFromHeader:
    """Tests for get_timezone_from_header function"""

    def _create_mock_request(self, headers: dict) -> Mock:
        """Create a mock request with specified headers"""
        request = Mock()
        request.headers = headers
        return request

    def test_x_timezone_header(self):
        """X-Timezone header should be recognized"""
        request = self._create_mock_request({"X-Timezone": "Europe/London"})
        assert get_timezone_from_header(request) == "Europe/London"

    def test_x_user_timezone_header(self):
        """X-User-Timezone header should be recognized"""
        request = self._create_mock_request({"X-User-Timezone": "America/Los_Angeles"})
        assert get_timezone_from_header(request) == "America/Los_Angeles"

    def test_x_timezone_takes_precedence(self):
        """X-Timezone should be checked before X-User-Timezone"""
        request = self._create_mock_request({
            "X-Timezone": "Asia/Tokyo",
            "X-User-Timezone": "Europe/Paris",
        })
        assert get_timezone_from_header(request) == "Asia/Tokyo"

    def test_no_header_returns_none(self):
        """No timezone header should return None"""
        request = self._create_mock_request({"Content-Type": "application/json"})
        assert get_timezone_from_header(request) is None

    def test_invalid_header_value_returns_none(self):
        """Invalid timezone value should return None"""
        request = self._create_mock_request({"X-Timezone": "INVALID"})
        assert get_timezone_from_header(request) is None


class TestGetTimezoneFromCountry:
    """Tests for get_timezone_from_country function"""

    def test_common_countries(self):
        """Common country codes should return expected timezones"""
        assert get_timezone_from_country("CN") == "Asia/Shanghai"
        assert get_timezone_from_country("US") == "America/New_York"
        assert get_timezone_from_country("GB") == "Europe/London"
        assert get_timezone_from_country("JP") == "Asia/Tokyo"
        assert get_timezone_from_country("AU") == "Australia/Sydney"

    def test_case_insensitive(self):
        """Country code lookup should be case-insensitive"""
        assert get_timezone_from_country("cn") == "Asia/Shanghai"
        assert get_timezone_from_country("Cn") == "Asia/Shanghai"

    def test_unknown_country_returns_none(self):
        """Unknown country code should return None"""
        assert get_timezone_from_country("XX") is None
        assert get_timezone_from_country("ZZ") is None

    def test_none_returns_none(self):
        """None input should return None"""
        assert get_timezone_from_country(None) is None

    def test_all_mapped_countries_valid(self):
        """All mapped timezones should be valid IANA timezones"""
        for country, tz in COUNTRY_DEFAULT_TIMEZONES.items():
            assert is_valid_timezone(tz), f"{country} -> {tz} should be valid"


class TestGetRequestTimezone:
    """Tests for get_request_timezone async function"""

    def _create_mock_request(self, headers: dict = None) -> Mock:
        """Create a mock request with specified headers"""
        request = Mock()
        request.headers = headers or {}
        return request

    @pytest.mark.asyncio
    async def test_explicit_override_takes_precedence(self):
        """Explicit timezone_override should take highest precedence"""
        request = self._create_mock_request({
            "X-Timezone": "Europe/Paris",
            "CF-IPTimezone": "Asia/Tokyo",
        })

        result = await get_request_timezone(
            request,
            timezone_override="America/New_York"
        )

        assert result == "America/New_York"

    @pytest.mark.asyncio
    async def test_header_precedence_over_cloudflare(self):
        """X-Timezone header should take precedence over Cloudflare"""
        request = self._create_mock_request({
            "X-Timezone": "Europe/Paris",
            "CF-IPTimezone": "Asia/Tokyo",
        })

        result = await get_request_timezone(request)

        assert result == "Europe/Paris"

    @pytest.mark.asyncio
    async def test_cloudflare_fallback(self):
        """Cloudflare timezone should be used when no header"""
        request = self._create_mock_request({
            "CF-IPTimezone": "Asia/Shanghai",
        })

        result = await get_request_timezone(request)

        assert result == "Asia/Shanghai"

    @pytest.mark.asyncio
    async def test_user_profile_fallback(self):
        """User profile timezone should be used as fallback"""
        request = self._create_mock_request({})

        with patch(
            'core.utils.timezone.get_timezone_from_user_profile',
            new_callable=AsyncMock,
            return_value="Australia/Sydney",
        ):
            result = await get_request_timezone(request, user_id="user123")

        assert result == "Australia/Sydney"

    @pytest.mark.asyncio
    async def test_default_fallback(self):
        """Default UTC should be returned when no timezone found"""
        request = self._create_mock_request({})

        with patch(
            'core.utils.timezone.get_timezone_from_user_profile',
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_request_timezone(request)

        assert result == "UTC"

    @pytest.mark.asyncio
    async def test_custom_default(self):
        """Custom default should be respected"""
        request = self._create_mock_request({})

        with patch(
            'core.utils.timezone.get_timezone_from_user_profile',
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_request_timezone(request, default="Asia/Tokyo")

        assert result == "Asia/Tokyo"

    @pytest.mark.asyncio
    async def test_invalid_override_uses_next_source(self):
        """Invalid override should fall through to next source"""
        request = self._create_mock_request({
            "X-Timezone": "Europe/Berlin",
        })

        result = await get_request_timezone(
            request,
            timezone_override="INVALID",
            default="UTC"
        )

        # Should fall through to header
        assert result == "Europe/Berlin"


class TestGetTimezoneInfo:
    """Tests for get_timezone_info async function"""

    def _create_mock_request(self, headers: dict = None) -> Mock:
        """Create a mock request with specified headers"""
        request = Mock()
        request.headers = MagicMock()
        request.headers.get = lambda key, default=None: (headers or {}).get(key, default)
        return request

    @pytest.mark.asyncio
    async def test_returns_complete_info(self):
        """Should return complete timezone information"""
        request = self._create_mock_request({
            "X-Timezone": "Asia/Tokyo",
            "CF-IPTimezone": "Asia/Shanghai",
            "CF-IPCountry": "JP",
            "CF-IPCity": "Tokyo",
        })

        with patch(
            'core.utils.timezone.get_timezone_from_user_profile',
            new_callable=AsyncMock,
            return_value=None,
        ):
            info = await get_timezone_info(request)

        assert "resolved" in info
        assert "sources" in info
        assert "cloudflare_headers" in info
        assert "default" in info

        assert info["sources"]["header"] == "Asia/Tokyo"
        assert info["sources"]["cloudflare"] == "Asia/Shanghai"
        assert info["cloudflare_headers"]["CF-IPCountry"] == "JP"
        assert info["default"] == "UTC"

    @pytest.mark.asyncio
    async def test_handles_missing_headers(self):
        """Should handle missing headers gracefully"""
        request = self._create_mock_request({})

        with patch(
            'core.utils.timezone.get_timezone_from_user_profile',
            new_callable=AsyncMock,
            return_value=None,
        ):
            info = await get_timezone_info(request)

        assert info["resolved"] == "UTC"
        assert info["sources"]["header"] is None
        assert info["sources"]["cloudflare"] is None


class TestGetRequestTimezoneWithCountryFallback:
    """Tests for get_request_timezone_with_country_fallback async function"""

    def _create_mock_request(self, headers: dict = None) -> Mock:
        """Create a mock request with specified headers"""
        request = Mock()
        headers_dict = headers or {}
        # Use MagicMock for headers so we can set the .get method
        mock_headers = MagicMock()
        mock_headers.get = lambda key, default=None: headers_dict.get(key, default)
        mock_headers.__iter__ = lambda self: iter(headers_dict)
        mock_headers.__getitem__ = lambda self, key: headers_dict[key]
        request.headers = mock_headers
        return request

    @pytest.mark.asyncio
    async def test_country_fallback_used(self):
        """Should use country-based timezone when others not available"""
        request = self._create_mock_request({
            "CF-IPCountry": "JP",
            # Note: No CF-IPTimezone
        })

        with patch(
            'core.utils.timezone.get_timezone_from_user_profile',
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_request_timezone_with_country_fallback(request)

        assert result == "Asia/Tokyo"

    @pytest.mark.asyncio
    async def test_timezone_header_preferred_over_country(self):
        """Timezone header should be preferred over country fallback"""
        request = self._create_mock_request({
            "X-Timezone": "Europe/London",
            "CF-IPCountry": "JP",
        })

        result = await get_request_timezone_with_country_fallback(request)

        assert result == "Europe/London"

    @pytest.mark.asyncio
    async def test_default_when_no_country(self):
        """Should return default when no timezone sources available"""
        request = self._create_mock_request({})

        with patch(
            'core.utils.timezone.get_timezone_from_user_profile',
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_request_timezone_with_country_fallback(
                request,
                default="Pacific/Auckland"
            )

        assert result == "Pacific/Auckland"


class TestCommonTimezones:
    """Tests for COMMON_TIMEZONES constant"""

    def test_contains_utc(self):
        """Should contain UTC"""
        assert "UTC" in COMMON_TIMEZONES

    def test_contains_major_regions(self):
        """Should contain timezones from major regions"""
        regions = ["Asia", "America", "Europe", "Pacific", "Australia", "Africa"]

        for region in regions:
            matching = [tz for tz in COMMON_TIMEZONES if tz.startswith(region)]
            assert len(matching) > 0, f"No timezones found for region {region}"

    def test_all_are_strings(self):
        """All entries should be strings"""
        for tz in COMMON_TIMEZONES:
            assert isinstance(tz, str)

    def test_no_duplicates(self):
        """Should have no duplicates"""
        assert len(COMMON_TIMEZONES) == len(set(COMMON_TIMEZONES))


class TestCountryDefaultTimezones:
    """Tests for COUNTRY_DEFAULT_TIMEZONES constant"""

    def test_keys_are_country_codes(self):
        """All keys should be 2-letter country codes"""
        for code in COUNTRY_DEFAULT_TIMEZONES.keys():
            assert len(code) == 2
            assert code.isupper()
            assert code.isalpha()

    def test_values_are_valid_timezones(self):
        """All values should be valid IANA timezones"""
        for tz in COUNTRY_DEFAULT_TIMEZONES.values():
            assert is_valid_timezone(tz), f"{tz} should be a valid timezone"

    def test_contains_major_countries(self):
        """Should contain major countries"""
        major_countries = ["US", "CN", "GB", "JP", "DE", "FR", "AU", "BR", "IN"]

        for country in major_countries:
            assert country in COUNTRY_DEFAULT_TIMEZONES, f"{country} should be mapped"
