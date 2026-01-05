"""
Progress Tracker Service
进度追踪服务

Tracks and broadcasts task progress via Redis.
Used by both workers (to update) and API (to read/broadcast).
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone

from services.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Redis key patterns
STATUS_KEY = "task:{task_id}:status"
PUBSUB_CHANNEL = "task:progress:{task_id}"


class ProgressTracker:
    """
    Manages task progress tracking via Redis.
    
    Features:
    - Atomic status updates
    - Redis PubSub for real-time notifications
    - Progress history
    """
    
    def __init__(self):
        self._redis = None
        self._pubsub = None
        self._subscribers: Dict[str, List[Callable]] = {}
    
    def _ensure_redis(self):
        """Lazy Redis initialization."""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis
    
    def update(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update task progress.
        
        Args:
            task_id: Task ID
            status: Task status (pending, queued, processing, completed, failed, cancelled)
            progress: Progress percentage (0-100)
            current_step: Current step number
            total_steps: Total steps
            message: Human-readable progress message
            result: Final result data (for completed tasks)
            error: Error message (for failed tasks)
        
        Returns:
            True if update successful
        """
        redis = self._ensure_redis()
        if not redis:
            logger.warning("[ProgressTracker] Redis not available")
            return False
        
        try:
            key = STATUS_KEY.format(task_id=task_id)
            
            # Build update data
            update_data = {}
            if status is not None:
                update_data["status"] = status
            if progress is not None:
                update_data["progress"] = str(progress)
            if current_step is not None:
                update_data["current_step"] = str(current_step)
            if total_steps is not None:
                update_data["total_steps"] = str(total_steps)
            if message is not None:
                update_data["message"] = message
            if result is not None:
                update_data["result"] = json.dumps(result)
            if error is not None:
                update_data["error"] = error
            
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update Redis hash
            redis.hset(key, mapping=update_data)
            
            # Publish progress update for WebSocket subscribers
            channel = PUBSUB_CHANNEL.format(task_id=task_id)
            pubsub_data = {
                "task_id": task_id,
                "type": "progress",
                **{k: v for k, v in update_data.items() if k != "result"},
            }
            if result is not None:
                pubsub_data["result"] = result  # Include result in pubsub
            
            redis.publish(channel, json.dumps(pubsub_data))
            
            logger.debug(f"[ProgressTracker] Updated {task_id}: {update_data}")
            return True
            
        except Exception as e:
            logger.error(f"[ProgressTracker] Update failed: {e}")
            return False
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current task status.
        
        Args:
            task_id: Task ID
        
        Returns:
            Status dict or None if not found
        """
        redis = self._ensure_redis()
        if not redis:
            return None
        
        try:
            key = STATUS_KEY.format(task_id=task_id)
            data = redis.hgetall(key)
            
            if not data:
                return None
            
            # Parse numeric fields
            result = {
                "task_id": task_id,
                "status": data.get("status", "unknown"),
                "progress": int(data.get("progress", 0)),
                "current_step": int(data.get("current_step", 0)),
                "total_steps": int(data.get("total_steps", 0)),
                "message": data.get("message", ""),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }
            
            # Parse JSON fields
            if "result" in data:
                try:
                    result["result"] = json.loads(data["result"])
                except json.JSONDecodeError:
                    result["result"] = data["result"]
            
            if "error" in data:
                result["error"] = data["error"]
            
            return result
            
        except Exception as e:
            logger.error(f"[ProgressTracker] Get status failed: {e}")
            return None
    
    def mark_started(self, task_id: str, worker_id: str = None):
        """Mark task as started processing."""
        update = {
            "status": "processing",
            "message": "Processing started",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        if worker_id:
            update["worker_id"] = worker_id
        
        redis = self._ensure_redis()
        if redis:
            key = STATUS_KEY.format(task_id=task_id)
            redis.hset(key, mapping=update)
            
            # Publish start event
            channel = PUBSUB_CHANNEL.format(task_id=task_id)
            redis.publish(channel, json.dumps({
                "task_id": task_id,
                "type": "started",
                **update
            }))
    
    def mark_completed(self, task_id: str, result: Dict[str, Any]):
        """Mark task as completed with result."""
        self.update(
            task_id=task_id,
            status="completed",
            progress=100,
            message="Generation complete",
            result=result
        )
        
        # Set expiration for cleanup
        redis = self._ensure_redis()
        if redis:
            key = STATUS_KEY.format(task_id=task_id)
            redis.expire(key, 86400)  # 24 hours
    
    def mark_failed(self, task_id: str, error: str, error_code: str = None):
        """Mark task as failed with error."""
        redis = self._ensure_redis()
        if redis:
            key = STATUS_KEY.format(task_id=task_id)
            update = {
                "status": "failed",
                "error": error,
                "message": f"Failed: {error}",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if error_code:
                update["error_code"] = error_code
            
            redis.hset(key, mapping=update)
            
            # Publish failure event
            channel = PUBSUB_CHANNEL.format(task_id=task_id)
            redis.publish(channel, json.dumps({
                "task_id": task_id,
                "type": "failed",
                **update
            }))
    
    def increment_step(
        self,
        task_id: str,
        step_result: Any = None,
        message: str = None
    ):
        """
        Increment current step and update progress.
        
        Args:
            task_id: Task ID
            step_result: Optional result for this step
            message: Optional progress message
        """
        redis = self._ensure_redis()
        if not redis:
            return
        
        try:
            key = STATUS_KEY.format(task_id=task_id)
            
            # Atomic increment
            new_step = redis.hincrby(key, "current_step", 1)
            total_steps = int(redis.hget(key, "total_steps") or 1)
            
            # Calculate progress percentage
            progress = min(100, int((new_step / total_steps) * 100))
            
            # Update progress
            update = {
                "progress": str(progress),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if message:
                update["message"] = message
            else:
                update["message"] = f"Generating {new_step}/{total_steps}..."
            
            redis.hset(key, mapping=update)
            
            # Publish progress
            channel = PUBSUB_CHANNEL.format(task_id=task_id)
            pubsub_data = {
                "task_id": task_id,
                "type": "progress",
                "current_step": new_step,
                "total_steps": total_steps,
                "progress": progress,
                "message": update["message"],
            }
            if step_result:
                pubsub_data["step_result"] = step_result
            
            redis.publish(channel, json.dumps(pubsub_data))
            
        except Exception as e:
            logger.error(f"[ProgressTracker] Increment step failed: {e}")
    
    def delete(self, task_id: str):
        """Delete task status (cleanup)."""
        redis = self._ensure_redis()
        if redis:
            key = STATUS_KEY.format(task_id=task_id)
            redis.delete(key)


# Global singleton
progress_tracker = ProgressTracker()
