# Scaling Guide - Multi-Instance Deployment

> This guide documents how to scale the FastAPI backend to multiple instances.

## Current Architecture (Single Instance)

```
Users ──► Railway (1 instance) ──► Supabase
              │
              └── Scheduler runs here
```

## Scaled Architecture (Multiple Instances)

```
                    ┌──► Instance 1 (ENABLE_SCHEDULER=true)
Users ──► Railway ──┼──► Instance 2 (ENABLE_SCHEDULER=false)
       Load Balancer└──► Instance 3 (ENABLE_SCHEDULER=false)
                              │
                              └── All instances ──► Supabase
```

## When to Scale

Monitor these metrics in Railway Dashboard:

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU Usage | > 70% sustained | Add instance |
| Memory Usage | > 80% sustained | Add instance |
| Response Time P95 | > 2 seconds | Add instance |
| Daily Active Users | > 1000 | Consider scaling |

## How to Scale on Railway

### Step 1: Prepare Environment Variables

Before scaling, ensure you have these env vars ready:

```bash
# Instance 1 (Primary - runs scheduler)
ENABLE_SCHEDULER=true

# Instance 2, 3, ... (Workers - no scheduler)
ENABLE_SCHEDULER=false
```

### Step 2: Scale in Railway

1. Go to Railway Dashboard → Your Project → Backend Service
2. Click "Settings" → "Scaling"
3. Increase replica count
4. Configure environment variables per replica (if supported)
   - OR use Railway's replica ID to conditionally enable scheduler

### Step 3: Verify Deployment

```bash
# Check logs for instance IDs
# Each instance logs: "🚀 Starting instance: {INSTANCE_ID}"

# Verify only ONE instance shows:
# "📅 Scheduler started with jobs:"
```

## Component Behaviors in Multi-Instance Mode

### 1. Scheduler (APScheduler)

| Setting | Behavior |
|---------|----------|
| `ENABLE_SCHEDULER=true` | Runs scheduled jobs (hourly/daily aggregation) |
| `ENABLE_SCHEDULER=false` | Scheduler disabled, instance only handles API requests |

**⚠️ WARNING**: If multiple instances have `ENABLE_SCHEDULER=true`, jobs will run multiple times!

### 2. In-Memory Caches

| Cache | TTL | Multi-Instance Behavior |
|-------|-----|------------------------|
| `config_service` cache | 60s | Each instance has own cache; 60s max inconsistency |
| `db_service` config cache | 300s | Each instance has own cache; 5min max inconsistency |

**Impact**: Config changes may take up to 5 minutes to propagate to all instances.

**Mitigation**: Call admin API `/api/admin/configs/cache/invalidate` after config changes.

### 3. Rate Limiting (slowapi)

Current implementation uses **in-memory storage**.

| Mode | Behavior |
|------|----------|
| Single Instance | Works correctly |
| Multi-Instance | Rate limits are per-instance (not shared) |

**Future Enhancement**: Use Redis for shared rate limiting:
```python
from slowapi import Limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://your-redis-url:6379"
)
```

### 4. Database Connections

Supabase client is stateless - each instance creates its own connection.
No special handling needed.

### 5. File Storage

All file operations use Supabase Storage (external).
No special handling needed.

## Future Enhancements (When Needed)

### Phase 1: Shared Rate Limiting
```
Add Upstash Redis → Configure slowapi to use Redis storage
Estimated effort: 2-4 hours
```

### Phase 2: Shared Cache
```
Add Redis → Replace in-memory caches with Redis
Estimated effort: 4-8 hours
```

### Phase 3: Message Queue (for long-running tasks)
```
Add Redis Queue/Celery → Offload AI generation to workers
Estimated effort: 1-2 weeks (includes frontend changes)
```

## Troubleshooting

### Issue: Scheduled tasks running multiple times
**Cause**: Multiple instances have `ENABLE_SCHEDULER=true`
**Fix**: Ensure only ONE instance has `ENABLE_SCHEDULER=true`

### Issue: Rate limits not working correctly
**Cause**: In-memory rate limiting doesn't share state across instances
**Fix**: Implement Redis-based rate limiting

### Issue: Config changes not reflecting
**Cause**: Each instance has its own cache
**Fix**: 
1. Wait for TTL (up to 5 minutes)
2. Or call `/api/admin/configs/cache/invalidate` on all instances
3. Or restart all instances

## Monitoring

When running multiple instances, ensure your logging includes instance ID:

```python
# Already implemented in app.py
logger.info(f"[Instance {INSTANCE_ID}] Request processed")
```

This helps trace which instance handled a specific request.

---

Last Updated: 2026-01-03
