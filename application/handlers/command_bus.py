"""
Command Bus - Dispatches commands to their handlers.

Implements the Command pattern for write operations.

@module application.handlers.command_bus
@version 1.0.0
"""

import logging
from typing import Any, Protocol, TypeVar, Generic, Dict, Type

logger = logging.getLogger(__name__)

# Generic types for commands and results
TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')


class ICommandHandler(Protocol[TCommand, TResult]):
    """Interface for command handlers."""

    async def handle(self, command: TCommand) -> TResult:
        """Handle a command and return result."""
        ...


class CommandBus:
    """
    Command Bus - Central dispatcher for commands.

    Usage:
        # Register handlers
        bus = CommandBus()
        bus.register(DeductCreditsCommand, DeductCreditsHandler(billing_service))

        # Execute command
        command = DeductCreditsCommand(user_id="user_123", operation="image_generation")
        result = await bus.execute(command)
    """

    def __init__(self):
        self._handlers: Dict[Type, Any] = {}

    def register(self, command_type: Type[TCommand], handler: ICommandHandler[TCommand, TResult]):
        """
        Register a command handler.

        Args:
            command_type: The command class
            handler: The handler instance
        """
        if command_type in self._handlers:
            logger.warning(f"[CommandBus] Overwriting handler for {command_type.__name__}")

        self._handlers[command_type] = handler
        logger.debug(f"[CommandBus] Registered handler for {command_type.__name__}")

    async def execute(self, command: TCommand) -> TResult:
        """
        Execute a command by dispatching to its handler.

        Args:
            command: The command instance

        Returns:
            Result from the handler

        Raises:
            ValueError: If no handler is registered for the command
        """
        command_type = type(command)
        handler = self._handlers.get(command_type)

        if not handler:
            raise ValueError(
                f"No handler registered for command: {command_type.__name__}. "
                f"Available handlers: {[h.__name__ for h in self._handlers.keys()]}"
            )

        logger.info(f"[CommandBus] Executing {command_type.__name__}")

        try:
            result = await handler.handle(command)
            logger.debug(f"[CommandBus] {command_type.__name__} executed successfully")
            return result

        except Exception as e:
            logger.error(f"[CommandBus] {command_type.__name__} failed: {e}")
            raise

    def is_registered(self, command_type: Type[TCommand]) -> bool:
        """Check if a handler is registered for a command type."""
        return command_type in self._handlers

    def list_registered_commands(self) -> list[str]:
        """List all registered command types."""
        return [cmd.__name__ for cmd in self._handlers.keys()]
