"""Export Service - PDF, Preview, ZIP export functionality.

@module domains.export.export_service
@version 2.2.0

Service for project export functionality with complete DDD architecture.

Changes in v2.2.0:
- Removed run_in_threadpool usage (AsyncClient migration)
- Direct execution of PDF/ZIP generation (I/O-bound operations)

Changes in v2.1.0:
- Removed hardcoded tier checks, now uses TierService for permission checking
- ZIP export permission is checked via tier_service.can_use_feature()

Changes in v2.0.0:
- Added async-optimized export methods (export_pdf_async, export_zip_async)
- Concurrent image downloads with aiohttp for ZIP exports
- Progress callback support for real-time updates
"""

import logging
import asyncio
import zipfile
from io import BytesIO
from typing import Dict, List, Optional, Callable, TYPE_CHECKING

from domains.creation.repository import IProjectRepository
from infrastructure.logging.activity_logger import log_activity
from shared.ai.zine_generator import create_foldable_book, create_assets_zip

if TYPE_CHECKING:
    from domains.identity.tier_service import TierService

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

    def __init__(
        self,
        project_repository: IProjectRepository,
        tier_service: "TierService" = None
    ):
        """
        Initialize ExportService.

        Args:
            project_repository: Repository for project data access
            tier_service: TierService for permission checking
        """
        self.project_repository = project_repository
        self._tier_service = tier_service

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

        # Log extracted data for debugging
        logger.info(f"Preview export: project_id={project_id[:8]}..., paper_size={paper_size}, "
                    f"pages_with_images={sum(1 for u in image_urls if u)}/8")

        # Generate PDF first
        pdf_buffer = BytesIO()
        try:
            create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
            pdf_buffer.seek(0)
        except Exception as e:
            logger.error(f"PDF generation for preview failed: {type(e).__name__}: {str(e)}", exc_info=True)
            raise ExportException(f"Preview generation failed: {str(e)}")

        # Verify PDF buffer has content
        pdf_size = pdf_buffer.getbuffer().nbytes
        if pdf_size == 0:
            logger.error("PDF generation returned empty buffer")
            raise ExportException("PDF generation failed: empty buffer")

        logger.info(f"PDF generated successfully: {pdf_size} bytes")

        # Convert to image using PyMuPDF
        pdf_data = pdf_buffer.read()
        try:
            logger.info(f"Opening PDF with fitz, data size: {len(pdf_data)} bytes")
            pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
            logger.info(f"PDF opened, pages: {len(pdf_doc)}")

            if len(pdf_doc) == 0:
                logger.error("PDF has no pages")
                raise ExportException("PDF has no pages")

            page = pdf_doc[0]
            logger.info(f"Got page 0, size: {page.rect}")

            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            logger.info(f"Creating pixmap with zoom={zoom}")
            pix = page.get_pixmap(matrix=mat)
            logger.info(f"Pixmap created, size: {pix.width}x{pix.height}")

            img_buffer = BytesIO(pix.tobytes("png"))
            pdf_doc.close()
            logger.info(f"Preview image generated, size: {img_buffer.getbuffer().nbytes} bytes")

            # Log activity
            log_activity(user_id, "preview_pdf", {"project_id": project_id})

            return img_buffer

        except RuntimeError as e:
            # PyMuPDF RuntimeError - likely missing system dependencies (mupdf)
            logger.error(f"PyMuPDF RuntimeError (check nixpacks.toml for mupdf dep): {str(e)}", exc_info=True)
            raise ExportException(f"Failed to generate preview: PyMuPDF error - {str(e)}")
        except Exception as e:
            logger.error(f"PDF to image conversion failed: {type(e).__name__}: {str(e)}", exc_info=True)
            raise ExportException(f"Failed to generate preview: {str(e)}")

    async def export_project_zip(
        self,
        user_id: str,
        project_id: str,
        tier: str,
        is_trial_active: bool = False,
    ) -> tuple[BytesIO, str]:
        """
        Export project assets as ZIP.

        Args:
            user_id: User ID for ownership verification
            project_id: Project ID to export
            tier: User tier
            is_trial_active: Whether t1 user is in trial period

        Returns:
            tuple: (ZIP buffer, sanitized filename)

        Raises:
            InsufficientPermissionException: If user doesn't have ZIP export permission
            ProjectNotFoundException: If project not found or access denied
            ExportException: If no valid URLs or ZIP generation fails
        """
        # Check ZIP export permission via TierService
        can_export = await self._check_zip_permission(tier, is_trial_active)
        if not can_export:
            raise InsufficientPermissionException("ZIP export requires Pro plan")

        # Get and verify project
        proj = await self._get_user_project(user_id, project_id)

        # Extract URLs
        image_urls, _, _ = self._extract_project_data(proj)

        # Filter allowed URLs (SSRF protection)
        from core.validators import is_allowed_url
        valid_urls = [url for url in image_urls if is_allowed_url(url)]

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
        is_trial_active: bool = False,
    ) -> BytesIO:
        """
        Export custom URLs as ZIP (deprecated endpoint support).

        Args:
            user_id: User ID for logging
            image_urls: List of image URLs (already validated by Pydantic)
            tier: User tier
            project_id: Optional project ID for logging
            is_trial_active: Whether t1 user is in trial period

        Returns:
            BytesIO: ZIP buffer

        Raises:
            InsufficientPermissionException: If user doesn't have ZIP export permission
            ExportException: If ZIP generation fails
        """
        # Check ZIP export permission via TierService
        can_export = await self._check_zip_permission(tier, is_trial_active)
        if not can_export:
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

    # ==========================================
    # Async-Optimized Methods (v2.0.0)
    # ==========================================

    async def export_pdf_async(
        self,
        user_id: str,
        project_id: str,
    ) -> tuple[BytesIO, str]:
        """
        Async-optimized PDF export with threadpool offloading.

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

        # Generate PDF (CPU-intensive, but fast enough for direct execution)
        # Note: create_foldable_book is I/O-bound (image fetching) not CPU-bound
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

    async def export_zip_async(
        self,
        user_id: str,
        project_id: str,
        tier: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_trial_active: bool = False,
    ) -> tuple[BytesIO, str]:
        """
        Async-optimized ZIP export with concurrent image downloads.

        Args:
            user_id: User ID for ownership verification
            project_id: Project ID to export
            tier: User tier
            progress_callback: Optional callback(current, total, message) for progress updates
            is_trial_active: Whether t1 user is in trial period

        Returns:
            tuple: (ZIP buffer, sanitized filename)

        Raises:
            InsufficientPermissionException: If user doesn't have ZIP export permission
            ProjectNotFoundException: If project not found or access denied
            ExportException: If no valid URLs or ZIP generation fails
        """
        # Check ZIP export permission via TierService
        can_export = await self._check_zip_permission(tier, is_trial_active)
        if not can_export:
            raise InsufficientPermissionException("ZIP export requires Pro plan")

        # Get and verify project
        proj = await self._get_user_project(user_id, project_id)

        # Extract URLs
        image_urls, _, _ = self._extract_project_data(proj)

        # Filter allowed URLs (SSRF protection)
        from core.validators import is_allowed_url
        valid_urls = [url for url in image_urls if is_allowed_url(url) and url]

        if not valid_urls:
            raise ExportException("No valid image URLs found in project")

        # Download images concurrently
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                download_tasks = [
                    self._download_image_async(session, url, idx)
                    for idx, url in enumerate(valid_urls)
                ]

                # Download with progress updates
                images = []
                for idx, task in enumerate(asyncio.as_completed(download_tasks)):
                    result = await task
                    images.append(result)

                    if progress_callback:
                        await progress_callback(
                            idx + 1,
                            len(valid_urls),
                            f"Downloaded {idx + 1}/{len(valid_urls)} images"
                        )

                # Sort by index (as_completed returns in random order)
                images.sort(key=lambda x: x[0])

        except Exception as e:
            logger.error(f"Image download failed for project {project_id[:8]}...: {type(e).__name__}")
            raise ExportException(f"Image download failed: {str(e)}")

        # Create ZIP (I/O operation, fast enough for direct execution)
        buf = BytesIO()
        try:
            self._create_zip_from_images(images, buf)
            buf.seek(0)
        except Exception as e:
            logger.error(f"ZIP creation failed for project {project_id[:8]}...: {type(e).__name__}")
            raise ExportException(f"ZIP creation failed: {str(e)}")

        # Log activity
        log_activity(user_id, "export_zip", {"project_id": project_id})

        # Get sanitized filename
        title = self._sanitize_filename(proj.get("title", "project"))

        return buf, title

    async def _download_image_async(
        self,
        session,
        url: str,
        index: int
    ) -> tuple[int, Optional[bytes]]:
        """
        Download single image asynchronously.

        Args:
            session: aiohttp ClientSession
            url: Image URL
            index: Image index

        Returns:
            tuple: (index, image_data) or (index, None) if failed
        """
        import aiohttp

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return (index, data)
                else:
                    logger.warning(f"Image download failed (HTTP {resp.status}): {url}")
                    return (index, None)
        except asyncio.TimeoutError:
            logger.warning(f"Image download timeout: {url}")
            return (index, None)
        except Exception as e:
            logger.warning(f"Image download error for {url}: {type(e).__name__}")
            return (index, None)

    def _create_zip_from_images(
        self,
        images: List[tuple[int, Optional[bytes]]],
        buffer: BytesIO
    ):
        """
        Create ZIP file from downloaded images (runs in threadpool).

        Args:
            images: List of (index, image_data) tuples
            buffer: BytesIO buffer to write ZIP to
        """
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for index, data in images:
                if data:
                    filename = f"Page_{index + 1}.png"
                    zip_file.writestr(filename, data)
                    logger.debug(f"Added {filename} to ZIP ({len(data)} bytes)")

        logger.info(f"Created ZIP with {len([d for _, d in images if d])} images")

    async def _check_zip_permission(
        self,
        tier: str,
        is_trial_active: bool = False
    ) -> bool:
        """
        Check if user has ZIP export permission.

        Uses TierService to check permission dynamically.
        Falls back to t3-only check if tier_service not available.

        Args:
            tier: User tier code (t1/t2/t3/t4)
            is_trial_active: Whether t1 user is in trial period

        Returns:
            True if user can use ZIP export
        """
        if self._tier_service:
            from domains.identity.tier_service import FeatureKey
            return await self._tier_service.can_use_feature(
                tier, FeatureKey.ZIP_EXPORT, is_trial_active
            )

        # Fallback: only t3 and t4 can export ZIP
        return tier.lower() in ("t3", "t4")
