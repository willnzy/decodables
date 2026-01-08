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


def run_storage_cleanup():
    """Run storage cleanup task (v3.18)"""
    logger.info(f"[{datetime.now()}] 🧹 Starting storage cleanup...")
    
    try:
        from infrastructure.tasks.storage_cleanup import run_storage_cleanup as do_cleanup
        result = do_cleanup()
        logger.info(f"[{datetime.now()}] ✅ Storage cleanup complete: {result.get('files_deleted', 0)} files deleted, {result.get('space_freed_mb', 0)} MB freed")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Storage cleanup failed: {e}")

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
    
    # Start the scheduler
    scheduler.start()
    logger.info("📅 Scheduler started with jobs:")
    logger.info("   - Hourly aggregation: every hour at :05")
    logger.info("   - Daily aggregation: 2:00 AM UTC")
    logger.info("   - Storage cleanup: 3:00 AM UTC (v3.18)")

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

