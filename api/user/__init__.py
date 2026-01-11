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
# REMOVED: generation.py was redundant - endpoints now in generation_images/pdf/story.py
# from .generation import router as generation_router
from .webhooks import router as webhooks_router
from .projects import router as projects_router
from .marketplace import router as marketplace_router
from .campaigns import router as campaigns_router
from .templates import router as templates_router
from .themes import router as themes_router
from .analytics import router as analytics_router
from .config import router as config_router
from .resources import router as resources_router
from .payment import router as payment_router
from .support import router as support_router
from .export import router as export_router
from .logs import router as logs_router
from .tools import router as tools_router
from .tasks import router as tasks_router
from .generations import router as generations_router
from .experiments import router as experiments_router
from .user_profile import router as user_profile_router
from .user_assets import router as user_assets_router
from .generation_images import router as generation_images_router
from .generation_pdf import router as generation_pdf_router
from .generation_story import router as generation_story_router
from .system_resources import router as system_resources_router
from .onboarding import router as onboarding_router
from .referrals import router as referrals_router
from .articles import router as articles_router

# User API root router
user_router = APIRouter(prefix="/api/v2/user", tags=["user-v2"])

# Include all user sub-routers
user_router.include_router(billing_router)
# REMOVED: user_router.include_router(generation_router)
user_router.include_router(webhooks_router)
user_router.include_router(projects_router)
user_router.include_router(marketplace_router)
user_router.include_router(campaigns_router)
user_router.include_router(templates_router)
user_router.include_router(themes_router)
user_router.include_router(analytics_router)
user_router.include_router(config_router)
user_router.include_router(resources_router)
user_router.include_router(payment_router)
user_router.include_router(support_router)
user_router.include_router(export_router)
user_router.include_router(logs_router)
user_router.include_router(tools_router)
user_router.include_router(tasks_router)
user_router.include_router(generations_router)
user_router.include_router(experiments_router)
user_router.include_router(user_profile_router)
user_router.include_router(user_assets_router)
user_router.include_router(generation_images_router)
user_router.include_router(generation_pdf_router)
user_router.include_router(generation_story_router)
user_router.include_router(system_resources_router)
user_router.include_router(onboarding_router)
user_router.include_router(referrals_router)
user_router.include_router(articles_router)

__all__ = ["user_router"]
