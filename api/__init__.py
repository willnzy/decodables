"""
API Layer - FastAPI routers using new DDD architecture.

This module provides routers that use the new command/query handlers
from the container. These routers demonstrate the clean architecture
pattern and can be used alongside existing routers during migration.

@package api
@version 1.0.0

Migration Strategy:
- Existing routers in /routers/ continue to work
- New routers in /api/ use container + handlers
- Gradually migrate endpoints as needed

Endpoints:
- /api/v2/billing/* - Billing/credit management
- /api/v2/credits/* - User-facing credits API
- /api/v2/user/* - User profile management
- /api/v2/projects/* - Project management
"""

from fastapi import APIRouter

# Import new routers
from .billing_api import router as billing_router
from .credits_api import router as credits_router
from .user_api import router as user_router
from .projects_api import router as projects_router

# Create main API router
api_router = APIRouter()

# Include domain routers
api_router.include_router(billing_router)
api_router.include_router(credits_router)
api_router.include_router(user_router)
api_router.include_router(projects_router)

__all__ = [
    'api_router',
    'billing_router',
    'credits_router',
    'user_router',
    'projects_router',
]
