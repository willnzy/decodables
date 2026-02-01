"""
Experiments CRUD - Create, Read, Update, Delete operations

@module services.experiments.crud
@version 3.30 (WS-13 Async Migration)

Changes in v3.30 (WS-13):
- Converted all functions from sync to async
- Removed asyncio.run() anti-pattern (ASYNC-03)
- Callers must now use `await` when calling these functions

Changes in v3.28:
- Complete DDD Migration to Repository pattern (EXP-CRITICAL-1)
- All database access through infrastructure/repositories/experiment_repository.py
"""

import logging

from core.database import get_async_db_client
from typing import Optional, Dict, List, Tuple

# v3.28: DDD Migration - Use Repository only
from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository

logger = logging.getLogger(__name__)


async def _get_repo() -> SupabaseExperimentRepository:
    """Get experiment repository instance."""
    db_client = await get_async_db_client()
    return SupabaseExperimentRepository(client=db_client)


async def list_experiments(
    status: str = None,
    experiment_type: str = None,
    offset: int = 0,
    limit: int = 20
) -> Tuple[List[Dict], int]:
    """
    List experiments with filters.

    v3.30: WS-13 — Converted to native async (removed asyncio.run).

    Args:
        status: Filter by experiment status
        experiment_type: Filter by experiment type
        offset: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        Tuple of (experiments list, total count)
    """
    try:
        repo = await _get_repo()
        return await repo.list_experiments(
            status=status,
            experiment_type=experiment_type,
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.error(f"[Experiment] Failed to list: {e}")
        return ([], 0)


async def get_experiment(experiment_key: str, use_cache: bool = True) -> Optional[Dict]:
    """
    Get experiment by key.

    v3.30: WS-13 — Converted to native async (removed asyncio.run).

    Args:
        experiment_key: Experiment identifier
        use_cache: Ignored (kept for API compatibility)

    Returns:
        Experiment dict or None
    """
    try:
        repo = await _get_repo()
        return await repo.get_by_key(experiment_key)
    except Exception as e:
        logger.error(f"[Experiment] Failed to get {experiment_key}: {e}")
        return None


async def get_experiment_by_id(experiment_id: str) -> Optional[Dict]:
    """Get experiment by ID (deprecated)."""
    logger.warning("[Experiment] get_experiment_by_id is deprecated, use get_experiment with key")
    return None


async def get_active_experiments() -> List[Dict]:
    """
    Get all active (running) experiments.

    Returns:
        List of running experiments
    """
    try:
        exps, _ = await list_experiments(status="running", limit=1000)
        return exps
    except Exception as e:
        logger.error(f"[Experiment] Failed to get active: {e}")
        return []


# ==========================================
# Experiment Management Functions
# ==========================================

async def delete_experiment(experiment_key: str) -> bool:
    """
    Delete experiment.

    v3.30: WS-13 — Converted to native async (removed asyncio.run).

    Args:
        experiment_key: Experiment identifier

    Returns:
        True if deleted successfully
    """
    try:
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
    except Exception as e:
        logger.error(f"[Experiment] Failed to delete {experiment_key}: {e}")
        return False
