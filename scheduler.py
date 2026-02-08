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

# WS-19: Default timeout for async scheduler tasks (seconds)
SCHEDULER_TASK_TIMEOUT = int(os.environ.get("SCHEDULER_TASK_TIMEOUT", "300"))


def _run_async_with_timeout(coro_func, task_name: str, timeout: int = SCHEDULER_TASK_TIMEOUT):
    """
    WS-19: Execute an async coroutine with timeout protection and failure alerting.

    Wraps asyncio.run() with asyncio.wait_for() to prevent tasks from hanging
    indefinitely. On failure or timeout, logs structured alerts.

    Args:
        coro_func: Async function that returns a coroutine
        task_name: Human-readable task name for logging
        timeout: Max seconds before task is terminated
    """
    import asyncio

    async def _with_timeout():
        return await asyncio.wait_for(coro_func(), timeout=timeout)

    try:
        return asyncio.run(_with_timeout())
    except asyncio.TimeoutError:
        logger.critical(
            f"[{datetime.now(timezone.utc).isoformat()}] ⏰ TIMEOUT: Task '{task_name}' "
            f"exceeded {timeout}s limit and was terminated",
            extra={"task": task_name, "error": "timeout", "timeout_seconds": timeout}
        )
        # Send Sentry alert for timeout
        try:
            import sentry_sdk
            sentry_sdk.capture_message(
                f"Scheduler task timeout: {task_name} exceeded {timeout}s",
                level="error",
            )
        except Exception:
            pass
        return None
    except Exception as e:
        logger.error(
            f"[{datetime.now(timezone.utc).isoformat()}] ❌ Task '{task_name}' failed: {e}",
            exc_info=True,
            extra={"task": task_name, "error": str(e)}
        )
        # Send Sentry alert for failure
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
        except Exception:
            pass
        return None

# Scheduler instance
scheduler = BackgroundScheduler()

def run_hourly_aggregation():
    """Run hourly aggregation tasks (both legacy and new ETL)"""
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🕐 Starting hourly aggregation...")
    
    # Run new metrics ETL (v3.12)
    try:
        from application.services.metrics import run_hourly_etl
        run_hourly_etl()
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Metrics ETL (hourly) complete")
    except Exception as e:
        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] ❌ Metrics ETL failed: {e}")

    # Run legacy aggregation for backwards compatibility
    try:
        from application.services.aggregators import run_hourly_tasks
        run_hourly_tasks()
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Legacy aggregation complete")
    except Exception as e:
        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] ❌ Legacy aggregation failed: {e}")

    # Run A/B experiment aggregation (v3.20)
    try:
        from application.services.experiments import run_hourly_experiment_tasks
        run_hourly_experiment_tasks()
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Experiment aggregation (hourly) complete")
    except Exception as e:
        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] ❌ Experiment aggregation failed: {e}")

def run_daily_aggregation():
    """Run daily aggregation tasks (both legacy and new ETL)"""
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 📅 Starting daily aggregation...")
    
    # Run new metrics ETL (v3.12) - industry-standard SaaS metrics
    try:
        from application.services.metrics import run_daily_etl
        run_daily_etl()
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Metrics ETL (daily) complete")
    except Exception as e:
        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] ❌ Metrics ETL failed: {e}")

    # Run legacy aggregation for backwards compatibility
    try:
        from application.services.aggregators import run_daily_tasks
        run_daily_tasks()
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Legacy aggregation complete")
    except Exception as e:
        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] ❌ Legacy aggregation failed: {e}")

    # Run A/B experiment daily tasks (v3.20)
    try:
        from application.services.experiments import run_daily_experiment_tasks
        run_daily_experiment_tasks()
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Experiment aggregation (daily) complete")
    except Exception as e:
        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] ❌ Experiment daily tasks failed: {e}")


