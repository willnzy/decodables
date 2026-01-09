"""Export Service - PDF, Preview, ZIP export functionality.

@module domains.export.export_service
@version 1.0.0

Service for project export functionality with complete DDD architecture.
"""

import logging
from io import BytesIO
from typing import Dict, List, Optional

from domains.creation.repository import IProjectRepository
from infrastructure.logging.activity_logger import log_activity
from shared.ai.zine_generator import create_foldable_book, create_assets_zip

logger = logging.getLogger(__name__)


# ==========================================
# Custom Exceptions
# ==========================================

class ProjectNotFoundException(Exception):
    """Raised when project is not found or user doesn't have access."""
    pass


class ExportException(Exception):
    """Base exception for export failures."""
    pass


class InsufficientPermissionException(Exception):
    """Raised when user doesn't have required tier for operation."""
    pass


# ==========================================
# ExportService
# ==========================================

class ExportService:
    """
    Service for project export functionality.

    Handles PDF, Preview, and ZIP exports with complete business logic encapsulation.

    Responsibilities:
    - Project retrieval and ownership verification
    - Data extraction from canvas_data
    - PDF/Preview/ZIP generation orchestration
    - Activity logging
    - Error handling with user-friendly messages
    """

    def __init__(self, project_repository: IProjectRepository):
        """
        Initialize ExportService.

        Args:
            project_repository: Repository for project data access
        """
        self.project_repository = project_repository

    # ==========================================
    # Public Methods
    # ==========================================

    async def export_pdf(
        self,
        user_id: str,
        project_id: str,
    ) -> tuple[BytesIO, str]:
        """
        Export project as PDF.

        Args:
            user_id: User ID for ownership verification
            project_id: Project ID to export

        Returns:
            tuple: (PDF buffer, sanitized filename)

        Raises:
            ProjectNotFoundException: If project not found or access denied
            ExportException: If PDF generation fails
        """
        # Get and verify project
        proj = await self._get_user_project(user_id, project_id)

        # Extract data
        image_urls, texts, paper_size = self._extract_project_data(proj)

        # Generate PDF
        buf = BytesIO()
        try:
            create_foldable_book(image_urls, texts, buf, paper_type=paper_size)
            buf.seek(0)
        except Exception as e:
            logger.error(f"PDF generation failed for project {project_id[:8]}...: {type(e).__name__}")
            raise ExportException(f"PDF generation failed: {str(e)}")

        # Log activity
        log_activity(user_id, "download_pdf", {"project_id": project_id})

        # Get sanitized filename
        title = self._sanitize_filename(proj.get("title", "project"))

        return buf, title

    async def export_preview(
        self,
        user_id: str,
        project_id: str,
    ) -> BytesIO:
        """
        Export project preview image.

        Args:
            user_id: User ID for ownership verification
            project_id: Project ID to export

        Returns:
            BytesIO: PNG image buffer

        Raises:
            ProjectNotFoundException: If project not found or access denied
            ExportException: If preview generation fails
        """
        import fitz  # PyMuPDF

        # Get and verify project
        proj = await self._get_user_project(user_id, project_id)

        # Extract data
        image_urls, texts, paper_size = self._extract_project_data(proj)

        # Generate PDF first
        pdf_buffer = BytesIO()
        try:
            create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
            pdf_buffer.seek(0)
        except Exception as e:
            logger.error(f"PDF generation for preview failed: {type(e).__name__}")
            raise ExportException("Preview generation failed")

        # Convert to image
        try:
            pdf_doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
            page = pdf_doc[0]

            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            img_buffer = BytesIO(pix.tobytes("png"))
            pdf_doc.close()

            # Log activity
            log_activity(user_id, "preview_pdf", {"project_id": project_id})

            return img_buffer

        except Exception as e:
            logger.error(f"PDF to image conversion failed: {type(e).__name__}")
            raise ExportException("Failed to generate preview")

    async def export_project_zip(
        self,
        user_id: str,
        project_id: str,
        tier: str,
    ) -> tuple[BytesIO, str]:
        """
        Export project assets as ZIP.

        Args:
            user_id: User ID for ownership verification
            project_id: Project ID to export
            tier: User tier (must be "pro")

        Returns:
            tuple: (ZIP buffer, sanitized filename)

        Raises:
            InsufficientPermissionException: If tier is not "pro"
            ProjectNotFoundException: If project not found or access denied
            ExportException: If no valid URLs or ZIP generation fails
        """
        # Verify Pro tier
        if tier.lower() != "pro":
            raise InsufficientPermissionException("ZIP export requires Pro plan")

        # Get and verify project
        proj = await self._get_user_project(user_id, project_id)

        # Extract URLs
        image_urls, _, _ = self._extract_project_data(proj)

        # Filter allowed URLs (SSRF protection)
        from api.user.export import _is_allowed_url
        valid_urls = [url for url in image_urls if _is_allowed_url(url)]

        if not valid_urls:
            raise ExportException("No valid image URLs found in project")

        # Create ZIP
        buf = BytesIO()
        try:
            create_assets_zip(valid_urls, buf)
            buf.seek(0)
        except Exception as e:
            logger.error(f"ZIP generation failed for project {project_id[:8]}...: {type(e).__name__}")
            raise ExportException(f"ZIP generation failed: {str(e)}")

        # Log activity
        log_activity(user_id, "export_zip", {"project_id": project_id})

        # Get sanitized filename
        title = self._sanitize_filename(proj.get("title", "project"))

        return buf, title

    async def export_custom_zip(
        self,
        user_id: str,
        image_urls: List[str],
        tier: str,
        project_id: Optional[str] = None,
    ) -> BytesIO:
        """
        Export custom URLs as ZIP (deprecated endpoint support).

        Args:
            user_id: User ID for logging
            image_urls: List of image URLs (already validated by Pydantic)
            tier: User tier (must be "pro")
            project_id: Optional project ID for logging

        Returns:
            BytesIO: ZIP buffer

        Raises:
            InsufficientPermissionException: If tier is not "pro"
            ExportException: If ZIP generation fails
        """
        # Verify Pro tier
        if tier.lower() != "pro":
            raise InsufficientPermissionException("ZIP export requires Pro plan")

        # Create ZIP
        buf = BytesIO()
        try:
            create_assets_zip(image_urls, buf)
            buf.seek(0)
        except Exception as e:
            logger.error(f"Custom ZIP generation failed: {type(e).__name__}")
            raise ExportException(f"ZIP generation failed: {str(e)}")

        # Log activity
        log_activity(user_id, "export_zip", {"project_id": project_id})

        return buf

    # ==========================================
    # Private Methods
    # ==========================================

    async def _get_user_project(self, user_id: str, project_id: str) -> Dict:
        """
        Get project and verify ownership.

        Args:
            user_id: User ID for ownership check
            project_id: Project ID to retrieve

        Returns:
            Dict: Project data

        Raises:
            ProjectNotFoundException: If project not found or access denied
        """
        proj = await self.project_repository.get_project_detail(project_id, user_id)
        if not proj:
            raise ProjectNotFoundException("Project not found or access denied")
        return proj

    def _extract_project_data(self, proj: Dict) -> tuple[list, list, str]:
        """
        Extract pages data and paper size from project.

        Args:
            proj: Project data dictionary

        Returns:
            tuple: (image_urls, texts, paper_size)
        """
        canvas_data = proj.get("canvas_data", {})

        if isinstance(canvas_data, list):
            pages = canvas_data
            paper_size = "US_LETTER"
        else:
            pages = canvas_data.get("pages", [])
            paper_size_raw = canvas_data.get("paperSize", "Letter")
            paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"

        image_urls = []
        texts = []
        for page in pages:
            if isinstance(page, dict):
                image_urls.append(page.get("previewImage", "") or "")
                texts.append(page.get("prompt", "") or "")
            else:
                image_urls.append("")
                texts.append("")

        # Pad to 8 pages
        while len(image_urls) < 8:
            image_urls.append("")
            texts.append("")

        return image_urls, texts, paper_size

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename for Content-Disposition header.

        Args:
            name: Original filename

        Returns:
            str: Sanitized filename (safe for HTTP headers)
        """
        import re

        if not name:
            return "export"

        # Remove unsafe characters (keep alphanumeric, underscore, hyphen, space)
        SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9_\- ]")
        safe_name = SAFE_FILENAME_PATTERN.sub("", name)

        # Limit length and provide fallback
        safe_name = safe_name[:50].strip() or "export"

        return safe_name
