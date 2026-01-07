"""
Tests for Command Bus.

@module tests.application.test_command_bus
@version 1.0.0
"""

import pytest
from dataclasses import dataclass

from application.handlers.command_bus import CommandBus, ICommandHandler


# Test fixtures
@dataclass
class TestCommand:
    """Test command."""
    value: str


@dataclass
class TestResult:
    """Test result."""
    success: bool
    message: str


class TestCommandHandler:
    """Test command handler."""

    async def handle(self, command: TestCommand) -> TestResult:
        return TestResult(success=True, message=f"Handled: {command.value}")


class FailingCommandHandler:
    """Test handler that always fails."""

    async def handle(self, command: TestCommand) -> TestResult:
        raise ValueError("Intentional failure")


# Tests
class TestCommandBus:
    """Tests for CommandBus."""

    def test_register_handler(self):
        """Test registering a command handler."""
        bus = CommandBus()
        handler = TestCommandHandler()

        bus.register(TestCommand, handler)

        assert bus.is_registered(TestCommand)
        assert "TestCommand" in bus.list_registered_commands()

    @pytest.mark.asyncio
    async def test_execute_command_success(self):
        """Test successful command execution."""
        # Arrange
        bus = CommandBus()
        handler = TestCommandHandler()
        bus.register(TestCommand, handler)

        command = TestCommand(value="test_value")

        # Act
        result = await bus.execute(command)

        # Assert
        assert result.success is True
        assert result.message == "Handled: test_value"

    @pytest.mark.asyncio
    async def test_execute_unregistered_command_fails(self):
        """Test executing an unregistered command raises error."""
        # Arrange
        bus = CommandBus()
        command = TestCommand(value="test")

        # Act & Assert
        with pytest.raises(ValueError, match="No handler registered"):
            await bus.execute(command)

    @pytest.mark.asyncio
    async def test_execute_command_handler_error_propagates(self):
        """Test that handler errors are propagated."""
        # Arrange
        bus = CommandBus()
        handler = FailingCommandHandler()
        bus.register(TestCommand, handler)

        command = TestCommand(value="test")

        # Act & Assert
        with pytest.raises(ValueError, match="Intentional failure"):
            await bus.execute(command)

    def test_overwrite_handler_warning(self, caplog):
        """Test that overwriting a handler logs a warning."""
        # Arrange
        bus = CommandBus()
        handler1 = TestCommandHandler()
        handler2 = TestCommandHandler()

        # Act
        bus.register(TestCommand, handler1)
        bus.register(TestCommand, handler2)  # Overwrite

        # Assert
        assert "Overwriting handler" in caplog.text

    def test_list_registered_commands(self):
        """Test listing all registered commands."""
        # Arrange
        bus = CommandBus()
        handler = TestCommandHandler()

        # Act
        bus.register(TestCommand, handler)
        commands = bus.list_registered_commands()

        # Assert
        assert len(commands) == 1
        assert "TestCommand" in commands
