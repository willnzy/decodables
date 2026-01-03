"""
Admin Router - System Configs & Metrics
Only contains endpoints NOT already defined in app.py

@module routers/admin
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import require_admin
from db_service import (
    # System Config Functions
    admin_get_system_configs, admin_get_config_groups,
    admin_create_system_config, admin_update_system_config,
    admin_delete_system_config, admin_get_config_audit_logs,
    invalidate_config_cache_api,
    supabase
)
from datetime import date, timedelta

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==========================================
# System Configuration Routes
# ==========================================

class ConfigCreateRequest(BaseModel):
    key: str
    value: str
    value_type: str = "text"  # 'text', 'boolean', 'json', 'number'
    config_group: str = "general"
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    value: Optional[str] = None
    value_type: Optional[str] = None
    config_group: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/configs")
def get_configs(
    group: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """
    Get all system configs with filtering.
    
    Args:
        group: Filter by config_group
        search: Search in key or description
    
    Returns:
        Paginated configs
    """
    return admin_get_system_configs(group, search, page, limit)


@router.get("/configs/groups")
def get_config_groups(admin: dict = Depends(require_admin)):
    """
    Get all distinct config groups.
    
    Returns:
        List of group names
    """
    groups = admin_get_config_groups()
    return {"groups": groups}


@router.post("/configs")
def create_config(req: ConfigCreateRequest, admin: dict = Depends(require_admin)):
    """
    Create a new system config.
    
    Returns:
        Created config
    """
    try:
        result = admin_create_system_config(
            key=req.key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            admin_id=admin["id"]
        )
        if result:
            return {"status": "created", "config": result}
        raise HTTPException(500, "Failed to create config")
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(409, f"Config key '{req.key}' already exists")
        raise HTTPException(500, str(e))


@router.put("/configs/{key:path}")
def update_config(key: str, req: ConfigUpdateRequest, admin: dict = Depends(require_admin)):
    """
    Update an existing system config.
    
    Returns:
        Updated config
    """
    try:
        result = admin_update_system_config(
            key=key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            is_active=req.is_active,
            admin_id=admin["id"]
        )
        if result:
            return {"status": "updated", "config": result}
        raise HTTPException(404, "Config not found")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/configs/{key:path}")
def delete_config(key: str, admin: dict = Depends(require_admin)):
    """
    Delete a system config.
    
    Returns:
        Status
    """
    try:
        result = admin_delete_system_config(key, admin["id"])
        if result:
            return {"status": "deleted", "key": key}
        raise HTTPException(404, "Config not found")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/configs/audit")
def get_config_audit_logs(
    config_key: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """
    Get config change audit logs.
    
    Returns:
        Audit log entries
    """
    logs = admin_get_config_audit_logs(config_key, page, limit)
    return {"items": logs, "page": page}


@router.post("/configs/cache/invalidate")
def invalidate_cache(admin: dict = Depends(require_admin)):
    """
    Manually invalidate all config cache.
    Useful for forcing immediate updates across all instances.
    
    Returns:
        Status
    """
    invalidate_config_cache_api()
    return {"status": "cache_invalidated"}


# ==========================================
# Analytics & Metrics API (v3.12)
# ==========================================

@router.get("/metrics/daily")
def get_daily_metrics(
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """
    Get daily metrics trend (DAU, new users, AI usage, etc.)
    
    Args:
        days: Number of days to fetch (default 30)
    
    Returns:
        List of daily metrics
    """
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    result = supabase.table("analytics_daily_metrics").select("*").gte(
        "metric_date", start_date
    ).order("metric_date", desc=True).execute()
    
    return {
        "items": result.data or [],
        "period_days": days
    }


@router.get("/metrics/monthly")
def get_monthly_metrics(
    months: int = 12,
    admin: dict = Depends(require_admin)
):
    """
    Get monthly metrics (MRR, MAU, ARPU, etc.)
    
    Args:
        months: Number of months to fetch (default 12)
    
    Returns:
        List of monthly metrics
    """
    start_date = (date.today() - timedelta(days=months * 30)).replace(day=1).isoformat()
    
    result = supabase.table("analytics_monthly_metrics").select("*").gte(
        "metric_month", start_date
    ).order("metric_month", desc=True).execute()
    
    return {
        "items": result.data or [],
        "period_months": months
    }


@router.get("/metrics/retention")
def get_retention_metrics(admin: dict = Depends(require_admin)):
    """
    Get cohort retention data for retention analysis.
    
    Returns:
        Cohort retention rates
    """
    result = supabase.table("analytics_cohort_retention").select("*").eq(
        "cohort_type", "week"
    ).order("cohort_date", desc=True).limit(12).execute()
    
    return {
        "cohorts": result.data or [],
        "retention_periods": ["D1", "D7", "D14", "D30", "D60", "D90"]
    }


@router.get("/metrics/funnel")
def get_funnel_metrics(
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """
    Get conversion funnel metrics.
    
    Returns:
        Funnel stages with conversion rates
    """
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    result = supabase.table("analytics_funnel_metrics").select("*").eq(
        "funnel_type", "main"
    ).gte("metric_date", start_date).order("metric_date", desc=True).execute()
    
    # Aggregate totals
    totals = {
        "visitors": 0,
        "signups": 0,
        "activated": 0,
        "engaged": 0,
        "converted": 0,
    }
    
    for row in result.data or []:
        totals["visitors"] += row.get("stage_visitors", 0)
        totals["signups"] += row.get("stage_signups", 0)
        totals["activated"] += row.get("stage_activated", 0)
        totals["engaged"] += row.get("stage_engaged", 0)
        totals["converted"] += row.get("stage_converted", 0)
    
    # Calculate overall conversion rates
    rates = {}
    if totals["visitors"] > 0:
        rates["visitor_to_signup"] = round(totals["signups"] / totals["visitors"] * 100, 2)
        rates["visitor_to_converted"] = round(totals["converted"] / totals["visitors"] * 100, 2)
    if totals["signups"] > 0:
        rates["signup_to_activated"] = round(totals["activated"] / totals["signups"] * 100, 2)
        rates["signup_to_converted"] = round(totals["converted"] / totals["signups"] * 100, 2)
    
    return {
        "period_days": days,
        "totals": totals,
        "rates": rates,
        "daily": result.data or []
    }


@router.get("/metrics/errors")
def get_error_metrics(
    days: int = 7,
    admin: dict = Depends(require_admin)
):
    """
    Get error summary for monitoring dashboard.
    
    Returns:
        Top errors with affected users and trend
    """
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    result = supabase.table("analytics_error_summary").select("*").gte(
        "summary_date", start_date
    ).order("occurrence_count", desc=True).limit(100).execute()
    
    # Group by error code
    error_groups = {}
    for row in result.data or []:
        code = row.get("error_code", "UNKNOWN")
        if code not in error_groups:
            error_groups[code] = {
                "error_code": code,
                "error_type": row.get("error_type"),
                "total_occurrences": 0,
                "total_affected_users": 0,
                "latest_message": row.get("sample_message"),
                "latest_request_id": row.get("sample_request_id"),
                "avg_trend": 0,
                "endpoints": set()
            }
        
        error_groups[code]["total_occurrences"] += row.get("occurrence_count", 0)
        error_groups[code]["total_affected_users"] += row.get("affected_users", 0)
        if row.get("endpoint"):
            error_groups[code]["endpoints"].add(row["endpoint"])
    
    # Convert to list and sort
    top_errors = sorted(
        [
            {**v, "endpoints": list(v["endpoints"])} 
            for v in error_groups.values()
        ],
        key=lambda x: -x["total_occurrences"]
    )[:20]
    
    return {
        "period_days": days,
        "top_errors": top_errors,
        "total_error_types": len(error_groups)
    }


@router.get("/metrics/dau-trend")
def get_dau_trend(admin: dict = Depends(require_admin)):
    """
    Get DAU trend with 7-day moving average (from materialized view).
    
    Returns:
        DAU trend data
    """
    result = supabase.table("mv_dau_trend").select("*").order(
        "metric_date", desc=True
    ).limit(30).execute()
    
    return {
        "trend": result.data or []
    }


@router.post("/metrics/refresh")
def refresh_metrics(admin: dict = Depends(require_admin)):
    """
    Manually trigger metrics ETL.
    
    Returns:
        Status
    """
    try:
        from scheduled_tasks.metrics_etl import run_daily_etl
        run_daily_etl()
        return {"status": "success", "message": "Metrics refresh completed"}
    except Exception as e:
        raise HTTPException(500, f"Metrics refresh failed: {str(e)}")


# ==========================================
# Campaign Management Routes (v3.13)
# ==========================================

class CampaignCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # credits_gift | credits_discount | credits_bonus
    config: dict
    target_type: str = 'all'
    target_config: Optional[dict] = {}
    notification_channels: list = ['banner']
    notification_config: Optional[dict] = {}
    start_at: str  # ISO datetime
    end_at: str    # ISO datetime
    timezone: str = 'America/New_York'
    usage_limit: Optional[int] = None
    usage_per_user: int = 1


class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    config: Optional[dict] = None
    target_type: Optional[str] = None
    target_config: Optional[dict] = None
    notification_channels: Optional[list] = None
    notification_config: Optional[dict] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    timezone: Optional[str] = None
    usage_limit: Optional[int] = None
    usage_per_user: Optional[int] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/campaigns")
def list_campaigns(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """
    List all campaigns with filtering.
    
    Args:
        status: Filter by status (draft/scheduled/active/paused/ended)
        type: Filter by type (credits_gift/credits_discount/credits_bonus)
        page: Page number
        limit: Items per page
    
    Returns:
        Paginated list of campaigns
    """
    query = supabase.table('campaigns').select('*', count='exact')
    
    if status:
        query = query.eq('status', status)
    if type:
        query = query.eq('type', type)
    
    offset = (page - 1) * limit
    result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
    
    return {
        "items": result.data or [],
        "total": result.count or 0,
        "page": page,
        "limit": limit,
        "total_pages": (result.count + limit - 1) // limit if result.count else 0
    }


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Get campaign details.
    """
    result = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
    
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    
    return result.data[0]


