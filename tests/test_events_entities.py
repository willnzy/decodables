"""
Events Entities Tests (v3.27 DDD Architecture)
事件实体层单元测试

Coverage target: 90%+
Entity logic tested:
- Entity initialization
- to_dict() serialization
- from_dict() deserialization
- Type validation
- Default values

创建时间: 2026-01-09
"""

import pytest
from datetime import datetime, timezone

from domains.events.entities import UserEvent, EventStats, AggregatedStats


class TestUserEvent:
    """Test UserEvent entity"""

    def test_user_event_initialization(self):
        """UserEvent initializes with required fields"""
        event = UserEvent(
            user_id="user_123",
            event_type="page_view"
        )

        assert event.user_id == "user_123"
        assert event.event_type == "page_view"
        assert event.id is None
        assert event.event_data is None

    def test_user_event_with_all_fields(self):
        """UserEvent initializes with all fields"""
        created_at = datetime.now(timezone.utc)

        event = UserEvent(
            id="evt_123",
            user_id="user_123",
            event_type="button_click",
            event_data={"button_id": "submit"},
            session_id="sess_456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_at=created_at
        )

        assert event.id == "evt_123"
        assert event.user_id == "user_123"
        assert event.event_type == "button_click"
        assert event.event_data == {"button_id": "submit"}
        assert event.session_id == "sess_456"
        assert event.ip_address == "192.168.1.1"
        assert event.user_agent == "Mozilla/5.0"
        assert event.created_at == created_at

    def test_user_event_to_dict(self):
        """UserEvent serializes to dict correctly"""
        created_at = datetime(2026, 1, 9, 10, 0, 0, tzinfo=timezone.utc)

        event = UserEvent(
            id="evt_123",
            user_id="user_123",
            event_type="page_view",
            event_data={"page": "/home"},
            created_at=created_at
        )

        result = event.to_dict()

        assert result["id"] == "evt_123"
        assert result["user_id"] == "user_123"
        assert result["event_type"] == "page_view"
        assert result["event_data"] == {"page": "/home"}
        assert result["created_at"] == "2026-01-09T10:00:00+00:00"

    def test_user_event_to_dict_with_none_values(self):
        """UserEvent to_dict handles None values"""
        event = UserEvent(
            user_id="user_123",
            event_type="page_view"
        )

        result = event.to_dict()

        assert result["id"] is None
        assert result["event_data"] is None
        assert result["session_id"] is None

    def test_user_event_from_dict(self):
        """UserEvent deserializes from dict correctly"""
        data = {
            "id": "evt_123",
            "user_id": "user_123",
            "event_type": "page_view",
            "event_data": {"page": "/home"},
            "session_id": "sess_456",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "created_at": "2026-01-09T10:00:00Z"
        }

        event = UserEvent.from_dict(data)

        assert event.id == "evt_123"
        assert event.user_id == "user_123"
        assert event.event_type == "page_view"
        assert event.event_data == {"page": "/home"}
        assert event.session_id == "sess_456"
        assert isinstance(event.created_at, datetime)

    def test_user_event_from_dict_with_missing_fields(self):
        """UserEvent from_dict handles missing optional fields"""
        data = {
            "user_id": "user_123",
            "event_type": "page_view"
        }

        event = UserEvent.from_dict(data)

        assert event.user_id == "user_123"
        assert event.event_type == "page_view"
        assert event.id is None
        assert event.event_data is None

    def test_user_event_from_dict_with_datetime_object(self):
        """UserEvent from_dict handles datetime objects"""
        created_at = datetime.now(timezone.utc)

        data = {
            "user_id": "user_123",
            "event_type": "page_view",
            "created_at": created_at
        }

        event = UserEvent.from_dict(data)

        assert event.created_at == created_at


class TestEventStats:
    """Test EventStats entity"""

    def test_event_stats_initialization(self):
        """EventStats initializes correctly"""
        stats = EventStats(
            group_key="page_view",
            count=100
        )

        assert stats.group_key == "page_view"
        assert stats.count == 100
        assert stats.metadata == {}

    def test_event_stats_with_metadata(self):
        """EventStats initializes with metadata"""
        stats = EventStats(
            group_key="button_click",
            count=50,
            metadata={"source": "analytics"}
        )

        assert stats.group_key == "button_click"
        assert stats.count == 50
        assert stats.metadata == {"source": "analytics"}

    def test_event_stats_to_dict(self):
        """EventStats serializes to dict correctly"""
        stats = EventStats(
            group_key="page_view",
            count=100,
            metadata={"source": "analytics"}
        )

        result = stats.to_dict()

        assert result["key"] == "page_view"
        assert result["count"] == 100
        assert result["metadata"] == {"source": "analytics"}

    def test_event_stats_default_metadata(self):
        """EventStats has default empty dict for metadata"""
        stats = EventStats(
            group_key="page_view",
            count=100
        )

        assert isinstance(stats.metadata, dict)
        assert len(stats.metadata) == 0


