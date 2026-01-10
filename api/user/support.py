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
    user: dict = Depends(get_current_user),
) -> SupportResponse:
    """
    Create a support ticket.

    v3.0.0: Now uses CreateSupportTicketHandler (CQRS Command pattern).
    """
    container = get_container()
    handler = container.create_support_ticket_handler

    email = req.email or user.get("email", "unknown@user.com")

    command = CreateSupportTicketCommand(
        user_id=user["id"],
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
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    """
    AI-powered support chat.

    v3.0.0: Now uses AiChatSupportHandler (CQRS Command pattern).
    """
    from application.services import ai_chat_service
    from config import OPENAI_ASSISTANT_ID
    from shared.ai.story_generator import client as openai_client

    container = get_container()
    handler = container.ai_chat_support_handler

    command = AiChatSupportCommand(
        user_id=user["id"],
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
    user: dict = Depends(get_current_user),
) -> SupportResponse:
    """
    Submit contact form.

    v3.0.0: Now uses SendContactMessageHandler (CQRS Command pattern).
    """
    container = get_container()
    handler = container.send_contact_message_handler

    command = SendContactMessageCommand(
        user_id=user["id"],
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
    user: dict = Depends(get_current_user),
) -> SupportResponse:
    """
    Submit user feedback.

    v3.0.0: Now uses SubmitFeedbackHandler (CQRS Command pattern).
    """
    container = get_container()
    handler = container.submit_feedback_handler

    email = req.email or user.get("email", "unknown@user.com")

    command = SubmitFeedbackCommand(
        user_id=user["id"],
        user_email=email,
        message=req.message,
        images=req.images,
    )

    result = await handler.handle(command)

    return SupportResponse(**result.result_data)
