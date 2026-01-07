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

# User API root router
user_router = APIRouter(prefix="/api/v2/user", tags=["user-v2"])

# Include all user sub-routers
user_router.include_router(billing_router)

__all__ = ["user_router"]
