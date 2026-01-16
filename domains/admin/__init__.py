"""
Admin Domain Module

@module domains.admin
@version 1.3.0

Provides admin-specific business logic for:
- User management (AdminUsersService)
- Logs and audit (AdminLogsService)
- Metrics and analytics (AdminMetricsService)
- Task management (AdminTasksService)

WHY separate Admin domain?
- Admin operations require audit logging
- Different security context (admin authentication)
- Cross-domain operations (users + projects + assets + analytics + logs + metrics + tasks)
"""

from .admin_users_service import AdminUsersService
from .admin_logs_service import AdminLogsService
from .admin_metrics_service import AdminMetricsService
from .admin_tasks_service import AdminTasksService

__all__ = [
    "AdminUsersService",
    "AdminLogsService",
    "AdminMetricsService",
    "AdminTasksService",
]
