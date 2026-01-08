"""
Support API - Customer support and feedback endpoints (v2).

@module api.user.support
@version 2.1.0

Changes:
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
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.support_repository import SupabaseSupportRepository
from core.database import get_database_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["user-support-v2"])


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
    """Create a support ticket."""
    email = req.email or user.get("email", "unknown@user.com")
    support_repo = SupabaseSupportRepository(get_database_client())
    await support_repo.create_support_ticket(user["id"], email, req.message)
    return SupportResponse(status="ok")


@router.post("/chat")
@limiter.limit("20/minute")
async def chat_support(
    request: Request,
    req: ChatSupportRequest,
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    """AI-powered support chat."""
    from application.services.ai_chat_service import chat_with_assistant, chat_with_vision, SUPPORT_SYSTEM_PROMPT_FALLBACK
    from config import OPENAI_ASSISTANT_ID
    from shared.ai.story_generator import client as openai_client

    try:
        # Use vision API if images provided
        if req.images:
            result = await chat_with_vision(
                req.message,
                req.images,
                req.conversation_history,
            )
            return ChatResponse(**result)

        # Use Assistants API for text-only (with RAG)
        if OPENAI_ASSISTANT_ID:
            result = await chat_with_assistant(
                req.message,
                req.conversation_history,
            )
            return ChatResponse(**result)

        # Fallback to Chat Completions
        messages = [
            {"role": "system", "content": SUPPORT_SYSTEM_PROMPT_FALLBACK}
        ]
        for msg in req.conversation_history[-10:]:
            if msg.get("role") in ["user", "assistant"]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": req.message})

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )

        return ChatResponse(
            status="ok",
            message=response.choices[0].message.content,
            source="fallback",
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            status="error",
            message="I'm having trouble right now. Please try again or contact us at info@makedecodables.com",
            error=str(e),
        )


@router.post("/contact")
@limiter.limit("5/minute")
async def contact(
    request: Request,
    req: ContactRequest,
    user: dict = Depends(get_current_user),
) -> SupportResponse:
    """Submit contact form."""

    support_repo = SupabaseSupportRepository(get_database_client())
    support_repo.send_support_email(
        user_id=user["id"],
        user_email=req.email,
        message=f"Name: {req.name}\nSubject: {req.subject or 'N/A'}\n\n{req.message}",
    )
    return SupportResponse(status="ok", message="Message received")


@router.post("/feedback")
@limiter.limit("5/minute")
async def feedback(
    request: Request,
    req: FeedbackRequest,
    user: dict = Depends(get_current_user),
) -> SupportResponse:
    """Submit user feedback."""
    support_repo = SupabaseSupportRepository(get_database_client())
    email = req.email or user.get("email", "unknown@user.com")
    support_repo.send_feedback_with_images(user["id"], email, req.message, req.images)
    return SupportResponse(status="ok", message="Feedback submitted successfully")
