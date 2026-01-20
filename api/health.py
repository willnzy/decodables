"""
Health Check Router - Railway deployment monitoring
健康检查路由 - 用于 Railway 部署监控

@module api.health
@version 3.26 (Container DI Migration)

Changes:
- v3.26: Container DI Migration
  - Fixed async/sync mismatch in check_supabase_connection()
  - Added timeout protection for health checks
  - Properly awaits database connection check
- v3.25: Security improvements
  - HEALTH-MEDIUM-1: Added rate limiting to both endpoints
  - HEALTH-LOW-1: Limited error exposure in helper functions
  - HEALTH-LOW-2: Added admin authentication to /health/detailed

Endpoints:
- GET /health - Basic health check (public)
- GET /health/detailed - Detailed health with queue status (admin only)
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request

from dependencies import require_admin
from core.cache.redis_provider import is_redis_available, get_redis_info
from core.database import get_async_db_client
from infrastructure.rate_limiter import limiter
from config import API_VERSION, ENV

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Health check timeout (seconds)
HEALTH_CHECK_TIMEOUT = 5.0


# ==========================================
# Health Check Endpoints
# ==========================================

@router.get("/health/diagnose")
@limiter.limit("10/minute")
async def diagnose_connection(request: Request):
    """
    诊断 AsyncClient 连接问题。

    测试内容:
    1. 直接 httpx 请求 Supabase REST API
    2. 使用缓存的 AsyncClient 查询
    3. 新建 AsyncClient 查询

    用于定位间歇性连接超时的根本原因。
    """
    import time
    import httpx
    from config import SUPABASE_URL, SUPABASE_KEY

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {}
    }

    # Test 1: 直接 httpx 请求
    try:
        url = f"{SUPABASE_URL}rest/v1/profiles?select=id&limit=1"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        start = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            elapsed = time.time() - start
            results["tests"]["direct_httpx"] = {
                "status": "ok" if response.status_code == 200 else "error",
                "time_ms": round(elapsed * 1000, 2),
                "http_status": response.status_code
            }
    except Exception as e:
        results["tests"]["direct_httpx"] = {
            "status": "error",
            "error": str(e)[:100]
        }

    # Test 2: 缓存的 AsyncClient
    try:
        start = time.time()
        client = await get_async_db_client()
        get_client_time = time.time() - start

        if client:
            start = time.time()
            result = await client.table("profiles").select("id").limit(1).execute()
            query_time = time.time() - start
            results["tests"]["cached_async_client"] = {
                "status": "ok",
                "get_client_ms": round(get_client_time * 1000, 2),
                "query_ms": round(query_time * 1000, 2),
                "total_ms": round((get_client_time + query_time) * 1000, 2)
            }
        else:
            results["tests"]["cached_async_client"] = {
                "status": "error",
                "error": "Client is None"
            }
    except Exception as e:
        results["tests"]["cached_async_client"] = {
            "status": "error",
            "error": str(e)[:100]
        }

    # Test 3: 新建 AsyncClient
    try:
        from supabase import acreate_client

        start = time.time()
        new_client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
        init_time = time.time() - start

        start = time.time()
        result = await new_client.table("profiles").select("id").limit(1).execute()
        query_time = time.time() - start

        results["tests"]["new_async_client"] = {
            "status": "ok",
            "init_ms": round(init_time * 1000, 2),
            "query_ms": round(query_time * 1000, 2),
            "total_ms": round((init_time + query_time) * 1000, 2)
        }
    except Exception as e:
        results["tests"]["new_async_client"] = {
            "status": "error",
            "error": str(e)[:100]
        }

    # 诊断结论
    cached = results["tests"].get("cached_async_client", {})
    direct = results["tests"].get("direct_httpx", {})
    new = results["tests"].get("new_async_client", {})

    if cached.get("status") == "ok" and direct.get("status") == "ok":
        cached_time = cached.get("total_ms", 0)
        direct_time = direct.get("time_ms", 0)

        if cached_time > direct_time * 5 and cached_time > 1000:
            results["diagnosis"] = "CACHED_CLIENT_SLOW"
            results["recommendation"] = "缓存的 AsyncClient 连接可能已失效，建议重启服务"
        elif cached_time > 5000:
            results["diagnosis"] = "CONNECTION_TIMEOUT"
            results["recommendation"] = "连接超时，可能是网络问题"
        else:
            results["diagnosis"] = "HEALTHY"
            results["recommendation"] = "连接正常"
    elif cached.get("status") == "error":
        results["diagnosis"] = "CACHED_CLIENT_ERROR"
        results["recommendation"] = f"缓存客户端错误: {cached.get('error', 'unknown')}"
    else:
        results["diagnosis"] = "UNKNOWN"
        results["recommendation"] = "需要进一步排查"

    return results


@router.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """
    Basic health check for Railway monitoring.

    v3.26: Fixed async/sync mismatch, added timeout protection.

    Returns:
        - status: healthy/degraded/unhealthy
        - version: API version
        - environment: production/staging/development
        - services: Status of dependencies
    """
    redis_ok = is_redis_available()

    # v3.26: Properly await async database check with timeout
    try:
        supabase_ok = await asyncio.wait_for(
            check_supabase_connection_async(),
            timeout=HEALTH_CHECK_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.warning("[Health] Supabase connection check timed out")
        supabase_ok = False

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

    v3.26: Fixed async/sync mismatch, added timeout protection.

    Provides:
    - Redis connection info
    - Queue lengths (high/default/low)
    - Worker counts
    - Supabase status
    """
    redis_ok = is_redis_available()

    # v3.26: Properly await async database check with timeout
    try:
        supabase_ok = await asyncio.wait_for(
            check_supabase_connection_async(),
            timeout=HEALTH_CHECK_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.warning("[Health] Supabase connection check timed out")
        supabase_ok = False

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

async def check_supabase_connection_async() -> bool:
    """
    Check if Supabase is accessible (async).

    v3.26: Renamed to _async suffix, properly awaits AsyncClient operations.

    WHY async?
    - get_async_db_client() returns AsyncClient
    - Database operations should not block the event loop
    - Enables timeout protection via asyncio.wait_for()
    """
    try:
        supabase = await get_async_db_client()
        if supabase is None:
            logger.warning("[Health] Database client not configured")
            return False
        # Try a simple query - uses AsyncClient
        result = await supabase.table("profiles").select("id").limit(1).execute()
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
