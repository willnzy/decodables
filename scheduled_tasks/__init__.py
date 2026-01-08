"""
DEPRECATED: scheduled_tasks package has been refactored to DDD layers.

This module provides backward compatibility.
Please update your imports to use the new locations:

- scheduled_tasks.metrics_etl -> application.services.metrics
- scheduled_tasks.aggregate_stats -> application.services.aggregators
- scheduled_tasks.experiment_aggregator -> application.services.experiments
- scheduled_tasks.storage_cleanup -> infrastructure.tasks.storage_cleanup
- scheduled_tasks.task_logger -> infrastructure.logging.task_logger
- scheduled_tasks.campaign_scheduler -> application.services.campaigns
"""

import warnings

warnings.warn(
    "The 'scheduled_tasks' package is deprecated. "
    "Use 'application.services' or 'infrastructure' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
from application.services.metrics import run_hourly_etl, run_daily_etl
from application.services.aggregators import run_hourly_tasks, run_daily_tasks
from application.services.experiments import (
    run_hourly_experiment_tasks,
    run_daily_experiment_tasks,
)
from infrastructure.tasks.storage_cleanup import run_storage_cleanup
from infrastructure.logging.task_logger import TaskLogger, task_context, log_task_run
