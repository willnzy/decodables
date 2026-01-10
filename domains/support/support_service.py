"""
Support Service - Support and report management service.

@module domains.support.support_service
@version 3.1.0

Changes:
- v3.1.0: DDD architecture expansion - User support features
  - Added create_support_ticket() - Support ticket submission
  - Added process_ai_chat() - AI-powered chat support
  - Added send_contact_message() - Contact form submission
  - Added submit_feedback() - User feedback with images
  - All validation and business logic moved from API layer

- v3.0.0: Initial DDD compliance
  - Created for marketplace reports (MARKET-CRITICAL-1 fix)

Service for managing support tickets, AI chat, and marketplace reports.
Encapsulates business logic for all support-related operations.
"""

import logging
import re
from typing import Dict, List, Any, Optional

from infrastructure.repositories.support_repository import SupabaseSupportRepository
from infrastructure.logging.activity_logger import log_activity

logger = logging.getLogger(__name__)

# v3.1.0: Email validation pattern
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class ReportAlreadyExistsException(Exception):
    """Raised when user already reported this listing."""
    pass


class SupportService:
    """
    Service for support and report management.

    Handles marketplace content reports with business logic validation.

    Responsibilities:
    - Create marketplace content reports with duplicate detection
    - Retrieve user's reports with pagination
    - Activity logging for all report submissions

    Architecture: API → SupportService → Repository

    v3.0.0: Created for DDD compliance (MARKET-CRITICAL-1 fix)
    """

    def __init__(self, db_client):
        """
        Initialize SupportService.

        Args:
            db_client: Supabase database client
        """
        self.repository = SupabaseSupportRepository(db_client)

    # ==========================================
    # Public Methods
    # ==========================================

    async def create_report(
        self,
        user_id: str,
        listing_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Create a marketplace content report.

        Args:
            user_id: Reporter user ID
            listing_id: Listing being reported
            reason: Report reason

        Returns:
            Dict: Created report record

        Raises:
            ReportAlreadyExistsException: If user already reported this listing

        Example:
            >>> report = await service.create_report(
            ...     "user_123",
            ...     "listing_abc",
            ...     "Copyright violation"
            ... )
        """
        try:
            report = await self.repository.create_report(user_id, listing_id, reason)

            if report:
                # Log activity
                log_activity(user_id, "submit_report", {"listing_id": listing_id})

            return report

        except Exception as e:
            error_msg = str(e)
            # Translate repository exception to domain exception
            if "already reported" in error_msg.lower():
                raise ReportAlreadyExistsException("You have already reported this listing")
            # Re-raise other exceptions
            raise

    async def get_user_reports(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get reports submitted by a user with pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            tuple: (reports, total_count)
                - reports: List of report records
                - total_count: Total number of matching records

        Example:
            >>> reports, total = await service.get_user_reports("user_123", page=1, limit=20)
            >>> print(f"Found {total} reports, showing {len(reports)}")
        """
        reports, total_count = await self.repository.get_user_reports_with_count(
            user_id, page, limit
        )

        return reports, total_count

    # ==========================================
    # v3.1.0: User Support Methods
    # ==========================================

    def validate_email(self, email: Optional[str]) -> Optional[str]:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            Validated email or None

        Raises:
            ValueError: If email format is invalid
        """
        if email is None:
            return None
        if not EMAIL_PATTERN.match(email):
            raise ValueError("Invalid email format")
        return email

    async def create_support_ticket(
        self,
        user_id: str,
        user_email: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Create a support ticket.

        v3.1.0: Moved from API layer with email validation.

        Args:
            user_id: User ID
            user_email: User email (validated)
            message: Support message

        Returns:
            Dict: Success status

        Example:
            >>> result = await service.create_support_ticket(
            ...     "user_123",
            ...     "user@example.com",
            ...     "I need help with..."
            ... )
        """
        # Validate email format
        self.validate_email(user_email)

        # Create ticket in database
        await self.repository.create_ticket(
            user_id=user_id,
            subject="Support Request",
            message=f"From: {user_email}\n\n{message}",
            priority="medium",
        )

        # Log activity
        log_activity(user_id, "create_support_ticket", {
            "email": user_email,
        })

        return {"status": "ok"}

    async def process_ai_chat(
        self,
        user_id: str,
        message: str,
        images: List[str],
        conversation_history: List[Dict[str, Any]],
        ai_chat_service,
        openai_assistant_id: Optional[str],
        openai_client,
        support_system_prompt: str,
    ) -> Dict[str, Any]:
        """
        Process AI-powered support chat.

        v3.1.0: Extracted AI chat logic from API layer.

        Args:
            user_id: User ID
            message: User message
            images: List of image URLs
            conversation_history: Previous conversation
            ai_chat_service: AI chat service module
            openai_assistant_id: OpenAI Assistant ID (optional)
            openai_client: OpenAI client
            support_system_prompt: System prompt for fallback

        Returns:
            Dict: Chat response with status, message, source, error

        Example:
            >>> result = await service.process_ai_chat(
            ...     "user_123",
            ...     "How do I...?",
            ...     [],
            ...     [],
            ...     ai_chat_service,
            ...     assistant_id,
            ...     client,
            ...     prompt
            ... )
        """
        try:
            # Use vision API if images provided
            if images:
                result = await ai_chat_service.chat_with_vision(
                    message,
                    images,
                    conversation_history,
                )
                return result

            # Use Assistants API for text-only (with RAG)
            if openai_assistant_id:
                result = await ai_chat_service.chat_with_assistant(
                    message,
                    conversation_history,
                )
                return result

            # Fallback to Chat Completions
            messages = [
                {"role": "system", "content": support_system_prompt}
            ]
            for msg in conversation_history[-10:]:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": message})

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )

            return {
                "status": "ok",
                "message": response.choices[0].message.content,
                "source": "fallback",
            }

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "status": "error",
                "message": "I'm having trouble right now. Please try again or contact us at info@makedecodables.com",
                "error": str(e),
            }

    async def send_contact_message(
        self,
        user_id: str,
        name: str,
        email: str,
        message: str,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send contact form message.

        v3.1.0: Moved from API layer with email validation.

        Args:
            user_id: User ID
            name: Sender name
            email: Sender email
            message: Contact message
            subject: Optional subject

        Returns:
            Dict: Success status and message

        Example:
            >>> result = await service.send_contact_message(
            ...     "user_123",
            ...     "John Doe",
            ...     "john@example.com",
            ...     "I have a question...",
            ...     "Question about features"
            ... )
        """
        # Validate email format
        self.validate_email(email)

        # Format message with metadata
        formatted_message = f"Name: {name}\nSubject: {subject or 'N/A'}\n\n{message}"

        # Create ticket (using repository's create_ticket method)
        await self.repository.create_ticket(
            user_id=user_id,
            subject=subject or "Contact Form",
            message=formatted_message,
            priority="medium",
        )

        # Log activity
        log_activity(user_id, "contact_form", {
            "name": name,
            "email": email,
        })

        return {"status": "ok", "message": "Message received"}

    async def submit_feedback(
        self,
        user_id: str,
        user_email: str,
        message: str,
        images: List[str],
    ) -> Dict[str, Any]:
        """
        Submit user feedback with optional images.

        v3.1.0: Moved from API layer with email validation.

        Args:
            user_id: User ID
            user_email: User email
            message: Feedback message
            images: List of image URLs (max 5)

        Returns:
            Dict: Success status and message

        Example:
            >>> result = await service.submit_feedback(
            ...     "user_123",
            ...     "user@example.com",
            ...     "Great product!",
            ...     ["https://example.com/screenshot.png"]
            ... )
        """
        # Validate email format
        self.validate_email(user_email)

        # Format message with images
        formatted_message = message
        if images:
            formatted_message += f"\n\nAttached images ({len(images)}):\n" + "\n".join(images)

        # Create ticket
        await self.repository.create_ticket(
            user_id=user_id,
            subject="User Feedback",
            message=f"From: {user_email}\n\n{formatted_message}",
            priority="low",
            category="feedback",
        )

        # Log activity
        log_activity(user_id, "submit_feedback", {
            "email": user_email,
            "has_images": len(images) > 0,
        })

        return {"status": "ok", "message": "Feedback submitted successfully"}
