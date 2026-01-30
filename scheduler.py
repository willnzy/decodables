"""
Background Scheduler for Data Aggregation Tasks

v3.12: Integrated new metrics ETL system for industry-standard SaaS analytics.

Runs on FastAPI startup in Railway deployment.

MULTI-INSTANCE DEPLOYMENT GUIDE:
================================
When scaling to multiple instances, the scheduler should run on ONLY ONE instance
to prevent duplicate task execution.

Option 1: Environment Variable (Recommended for Railway)
  - Set ENABLE_SCHEDULER=true on ONE instance only
  - Set ENABLE_SCHEDULER=false on all other instances
  - Railway: Use different env vars per replica

Option 2: Leader Election (Future Enhancement)
  - Use Redis distributed lock for automatic leader election
  - Only the leader instance runs scheduled tasks
  - More robust but requires Redis

Current default: ENABLE_SCHEDULER=true (backwards compatible for single instance)
"""

import os
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = BackgroundScheduler()

def run_hourly_aggregation():
    """Run hourly aggregation tasks (both legacy and new ETL)"""
    logger.info(f"[{datetime.now()}] 🕐 Starting hourly aggregation...")
    
    # Run new metrics ETL (v3.12)
    try:
        from application.services.metrics import run_hourly_etl
        run_hourly_etl()
        logger.info(f"[{datetime.now()}] ✅ Metrics ETL (hourly) complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Metrics ETL failed: {e}")

    # Run legacy aggregation for backwards compatibility
    try:
        from application.services.aggregators import run_hourly_tasks
        run_hourly_tasks()
        logger.info(f"[{datetime.now()}] ✅ Legacy aggregation complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Legacy aggregation failed: {e}")

    # Run A/B experiment aggregation (v3.20)
    try:
        from application.services.experiments import run_hourly_experiment_tasks
        run_hourly_experiment_tasks()
        logger.info(f"[{datetime.now()}] ✅ Experiment aggregation (hourly) complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Experiment aggregation failed: {e}")

def run_daily_aggregation():
    """Run daily aggregation tasks (both legacy and new ETL)"""
    logger.info(f"[{datetime.now()}] 📅 Starting daily aggregation...")
    
    # Run new metrics ETL (v3.12) - industry-standard SaaS metrics
    try:
        from application.services.metrics import run_daily_etl
        run_daily_etl()
        logger.info(f"[{datetime.now()}] ✅ Metrics ETL (daily) complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Metrics ETL failed: {e}")

    # Run legacy aggregation for backwards compatibility
    try:
        from application.services.aggregators import run_daily_tasks
        run_daily_tasks()
        logger.info(f"[{datetime.now()}] ✅ Legacy aggregation complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Legacy aggregation failed: {e}")

    # Run A/B experiment daily tasks (v3.20)
    try:
        from application.services.experiments import run_daily_experiment_tasks
        run_daily_experiment_tasks()
        logger.info(f"[{datetime.now()}] ✅ Experiment aggregation (daily) complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Experiment daily tasks failed: {e}")


def run_daily_maintenance():
    """
    Run daily database maintenance tasks (v3.30, v3.31 AsyncClient fix)

    IMPORTANT: Uses create_task_async_client() instead of get_async_db_client()
    to avoid "Event loop is closed" error. See docs/main/backend-architecture.md 1.3.1.3
    """
    logger.info(f"[{datetime.now()}] 🔧 Starting daily maintenance tasks...")

    import asyncio

    async def _async_daily_maintenance():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client
        from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler

        # Create fresh AsyncClient for this task (NOT singleton!)
        db = await create_task_async_client()

        try:
            result = await MaintenanceScheduler.run_daily_maintenance(db=db)
            return result
        finally:
            # Cleanup: close client after task
            if hasattr(db, 'aclose'):
                await db.aclose()
                logger.info("[DB] Task-specific async client closed")

    try:
        result = asyncio.run(_async_daily_maintenance())
        total_deleted = result.get('total_deleted', 0)
        logger.info(f"[{datetime.now()}] ✅ Daily maintenance complete: {total_deleted} records deleted")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Daily maintenance failed: {e}", exc_info=True)


def run_weekly_maintenance():
    """
    Run weekly database maintenance tasks (v3.30, v3.31 AsyncClient fix)

    IMPORTANT: Uses create_task_async_client() instead of get_async_db_client()
    to avoid "Event loop is closed" error. See docs/main/backend-architecture.md 1.3.1.3
    """
    logger.info(f"[{datetime.now()}] 🔧 Starting weekly maintenance tasks...")

    import asyncio

    async def _async_weekly_maintenance():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client
        from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler

        # Create fresh AsyncClient for this task (NOT singleton!)
        db = await create_task_async_client()

        try:
            result = await MaintenanceScheduler.run_weekly_maintenance(db=db)
            return result
        finally:
            # Cleanup: close client after task
            if hasattr(db, 'aclose'):
                await db.aclose()
                logger.info("[DB] Task-specific async client closed")

    try:
        result = asyncio.run(_async_weekly_maintenance())
        total_deleted = result.get('total_deleted', 0)
        logger.info(f"[{datetime.now()}] ✅ Weekly maintenance complete: {total_deleted} records deleted")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Weekly maintenance failed: {e}", exc_info=True)


