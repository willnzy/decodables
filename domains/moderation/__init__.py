"""
Moderation Domain - Content moderation and marketplace listing approval.

@module domains.moderation
@version 3.28

This domain handles:
- Marketplace listing moderation (approve/reject/delete/unpublish)
- Content reports management (respond/stats)
- Admin operation logging
"""

from domains.moderation.service import (
    # Marketplace moderation
    get_moderation_list,
    get_moderation_detail,
    approve_listing,
    reject_listing,
    delete_listing,
    unpublish_listing,
    # Content reports
    get_reports,
    get_reports_stats,
    get_report_detail,
    respond_to_report,
)

__all__ = [
    # Marketplace moderation
    "get_moderation_list",
    "get_moderation_detail",
    "approve_listing",
    "reject_listing",
    "delete_listing",
    "unpublish_listing",
    # Content reports
    "get_reports",
    "get_reports_stats",
    "get_report_detail",
    "respond_to_report",
]
