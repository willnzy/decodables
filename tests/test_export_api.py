"""
Tests for Export API endpoints (PRD v3.2)
- ZIP export: Pro only
- PDF export: All tiers
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app import dl_zip, get_project_zip, PdfGenRequest
from db_service import get_project_detail


class TestZIPExport:
    """Test ZIP export permissions (PRD v3.2: Pro only)"""
    
    def test_zip_export_free_denied(self):
        """Free user cannot export ZIP"""
        user = {
            "id": "user_free_123",
            "tier": "free",
        }
        
        req = PdfGenRequest(project_id="test", image_urls=[], texts=[])
        
        with pytest.raises(HTTPException) as exc_info:
            dl_zip(req, user)
        
        assert exc_info.value.status_code == 403
        assert "ZIP export requires Pro plan" in str(exc_info.value.detail)
    
    def test_zip_export_starter_denied(self):
        """Starter user cannot export ZIP (PRD v3.2)"""
        user = {
            "id": "user_starter_123",
            "tier": "starter",
        }
        
        req = PdfGenRequest(project_id="test", image_urls=[], texts=[])
        
        with pytest.raises(HTTPException) as exc_info:
            dl_zip(req, user)
        
        assert exc_info.value.status_code == 403
        assert "ZIP export requires Pro plan" in str(exc_info.value.detail)
        assert "Starter users can export PDF only" in str(exc_info.value.detail)
    
    @patch('app.create_assets_zip')
    @patch('app.BytesIO')
    @patch('app.StreamingResponse')
    def test_zip_export_pro_allowed(self, mock_streaming, mock_bytesio, mock_create_zip):
        """Pro user can export ZIP"""
        user = {
            "id": "user_pro_123",
            "tier": "pro",
        }
        
        from routers.projects import PdfGenRequest
        req = PdfGenRequest(project_id="test", image_urls=["url1", "url2"], texts=["text1", "text2"])
        
        mock_buffer = MagicMock()
        mock_bytesio.return_value = mock_buffer
        
        response = dl_zip(req, user)
        
        mock_create_zip.assert_called_once()
        mock_streaming.assert_called_once()
    
    @patch('app.get_project_detail')
    def test_project_zip_export_free_denied(self, mock_get_project):
        """Free user cannot export project ZIP"""
        user = {
            "id": "user_free_123",
            "tier": "free",
        }
        mock_get_project.return_value = {"id": "project_1", "canvas_data": {}}
        
        with pytest.raises(HTTPException) as exc_info:
            get_project_zip("project_1", user)
        
        assert exc_info.value.status_code == 403
        assert "ZIP export requires Pro plan" in str(exc_info.value.detail)
    
    @patch('app.get_project_detail')
    def test_project_zip_export_starter_denied(self, mock_get_project):
        """Starter user cannot export project ZIP"""
        user = {
            "id": "user_starter_123",
            "tier": "starter",
        }
        mock_get_project.return_value = {"id": "project_1", "canvas_data": {}}
        
        with pytest.raises(HTTPException) as exc_info:
            get_project_zip("project_1", user)
        
        assert exc_info.value.status_code == 403
        assert "ZIP export requires Pro plan" in str(exc_info.value.detail)

