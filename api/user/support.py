"""
Support API - Customer support and feedback endpoints (v3).

@module api.user.support
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - CQRS Command pattern
  - Created SupportService v3.1.0 with 4 new methods
  - Added CreateSupportTicketHandler (Command Handler)
  - Added AiChatSupportHandler (Command Handler)
  - Added SendContactMessageHandler (Command Handler)
  - Added SubmitFeedbackHandler (Command Handler)
  - Eliminated direct Repository calls from API layer
  - Moved all business logic to Service layer
  - Improved testability and maintainability

- v2.1.0: Security improvements
  - SUP-MEDIUM-1: Added images list size limit (max 4)
  - SUP-MEDIUM-2: Added conversation_history size limit (max 20)
  - SUP-LOW-1: Added feedback images limit (max 5)
  - SUP-LOW-2: Added email format validation
  - SUP-LOW-3: Added email format validation for optional emails

Endpoints:
- POST /api/v2/user/support/ticket - Create support ticket
- POST /api/v2/user/support/chat - AI support chat
- POST /api/v2/user/support/contact - Contact form
- POST /api/v2/user/support/feedback - Submit feedback
"""

import logging
import re
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user
from container import get_container
from application.commands.support import (
    CreateSupportTicketCommand,
    AiChatSupportCommand,
    SendContactMessageCommand,
    SubmitFeedbackCommand,
)
from infrastructure.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["user-support-v3"])


# ==========================================
# Constants (v2.1.0)
# ==========================================

# v2.1.0: SUP-MEDIUM-1 - Max images in chat request
MAX_CHAT_IMAGES = 4

# v2.1.0: SUP-MEDIUM-2 - Max conversation history items
MAX_CONVERSATION_HISTORY = 20

# v2.1.0: SUP-LOW-1 - Max images in feedback
MAX_FEEDBACK_IMAGES = 5

# v2.1.0: SUP-LOW-2/3 - Email validation pattern
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_email_format(email: Optional[str]) -> Optional[str]:
    """Validate email format if provided."""
    if email is None:
        return None
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email format")
    return email


# ==========================================
# Request/Response Models
# ==========================================

class SupportTicketRequest(BaseModel):
    """Support ticket request."""
    message: str = Field(..., min_length=1, max_length=5000)
    email: Optional[str] = None

    # v2.1.0: SUP-LOW-3 - Email validation
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return validate_email_format(v)


class ChatSupportRequest(BaseModel):
    """AI chat support request."""
    message: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = Field(default=[], max_length=MAX_CHAT_IMAGES)  # v2.1.0: SUP-MEDIUM-1
    conversation_history: List[Dict[str, Any]] = Field(default=[], max_length=MAX_CONVERSATION_HISTORY)  # v2.1.0: SUP-MEDIUM-2


class ContactRequest(BaseModel):
    """Contact form request."""
    name: str = Field(..., min_length=1, max_length=100)
    email: str
    message: str = Field(..., min_length=1, max_length=5000)
    subject: Optional[str] = Field(None, max_length=200)

    # v2.1.0: SUP-LOW-2 - Email format validation
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not EMAIL_PATTERN.match(v):
            raise ValueError("Invalid email format")
        return v


class FeedbackRequest(BaseModel):
    """Feedback request."""
    message: str = Field(..., min_length=1, max_length=5000)
    email: Optional[str] = None
    images: List[str] = Field(default=[], max_length=MAX_FEEDBACK_IMAGES)  # v2.1.0: SUP-LOW-1

    # v2.1.0: SUP-LOW-3 - Email validation
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return validate_email_format(v)


