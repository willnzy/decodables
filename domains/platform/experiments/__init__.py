"""
Experiments Service Package

Modular A/B testing experiment service.

@package services.experiments
@version 3.29

Changes in v3.29:
- Added ExperimentService class for DDD architecture
- API layer now uses Depends(get_experiment_service) for dependency injection
- CRUD operations migrated to Service layer
- Legacy module functions kept for analysis/tracking (not yet migrated)
Changes in v3.27:
- Fixed assignment.py: status enum ('active' not 'running') + user_id field fixes
- Fixed tracking.py: user_id field + added missing tables to schema
"""

from .core import supabase, logger, CACHE_TTL
from .service import ExperimentService  # v3.29: DDD Service
from .crud import (
    create_experiment,
    get_experiment,
    get_experiment_by_id,
    list_experiments,
    update_experiment,
    update_experiment_status,
    delete_experiment,
    get_active_experiments,
)
from .assignment import (
    assign_variant,
    get_user_variant,
    get_user_experiments,
)
from .tracking import (
    track_exposure,
    track_conversion,
)
from .analysis import (
    aggregate_experiment_results,
    get_experiment_results,
    calculate_statistical_significance,
)
from .trend import (
    get_daily_trend,
    get_hourly_trend,
)
from .utils import (
    clear_experiment_cache,
)

__all__ = [
    # Core
    'supabase', 'logger',
    # Service (v3.29: DDD)
    'ExperimentService',
    # CRUD (legacy module functions)
    'create_experiment', 'get_experiment', 'get_experiment_by_id',
    'list_experiments', 'update_experiment', 'update_experiment_status',
    'delete_experiment', 'get_active_experiments',
    # Assignment
    'assign_variant', 'get_user_variant', 'get_user_experiments',
    # Tracking
    'track_exposure', 'track_conversion',
    # Analysis
    'aggregate_experiment_results', 'get_experiment_results',
    'calculate_statistical_significance',
    # Trend
    'get_daily_trend', 'get_hourly_trend',
    # Utils
    'clear_experiment_cache',
]