def run_daily_maintenance():
    """
    Run daily database maintenance tasks (v3.30, v3.31 AsyncClient fix)

    IMPORTANT: Uses create_task_async_client() instead of get_async_db_client()
    to avoid "Event loop is closed" error. See docs/main/backend-architecture.md 1.3.1.3

    WS-19: Now uses _run_async_with_timeout for timeout protection.
    """
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🔧 Starting daily maintenance tasks...")

    async def _async_daily_maintenance():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client
        from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler

        db = await create_task_async_client()
        try:
            return await MaintenanceScheduler.run_daily_maintenance(db=db)
        finally:
            if hasattr(db, 'aclose'):
                await db.aclose()

    result = _run_async_with_timeout(_async_daily_maintenance, "daily_maintenance")
    if result:
        total_deleted = result.get('total_deleted', 0)
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Daily maintenance complete: {total_deleted} records deleted")


def run_weekly_maintenance():
    """
    Run weekly database maintenance tasks (v3.30, v3.31 AsyncClient fix)

    WS-19: Now uses _run_async_with_timeout for timeout protection.
    """
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🔧 Starting weekly maintenance tasks...")

    async def _async_weekly_maintenance():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client
        from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler

        db = await create_task_async_client()
        try:
            return await MaintenanceScheduler.run_weekly_maintenance(db=db)
        finally:
            if hasattr(db, 'aclose'):
                await db.aclose()

    result = _run_async_with_timeout(_async_weekly_maintenance, "weekly_maintenance")
    if result:
        total_deleted = result.get('total_deleted', 0)
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Weekly maintenance complete: {total_deleted} records deleted")


def run_storage_cleanup():
    """Run storage cleanup task (v3.18)"""
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🧹 Starting storage cleanup...")

    try:
        from infrastructure.tasks.storage_cleanup import run_storage_cleanup as do_cleanup
        result = do_cleanup()
        logger.info(f"[{datetime.now(timezone.utc).isoformat()}] ✅ Storage cleanup complete: {result.get('files_deleted', 0)} files deleted, {result.get('space_freed_mb', 0)} MB freed")
    except Exception as e:
        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] ❌ Storage cleanup failed: {e}")


def run_webhook_retry():
    """
    Run webhook retry task (P3-022, v2.0 AsyncClient)

    WS-19: Now uses _run_async_with_timeout for timeout protection.
    """
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🔄 Starting webhook retry task...")

    async def _async_webhook_retry():
        """Async wrapper for webhook retry with fresh AsyncClient"""
        from core.database import create_task_async_client
        from infrastructure.repositories import (
            SupabaseWebhookRepository,
            SupabaseUserRepository,
            SupabaseCreditRepository,
            SupabasePaymentRepository,
        )
        from domains.webhooks import StripeWebhookService
        from domains.webhooks.webhook_retry_service import WebhookRetryService

        db = await create_task_async_client()
        try:
            webhook_repo = SupabaseWebhookRepository(db)
            user_repo = SupabaseUserRepository(db)
            credit_repo = SupabaseCreditRepository(db)
            payment_repo = SupabasePaymentRepository(db)

            stripe_service = StripeWebhookService(user_repo, credit_repo, payment_repo)
            retry_service = WebhookRetryService(webhook_repo, stripe_service)

            return await retry_service.retry_all_failed_webhooks()
        finally:
            if hasattr(db, 'aclose'):
                await db.aclose()

    result = _run_async_with_timeout(_async_webhook_retry, "webhook_retry")
    if result:
        total = result["total"]
        logger.info(
            f"[{datetime.now(timezone.utc).isoformat()}] ✅ Webhook retry complete: "
            f"{total['processed']} processed, {total['failed']} failed, {total['skipped']} skipped"
        )

