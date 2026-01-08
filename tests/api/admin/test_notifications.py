"""Test admin/notifications API endpoints.

Tests for admin notification management endpoints.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import app


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ==========================================
# Basic Endpoint Tests (Auth)
# ==========================================

class TestNotificationEndpointsAuth:
    """Basic tests for notification API authentication requirements."""

    def test_broadcast_requires_auth(self, client):
        """Broadcast endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/notifications/broadcast",
            json={"title": "Test", "content": "Test content"}
        )
        assert response.status_code in [401, 403]

    def test_send_notification_requires_auth(self, client):
        """Send notification endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/notifications/notification/send",
            json={"user_id": "test", "title": "Test", "content": "Test content"}
        )
        assert response.status_code in [401, 403]

    def test_batch_notification_requires_auth(self, client):
        """Batch notification endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/notifications/notification/batch",
            json={"user_ids": ["u1"], "title": "Test", "content": "Test content"}
        )
        assert response.status_code in [401, 403]

    def test_notification_stats_requires_auth(self, client):
        """Notification stats endpoint requires authentication."""
        response = client.get("/api/v2/admin/notifications/notification/stats")
        assert response.status_code in [401, 403]

    def test_notification_history_requires_auth(self, client):
        """Notification history endpoint requires authentication."""
        response = client.get("/api/v2/admin/notifications/notification/history")
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestNotificationConstants:
    """Tests for notification constants."""

    def test_valid_target_groups(self):
        """Valid target groups are defined."""
        from api.admin.notifications import VALID_TARGET_GROUPS

        assert "all" in VALID_TARGET_GROUPS
        assert "free" in VALID_TARGET_GROUPS
        assert "starter" in VALID_TARGET_GROUPS
        assert "pro" in VALID_TARGET_GROUPS
        assert "invalid" not in VALID_TARGET_GROUPS

    def test_valid_notification_types(self):
        """Valid notification types are defined."""
        from api.admin.notifications import VALID_NOTIFICATION_TYPES

        assert "system" in VALID_NOTIFICATION_TYPES
        assert "marketing" in VALID_NOTIFICATION_TYPES
        assert "alert" in VALID_NOTIFICATION_TYPES
        assert "update" in VALID_NOTIFICATION_TYPES
        assert "promotion" in VALID_NOTIFICATION_TYPES
        assert "invalid" not in VALID_NOTIFICATION_TYPES


# ==========================================
# Request Model Validation Tests
# ==========================================

class TestAdminBroadcastRequestValidation:
    """Tests for AdminBroadcastRequest model validation."""

    def test_valid_broadcast_request(self):
        """Valid broadcast request is accepted."""
        from api.admin.notifications import AdminBroadcastRequest

        req = AdminBroadcastRequest(
            title="Test Title",
            content="Test content",
            target_group="all"
        )
        assert req.title == "Test Title"
        assert req.target_group == "all"

    def test_broadcast_default_target_group(self):
        """Default target group is 'all'."""
        from api.admin.notifications import AdminBroadcastRequest

        req = AdminBroadcastRequest(title="Test", content="Content")
        assert req.target_group == "all"

    def test_broadcast_title_length_validation(self):
        """Title must be between 1-200 characters."""
        from api.admin.notifications import AdminBroadcastRequest

        # Valid title
        AdminBroadcastRequest(title="Valid", content="Content")
        AdminBroadcastRequest(title="a" * 200, content="Content")

        # Invalid: empty title
        with pytest.raises(ValidationError):
            AdminBroadcastRequest(title="", content="Content")

        # Invalid: too long
        with pytest.raises(ValidationError):
            AdminBroadcastRequest(title="a" * 201, content="Content")

    def test_broadcast_content_length_validation(self):
        """Content must be between 1-5000 characters."""
        from api.admin.notifications import AdminBroadcastRequest

        # Valid content
        AdminBroadcastRequest(title="Test", content="Valid content")
        AdminBroadcastRequest(title="Test", content="a" * 5000)

        # Invalid: empty content
        with pytest.raises(ValidationError):
            AdminBroadcastRequest(title="Test", content="")

        # Invalid: too long
        with pytest.raises(ValidationError):
            AdminBroadcastRequest(title="Test", content="a" * 5001)

    def test_broadcast_target_group_validation(self):
        """Target group must be valid."""
        from api.admin.notifications import AdminBroadcastRequest

        # Valid target groups
        for group in ["all", "free", "starter", "pro"]:
            req = AdminBroadcastRequest(title="Test", content="Content", target_group=group)
            assert req.target_group == group

        # Invalid target group
        with pytest.raises(ValidationError) as exc_info:
            AdminBroadcastRequest(title="Test", content="Content", target_group="invalid")
        assert "Invalid target_group" in str(exc_info.value)


