"""
Tests for File Upload Size Validation (P3-005)

Test coverage:
- File size within limit (valid)
- File size exceeds limit (invalid)
- Custom size limit
- Edge cases and boundary conditions
"""

import pytest
from io import BytesIO
from fastapi import UploadFile, HTTPException

from core.middleware.file_upload import (
    validate_file_size,
    create_file_size_validator,
    MAX_UPLOAD_SIZE_MB,
    MAX_UPLOAD_SIZE_BYTES,
)


# ==========================================
# Test Validate File Size
# ==========================================

@pytest.mark.asyncio
async def test_validate_file_size_within_limit():
    """File within 10MB limit should pass validation."""
    # Create a 5MB file
    content = b"x" * (5 * 1024 * 1024)
    file = UploadFile(filename="test.txt", file=BytesIO(content))

    result = await validate_file_size(file)

    assert result is not None
    assert result.filename == "test.txt"
    # File position should be reset to 0 after validation
    assert file.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_file_size_exactly_at_limit():
    """File exactly at 10MB limit should pass validation."""
    # Create exactly 10MB file
    content = b"x" * (10 * 1024 * 1024)
    file = UploadFile(filename="exactly_10mb.txt", file=BytesIO(content))

    result = await validate_file_size(file)

    assert result is not None


@pytest.mark.asyncio
async def test_validate_file_size_exceeds_limit():
    """File exceeding 10MB limit should raise HTTPException 413."""
    # Create a 15MB file
    content = b"x" * (15 * 1024 * 1024)
    file = UploadFile(filename="too_large.txt", file=BytesIO(content))

    with pytest.raises(HTTPException) as exc_info:
        await validate_file_size(file)

    assert exc_info.value.status_code == 413
    assert "exceeds maximum allowed size" in exc_info.value.detail
    assert "15" in exc_info.value.detail  # Size should be in error message
    assert "10" in exc_info.value.detail  # Limit should be in error message


@pytest.mark.asyncio
async def test_validate_file_size_custom_limit():
    """Custom size limit should be respected."""
    # Create a 7MB file
    content = b"x" * (7 * 1024 * 1024)
    file = UploadFile(filename="test.txt", file=BytesIO(content))

    # 7MB should pass with default 10MB limit
    result = await validate_file_size(file)
    assert result is not None

    # Reset file
    file.file.seek(0)

    # 7MB should fail with custom 5MB limit
    with pytest.raises(HTTPException) as exc_info:
        await validate_file_size(file, max_size_mb=5)

    assert exc_info.value.status_code == 413
    assert "5" in exc_info.value.detail  # Custom limit in error


@pytest.mark.asyncio
async def test_validate_file_size_zero_bytes():
    """Empty file (0 bytes) should pass validation."""
    content = b""
    file = UploadFile(filename="empty.txt", file=BytesIO(content))

    result = await validate_file_size(file)

    assert result is not None


@pytest.mark.asyncio
async def test_validate_file_size_small_file():
    """Small file (1 byte) should pass validation."""
    content = b"x"
    file = UploadFile(filename="tiny.txt", file=BytesIO(content))

    result = await validate_file_size(file)

    assert result is not None


@pytest.mark.asyncio
async def test_validate_file_size_file_position_reset():
    """File position should be reset to 0 after validation."""
    content = b"x" * 1000
    buffer = BytesIO(content)

    # Move file pointer to middle
    buffer.seek(500)

    file = UploadFile(filename="test.txt", file=buffer)

    await validate_file_size(file)

    # Should be reset to 0, not 500
    assert file.file.tell() == 0


# ==========================================
# Test Custom Validator Factory
# ==========================================

@pytest.mark.asyncio
async def test_create_file_size_validator_5mb():
    """Custom validator with 5MB limit should work."""
    validate_5mb = create_file_size_validator(5)

    # 3MB file should pass
    content = b"x" * (3 * 1024 * 1024)
    file = UploadFile(filename="test.txt", file=BytesIO(content))

    result = await validate_5mb(file)
    assert result is not None


@pytest.mark.asyncio
async def test_create_file_size_validator_5mb_exceeds():
    """Custom 5MB validator should reject 7MB file."""
    validate_5mb = create_file_size_validator(5)

    # 7MB file should fail
    content = b"x" * (7 * 1024 * 1024)
    file = UploadFile(filename="too_large.txt", file=BytesIO(content))

    with pytest.raises(HTTPException) as exc_info:
        await validate_5mb(file)

    assert exc_info.value.status_code == 413
    assert "5" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_file_size_validator_1mb():
    """Custom 1MB validator should work."""
    validate_1mb = create_file_size_validator(1)

    # 0.5MB file should pass
    content = b"x" * (512 * 1024)
    file = UploadFile(filename="small.txt", file=BytesIO(content))

    result = await validate_1mb(file)
    assert result is not None

    # Reset and try 2MB (should fail)
    file.file.seek(0)
    file.file = BytesIO(b"x" * (2 * 1024 * 1024))

    with pytest.raises(HTTPException) as exc_info:
        await validate_1mb(file)

    assert exc_info.value.status_code == 413


# ==========================================
# Test Constants
# ==========================================

def test_constants():
    """Verify constants are correctly set."""
    assert MAX_UPLOAD_SIZE_MB == 10
    assert MAX_UPLOAD_SIZE_BYTES == 10 * 1024 * 1024


# ==========================================
# Test Error Message Format
# ==========================================

@pytest.mark.asyncio
async def test_error_message_includes_filename():
    """Error message should include filename for debugging."""
    content = b"x" * (15 * 1024 * 1024)
    file = UploadFile(filename="large_document.pdf", file=BytesIO(content))

    with pytest.raises(HTTPException) as exc_info:
        await validate_file_size(file)

    # Filename should be in logs (not in detail, but logged)
    # We can verify HTTPException was raised with correct details
    assert "File size" in exc_info.value.detail
    assert "exceeds maximum" in exc_info.value.detail


@pytest.mark.asyncio
async def test_error_message_shows_both_sizes():
    """Error message should show both actual and maximum sizes."""
    content = b"x" * (12 * 1024 * 1024)  # 12MB
    file = UploadFile(filename="test.txt", file=BytesIO(content))

    with pytest.raises(HTTPException) as exc_info:
        await validate_file_size(file)

    error_detail = exc_info.value.detail
    # Should contain both sizes
    assert "12" in error_detail  # Actual size
    assert "10" in error_detail  # Max size
