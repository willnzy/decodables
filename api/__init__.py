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
- /api/v2/payment/* - Payment and checkout
- /api/v2/resources/* - System resources (stickers, backgrounds)
- /api/v2/assets/* - User assets management
- /api/v2/generate/* - AI content generation
- /api/v2/tasks/* - Async task management
- /api/v2/templates/* - Prompt templates management
- /api/v2/export/* - PDF/preview/ZIP export
- /api/v2/themes/* - Holiday themes
- /api/v2/campaigns/* - Marketing campaigns
- /api/v2/analytics/* - Analytics events
- /api/v2/tools/* - PDF preview and OCR tools
- /api/v2/generations/* - Generation history
- /api/v2/support/* - Customer support and feedback
- /api/v2/configs/* - Public configurations
- /api/v2/logs/* - Error logging
- /api/v2/experiments/* - A/B testing experiments (public)
- /api/v2/admin/* - Admin management (users, stats, config, etc.)
- /api/v2/ws/* - WebSocket endpoints
"""

from fastapi import APIRouter

# Import all routers
from .billing_api import router as billing_router
from .credits_api import router as credits_router
from .user_api import router as user_router
from .projects_api import router as projects_router
from .marketplace_api import router as marketplace_router
from .platform_api import router as platform_router
from .payment_api import router as payment_router
from .resources_api import router as resources_router
from .assets_api import router as assets_router
from .generation_api import router as generation_router
from .tasks_api import router as tasks_router
from .templates_api import router as templates_router
from .export_api import router as export_router
from .themes_api import router as themes_router
from .campaigns_api import router as campaigns_router
from .analytics_api import router as analytics_router
from .tools_api import router as tools_router
from .generations_api import router as generations_router
from .support_api import router as support_router
from .config_api import router as config_router
from .logs_api import router as logs_router
from .websocket_api import router as websocket_router
from .experiments_api import router as experiments_router
from .admin import admin_router

# Create main API router
api_router = APIRouter()

# Include all domain routers
api_router.include_router(billing_router)
api_router.include_router(credits_router)
api_router.include_router(user_router)
api_router.include_router(projects_router)
api_router.include_router(marketplace_router)
api_router.include_router(platform_router)
api_router.include_router(payment_router)
api_router.include_router(resources_router)
api_router.include_router(assets_router)
api_router.include_router(generation_router)
api_router.include_router(tasks_router)
api_router.include_router(templates_router)
api_router.include_router(export_router)
api_router.include_router(themes_router)
api_router.include_router(campaigns_router)
api_router.include_router(analytics_router)
api_router.include_router(tools_router)
api_router.include_router(generations_router)
api_router.include_router(support_router)
api_router.include_router(config_router)
api_router.include_router(logs_router)
api_router.include_router(websocket_router)
api_router.include_router(experiments_router)
api_router.include_router(admin_router)

__all__ = [
    'api_router',
    'billing_router',
    'credits_router',
    'user_router',
    'projects_router',
    'marketplace_router',
    'platform_router',
    'payment_router',
    'resources_router',
    'assets_router',
    'generation_router',
    'tasks_router',
    'templates_router',
    'export_router',
    'themes_router',
    'campaigns_router',
    'analytics_router',
    'tools_router',
    'generations_router',
    'support_router',
    'config_router',
    'logs_router',
    'websocket_router',
    'experiments_router',
    'admin_router',
]
