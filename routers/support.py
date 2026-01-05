"""
Support Router - Customer support and feedback endpoints

@module routers.support
@version 3.24

Endpoints:
- POST /api/support/email - Create support ticket
- POST /api/chat/support - AI support chat
- POST /api/contact - Contact form
- POST /api/feedback - Submit feedback
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from services.db_service import create_support_ticket, send_feedback_with_images
from services.rate_limiter import limiter
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["support"])


# ==========================================
# Request Models
# ==========================================

class SupportTicketRequest(BaseModel):
    message: str
    email: Optional[str] = None


class ChatSupportRequest(BaseModel):
    message: str
    images: List[str] = []  # Base64 or URLs
    conversation_history: List[dict] = []


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str
    subject: Optional[str] = None


class FeedbackRequest(BaseModel):
    email: Optional[str] = None
    message: str
    images: List[str] = []


# ==========================================
# Support Endpoints
# ==========================================

@router.post("/api/support/email")
@limiter.limit("3/minute")
def ticket(request: Request, req: SupportTicketRequest, user: dict = Depends(get_current_user)):
    """Create a support ticket."""
    email = req.email or user.get("email", "unknown@user.com")
    create_support_ticket(user["id"], email, req.message)
    return {"status": "ok"}


@router.post("/api/chat/support")
@limiter.limit("20/minute")
async def chat_support(
    request: Request,
    req: ChatSupportRequest,
    user: dict = Depends(get_current_user)
):
    """AI-powered support chat."""
    from services.ai_chat_service import chat_with_assistant, chat_with_vision, SUPPORT_SYSTEM_PROMPT_FALLBACK
    from config import OPENAI_ASSISTANT_ID
    from services.ai.story_generator import client as openai_client
    
    try:
        # Use vision API if images provided
        if req.images:
            return await chat_with_vision(
                req.message, 
                req.images, 
                req.conversation_history
            )
        
        # Use Assistants API for text-only (with RAG)
        if OPENAI_ASSISTANT_ID:
            return await chat_with_assistant(
                req.message,
                req.conversation_history
            )
        
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
            max_tokens=500
        )
        
        return {
            "status": "ok",
            "message": response.choices[0].message.content,
            "source": "fallback"
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {
            "status": "error",
            "message": "I'm having trouble right now. Please try again or contact us at info@makedecodables.com",
            "error": str(e)
        }


@router.post("/api/contact")
@limiter.limit("5/minute")
def contact(request: Request, req: ContactRequest, user: dict = Depends(get_current_user)):
    """Submit contact form."""
    from services.db_service import save_contact_message
    
    save_contact_message(
        user_id=user["id"],
        name=req.name,
        email=req.email,
        subject=req.subject,
        message=req.message
    )
    return {"status": "ok", "message": "Message received"}


@router.post("/api/feedback")
@limiter.limit("5/minute")
def feedback(request: Request, req: FeedbackRequest, user: dict = Depends(get_current_user)):
    """Submit user feedback."""
    user_id = user["id"]
    send_feedback_with_images(user_id, req.email, req.message, req.images)
    return {"status": "ok", "message": "Feedback submitted successfully"}
