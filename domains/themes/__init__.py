"""Themes Domain - Holiday themes management.

@module domains.themes
@version 2.1.0
"""

from domains.themes.themes_service import ThemesService
from domains.themes.constants import (
    # Categories
    VALID_CATEGORIES,
    CATEGORY_HOLIDAY,
    CATEGORY_MEMORIAL,
    CATEGORY_HISTORICAL,
    CATEGORY_NOTABLE,
    CATEGORY_CAMPAIGN,
    CATEGORY_SPECIAL,
    # Review statuses
    VALID_REVIEW_STATUSES,
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_AUTO_APPROVED,
    REVIEW_STATUS_REVIEWED,
    REVIEW_STATUS_REJECTED,
    # Statuses
    VALID_STATUSES,
    STATUS_DRAFT,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    # Review actions
    VALID_REVIEW_ACTIONS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_SWITCH,
    # Pagination
    DEFAULT_LIMIT,
    MAX_LIMIT,
    # Batch generation
    MAX_BATCH_DAYS,
    DEFAULT_BATCH_DAYS,
)

__all__ = [
    # Service
    "ThemesService",
    # Categories
    "VALID_CATEGORIES",
    "CATEGORY_HOLIDAY",
    "CATEGORY_MEMORIAL",
    "CATEGORY_HISTORICAL",
    "CATEGORY_NOTABLE",
    "CATEGORY_CAMPAIGN",
    "CATEGORY_SPECIAL",
    # Review statuses
    "VALID_REVIEW_STATUSES",
    "REVIEW_STATUS_PENDING",
    "REVIEW_STATUS_AUTO_APPROVED",
    "REVIEW_STATUS_REVIEWED",
    "REVIEW_STATUS_REJECTED",
    # Statuses
    "VALID_STATUSES",
    "STATUS_DRAFT",
    "STATUS_ACTIVE",
    "STATUS_ARCHIVED",
    # Review actions
    "VALID_REVIEW_ACTIONS",
    "REVIEW_ACTION_APPROVE",
    "REVIEW_ACTION_REJECT",
    "REVIEW_ACTION_SWITCH",
    # Pagination
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    # Batch generation
    "MAX_BATCH_DAYS",
    "DEFAULT_BATCH_DAYS",
]
