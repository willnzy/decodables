"""
Query Bus - Dispatches queries to their handlers.

Implements the Query pattern for read operations.

@module application.handlers.query_bus
@version 1.0.0
"""

import logging
from typing import Any, Protocol, TypeVar, Generic, Dict, Type

logger = logging.getLogger(__name__)

# Generic types for queries and results
TQuery = TypeVar('TQuery')
TResult = TypeVar('TResult')


class IQueryHandler(Protocol[TQuery, TResult]):
    """Interface for query handlers."""

    async def handle(self, query: TQuery) -> TResult:
        """Handle a query and return result."""
        ...


class QueryBus:
    """
    Query Bus - Central dispatcher for queries.

    Usage:
        # Register handlers
        bus = QueryBus()
        bus.register(GetUserCreditsQuery, GetUserCreditsHandler(billing_service))

        # Execute query
        query = GetUserCreditsQuery(user_id="user_123")
        result = await bus.execute(query)
    """

    def __init__(self):
        self._handlers: Dict[Type, Any] = {}

    def register(self, query_type: Type[TQuery], handler: IQueryHandler[TQuery, TResult]):
        """
        Register a query handler.

        Args:
            query_type: The query class
            handler: The handler instance
        """
        if query_type in self._handlers:
            logger.warning(f"[QueryBus] Overwriting handler for {query_type.__name__}")

        self._handlers[query_type] = handler
        logger.debug(f"[QueryBus] Registered handler for {query_type.__name__}")

    async def execute(self, query: TQuery) -> TResult:
        """
        Execute a query by dispatching to its handler.

        Args:
            query: The query instance

        Returns:
            Result from the handler

        Raises:
            ValueError: If no handler is registered for the query
        """
        query_type = type(query)
        handler = self._handlers.get(query_type)

        if not handler:
            raise ValueError(
                f"No handler registered for query: {query_type.__name__}. "
                f"Available handlers: {[h.__name__ for h in self._handlers.keys()]}"
            )

        logger.debug(f"[QueryBus] Executing {query_type.__name__}")

        try:
            result = await handler.handle(query)
            logger.debug(f"[QueryBus] {query_type.__name__} executed successfully")
            return result

        except Exception as e:
            logger.error(f"[QueryBus] {query_type.__name__} failed: {e}")
            raise

    def is_registered(self, query_type: Type[TQuery]) -> bool:
        """Check if a handler is registered for a query type."""
        return query_type in self._handlers

    def list_registered_queries(self) -> list[str]:
        """List all registered query types."""
        return [query.__name__ for query in self._handlers.keys()]
