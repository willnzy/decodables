"""
Support Repository Extended - Additional methods for services/db migration.

@module infrastructure.repositories.support_repository_extended
@version 1.0.0

Provides all support and report operations needed to replace services/db/support.py.
"""

import os
import logging
from typing import Optional, Dict, Any, List

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)

# Try to import email service
try:
    import resend
    resend.api_key = os.environ.get("RESEND_API_KEY")
    RESEND_ENABLED = bool(resend.api_key)
except ImportError:
    RESEND_ENABLED = False


class SupabaseSupportRepositoryExtended:
    """
    Extended support repository for support_tickets and reports tables.

    Provides all methods needed to replace services/db/support.py functions.
    """

    def __init__(self, client):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

    @retry_on_network_error()
    async def create_support_ticket(
        self,
        user_id: str,
        email: str,
        message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create support ticket.

        Args:
            user_id: User ID
            email: User email
            message: Support message

        Returns:
            Created ticket dict
        """
        result = self.client.table("support_tickets").insert({
            "user_id": user_id,
            "email": email,
            "message": message,
            "status": "open",
        }).execute()

        return result.data[0] if result.data else None

    def send_support_email(
        self,
        user_id: str,
        user_email: str,
        message: str,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send support email via Resend.

        Args:
            user_id: User ID
            user_email: User email
            message: Support message
            images: Optional list of image URLs

        Returns:
            Dict with success status
        """
        if not RESEND_ENABLED:
            logger.warning("Resend not configured, skipping email")
            return {"success": False, "error": "Email service not configured"}

        support_email = os.environ.get("SUPPORT_EMAIL", "support@makedecodables.com")

        # Build HTML content
        html_content = f"""
        <h2>Support Request</h2>
        <p><strong>From:</strong> {user_email}</p>
        <p><strong>User ID:</strong> {user_id}</p>
        <hr>
        <p>{message.replace(chr(10), '<br>')}</p>
        """

        if images:
            html_content += "<h3>Attachments:</h3>"
            for i, img in enumerate(images):
                html_content += f'<p><a href="{img}">Image {i+1}</a></p>'

        try:
            resend.Emails.send({
                "from": "MakeDecodables <noreply@makedecodables.com>",
                "to": [support_email],
                "subject": f"Support Request from {user_email}",
                "html": html_content,
                "reply_to": user_email,
            })

            # Log ticket (synchronous helper)
            self.client.table("support_tickets").insert({
                "user_id": user_id,
                "email": user_email,
                "message": message,
                "status": "open",
            }).execute()

            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to send support email: {e}")
            return {"success": False, "error": str(e)}

    def send_feedback_with_images(
        self,
        user_id: str,
        user_email: str,
        message: str,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send feedback (alias for support email).

        Args:
            user_id: User ID
            user_email: User email
            message: Feedback message
            images: Optional list of image URLs

        Returns:
            Dict with success status
        """
        return self.send_support_email(user_id, user_email, message, images)

    @retry_on_network_error()
    async def create_report(
        self,
        reporter_id: str,
        listing_id: str,
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create content report.

        Args:
            reporter_id: Reporter user ID
            listing_id: Listing ID being reported
            reason: Report reason

        Returns:
            Created report dict
        """
        result = self.client.table("reports").insert({
            "reporter_id": reporter_id,
            "listing_id": listing_id,
            "reason": reason,
            "status": "pending",
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_user_reports(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's reports.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            List of report dicts
        """
        offset = (page - 1) * limit
        result = self.client.table("reports").select("*").eq(
            "reporter_id", user_id
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        return result.data or []
