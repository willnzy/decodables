"""
Task Queue Service
任务队列服务

Provides:
- Async task queueing with Redis Queue (RQ)
- Progress tracking via Redis
- Task status management
- Priority-based scheduling

Usage:
    from infrastructure.task_queue import task_queue, progress_tracker
    
    # Enqueue a task
    task_id = await task_queue.enqueue_image_generation(user_id, params)
    
    # Update progress
    progress_tracker.update(task_id, progress=50, message="Generating 4/8...")
    
    # Get status
    status = progress_tracker.get_status(task_id)
"""

from .queue_service import TaskQueueService, task_queue
from .progress_tracker import ProgressTracker, progress_tracker
from .task_handlers import ImageGenerationHandler

__all__ = [
    'TaskQueueService',
    'task_queue',
    'ProgressTracker', 
    'progress_tracker',
    'ImageGenerationHandler',
]
