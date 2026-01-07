"""
Tests for Query Bus.

@module tests.application.test_query_bus
@version 1.0.0
"""

import pytest
from dataclasses import dataclass

from application.handlers.query_bus import QueryBus, IQueryHandler


# Test fixtures
@dataclass
class TestQuery:
    """Test query."""
    value: str


@dataclass
class TestQueryResult:
    """Test query result."""
    data: str


class TestQueryHandler:
    """Test query handler."""

    async def handle(self, query: TestQuery) -> TestQueryResult:
        return TestQueryResult(data=f"Query result: {query.value}")


class FailingQueryHandler:
    """Test handler that always fails."""

    async def handle(self, query: TestQuery) -> TestQueryResult:
        raise ValueError("Query failed")


# Tests
class TestQueryBus:
    """Tests for QueryBus."""

    def test_register_handler(self):
        """Test registering a query handler."""
        bus = QueryBus()
        handler = TestQueryHandler()

        bus.register(TestQuery, handler)

        assert bus.is_registered(TestQuery)
        assert "TestQuery" in bus.list_registered_queries()

    @pytest.mark.asyncio
    async def test_execute_query_success(self):
        """Test successful query execution."""
        # Arrange
        bus = QueryBus()
        handler = TestQueryHandler()
        bus.register(TestQuery, handler)

        query = TestQuery(value="test_value")

        # Act
        result = await bus.execute(query)

        # Assert
        assert result.data == "Query result: test_value"

    @pytest.mark.asyncio
    async def test_execute_unregistered_query_fails(self):
        """Test executing an unregistered query raises error."""
        # Arrange
        bus = QueryBus()
        query = TestQuery(value="test")

        # Act & Assert
        with pytest.raises(ValueError, match="No handler registered"):
            await bus.execute(query)

    @pytest.mark.asyncio
    async def test_execute_query_handler_error_propagates(self):
        """Test that handler errors are propagated."""
        # Arrange
        bus = QueryBus()
        handler = FailingQueryHandler()
        bus.register(TestQuery, handler)

        query = TestQuery(value="test")

        # Act & Assert
        with pytest.raises(ValueError, match="Query failed"):
            await bus.execute(query)

    def test_overwrite_handler_warning(self, caplog):
        """Test that overwriting a handler logs a warning."""
        # Arrange
        bus = QueryBus()
        handler1 = TestQueryHandler()
        handler2 = TestQueryHandler()

        # Act
        bus.register(TestQuery, handler1)
        bus.register(TestQuery, handler2)  # Overwrite

        # Assert
        assert "Overwriting handler" in caplog.text

    def test_list_registered_queries(self):
        """Test listing all registered queries."""
        # Arrange
        bus = QueryBus()
        handler = TestQueryHandler()

        # Act
        bus.register(TestQuery, handler)
        queries = bus.list_registered_queries()

        # Assert
        assert len(queries) == 1
        assert "TestQuery" in queries
