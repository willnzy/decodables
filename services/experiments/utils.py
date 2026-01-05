"""
Experiments Utils - Utility functions

@module services.experiments.utils
@version 3.24
"""

from .core import invalidate_cache, logger


def clear_experiment_cache():
    """Clear all experiment cache."""
    invalidate_cache()
    logger.info("[Experiment] Cache cleared")
    return True
