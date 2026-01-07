"""
Logging Middleware - Structured logging with request context.

@module core.middleware.logging
@version 1.0.0
"""

import json
import time
import logging
from typing import Callable, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .request_id import get_request_id, get_user_id


class RequestContextFilter(logging.Filter):
    """
    Logging filter that injects request context into log records.

    Adds to all log messages:
    - request_id
    - user_id
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        record.user_id = get_user_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production environments."""

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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request/response logging.

    Use in development for debugging.
    In production, rely on access logs from your load balancer.

    Attributes:
        skip_paths: Paths to skip logging (health checks, etc.)
        max_body_log_size: Maximum body size to log
    """

    DEFAULT_SKIP_PATHS: Set[str] = {"/health", "/ready", "/metrics", "/favicon.ico"}

    def __init__(self, app, skip_paths: Set[str] = None, max_body_log_size: int = 10000):
        super().__init__(app)
        self.skip_paths = skip_paths or self.DEFAULT_SKIP_PATHS
        self.max_body_log_size = max_body_log_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = logging.getLogger(__name__)

        # Skip logging for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Log request info
        client_host = request.client.host if request.client else "unknown"
        logger.debug(f"[REQUEST] {request.method} {request.url.path} from {client_host}")

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