def run_storage_cleanup():
    """Run storage cleanup task (v3.18)"""
    logger.info(f"[{datetime.now()}] 🧹 Starting storage cleanup...")

    try:
        from infrastructure.tasks.storage_cleanup import run_storage_cleanup as do_cleanup
        result = do_cleanup()
        logger.info(f"[{datetime.now()}] ✅ Storage cleanup complete: {result.get('files_deleted', 0)} files deleted, {result.get('space_freed_mb', 0)} MB freed")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Storage cleanup failed: {e}")


def run_webhook_retry():
    """
    Run webhook retry task (P3-022, v2.0 AsyncClient)

    IMPORTANT: Uses create_task_async_client() instead of get_async_db_client()
    to avoid "Event loop is closed" error.

    Background:
    - BackgroundScheduler runs this in a separate thread
    - asyncio.run() creates a new event loop for each execution
    - Singleton async clients (get_async_db_client) are bound to FastAPI's event loop
    - Using singleton across event loops causes "Event loop is closed" error
    - Solution: Create fresh client for each task execution
    """
    logger.info(f"[{datetime.now()}] 🔄 Starting webhook retry task...")

    import asyncio

    async def _async_webhook_retry():
        """Async wrapper for webhook retry with fresh AsyncClient"""
        from core.database import create_task_async_client
        from infrastructure.repositories import (
            SupabaseWebhookRepository,
            SupabaseUserRepository,
            SupabaseCreditRepository,
            SupabasePaymentRepository,
        )
        from domains.webhooks import ClerkWebhookService, StripeWebhookService
        from domains.webhooks.webhook_retry_service import WebhookRetryService

        # Create fresh AsyncClient for this task (NOT singleton!)
        # This avoids "Event loop is closed" error
        db = await create_task_async_client()

        try:
            # Initialize repositories with AsyncClient
            webhook_repo = SupabaseWebhookRepository(db)
            user_repo = SupabaseUserRepository(db)
            credit_repo = SupabaseCreditRepository(db)
            payment_repo = SupabasePaymentRepository(db)

            # Initialize services
            clerk_service = ClerkWebhookService(user_repo, credit_repo)
            stripe_service = StripeWebhookService(user_repo, credit_repo, payment_repo)
            retry_service = WebhookRetryService(webhook_repo, clerk_service, stripe_service)

            # Run retry task
            result = await retry_service.retry_all_failed_webhooks()
            return result
        finally:
            # Cleanup: close client after task
            if hasattr(db, 'aclose'):
                await db.aclose()
                logger.info("[DB] Task-specific async client closed")

    try:
        # Run async function in new event loop
        result = asyncio.run(_async_webhook_retry())

        total = result["total"]
        logger.info(
            f"[{datetime.now()}] ✅ Webhook retry complete: "
            f"{total['processed']} processed, {total['failed']} failed, {total['skipped']} skipped"
        )
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Webhook retry failed: {e}", exc_info=True)

def run_credit_reconciliation():
    """
    Daily credit reconciliation task (WS7d, #38)

    Checks for active subscription users (t2/t3) whose last monthly_reset
    credit transaction is older than 32 days — indicating a missed refresh.

    SAFETY: This task only LOGS anomalies and sends Sentry alerts.
    It does NOT auto-fix. Admin must manually verify and issue credits
    via the Admin API.

    Schedule: 6:00 AM UTC daily
    """
    logger.info(f"[{datetime.now()}] 🔍 Starting credit reconciliation...")

    import asyncio

    async def _async_credit_reconciliation():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client

        db = await create_task_async_client()

        try:
            # 1. Find active subscription users (t2/t3)
            active_result = await db.table("profiles").select(
                "id, tier, email, subscription_status"
            ).in_(
                "tier", ["t2", "t3"]
            ).eq(
                "subscription_status", "active"
            ).execute()

            if not active_result.data:
                logger.info("[Reconciliation] No active subscribers found")
                return {"checked": 0, "anomalies": []}

            anomalies = []
            checked = 0

            for user in active_result.data:
                checked += 1
                user_id = user["id"]
                tier = user["tier"]

                # 2. Check last monthly_reset transaction
                tx_result = await db.table("credit_transactions").select(
                    "created_at"
                ).eq(
                    "user_id", user_id
                ).eq(
                    "transaction_type", "monthly_reset"
                ).order(
                    "created_at", desc=True
                ).limit(1).execute()

                if not tx_result.data:
                    # No monthly_reset ever — anomaly if subscription is active
                    anomalies.append({
                        "user_id": user_id,
                        "tier": tier,
                        "email": user.get("email"),
                        "reason": "no_monthly_reset_found",
                        "last_reset": None,
                    })
                    continue

                last_reset_str = tx_result.data[0]["created_at"]
                from datetime import datetime as dt
                try:
                    last_reset = dt.fromisoformat(last_reset_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue

                # 3. Check if last reset is older than 32 days
                age_days = (datetime.now(timezone.utc) - last_reset).days
                if age_days > 32:
                    anomalies.append({
                        "user_id": user_id,
                        "tier": tier,
                        "email": user.get("email"),
                        "reason": "stale_monthly_reset",
                        "last_reset": last_reset_str,
                        "days_since_reset": age_days,
                    })

            return {"checked": checked, "anomalies": anomalies}

        finally:
            if hasattr(db, 'aclose'):
                await db.aclose()
                logger.info("[DB] Reconciliation async client closed")

    try:
        result = asyncio.run(_async_credit_reconciliation())
        checked = result["checked"]
        anomalies = result["anomalies"]

        if anomalies:
            logger.warning(
                f"[{datetime.now()}] ⚠️ Credit reconciliation found {len(anomalies)} anomalies "
                f"out of {checked} active subscribers"
            )
            for a in anomalies:
                logger.warning(
                    f"  [ANOMALY] user={a['user_id']} tier={a['tier']} "
                    f"reason={a['reason']} last_reset={a.get('last_reset')} "
                    f"days={a.get('days_since_reset', 'N/A')}"
                )

            # Send Sentry alert for anomalies
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f"Credit reconciliation: {len(anomalies)} anomalies found",
                    level="warning",
                    extras={"anomalies": anomalies, "checked": checked},
                )
            except Exception:
                pass  # Sentry not configured is OK
        else:
            logger.info(
                f"[{datetime.now()}] ✅ Credit reconciliation complete: "
                f"{checked} subscribers checked, no anomalies"
            )
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Credit reconciliation failed: {e}", exc_info=True)


