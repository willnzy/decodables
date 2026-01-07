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
"""

from fastapi import APIRouter

from .users_api import router as users_router
from .stats_api import router as stats_router
from .config_api import router as config_router
from .campaigns_api import router as campaigns_router
from .moderation_api import router as moderation_router
from .notifications_api import router as notifications_router
from .system_api import router as system_router
from .tasks_api import router as tasks_router
from .ai_api import router as ai_router
from .logs_api import router as logs_router
from .metrics_api import router as metrics_router
from .subscriptions_api import router as subscriptions_router
from .events_api import router as events_router
from .experiments_api import router as experiments_router

# New v2 routers (without _api suffix)
from .users import router as users_v2_router
from .stats import router as stats_v2_router
from .campaigns import router as campaigns_v2_router
from .logs import router as logs_v2_router
from .metrics import router as metrics_v2_router
from .experiments import router as experiments_v2_router

# Create admin API router
admin_router = APIRouter(prefix="/api/v2/admin", tags=["admin-v2"])

# Include all admin sub-routers
admin_router.include_router(users_router)
admin_router.include_router(stats_router)
admin_router.include_router(config_router)
admin_router.include_router(campaigns_router)
admin_router.include_router(moderation_router)
admin_router.include_router(notifications_router)
admin_router.include_router(system_router)
admin_router.include_router(tasks_router)
admin_router.include_router(ai_router)
admin_router.include_router(logs_router)
admin_router.include_router(metrics_router)
admin_router.include_router(subscriptions_router)
admin_router.include_router(events_router)
admin_router.include_router(experiments_router)

# Include new v2 routers
admin_router.include_router(users_v2_router)
admin_router.include_router(stats_v2_router)
admin_router.include_router(campaigns_v2_router)
admin_router.include_router(logs_v2_router)
admin_router.include_router(metrics_v2_router)
admin_router.include_router(experiments_v2_router)

__all__ = ['admin_router']
