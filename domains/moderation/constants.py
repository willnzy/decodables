"""
Moderation Domain Constants.

@module domains.moderation.constants
@version 3.28
"""

# Moderation statuses for marketplace listings
VALID_MODERATION_STATUSES = {"pending", "approved", "rejected"}

# Resource types for marketplace listings
VALID_RESOURCE_TYPES = {"sticker", "clipart", "template", "font", "all"}

# Report statuses for content reports
VALID_REPORT_STATUSES = {"reviewed", "resolved", "dismissed"}

# Event types for logging
EVENT_MODERATION_APPROVE = "admin_moderation_approve"
EVENT_MODERATION_REJECT = "admin_moderation_reject"
EVENT_MODERATION_DELETE = "admin_moderation_delete"
EVENT_MODERATION_UNPUBLISH = "admin_moderation_unpublish"
EVENT_REPORT_RESPOND = "admin_report_respond"

# Operation types for admin logging
OP_LISTING_APPROVE = "listing_approve"
OP_LISTING_REJECT = "listing_reject"
OP_REPORT_RESPOND = "report_respond"