def run_webhook_events_cleanup():
    """
    GAP-008 Phase 4: Clean up processed webhook events older than 90 days.

    Schedule: Weekly Sunday 3:00 AM UTC.

    Deletes stripe_webhook_events records that are:
    - processed (processed_at IS NOT NULL)
    - older than 90 days from current UTC time

    This prevents unbounded growth of the webhook events table while
    maintaining audit trail for recent events.
    """
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🧹 Starting webhook events cleanup...")

    async def _async_webhook_cleanup():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client
        from datetime import timedelta

        db = await create_task_async_client()
        try:
            # Calculate cutoff date (90 days ago)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
            cutoff_iso = cutoff_date.isoformat()

            # Delete processed events older than 90 days
            result = await db.table("stripe_webhook_events").delete().lt(
                "processed_at", cutoff_iso
            ).not_.is_("processed_at", "null").execute()

            deleted_count = len(result.data) if result.data else 0
            return {"deleted_count": deleted_count, "cutoff_date": cutoff_iso}

        finally:
            if hasattr(db, 'aclose'):
                await db.aclose()
                logger.info("[DB] Webhook cleanup async client closed")

    # WS-19: Use timeout wrapper
    result = _run_async_with_timeout(_async_webhook_cleanup, "webhook_events_cleanup")
    if result:
        deleted_count = result["deleted_count"]
        cutoff_date = result["cutoff_date"]
        logger.info(
            f"[{datetime.now(timezone.utc).isoformat()}] ✅ Webhook events cleanup complete: "
            f"Deleted {deleted_count} processed events older than 90 days (cutoff: {cutoff_date})"
        )


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
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🔍 Starting credit reconciliation...")

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

    # WS-19: Use timeout wrapper
    result = _run_async_with_timeout(_async_credit_reconciliation, "credit_reconciliation")
    if result:
        checked = result["checked"]
        anomalies = result["anomalies"]

        if anomalies:
            logger.warning(
                f"[{datetime.now(timezone.utc).isoformat()}] ⚠️ Credit reconciliation found {len(anomalies)} anomalies "
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
                f"[{datetime.now(timezone.utc).isoformat()}] ✅ Credit reconciliation complete: "
                f"{checked} subscribers checked, no anomalies"
            )


