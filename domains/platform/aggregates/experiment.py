"""
Experiment Aggregate - Encapsulates A/B experiment management.

@module domains.platform.aggregates.experiment
@version 1.0.0

This is the aggregate root for A/B experiment management.
All experiment operations must go through this aggregate.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from ..value_objects import (
    ExperimentId,
    ExperimentStatus,
    ExperimentVariant,
    TargetingRule,
)


@dataclass
class Experiment:
    """
    Aggregate root for A/B experiment management.

    Encapsulates:
    - Experiment configuration
    - Variant definitions
    - User assignment logic
    - Results tracking
    """
    experiment_id: str
    name: str
    description: Optional[str] = None
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: List[ExperimentVariant] = field(default_factory=list)
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_new(
        cls,
        name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> "Experiment":
        """
        Factory method to create a new experiment.

        Args:
            name: Experiment name
            description: Optional description
            created_by: User who created the experiment

        Returns:
            New Experiment instance with default control/treatment variants
        """
        experiment_id = ExperimentId.generate()

        experiment = cls(
            experiment_id=str(experiment_id),
            name=name,
            description=description,
            created_by=created_by,
            status=ExperimentStatus.DRAFT,
        )

        # Add default variants
        experiment.add_variant("control", "Control", weight=50)
        experiment.add_variant("treatment", "Treatment", weight=50)

        return experiment

    @property
    def is_running(self) -> bool:
        """Check if experiment is running."""
        return self.status == ExperimentStatus.RUNNING

    @property
    def is_active(self) -> bool:
        """Check if experiment is actively running."""
        if not self.is_running:
            return False

        now = datetime.now(timezone.utc)
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    @property
    def total_weight(self) -> int:
        """Get total weight of all variants."""
        return sum(v.weight for v in self.variants)

    def add_variant(
        self,
        variant_id: str,
        name: str,
        weight: int = 50,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Add a variant to the experiment.

        Args:
            variant_id: Unique variant identifier
            name: Variant name
            weight: Weight for assignment (percentage)
            config: Variant-specific configuration
        """
        variant = ExperimentVariant(
            variant_id=variant_id,
            name=name,
            weight=weight,
            config=config or {},
        )
        self.variants.append(variant)
        self.updated_at = datetime.now(timezone.utc)

    def remove_variant(self, variant_id: str):
        """Remove a variant by ID."""
        self.variants = [v for v in self.variants if v.variant_id != variant_id]
        self.updated_at = datetime.now(timezone.utc)

    def update_variant_weight(self, variant_id: str, weight: int):
        """Update variant weight."""
        for variant in self.variants:
            if variant.variant_id == variant_id:
                variant.weight = weight
                self.updated_at = datetime.now(timezone.utc)
                return
        raise ValueError(f"Variant not found: {variant_id}")

    def assign_variant(
        self,
        user_id: str,
        user_tier: Optional[str] = None
    ) -> Optional[ExperimentVariant]:
        """
        Assign a variant to a user.

        Uses deterministic hashing for consistent assignment.

        Args:
            user_id: User ID
            user_tier: User's subscription tier

        Returns:
            Assigned variant or None if not eligible
        """
        if not self.is_active:
            return None

        # Check targeting rules
        is_targeted = len(self.targeting_rules) == 0  # No rules = target all
        for rule in self.targeting_rules:
            if rule.matches(user_id=user_id, user_tier=user_tier):
                is_targeted = True
                break

        if not is_targeted:
            return None

        # Deterministic assignment based on user_id and experiment_id
        hash_input = f"{user_id}:{self.experiment_id}"
        hash_value = hash(hash_input) % 100

        # Assign based on weights
        cumulative = 0
        for variant in self.variants:
            cumulative += variant.weight
            if hash_value < cumulative:
                return variant

        # Fallback to first variant
        return self.variants[0] if self.variants else None

    def start(self):
        """Start the experiment."""
        if not self.variants:
            raise ValueError("Cannot start experiment without variants")
        if self.total_weight != 100:
            raise ValueError(f"Variant weights must sum to 100, got {self.total_weight}")

        self.status = ExperimentStatus.RUNNING
        self.start_date = self.start_date or datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def pause(self):
        """Pause the experiment."""
        if self.status != ExperimentStatus.RUNNING:
            raise ValueError("Can only pause running experiments")

        self.status = ExperimentStatus.PAUSED
        self.updated_at = datetime.now(timezone.utc)

    def resume(self):
        """Resume paused experiment."""
        if self.status != ExperimentStatus.PAUSED:
            raise ValueError("Can only resume paused experiments")

        self.status = ExperimentStatus.RUNNING
        self.updated_at = datetime.now(timezone.utc)

    def complete(self):
        """Complete the experiment."""
        self.status = ExperimentStatus.COMPLETED
        self.end_date = self.end_date or datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def archive(self):
        """Archive the experiment."""
        self.status = ExperimentStatus.ARCHIVED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "is_active": self.is_active,
            "variants": [v.to_dict() for v in self.variants],
            "targeting_rules": [r.to_dict() for r in self.targeting_rules],
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
