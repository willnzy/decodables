"""
Database Async Utilities - Tools for running sync DB operations in async context.

@module core.database.async_utils
@version 1.0.0

This module provides utilities for properly handling synchronous database SDKs
(like Supabase Python SDK) in FastAPI's async environment.

Best Practice Reference:
- FastAPI Official: https://fastapi.tiangolo.com/async/
- FastAPI GitHub Discussion #7623
- Sentry: run_in_executor vs run_in_threadpool
"""

import logging
from typing import Callable, TypeVar, ParamSpec
from functools import wraps

from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


async def run_sync(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """
    Run a synchronous function in a thread pool without blocking the event loop.

    This is the recommended way to call synchronous database SDKs in FastAPI.
    Uses Starlette's run_in_threadpool internally.

    Args:
        func: Synchronous function to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func

    Example:
        # Instead of blocking call:
        result = supabase.table("users").select("*").execute()

        # Use non-blocking:
        result = await run_sync(
            lambda: supabase.table("users").select("*").execute()
        )

        # Or with a regular function:
        def fetch_users():
            return supabase.table("users").select("*").execute()

        result = await run_sync(fetch_users)
    """
    return await run_in_threadpool(func, *args, **kwargs)


def async_wrap(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to wrap a synchronous function for async execution.

    The decorated function will run in a thread pool when awaited.

    Args:
        func: Synchronous function to wrap

    Returns:
        Async version of the function

    Example:
        @async_wrap
        def sync_db_operation(user_id: str):
            return supabase.table("users").select("*").eq("id", user_id).execute()

        # Now can be awaited:
        result = await sync_db_operation("user_123")
    """
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await run_in_threadpool(func, *args, **kwargs)
    return wrapper


async def run_sync_safe(
    func: Callable[P, T],
    *args: P.args,
    default: T = None,
    log_errors: bool = True,
    **kwargs: P.kwargs
) -> T:
    """
    Run a synchronous function safely, catching and logging any exceptions.

    Useful for non-critical operations like logging, analytics, etc.

    Args:
        func: Synchronous function to execute
        *args: Positional arguments to pass to func
        default: Value to return if func raises an exception
        log_errors: Whether to log exceptions (default: True)
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func, or default if an exception occurs

    Example:
        # Non-critical analytics logging that shouldn't fail the request
        await run_sync_safe(
            log_activity, user_id, "page_view", {"page": "/home"},
            default=None,
            log_errors=True
        )
    """
    try:
        return await run_in_threadpool(func, *args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.warning(f"[run_sync_safe] {func.__name__} failed: {e}")
        return default
