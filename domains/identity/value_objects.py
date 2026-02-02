"""
Identity Value Objects - Immutable domain primitives.

@module domains.identity.value_objects
@version 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class UserRole(str, Enum):
    """
    User role for access control.

    - user: Regular user (default)
    - admin: Administrator with full access
    """
    USER = "user"
    ADMIN = "admin"


class UserTier(str, Enum):
    """
    User subscription tier.

    System codes (永不改变):
    - t1: First Tier (Free Plan)
    - t2: Second Tier (Starter Plan)
    - t3: Third Tier (Pro Plan)

    Display names are configurable via system_configs.
    """
    T1 = "t1"  # First Tier (Free Plan)
    T2 = "t2"  # Second Tier (Starter Plan)
    T3 = "t3"  # Third Tier (Pro Plan)

    # Backward compatibility aliases (deprecated)
    FREE = "t1"
    STARTER = "t2"
    PRO = "t3"

    @property
    def display_name(self) -> str:
        """
        Human-readable tier name (fixed label).

        Note: User-facing display names should come from system_configs
        via TierService.get_tier_display_name()
        """
        labels = {
            "t1": "First Tier",
            "t2": "Second Tier",
            "t3": "Third Tier",
        }
        return labels.get(self.value, self.value.upper())

    @property
    def monthly_credits(self) -> int:
        """Monthly credit allowance for this tier (fallback, use TierService for dynamic config)."""
        allowances = {
            UserTier.T1: 0,
            UserTier.T2: 100,  # database: tier.t2.monthly_credits
            UserTier.T3: 200,  # database: tier.t3.monthly_credits
        }
        return allowances[self]

    @property
    def price_monthly(self) -> float:
        """Monthly price in USD (original price)."""
        prices = {
            UserTier.T1: 0.0,
            UserTier.T2: 14.9,
            UserTier.T3: 29.9,
        }
        return prices[self]

    def has_feature(self, feature: str) -> bool:
        """Check if tier has access to a feature."""
        features = {
            UserTier.T1: {"basic_editor", "export_png"},
            UserTier.T2: {"basic_editor", "export_png", "sticker_library", "publish_asset"},
            UserTier.T3: {"basic_editor", "export_png", "sticker_library", "publish_asset",
                          "commercial_license", "priority_support", "advanced_ai"},
        }
        return feature in features.get(self, set())


class OnboardingStep(str, Enum):
    """Onboarding progress steps."""
    NOT_STARTED = "not_started"
    PROFILE_SETUP = "profile_setup"
    FIRST_PROJECT = "first_project"
    EXPLORE_FEATURES = "explore_features"
    COMPLETED = "completed"

    @property
    def order(self) -> int:
        """Step order for progress tracking."""
        orders = {
            OnboardingStep.NOT_STARTED: 0,
            OnboardingStep.PROFILE_SETUP: 1,
            OnboardingStep.FIRST_PROJECT: 2,
            OnboardingStep.EXPLORE_FEATURES: 3,
            OnboardingStep.COMPLETED: 4,
        }
        return orders[self]

    def is_after(self, other: "OnboardingStep") -> bool:
        """Check if this step comes after another."""
        return self.order > other.order


class SubscriptionStatus(str, Enum):
    """Subscription status values.

    SYNC: Must match 01_core_business.sql profiles.subscription_status CHECK constraint:
    CHECK (subscription_status IN ('active', 'canceled', 'past_due', 'incomplete', 'trialing', 'inactive'))
    """
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class UserId:
    """
    User identifier value object.

    Wraps the user ID for type safety.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("User ID cannot be empty")
        if not self.value.startswith("user_"):
            raise ValueError("Invalid user ID format (must start with 'user_')")

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, UserId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class UserPreferences:
    """
    User preferences value object.

    Stores user-configurable settings.
    """
    language: str = "en"
    theme: str = "light"
    email_notifications: bool = True
    marketing_emails: bool = False
    default_canvas_size: str = "1080x1080"
    auto_save_enabled: bool = True
    tutorial_completed: bool = False

    def with_language(self, language: str) -> "UserPreferences":
        """Return new preferences with updated language."""
        return UserPreferences(
            language=language,
            theme=self.theme,
            email_notifications=self.email_notifications,
            marketing_emails=self.marketing_emails,
            default_canvas_size=self.default_canvas_size,
            auto_save_enabled=self.auto_save_enabled,
            tutorial_completed=self.tutorial_completed,
        )

    def with_theme(self, theme: str) -> "UserPreferences":
        """Return new preferences with updated theme."""
        return UserPreferences(
            language=self.language,
            theme=theme,
            email_notifications=self.email_notifications,
            marketing_emails=self.marketing_emails,
            default_canvas_size=self.default_canvas_size,
            auto_save_enabled=self.auto_save_enabled,
            tutorial_completed=self.tutorial_completed,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return {
            "language": self.language,
            "theme": self.theme,
            "email_notifications": self.email_notifications,
            "marketing_emails": self.marketing_emails,
            "default_canvas_size": self.default_canvas_size,
            "auto_save_enabled": self.auto_save_enabled,
            "tutorial_completed": self.tutorial_completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        """Create from dictionary."""
        return cls(
            language=data.get("language", "en"),
            theme=data.get("theme", "light"),
            email_notifications=data.get("email_notifications", True),
            marketing_emails=data.get("marketing_emails", False),
            default_canvas_size=data.get("default_canvas_size", "1080x1080"),
            auto_save_enabled=data.get("auto_save_enabled", True),
            tutorial_completed=data.get("tutorial_completed", False),
        )
