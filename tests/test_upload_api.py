"""
Tests for Upload API endpoints (PRD v3.2)
- Personal upload: Pro only
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, UploadFile
from io import BytesIO

from app import upload_asset


class TestPersonalUpload:
    """Test personal asset upload permissions (PRD v3.2: Pro only)"""
    
    def test_upload_free_denied(self):
        """Free user cannot upload personal assets"""
        user = {
            "id": "user_free_123",
            "tier": "free",
        }
        
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(b"fake image data"),
            headers={"content-type": "image/jpeg"}
        )
        
        with pytest.raises(HTTPException) as exc_info:
            upload_asset(file, None, user)
        
        assert exc_info.value.status_code == 403
        assert "Personal asset upload requires Pro plan" in str(exc_info.value.detail)
    
    def test_upload_starter_denied(self):
        """Starter user cannot upload personal assets"""
        user = {
            "id": "user_starter_123",
            "tier": "starter",
        }
        
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(b"fake image data"),
            headers={"content-type": "image/jpeg"}
        )
        
        with pytest.raises(HTTPException) as exc_info:
            upload_asset(file, None, user)
        
        assert exc_info.value.status_code == 403
        assert "Personal asset upload requires Pro plan" in str(exc_info.value.detail)
    
    @patch('app.save_asset')
    @patch('app.supabase')
    def test_upload_pro_allowed(self, mock_supabase, mock_save_asset):
        """Pro user can upload personal assets"""
        user = {
            "id": "user_pro_123",
            "tier": "pro",
        }
        
        # Mock Supabase storage
        mock_storage = MagicMock()
        mock_storage.from_.return_value.upload.return_value = None
        mock_storage.from_.return_value.get_public_url.return_value = "https://example.com/image.jpg"
        mock_supabase.storage = mock_storage
        
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(b"fake image data"),
            headers={"content-type": "image/jpeg"}
        )
        
        response = upload_asset(file, "project_1", user)
        
        assert "url" in response
        mock_save_asset.assert_called_once()

