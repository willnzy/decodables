"""
Support API - Customer support and feedback endpoints.

@module api.support_api
@version 1.0.0

Endpoints:
- POST /api/v2/support/ticket - Create support ticket
- POST /api/v2/support/chat - AI support chat
- POST /api/v2/support/contact - Contact form
- POST /api/v2/support/feedback - Submit feedback
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from dependencies import get_current_user
from services.db_service import create_support_ticket, send_feedback_with_images
from services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/support", tags=["support-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class SupportTicketRequest(BaseModel):
    """Support ticket request."""
    message: str = Field(..., min_length=1, max_length=5000)
    email: Optional[str] = None


class ChatSupportRequest(BaseModel):
    """AI chat support request."""
    message: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = []  # Base64 or URLs
    conversation_history: List[Dict[str, Any]] = []


class ContactRequest(BaseModel):
    """Contact form request."""
    name: str = Field(..., min_length=1, max_length=100)
    email: str
    message: str = Field(..., min_length=1, max_length=5000)
    subject: Optional[str] = Field(None, max_length=200)


class FeedbackRequest(BaseModel):
    """Feedback request."""
    message: str = Field(..., min_length=1, max_length=5000)
    email: Optional[str] = None
    images: List[str] = []


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
    create_support_ticket(user["id"], email, req.message)
    return SupportResponse(status="ok")


@router.post("/chat")
@limiter.limit("20/minute")
async def chat_support(
    request: Request,
    req: ChatSupportRequest,
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    """AI-powered support chat."""
    from services.ai_chat_service import chat_with_assistant, chat_with_vision, SUPPORT_SYSTEM_PROMPT_FALLBACK
    from config import OPENAI_ASSISTANT_ID
    from services.ai.story_generator import client as openai_client

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
    from services.db_service import save_contact_message

    save_contact_message(
        user_id=user["id"],
        name=req.name,
        email=req.email,
        subject=req.subject,
        message=req.message,
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
    send_feedback_with_images(user["id"], req.email, req.message, req.images)
    return SupportResponse(status="ok", message="Feedback submitted successfully")
