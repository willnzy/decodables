"""
Events Service Tests (v3.27 DDD Architecture)
事件服务单元测试

Coverage target: 60%+
Business logic tested:
- Parameter validation (dates, pagination, group_by, stat_type)
- Service orchestration (Domain Service + Repository)
- Error handling (ValueError for client errors)

创建时间: 2026-01-09
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from application.services.events_service import EventsService
from domains.events import EventsDomainService
from domains.events.entities import AggregatedStats


class TestEventsServiceValidation:
    """Test EventsService validation logic"""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create EventsService with mock repository"""
        return EventsService(mock_repository)

    @pytest.mark.asyncio
    async def test_get_user_events_validates_dates(self, service, mock_repository):
        """get_user_events validates date format"""
        mock_repository.get_user_events = AsyncMock(return_value={
            "events": [],
            "total": 0,
            "offset": 0,
            "limit": 50,
            "has_more": False
        })

        # Valid date formats
        await service.get_user_events(start_date="2026-01-09")
        await service.get_user_events(start_date="2026-01-09T10:00:00Z")

        # Invalid date format should raise ValueError
        with pytest.raises(ValueError, match="Invalid start_date format"):
            await service.get_user_events(start_date="invalid-date")

    @pytest.mark.asyncio
    async def test_get_user_events_validates_pagination(self, service, mock_repository):
        """get_user_events validates pagination parameters"""
        mock_repository.get_user_events = AsyncMock(return_value={
            "events": [],
            "total": 0,
            "offset": 0,
            "limit": 10,
            "has_more": False
        })

        # Valid pagination
        await service.get_user_events(offset=0, limit=50)

        # Invalid offset (negative)
        with pytest.raises(ValueError, match="offset must be"):
            await service.get_user_events(offset=-1, limit=50)

        # Invalid limit (too large)
        with pytest.raises(ValueError, match="limit must be"):
            await service.get_user_events(offset=0, limit=1000)

        # Invalid limit (zero)
        with pytest.raises(ValueError, match="limit must be"):
            await service.get_user_events(offset=0, limit=0)

    @pytest.mark.asyncio
    async def test_get_event_stats_validates_group_by(self, service, mock_repository):
        """get_event_stats validates group_by parameter"""
        mock_repository.get_event_stats = AsyncMock(return_value={"page_view": 100})

        # Valid group_by values
        for group_by in ["event_type", "user_id", "date", "hour"]:
            await service.get_event_stats(group_by=group_by)

        # Invalid group_by
        with pytest.raises(ValueError, match="Invalid group_by"):
            await service.get_event_stats(group_by="invalid_group")

    @pytest.mark.asyncio
    async def test_get_aggregated_stats_validates_stat_type(self, service, mock_repository):
        """get_aggregated_stats validates stat_type parameter"""
        mock_stat = AggregatedStats(
            stat_type="daily_active_users",
            date="2026-01-09",
            value=100
        )
        mock_repository.get_aggregated_stats = AsyncMock(return_value=mock_stat)

        # Valid stat_types
        for stat_type in ["daily_active_users", "hourly_active_users", "daily_events", "hourly_events"]:
            await service.get_aggregated_stats(stat_type=stat_type)

        # Invalid stat_type
        with pytest.raises(ValueError, match="Invalid stat_type"):
            await service.get_aggregated_stats(stat_type="invalid_stat")

    @pytest.mark.asyncio
    async def test_get_aggregated_stats_range_validates_days(self, service, mock_repository):
        """get_aggregated_stats_range validates days parameter"""
        mock_repository.get_aggregated_stats_range = AsyncMock(return_value=[])

        # Valid days
        await service.get_aggregated_stats_range(stat_type="daily_active_users", days=30)

        # Invalid days (too small)
        with pytest.raises(ValueError, match="days must be >= 1"):
            await service.get_aggregated_stats_range(stat_type="daily_active_users", days=0)

        # Invalid days (too large)
        with pytest.raises(ValueError, match="days must be <= 90"):
            await service.get_aggregated_stats_range(stat_type="daily_active_users", days=100)


