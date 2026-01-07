"""
FeatureFlag Aggregate - Encapsulates feature flag management.

@module domains.platform.aggregates.feature_flag
@version 1.0.0

This is the aggregate root for feature flag management.
All feature flag operations must go through this aggregate.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..value_objects import (
    FeatureFlagId,
    FlagStatus,
    TargetingRule,
    TargetType,
)


@dataclass
class FeatureFlag:
    """
    Aggregate root for feature flag management.

    Encapsulates:
    - Flag configuration
    - Targeting rules
    - Evaluation logic
    """
    key: str
    name: str
    description: Optional[str] = None
    status: FlagStatus = FlagStatus.DRAFT
    default_value: bool = False
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_new(
        cls,
        key: str,
        name: str,
        description: Optional[str] = None,
        default_value: bool = False,
        created_by: Optional[str] = None
    ) -> "FeatureFlag":
        """
        Factory method to create a new feature flag.

        Args:
            key: Unique flag key (e.g., "new_editor_v2")
            name: Human-readable name
            description: Optional description
            default_value: Default value when no rules match
            created_by: User who created the flag

        Returns:
            New FeatureFlag instance
        """
        # Validate key format
        FeatureFlagId(key)

        return cls(
            key=key,
            name=name,
            description=description,
            default_value=default_value,
            created_by=created_by,
            status=FlagStatus.DRAFT,
        )

    @property
    def is_active(self) -> bool:
        """Check if flag is active."""
        return self.status == FlagStatus.ACTIVE

    @property
    def is_evaluable(self) -> bool:
        """Check if flag can be evaluated."""
        return self.status.is_evaluable

    def evaluate(
        self,
        user_id: Optional[str] = None,
        user_tier: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Evaluate the feature flag for a user.

        Args:
            user_id: User ID
            user_tier: User's subscription tier
            context: Additional evaluation context

        Returns:
            True if feature is enabled for user
        """
        if not self.is_evaluable:
            return self.default_value

        # Evaluate targeting rules in order
        for rule in self.targeting_rules:
            if rule.matches(user_id=user_id, user_tier=user_tier):
                return True

        return self.default_value

    def add_targeting_rule(self, rule: TargetingRule):
        """Add a targeting rule."""
        self.targeting_rules.append(rule)
        self.updated_at = datetime.utcnow()

    def remove_targeting_rule(self, index: int):
        """Remove a targeting rule by index."""
        if 0 <= index < len(self.targeting_rules):
            self.targeting_rules.pop(index)
            self.updated_at = datetime.utcnow()

    def enable_for_users(self, user_ids: List[str]):
        """Enable flag for specific users."""
        rule = TargetingRule(
            rule_type=TargetType.USER_IDS,
            user_ids=user_ids,
            enabled=True,
        )
        self.add_targeting_rule(rule)

    def enable_for_tiers(self, tiers: List[str]):
        """Enable flag for specific subscription tiers."""
        rule = TargetingRule(
            rule_type=TargetType.USER_TIERS,
            user_tiers=tiers,
            enabled=True,
        )
        self.add_targeting_rule(rule)

    def enable_percentage(self, percentage: int):
        """Enable flag for a percentage of users."""
        rule = TargetingRule(
            rule_type=TargetType.PERCENTAGE,
            percentage=percentage,
            enabled=True,
        )
        self.add_targeting_rule(rule)

    def activate(self):
        """Activate the feature flag."""
        self.status = FlagStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def deprecate(self):
        """Mark flag as deprecated."""
        self.status = FlagStatus.DEPRECATED
        self.updated_at = datetime.utcnow()

    def archive(self):
        """Archive the feature flag."""
        self.status = FlagStatus.ARCHIVED
        self.updated_at = datetime.utcnow()

    def update_default(self, default_value: bool):
        """Update default value."""
        self.default_value = default_value
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "default_value": self.default_value,
            "targeting_rules": [r.to_dict() for r in self.targeting_rules],
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
