"""
WebSocket Service
WebSocket 实时通信服务

Provides:
- WebSocket connection management
- Real-time task progress broadcasting
- Redis PubSub integration for multi-instance support

Usage:
    from infrastructure.websocket import ws_manager
    
    # In FastAPI endpoint
    @app.websocket("/ws/task/{task_id}")
    async def task_websocket(websocket: WebSocket, task_id: str):
        await ws_manager.handle_task_connection(websocket, task_id)
"""

from .connection_manager import WebSocketManager, ws_manager

__all__ = [
    'WebSocketManager',
    'ws_manager',
]
