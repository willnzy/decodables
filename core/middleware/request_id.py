"""
Request ID Middleware - Request tracking and context management.

@module core.middleware.request_id
@version 1.0.0
"""

import uuid
import time
import logging
from contextvars import ContextVar
from typing import Optional, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variables (thread-safe, request-scoped)
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


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates a unique Request ID for each request.

    Features:
    - Generates UUID for each request
    - Accepts existing ID from X-Request-ID header (for tracing through proxies)
    - Injects ID into response headers
    - Sets context variable for use in logging
    - Logs request duration

    Usage:
        app.add_middleware(RequestIDMiddleware)
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get existing request ID from header or generate new one
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set context variable (accessible throughout request lifecycle)
        request_id_var.set(request_id)

        # Store in request state for easy access
        request.state.request_id = request_id

        # Process request
        start_time = time.time()
        response = None

        try:
            response = await call_next(request)
        finally:
            # Calculate request duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log request completion
            status = response.status_code if response else "error"
            logger.info(
                f"{request.method} {request.url.path} completed in "
                f"{duration_ms}ms (status: {status})"
            )

            # Reset context variables
            request_id_var.set(None)
            user_id_var.set(None)

        # Add request ID to response headers
        if response:
            response.headers[self.HEADER_NAME] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response
