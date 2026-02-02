"""
UserProfile Aggregate - Encapsulates user identity and profile data.

@module domains.identity.aggregates.user_profile
@version 1.0.0

This is the aggregate root for user identity management.
All user profile operations must go through this aggregate.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..value_objects import UserTier, UserRole, OnboardingStep, UserPreferences


@dataclass
class UserProfile:
    """
    Aggregate root for user profile management.

    Encapsulates:
    - Basic user information
    - Subscription tier
    - Onboarding progress
    - User preferences
    """
    user_id: str
    email: str
    user_code: Optional[str] = None  # 26-digit unique user code
    
    # Profile fields
    username: Optional[str] = None       # Username
    first_name: Optional[str] = None     # User's first name
    last_name: Optional[str] = None      # User's last name
    
    # User-managed fields
    display_name: Optional[str] = None   # Display name (can be customized by user)
    avatar_url: Optional[str] = None
    
    # Role and subscription
    role: UserRole = UserRole.USER  # user or admin
    tier: UserTier = UserTier.T1
    subscription_status: Optional[str] = None  # active, canceled, past_due, incomplete, trialing
    stripe_customer_id: Optional[str] = None
    
    # Onboarding and preferences
    onboarding_step: OnboardingStep = OnboardingStep.NOT_STARTED
    preferences: UserPreferences = field(default_factory=UserPreferences)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_new(
        cls,
        user_id: str,
        email: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> "UserProfile":
        """
        Factory method to create a new user profile.

        Args:
            user_id: User ID (UUID string)
            email: User email
            username: Username
            first_name: User's first name
            last_name: User's last name
            avatar_url: Avatar URL
            display_name: Display name (defaults to username if not provided)

        Returns:
            New UserProfile instance
        """
        return cls(
            user_id=user_id,
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            display_name=display_name or username or first_name,
            tier=UserTier.T1,
            onboarding_step=OnboardingStep.NOT_STARTED,
            preferences=UserPreferences(),
        )

    @property
    def is_premium(self) -> bool:
        """Check if user has a paid subscription."""
        return self.tier in (UserTier.T2, UserTier.T3)

    @property
    def is_onboarding_complete(self) -> bool:
        """Check if user has completed onboarding."""
        return self.onboarding_step == OnboardingStep.COMPLETED

    @property
    def monthly_credit_allowance(self) -> int:
        """Get monthly credit allowance based on tier."""
        return self.tier.monthly_credits

    def has_feature(self, feature: str) -> bool:
        """Check if user has access to a feature."""
        return self.tier.has_feature(feature)

    def upgrade_tier(self, new_tier: UserTier, stripe_customer_id: Optional[str] = None):
        """
        Upgrade user's subscription tier.

        Args:
            new_tier: New subscription tier
            stripe_customer_id: Stripe customer ID if upgrading from free
        """
        if new_tier == self.tier:
            return

        self.tier = new_tier
        if stripe_customer_id:
            self.stripe_customer_id = stripe_customer_id
        self.updated_at = datetime.utcnow()

    def downgrade_tier(self, new_tier: UserTier):
        """
        Downgrade user's subscription tier.

        Args:
            new_tier: New subscription tier
        """
        self.tier = new_tier
        self.updated_at = datetime.utcnow()

    def advance_onboarding(self, to_step: OnboardingStep):
        """
        Advance onboarding to a specific step.

        Args:
            to_step: Step to advance to

        Raises:
            ValueError: If trying to go backwards
        """
        if not to_step.is_after(self.onboarding_step) and to_step != self.onboarding_step:
            if to_step != OnboardingStep.COMPLETED:
                raise ValueError(f"Cannot go backwards in onboarding from {self.onboarding_step} to {to_step}")

        self.onboarding_step = to_step
        self.updated_at = datetime.utcnow()

    def complete_onboarding(self):
        """Mark onboarding as complete."""
        self.onboarding_step = OnboardingStep.COMPLETED
        self.updated_at = datetime.utcnow()

    def update_preferences(self, preferences: UserPreferences):
        """
        Update user preferences.

        Args:
            preferences: New preferences
        """
        self.preferences = preferences
        self.updated_at = datetime.utcnow()

    def update_profile(
        self,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ):
        """
        Update basic profile information.

        Args:
            username: New username
            first_name: New first name
            last_name: New last name
            display_name: New display name
            avatar_url: New avatar URL
        """
        if username is not None:
            self.username = username
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if display_name is not None:
            self.display_name = display_name
        if avatar_url is not None:
            self.avatar_url = avatar_url
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "tier": self.tier.value,
            "tier_display": self.tier.display_name,
            "is_premium": self.is_premium,
            "onboarding_step": self.onboarding_step.value,
            "is_onboarding_complete": self.is_onboarding_complete,
            "preferences": self.preferences.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
