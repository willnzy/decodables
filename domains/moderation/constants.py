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
# WS-14: Added "pending" as initial state
REPORT_STATUS_PENDING = "pending"
REPORT_STATUS_REVIEWED = "reviewed"
REPORT_STATUS_RESOLVED = "resolved"
REPORT_STATUS_DISMISSED = "dismissed"
VALID_REPORT_STATUSES = {"pending", "reviewed", "resolved", "dismissed"}

# WS-14: Report 状态转换矩阵
VALID_REPORT_TRANSITIONS = {
    "pending": {"reviewed", "resolved", "dismissed"},
    "reviewed": {"resolved", "dismissed"},
    "resolved": set(),    # 终态
    "dismissed": set(),   # 终态
}

# WS-14: Listing moderation 状态转换矩阵
VALID_LISTING_TRANSITIONS = {
    "pending": {"approved", "rejected"},
    "approved": {"rejected"},   # 可撤销审批
    "rejected": {"pending"},    # 可重新提交
}

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
