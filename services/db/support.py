"""
Database Support - Support ticket and feedback operations

@module services.db.support
@version 3.24
"""

import os
import logging
from datetime import datetime, timezone

from .core import supabase, retry_on_network_error

logger = logging.getLogger(__name__)

# Try to import email service
try:
    import resend
    resend.api_key = os.environ.get("RESEND_API_KEY")
    RESEND_ENABLED = bool(resend.api_key)
except ImportError:
    RESEND_ENABLED = False


@retry_on_network_error()
def create_support_ticket(user_id: str, email: str, message: str):
    """Create support ticket."""
    if not supabase:
        return None
    
    result = supabase.table("support_tickets").insert({
        "user_id": user_id,
        "email": email,
        "message": message,
        "status": "open",
    }).execute()
    
    return result.data[0] if result.data else None


def send_support_email(user_id: str, user_email: str, message: str, images: list = None):
    """Send support email."""
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
        
        # Log ticket
        create_support_ticket(user_id, user_email, message)
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to send support email: {e}")
        return {"success": False, "error": str(e)}


def send_feedback_with_images(user_id: str, user_email: str, message: str, images: list = None):
    """Send feedback (alias for support email)."""
    return send_support_email(user_id, user_email, message, images)


# ==========================================
# Reports
# ==========================================

@retry_on_network_error()
def create_report(reporter_id: str, listing_id: str, reason: str):
    """Create content report."""
    if not supabase:
        return None
    
    result = supabase.table("reports").insert({
        "reporter_id": reporter_id,
        "listing_id": listing_id,
        "reason": reason,
        "status": "pending",
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def get_user_reports(user_id: str, page: int = 1, limit: int = 20):
    """Get user's reports."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    result = supabase.table("reports").select("*")\
        .eq("reporter_id", user_id)\
        .order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return result.data or []
