"""
Experiments Tracking - Exposure and conversion tracking

@module services.experiments.tracking
@version 3.25

Changes in v3.25:
- Fixed field name: user_identifier → user_id (aligned with database schema)
- Added missing experiment_exposures and experiment_conversions tables to schema
- Fixed query: use experiment_id instead of experiment_key in exposures table
"""

from typing import Optional, Dict
from datetime import datetime, timezone

from .core import supabase, logger
from .crud import get_experiment


def track_exposure(
    experiment_key: str,
    user_identifier: str,
    variant_key: str,
    context: Dict = None
) -> bool:
    """
    Track experiment exposure.

    Args:
        experiment_key: Experiment identifier
        user_identifier: User ID
        variant_key: Assigned variant
        context: Additional context (page, etc.)

    Returns:
        Success status
    """
    if not supabase:
        return False

    experiment = get_experiment(experiment_key)
    if not experiment:
        return False

    try:
        # Check for recent exposure to avoid duplicates
        recent = supabase.table("experiment_exposures").select("id")\
            .eq("experiment_id", experiment.get('id'))\
            .eq("user_id", user_identifier)\
            .gte("created_at", _get_dedup_cutoff()).execute()

        if recent.data:
            # Already tracked recently
            return True

        supabase.table("experiment_exposures").insert({
            "experiment_id": experiment.get('id'),
            "user_id": user_identifier,
            "variant_key": variant_key,
            "context": context or {},
        }).execute()

        return True

    except Exception as e:
        logger.error(f"[Tracking] Failed to track exposure: {e}")
        return False


def track_conversion(
    experiment_key: str,
    user_identifier: str,
    metric_key: str,
    value: float = 1.0,
    metadata: Dict = None
) -> bool:
    """
    Track experiment conversion.

    Args:
        experiment_key: Experiment identifier
        user_identifier: User ID
        metric_key: Metric being tracked (e.g., 'signup', 'purchase')
        value: Metric value (e.g., revenue amount)
        metadata: Additional metadata

    Returns:
        Success status
    """
    if not supabase:
        return False

    experiment = get_experiment(experiment_key)
    if not experiment:
        return False

    # Get user's variant
    try:
        # EXP-HIGH-7 FIX: Database field is 'user_id', not 'user_identifier'
        # Need to join with experiments table to filter by experiment_key
        assignment = supabase.table("experiment_assignments").select(
            "variant_key, experiments!inner(experiment_key)"
        ).eq("experiments.experiment_key", experiment_key).eq(
            "user_id", user_identifier
        ).execute()

        if not assignment.data:
            logger.warning(f"[Tracking] No assignment found for conversion")
            return False

        variant_key = assignment.data[0].get('variant_key')

        supabase.table("experiment_conversions").insert({
            "experiment_id": experiment.get('id'),
            "user_id": user_identifier,
            "variant_key": variant_key,
            "metric_key": metric_key,
            "value": value,
            "metadata": metadata or {},
        }).execute()

        return True

    except Exception as e:
        logger.error(f"[Tracking] Failed to track conversion: {e}")
        return False


def _get_dedup_cutoff() -> str:
    """Get cutoff time for deduplication (1 hour ago)."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    return cutoff.isoformat()
