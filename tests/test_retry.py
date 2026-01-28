"""
Tests for core.database.retry module v2.0.

Covers:
- Network error pattern matching
- PostgREST APIError transient code detection
- Cloudflare/Supabase error pattern matching
- Jitter delay behavior
- Sync and async retry decorators
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from core.database.retry import (
    is_retryable_error,
    _is_postgrest_transient_error,
    _jittered_delay,
    retry_on_network_error,
    retry_on_network_error_async,
    RETRYABLE_ERROR_PATTERNS,
    RETRYABLE_POSTGREST_CODES,
)


# ---------------------------------------------------------------------------
# Helpers: Fake PostgREST APIError
# ---------------------------------------------------------------------------

class FakeAPIError(Exception):
    """Mimics postgrest.exceptions.APIError with code and message attrs."""

    def __init__(self, message: str, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    # Make type(error).__name__ == 'APIError'
    pass


# Rename class so __name__ matches the real PostgREST exception
FakeAPIError.__name__ = 'APIError'


# ---------------------------------------------------------------------------
# Tests: _is_postgrest_transient_error
# ---------------------------------------------------------------------------

class TestIsPostgrestTransientError:
    """Test PostgREST APIError transient detection."""

    def test_api_error_502(self):
        error = FakeAPIError("JSON could not be generated", code=502)
        assert _is_postgrest_transient_error(error) is True

    def test_api_error_503(self):
        error = FakeAPIError("Service temporarily unavailable", code=503)
        assert _is_postgrest_transient_error(error) is True

    def test_api_error_504(self):
        error = FakeAPIError("Gateway timeout", code=504)
        assert _is_postgrest_transient_error(error) is True

    def test_api_error_500(self):
        error = FakeAPIError("Internal server error", code=500)
        assert _is_postgrest_transient_error(error) is True

    def test_api_error_string_code(self):
        """Code can be a string representation of int."""
        error = FakeAPIError("Bad gateway", code="502")
        assert _is_postgrest_transient_error(error) is True

    def test_api_error_non_transient_code(self):
        """Non-transient codes (e.g. 404, 409) should NOT be retried."""
        error = FakeAPIError("Not found", code=404)
        assert _is_postgrest_transient_error(error) is False

    def test_api_error_code_400(self):
        error = FakeAPIError("Bad request", code=400)
        assert _is_postgrest_transient_error(error) is False

    def test_non_api_error(self):
        """Regular exceptions should not match."""
        error = ValueError("some error with code 502")
        assert _is_postgrest_transient_error(error) is False

    def test_api_error_no_code(self):
        """APIError without code attribute falls through to message check."""
        error = FakeAPIError("Something with 502 in message")
        error.code = None
        assert _is_postgrest_transient_error(error) is True

    def test_api_error_no_code_no_match(self):
        error = FakeAPIError("Generic error")
        error.code = None
        assert _is_postgrest_transient_error(error) is False


# ---------------------------------------------------------------------------
# Tests: is_retryable_error
# ---------------------------------------------------------------------------

class TestIsRetryableError:
    """Test unified retryable error detection."""

    # --- Network patterns ---

    def test_connection_reset(self):
        error = ConnectionError("Connection reset by peer")
        assert is_retryable_error(error) is True

    def test_timeout(self):
        error = TimeoutError("Request timed out")
        assert is_retryable_error(error) is True

    def test_dns_failure(self):
        error = OSError("Temporary failure in name resolution")
        assert is_retryable_error(error) is True

    # --- Cloudflare/Supabase patterns ---

    def test_json_could_not_be_generated(self):
        error = Exception("JSON could not be generated")
        assert is_retryable_error(error) is True

    def test_bad_gateway(self):
        error = Exception("502 Bad Gateway")
        assert is_retryable_error(error) is True

    def test_cloudflare_error_page(self):
        error = Exception("Error from Cloudflare: server error")
        assert is_retryable_error(error) is True

    def test_internal_server_error(self):
        error = Exception("500 Internal Server Error")
        assert is_retryable_error(error) is True

    # --- PostgREST APIError (via code check) ---

    def test_postgrest_502_via_code(self):
        error = FakeAPIError("JSON could not be generated", code=502)
        assert is_retryable_error(error) is True

    def test_postgrest_404_not_retryable(self):
        error = FakeAPIError("Resource not found", code=404)
        assert is_retryable_error(error) is False

    # --- Non-retryable errors ---

    def test_value_error_not_retryable(self):
        error = ValueError("Invalid argument")
        assert is_retryable_error(error) is False

    def test_key_error_not_retryable(self):
        error = KeyError("missing_key")
        assert is_retryable_error(error) is False

    # --- Custom patterns ---

    def test_custom_patterns(self):
        error = Exception("rate limit exceeded")
        assert is_retryable_error(error, patterns=['rate limit']) is True

    def test_custom_patterns_no_match(self):
        error = Exception("rate limit exceeded")
        assert is_retryable_error(error, patterns=['auth failed']) is False


# ---------------------------------------------------------------------------
# Tests: _jittered_delay
# ---------------------------------------------------------------------------

class TestJitteredDelay:
    """Test jitter delay calculation."""

    def test_jitter_within_range(self):
        """Jittered delay should be between 50%-100% of base."""
        for _ in range(100):
            delay = _jittered_delay(1.0)
            assert 0.5 <= delay <= 1.0

    def test_jitter_zero_base(self):
        assert _jittered_delay(0.0) == 0.0

    def test_jitter_large_base(self):
        for _ in range(50):
            delay = _jittered_delay(10.0)
            assert 5.0 <= delay <= 10.0

    def test_jitter_not_constant(self):
        """Multiple calls should produce different values (probabilistic)."""
        delays = {_jittered_delay(1.0) for _ in range(20)}
        # With 20 samples from uniform(0.5, 1.0), extremely unlikely all same
        assert len(delays) > 1


# ---------------------------------------------------------------------------
# Tests: retry_on_network_error (sync)
# ---------------------------------------------------------------------------

class TestRetryOnNetworkError:
    """Test sync retry decorator."""

    def test_success_no_retry(self):
        call_count = 0

        @retry_on_network_error(max_retries=3)
        def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = func()
        assert result == "ok"
        assert call_count == 1

    @patch('core.database.retry.time.sleep')
    def test_retry_on_network_error_then_success(self, mock_sleep):
        call_count = 0

        @retry_on_network_error(max_retries=3, delay=0.1)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection reset")
            return "ok"

        result = func()
        assert result == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch('core.database.retry.time.sleep')
    def test_non_retryable_error_raises_immediately(self, mock_sleep):
        call_count = 0

        @retry_on_network_error(max_retries=3)
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Bad input")

        with pytest.raises(ValueError, match="Bad input"):
            func()
        assert call_count == 1
        mock_sleep.assert_not_called()

    @patch('core.database.retry.time.sleep')
    def test_all_retries_exhausted(self, mock_sleep):
        call_count = 0

        @retry_on_network_error(max_retries=2, delay=0.1)
        def func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection refused")

        with pytest.raises(ConnectionError):
            func()
        assert call_count == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# Tests: retry_on_network_error_async
# ---------------------------------------------------------------------------

class TestRetryOnNetworkErrorAsync:
    """Test async retry decorator."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        call_count = 0

        @retry_on_network_error_async(max_retries=3)
        async def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await func()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    @patch('core.database.retry._jittered_delay', return_value=0.0)
    async def test_retry_on_postgrest_502_then_success(self, mock_jitter):
        call_count = 0

        @retry_on_network_error_async(max_retries=3, delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise FakeAPIError("JSON could not be generated", code=502)
            return "recovered"

        result = await func()
        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    @patch('core.database.retry._jittered_delay', return_value=0.0)
    async def test_retry_on_cloudflare_error(self, mock_jitter):
        call_count = 0

        @retry_on_network_error_async(max_retries=3, delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Cloudflare returned 500 Internal Server Error")
            return "ok"

        result = await func()
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_api_error_raises_immediately(self):
        call_count = 0

        @retry_on_network_error_async(max_retries=3)
        async def func():
            nonlocal call_count
            call_count += 1
            raise FakeAPIError("Column not found", code=400)

        with pytest.raises(Exception, match="Column not found"):
            await func()
        assert call_count == 1

    @pytest.mark.asyncio
    @patch('core.database.retry._jittered_delay', return_value=0.0)
    async def test_all_retries_exhausted_async(self, mock_jitter):
        call_count = 0

        @retry_on_network_error_async(max_retries=2, delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            raise FakeAPIError("Service unavailable", code=503)

        with pytest.raises(Exception, match="Service unavailable"):
            await func()
        assert call_count == 3  # 1 initial + 2 retries
