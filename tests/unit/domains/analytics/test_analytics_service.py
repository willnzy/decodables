"""
Unit tests for AnalyticsService.

@module tests.unit.domains.analytics.test_analytics_service
@version 1.0.0
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from domains.analytics.service import AnalyticsService
from domains.analytics.repository import IAnalyticsRepository
from domains.analytics.entities import AnalyticsEvent


@pytest.fixture
def mock_repository():
    """Create a mock analytics repository."""
    repo = Mock(spec=IAnalyticsRepository)
    repo.save = AsyncMock()
    repo.save_batch = AsyncMock(return_value=5)
    repo.batch_insert_all = AsyncMock(return_value=(3, 5, 2))
    return repo


@pytest.fixture
def analytics_service(mock_repository):
    """Create analytics service with mock repository."""
    return AnalyticsService(mock_repository)


class TestTrackEvent:
    """Tests for track_event method."""
    
    @pytest.mark.asyncio
    async def test_track_event_creates_entity(self, analytics_service, mock_repository):
        """Should create AnalyticsEvent entity and save to repository."""
        event = await analytics_service.track_event(
            event_name="Test Event",
            event_type="test_event",
            user_id="user_123",
            properties={"key": "value"}
        )
        
        # Verify event was created
        assert isinstance(event, AnalyticsEvent)
        assert event.event_name == "test event"  # Normalized to lowercase
        assert event.event_type == "test_event"
        assert event.user_id == "user_123"
        assert event.properties["key"] == "value"
        
        # Verify repository was called
        mock_repository.save.assert_called_once()
        saved_event = mock_repository.save.call_args[0][0]
        assert saved_event.event_name == "test event"
    
    @pytest.mark.asyncio
    async def test_track_event_handles_repository_errors(
        self, analytics_service, mock_repository, caplog
    ):
        """Should log errors but not raise when repository fails."""
        mock_repository.save.side_effect = Exception("Database error")
        
        # Should not raise exception
        event = await analytics_service.track_event(
            event_name="Test Event",
            event_type="test_event",
            user_id="user_123"
        )
        
        # Event should still be created
        assert isinstance(event, AnalyticsEvent)
        
        # Error should be logged
        assert "Failed to track event" in caplog.text


class TestTrackAIGeneration:
    """Tests for track_ai_generation convenience method."""
    
    @pytest.mark.asyncio
    async def test_track_success_event(self, analytics_service, mock_repository):
        """Should track successful AI generation."""
        event = await analytics_service.track_ai_generation(
            user_id="user_123",
            success=True,
            model="flux",
            cost_credits=5,
            duration_ms=3200
        )
        
        assert event.event_type == "ai_generate_success"
        assert event.properties["model"] == "flux"
        assert event.properties["cost_credits"] == 5
        assert event.properties["duration_ms"] == 3200
        assert event.properties["success"] is True
    
    @pytest.mark.asyncio
    async def test_track_failure_event(self, analytics_service, mock_repository):
        """Should track failed AI generation."""
        event = await analytics_service.track_ai_generation(
            user_id="user_123",
            success=False,
            model="flux",
            cost_credits=5,
            error_code="TIMEOUT"
        )
        
        assert event.event_type == "ai_generate_failure"
        assert event.properties["error_code"] == "TIMEOUT"
        assert event.properties["success"] is False


class TestTrackPayment:
    """Tests for track_payment convenience method."""
    
    @pytest.mark.asyncio
    async def test_track_payment_event(self, analytics_service, mock_repository):
        """Should track payment event with all properties."""
        event = await analytics_service.track_payment(
            user_id="user_123",
            event_name="checkout_completed",
            amount_cents=2990,
            plan="t3",
            stripe_payment_id="pi_xxx"
        )
        
        assert event.event_type == "checkout_completed"
        assert event.properties["amount_cents"] == 2990
        assert event.properties["plan"] == "t3"
        assert event.properties["stripe_payment_id"] == "pi_xxx"


class TestProcessAndSaveEvents:
    """Tests for frontend batch event processing."""
    
    @pytest.mark.asyncio
    async def test_process_batch_events(self, analytics_service, mock_repository):
        """Should process and save batch events to all tables."""
        events = [
            {
                "event_type": "page_view",
                "properties": {"page": "/dashboard"},
                "env": {"browser": "Chrome"},
            },
            {
                "event_type": "button_click",
                "properties": {"button": "create_project"},
                "env": {"browser": "Chrome"},
            }
        ]
        
        location_info = {
            "ip": "1.2.3.4",
            "country_code": "US",
            "city": "San Francisco",
            "region": "CA"
        }
        
        requested, inserted = await analytics_service.process_and_save_events(
            events=events,
            user_id="user_123",
            location_info=location_info,
            user_agent="Mozilla/5.0",
            accept_language="en-US"
        )
        
        # Verify counts
        assert requested == 2
        assert inserted == 5  # From mock return value
        
        # Verify repository was called
        mock_repository.batch_insert_all.assert_called_once()


class TestAnalyticsEvent:
    """Tests for AnalyticsEvent entity."""
    
    def test_entity_validates_event_name(self):
        """Should validate event_name is required."""
        with pytest.raises(ValueError, match="event_name is required"):
            AnalyticsEvent(event_name="", event_type="test")
    
    def test_entity_normalizes_names(self):
        """Should normalize event names to lowercase."""
        event = AnalyticsEvent(
            event_name="Test Event",
            event_type="TEST_TYPE"
        )
        
        assert event.event_name == "test event"
        assert event.event_type == "test_type"
    
    def test_entity_auto_generates_event_id(self):
        """Should auto-generate event_id if not provided."""
        event = AnalyticsEvent(
            event_name="test",
            event_type="test"
        )
        
        assert event.event_id is not None
        assert event.event_id == str(event.id)
    
    def test_entity_to_dict(self):
        """Should serialize to dictionary correctly."""
        event = AnalyticsEvent(
            event_name="test",
            event_type="test",
            user_id="user_123",
            properties={"key": "value"}
        )
        
        data = event.to_dict()
        
        assert data["event_name"] == "test"
        assert data["event_type"] == "test"
        assert data["user_id"] == "user_123"
        assert data["properties"]["key"] == "value"
        assert "id" in data
        assert "created_at" in data
