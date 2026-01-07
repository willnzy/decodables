"""
WebSocket Connection Manager
WebSocket 连接管理器

Manages WebSocket connections and broadcasts task progress updates.
Uses Redis PubSub for multi-instance support (horizontal scaling).
"""

import os
import json
import asyncio
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from core.cache.redis_provider import get_redis_client

logger = logging.getLogger(__name__)

# Redis PubSub channel pattern
TASK_CHANNEL_PATTERN = "task:progress:*"
TASK_CHANNEL_PREFIX = "task:progress:"


class WebSocketManager:
    """
    Manages WebSocket connections for real-time task updates.
    
    Features:
    - Connection tracking per task
    - Redis PubSub subscription for cross-instance messaging
    - Graceful disconnection handling
    - Heartbeat support
    """
    
    def __init__(self):
        # task_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Active Redis PubSub subscriptions
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._redis = None
    
    def _get_redis(self):
        """Get Redis client (lazy initialization)."""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis
    
    async def connect(self, websocket: WebSocket, task_id: str, user_id: str = None):
        """
        Accept WebSocket connection and subscribe to task updates.
        
        Args:
            websocket: WebSocket connection
            task_id: Task ID to subscribe to
            user_id: Optional user ID for authorization
        """
        await websocket.accept()
        
        async with self._lock:
            if task_id not in self._connections:
                self._connections[task_id] = set()
            self._connections[task_id].add(websocket)
        
        logger.info(f"[WebSocket] Client connected for task {task_id}")
        
        # Start Redis PubSub listener if not already running
        await self._ensure_pubsub_listener(task_id)
        
        # Send current status immediately
        await self._send_current_status(websocket, task_id)
    
    async def disconnect(self, websocket: WebSocket, task_id: str):
        """
        Handle WebSocket disconnection.
        
        Args:
            websocket: WebSocket connection
            task_id: Task ID
        """
        async with self._lock:
            if task_id in self._connections:
                self._connections[task_id].discard(websocket)
                
                # Clean up empty sets
                if not self._connections[task_id]:
                    del self._connections[task_id]
                    
                    # Stop PubSub listener if no more connections
                    if task_id in self._pubsub_tasks:
                        self._pubsub_tasks[task_id].cancel()
                        del self._pubsub_tasks[task_id]
        
        logger.info(f"[WebSocket] Client disconnected from task {task_id}")
    
    async def broadcast_to_task(self, task_id: str, message: Dict[str, Any]):
        """
        Broadcast message to all connections for a task.
        
        Args:
            task_id: Task ID
            message: Message dict to send
        """
        if task_id not in self._connections:
            return
        
        disconnected = set()
        
        for websocket in self._connections[task_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"[WebSocket] Send failed: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                if task_id in self._connections:
                    self._connections[task_id] -= disconnected
    
    async def _send_current_status(self, websocket: WebSocket, task_id: str):
        """Send current task status on connection."""
        redis = self._get_redis()
        if not redis:
            return
        
        try:
            # Get current status from Redis
            status_key = f"task:{task_id}:status"
            data = redis.hgetall(status_key)
            
            if data:
                message = {
                    "type": "status",
                    "task_id": task_id,
                    "status": data.get("status", "unknown"),
                    "progress": int(data.get("progress", 0)),
                    "current_step": int(data.get("current_step", 0)),
                    "total_steps": int(data.get("total_steps", 0)),
                    "message": data.get("message", ""),
                }
                
                # Include result if completed
                if "result" in data:
                    try:
                        message["result"] = json.loads(data["result"])
                    except json.JSONDecodeError:
                        pass
                
                # Include error if failed
                if "error" in data:
                    message["error"] = data["error"]
                
                await websocket.send_json(message)
            else:
                # Task not found
                await websocket.send_json({
                    "type": "error",
                    "task_id": task_id,
                    "error": "Task not found",
                })
                
        except Exception as e:
            logger.warning(f"[WebSocket] Failed to send initial status: {e}")
    
    async def _ensure_pubsub_listener(self, task_id: str):
        """Ensure PubSub listener is running for task."""
        if task_id in self._pubsub_tasks:
            return
        
        redis = self._get_redis()
        if not redis:
            return
        
        # Start background task to listen for Redis PubSub messages
        task = asyncio.create_task(self._pubsub_listener(task_id))
        self._pubsub_tasks[task_id] = task
    
    async def _pubsub_listener(self, task_id: str):
        """
        Listen for Redis PubSub messages and broadcast to WebSocket clients.
        
        This enables multi-instance support - workers can publish updates
        from any instance, and all connected clients will receive them.
        """
        redis = self._get_redis()
        if not redis:
            return
        
        channel = f"{TASK_CHANNEL_PREFIX}{task_id}"
        pubsub = redis.pubsub()
        
        try:
            pubsub.subscribe(channel)
            logger.info(f"[WebSocket] Subscribed to Redis channel: {channel}")
            
            # Use sync iteration in async context
            while True:
                # Non-blocking get with timeout
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast_to_task(task_id, data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"[WebSocket] Invalid PubSub message: {e}")
                
                # Small sleep to prevent tight loop
                await asyncio.sleep(0.05)
                
                # Check if still has connections
                if task_id not in self._connections or not self._connections[task_id]:
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"[WebSocket] PubSub listener cancelled for {task_id}")
        except Exception as e:
            logger.error(f"[WebSocket] PubSub listener error: {e}")
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
            except Exception:
                pass
    
    async def handle_task_connection(
        self,
        websocket: WebSocket,
        task_id: str,
        user_id: str = None
    ):
        """
        Main handler for task WebSocket connections.
        
        Use this in your FastAPI WebSocket endpoint.
        
        Args:
            websocket: WebSocket connection
            task_id: Task ID
            user_id: User ID for authorization (optional)
        """
        await self.connect(websocket, task_id, user_id)
        
        try:
            while True:
                # Wait for client messages (heartbeat, cancel, etc.)
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=30.0  # 30 second timeout for heartbeat
                    )
                    
                    # Handle client messages
                    msg_type = data.get("type")
                    
                    if msg_type == "ping":
                        # Heartbeat response
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    
                    elif msg_type == "cancel":
                        # Client requests cancellation
                        from services.task_queue import task_queue
                        if user_id and task_queue.cancel_task(task_id, user_id):
                            await websocket.send_json({
                                "type": "cancelled",
                                "task_id": task_id,
                                "message": "Task cancelled"
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Cannot cancel task"
                            })
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    try:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    except Exception:
                        break
                        
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning(f"[WebSocket] Connection error: {e}")
        finally:
            await self.disconnect(websocket, task_id)
    
    def get_connection_count(self, task_id: str = None) -> int:
        """Get number of active connections."""
        if task_id:
            return len(self._connections.get(task_id, set()))
        return sum(len(conns) for conns in self._connections.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": self.get_connection_count(),
            "tasks_with_connections": len(self._connections),
            "active_pubsub_listeners": len(self._pubsub_tasks),
        }


# Global singleton
ws_manager = WebSocketManager()
