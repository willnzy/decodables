"""
Experiments CRUD - Create, Read, Update, Delete operations

@module services.experiments.crud
@version 3.28 (DDD Compliant)

Changes in v3.28:
- Complete DDD Migration to Repository pattern (EXP-CRITICAL-1)
- All database access through infrastructure/repositories/experiment_repository.py
- Added @retry_on_network_error_async + OOM protection to all queries
- Removed direct Supabase access
- Removed legacy caching (can be re-implemented later if needed)
- Achieved 100% DDD architecture compliance

Changes in v3.25:
- Changed list_experiments to use offset instead of page (DDD standard)
"""

import asyncio
import logging

from core.database import get_async_db_client
from typing import Optional, Dict, List

# v3.28: DDD Migration - Use Repository only
from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository

logger = logging.getLogger(__name__)


async def _get_repo() -> SupabaseExperimentRepository:
    """
    Get experiment repository instance.

    v3.28: DDD Migration helper (EXP-CRITICAL-1).
    v3.29: Fixed to async function for AsyncClient.
    """
    db_client = await get_async_db_client()
    return SupabaseExperimentRepository(client=db_client)


def list_experiments(
    status: str = None,
    experiment_type: str = None,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[Dict], int]:
    """
    List experiments with filters.

    v3.28: DDD Migration - Uses Repository with retry + OOM protection.
    v3.29: Fixed async wrapper pattern.

    Args:
        status: Filter by experiment status
        experiment_type: Filter by experiment type
        offset: Number of items to skip (DDD standard pagination)
        limit: Maximum number of items to return

    Returns:
        Tuple of (experiments list, total count)
    """
    async def _async_list():
        repo = await _get_repo()
        return await repo.list_experiments(
            status=status,
            experiment_type=experiment_type,
            offset=offset,
            limit=limit
        )

    try:
        experiments, total = asyncio.run(_async_list())
        return (experiments, total)

    except Exception as e:
        logger.error(f"[Experiment] Failed to list: {e}")
        return ([], 0)


def get_experiment(experiment_key: str, use_cache: bool = True) -> Optional[Dict]:
    """
    Get experiment by key.

    v3.28: DDD Migration - Uses Repository. Cache removed for DDD compliance.
    v3.29: Fixed async wrapper pattern.

    Args:
        experiment_key: Experiment identifier
        use_cache: Ignored (kept for API compatibility)

    Returns:
        Experiment dict or None
    """
    async def _async_get():
        repo = await _get_repo()
        return await repo.get_by_key(experiment_key)

    try:
        experiment = asyncio.run(_async_get())
        return experiment

    except Exception as e:
        logger.error(f"[Experiment] Failed to get {experiment_key}: {e}")
        return None


def get_experiment_by_id(experiment_id: str) -> Optional[Dict]:
    """
    Get experiment by ID.

    v3.28: DDD Migration - Uses Repository.

    Args:
        experiment_id: Internal experiment ID

    Returns:
        Experiment dict or None (currently not fully implemented in Repository)
    """
    logger.warning(f"[Experiment] get_experiment_by_id is deprecated, use get_experiment with key")
    return None


def get_active_experiments() -> List[Dict]:
    """
    Get all active (running) experiments.

    v3.28: DDD Migration - Uses Repository with limit.
    v3.29: Simplified to use list_experiments (already has async wrapper).

    Returns:
        List of running experiments
    """
    try:
        # list_experiments already handles async properly
        exps, _ = list_experiments(status="running", limit=1000)
        return exps

    except Exception as e:
        logger.error(f"[Experiment] Failed to get active: {e}")
        return []


# ==========================================
# Experiment Management Functions
# ==========================================

def delete_experiment(experiment_key: str) -> bool:
    """
    Delete experiment.

    v3.28: Migrated to Repository pattern.
    v3.29: Fixed async wrapper pattern.

    Args:
        experiment_key: Experiment identifier

    Returns:
        True if deleted successfully
    """
    async def _async_delete():
        # First get the experiment to find its ID
        repo = await _get_repo()
        experiment = await repo.get_by_key(experiment_key)
        if not experiment:
            logger.error(f"[Experiment] Cannot delete {experiment_key}: not found")
            return False

        experiment_id = experiment.get("experiment_id") or experiment.get("id")
        if not experiment_id:
            logger.error(f"[Experiment] Cannot delete {experiment_key}: missing ID")
            return False

        return await repo.delete(experiment_id)

    try:
        success = asyncio.run(_async_delete())
        return success

    except Exception as e:
        logger.error(f"[Experiment] Failed to delete {experiment_key}: {e}")
        return False