def init_scheduler():
    """
    Initialize and start the scheduler
     FastAPI 
    """
    # Only run scheduler in production or if explicitly enabled
    enable_scheduler = os.environ.get("ENABLE_SCHEDULER", "true").lower() == "true"
    
    if not enable_scheduler:
        logger.info("📅 Scheduler disabled (ENABLE_SCHEDULER != true)")
        return
    
    # Hourly task - run at minute 5 of every hour
    scheduler.add_job(
        run_hourly_aggregation,
        CronTrigger(minute=5),  # Every hour at :05
        id="hourly_aggregation",
        replace_existing=True,
        misfire_grace_time=300  # 5 minutes grace period
    )
    
    # Daily task - run at 2:00 AM UTC
    scheduler.add_job(
        run_daily_aggregation,
        CronTrigger(hour=2, minute=0),  # 2:00 AM UTC
        id="daily_aggregation",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )
    
    # v3.18: Storage cleanup task - run at 3:00 AM UTC
    scheduler.add_job(
        run_storage_cleanup,
        CronTrigger(hour=3, minute=0),  # 3:00 AM UTC
        id="storage_cleanup",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )

    # P3-022: Webhook retry task - run every hour at :15
    scheduler.add_job(
        run_webhook_retry,
        CronTrigger(minute=15),  # Every hour at :15
        id="webhook_retry",
        replace_existing=True,
        misfire_grace_time=600  # 10 minutes grace period
    )
    
    # v3.30: Daily maintenance task - run at 4:00 AM UTC
    scheduler.add_job(
        run_daily_maintenance,
        CronTrigger(hour=4, minute=0),  # 4:00 AM UTC
        id="daily_maintenance",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )
    
    # v3.30: Weekly maintenance task - run every Sunday at 5:00 AM UTC
    scheduler.add_job(
        run_weekly_maintenance,
        CronTrigger(day_of_week='sun', hour=5, minute=0),  # Sunday 5:00 AM UTC
        id="weekly_maintenance",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )

    # WS7d: Credit reconciliation task - run at 6:00 AM UTC daily
    scheduler.add_job(
        run_credit_reconciliation,
        CronTrigger(hour=6, minute=0),  # 6:00 AM UTC
        id="credit_reconciliation",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )

    # Start the scheduler
    scheduler.start()
    logger.info("📅 Scheduler started with jobs:")
    logger.info("   - Hourly aggregation: every hour at :05")
    logger.info("   - Daily aggregation: 2:00 AM UTC")
    logger.info("   - Storage cleanup: 3:00 AM UTC (v3.18)")
    logger.info("   - Daily maintenance: 4:00 AM UTC (v3.30)")
    logger.info("   - Weekly maintenance: Sunday 5:00 AM UTC (v3.30)")
    logger.info("   - Webhook retry: every hour at :15 (P3-022)")
    logger.info("   - Credit reconciliation: 6:00 AM UTC (WS7d)")

def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully
     FastAPI 
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("📅 Scheduler shutdown")

def run_aggregation_now(task_type: str = "all"):
    """
    Manually trigger aggregation (for admin API)
    （ admin API）
    """
    if task_type == "hourly":
        run_hourly_aggregation()
    elif task_type == "daily":
        run_daily_aggregation()
    else:
        run_daily_aggregation()
        run_hourly_aggregation()
    return {"status": "completed", "task_type": task_type}