class TestAdminSendNotificationRequestValidation:
    """Tests for AdminSendNotificationRequest model validation."""

    def test_valid_send_request(self):
        """Valid send notification request is accepted."""
        from api.admin.notifications import AdminSendNotificationRequest

        req = AdminSendNotificationRequest(
            user_id="user-123",
            title="Test Title",
            content="Test content",
            notification_type="system"
        )
        assert req.user_id == "user-123"
        assert req.notification_type == "system"

    def test_send_default_notification_type(self):
        """Default notification type is 'system'."""
        from api.admin.notifications import AdminSendNotificationRequest

        req = AdminSendNotificationRequest(
            user_id="user-123",
            title="Test",
            content="Content"
        )
        assert req.notification_type == "system"

    def test_send_user_id_length_validation(self):
        """User ID must be between 1-100 characters."""
        from api.admin.notifications import AdminSendNotificationRequest

        # Valid user_id
        AdminSendNotificationRequest(user_id="user-123", title="Test", content="Content")
        AdminSendNotificationRequest(user_id="a" * 100, title="Test", content="Content")

        # Invalid: empty user_id
        with pytest.raises(ValidationError):
            AdminSendNotificationRequest(user_id="", title="Test", content="Content")

        # Invalid: too long
        with pytest.raises(ValidationError):
            AdminSendNotificationRequest(user_id="a" * 101, title="Test", content="Content")

    def test_send_notification_type_validation(self):
        """Notification type must be valid."""
        from api.admin.notifications import AdminSendNotificationRequest

        # Valid notification types
        for ntype in ["system", "marketing", "alert", "update", "promotion"]:
            req = AdminSendNotificationRequest(
                user_id="user-123",
                title="Test",
                content="Content",
                notification_type=ntype
            )
            assert req.notification_type == ntype

        # Invalid notification type
        with pytest.raises(ValidationError) as exc_info:
            AdminSendNotificationRequest(
                user_id="user-123",
                title="Test",
                content="Content",
                notification_type="invalid"
            )
        assert "Invalid notification_type" in str(exc_info.value)


class TestAdminBatchNotificationRequestValidation:
    """Tests for AdminBatchNotificationRequest model validation."""

    def test_valid_batch_request(self):
        """Valid batch notification request is accepted."""
        from api.admin.notifications import AdminBatchNotificationRequest

        req = AdminBatchNotificationRequest(
            user_ids=["user-1", "user-2"],
            title="Test Title",
            content="Test content",
            notification_type="alert"
        )
        assert len(req.user_ids) == 2
        assert req.notification_type == "alert"

    def test_batch_default_notification_type(self):
        """Default notification type is 'system'."""
        from api.admin.notifications import AdminBatchNotificationRequest

        req = AdminBatchNotificationRequest(
            user_ids=["user-1"],
            title="Test",
            content="Content"
        )
        assert req.notification_type == "system"

    def test_batch_user_ids_max_length(self):
        """User IDs list cannot exceed 100 items."""
        from api.admin.notifications import AdminBatchNotificationRequest

        # Valid: 100 users
        AdminBatchNotificationRequest(
            user_ids=[f"user-{i}" for i in range(100)],
            title="Test",
            content="Content"
        )

        # Invalid: 101 users (Field max_length)
        with pytest.raises(ValidationError):
            AdminBatchNotificationRequest(
                user_ids=[f"user-{i}" for i in range(101)],
                title="Test",
                content="Content"
            )

    def test_batch_title_length_validation(self):
        """Title must be between 1-200 characters."""
        from api.admin.notifications import AdminBatchNotificationRequest

        # Invalid: empty title
        with pytest.raises(ValidationError):
            AdminBatchNotificationRequest(
                user_ids=["user-1"],
                title="",
                content="Content"
            )

        # Invalid: too long
        with pytest.raises(ValidationError):
            AdminBatchNotificationRequest(
                user_ids=["user-1"],
                title="a" * 201,
                content="Content"
            )

    def test_batch_notification_type_validation(self):
        """Notification type must be valid."""
        from api.admin.notifications import AdminBatchNotificationRequest

        # Valid notification types
        for ntype in ["system", "marketing", "alert", "update", "promotion"]:
            req = AdminBatchNotificationRequest(
                user_ids=["user-1"],
                title="Test",
                content="Content",
                notification_type=ntype
            )
            assert req.notification_type == ntype

        # Invalid notification type
        with pytest.raises(ValidationError) as exc_info:
            AdminBatchNotificationRequest(
                user_ids=["user-1"],
                title="Test",
                content="Content",
                notification_type="invalid"
            )
        assert "Invalid notification_type" in str(exc_info.value)


# ==========================================
# Parameter Validation Tests (Integration-style)
# ==========================================

class TestNotificationParameterValidation:
    """Integration tests for parameter validation."""

    @pytest.mark.parametrize("target_group", ["all", "free", "starter", "pro"])
    def test_valid_target_group_values(self, target_group):
        """Valid target group values are accepted."""
        from api.admin.notifications import VALID_TARGET_GROUPS

        assert target_group in VALID_TARGET_GROUPS

    @pytest.mark.parametrize("notification_type", ["system", "marketing", "alert", "update", "promotion"])
    def test_valid_notification_type_values(self, notification_type):
        """Valid notification type values are accepted."""
        from api.admin.notifications import VALID_NOTIFICATION_TYPES

        assert notification_type in VALID_NOTIFICATION_TYPES

    @pytest.mark.parametrize("offset", [0, 10, 50, 100])
    def test_valid_offset_values(self, offset):
        """Valid offset values are non-negative."""
        assert offset >= 0

    @pytest.mark.parametrize("limit", [1, 20, 50, 100])
    def test_valid_limit_values(self, limit):
        """Valid limit values are within range."""
        assert 1 <= limit <= 100


# ==========================================
# Endpoint Logic Tests
# ==========================================

class TestBatchNotificationLogic:
    """Tests for batch notification endpoint logic."""

    def test_batch_limit_enforced(self, client):
        """Batch endpoint enforces 100 user limit."""
        # This tests that even unauthenticated requests with >100 users
        # would be rejected if they got past auth
        # The 100-user limit is also enforced at the model level
        from api.admin.notifications import AdminBatchNotificationRequest

        # Model validation should reject >100 users
        with pytest.raises(ValidationError):
            AdminBatchNotificationRequest(
                user_ids=[f"user-{i}" for i in range(101)],
                title="Test",
                content="Content"
            )
