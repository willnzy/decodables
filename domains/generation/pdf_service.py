"""
PDF Generation Service - Business logic for PDF export.

@module domains.generation.pdf_service
@version 1.0.0

This service orchestrates the PDF generation workflow:
1. Project ownership verification
2. Project hash update (track download changes)
3. PDF generation from images and texts
4. Activity logging

Changes:
- v1.0.0: Initial creation - Extracted from api/user/generation_pdf.py
          Implemented DDD architecture with dependency injection
"""

import logging
from io import BytesIO
from typing import List, Optional

from shared.ai.zine_generator import create_foldable_book
from infrastructure.repositories.project_repository import SupabaseProjectRepository
from infrastructure.logging.activity_logger import log_activity

logger = logging.getLogger(__name__)


# ==========================================
# Custom Exceptions
# ==========================================

class ProjectNotFoundException(Exception):
    """Raised when project not found or user lacks permission."""
    def __init__(self, project_id: str):
        self.project_id = project_id
        super().__init__(f"Project {project_id} not found or access denied")


class PdfGenerationException(Exception):
    """Raised when PDF generation fails."""
    pass


# ==========================================
# PDF Generation Service
# ==========================================

class PdfGenerationService:
    """
    Service for PDF generation workflow.

    Responsibilities:
    - Verify project ownership
    - Update project download hash
    - Generate foldable book PDF
    - Log user activity

    Dependencies (Injected):
    - project_repository: Access to project data
    """

    def __init__(self, project_repository: SupabaseProjectRepository):
        """
        Initialize PdfGenerationService.

        Args:
            project_repository: Repository for project data access
        """
        self.project_repo = project_repository

    async def generate_pdf(
        self,
        user_id: str,
        project_id: str,
        current_hash: str,
        image_urls: List[str],
        texts: List[str],
    ) -> BytesIO:
        """
        Generate PDF with full workflow orchestration.

        Workflow:
        1. Verify project ownership (raises ProjectNotFoundException if not owned)
        2. Update project hash if changed (tracks download state)
        3. Generate PDF from images and texts
        4. Log download activity
        5. Return PDF buffer

        Args:
            user_id: ID of the user requesting PDF
            project_id: UUID of the project
            current_hash: Hash of current project state (for tracking changes)
            image_urls: List of image URLs (max 20, empty strings for blank pages)
            texts: List of text content for each page (max 2000 chars each)

        Returns:
            BytesIO: PDF binary buffer (ready for streaming)

        Raises:
            ProjectNotFoundException: If project not found or user lacks permission
            PdfGenerationException: If PDF generation fails
        """
        # Step 1: Verify project ownership
        logger.debug(f"Generating PDF for project {project_id}, user {user_id}")
        proj = await self.project_repo.get_project_detail(project_id, user_id)

        if not proj:
            logger.warning(f"Project {project_id} not found or access denied for user {user_id}")
            raise ProjectNotFoundException(project_id)

        # Step 2: Update hash if changed
        # Purpose: Track when user downloads a new version of their project
        # Business rule: Only update if hash has actually changed to avoid unnecessary DB writes
        last_hash = proj.get("last_downloaded_hash")
        if current_hash != last_hash:
            logger.info(f"Updating project {project_id} hash: {last_hash} → {current_hash}")
            await self.project_repo.update_project_hash(project_id, current_hash)
        else:
            logger.debug(f"Project {project_id} hash unchanged, skipping update")

        # Step 3: Generate PDF
        # create_foldable_book() creates an 8-page foldable zine layout
        # Format: Single A4 sheet → fold into booklet
        try:
            buf = BytesIO()
            create_foldable_book(image_urls, texts, buf)
            buf.seek(0)  # Reset buffer position for reading
            logger.info(f"PDF generated successfully for project {project_id}")
        except ValueError as e:
            # ValueError typically means invalid image format or content
            logger.error(f"PDF generation failed (invalid input): {e}", exc_info=True)
            raise PdfGenerationException(f"Invalid image format: {str(e)}")
        except Exception as e:
            # Catch-all for unexpected errors (network issues, PIL errors, etc.)
            logger.error(f"PDF generation failed (unexpected): {e}", exc_info=True)
            raise PdfGenerationException("PDF generation failed unexpectedly")

        # Step 4: Log activity
        log_activity(user_id, "download_pdf", {"project_id": project_id})

        return buf
