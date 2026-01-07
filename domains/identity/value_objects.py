"""
Identity Value Objects - Immutable domain primitives.

@module domains.identity.value_objects
@version 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class UserTier(str, Enum):
    """User subscription tier."""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"

    @property
    def display_name(self) -> str:
        """Human-readable tier name."""
        return self.value.capitalize()

    @property
    def monthly_credits(self) -> int:
        """Monthly credit allowance for this tier."""
        allowances = {
            UserTier.FREE: 0,
            UserTier.STARTER: 500,
            UserTier.PRO: 1000,
        }
        return allowances[self]

    @property
    def price_monthly(self) -> float:
        """Monthly price in USD."""
        prices = {
            UserTier.FREE: 0.0,
            UserTier.STARTER: 14.9,
            UserTier.PRO: 29.9,
        }
        return prices[self]

    def has_feature(self, feature: str) -> bool:
        """Check if tier has access to a feature."""
        features = {
            UserTier.FREE: {"basic_editor", "export_png"},
            UserTier.STARTER: {"basic_editor", "export_png", "sticker_library", "publish_asset"},
            UserTier.PRO: {"basic_editor", "export_png", "sticker_library", "publish_asset",
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


@dataclass(frozen=True)
class UserId:
    """
    User identifier value object.

    Wraps the Clerk user ID for type safety.
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
