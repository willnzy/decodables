"""Themes Domain Constants.

@module domains.themes.constants
@version 2.1.0

All constants for the themes domain, including categories, statuses,
and validation limits.
"""

from typing import List

# ==========================================
# Theme Categories
# ==========================================

CATEGORY_HOLIDAY = "holiday"
CATEGORY_MEMORIAL = "memorial"
CATEGORY_HISTORICAL = "historical"
CATEGORY_NOTABLE = "notable"
CATEGORY_CAMPAIGN = "campaign"
CATEGORY_SPECIAL = "special"

VALID_CATEGORIES: List[str] = [
    CATEGORY_HOLIDAY,
    CATEGORY_MEMORIAL,
    CATEGORY_HISTORICAL,
    CATEGORY_NOTABLE,
    CATEGORY_CAMPAIGN,
    CATEGORY_SPECIAL,
]

# ==========================================
# Review Statuses (v2.1)
# ==========================================

REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_AUTO_APPROVED = "auto_approved"
REVIEW_STATUS_REVIEWED = "reviewed"
REVIEW_STATUS_REJECTED = "rejected"

VALID_REVIEW_STATUSES: List[str] = [
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_AUTO_APPROVED,
    REVIEW_STATUS_REVIEWED,
    REVIEW_STATUS_REJECTED,
]

# ==========================================
# Theme Statuses
# ==========================================

STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_ARCHIVED = "archived"

VALID_STATUSES: List[str] = [
    STATUS_DRAFT,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
]

# ==========================================
# Pagination Defaults
# ==========================================

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
DEFAULT_OFFSET = 0

# ==========================================
# Batch Generation Limits (v2.1)
# ==========================================

MAX_BATCH_DAYS = 365
DEFAULT_BATCH_DAYS = 300
MIN_BATCH_DAYS = 1

# AI alternatives per theme
AI_ALTERNATIVES_COUNT = 3

# ==========================================
# Field Length Limits
# ==========================================

NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 100
SLOGAN_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 1000
REVIEW_NOTES_MAX_LENGTH = 500
SOURCE_URL_MAX_LENGTH = 500
LEARN_MORE_URL_MAX_LENGTH = 500

# ==========================================
# Priority Defaults
# ==========================================

PRIORITY_MIN = 0
PRIORITY_MAX = 100
PRIORITY_DEFAULT = 50

# Priority guidelines by category
PRIORITY_HOLIDAY_HIGH = 95  # Major holidays (Christmas, New Year)
PRIORITY_HOLIDAY_MEDIUM = 70  # Regional holidays (Thanksgiving)
PRIORITY_MEMORIAL = 75  # Memorial days (MLK Day, Earth Day)
PRIORITY_NOTABLE = 55  # Notable days (Pi Day)
PRIORITY_CAMPAIGN = 60  # Marketing campaigns
PRIORITY_SPECIAL = 50  # Special occasions

# ==========================================
# Review Actions (v2.1)
# ==========================================

REVIEW_ACTION_APPROVE = "approve"
REVIEW_ACTION_REJECT = "reject"
REVIEW_ACTION_SWITCH = "switch"

VALID_REVIEW_ACTIONS: List[str] = [
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_SWITCH,
]
