"""
Support Schemas - Support ticket and feedback models

@module schemas.support
"""

from typing import Optional, List
from pydantic import BaseModel


class SupportTicketRequest(BaseModel):
    """Support ticket request."""
    email: Optional[str] = None  # Optional - will use user's email if not provided
    message: str


class ChatImageData(BaseModel):
    """Image data for chat."""
    name: str
    data: str  # Base64 encoded image


class ChatSupportRequest(BaseModel):
    """Request model for AI support chat."""
    message: str
    conversation_history: Optional[List[dict]] = []  # Previous messages for context
    images: Optional[List[ChatImageData]] = []  # Optional images for vision analysis


class ContactFormRequest(BaseModel):
    """Contact form request."""
    email: str  # Required for guest users
    message: str


class FeedbackWithImagesRequest(BaseModel):
    """Feedback with images request."""
    email: str
    message: str
    images: Optional[List[dict]] = []  # List of {name, data} where data is base64
