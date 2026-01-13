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
    """Run daily database maintenance tasks (v3.30)"""
    logger.info(f"[{datetime.now()}] 🔧 Starting daily maintenance tasks...")
    
    try:
        import asyncio
        from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler
        
        # Run maintenance in async context
        asyncio.run(MaintenanceScheduler.run_daily_maintenance())
        logger.info(f"[{datetime.now()}] ✅ Daily maintenance complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Daily maintenance failed: {e}")


def run_weekly_maintenance():
    """Run weekly database maintenance tasks (v3.30)"""
    logger.info(f"[{datetime.now()}] 🔧 Starting weekly maintenance tasks...")
    
    try:
        import asyncio
        from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler
        
        # Run maintenance in async context
        asyncio.run(MaintenanceScheduler.run_weekly_maintenance())
        logger.info(f"[{datetime.now()}] ✅ Weekly maintenance complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Weekly maintenance failed: {e}")


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
    """Run webhook retry task (P3-022, v2.0 AsyncClient)"""
    logger.info(f"[{datetime.now()}] 🔄 Starting webhook retry task...")

    import asyncio

    async def _async_webhook_retry():
        """Async wrapper for webhook retry with AsyncClient"""
        from core.database import get_async_db_client
        from infrastructure.repositories import (
            SupabaseWebhookRepository,
            SupabaseUserRepository,
            SupabaseCreditRepository,
            SupabasePaymentRepository,
        )
        from domains.webhooks import ClerkWebhookService, StripeWebhookService
        from domains.webhooks.webhook_retry_service import WebhookRetryService

        # Get AsyncClient
        db = await get_async_db_client()

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

    try:
        # Run async function
        result = asyncio.run(_async_webhook_retry())

        total = result["total"]
        logger.info(
            f"[{datetime.now()}] ✅ Webhook retry complete: "
            f"{total['processed']} processed, {total['failed']} failed, {total['skipped']} skipped"
        )
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Webhook retry failed: {e}", exc_info=True)

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

    # Start the scheduler
    scheduler.start()
    logger.info("📅 Scheduler started with jobs:")
    logger.info("   - Hourly aggregation: every hour at :05")
    logger.info("   - Daily aggregation: 2:00 AM UTC")
    logger.info("   - Storage cleanup: 3:00 AM UTC (v3.18)")
    logger.info("   - Daily maintenance: 4:00 AM UTC (v3.30)")
    logger.info("   - Weekly maintenance: Sunday 5:00 AM UTC (v3.30)")
    logger.info("   - Webhook retry: every hour at :15 (P3-022)")

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

