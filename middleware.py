"""
Middleware Components (v3.12)
=============================

This module provides middleware for:
- Request ID generation and tracking
- Structured logging context
- Request/Response logging

The Request ID flows through the entire request lifecycle:
  Client Request -> Middleware (generate ID) -> Handler -> Logs -> Response Header

Usage in app.py:
    from middleware import RequestIDMiddleware, setup_logging
    
    # Setup logging first
    setup_logging()
    
    # Add middleware
    app.add_middleware(RequestIDMiddleware)
"""

import uuid
import time
import logging
from contextvars import ContextVar
from typing import Optional, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import json

# ==========================================
# Context Variables (Thread-Safe)
# ==========================================

# These are accessible anywhere in the request lifecycle
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()

def get_user_id() -> Optional[str]:
    """Get the current user ID from context."""
    return user_id_var.get()

def set_user_id(user_id: str) -> None:
    """Set the current user ID in context (call from auth dependency)."""
    user_id_var.set(user_id)


# ==========================================
# Logging Configuration
# ==========================================

class RequestContextFilter(logging.Filter):
    """
    Logging filter that injects request context into log records.
    
    This allows all log messages to automatically include:
    - request_id
    - user_id
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        record.user_id = get_user_id() or "-"
        return True


def setup_logging(
    level: int = logging.INFO,
    json_format: bool = False
) -> logging.Logger:
    """
    Configure the root logger with request context injection.
    
    Args:
        level: Logging level (default: INFO)
        json_format: If True, output logs as JSON (for production)
    
    Returns:
        Configured root logger
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # Add context filter
    handler.addFilter(RequestContextFilter())
    
    if json_format:
        # JSON format for production (structured logging)
        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "request_id": getattr(record, 'request_id', '-'),
                    "user_id": getattr(record, 'user_id', '-'),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data)
        
        handler.setFormatter(JSONFormatter())
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [rid:%(request_id)s] [uid:%(user_id)s] "
            "%(module)s.%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger


# ==========================================
# Request ID Middleware
# ==========================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates a unique Request ID for each request.
    
    Features:
    - Generates UUID for each request
    - Accepts existing ID from X-Request-ID header (for tracing through proxies)
    - Injects ID into response headers
    - Sets context variable for use in logging
    """
    
    HEADER_NAME = "X-Request-ID"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get existing request ID from header (e.g., from Nginx/CloudFlare)
        # Or generate a new one
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Set context variable (accessible throughout request lifecycle)
        request_id_var.set(request_id)
        
        # Store in request state for easy access
        request.state.request_id = request_id
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
        finally:
            # Calculate request duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log request completion
            logger = logging.getLogger(__name__)
            logger.info(
                f"{request.method} {request.url.path} completed in {duration_ms}ms "
                f"(status: {response.status_code if 'response' in dir() else 'error'})"
            )
            
            # Reset context variables
            request_id_var.set(None)
            user_id_var.set(None)
        
        # Add request ID to response headers
        response.headers[self.HEADER_NAME] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        
        return response


# ==========================================
# Request Logging Middleware (Optional)
# ==========================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request/response logging.
    
    Use this in development for debugging.
    In production, rely on access logs from your load balancer.
    """
    
    # Paths to skip logging (health checks, static files, etc.)
    SKIP_PATHS = {"/health", "/ready", "/metrics", "/favicon.ico"}
    
    # Max body size to log (don't log huge payloads)
    MAX_BODY_LOG_SIZE = 10000
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = logging.getLogger(__name__)
        
        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Log request info
        logger.debug(
            f"[REQUEST] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request and measure time
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        
        # Log response info
        log_level = logging.WARNING if response.status_code >= 400 else logging.DEBUG
        logger.log(
            log_level,
            f"[RESPONSE] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration*1000:.1f}ms)"
        )
        
        return response


# ==========================================
# CORS Headers Middleware (if needed)
# ==========================================

def add_cors_headers(response: Response, origins: list = None) -> Response:
    """
    Add CORS headers to a response.
    Use this for error responses that bypass normal CORS middleware.
    """
    origin = origins[0] if origins else "*"
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID"
    return response
