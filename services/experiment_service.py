"""
Experiment Service - Backward Compatibility Layer

This module re-exports all experiment operations from the new modular
structure in services/experiments/ for backward compatibility.

For new code, prefer importing directly from services.experiments:
    from services.experiments import create_experiment, assign_variant

@module services.experiment_service
@version 3.24
@deprecated Use services.experiments directly for new code
"""

# Re-export everything from the experiments package
from .experiments import *
