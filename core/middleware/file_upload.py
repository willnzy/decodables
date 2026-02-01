"""
File Upload Middleware - Upload size validation.

@module core.middleware.file_upload
@version 1.1.0

WS-05: Added Content-Length header pre-check to reject oversized
uploads before reading them into memory (DoS prevention).

P3-005: Add file upload size limits to prevent DoS attacks.
"""

import logging
from fastapi import UploadFile, HTTPException, Request
from typing import Optional

logger = logging.getLogger(__name__)

# P3-005: File upload size limits
MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # 10MB


def check_content_length(request: Request, max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES) -> None:
    """
    WS-05: Pre-check Content-Length header to reject oversized uploads
    before reading the request body into memory.

    This is a defense-in-depth measure — the actual file size is still
    validated after reading, but this prevents memory exhaustion from
    extremely large uploads.

    Args:
        request: FastAPI request object
        max_size_bytes: Maximum allowed size in bytes

    Raises:
        HTTPException: 413 if Content-Length exceeds limit
    """
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            cl = int(content_length)
            if cl > max_size_bytes:
                max_mb = max_size_bytes / (1024 * 1024)
                logger.warning(
                    f"[FileUpload] Content-Length pre-check failed: "
                    f"{cl / 1024 / 1024:.2f}MB > {max_mb}MB"
                )
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum allowed: {max_mb:.0f}MB"
                )
        except ValueError:
            pass  # Invalid Content-Length header, let the actual read handle it


async def validate_file_size(
    file: UploadFile,
    max_size_mb: Optional[int] = None
) -> UploadFile:
    """
    Validate uploaded file size.

    P3-005: Prevent DoS attacks by limiting file upload size.

    Args:
        file: The uploaded file
        max_size_mb: Custom max size in MB (default: 10MB)

    Returns:
        The file if valid

    Raises:
        HTTPException: 413 if file exceeds size limit

    Usage:
        ```python
        from core.middleware.file_upload import validate_file_size

        @router.post("/upload")
        async def upload(file: UploadFile = Depends(validate_file_size)):
            ...
        ```
    """
    max_size = (max_size_mb or MAX_UPLOAD_SIZE_MB) * 1024 * 1024

    # Read file content to check size
    content = await file.read()
    file_size = len(content)

    # Reset file position for further processing
    await file.seek(0)

    if file_size > max_size:
        logger.warning(
            f"[FileUpload] File too large: {file.filename} "
            f"({file_size / 1024 / 1024:.2f}MB > {max_size / 1024 / 1024}MB)"
        )
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum allowed size ({max_size / 1024 / 1024}MB)"
        )

    logger.debug(
        f"[FileUpload] File size validated: {file.filename} "
        f"({file_size / 1024 / 1024:.2f}MB)"
    )

    return file


def create_file_size_validator(max_size_mb: int):
    """
    Create a custom file size validator with specific size limit.

    Args:
        max_size_mb: Maximum file size in MB

    Returns:
        Validator function

    Usage:
        ```python
        from core.middleware.file_upload import create_file_size_validator

        validate_5mb = create_file_size_validator(5)

        @router.post("/upload-small")
        async def upload(file: UploadFile = Depends(validate_5mb)):
            ...
        ```
    """
    async def validator(file: UploadFile) -> UploadFile:
        return await validate_file_size(file, max_size_mb)

    return validator
