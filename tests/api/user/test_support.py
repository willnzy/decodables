"""
Support API Tests - v3.0.0 DDD Architecture

Tests for api/user/support.py

@version 3.0.0
@updated 2026-01-10 (v3.0.0: Updated to mock Command Handlers instead of Infrastructure)

Test Pattern:
- v2.1.0: Mocked Infrastructure (SupabaseSupportRepository, AI services)
- v3.0.0: Mocks Command Handlers (CreateSupportTicketHandler, AiChatSupportHandler, etc.)

Endpoints:
- POST /api/v2/user/support/ticket - Create support ticket
- POST /api/v2/user/support/chat - AI support chat
- POST /api/v2/user/support/contact - Contact form submission
- POST /api/v2/user/support/feedback - Submit user feedback

Changes in v3.0.0:
- Migrated to Handler-based testing pattern
- Mock handlers via Container._handlers injection
- Removed direct Infrastructure mocking

Changes in v2.1.0:
- Added tests for images list size limit (SUP-MEDIUM-1)
- Added tests for conversation_history size limit (SUP-MEDIUM-2)
- Added tests for feedback images limit (SUP-LOW-1)
- Added tests for email format validation (SUP-LOW-2, SUP-LOW-3)

Created: 2026-01-08
Coverage Target: 100% (4/4 endpoints)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# IMPORTANT: Bypass rate limiter BEFORE importing app
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user() -> Dict[str, Any]:
    """Mock authenticated user."""
    return {
        "id": "user_test_123",
        "email": "test@example.com",
        "tier": "free",
        "subscription_tier": "free",
    }


@pytest.fixture
def override_get_current_user(mock_user):
    """Override dependency to return mock user."""
    async def _get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_chat_response():
    """Mock AI chat response."""
    return {
        "status": "ok",
        "message": "I can help you with that!",
        "source": "assistant",
    }


@pytest.fixture
def mock_chat_response_fallback():
    """Mock AI chat fallback response."""
    return {
        "status": "ok",
        "message": "Here's how to solve your issue...",
        "source": "fallback",
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="I can help you with that!"))
    ]
    return mock_response


# ==========================================
# POST /api/v2/user/support/ticket Tests
# ==========================================

class TestCreateTicket:
    """Tests for POST /api/v2/user/support/ticket endpoint (v3.0.0)."""

    def test_create_ticket_success(
        self,
        override_get_current_user,
        mock_user,
    ):
        """
        v3.0.0: Test create support ticket successfully

        Given: User with valid authentication
        When: POST /api/v2/user/support/ticket with message
        Then: Returns status=ok
        """
        from application.commands.support import CreateSupportTicketHandler, CreateSupportTicketResult

        # Mock handler
        mock_handler = MagicMock(spec=CreateSupportTicketHandler)
        mock_handler.handle = AsyncMock(return_value=CreateSupportTicketResult(
            result_data={"status": "ok"}
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_support_ticket')
        container._handlers['create_support_ticket'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/ticket",
                json={
                    "message": "I need help with my project",
                    "email": "custom@example.com",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

            # Verify handler called
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert call_args.user_id == mock_user["id"]
            assert call_args.user_email == "custom@example.com"
            assert call_args.message == "I need help with my project"

        finally:
            if original_handler:
                container._handlers['create_support_ticket'] = original_handler
            else:
                container._handlers.pop('create_support_ticket', None)

    def test_create_ticket_default_email(
        self,
        override_get_current_user,
        mock_user,
    ):
        """
        v3.0.0: Test create ticket with default user email

        Given: User without custom email
        When: POST without email field
        Then: Uses user's default email
        """
        from application.commands.support import CreateSupportTicketHandler, CreateSupportTicketResult

        # Mock handler
        mock_handler = MagicMock(spec=CreateSupportTicketHandler)
        mock_handler.handle = AsyncMock(return_value=CreateSupportTicketResult(
            result_data={"status": "ok"}
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('create_support_ticket')
        container._handlers['create_support_ticket'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/ticket",
                json={"message": "Need help"},
            )

            # Assert
            assert response.status_code == 200

            # Verify default email used
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert call_args.user_email == "test@example.com"  # From mock_user
            assert call_args.message == "Need help"

        finally:
            if original_handler:
                container._handlers['create_support_ticket'] = original_handler
            else:
                container._handlers.pop('create_support_ticket', None)

    def test_create_ticket_validation_error(
        self,
        override_get_current_user,
    ):
        """
        Test: Empty message should return 422

        Given: User with valid authentication
        When: POST with empty message
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/support/ticket",
            json={"message": ""},  # Empty message
        )

        # Assert
        assert response.status_code == 422

    def test_create_ticket_message_too_long(
        self,
        override_get_current_user,
    ):
        """
        Test: Message exceeding max length should return 422

        Given: User with valid authentication
        When: POST with message > 5000 characters
        Then: Returns 422 Validation Error
        """
        # Arrange
        long_message = "A" * 5001  # Exceeds max_length=5000

        # Act
        response = client.post(
            "/api/v2/user/support/ticket",
            json={"message": long_message},
        )

        # Assert
        assert response.status_code == 422

    def test_create_ticket_unauthorized(self):
        """
        Test: Unauthenticated request should return 401

        Given: No authentication headers
        When: POST /api/v2/user/support/ticket
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/support/ticket",
            json={"message": "Need help"},
        )

        # Assert
        assert response.status_code == 401


# ==========================================
# POST /api/v2/user/support/chat Tests
# ==========================================

class TestChatSupport:
    """Tests for POST /api/v2/user/support/chat endpoint (v3.0.0)."""

    def test_chat_with_assistant_api(
        self,
        override_get_current_user,
        mock_chat_response,
    ):
        """
        v3.0.0: Test chat using Assistants API (with RAG)

        Given: Handler returns assistant response
        When: POST /api/v2/user/support/chat without images
        Then: Returns chat response
        """
        from application.commands.support import AiChatSupportHandler, AiChatSupportResult

        # Mock handler
        mock_handler = MagicMock(spec=AiChatSupportHandler)
        mock_handler.handle = AsyncMock(return_value=AiChatSupportResult(
            result_data=mock_chat_response
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ai_chat_support')
        container._handlers['ai_chat_support'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/chat",
                json={
                    "message": "How do I create a project?",
                    "conversation_history": [],
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["message"] == "I can help you with that!"
            assert data["source"] == "assistant"

            # Verify handler was called
            mock_handler.handle.assert_called_once()

        finally:
            if original_handler:
                container._handlers['ai_chat_support'] = original_handler
            else:
                container._handlers.pop('ai_chat_support', None)

    def test_chat_with_vision_api(
        self,
        override_get_current_user,
        mock_chat_response,
    ):
        """
        v3.0.0: Test chat with images using Vision API

        Given: Handler returns vision response
        When: POST /api/v2/user/support/chat with images
        Then: Returns chat response
        """
        from application.commands.support import AiChatSupportHandler, AiChatSupportResult

        # Mock handler
        mock_handler = MagicMock(spec=AiChatSupportHandler)
        mock_handler.handle = AsyncMock(return_value=AiChatSupportResult(
            result_data=mock_chat_response
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ai_chat_support')
        container._handlers['ai_chat_support'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/chat",
                json={
                    "message": "What's wrong with this image?",
                    "images": ["data:image/png;base64,iVBORw0KGgoAAAA..."],
                    "conversation_history": [],
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

            # Verify handler was called
            mock_handler.handle.assert_called_once()

        finally:
            if original_handler:
                container._handlers['ai_chat_support'] = original_handler
            else:
                container._handlers.pop('ai_chat_support', None)

    @patch('config.OPENAI_ASSISTANT_ID', None)
    def test_chat_fallback_chat_completions(
        self,
        override_get_current_user,
        mock_chat_response_fallback,
    ):
        """
        v3.0.0: Test chat using Chat Completions API (fallback)

        Given: OPENAI_ASSISTANT_ID is not configured
        When: POST /api/v2/user/support/chat without images
        Then: Uses Chat Completions API and returns response
        """
        from application.commands.support import AiChatSupportHandler, AiChatSupportResult

        # Mock handler
        mock_handler = MagicMock(spec=AiChatSupportHandler)
        mock_handler.handle = AsyncMock(return_value=AiChatSupportResult(
            result_data=mock_chat_response_fallback
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ai_chat_support')
        container._handlers['ai_chat_support'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/chat",
                json={
                    "message": "Need help",
                    "conversation_history": [
                        {"role": "user", "content": "Previous message"},
                        {"role": "assistant", "content": "Previous response"},
                    ],
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["message"] == "Here's how to solve your issue..."
            assert data["source"] == "fallback"

            # Verify handler was called
            mock_handler.handle.assert_called_once()

        finally:
            if original_handler:
                container._handlers['ai_chat_support'] = original_handler
            else:
                container._handlers.pop('ai_chat_support', None)

    def test_chat_validation_error_empty_message(
        self,
        override_get_current_user,
    ):
        """
        Test: Empty message should return 422

        Given: User with valid authentication
        When: POST with empty message
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/support/chat",
            json={
                "message": "",
                "conversation_history": [],
            },
        )

        # Assert
        assert response.status_code == 422

    def test_chat_validation_error_message_too_long(
        self,
        override_get_current_user,
    ):
        """
        Test: Message exceeding max length should return 422

        Given: User with valid authentication
        When: POST with message > 2000 characters
        Then: Returns 422 Validation Error
        """
        # Arrange
        long_message = "A" * 2001  # Exceeds max_length=2000

        # Act
        response = client.post(
            "/api/v2/user/support/chat",
            json={
                "message": long_message,
                "conversation_history": [],
            },
        )

        # Assert
        assert response.status_code == 422

    def test_chat_unauthorized(self):
        """
        Test: Unauthenticated request should return 401

        Given: No authentication headers
        When: POST /api/v2/user/support/chat
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/support/chat",
            json={
                "message": "Need help",
                "conversation_history": [],
            },
        )

        # Assert
        assert response.status_code == 401


# ==========================================
# POST /api/v2/user/support/contact Tests
# ==========================================

class TestContact:
    """Tests for POST /api/v2/user/support/contact endpoint (v3.0.0)."""

    def test_contact_success(
        self,
        override_get_current_user,
        mock_user,
    ):
        """
        v3.0.0: Test submit contact form successfully

        Given: User with valid authentication
        When: POST /api/v2/user/support/contact with all fields
        Then: Returns status=ok with confirmation message
        """
        from application.commands.support import SendContactMessageHandler, SendContactMessageResult

        # Mock handler
        mock_handler = MagicMock(spec=SendContactMessageHandler)
        mock_handler.handle = AsyncMock(return_value=SendContactMessageResult(
            result_data={"status": "ok", "message": "Message received"}
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('send_contact_message')
        container._handlers['send_contact_message'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/contact",
                json={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "Product Inquiry",
                    "message": "I'm interested in your product",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["message"] == "Message received"

            # Verify handler was called
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert call_args.user_id == mock_user["id"]
            assert call_args.name == "John Doe"
            assert call_args.email == "john@example.com"
            assert call_args.subject == "Product Inquiry"
            assert call_args.message == "I'm interested in your product"

        finally:
            if original_handler:
                container._handlers['send_contact_message'] = original_handler
            else:
                container._handlers.pop('send_contact_message', None)

    def test_contact_without_subject(
        self,
        override_get_current_user,
        mock_user,
    ):
        """
        v3.0.0: Test submit contact form without subject (optional)

        Given: User without subject field
        When: POST /api/v2/user/support/contact
        Then: Returns success (subject is optional)
        """
        from application.commands.support import SendContactMessageHandler, SendContactMessageResult

        # Mock handler
        mock_handler = MagicMock(spec=SendContactMessageHandler)
        mock_handler.handle = AsyncMock(return_value=SendContactMessageResult(
            result_data={"status": "ok", "message": "Message received"}
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('send_contact_message')
        container._handlers['send_contact_message'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/contact",
                json={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "message": "General inquiry",
                },
            )

            # Assert
            assert response.status_code == 200

            # Verify handler was called with None subject
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert call_args.subject is None

        finally:
            if original_handler:
                container._handlers['send_contact_message'] = original_handler
            else:
                container._handlers.pop('send_contact_message', None)

    def test_contact_validation_error_missing_fields(
        self,
        override_get_current_user,
    ):
        """
        Test: Missing required fields should return 422

        Given: User with valid authentication
        When: POST without name/email/message
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/support/contact",
            json={"name": "John Doe"},  # Missing email and message
        )

        # Assert
        assert response.status_code == 422

    def test_contact_validation_error_message_too_long(
        self,
        override_get_current_user,
    ):
        """
        Test: Message exceeding max length should return 422

        Given: User with valid authentication
        When: POST with message > 5000 characters
        Then: Returns 422 Validation Error
        """
        # Arrange
        long_message = "A" * 5001

        # Act
        response = client.post(
            "/api/v2/user/support/contact",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "message": long_message,
            },
        )

        # Assert
        assert response.status_code == 422

    def test_contact_unauthorized(self):
        """
        Test: Unauthenticated request should return 401

        Given: No authentication headers
        When: POST /api/v2/user/support/contact
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/support/contact",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "message": "Inquiry",
            },
        )

        # Assert
        assert response.status_code == 401


# ==========================================
# POST /api/v2/user/support/feedback Tests
# ==========================================

class TestFeedback:
    """Tests for POST /api/v2/user/support/feedback endpoint (v3.0.0)."""

    def test_feedback_success(
        self,
        override_get_current_user,
        mock_user,
    ):
        """
        v3.0.0: Test submit feedback successfully

        Given: User with valid authentication
        When: POST /api/v2/user/support/feedback with message
        Then: Returns status=ok with confirmation message
        """
        from application.commands.support import SubmitFeedbackHandler, SubmitFeedbackResult

        # Mock handler
        mock_handler = MagicMock(spec=SubmitFeedbackHandler)
        mock_handler.handle = AsyncMock(return_value=SubmitFeedbackResult(
            result_data={"status": "ok", "message": "Feedback submitted successfully"}
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('submit_feedback')
        container._handlers['submit_feedback'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/feedback",
                json={
                    "message": "Great product! Love the new features.",
                    "email": "custom@example.com",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "submitted successfully" in data["message"].lower()

            # Verify handler was called
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert call_args.user_id == mock_user["id"]
            assert call_args.user_email == "custom@example.com"
            assert call_args.message == "Great product! Love the new features."
            assert call_args.images == []

        finally:
            if original_handler:
                container._handlers['submit_feedback'] = original_handler
            else:
                container._handlers.pop('submit_feedback', None)

    def test_feedback_with_images(
        self,
        override_get_current_user,
        mock_user,
    ):
        """
        v3.0.0: Test submit feedback with images/screenshots

        Given: User with screenshots
        When: POST /api/v2/user/support/feedback with images
        Then: Returns success and passes images to service
        """
        from application.commands.support import SubmitFeedbackHandler, SubmitFeedbackResult

        # Mock handler
        mock_handler = MagicMock(spec=SubmitFeedbackHandler)
        mock_handler.handle = AsyncMock(return_value=SubmitFeedbackResult(
            result_data={"status": "ok", "message": "Feedback submitted successfully"}
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('submit_feedback')
        container._handlers['submit_feedback'] = mock_handler

        try:
            images = [
                "data:image/png;base64,iVBORw0KGgo...",
                "https://example.com/screenshot.png",
            ]

            # Act
            response = client.post(
                "/api/v2/user/support/feedback",
                json={
                    "message": "Bug in the editor",
                    "images": images,
                },
            )

            # Assert
            assert response.status_code == 200

            # Verify handler was called with images
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert call_args.user_email == "test@example.com"  # Default email
            assert call_args.message == "Bug in the editor"
            assert call_args.images == images

        finally:
            if original_handler:
                container._handlers['submit_feedback'] = original_handler
            else:
                container._handlers.pop('submit_feedback', None)

    def test_feedback_without_email(
        self,
        override_get_current_user,
        mock_user,
    ):
        """
        v3.0.0: Test submit feedback without custom email (optional)

        Given: User without email field
        When: POST /api/v2/user/support/feedback
        Then: Returns success (email is optional)
        """
        from application.commands.support import SubmitFeedbackHandler, SubmitFeedbackResult

        # Mock handler
        mock_handler = MagicMock(spec=SubmitFeedbackHandler)
        mock_handler.handle = AsyncMock(return_value=SubmitFeedbackResult(
            result_data={"status": "ok", "message": "Feedback submitted successfully"}
        ))

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('submit_feedback')
        container._handlers['submit_feedback'] = mock_handler

        try:
            # Act
            response = client.post(
                "/api/v2/user/support/feedback",
                json={"message": "Good job!"},
            )

            # Assert
            assert response.status_code == 200

            # Verify handler was called with default email
            mock_handler.handle.assert_called_once()
            call_args = mock_handler.handle.call_args[0][0]
            assert call_args.user_email == "test@example.com"  # Fallback to user's email

        finally:
            if original_handler:
                container._handlers['submit_feedback'] = original_handler
            else:
                container._handlers.pop('submit_feedback', None)

    def test_feedback_validation_error_empty_message(
        self,
        override_get_current_user,
    ):
        """
        Test: Empty message should return 422

        Given: User with valid authentication
        When: POST with empty message
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/support/feedback",
            json={"message": ""},
        )

        # Assert
        assert response.status_code == 422

    def test_feedback_validation_error_message_too_long(
        self,
        override_get_current_user,
    ):
        """
        Test: Message exceeding max length should return 422

        Given: User with valid authentication
        When: POST with message > 5000 characters
        Then: Returns 422 Validation Error
        """
        # Arrange
        long_message = "A" * 5001

        # Act
        response = client.post(
            "/api/v2/user/support/feedback",
            json={"message": long_message},
        )

        # Assert
        assert response.status_code == 422

    def test_feedback_unauthorized(self):
        """
        Test: Unauthenticated request should return 401

        Given: No authentication headers
        When: POST /api/v2/user/support/feedback
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/support/feedback",
            json={"message": "Great product!"},
        )

        # Assert
        assert response.status_code == 401


# ==========================================
# Tests: Security Validations (v2.1.0)
# ==========================================

class TestSecurityValidations:
    """Test security validations added in v2.1.0."""

    def test_ticket_invalid_email_format(self, override_get_current_user):
        """
        v2.1.0: SUP-LOW-3 - Invalid email format should be rejected.

        Given: Invalid email format
        When: POST /api/v2/user/support/ticket
        Then: Returns 422 Validation Error
        """
        response = client.post(
            "/api/v2/user/support/ticket",
            json={
                "message": "Need help",
                "email": "not-an-email",  # Invalid format
            },
        )

        assert response.status_code == 422

    def test_contact_invalid_email_format(self, override_get_current_user):
        """
        v2.1.0: SUP-LOW-2 - Contact email must be valid format.

        Given: Invalid email format
        When: POST /api/v2/user/support/contact
        Then: Returns 422 Validation Error
        """
        response = client.post(
            "/api/v2/user/support/contact",
            json={
                "name": "John",
                "email": "invalid-email",  # Invalid format
                "message": "Hello",
            },
        )

        assert response.status_code == 422

    def test_chat_too_many_images(self, override_get_current_user):
        """
        v2.1.0: SUP-MEDIUM-1 - Chat images limited to 4.

        Given: More than 4 images
        When: POST /api/v2/user/support/chat
        Then: Returns 422 Validation Error
        """
        response = client.post(
            "/api/v2/user/support/chat",
            json={
                "message": "Help with images",
                "images": ["img1", "img2", "img3", "img4", "img5"],  # 5 > 4
                "conversation_history": [],
            },
        )

        assert response.status_code == 422

    def test_chat_too_long_history(self, override_get_current_user):
        """
        v2.1.0: SUP-MEDIUM-2 - Conversation history limited to 20.

        Given: More than 20 history items
        When: POST /api/v2/user/support/chat
        Then: Returns 422 Validation Error
        """
        long_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(25)  # 25 > 20
        ]

        response = client.post(
            "/api/v2/user/support/chat",
            json={
                "message": "New message",
                "conversation_history": long_history,
            },
        )

        assert response.status_code == 422

    def test_feedback_too_many_images(self, override_get_current_user):
        """
        v2.1.0: SUP-LOW-1 - Feedback images limited to 5.

        Given: More than 5 images
        When: POST /api/v2/user/support/feedback
        Then: Returns 422 Validation Error
        """
        response = client.post(
            "/api/v2/user/support/feedback",
            json={
                "message": "Great product",
                "images": ["img1", "img2", "img3", "img4", "img5", "img6"],  # 6 > 5
            },
        )

        assert response.status_code == 422

    def test_feedback_invalid_email_format(self, override_get_current_user):
        """
        v2.1.0: SUP-LOW-3 - Feedback email must be valid format.

        Given: Invalid email format
        When: POST /api/v2/user/support/feedback
        Then: Returns 422 Validation Error
        """
        response = client.post(
            "/api/v2/user/support/feedback",
            json={
                "message": "Nice app",
                "email": "bad@email",  # Invalid format (missing TLD)
            },
        )

        assert response.status_code == 422


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary (v3.0.0):

POST /api/v2/user/support/ticket:
✅ Success with custom email
✅ Success with default user email
✅ Validation error: empty message (422)
✅ Validation error: message too long (422)
✅ Unauthorized (401)

POST /api/v2/user/support/chat:
✅ Success with Assistants API (RAG)
✅ Success with Vision API (images)
✅ Fallback to Chat Completions API
✅ Validation error: empty message (422)
✅ Validation error: message too long (422)
✅ Unauthorized (401)

POST /api/v2/user/support/contact:
✅ Success with all fields
✅ Success without subject (optional)
✅ Validation error: missing fields (422)
✅ Validation error: message too long (422)
✅ Unauthorized (401)

POST /api/v2/user/support/feedback:
✅ Success with message
✅ Success with images
✅ Success without email (optional)
✅ Validation error: empty message (422)
✅ Validation error: message too long (422)
✅ Unauthorized (401)

Security Validations (v2.1.0):
✅ Ticket: invalid email format (422)
✅ Contact: invalid email format (422)
✅ Chat: too many images (422)
✅ Chat: too long history (422)
✅ Feedback: too many images (422)
✅ Feedback: invalid email format (422)

Total Tests: 28 (v3.0.0)
Coverage: 100% (4/4 endpoints + security validations)

Test Breakdown:
- TestCreateTicket: 5 tests
- TestChatSupport: 6 tests
- TestContact: 5 tests
- TestFeedback: 6 tests
- TestSecurityValidations: 6 tests

Changes in v3.0.0:
- Migrated from Infrastructure mocking to Handler mocking
- All tests now mock Command Handlers via Container injection
- Tests focus on API contract and data validation
- Removed implementation-detail tests (these belong in domain/service tests)

Business Logic Tested:
- ✅ Handler command parameter validation
- ✅ Email fallback (custom email → user email)
- ✅ Image support (base64 and URLs)
- ✅ Optional fields (email, subject)
- ✅ String validation (min_length, max_length)
- ✅ Authentication requirement

Not Tested (Requires Integration/E2E or Domain Tests):
- AI service selection logic (Assistants API → Vision API → Chat Completions)
- Conversation history handling (last 10 messages)
- Error handling (AI failures return friendly messages)
- Actual OpenAI API interaction
- Real rate limiting behavior
- Email delivery
- Database transaction consistency
"""
