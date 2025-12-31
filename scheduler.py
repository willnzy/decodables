"""
Background Scheduler for Data Aggregation Tasks


 FastAPI ， Railway 
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
    """Run hourly aggregation tasks"""
    logger.info(f"[{datetime.now()}] 🕐 Starting hourly aggregation...")
    try:
        from scheduled_tasks.aggregate_stats import run_hourly_tasks
        run_hourly_tasks()
        logger.info(f"[{datetime.now()}] ✅ Hourly aggregation complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Hourly aggregation failed: {e}")

def run_daily_aggregation():
    """Run daily aggregation tasks"""
    logger.info(f"[{datetime.now()}] 📅 Starting daily aggregation...")
    try:
        from scheduled_tasks.aggregate_stats import run_daily_tasks
        run_daily_tasks()
        logger.info(f"[{datetime.now()}] ✅ Daily aggregation complete")
    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Daily aggregation failed: {e}")

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
    
    # Start the scheduler
    scheduler.start()
    logger.info("📅 Scheduler started with jobs:")
    logger.info("   - Hourly aggregation: every hour at :05")
    logger.info("   - Daily aggregation: 2:00 AM UTC")

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

