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
]
