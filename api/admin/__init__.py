"""
Admin API Layer - Admin management endpoints (v2).

@package api.admin
@version 2.0.0

Endpoints:
- /api/v2/admin/users/* - User management
- /api/v2/admin/stats/* - Dashboard and analytics
- /api/v2/admin/config/* - System configuration
- /api/v2/admin/campaigns/* - Campaign management
- /api/v2/admin/moderation/* - Content moderation
- /api/v2/admin/notifications/* - Notification management
- /api/v2/admin/system/* - System operations
- /api/v2/admin/tasks/* - Task queue management
- /api/v2/admin/ai/* - AI insights and model configuration
- /api/v2/admin/logs/* - Error and operation logs
- /api/v2/admin/metrics/* - System metrics
- /api/v2/admin/subscriptions/* - Subscription management
- /api/v2/admin/events/* - Events and aggregation
- /api/v2/admin/experiments/* - A/B testing experiments
- /api/v2/admin/webhooks/* - Webhook retry management
- /api/v2/admin/asset-categories/* - Asset category management
"""

from fastapi import APIRouter

# v2 routers (clean module names)
from .users import router as users_router
from .stats import router as stats_router
from .campaigns import router as campaigns_router
from .logs import router as logs_router
from .metrics import router as metrics_router
from .experiments import router as experiments_router
from .ai import router as ai_router
from .ai_models import router as ai_models_router
from .config import router as config_router
from .events import router as events_router
from .moderation import router as moderation_router
from .notifications import router as notifications_router
from .subscriptions import router as subscriptions_router
from .system import router as system_router
from .tasks_mgmt import router as tasks_mgmt_router
from .feature_flags import router as feature_flags_router
from .webhooks_retry import router as webhooks_retry_router
from .asset_categories import router as asset_categories_router

# Create admin API router
admin_router = APIRouter(prefix="/api/v2/admin", tags=["admin-v2"])

# Include all v2 admin sub-routers
admin_router.include_router(users_router)
admin_router.include_router(stats_router)
admin_router.include_router(campaigns_router)
admin_router.include_router(logs_router)
admin_router.include_router(metrics_router)
admin_router.include_router(experiments_router)
admin_router.include_router(ai_router)
admin_router.include_router(ai_models_router)
admin_router.include_router(config_router)
admin_router.include_router(events_router)
admin_router.include_router(moderation_router)
admin_router.include_router(notifications_router)
admin_router.include_router(subscriptions_router)
admin_router.include_router(system_router)
admin_router.include_router(tasks_mgmt_router)
admin_router.include_router(feature_flags_router)
admin_router.include_router(webhooks_retry_router)
admin_router.include_router(asset_categories_router)

__all__ = ['admin_router']