@router.post("/campaigns")
def create_campaign(
    req: CampaignCreateRequest,
    admin: dict = Depends(require_admin)
):
    """
    Create a new campaign.
    """
    from datetime import datetime
    
    # Determine initial status based on start time
    now = datetime.utcnow()
    start_at = datetime.fromisoformat(req.start_at.replace('Z', '+00:00'))
    status = 'scheduled' if start_at.replace(tzinfo=None) > now else 'active'
    
    data = {
        "name": req.name,
        "description": req.description,
        "type": req.type,
        "config": req.config,
        "target_type": req.target_type,
        "target_config": req.target_config or {},
        "notification_channels": req.notification_channels,
        "notification_config": req.notification_config or {},
        "start_at": req.start_at,
        "end_at": req.end_at,
        "timezone": req.timezone,
        "usage_limit": req.usage_limit,
        "usage_per_user": req.usage_per_user,
        "status": status,
        "created_by": admin['id'],
    }
    
    result = supabase.table('campaigns').insert(data).execute()
    
    if not result.data:
        raise HTTPException(500, "Failed to create campaign")
    
    return {"status": "created", "campaign": result.data[0]}


@router.put("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: str,
    req: CampaignUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """
    Update an existing campaign.
    """
    from datetime import datetime
    
    # Build update data (only include non-None fields)
    data = {k: v for k, v in req.dict().items() if v is not None}
    data['updated_at'] = datetime.utcnow().isoformat()
    
    result = supabase.table('campaigns').update(data).eq('id', campaign_id).execute()
    
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    
    return {"status": "updated", "campaign": result.data[0]}


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Delete a campaign.
    """
    supabase.table('campaigns').delete().eq('id', campaign_id).execute()
    return {"status": "deleted"}


@router.post("/campaigns/{campaign_id}/activate")
def activate_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Activate a campaign.
    """
    from datetime import datetime
    
    result = supabase.table('campaigns').update({
        'status': 'active',
        'is_active': True,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', campaign_id).execute()
    
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    
    return {"status": "activated", "campaign": result.data[0]}


@router.post("/campaigns/{campaign_id}/pause")
def pause_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Pause a campaign.
    """
    from datetime import datetime
    
    result = supabase.table('campaigns').update({
        'status': 'paused',
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', campaign_id).execute()
    
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    
    return {"status": "paused", "campaign": result.data[0]}


@router.get("/campaigns/{campaign_id}/stats")
def get_campaign_stats(
    campaign_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Get campaign statistics.
    """
    # Get campaign
    campaign = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
    if not campaign.data:
        raise HTTPException(404, "Campaign not found")
    
    campaign_data = campaign.data[0]
    
    # Get claims
    claims = supabase.table('campaign_claims').select('*', count='exact').eq(
        'campaign_id', campaign_id
    ).execute()
    
    total_credits = sum(c.get('credits_received', 0) or 0 for c in (claims.data or []))
    
    usage_limit = campaign_data.get('usage_limit')
    usage_rate = None
    if usage_limit:
        usage_rate = round((claims.count or 0) / usage_limit * 100, 1)
    
    return {
        "campaign": campaign_data,
        "stats": {
            "total_claims": claims.count or 0,
            "total_credits_given": total_credits,
            "usage_rate": usage_rate,
        },
        "recent_claims": (claims.data or [])[:20]
    }


# ==========================================
# Scheduled Task Monitoring Routes (v3.15)
# ==========================================

@router.get("/tasks/status")
def get_task_status(admin: dict = Depends(require_admin)):
    """
    Get the latest status of all scheduled tasks.
    
    Returns:
        List of tasks with their latest run status
    """
    try:
        # Try to use the view first
        result = supabase.table('v_latest_task_status').select('*').execute()
        if result.data:
            return {"tasks": result.data}
    except:
        pass
    
    # Fallback: manual query
    # Get distinct task names
    tasks_result = supabase.rpc('get_distinct_task_names').execute()
    
    if not tasks_result.data:
        # Direct query approach
        result = supabase.table('scheduled_task_logs').select(
            'task_name'
        ).order('started_at', desc=True).limit(100).execute()
        
        task_names = list(set(r['task_name'] for r in (result.data or [])))
    else:
        task_names = [r['task_name'] for r in tasks_result.data]
    
    tasks = []
    for task_name in task_names:
        latest = supabase.table('scheduled_task_logs').select('*').eq(
            'task_name', task_name
        ).order('started_at', desc=True).limit(1).execute()
        
        if latest.data:
            task = latest.data[0]
            # Calculate minutes since last run
            if task.get('started_at'):
                started = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
                minutes_ago = (datetime.now(timezone.utc) - started).total_seconds() / 60
                task['minutes_since_last_run'] = round(minutes_ago, 1)
            tasks.append(task)
    
    return {"tasks": tasks}


@router.get("/tasks/logs")
def get_task_logs(
    task_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """
    Get scheduled task execution logs.
    
    Args:
        task_name: Filter by task name
        status: Filter by status (running/success/failed)
        limit: Number of logs to return
    
    Returns:
        List of task execution logs
    """
    query = supabase.table('scheduled_task_logs').select('*')
    
    if task_name:
        query = query.eq('task_name', task_name)
    if status:
        query = query.eq('status', status)
    
    result = query.order('started_at', desc=True).limit(limit).execute()
    
    return {"logs": result.data or []}


@router.get("/tasks/health")
def get_tasks_health(admin: dict = Depends(require_admin)):
    """
    Get health status of scheduled tasks.
    
    Checks if tasks are running on schedule and flags any issues.
    
    Returns:
        Health status with alerts
    """
    # Expected intervals (in minutes)
    expected_intervals = {
        'campaign_scheduler': 60,      # Should run at least hourly
        'metrics_etl': 1440,           # Should run daily
        'aggregate_stats': 1440,       # Should run daily
    }
    
    health = {
        "status": "healthy",
        "tasks": [],
        "alerts": []
    }
    
    for task_name, max_interval in expected_intervals.items():
        latest = supabase.table('scheduled_task_logs').select('*').eq(
            'task_name', task_name
        ).order('started_at', desc=True).limit(1).execute()
        
        task_health = {
            "task_name": task_name,
            "expected_interval_minutes": max_interval,
            "status": "unknown",
            "last_run": None,
            "last_status": None,
            "minutes_since_last_run": None
        }
        
        if latest.data:
            task = latest.data[0]
            task_health["last_run"] = task.get('started_at')
            task_health["last_status"] = task.get('status')
            task_health["last_result"] = task.get('result_summary')
            
            if task.get('started_at'):
                started = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
                minutes_ago = (datetime.now(timezone.utc) - started).total_seconds() / 60
                task_health["minutes_since_last_run"] = round(minutes_ago, 1)
                
                # Check if overdue
                if minutes_ago > max_interval * 1.5:
                    task_health["status"] = "overdue"
                    health["alerts"].append({
                        "level": "warning",
                        "message": f"{task_name} is overdue (last run {round(minutes_ago)} minutes ago)"
                    })
                elif task.get('status') == 'failed':
                    task_health["status"] = "failed"
                    health["alerts"].append({
                        "level": "error",
                        "message": f"{task_name} last run failed: {task.get('error_message', 'Unknown error')}"
                    })
                elif task.get('status') == 'running':
                    task_health["status"] = "running"
                else:
                    task_health["status"] = "healthy"
        else:
            task_health["status"] = "never_run"
            health["alerts"].append({
                "level": "info",
                "message": f"{task_name} has never been executed"
            })
        
        health["tasks"].append(task_health)
    
    # Set overall status
    if any(t["status"] == "failed" for t in health["tasks"]):
        health["status"] = "degraded"
    elif any(t["status"] == "overdue" for t in health["tasks"]):
        health["status"] = "warning"
    elif all(t["status"] in ["healthy", "running"] for t in health["tasks"]):
        health["status"] = "healthy"
    
    return health


@router.post("/tasks/{task_name}/run")
def trigger_task(
    task_name: str,
    admin: dict = Depends(require_admin)
):
    """
    Manually trigger a scheduled task.
    
    Note: This runs synchronously and may timeout for long-running tasks.
    For production, consider using a job queue.
    """
    import subprocess
    import os
    
    # Map task names to scripts
    task_scripts = {
        'campaign_scheduler': 'scheduled_tasks/campaign_scheduler.py',
        'metrics_etl': 'scheduled_tasks/metrics_etl.py --hourly',
        'aggregate_stats': 'scheduled_tasks/aggregate_stats.py --hourly',
    }
    
    if task_name not in task_scripts:
        raise HTTPException(400, f"Unknown task: {task_name}")
    
    script = task_scripts[task_name]
    
    try:
        # Run in background (non-blocking)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cmd = f"cd {base_dir} && python {script}"
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return {
            "status": "triggered",
            "task_name": task_name,
            "message": f"Task {task_name} has been triggered"
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to trigger task: {str(e)}")