class TestAggregatedStats:
    """Test AggregatedStats entity"""

    def test_aggregated_stats_initialization(self):
        """AggregatedStats initializes correctly"""
        stats = AggregatedStats(
            stat_type="daily_active_users",
            date="2026-01-09",
            value=150
        )

        assert stats.stat_type == "daily_active_users"
        assert stats.date == "2026-01-09"
        assert stats.value == 150
        assert stats.metadata is None
        assert stats.created_at is None

    def test_aggregated_stats_with_all_fields(self):
        """AggregatedStats initializes with all fields"""
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        stats = AggregatedStats(
            stat_type="daily_active_users",
            date="2026-01-09",
            value=150,
            metadata={"source": "cron"},
            created_at=created_at,
            updated_at=updated_at
        )

        assert stats.stat_type == "daily_active_users"
        assert stats.date == "2026-01-09"
        assert stats.value == 150
        assert stats.metadata == {"source": "cron"}
        assert stats.created_at == created_at
        assert stats.updated_at == updated_at

    def test_aggregated_stats_to_dict(self):
        """AggregatedStats serializes to dict correctly"""
        created_at = datetime(2026, 1, 9, 10, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2026, 1, 9, 11, 0, 0, tzinfo=timezone.utc)

        stats = AggregatedStats(
            stat_type="daily_active_users",
            date="2026-01-09",
            value=150,
            metadata={"source": "cron"},
            created_at=created_at,
            updated_at=updated_at
        )

        result = stats.to_dict()

        assert result["stat_type"] == "daily_active_users"
        assert result["date"] == "2026-01-09"
        assert result["value"] == 150
        assert result["metadata"] == {"source": "cron"}
        assert result["created_at"] == "2026-01-09T10:00:00+00:00"
        assert result["updated_at"] == "2026-01-09T11:00:00+00:00"

    def test_aggregated_stats_to_dict_with_none_timestamps(self):
        """AggregatedStats to_dict handles None timestamps"""
        stats = AggregatedStats(
            stat_type="daily_active_users",
            date="2026-01-09",
            value=150
        )

        result = stats.to_dict()

        assert result["created_at"] is None
        assert result["updated_at"] is None

    def test_aggregated_stats_from_dict(self):
        """AggregatedStats deserializes from dict correctly"""
        data = {
            "stat_type": "daily_active_users",
            "date": "2026-01-09",
            "value": 150,
            "metadata": {"source": "cron"},
            "created_at": "2026-01-09T10:00:00Z",
            "updated_at": "2026-01-09T11:00:00Z"
        }

        stats = AggregatedStats.from_dict(data)

        assert stats.stat_type == "daily_active_users"
        assert stats.date == "2026-01-09"
        assert stats.value == 150
        assert stats.metadata == {"source": "cron"}
        assert isinstance(stats.created_at, datetime)
        assert isinstance(stats.updated_at, datetime)

    def test_aggregated_stats_from_dict_minimal(self):
        """AggregatedStats from_dict handles minimal fields"""
        data = {
            "stat_type": "daily_active_users",
            "date": "2026-01-09",
            "value": 150
        }

        stats = AggregatedStats.from_dict(data)

        assert stats.stat_type == "daily_active_users"
        assert stats.date == "2026-01-09"
        assert stats.value == 150
        assert stats.metadata is None
        assert stats.created_at is None

    def test_aggregated_stats_from_dict_with_datetime_objects(self):
        """AggregatedStats from_dict handles datetime objects"""
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        data = {
            "stat_type": "daily_active_users",
            "date": "2026-01-09",
            "value": 150,
            "created_at": created_at,
            "updated_at": updated_at
        }

        stats = AggregatedStats.from_dict(data)

        assert stats.created_at == created_at
        assert stats.updated_at == updated_at

    def test_aggregated_stats_value_types(self):
        """AggregatedStats handles integer value"""
        stats = AggregatedStats(
            stat_type="daily_events",
            date="2026-01-09",
            value=1000
        )

        assert stats.value == 1000
        assert isinstance(stats.value, int)
