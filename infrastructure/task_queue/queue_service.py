"""
Task Queue Service
任务队列服务

Handles task enqueueing and management using Redis Queue (RQ).
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from redis import Redis
from rq import Queue
from rq.job import Job

from core.cache.redis_provider import get_redis_client, REDIS_URL

logger = logging.getLogger(__name__)

# Queue names with priority levels
QUEUE_HIGH = "high"
QUEUE_DEFAULT = "default"
QUEUE_LOW = "low"

# Task timeout configuration (seconds)
TASK_TIMEOUT_IMAGE = 300  # 5 minutes for image generation
TASK_TIMEOUT_EXPORT = 600  # 10 minutes for PDF/ZIP export
TASK_TIMEOUT_DEFAULT = 120  # 2 minutes default

# Priority mapping: tier -> queue
TIER_PRIORITY = {
    "t3": QUEUE_HIGH,
    "t2": QUEUE_DEFAULT,
    "t1": QUEUE_LOW,
}


class TaskQueueService:
    """
    Manages task queueing and status tracking.
    """
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._queues: Dict[str, Queue] = {}
        self._initialized = False
    
    def _ensure_initialized(self) -> bool:
        """
        Lazy initialization of Redis connection and queues.
        """
        if self._initialized:
            return True
        
        self._redis = get_redis_client()
        if not self._redis:
            logger.warning("[TaskQueue] Redis not available, queue disabled")
            return False
        
        try:
            # Create queues with different priorities
            # Workers will listen to queues in order: high, default, low
            self._queues = {
                QUEUE_HIGH: Queue(QUEUE_HIGH, connection=self._redis),
                QUEUE_DEFAULT: Queue(QUEUE_DEFAULT, connection=self._redis),
                QUEUE_LOW: Queue(QUEUE_LOW, connection=self._redis),
            }
            self._initialized = True
            logger.info("[TaskQueue] ✅ Initialized with 3 priority queues")
            return True
        except Exception as e:
            logger.error(f"[TaskQueue] ❌ Initialization failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if queue service is available."""
        return self._ensure_initialized()
    
    def _get_queue(self, tier: str = "t1") -> Optional[Queue]:
        """Get appropriate queue based on user tier."""
        if not self._ensure_initialized():
            return None
        
        queue_name = TIER_PRIORITY.get(tier.lower(), QUEUE_DEFAULT)
        return self._queues.get(queue_name)
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        random_part = uuid.uuid4().hex[:8]
        return f"task_{timestamp}_{random_part}"
    
    def enqueue_image_generation(
        self,
        user_id: str,
        params: Dict[str, Any],
        tier: str = "t1",
        idempotency_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Enqueue image generation task.
        
        Args:
            user_id: User ID
            params: Generation parameters
            tier: User tier for priority
            idempotency_key: Optional key for deduplication
        
        Returns:
            task_id if enqueued, None if failed
        """
        if not self._ensure_initialized():
            logger.error("[TaskQueue] Cannot enqueue: service not available")
            return None
        
        # Generate or use provided task ID
        task_id = idempotency_key or self._generate_task_id()
        
        # Check for existing task (idempotency)
        existing_key = f"task:{task_id}:status"
        if self._redis.exists(existing_key):
            logger.info(f"[TaskQueue] Task {task_id} already exists (idempotent)")
            return task_id
        
        # Prepare task data
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "params": params,
            "tier": tier,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Get appropriate queue
        queue = self._get_queue(tier)
        if not queue:
            return None
        
        try:
            # Import handler function (avoid circular imports)
            from .task_handlers import execute_image_generation
            
            # Enqueue job
            job = queue.enqueue(
                execute_image_generation,
                task_data,
                job_id=task_id,
                job_timeout=TASK_TIMEOUT_IMAGE,
                result_ttl=86400,  # Keep result for 24 hours
                failure_ttl=86400,  # Keep failed job for 24 hours
            )
            
            # Initialize status in Redis
            self._redis.hset(existing_key, mapping={
                "status": "queued",
                "progress": "0",
                "current_step": "0",
                "total_steps": str(len(params.get("prompts", [])) * params.get("num_images", 1)),
                "message": "Task queued",
                "created_at": task_data["created_at"],
            })
            self._redis.expire(existing_key, 86400)  # 24 hour TTL
            
            logger.info(f"[TaskQueue] ✅ Enqueued task {task_id} to {queue.name} queue")
            return task_id
            
        except Exception as e:
            logger.error(f"[TaskQueue] ❌ Failed to enqueue task: {e}")
            return None
    
    def get_job(self, task_id: str) -> Optional[Job]:
        """Get RQ job by task ID."""
        if not self._ensure_initialized():
            return None
        
        try:
            return Job.fetch(task_id, connection=self._redis)
        except Exception:
            return None
    
    def cancel_task(self, task_id: str, user_id: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_id: Task ID
            user_id: User ID (for authorization)
        
        Returns:
            True if cancelled, False otherwise
        """
        if not self._ensure_initialized():
            return False
        
        try:
            job = self.get_job(task_id)
            if not job:
                return False
            
            # Verify ownership
            job_data = job.args[0] if job.args else {}
            if job_data.get("user_id") != user_id:
                logger.warning(f"[TaskQueue] Cancel denied: user mismatch for {task_id}")
                return False
            
            # Only cancel if not started
            if job.get_status() in ['queued', 'scheduled']:
                job.cancel()
                
                # Update status
                status_key = f"task:{task_id}:status"
                self._redis.hset(status_key, mapping={
                    "status": "cancelled",
                    "message": "Task cancelled by user",
                })
                
                logger.info(f"[TaskQueue] Task {task_id} cancelled")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[TaskQueue] Cancel failed: {e}")
            return False
    
    def enqueue_export_task(
        self,
        user_id: str,
        project_id: str,
        export_type: str,
        tier: str = "t1",
        idempotency_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Enqueue PDF/ZIP export task.

        Args:
            user_id: User ID
            project_id: Project ID to export
            export_type: "pdf" or "zip"
            tier: User tier for priority routing
            idempotency_key: Optional key for deduplication

        Returns:
            task_id if enqueued, None if failed
        """
        if not self._ensure_initialized():
            logger.error("[TaskQueue] Cannot enqueue: service not available")
            return None

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Check for existing task with same idempotency key
        if idempotency_key:
            # Check Redis for existing task
            existing_key = f"idempotency:{idempotency_key}"
            existing_task_id = self._redis.get(existing_key)
            if existing_task_id:
                logger.info(f"[TaskQueue] Export task already exists (idempotent): {existing_task_id}")
                return existing_task_id.decode('utf-8') if isinstance(existing_task_id, bytes) else existing_task_id

            # Store idempotency mapping (24 hour TTL)
            self._redis.setex(existing_key, 86400, task_id)

        # Get appropriate queue
        queue = self._get_queue(tier)
        if not queue:
            return None

        try:
            # Import handler function (avoid circular imports)
            from .export_handler import execute_export_task

            # Enqueue job
            job = queue.enqueue(
                execute_export_task,
                task_id=task_id,
                user_id=user_id,
                project_id=project_id,
                export_type=export_type,
                tier=tier,
                job_id=task_id,
                job_timeout=TASK_TIMEOUT_EXPORT,
                result_ttl=86400,  # Keep result for 24 hours
                failure_ttl=86400,  # Keep failed job for 24 hours
            )

            # Initialize status in Redis
            status_key = f"task:{task_id}:status"
            self._redis.hset(status_key, mapping={
                "status": "queued",
                "progress": "0",
                "current_step": "0",
                "total_steps": "4",  # PDF: 4 steps, ZIP: 5 steps
                "message": f"{export_type.upper()} export queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            self._redis.expire(status_key, 86400)  # 24 hour TTL

            queue_name = TIER_PRIORITY.get(tier.lower(), QUEUE_DEFAULT)
            logger.info(f"[TaskQueue] ✅ Enqueued {export_type} export task {task_id} to {queue_name} queue")
            return task_id

        except Exception as e:
            logger.error(f"[TaskQueue] ❌ Failed to enqueue export task: {e}")
            return None

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics for monitoring."""
        if not self._ensure_initialized():
            return {"available": False}

        stats = {"available": True, "queues": {}}

        for name, queue in self._queues.items():
            try:
                stats["queues"][name] = {
                    "pending": len(queue),
                    "failed": len(queue.failed_job_registry),
                    "finished": len(queue.finished_job_registry),
                }
            except Exception as e:
                stats["queues"][name] = {"error": str(e)}

        return stats


# Global singleton
task_queue = TaskQueueService()