class TestEventsServiceOrchestration:
    """Test EventsService orchestration logic"""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create EventsService with mock repository"""
        return EventsService(mock_repository)

    @pytest.mark.asyncio
    async def test_get_user_events_calls_repository(self, service, mock_repository):
        """get_user_events calls repository with correct parameters"""
        mock_repository.get_user_events = AsyncMock(return_value={
            "events": [{"id": "evt_1", "event_type": "page_view"}],
            "total": 1,
            "offset": 0,
            "limit": 50,
            "has_more": False
        })

        result = await service.get_user_events(
            user_id="user_123",
            event_type="page_view",
            offset=10,
            limit=20
        )

        # Verify repository was called
        mock_repository.get_user_events.assert_called_once_with(
            user_id="user_123",
            event_type="page_view",
            start_date=None,
            end_date=None,
            offset=10,
            limit=20
        )

        # Verify result structure
        assert "events" in result
        assert "total" in result
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_get_event_stats_calls_repository(self, service, mock_repository):
        """get_event_stats calls repository with correct parameters"""
        mock_repository.get_event_stats = AsyncMock(return_value={
            "page_view": 100,
            "button_click": 50
        })

        result = await service.get_event_stats(
            start_date="2026-01-01",
            end_date="2026-01-09",
            group_by="event_type"
        )

        # Verify repository was called
        mock_repository.get_event_stats.assert_called_once_with(
            start_date="2026-01-01",
            end_date="2026-01-09",
            group_by="event_type"
        )

        # Verify result
        assert result["page_view"] == 100
        assert result["button_click"] == 50

    @pytest.mark.asyncio
    async def test_get_aggregated_stats_returns_none_when_not_found(self, service, mock_repository):
        """get_aggregated_stats returns None when data not found"""
        mock_repository.get_aggregated_stats = AsyncMock(return_value=None)

        result = await service.get_aggregated_stats(stat_type="daily_active_users")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_aggregated_stats_returns_entity(self, service, mock_repository):
        """get_aggregated_stats returns AggregatedStats entity"""
        mock_stat = AggregatedStats(
            stat_type="daily_active_users",
            date="2026-01-09",
            value=150
        )
        mock_repository.get_aggregated_stats = AsyncMock(return_value=mock_stat)

        result = await service.get_aggregated_stats(stat_type="daily_active_users")

        assert result == mock_stat
        assert result.value == 150

    @pytest.mark.asyncio
    async def test_get_aggregated_stats_range_calls_repository(self, service, mock_repository):
        """get_aggregated_stats_range calls repository with correct parameters"""
        mock_stats = [
            AggregatedStats(stat_type="daily_active_users", date="2026-01-09", value=150),
            AggregatedStats(stat_type="daily_active_users", date="2026-01-08", value=140),
        ]
        mock_repository.get_aggregated_stats_range = AsyncMock(return_value=mock_stats)

        result = await service.get_aggregated_stats_range(
            stat_type="daily_active_users",
            days=7
        )

        # Verify repository was called
        mock_repository.get_aggregated_stats_range.assert_called_once_with(
            stat_type="daily_active_users",
            days=7
        )

        # Verify result
        assert len(result) == 2
        assert result[0].value == 150


class TestEventsServiceErrorHandling:
    """Test EventsService error handling"""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository"""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create EventsService with mock repository"""
        return EventsService(mock_repository)

    @pytest.mark.asyncio
    async def test_get_user_events_handles_repository_error(self, service, mock_repository):
        """get_user_events propagates repository errors"""
        mock_repository.get_user_events = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(Exception, match="Database error"):
            await service.get_user_events()

    @pytest.mark.asyncio
    async def test_get_event_stats_handles_repository_error(self, service, mock_repository):
        """get_event_stats propagates repository errors"""
        mock_repository.get_event_stats = AsyncMock(side_effect=Exception("Network timeout"))

        with pytest.raises(Exception, match="Network timeout"):
            await service.get_event_stats()


class TestEventsDomainService:
    """Test EventsDomainService validation methods"""

    def test_validate_group_by_valid(self):
        """validate_group_by accepts valid values"""
        domain_service = EventsDomainService()

        # Should not raise
        for group_by in ["event_type", "user_id", "date", "hour"]:
            domain_service.validate_group_by(group_by)

    def test_validate_group_by_invalid(self):
        """validate_group_by rejects invalid values"""
        domain_service = EventsDomainService()

        with pytest.raises(ValueError, match="Invalid group_by"):
            domain_service.validate_group_by("invalid_value")

    def test_validate_stat_type_valid(self):
        """validate_stat_type accepts valid values"""
        domain_service = EventsDomainService()

        # Should not raise
        for stat_type in ["daily_active_users", "hourly_active_users", "daily_events", "hourly_events"]:
            domain_service.validate_stat_type(stat_type)

    def test_validate_stat_type_invalid(self):
        """validate_stat_type rejects invalid values"""
        domain_service = EventsDomainService()

        with pytest.raises(ValueError, match="Invalid stat_type"):
            domain_service.validate_stat_type("unknown_stat")

    def test_validate_date_format_valid(self):
        """validate_date_format accepts valid ISO dates"""
        domain_service = EventsDomainService()

        # Should not raise
        domain_service.validate_date_format("2026-01-09", "start_date")
        domain_service.validate_date_format("2026-01-09T10:00:00Z", "end_date")
        domain_service.validate_date_format(None, "optional_date")  # None is valid

    def test_validate_date_format_invalid(self):
        """validate_date_format rejects invalid dates"""
        domain_service = EventsDomainService()

        with pytest.raises(ValueError, match="Invalid start_date format"):
            domain_service.validate_date_format("invalid-date", "start_date")

        with pytest.raises(ValueError, match="Invalid end_date format"):
            domain_service.validate_date_format("2026/01/09", "end_date")

    def test_validate_pagination_valid(self):
        """validate_pagination accepts valid parameters"""
        domain_service = EventsDomainService()

        # Should not raise
        domain_service.validate_pagination(offset=0, limit=50, max_limit=100)
        domain_service.validate_pagination(offset=100, limit=100, max_limit=100)

    def test_validate_pagination_invalid_offset(self):
        """validate_pagination rejects negative offset"""
        domain_service = EventsDomainService()

        with pytest.raises(ValueError, match="offset must be"):
            domain_service.validate_pagination(offset=-1, limit=50, max_limit=100)

    def test_validate_pagination_invalid_limit(self):
        """validate_pagination rejects invalid limit"""
        domain_service = EventsDomainService()

        # Limit too small
        with pytest.raises(ValueError, match="limit must be"):
            domain_service.validate_pagination(offset=0, limit=0, max_limit=100)

        # Limit too large
        with pytest.raises(ValueError, match="limit must be"):
            domain_service.validate_pagination(offset=0, limit=200, max_limit=100)
