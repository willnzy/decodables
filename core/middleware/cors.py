"""
CORS Utilities - Cross-Origin Resource Sharing helpers.

@module core.middleware.cors
@version 1.0.0
"""

from typing import List, Optional
from starlette.responses import Response


def add_cors_headers(
    response: Response,
    origins: Optional[List[str]] = None,
    allow_credentials: bool = True,
    allow_methods: str = "GET, POST, PUT, DELETE, OPTIONS, PATCH",
    allow_headers: str = "Authorization, Content-Type, X-Request-ID, X-Workspace-Id"
) -> Response:
    """
    Add CORS headers to a response.

    Use this for error responses that bypass normal CORS middleware.

    Args:
        response: Response to add headers to
        origins: Allowed origins (first one used, or "*" if None)
        allow_credentials: Whether to allow credentials
        allow_methods: Allowed HTTP methods
        allow_headers: Allowed request headers

    Returns:
        Response with CORS headers added
    """
    origin = origins[0] if origins else "*"
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = str(allow_credentials).lower()
    response.headers["Access-Control-Allow-Methods"] = allow_methods
    response.headers["Access-Control-Allow-Headers"] = allow_headers
    return response
