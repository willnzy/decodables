"""
Task Logger Module (v3.15)

Provides unified logging for scheduled tasks to enable monitoring.

Usage:
    from task_logger import TaskLogger
    
    with TaskLogger('campaign_scheduler', 'full') as logger:
        # Do work...
        logger.set_result({'campaigns_activated': 5})
"""

import os
import sys
import socket
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from services.db_service import supabase


class TaskLogger:
    """
    Context manager for logging scheduled task execution.
    
    Automatically tracks:
    - Start time
    - End time
    - Duration
    - Status (success/failed)
    - Error information
    """
    
    def __init__(self, task_name: str, task_type: str = 'full'):
        """
        Initialize task logger.
        
        Args:
            task_name: Name of the task (e.g., 'campaign_scheduler')
            task_type: Type of run (e.g., 'full', 'campaigns', 'hourly')
        """
        self.task_name = task_name
        self.task_type = task_type
        self.log_id: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.result_summary: Dict[str, Any] = {}
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
    
    def __enter__(self):
        """Start task logging."""
        self.started_at = datetime.now(timezone.utc)
        
        try:
            result = supabase.table('scheduled_task_logs').insert({
                'task_name': self.task_name,
                'task_type': self.task_type,
                'started_at': self.started_at.isoformat(),
                'status': 'running',
                'hostname': self.hostname,
                'pid': self.pid,
            }).execute()
            
            if result.data:
                self.log_id = result.data[0]['id']
        except Exception as e:
            # Don't fail the task if logging fails
            print(f"[TaskLogger] Warning: Failed to create log entry: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete task logging."""
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - self.started_at).total_seconds() * 1000)
        
        if exc_type is not None:
            # Task failed with exception
            status = 'failed'
            error_message = str(exc_val)
            error_stack = ''.join(traceback.format_tb(exc_tb))
        else:
            status = 'success'
            error_message = None
            error_stack = None
        
        if self.log_id:
            try:
                supabase.table('scheduled_task_logs').update({
                    'completed_at': completed_at.isoformat(),
                    'duration_ms': duration_ms,
                    'status': status,
                    'result_summary': self.result_summary,
                    'error_message': error_message,
                    'error_stack': error_stack,
                }).eq('id', self.log_id).execute()
            except Exception as e:
                print(f"[TaskLogger] Warning: Failed to update log entry: {e}")
        
        # Don't suppress exceptions
        return False
    
    def set_result(self, summary: Dict[str, Any]):
        """
        Set the result summary for this task run.
        
        Args:
            summary: Dictionary with task-specific results
        """
        self.result_summary = summary
    
    def add_result(self, key: str, value: Any):
        """
        Add a single result to the summary.
        
        Args:
            key: Result key
            value: Result value
        """
        self.result_summary[key] = value


@contextmanager
def task_context(task_name: str, task_type: str = 'full'):
    """
    Convenience context manager for task logging.
    
    Usage:
        with task_context('my_task', 'hourly') as ctx:
            # Do work...
            ctx['result'] = {'processed': 100}
    """
    context = {'result': {}}
    logger = TaskLogger(task_name, task_type)
    
    with logger:
        try:
            yield context
        finally:
            logger.set_result(context.get('result', {}))


def log_task_run(
    task_name: str,
    task_type: str,
    status: str,
    result_summary: Dict[str, Any] = None,
    duration_ms: int = 0,
    error_message: str = None
):
    """
    Simple function to log a task run without context manager.
    
    Args:
        task_name: Name of the task
        task_type: Type of run
        status: 'success' or 'failed'
        result_summary: Results dictionary
        duration_ms: Duration in milliseconds
        error_message: Error message if failed
    """
    try:
        now = datetime.now(timezone.utc)
        supabase.table('scheduled_task_logs').insert({
            'task_name': task_name,
            'task_type': task_type,
            'started_at': (now - timedelta(milliseconds=duration_ms)).isoformat() if duration_ms else now.isoformat(),
            'completed_at': now.isoformat(),
            'duration_ms': duration_ms,
            'status': status,
            'result_summary': result_summary or {},
            'error_message': error_message,
            'hostname': socket.gethostname(),
            'pid': os.getpid(),
        }).execute()
    except Exception as e:
        print(f"[TaskLogger] Warning: Failed to log task run: {e}")


# Import timedelta for the function above
from datetime import timedelta
