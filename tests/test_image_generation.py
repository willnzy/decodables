"""
Tests for Image Generation API (PRD v3.2)
- Free/Starter: flux-schnell (standard model)
- Pro: flux-dev (high-quality model)

v3.21: Updated to test unified AI service integration
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException


class TestImageGenerationModelSelection:
    """Test AI model selection based on tier (PRD v3.2)"""
    
    @pytest.mark.asyncio
    @patch('app.generate_8_images', new_callable=AsyncMock)
    @patch('app.credit_deduct')
    @patch('app.save_asset')
    @patch('app.track_ai_generation')
    @patch('app.get_request_timezone')
    async def test_gen_images_free_uses_schnell(
        self, mock_tz, mock_track, mock_save, mock_deduct, mock_generate
    ):
        """Free user uses flux-schnell model"""
        from app import gen_images, ImageGenRequest
        
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
        mock_tz.return_value = "UTC"
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.headers = {}
        
        response = await gen_images(mock_request, req, user)
        
        # Check that generate_8_images was called with correct parameters
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert call_args[0][0] == ["test prompt"]  # prompts
        assert call_args[1]["model"] == "flux-schnell"  # model parameter
        # v3.21: Check that tier is passed
        assert call_args[1]["tier"] == "free"
        assert call_args[1]["user_id"] == "user_free_123"
        
        assert "model_used" in response
        assert response["model_used"] == "flux-schnell"
    
    @pytest.mark.asyncio
    @patch('app.generate_8_images', new_callable=AsyncMock)
    @patch('app.credit_deduct')
    @patch('app.save_asset')
    @patch('app.track_ai_generation')
    @patch('app.get_request_timezone')
    async def test_gen_images_starter_uses_schnell(
        self, mock_tz, mock_track, mock_save, mock_deduct, mock_generate
    ):
        """Starter user uses flux-schnell model"""
        from app import gen_images, ImageGenRequest
        
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
        mock_tz.return_value = "UTC"
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        mock_request = MagicMock()
        mock_request.headers = {}
        
        response = await gen_images(mock_request, req, user)
        
        call_args = mock_generate.call_args
        assert call_args[1]["model"] == "flux-schnell"
        assert call_args[1]["tier"] == "starter"
        assert response["model_used"] == "flux-schnell"
    
    @pytest.mark.asyncio
    @patch('app.generate_8_images', new_callable=AsyncMock)
    @patch('app.credit_deduct')
    @patch('app.save_asset')
    @patch('app.track_ai_generation')
    @patch('app.get_request_timezone')
    async def test_gen_images_pro_uses_dev(
        self, mock_tz, mock_track, mock_save, mock_deduct, mock_generate
    ):
        """Pro user uses flux-dev model (high-quality)"""
        from app import gen_images, ImageGenRequest
        
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
        mock_tz.return_value = "UTC"
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        mock_request = MagicMock()
        mock_request.headers = {}
        
        response = await gen_images(mock_request, req, user)
        
        call_args = mock_generate.call_args
        assert call_args[1]["model"] == "flux-dev"  # Pro uses high-quality model
        assert call_args[1]["tier"] == "pro"
        assert response["model_used"] == "flux-dev"
    
    @pytest.mark.asyncio
    @patch('app.credit_deduct')
    async def test_gen_images_insufficient_credits(self, mock_deduct):
        """Should raise 402 when user has insufficient credits"""
        from app import gen_images, ImageGenRequest
        
        user = {
            "id": "user_free_123",
            "tier": "free",
        }
        
        mock_deduct.side_effect = Exception("INSUFFICIENT credits")
        
        req = ImageGenRequest(prompts=["test prompt"], project_id="project_1")
        
        mock_request = MagicMock()
        mock_request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await gen_images(mock_request, req, user)
        
        assert exc_info.value.status_code == 402
        assert "Insufficient credits" in str(exc_info.value.detail)


class TestPromptEnhancementIntegration:
    """Test prompt enhancement with unified AI service"""
    
    @pytest.mark.asyncio
    @patch('app.generate_8_images', new_callable=AsyncMock)
    @patch('app.enhance_prompt')
    @patch('app.credit_deduct')
    @patch('app.save_asset')
    @patch('app.track_ai_generation')
    @patch('app.get_request_timezone')
    async def test_enhance_prompt_passes_user_context(
        self, mock_tz, mock_track, mock_save, mock_deduct, mock_enhance, mock_generate
    ):
        """Prompt enhancement receives user_id and tier"""
        from app import gen_images, ImageGenRequest
        
        user = {
            "id": "user_pro_456",
            "tier": "pro",
        }
        
        mock_deduct.return_value = {"total": 100}
        mock_enhance.return_value = {
            "enhanced_prompt": "Enhanced detailed prompt...",
            "key_elements": ["cat", "garden"],
            "composition": "centered"
        }
        mock_generate.return_value = (["url1"], "task_456")
        mock_tz.return_value = "UTC"
        
        # Request with theme triggers enhance_prompt
        req = ImageGenRequest(
            prompts=["original prompt"],
            project_id="project_1",
            theme="A cat in a garden",
            character="orange tabby cat",
            style="cartoon"
        )
        
        mock_request = MagicMock()
        mock_request.headers = {}
        
        await gen_images(mock_request, req, user)
        
        # Check enhance_prompt was called with user context
        mock_enhance.assert_called_once()
        call_args = mock_enhance.call_args
        assert call_args[1]["user_id"] == "user_pro_456"
        assert call_args[1]["tier"] == "pro"
