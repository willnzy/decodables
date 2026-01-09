"""
Identity Domain - User profiles and authentication.

This domain handles:
- User profile management
- User preferences and settings
- Subscription tier information
- Onboarding progress tracking

@package domains.identity
@version 1.0.0

Note: Authentication itself is handled by Clerk (external service).
This domain focuses on user data management within our system.
"""

from .value_objects import (
    UserId,
    UserTier,
    OnboardingStep,
    UserPreferences,
)
from .aggregates.user_profile import UserProfile
from .exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
    InvalidUserDataException,
)
from .repository import IUserRepository
from .service import IdentityService
from .constants import (
    TIER_T1,
    TIER_T2,
    TIER_T3,
    VALID_TIERS,
    TIER_LABELS,
    TIER_MONTHLY_CREDITS,
    TIER_LEVELS,
    DEFAULT_TIER_DISPLAY_NAMES,
    TIER_MONTHLY_PRICES,
    is_valid_tier,
    get_tier_level,
    compare_tiers,
    is_premium_tier,
)

__all__ = [
    # Value Objects
    'UserId',
    'UserTier',
    'OnboardingStep',
    'UserPreferences',
    # Aggregates
    'UserProfile',
    # Exceptions
    'UserNotFoundException',
    'UserAlreadyExistsException',
    'InvalidUserDataException',
    # Repository
    'IUserRepository',
    # Service
    'IdentityService',
    # Constants
    'TIER_T1',
    'TIER_T2',
    'TIER_T3',
    'VALID_TIERS',
    'TIER_LABELS',
    'TIER_MONTHLY_CREDITS',
    'TIER_LEVELS',
    'DEFAULT_TIER_DISPLAY_NAMES',
    'TIER_MONTHLY_PRICES',
    'is_valid_tier',
    'get_tier_level',
    'compare_tiers',
    'is_premium_tier',
]
