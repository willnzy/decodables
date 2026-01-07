"""
API Layer - FastAPI routers using new DDD architecture.

This module provides routers that use the new command/query handlers
from the container. These routers use clean architecture pattern.

@package api
@version 1.0.0

Endpoints:
- /api/v2/billing/* - Billing/credit management
- /api/v2/credits/* - User-facing credits API
- /api/v2/user/* - User profile management
- /api/v2/projects/* - Project management
- /api/v2/marketplace/* - Marketplace listings and purchases
- /api/v2/platform/* - Feature flags and experiments
"""

from fastapi import APIRouter

# Import all routers
from .billing_api import router as billing_router
from .credits_api import router as credits_router
from .user_api import router as user_router
from .projects_api import router as projects_router
from .marketplace_api import router as marketplace_router
from .platform_api import router as platform_router

# Create main API router
api_router = APIRouter()

# Include all domain routers
api_router.include_router(billing_router)
api_router.include_router(credits_router)
api_router.include_router(user_router)
api_router.include_router(projects_router)
api_router.include_router(marketplace_router)
api_router.include_router(platform_router)

__all__ = [
    'api_router',
    'billing_router',
    'credits_router',
    'user_router',
    'projects_router',
    'marketplace_router',
    'platform_router',
]
