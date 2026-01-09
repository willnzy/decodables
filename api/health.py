"""
Health Check Router - Railway deployment monitoring
健康检查路由 - 用于 Railway 部署监控

@module api.health
@version 3.25

Changes:
- v3.25: Security improvements
  - HEALTH-MEDIUM-1: Added rate limiting to both endpoints
  - HEALTH-LOW-1: Limited error exposure in helper functions
  - HEALTH-LOW-2: Added admin authentication to /health/detailed

Endpoints:
- GET /health - Basic health check (public)
- GET /health/detailed - Detailed health with queue status (admin only)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request

from dependencies import require_admin
from core.cache.redis_provider import is_redis_available, get_redis_info
from core.database import get_supabase_client
from infrastructure.rate_limiter import limiter
from config import API_VERSION, ENV

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# ==========================================
# Health Check Endpoints
# ==========================================

@router.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """
    Basic health check for Railway monitoring.

    Returns:
        - status: healthy/degraded/unhealthy
        - version: API version
        - environment: production/staging/development
        - services: Status of dependencies
    """
    redis_ok = is_redis_available()
    supabase_ok = check_supabase_connection()

    # Overall status
    if redis_ok and supabase_ok:
        status = "healthy"
    elif supabase_ok:  # Redis can fall back to memory
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "version": API_VERSION,
        "environment": ENV,
        "services": {
            "redis": "up" if redis_ok else "down",
            "supabase": "up" if supabase_ok else "down",
        }
    }


@router.get("/health/detailed")
@limiter.limit("30/minute")
async def detailed_health_check(request: Request, admin: dict = Depends(require_admin)):
    """
    Detailed health check with queue and worker status.

    **Requires admin authentication** (v3.25: HEALTH-LOW-2)

    Provides:
    - Redis connection info
    - Queue lengths (high/default/low)
    - Worker counts
    - Supabase status
    """
    redis_ok = is_redis_available()
    supabase_ok = check_supabase_connection()

    # Get Redis detailed info
    redis_info = get_redis_info()
    queue_info = get_queue_info() if redis_ok else None

    # Overall status
    if redis_ok and supabase_ok:
        status = "healthy"
    elif supabase_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "version": API_VERSION,
        "environment": ENV,
        "services": {
            "redis": {
                "status": "up" if redis_ok else "down",
                "info": redis_info if redis_ok else None
            },
            "supabase": {
                "status": "up" if supabase_ok else "down"
            }
        },
        "queues": queue_info,
        "warnings": get_health_warnings(redis_ok, supabase_ok, queue_info)
    }


# ==========================================
# Helper Functions
# ==========================================

def check_supabase_connection() -> bool:
    """Check if Supabase is accessible."""
    try:
        supabase = get_supabase_client()
        # Try a simple query
        result = supabase.table("profiles").select("id").limit(1).execute()
        return True
    except Exception as e:
        # v3.25: HEALTH-LOW-1 - Limited error exposure
        logger.warning(f"[Health] Supabase check failed: {e}")
        return False


def get_queue_info() -> Optional[dict]:
    """Get RQ queue information."""
    try:
        from rq import Queue
        from core.cache.redis_provider import get_redis_client

        redis_conn = get_redis_client()
        if not redis_conn:
            return None

        # Get queue stats
        queues = ["high", "default", "low"]
        queue_stats = {}

        for queue_name in queues:
            try:
                queue = Queue(queue_name, connection=redis_conn)
                queue_stats[queue_name] = {
                    "pending": len(queue),
                    "failed": queue.failed_job_registry.count,
                    "scheduled": queue.scheduled_job_registry.count,
                }
            except Exception as e:
                # v3.25: HEALTH-LOW-1 - Limited error exposure
                logger.warning(f"[Health] Failed to get {queue_name} queue stats")
                queue_stats[queue_name] = {"error": "Failed to retrieve queue stats"}

        # Get worker count
        from rq import Worker
        workers = Worker.all(connection=redis_conn)
        active_workers = [w for w in workers if w.state == "busy"]

        return {
            "queues": queue_stats,
            "workers": {
                "total": len(workers),
                "active": len(active_workers),
                "idle": len(workers) - len(active_workers)
            }
        }
    except Exception as e:
        # v3.25: HEALTH-LOW-1 - Limited error exposure
        logger.error(f"[Health] Failed to get queue info: {e}")
        return None


def get_health_warnings(redis_ok: bool, supabase_ok: bool, queue_info: Optional[dict]) -> list:
    """Generate health warnings based on system status."""
    warnings = []

    if not redis_ok:
        warnings.append({
            "severity": "warning",
            "message": "Redis is down, using memory fallback. Task queue disabled."
        })

    if not supabase_ok:
        warnings.append({
            "severity": "critical",
            "message": "Supabase is down, database operations will fail."
        })

    # Check queue health
    if queue_info and "queues" in queue_info:
        for queue_name, stats in queue_info["queues"].items():
            if "error" in stats:
                continue

            # Warn if too many pending tasks
            pending = stats.get("pending", 0)
            if pending > 50:
                warnings.append({
                    "severity": "warning",
                    "message": f"Queue '{queue_name}' has {pending} pending tasks. Consider scaling workers."
                })

            # Warn if failed tasks accumulating
            failed = stats.get("failed", 0)
            if failed > 10:
                warnings.append({
                    "severity": "warning",
                    "message": f"Queue '{queue_name}' has {failed} failed tasks. Review error logs."
                })

    # Check worker health
    if queue_info and "workers" in queue_info:
        workers = queue_info["workers"]
        if workers["total"] == 0:
            warnings.append({
                "severity": "critical",
                "message": "No workers running! Background tasks will not be processed."
            })
        elif workers["total"] < 2:
            warnings.append({
                "severity": "info",
                "message": f"Only {workers['total']} worker running. Consider scaling for high availability."
            })

    return warnings
