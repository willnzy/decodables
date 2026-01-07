"""
Platform Value Objects - Immutable domain primitives.

@module domains.platform.value_objects
@version 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, date
import uuid


class FlagStatus(str, Enum):
    """Feature flag lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

    @property
    def is_evaluable(self) -> bool:
        """Check if flag can be evaluated."""
        return self in (FlagStatus.ACTIVE, FlagStatus.DEPRECATED)


class ExperimentStatus(str, Enum):
    """A/B experiment lifecycle status."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    @property
    def is_active(self) -> bool:
        """Check if experiment is actively running."""
        return self == ExperimentStatus.RUNNING


class TargetType(str, Enum):
    """Targeting rule types."""
    ALL_USERS = "all_users"
    USER_IDS = "user_ids"
    USER_TIERS = "user_tiers"
    PERCENTAGE = "percentage"
    DATE_RANGE = "date_range"
    CUSTOM = "custom"


@dataclass(frozen=True)
class FeatureFlagId:
    """
    Feature flag identifier value object.

    Uses string key format for easy reference in code.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Feature flag ID cannot be empty")
        if not self.value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Feature flag ID must be alphanumeric with underscores/hyphens")

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, FeatureFlagId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class ExperimentId:
    """
    Experiment identifier value object.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Experiment ID cannot be empty")

    @classmethod
    def generate(cls) -> "ExperimentId":
        """Generate a new experiment ID."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, ExperimentId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass
class TargetingRule:
    """
    Targeting rule for feature flags and experiments.

    Determines which users see a feature.
    """
    rule_type: TargetType
    enabled: bool = True
    user_ids: List[str] = field(default_factory=list)
    user_tiers: List[str] = field(default_factory=list)
    percentage: int = 0  # 0-100
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    custom_rules: Dict[str, Any] = field(default_factory=dict)

    def matches(
        self,
        user_id: Optional[str] = None,
        user_tier: Optional[str] = None,
        evaluation_time: Optional[datetime] = None
    ) -> bool:
        """
        Check if user matches this targeting rule.

        Args:
            user_id: User ID to check
            user_tier: User's subscription tier
            evaluation_time: Time of evaluation

        Returns:
            True if user matches
        """
        if not self.enabled:
            return False

        if self.rule_type == TargetType.ALL_USERS:
            return True

        if self.rule_type == TargetType.USER_IDS:
            return user_id in self.user_ids

        if self.rule_type == TargetType.USER_TIERS:
            return user_tier in self.user_tiers

        if self.rule_type == TargetType.PERCENTAGE:
            if not user_id:
                return False
            # Deterministic hash-based percentage
            hash_val = hash(user_id) % 100
            return hash_val < self.percentage

        if self.rule_type == TargetType.DATE_RANGE:
            now = evaluation_time or datetime.utcnow()
            if self.start_date and now < self.start_date:
                return False
            if self.end_date and now > self.end_date:
                return False
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_type": self.rule_type.value,
            "enabled": self.enabled,
            "user_ids": self.user_ids,
            "user_tiers": self.user_tiers,
            "percentage": self.percentage,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "custom_rules": self.custom_rules,
        }


@dataclass
class ThemeConfig:
    """
    Daily Doodle / Theme configuration.
    """
    theme_id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    assets: List[Dict[str, Any]] = field(default_factory=list)
    schedule_date: Optional[date] = None
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "theme_id": self.theme_id,
            "name": self.name,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "assets": self.assets,
            "schedule_date": self.schedule_date.isoformat() if self.schedule_date else None,
            "is_active": self.is_active,
        }


@dataclass
class ExperimentVariant:
    """
    A/B experiment variant configuration.
    """
    variant_id: str
    name: str
    weight: int = 50  # Percentage allocation
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "weight": self.weight,
            "config": self.config,
        }
