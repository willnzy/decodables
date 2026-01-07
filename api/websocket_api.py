"""
WebSocket API - Real-time communication endpoints.

@module api.websocket_api
@version 1.0.0

Endpoints:
- WS /api/v2/ws/task/{task_id} - Task progress updates
"""

import logging

from fastapi import APIRouter, WebSocket

from services.websocket import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/ws", tags=["websocket-v2"])


@router.websocket("/task/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time task progress updates.

    Messages sent to client:
    - {"type": "status", ...}: Current task status
    - {"type": "progress", ...}: Progress update with percentage
    - {"type": "completed", ...}: Task completed with result
    - {"type": "failed", ...}: Task failed with error
    - {"type": "heartbeat", ...}: Keep-alive ping

    Messages from client:
    - {"type": "ping"}: Heartbeat request
    - {"type": "cancel"}: Request task cancellation
    """
    await ws_manager.handle_task_connection(websocket, task_id)
