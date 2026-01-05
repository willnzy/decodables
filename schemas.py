"""
Pydantic Schemas (Backward Compatibility)

This file re-exports all schemas from the new schemas/ package.
Import from `schemas` package directly for new code.

@deprecated Use `from schemas import X` instead
@module schemas
"""

# Re-export everything from schemas package
from schemas import *  # noqa: F401, F403
