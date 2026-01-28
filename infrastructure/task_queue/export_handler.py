"""
Export Task Handler - Background worker for PDF/ZIP exports.

@module infrastructure.task_queue.export_handler
@version 1.0.0

This module handles PDF and ZIP export tasks in background workers.
Uses the existing task queue infrastructure (RQ + Redis).

Entry point: execute_export_task() - Called by RQ worker
"""

import os
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from io import BytesIO

logger = logging.getLogger(__name__)

# File size limits (security)
MAX_EXPORT_SIZE_MB = 50

# Storage bucket
EXPORT_BUCKET = "make-decodables-u"


class ExportTaskHandler:
    """
    Handles PDF and ZIP export tasks in background worker.

    Features:
    - Async-optimized PDF generation (run_in_threadpool)
    - Concurrent image downloads for ZIP (aiohttp + asyncio.gather)
    - Real-time progress tracking via Redis PubSub
    - Automatic file upload to Supabase Storage
    - 7-day retention with automatic cleanup
    """

    def __init__(self, export_service, storage_service, progress_tracker, db_client):
        """
        Initialize export handler.

        Args:
            export_service: ExportService instance
            storage_service: StorageService instance
            progress_tracker: ProgressTracker instance
            db_client: Database client for task updates
        """
        self.export_service = export_service
        self.storage = storage_service
        self.progress = progress_tracker
        self.db = db_client
        self.worker_id = f"worker_{os.getpid()}"

    async def execute_pdf_export(
        self,
        task_id: str,
        user_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Execute PDF export task.

        Steps:
        1. Mark task as started (0%)
        2. Generate PDF with run_in_threadpool (0-50%)
        3. Upload to Supabase Storage (50-90%)
        4. Update database task record (90-100%)
        5. Mark task as completed (100%)

        Args:
            task_id: Task ID
            user_id: User ID
            project_id: Project ID to export

        Returns:
            Result dict with download_url, filename, size_bytes, expires_at

        Raises:
            Exception: If export fails
        """
        # Mark as started
        self.progress.mark_started(task_id, self.worker_id)
        self.progress.update(
            task_id,
            status="processing",
            progress=0,
            current_step=1,
            total_steps=4,
            message="Starting PDF generation..."
        )

        try:
            # Step 1: Generate PDF (0-50%)
            logger.info(f"[Export:{task_id}] Generating PDF for project {project_id}")
            buf, title = await self.export_service.export_pdf_async(user_id, project_id)

            self.progress.update(
                task_id,
                progress=50,
                current_step=2,
                message="PDF generated, uploading to storage..."
            )

            # Step 2: Upload to storage (50-90%)
            file_size = buf.tell()
            if file_size > MAX_EXPORT_SIZE_MB * 1024 * 1024:
                raise ValueError(f"PDF exceeds {MAX_EXPORT_SIZE_MB} MB limit")

            # Reset buffer position for reading
            buf.seek(0)

            # Generate storage path: {user_id}/temp/{YYYY-MM-DD}/{task_id}/export.pdf
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            storage_path = f"{user_id}/temp/{date_str}/{task_id}/export.pdf"

            logger.info(f"[Export:{task_id}] Uploading PDF to {storage_path} ({file_size} bytes)")

            upload_result = await self.storage.upload_file(
                bucket=EXPORT_BUCKET,
                path=storage_path,
                file_data=buf.read(),
                content_type="application/pdf",
                visibility="private"  # Requires auth to download
            )

            if not upload_result.success:
                raise Exception(f"Upload failed: {upload_result.error}")

            self.progress.update(
                task_id,
                progress=90,
                current_step=3,
                message="Upload complete, finalizing..."
            )

            # Step 3: Build result (90-100%)
            # Calculate expiration (7 days from now)
            expires_at = datetime.now(timezone.utc)
            expires_at = expires_at.replace(day=expires_at.day + 7)

            # Sanitize filename (remove unsafe characters)
            safe_filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_filename:
                safe_filename = "export"
            safe_filename += ".pdf"

            result = {
                "download_url": upload_result.url,
                "filename": safe_filename,
                "size_bytes": file_size,
                "expires_at": expires_at.isoformat(),
                "task_id": task_id,
                "export_type": "pdf",
            }

            # Step 4: Update database (100%)
            await self._update_db_task(task_id, "completed", result)

            # Mark completed
            self.progress.mark_completed(task_id, result)

            logger.info(f"[Export:{task_id}] PDF export completed: {upload_result.url}")
            return result

        except Exception as e:
            logger.error(f"[Export:{task_id}] PDF export failed: {e}")
            self.progress.mark_failed(task_id, str(e), "PDF_EXPORT_FAILED")
            await self._update_db_task(task_id, "failed", error=str(e))
            raise

    async def execute_zip_export(
        self,
        task_id: str,
        user_id: str,
        project_id: str,
        tier: str
    ) -> Dict[str, Any]:
        """
        Execute ZIP export task with concurrent image downloads.

        Steps:
        1. Mark task as started (0%)
        2. Download images concurrently (aiohttp + asyncio.gather) (0-70%)
        3. Create ZIP in threadpool (70-90%)
        4. Upload to Supabase Storage (90-95%)
        5. Update database and mark completed (95-100%)

        Args:
            task_id: Task ID
            user_id: User ID
            project_id: Project ID to export
            tier: User tier (for access control)

        Returns:
            Result dict with download_url, filename, size_bytes, expires_at

        Raises:
            Exception: If export fails
        """
        # Mark as started
        self.progress.mark_started(task_id, self.worker_id)
        self.progress.update(
            task_id,
            status="processing",
            progress=0,
            current_step=1,
            total_steps=5,
            message="Starting ZIP export..."
        )

        try:
            # Step 1: Generate ZIP with concurrent downloads (0-90%)
            logger.info(f"[Export:{task_id}] Generating ZIP for project {project_id}")

            # Pass progress callback for real-time updates
            async def progress_callback(current: int, total: int, message: str):
                # Map download progress to 0-70%
                progress_pct = int((current / total) * 70) if total > 0 else 0
                self.progress.update(
                    task_id,
                    progress=progress_pct,
                    current_step=2,
                    message=message
                )

            buf, title = await self.export_service.export_zip_async(
                user_id,
                project_id,
                tier,
                progress_callback=progress_callback
            )

            self.progress.update(
                task_id,
                progress=90,
                current_step=3,
                message="ZIP created, uploading to storage..."
            )

            # Step 2: Upload to storage (90-95%)
            file_size = buf.tell()
            if file_size > MAX_EXPORT_SIZE_MB * 1024 * 1024:
                raise ValueError(f"ZIP exceeds {MAX_EXPORT_SIZE_MB} MB limit")

            buf.seek(0)

            # Generate storage path
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            storage_path = f"{user_id}/temp/{date_str}/{task_id}/export.zip"

            logger.info(f"[Export:{task_id}] Uploading ZIP to {storage_path} ({file_size} bytes)")

            upload_result = await self.storage.upload_file(
                bucket=EXPORT_BUCKET,
                path=storage_path,
                file_data=buf.read(),
                content_type="application/zip",
                visibility="private"
            )

            if not upload_result.success:
                raise Exception(f"Upload failed: {upload_result.error}")

            self.progress.update(
                task_id,
                progress=95,
                current_step=4,
                message="Upload complete, finalizing..."
            )

            # Step 3: Build result (95-100%)
            expires_at = datetime.now(timezone.utc)
            expires_at = expires_at.replace(day=expires_at.day + 7)

            safe_filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_filename:
                safe_filename = "export"
            safe_filename += ".zip"

            result = {
                "download_url": upload_result.url,
                "filename": safe_filename,
                "size_bytes": file_size,
                "expires_at": expires_at.isoformat(),
                "task_id": task_id,
                "export_type": "zip",
            }

            # Step 4: Update database (100%)
            await self._update_db_task(task_id, "completed", result)

            # Mark completed
            self.progress.mark_completed(task_id, result)

            logger.info(f"[Export:{task_id}] ZIP export completed: {upload_result.url}")
            return result

        except Exception as e:
            logger.error(f"[Export:{task_id}] ZIP export failed: {e}")
            self.progress.mark_failed(task_id, str(e), "ZIP_EXPORT_FAILED")
            await self._update_db_task(task_id, "failed", error=str(e))
            raise

    async def _update_db_task(
        self,
        task_id: str,
        status: str,
        result: Dict = None,
        error: str = None
    ):
        """
        Update task record in database.

        Args:
            task_id: Task ID
            status: Task status (pending/processing/completed/failed)
            result: Result data (for completed tasks)
            error: Error message (for failed tasks)
        """
        try:
            update_data = {
                "status": status,
                "worker_id": self.worker_id,
            }

            if result:
                update_data["result"] = result
                update_data["result_url"] = result.get("download_url")
                update_data["result_metadata"] = {
                    "filename": result.get("filename"),
                    "size_bytes": result.get("size_bytes"),
                    "expires_at": result.get("expires_at"),
                }

            if error:
                update_data["error_message"] = error

            if status in ("completed", "failed"):
                update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Update database
            self.db.table("generation_tasks").update(update_data).eq(
                "id", task_id
            ).execute()

            logger.debug(f"[Export:{task_id}] Database updated: {status}")

        except Exception as e:
            logger.warning(f"[Export:{task_id}] Failed to update DB: {e}")


# ==========================================
# RQ Worker Entry Point
# ==========================================

def execute_export_task(
    task_id: str,
    user_id: str,
    project_id: str,
    export_type: str,
    tier: str = "t1"
):
    """
    RQ worker entry point for export tasks (SYNC wrapper).

    This function is called by RQ worker (synchronous context).
    It wraps the async handler execution in an event loop.

    Args:
        task_id: Task ID (UUID string)
        user_id: User ID
        project_id: Project ID to export
        export_type: "pdf" or "zip"
        tier: User tier (for tier-based access control)

    Returns:
        Result dict with download URL and metadata

    Raises:
        ValueError: If export_type is invalid
        Exception: If export fails
    """
    logger.info(f"[Export:{task_id}] Starting {export_type} export for user {user_id[:8]}...")

    # Import dependencies (avoid circular imports)
    # v3.31: Use create_task_async_client() to avoid "Event loop is closed" error
    # See docs/main/backend-architecture.md 1.3.1.3
    from core.database import create_task_async_client
    from shared.storage import get_storage_service
    from infrastructure.repositories.project_repository import SupabaseProjectRepository
    from domains.export import ExportService
    from infrastructure.task_queue.progress_tracker import progress_tracker
    import asyncio

    async def _execute_export():
        """Execute export with fresh AsyncClient (all in one event loop)"""
        db_client = await create_task_async_client()

        try:
            project_repo = SupabaseProjectRepository(db_client)
            export_service = ExportService(project_repository=project_repo)
            storage_service = get_storage_service()

            # Create handler
            handler = ExportTaskHandler(
                export_service=export_service,
                storage_service=storage_service,
                progress_tracker=progress_tracker,
                db_client=db_client
            )

            if export_type == "pdf":
                result = await handler.execute_pdf_export(task_id, user_id, project_id)
            elif export_type == "zip":
                result = await handler.execute_zip_export(task_id, user_id, project_id, tier)
            else:
                raise ValueError(f"Unknown export type: {export_type}")

            return result
        finally:
            # Cleanup: close client after task
            if hasattr(db_client, 'aclose'):
                await db_client.aclose()
                logger.info("[DB] Task-specific async client closed")

    result = asyncio.run(_execute_export())
    logger.info(f"[Export:{task_id}] Export completed successfully")
    return result
