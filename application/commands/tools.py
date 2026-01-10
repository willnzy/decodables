"""Tools Commands - Write operations for utility tools.

@module application.commands.tools
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from fastapi import UploadFile


# ==========================================
# PDF Preview Command
# ==========================================

@dataclass
class PdfPreviewCommand:
    """Command to generate PDF preview images."""
    file: UploadFile
    user: dict


@dataclass
class PdfPreviewResult:
    """Result of PDF preview generation."""
    result_data: Dict[str, Any]


class PdfPreviewHandler:
    """Handler for PdfPreviewCommand."""

    def __init__(self, tools_service):
        """
        Initialize with ToolsService.

        Args:
            tools_service: ToolsService instance
        """
        self._tools_service = tools_service

    async def handle(self, command: PdfPreviewCommand) -> PdfPreviewResult:
        """
        Execute command to generate PDF previews.

        Args:
            command: PdfPreviewCommand

        Returns:
            PdfPreviewResult with preview data
        """
        result_data = await self._tools_service.process_pdf_preview(
            command.file,
            command.user,
        )
        return PdfPreviewResult(result_data=result_data)


# ==========================================
# OCR Command
# ==========================================

@dataclass
class OcrCommand:
    """Command to process OCR."""
    file: UploadFile
    project_id: Optional[str]
    user: dict
    timezone: str
    is_trial: bool


@dataclass
class OcrResult:
    """Result of OCR processing."""
    result_data: Dict[str, Any]


class OcrHandler:
    """Handler for OcrCommand."""

    def __init__(self, tools_service):
        """
        Initialize with ToolsService.

        Args:
            tools_service: ToolsService instance
        """
        self._tools_service = tools_service

    async def handle(self, command: OcrCommand) -> OcrResult:
        """
        Execute command to process OCR.

        Args:
            command: OcrCommand

        Returns:
            OcrResult with OCR data
        """
        result_data = await self._tools_service.process_ocr(
            command.file,
            command.project_id,
            command.user,
            command.timezone,
            command.is_trial,
        )
        return OcrResult(result_data=result_data)
