"""
Database Service - Backward Compatibility Layer

This module re-exports all database operations from the new modular
structure in services/db/ for backward compatibility.

For new code, prefer importing directly from services.db:
    from services.db import get_user_profile, credit_deduct

@module services.db_service
@version 3.24
@deprecated Use services.db directly for new code
"""

# Re-export everything from the db package
from .db import *

# Additional backward-compatible aliases (commented out - functions already in services/db/__init__.py)
# from .db.users import (
#     update_user_profile as update_profile,
# )
# from .db.assets import (
#     get_deleted_assets as get_user_deleted_assets,
#     get_deleted_assets,  # Keep original name for backward compatibility
# )
# from .db.payments import (
#     admin_get_revenue_stats as admin_get_revenue_stats,
# )

# Legacy function names (if any were renamed)
deduct_credits_atomic = credit_deduct
