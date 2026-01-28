"""
Thumbnail Service - Background thumbnail generation for projects.

@module domains.creation.thumbnail_service
@version 1.0.0

This service handles automatic thumbnail generation when projects are saved.
It uses ExportService to generate preview images and uploads them to storage.

Architecture:
- Called by UpdateProjectHandler after canvas_data changes
- Runs asynchronously (non-blocking) to avoid slowing down save operations
- Updates project.thumbnail_url directly in the database

Benefits over frontend thumbnail generation:
- Always available (doesn't depend on frontend loading state)
- Consistent quality and format
- No client-side processing overhead
- Works even when user closes browser during save
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from io import BytesIO

if TYPE_CHECKING:
    from domains.export import ExportService
    from domains.creation.repository import IProjectRepository

logger = logging.getLogger(__name__)

# Storage configuration
THUMBNAIL_BUCKET = "make-decodables-u"
THUMBNAIL_PREFIX = "thumbnails"


class ThumbnailService:
    """
    Service for generating and storing project thumbnails.

    This service is responsible for:
    1. Generating preview images from project canvas data
    2. Uploading thumbnails to Supabase storage
    3. Updating project.thumbnail_url in the database

    Usage:
        thumbnail_service = ThumbnailService(export_service, project_repo, storage)
        url = await thumbnail_service.generate_and_store(project_id, user_id)
    """

    def __init__(
        self,
        export_service: "ExportService",
        project_repository: "IProjectRepository",
        storage_client,
    ):
        """
        Initialize ThumbnailService.

        Args:
            export_service: ExportService for generating preview images
            project_repository: Repository for updating project records
            storage_client: AsyncClient for Supabase storage operations
        """
        self._export_service = export_service
        self._project_repo = project_repository
        self._storage = storage_client

    async def generate_and_store(
        self,
        project_id: str,
        user_id: str,
    ) -> Optional[str]:
        """
        Generate thumbnail from project and store in Supabase.

        This is the main entry point for thumbnail generation. It:
        1. Generates a preview image from the project
        2. Uploads it to Supabase storage
        3. Updates the project's thumbnail_url field

        Args:
            project_id: Project ID to generate thumbnail for
            user_id: User ID (for ownership verification and storage path)

        Returns:
            str: Public URL of the uploaded thumbnail, or None if failed

        Note:
            This method is designed to be called in a background task.
            It will not raise exceptions - all errors are logged and None is returned.
        """
        try:
            # Step 1: Generate thumbnail image
            logger.info(f"[Thumbnail] Generating for project {project_id[:8]}...")
            img_buffer = await self._export_service.generate_thumbnail_from_project(
                project_id, user_id
            )

            if img_buffer is None:
                logger.warning(f"[Thumbnail] Failed to generate for {project_id[:8]}...")
                return None

            # Step 2: Upload to storage
            thumbnail_url = await self._upload_thumbnail(
                img_buffer, project_id, user_id
            )

            if thumbnail_url is None:
                logger.warning(f"[Thumbnail] Failed to upload for {project_id[:8]}...")
                return None

            # Step 3: Update project record
            await self._update_project_thumbnail(project_id, thumbnail_url)

            logger.info(f"[Thumbnail] Successfully generated for {project_id[:8]}...")
            return thumbnail_url

        except Exception as e:
            logger.error(f"[Thumbnail] Unexpected error for {project_id[:8]}...: {e}")
            return None

    async def _upload_thumbnail(
        self,
        img_buffer: BytesIO,
        project_id: str,
        user_id: str,
    ) -> Optional[str]:
        """
        Upload thumbnail image to Supabase storage.

        Args:
            img_buffer: PNG image buffer
            project_id: Project ID (for path organization)
            user_id: User ID (for path organization)

        Returns:
            str: Public URL of uploaded image, or None if failed
        """
        try:
            # Generate unique filename to avoid caching issues
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            storage_path = f"{THUMBNAIL_PREFIX}/{user_id}/{project_id}/{timestamp}_{unique_id}.png"

            # Read image data
            img_buffer.seek(0)
            img_data = img_buffer.read()
            img_size = len(img_data)

            logger.debug(f"[Thumbnail] Uploading {img_size} bytes to {storage_path}")

            # Upload to Supabase storage (AsyncClient requires await)
            result = await self._storage.storage.from_(THUMBNAIL_BUCKET).upload(
                path=storage_path,
                file=img_data,
                file_options={"content-type": "image/png", "upsert": "true"}
            )

            # Get public URL (sync method, no await needed)
            public_url = self._storage.storage.from_(THUMBNAIL_BUCKET).get_public_url(
                storage_path
            )

            logger.debug(f"[Thumbnail] Uploaded successfully: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"[Thumbnail] Upload failed: {e}")
            return None

    async def _update_project_thumbnail(
        self,
        project_id: str,
        thumbnail_url: str,
    ) -> bool:
        """
        Update project's thumbnail_url in database.

        Args:
            project_id: Project ID to update
            thumbnail_url: New thumbnail URL

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Use AsyncClient to update project directly
            # Note: We update directly via table to avoid loading full project
            result = await self._storage.table("projects").update({
                "thumbnail_url": thumbnail_url,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", project_id).execute()

            if result.data:
                logger.debug(f"[Thumbnail] Updated project {project_id[:8]}... thumbnail_url")
                return True
            else:
                logger.warning(f"[Thumbnail] No rows updated for {project_id[:8]}...")
                return False

        except Exception as e:
            logger.error(f"[Thumbnail] DB update failed for {project_id[:8]}...: {e}")
            return False
