"""
Tests for Image Generation API (PRD v3.2)
- Free/Starter: flux-schnell (standard model)
- Pro: flux-dev (high-quality model)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from app import gen_images, ImageGenRequest


class TestImageGenerationModelSelection:
    """Test AI model selection based on tier (PRD v3.2)"""
    
    @patch('app.generate_8_images')
    @patch('app.credit_deduct')
    @patch('app.save_asset')
    def test_gen_images_free_uses_schnell(self, mock_save, mock_deduct, mock_generate):
        """Free user uses flux-schnell model"""
        user = {
            "id": "user_free_123",
            "tier": "free",
        }
        
        mock_deduct.return_value = {
            "total": 45,
            "balance_monthly": 0,
            "balance_permanent": 45,
        }
        mock_generate.return_value = (["url1", "url2"], "task_123")
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        response = gen_images(None, req, user)
        
        # Check that generate_8_images was called with flux-schnell
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert call_args[0][0] == ["test prompt"]  # prompts
        assert call_args[1]["model"] == "flux-schnell"  # model parameter
        
        assert "model_used" in response
        assert response["model_used"] == "flux-schnell"
    
    @patch('app.generate_8_images')
    @patch('app.credit_deduct')
    @patch('app.save_asset')
    def test_gen_images_starter_uses_schnell(self, mock_save, mock_deduct, mock_generate):
        """Starter user uses flux-schnell model"""
        user = {
            "id": "user_starter_123",
            "tier": "starter",
        }
        
        mock_deduct.return_value = {
            "total": 495,
            "balance_monthly": 495,
            "balance_permanent": 0,
        }
        mock_generate.return_value = (["url1", "url2"], "task_123")
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        response = gen_images(None, req, user)
        
        call_args = mock_generate.call_args
        assert call_args[1]["model"] == "flux-schnell"
        assert response["model_used"] == "flux-schnell"
    
    @patch('app.generate_8_images')
    @patch('app.credit_deduct')
    @patch('app.save_asset')
    def test_gen_images_pro_uses_dev(self, mock_save, mock_deduct, mock_generate):
        """Pro user uses flux-dev model (high-quality)"""
        user = {
            "id": "user_pro_123",
            "tier": "pro",
        }
        
        mock_deduct.return_value = {
            "total": 995,
            "balance_monthly": 995,
            "balance_permanent": 0,
        }
        mock_generate.return_value = (["url1", "url2"], "task_123")
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        response = gen_images(None, req, user)
        
        call_args = mock_generate.call_args
        assert call_args[1]["model"] == "flux-dev"  # Pro uses high-quality model
        assert response["model_used"] == "flux-dev"
    
    @patch('app.credit_deduct')
    def test_gen_images_insufficient_credits(self, mock_deduct):
        """Should raise 402 when user has insufficient credits"""
        user = {
            "id": "user_free_123",
            "tier": "free",
        }
        
        mock_deduct.side_effect = Exception("INSUFFICIENT credits")
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        with pytest.raises(HTTPException) as exc_info:
            gen_images(None, req, user)
        
        assert exc_info.value.status_code == 402
        assert "Insufficient credits" in str(exc_info.value.detail)