def check_expired_trials():
    """
    SCHEDULER-002 / GAP-005: Check and expire overdue trials.

    Queries profiles where is_trial_active = TRUE and trial_end_date < NOW(),
    then updates is_trial_active = FALSE for each expired trial user.

    Schedule: Daily 1:00 AM UTC.

    WS-19: Uses _run_async_with_timeout for timeout protection.
    """
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 📋 Starting trial expiration check...")

    async def _async_check_expired_trials():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client

        db = await create_task_async_client()

        try:
            # Find expired trials: is_trial_active = TRUE AND trial_end_date < NOW()
            result = await db.table("profiles").select(
                "id, email, tier, trial_end_date"
            ).eq(
                "is_trial_active", True
            ).lt(
                "trial_end_date", datetime.now(timezone.utc).isoformat()
            ).execute()

            expired_users = result.data or []

            if not expired_users:
                logger.info("[trial_expiration] No expired trials found")
                return {"expired_count": 0}

            # Batch update: set is_trial_active = FALSE for each expired trial user
            expired_count = 0
            for user in expired_users:
                user_id = user["id"]
                try:
                    await db.table("profiles").update({
                        "is_trial_active": False,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq(
                        "id", user_id
                    ).execute()
                    expired_count += 1
                except Exception as e:
                    logger.error(
                        f"[trial_expiration] Failed to expire trial for user {user_id}: {e}"
                    )

            return {"expired_count": expired_count}

        finally:
            if hasattr(db, 'aclose'):
                await db.aclose()
                logger.info("[DB] Trial expiration async client closed")

    # WS-19: Use timeout wrapper
    result = _run_async_with_timeout(_async_check_expired_trials, "check_expired_trials", timeout=120)
    if result:
        expired_count = result.get("expired_count", 0)
        logger.info(
            f"[{datetime.now(timezone.utc).isoformat()}] ✅ Trial expiration check complete: "
            f"Expired {expired_count} trials"
        )


def reconcile_subscription_pauses():
    """
    SCHEDULER-003: Auto-resume expired subscription pauses.

    Finds paused subscriptions where pause_resume_at < NOW() and
    auto-resumes them by setting subscription_status = 'active'
    and clearing pause metadata.

    Schedule: Daily 2:00 AM UTC.

    WS-19: Uses _run_async_with_timeout for timeout protection.
    """
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] 🔄 Starting subscription pause reconciliation...")

    async def _async_reconcile_pauses():
        """Async wrapper with fresh AsyncClient"""
        from core.database import create_task_async_client

        db = await create_task_async_client()

        try:
            # Find paused subscriptions past resume date
            now = datetime.now(timezone.utc).isoformat()
            result = await db.table("profiles").select(
                "id, email, tier, subscription_status, pause_resume_at"
            ).eq(
                "subscription_status", "paused"
            ).lt(
                "pause_resume_at", now
            ).execute()

            expired_pauses = result.data or []

            if not expired_pauses:
                logger.info("[pause_reconcile] No expired pauses found")
                return {"resumed_count": 0}

            # Batch update: resume subscriptions
            resumed_count = 0
            for user in expired_pauses:
                user_id = user["id"]
                try:
                    await db.table("profiles").update({
                        "subscription_status": "active",
                        "pause_reason": None,
                        "pause_resume_at": None,
                        "updated_at": now,
                    }).eq(
                        "id", user_id
                    ).execute()
                    resumed_count += 1
                except Exception as e:
                    logger.error(
                        f"[pause_reconcile] Failed to resume subscription for user {user_id}: {e}"
                    )

            return {"resumed_count": resumed_count}

        finally:
            if hasattr(db, 'aclose'):
                await db.aclose()
                logger.info("[DB] Pause reconciliation async client closed")

    # WS-19: Use timeout wrapper
    result = _run_async_with_timeout(_async_reconcile_pauses, "reconcile_subscription_pauses", timeout=120)
    if result:
        resumed_count = result.get("resumed_count", 0)
        logger.info(
            f"[{datetime.now(timezone.utc).isoformat()}] ✅ Subscription pause reconciliation complete: "
            f"Auto-resumed {resumed_count} paused subscriptions"
        )


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

    # GAP-008 Phase 4: Webhook events cleanup - run every Sunday at 3:00 AM UTC
    scheduler.add_job(
        run_webhook_events_cleanup,
        CronTrigger(day_of_week='sun', hour=3, minute=0),  # Sunday 3:00 AM UTC
        id="webhook_events_cleanup",
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

    # SCHEDULER-002 / GAP-005: Trial expiration check - run at 1:00 AM UTC daily
    scheduler.add_job(
        check_expired_trials,
        CronTrigger(hour=1, minute=0),  # 1:00 AM UTC
        id="check_expired_trials",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )

    # SCHEDULER-003 (Phase 5+): Subscription pause reconciliation - run at 2:00 AM UTC daily
    scheduler.add_job(
        reconcile_subscription_pauses,
        CronTrigger(hour=2, minute=0),  # 2:00 AM UTC
        id="reconcile_subscription_pauses",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )

    # Start the scheduler
    scheduler.start()
    logger.info("📅 Scheduler started with jobs:")
    logger.info("   - Hourly aggregation: every hour at :05")
    logger.info("   - Trial expiration check: 1:00 AM UTC (SCHEDULER-002 / GAP-005)")
    logger.info("   - Subscription pause reconciliation: 2:00 AM UTC (SCHEDULER-003 Phase 5+)")
    logger.info("   - Daily aggregation: 2:00 AM UTC")
    logger.info("   - Storage cleanup: 3:00 AM UTC (v3.18)")
    logger.info("   - Daily maintenance: 4:00 AM UTC (v3.30)")
    logger.info("   - Webhook events cleanup: Sunday 3:00 AM UTC (GAP-008 Phase 4)")
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

