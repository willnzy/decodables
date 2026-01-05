"""
Routers Package
API route modules

@module routers
@version 3.24

Note: Import routers directly from their modules to avoid circular imports.
Example: from routers.admin import router as admin_router
"""

# Router imports for app.py registration
# These are imported here for convenience but can also be imported directly

# Existing routers
from .admin import router as admin_router
from .campaigns import router as campaigns_router
from .experiments import router as experiments_router
from .marketplace import router as marketplace_router
from .projects import router as projects_router
from .resources import router as resources_router
from .system_resources import router as system_resources_router
from .themes import router as themes_router
from .users import router as users_router

# New routers (v3.24 refactoring)
from .webhooks import router as webhooks_router
from .logs import router as logs_router
from .generation import router as generation_router
from .tasks import router as tasks_router
from .generations import router as generations_router
from .templates import router as templates_router
from .admin_users import router as admin_users_router
from .admin_subscriptions import router as admin_subscriptions_router

__all__ = [
    'admin_router',
    'campaigns_router',
    'experiments_router',
    'marketplace_router',
    'projects_router',
    'resources_router',
    'system_resources_router',
    'themes_router',
    'users_router',
    'webhooks_router',
    'logs_router',
    'generation_router',
    'tasks_router',
    'generations_router',
    'templates_router',
    'admin_users_router',
    'admin_subscriptions_router',
]
