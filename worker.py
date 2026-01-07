"""
Background Worker Entry Point
后台 Worker 进程入口

Runs RQ workers to process background tasks.

Usage:
    # Single worker (development)
    python worker.py
    
    # Multiple workers (production via Procfile)
    worker: python worker.py

Environment Variables:
    - REDIS_URL: Redis connection URL
    - WORKER_QUEUES: Comma-separated queue names (default: high,default,low)
    - WORKER_NAME: Custom worker name (optional)
    - WORKER_MAX_JOBS: Max jobs before restart (default: 100, Railway memory optimization)
    - WORKER_JOB_TIMEOUT: Job timeout in seconds (default: 600)
"""

import os
import sys
import signal
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redis import Redis
from rq import Worker, Queue
from rq.job import Job

from core.cache.redis_provider import get_redis_client, REDIS_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("worker")

# Queue configuration
DEFAULT_QUEUES = ["high", "default", "low"]

# Worker performance configuration (Railway optimized)
WORKER_MAX_JOBS = int(os.environ.get("WORKER_MAX_JOBS", "100"))  # Restart after N jobs to free memory
WORKER_JOB_TIMEOUT = int(os.environ.get("WORKER_JOB_TIMEOUT", "600"))  # 10 minutes default


def get_worker_queues() -> list:
    """Get queue names from environment or use defaults."""
    queues_env = os.environ.get("WORKER_QUEUES", "")
    if queues_env:
        return [q.strip() for q in queues_env.split(",") if q.strip()]
    return DEFAULT_QUEUES


def get_worker_name() -> str:
    """Generate unique worker name."""
    custom_name = os.environ.get("WORKER_NAME", "")
    if custom_name:
        return custom_name
    
    pid = os.getpid()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"worker_{timestamp}_{pid}"


def handle_job_exception(job: Job, exc_type, exc_value, traceback):
    """
    Custom exception handler for failed jobs.
    
    Updates task status in Redis and database.
    """
    task_id = job.id
    logger.error(f"[Worker] Job {task_id} failed: {exc_type.__name__}: {exc_value}")
    
    # Update progress tracker
    try:
        from infrastructure.task_queue.progress_tracker import progress_tracker
        progress_tracker.mark_failed(
            task_id,
            error=str(exc_value),
            error_code=exc_type.__name__
        )
    except Exception as e:
        logger.warning(f"[Worker] Failed to update progress tracker: {e}")
    
    # Update database task record
    try:
        from supabase import create_client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            if not supabase_url.endswith('/'):
                supabase_url = supabase_url + '/'
            
            supabase = create_client(supabase_url, supabase_key)
            supabase.table("generation_tasks").update({
                "status": "failed",
                "error_message": str(exc_value),
                "error_code": exc_type.__name__,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("task_id", task_id).execute()
    except Exception as e:
        logger.warning(f"[Worker] Failed to update database: {e}")


def handle_job_success(job: Job, queue: Queue, result):
    """
    Custom success handler for completed jobs.
    """
    task_id = job.id
    logger.info(f"[Worker] Job {task_id} completed successfully")


class MakeDecodablesWorker(Worker):
    """
    Custom RQ Worker with additional hooks.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logger
    
    def perform_job(self, job, queue):
        """Override to add custom logging."""
        task_id = job.id
        self.log.info(f"[Worker] Starting job {task_id} from queue '{queue.name}'")
        
        start_time = datetime.now(timezone.utc)
        result = super().perform_job(job, queue)
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        self.log.info(f"[Worker] Job {task_id} finished in {duration:.2f}s")
        
        return result


def run_worker():
    """
    Main entry point for running the worker.
    """
    # Get Redis connection
    redis_conn = get_redis_client()
    if not redis_conn:
        logger.error("[Worker] ❌ Redis not available, cannot start worker")
        sys.exit(1)
    
    # Get queue names
    queue_names = get_worker_queues()
    worker_name = get_worker_name()
    
    logger.info(f"[Worker] Starting worker '{worker_name}'")
    logger.info(f"[Worker] Listening on queues: {queue_names}")
    
    # Create queue objects
    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    
    # Create and run worker with Railway optimizations
    worker = MakeDecodablesWorker(
        queues,
        connection=redis_conn,
        name=worker_name,
        exception_handlers=[handle_job_exception],
        # Railway memory optimization: restart worker after max_jobs to prevent memory leaks
        max_jobs=WORKER_MAX_JOBS,
        # Job timeout to prevent hanging tasks
        job_monitoring_interval=60,  # Check every 60s
    )
    
    # Handle graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info("[Worker] Received shutdown signal, finishing current job...")
        worker.request_stop(signum, frame)
    
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # Start worker
    logger.info("[Worker] ✅ Worker started successfully")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    run_worker()
