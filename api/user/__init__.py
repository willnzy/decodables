"""
User API Module - All user-facing v2 endpoints.

@module api.user
@version 1.0.0

This module contains all user-facing API endpoints organized by domain:
- billing: Credit management
- projects: Project CRUD operations
- marketplace: Asset listings and purchases
- generation: AI generation endpoints
- campaigns: Campaign management
- templates: Template library
- themes: Theme system
- config: User configuration
- support: Support and feedback
- webhooks: External webhooks (Clerk, Stripe)
- payment: Payment processing

All endpoints follow the pattern: /api/v2/user/{domain}/{endpoint}
"""

from fastapi import APIRouter

from .billing import router as billing_router
from .generation import router as generation_router
from .webhooks import router as webhooks_router
from .projects import router as projects_router
from .marketplace import router as marketplace_router
from .campaigns import router as campaigns_router
from .templates import router as templates_router
from .themes import router as themes_router
from .analytics import router as analytics_router
from .config import router as config_router
from .resources import router as resources_router

# User API root router
user_router = APIRouter(prefix="/api/v2/user", tags=["user-v2"])

# Include all user sub-routers
user_router.include_router(billing_router)
user_router.include_router(generation_router)
user_router.include_router(webhooks_router)
user_router.include_router(projects_router)
user_router.include_router(marketplace_router)
user_router.include_router(campaigns_router)
user_router.include_router(templates_router)
user_router.include_router(themes_router)
user_router.include_router(analytics_router)
user_router.include_router(config_router)
user_router.include_router(resources_router)

__all__ = ["user_router"]
