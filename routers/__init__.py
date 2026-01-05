"""
Routers Package
API route modules

@module routers
@version 3.24

Note: Import routers directly from their modules to avoid circular imports.
Example: from routers.admin_users import router as admin_users_router
"""

# Router imports for app.py registration
# These are imported here for convenience but can also be imported directly

# Public-facing routers
from .campaigns import router as campaigns_router
from .marketplace import router as marketplace_router
from .projects import router as projects_router
from .resources import router as resources_router
from .system_resources import router as system_resources_router
from .themes import router as themes_router
from .users import router as users_router

# Experiment routers (v3.24: split from experiments.py)
from .experiments_public import router as experiments_public_router
from .experiments_admin import router as experiments_admin_router

# v3.24 refactored routers
from .webhooks import router as webhooks_router
from .logs import router as logs_router
from .generation import router as generation_router
from .generation_images import router as generation_images_router
from .generation_story import router as generation_story_router
from .generation_pdf import router as generation_pdf_router
from .tasks import router as tasks_router
from .generations import router as generations_router
from .templates import router as templates_router

# Admin sub-routers (v3.24: split from admin.py)
from .admin_system import router as admin_system_router
from .admin_metrics import router as admin_metrics_router
from .admin_campaigns import router as admin_campaigns_router
from .admin_tasks_mgmt import router as admin_tasks_mgmt_router
from .admin_ai_models import router as admin_ai_models_router
from .admin_users import router as admin_users_router
from .admin_subscriptions import router as admin_subscriptions_router
from .admin_notifications import router as admin_notifications_router
from .admin_stats import router as admin_stats_router
from .admin_moderation import router as admin_moderation_router
from .admin_logs import router as admin_logs_router
from .admin_ai import router as admin_ai_router
from .admin_events import router as admin_events_router
from .admin_config import router as admin_config_router

# Utility routers
from .user_assets import router as user_assets_router
from .user_profile import router as user_profile_router
from .tools import router as tools_router
from .payment import router as payment_router
from .support import router as support_router
from .config import router as config_router
from .export import router as export_router

__all__ = [
    # Public
    'campaigns_router',
    'marketplace_router',
    'projects_router',
    'resources_router',
    'system_resources_router',
    'themes_router',
    'users_router',
    # Experiments
    'experiments_public_router',
    'experiments_admin_router',
    # Generation
    'generation_router',
    'generation_images_router',
    'generation_story_router',
    'generation_pdf_router',
    # Tasks & Generations
    'tasks_router',
    'generations_router',
    'templates_router',
    # Webhooks & Logs
    'webhooks_router',
    'logs_router',
    # Admin
    'admin_system_router',
    'admin_metrics_router',
    'admin_campaigns_router',
    'admin_tasks_mgmt_router',
    'admin_ai_models_router',
    'admin_users_router',
    'admin_subscriptions_router',
    'admin_notifications_router',
    'admin_stats_router',
    'admin_moderation_router',
    'admin_logs_router',
    'admin_ai_router',
    'admin_events_router',
    'admin_config_router',
    # Utility
    'user_assets_router',
    'user_profile_router',
    'tools_router',
    'payment_router',
    'support_router',
    'config_router',
    'export_router',
]