class SupportResponse(BaseModel):
    """Generic support response."""
    status: str
    message: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat support response."""
    status: str
    message: str
    source: Optional[str] = None
    error: Optional[str] = None


# ==========================================
# Endpoints
# ==========================================

@router.post("/ticket")
@limiter.limit("3/minute")
async def create_ticket(
    request: Request,
    req: SupportTicketRequest,
    user: UserProfile = Depends(get_current_user),
) -> SupportResponse:
    """
    Create a support ticket for customer assistance.

    Allows users to submit support requests that require human agent intervention.
    Tickets are stored in the database and can be managed through the admin panel.
    Users receive confirmation via email (if provided).

    v3.0.0: Uses CreateSupportTicketHandler (CQRS Command pattern).
    v2.1.0: Added email format validation (SUP-LOW-3).

    Args:
        req: Support ticket request containing:
            - message: Detailed description of the issue or question (1-5000 chars, required)
            - email: Contact email for ticket updates (optional)
                If not provided, uses user's registered email
                Must be valid email format if provided

    Returns:
        SupportResponse containing:
            - status: "success" if ticket created successfully
            - message: Confirmation message with ticket ID or next steps

    Raises:
        400: Invalid email format or message validation error
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 3 requests per minute)
        500: Database error or email service failure

    Security:
        - Authentication required
        - Rate limit: 3 requests per minute (prevent spam)
        - Email format validated with regex
        - Message length limited to 5000 chars
        - User ID automatically attached to ticket

    Example:
        POST /api/v2/user/support/ticket
        {
            "message": "I'm unable to export my project as PDF. The download keeps failing.",
            "email": "user@example.com"
        }

        Response:
        {
            "status": "success",
            "message": "Support ticket created successfully. Ticket ID: #12345"
        }
    """
    container = get_container()
    handler = await container.get_create_support_ticket_handler()

    email = req.email or user.email or "unknown@user.com"

    command = CreateSupportTicketCommand(
        user_id=user.user_id,
        user_email=email,
        message=req.message,
    )

    result = await handler.handle(command)

    return SupportResponse(**result.result_data)


@router.post("/chat")
@limiter.limit("20/minute")
async def chat_support(
    request: Request,
    req: ChatSupportRequest,
    user: UserProfile = Depends(get_current_user),
) -> ChatResponse:
    """
    AI-powered support chat for instant assistance.

    Provides real-time AI assistant responses for common user questions and troubleshooting.
    Uses OpenAI Assistant API with custom support knowledge base. Supports multi-turn
    conversations with context history and image attachments for visual debugging.

    v3.0.0: Uses AiChatSupportHandler (CQRS Command pattern).
    v2.1.0: Added limits for images (max 4) and conversation history (max 20).

    Args:
        req: Chat support request containing:
            - message: User's question or message (1-2000 chars, required)
            - images: List of image URLs for visual context (max 4 images)
                Useful for sharing screenshots of errors or UI issues
                Empty list by default
            - conversation_history: Previous messages for context (max 20 messages)
                Format: [{"role": "user"|"assistant", "content": "..."}]
                Enables multi-turn conversations
                Empty list by default

    Returns:
        ChatResponse containing:
            - status: "success" or "error"
            - message: AI assistant's response text
            - source: Response source (e.g., "openai_assistant", "fallback")
            - error: Error message if status is "error" (null otherwise)

    Raises:
        400: Invalid message length, too many images (>4), or too long conversation history (>20)
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 20 requests per minute)
        500: AI service unavailable or unexpected error

    Security:
        - Authentication required
        - Rate limit: 20 requests per minute
        - Images limited to 4 per request (SUP-MEDIUM-1)
        - Conversation history limited to 20 messages (SUP-MEDIUM-2)
        - Message length limited to 2000 chars
        - Fallback to system prompt if OpenAI Assistant unavailable

    Example:
        POST /api/v2/user/support/chat
        {
            "message": "How do I add custom fonts to my project?",
            "images": [],
            "conversation_history": [
                {"role": "user", "content": "Hello, I need help with fonts"},
                {"role": "assistant", "content": "Sure! What would you like to know about fonts?"}
            ]
        }

        Response:
        {
            "status": "success",
            "message": "To add custom fonts, go to the Text Properties panel and click 'Add Font'...",
            "source": "openai_assistant",
            "error": null
        }
    """
    from application.services import ai_chat_service
    from config import OPENAI_ASSISTANT_ID
    from shared.ai.story_generator import client as openai_client

    container = get_container()
    handler = await container.get_ai_chat_support_handler()

    command = AiChatSupportCommand(
        user_id=user.user_id,
        message=req.message,
        images=req.images,
        conversation_history=req.conversation_history,
        ai_chat_service=ai_chat_service,
        openai_assistant_id=OPENAI_ASSISTANT_ID,
        openai_client=openai_client,
        support_system_prompt=ai_chat_service.SUPPORT_SYSTEM_PROMPT_FALLBACK,
    )

    result = await handler.handle(command)

    return ChatResponse(**result.result_data)


@router.post("/contact")
@limiter.limit("5/minute")
async def contact(
    request: Request,
    req: ContactRequest,
    user: UserProfile = Depends(get_current_user),
) -> SupportResponse:
    """
    Submit contact form for general inquiries or business requests.

    Allows users to send messages to the Make Decodables team for inquiries,
    partnerships, feature requests, or other non-support related communication.
    Messages are sent via email and stored in the database for tracking.

    v3.0.0: Uses SendContactMessageHandler (CQRS Command pattern).
    v2.1.0: Added email format validation (SUP-LOW-2).

    Args:
        req: Contact form request containing:
            - name: Sender's name (1-100 chars, required)
            - email: Sender's email address (required, validated format)
                Must be valid email format
            - message: Message content (1-5000 chars, required)
            - subject: Optional subject line (max 200 chars)
                If not provided, a default subject is used

    Returns:
        SupportResponse containing:
            - status: "success" if message sent successfully
            - message: Confirmation message

    Raises:
        400: Invalid email format, missing required fields, or validation error
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 5 requests per minute)
        500: Email service failure or database error

    Security:
        - Authentication required
        - Rate limit: 5 requests per minute (prevent spam)
        - Email format strictly validated with regex pattern
        - Message length limited to 5000 chars
        - Name length limited to 100 chars
        - Subject length limited to 200 chars

    Example:
        POST /api/v2/user/support/contact
        {
            "name": "John Doe",
            "email": "john.doe@school.edu",
            "subject": "Educational Partnership Inquiry",
            "message": "I'm interested in using Make Decodables for my classroom of 30 students. Do you offer educational discounts?"
        }

        Response:
        {
            "status": "success",
            "message": "Your message has been sent successfully. We'll get back to you soon!"
        }
    """
    container = get_container()
    handler = await container.get_send_contact_message_handler()

    command = SendContactMessageCommand(
        user_id=user.user_id,
        name=req.name,
        email=req.email,
        message=req.message,
        subject=req.subject,
    )

    result = await handler.handle(command)

    return SupportResponse(**result.result_data)


@router.post("/feedback")
@limiter.limit("5/minute")
async def feedback(
    request: Request,
    req: FeedbackRequest,
    user: UserProfile = Depends(get_current_user),
) -> SupportResponse:
    """
    Submit user feedback for product improvement.

    Allows users to share feedback, suggestions, bug reports, or feature requests
    to help improve the Make Decodables platform. Feedback is stored in the database
    and reviewed by the product team. Supports image attachments for visual feedback.

    v3.0.0: Uses SubmitFeedbackHandler (CQRS Command pattern).
    v2.1.0: Added image limit (max 5) and email validation (SUP-LOW-1, SUP-LOW-3).

    Args:
        req: Feedback request containing:
            - message: Feedback content (1-5000 chars, required)
                Can include: bug reports, feature requests, suggestions, complaints
            - email: Contact email for follow-up (optional)
                If not provided, uses user's registered email
                Must be valid email format if provided
            - images: List of image URLs for visual feedback (max 5 images)
                Useful for sharing screenshots of bugs, UI suggestions, etc.
                Empty list by default

    Returns:
        SupportResponse containing:
            - status: "success" if feedback submitted successfully
            - message: Confirmation message

    Raises:
        400: Invalid email format, too many images (>5), or validation error
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 5 requests per minute)
        500: Database error or storage failure

    Security:
        - Authentication required
        - Rate limit: 5 requests per minute (prevent spam)
        - Email format validated if provided
        - Message length limited to 5000 chars
        - Images limited to 5 per request (SUP-LOW-1)
        - User ID automatically attached to feedback

    Example:
        POST /api/v2/user/support/feedback
        {
            "message": "The new canvas editor is amazing! However, I'd love to see a grid snap feature for precise alignment.",
            "email": "user@example.com",
            "images": [
                "https://example.com/screenshot1.png"
            ]
        }

        Response:
        {
            "status": "success",
            "message": "Thank you for your feedback! We appreciate your input."
        }
    """
    container = get_container()
    handler = await container.get_submit_feedback_handler()

    email = req.email or user.email or "unknown@user.com"

    command = SubmitFeedbackCommand(
        user_id=user.user_id,
        user_email=email,
        message=req.message,
        images=req.images,
    )

    result = await handler.handle(command)

    return SupportResponse(**result.result_data)
