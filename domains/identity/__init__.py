"""
Identity Domain - User profiles and authentication.

This domain handles:
- User profile management
- User preferences and settings
- Subscription tier information
- Onboarding progress tracking

@package domains.identity
@version 1.0.0

Note: Authentication is handled by self-hosted auth (domains.auth module).
This domain focuses on user data management within our system.
"""

from .value_objects import (
    UserId,
    UserTier,
    OnboardingStep,
    SubscriptionStatus,
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
from .tier_service import TierService
from .trial_helper import is_user_in_trial, is_user_in_trial_async
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
    SIGNUP_BONUS_CREDITS,
    DEFAULT_TRIAL_DURATION_DAYS,
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
    'TierService',
    # Helpers
    'is_user_in_trial',
    'is_user_in_trial_async',
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
    'SIGNUP_BONUS_CREDITS',
    'DEFAULT_TRIAL_DURATION_DAYS',
    'is_valid_tier',
    'get_tier_level',
    'compare_tiers',
    'is_premium_tier',
]
