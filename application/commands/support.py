"""Support Commands - Write operations for user support.

@module application.commands.support
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


# ==========================================
# Create Support Ticket Command
# ==========================================

@dataclass
class CreateSupportTicketCommand:
    """Command to create a support ticket."""
    user_id: str
    user_email: str
    message: str


@dataclass
class CreateSupportTicketResult:
    """Result of support ticket creation."""
    result_data: Dict[str, Any]


class CreateSupportTicketHandler:
    """Handler for CreateSupportTicketCommand."""

    def __init__(self, support_service):
        """
        Initialize with SupportService.

        Args:
            support_service: SupportService instance
        """
        self._support_service = support_service

    async def handle(self, command: CreateSupportTicketCommand) -> CreateSupportTicketResult:
        """
        Execute command to create support ticket.

        Args:
            command: CreateSupportTicketCommand

        Returns:
            CreateSupportTicketResult with result data
        """
        result_data = await self._support_service.create_support_ticket(
            command.user_id,
            command.user_email,
            command.message,
        )
        return CreateSupportTicketResult(result_data=result_data)


# ==========================================
# AI Chat Support Command
# ==========================================

@dataclass
class AiChatSupportCommand:
    """Command to process AI chat support."""
    user_id: str
    message: str
    images: List[str]
    conversation_history: List[Dict[str, Any]]
    ai_chat_service: Any
    openai_assistant_id: Optional[str]
    openai_client: Any
    support_system_prompt: str


@dataclass
class AiChatSupportResult:
    """Result of AI chat support."""
    result_data: Dict[str, Any]


class AiChatSupportHandler:
    """Handler for AiChatSupportCommand."""

    def __init__(self, support_service):
        """
        Initialize with SupportService.

        Args:
            support_service: SupportService instance
        """
        self._support_service = support_service

    async def handle(self, command: AiChatSupportCommand) -> AiChatSupportResult:
        """
        Execute command to process AI chat.

        Args:
            command: AiChatSupportCommand

        Returns:
            AiChatSupportResult with chat response
        """
        result_data = await self._support_service.process_ai_chat(
            command.user_id,
            command.message,
            command.images,
            command.conversation_history,
            command.ai_chat_service,
            command.openai_assistant_id,
            command.openai_client,
            command.support_system_prompt,
        )
        return AiChatSupportResult(result_data=result_data)


# ==========================================
# Send Contact Message Command
# ==========================================

@dataclass
class SendContactMessageCommand:
    """Command to send contact form message."""
    user_id: str
    name: str
    email: str
    message: str
    subject: Optional[str] = None


@dataclass
class SendContactMessageResult:
    """Result of contact message."""
    result_data: Dict[str, Any]


class SendContactMessageHandler:
    """Handler for SendContactMessageCommand."""

    def __init__(self, support_service):
        """
        Initialize with SupportService.

        Args:
            support_service: SupportService instance
        """
        self._support_service = support_service

    async def handle(self, command: SendContactMessageCommand) -> SendContactMessageResult:
        """
        Execute command to send contact message.

        Args:
            command: SendContactMessageCommand

        Returns:
            SendContactMessageResult with result data
        """
        result_data = await self._support_service.send_contact_message(
            command.user_id,
            command.name,
            command.email,
            command.message,
            command.subject,
        )
        return SendContactMessageResult(result_data=result_data)


# ==========================================
# Submit Feedback Command
# ==========================================

@dataclass
class SubmitFeedbackCommand:
    """Command to submit user feedback."""
    user_id: str
    user_email: str
    message: str
    images: List[str]


@dataclass
class SubmitFeedbackResult:
    """Result of feedback submission."""
    result_data: Dict[str, Any]


class SubmitFeedbackHandler:
    """Handler for SubmitFeedbackCommand."""

    def __init__(self, support_service):
        """
        Initialize with SupportService.

        Args:
            support_service: SupportService instance
        """
        self._support_service = support_service

    async def handle(self, command: SubmitFeedbackCommand) -> SubmitFeedbackResult:
        """
        Execute command to submit feedback.

        Args:
            command: SubmitFeedbackCommand

        Returns:
            SubmitFeedbackResult with result data
        """
        result_data = await self._support_service.submit_feedback(
            command.user_id,
            command.user_email,
            command.message,
            command.images,
        )
        return SubmitFeedbackResult(result_data=result_data)
