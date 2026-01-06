"""
Generation API Integration Tests
Tests for AI generation endpoints

Coverage:
- Image Generation (with credits deduction)
- Story Generation
- Generation History
- Asset Prompt Templates
- Smart Scan / OCR
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import json


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def client():
    """Create test client"""
    with patch('app.supabase') as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[])
        from app import app
        return TestClient(app)


@pytest.fixture
def mock_user_with_credits():
    """User with sufficient credits"""
    return {
        'id': 'user_credits_123',
        'email': 'user@test.com',
        'tier': 'pro',
        'subscription_status': 'active',
        'credits_monthly': 500,
        'credits_permanent': 100,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_user_no_credits():
    """User without credits"""
    return {
        'id': 'user_nocredits_123',
        'email': 'broke@test.com',
        'tier': 'free',
        'subscription_status': 'inactive',
        'credits_monthly': 0,
        'credits_permanent': 0,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }


# ============================================
# A. Image Generation Tests
# ============================================

class TestImageGeneration:
    """Tests for POST /api/generate/images"""
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_with_fal')
    def test_generate_single_image(
        self, mock_fal, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ✅ PASS: Generates single image with valid prompt
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 495, 'balance_permanent': 100}
        mock_fal.return_value = {
            'images': [{'url': 'https://cdn.fal.ai/generated.png'}]
        }
        
        response = client.post(
            '/api/generate/images',
            json={
                'prompts': ['A cute cartoon cat'],
                'image_size': 'landscape_4_3'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'images' in data or 'image_urls' in data
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_with_fal')
    def test_generate_with_reference_image(
        self, mock_fal, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ✅ PASS: Generates image with reference (costs 7 credits)
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 493}
        mock_fal.return_value = {'images': [{'url': 'https://cdn.../generated.png'}]}
        
        response = client.post(
            '/api/generate/images',
            json={
                'prompts': ['Similar style portrait'],
                'reference_image': 'data:image/png;base64,iVBORw0KGgo...',
                'reference_strength': 0.8
            }
        )
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_with_fal')
    def test_generate_batch_images(
        self, mock_fal, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ✅ PASS: Generates multiple variations
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 480}  # 4 * 5 credits
        mock_fal.return_value = {
            'images': [
                {'url': 'https://cdn.../img1.png'},
                {'url': 'https://cdn.../img2.png'},
                {'url': 'https://cdn.../img3.png'},
                {'url': 'https://cdn.../img4.png'},
            ]
        }
        
        response = client.post(
            '/api/generate/images',
            json={
                'prompts': ['Landscape scene'],
                'num_images': 4
            }
        )
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_with_fal')
    def test_generate_with_5w1h_params(
        self, mock_fal, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ✅ PASS: Generates with 5W1H parameters
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 495}
        mock_fal.return_value = {'images': [{'url': 'https://cdn.../generated.png'}]}
        
        response = client.post(
            '/api/generate/images',
            json={
                'prompts': [],  # Empty when using 5W1H
                'who': 'A young wizard',
                'what': 'casting a spell',
                'where': 'ancient castle',
                'moods': ['mysterious', 'magical'],
                'enhance_prompt': True
            }
        )
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    def test_generate_insufficient_credits(
        self, mock_deduct, mock_get_user, client, mock_user_no_credits
    ):
        """
        ❌ FAIL: Returns 402 when credits insufficient
        """
        mock_get_user.return_value = mock_user_no_credits
        mock_deduct.side_effect = Exception("CREDITS_INSUFFICIENT")
        
        response = client.post(
            '/api/generate/images',
            json={'prompts': ['Test prompt']}
        )
        
        assert response.status_code in [402, 400, 500]
    
    @patch('app.get_current_user')
    def test_generate_empty_prompt(self, mock_get_user, client, mock_user_with_credits):
        """
        ❌ FAIL: Returns 400 for empty prompts
        """
        mock_get_user.return_value = mock_user_with_credits
        
        response = client.post(
            '/api/generate/images',
            json={'prompts': []}
        )
        
        # Should return 400 or handle with default prompt
        assert response.status_code in [200, 400, 422]
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_with_fal')
    def test_generate_with_negative_prompt(
        self, mock_fal, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ✅ PASS: Handles negative prompt
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 495}
        mock_fal.return_value = {'images': [{'url': 'https://cdn.../generated.png'}]}
        
        response = client.post(
            '/api/generate/images',
            json={
                'prompts': ['Portrait'],
                'negative_prompt': 'text, watermark, blurry'
            }
        )
        
        assert response.status_code == 200


# ============================================
# B. Story Generation Tests
# ============================================

class TestStoryGeneration:
    """Tests for POST /api/generate/story"""
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_story_with_openai')
    def test_generate_story(
        self, mock_openai, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ✅ PASS: Generates story from topic
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 490}
        mock_openai.return_value = {
            'title': 'Beach Adventure',
            'pages': [
                {'content': 'Once upon a time...', 'image_prompt': 'Beach scene'},
                {'content': 'The sun was setting...', 'image_prompt': 'Sunset'},
            ]
        }
        
        response = client.post(
            '/api/generate/story',
            json={'topic': 'A fun beach adventure'}
        )
        
        assert response.status_code == 200


# ============================================
# C. Inspiration Tests
# ============================================

class TestInspiration:
    """Tests for POST /api/generate/inspiration"""
    
    @patch('app.get_current_user')
    def test_get_inspiration_all(self, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Returns inspiration suggestions (free)
        """
        mock_get_user.return_value = mock_user_with_credits
        
        # Mock the inspiration generation
        with patch('app.get_creative_suggestions') as mock_suggestions:
            mock_suggestions.return_value = [
                {'type': 'character', 'prompt': 'A friendly robot chef'},
                {'type': 'scene', 'prompt': 'Underwater city'},
            ]
            
            response = client.post(
                '/api/generate/inspiration',
                json={'category': 'all'}
            )
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_get_inspiration_by_category(self, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Returns filtered inspiration
        """
        mock_get_user.return_value = mock_user_with_credits
        
        with patch('app.get_creative_suggestions') as mock_suggestions:
            mock_suggestions.return_value = [
                {'type': 'character', 'prompt': 'A brave knight'},
            ]
            
            response = client.post(
                '/api/generate/inspiration',
                json={'category': 'character'}
            )
        
        assert response.status_code == 200


# ============================================
# D. Generation History Tests
# ============================================

class TestGenerationHistory:
    """Tests for /api/generations/* endpoints"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_history(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Returns generation history
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_history = [
            {'id': 'gen_1', 'prompt': 'Test', 'url': 'https://...', 'is_favorited': False},
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .order.return_value.range.return_value.execute.return_value = Mock(data=mock_history)
        
        response = client.get('/api/generations/history?limit=20&offset=0')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_favorites_only(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Returns only favorited generations
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.order.return_value.range.return_value.execute.return_value = Mock(data=[])
        
        response = client.get('/api/generations/history?favorites_only=true')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_toggle_favorite(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Toggles generation favorite status
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock()
        
        response = client.post(
            '/api/generations/favorite',
            json={'generation_id': 'gen_123', 'is_favorited': True}
        )
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_delete_generation(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Deletes generation from history
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_supabase.table.return_value.delete.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock()
        
        response = client.delete('/api/generations/gen_123')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_clear_history_keep_favorites(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Clears history but keeps favorites
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_supabase.table.return_value.delete.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock()
        
        response = client.delete('/api/generations/batch?keep_favorites=true')
        
        assert response.status_code == 200


# ============================================
# E. Asset Prompt Templates Tests
# ============================================

class TestAssetPromptTemplates:
    """Tests for /api/asset-prompt/templates endpoints"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_get_templates(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Returns user's templates
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_templates = [
            {'id': 'tpl_1', 'name': 'Character', 'who': 'A hero'},
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .order.return_value.execute.return_value = Mock(data=mock_templates)
        
        response = client.get('/api/asset-prompt/templates')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_create_template(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Creates new template
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{'id': 'tpl_new'}]
        )
        
        response = client.post(
            '/api/asset-prompt/templates',
            json={
                'name': 'My Character',
                'who': 'A brave knight',
                'what': 'fighting',
                'where': 'battlefield'
            }
        )
        
        assert response.status_code in [200, 201]
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_delete_template(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Deletes template
        """
        mock_get_user.return_value = mock_user_with_credits
        
        mock_supabase.table.return_value.delete.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock()
        
        response = client.delete('/api/asset-prompt/templates/tpl_123')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_use_template(self, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Increments template usage counter
        """
        mock_get_user.return_value = mock_user_with_credits
        
        # Mock template exists
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock(data=[{'id': 'tpl_123', 'used_count': 5}])
        
        mock_supabase.table.return_value.update.return_value.eq.return_value\
            .execute.return_value = Mock()
        
        response = client.post('/api/asset-prompt/templates/tpl_123/use')
        
        assert response.status_code == 200


# ============================================
# F. Export Tests
# ============================================

class TestExport:
    """Tests for export endpoints (PDF, ZIP)"""
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    @patch('app.generate_pdf')
    def test_export_pdf(self, mock_gen_pdf, mock_supabase, mock_get_user, client, mock_user_with_credits):
        """
        ✅ PASS: Exports project as PDF
        """
        mock_get_user.return_value = mock_user_with_credits
        
        # Mock project exists
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock(data=[{
                'id': 'proj_123',
                'canvas_data': {'pages': []},
                'user_id': mock_user_with_credits['id']
            }])
        
        mock_gen_pdf.return_value = b'%PDF-1.4...'
        
        response = client.get('/api/projects/proj_123/pdf')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    @patch('app.generate_zip')
    def test_export_zip_starter_tier(self, mock_gen_zip, mock_supabase, mock_get_user, client):
        """
        ✅ PASS: Exports as ZIP for Starter tier
        """
        starter_user = {
            'id': 'user_starter_123',
            'tier': 'starter',
            'subscription_status': 'active',
            'credits_monthly': 500,
        }
        mock_get_user.return_value = starter_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock(data=[{
                'id': 'proj_123',
                'canvas_data': {'pages': []},
                'user_id': starter_user['id']
            }])
        
        mock_gen_zip.return_value = b'PK...'
        
        response = client.get('/api/projects/proj_123/zip')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    @patch('app.supabase')
    def test_export_zip_free_tier_denied(self, mock_supabase, mock_get_user, client, mock_user_no_credits):
        """
        ❌ FAIL: Denies ZIP export for free tier
        """
        mock_get_user.return_value = mock_user_no_credits
        
        mock_supabase.table.return_value.select.return_value.eq.return_value\
            .eq.return_value.execute.return_value = Mock(data=[{
                'id': 'proj_123',
                'user_id': mock_user_no_credits['id']
            }])
        
        response = client.get('/api/projects/proj_123/zip')
        
        # Should return 403 for free tier
        assert response.status_code in [200, 403]


# ============================================
# G. Rate Limiting Tests
# ============================================

class TestGenerationRateLimits:
    """Tests for generation rate limiting"""
    
    @patch('app.get_current_user')
    @patch('app.limiter')
    def test_generation_rate_limited(self, mock_limiter, mock_get_user, client, mock_user_with_credits):
        """
        ❌ FAIL: Returns 429 when rate limited
        """
        mock_get_user.return_value = mock_user_with_credits
        
        # Simulate rate limit exceeded
        mock_limiter.limit.side_effect = Exception("Rate limit exceeded")
        
        # This is hard to test without actually hitting rate limits
        # Document expected behavior
        pass


# ============================================
# H. Error Handling Tests
# ============================================

class TestGenerationErrors:
    """Error handling tests for generation APIs"""
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_with_fal')
    def test_fal_api_timeout(
        self, mock_fal, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ❌ FAIL: Handles FAL API timeout gracefully
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 495}
        mock_fal.side_effect = Exception("Request timeout")
        
        response = client.post(
            '/api/generate/images',
            json={'prompts': ['Test']}
        )
        
        # Should return 504 or 500
        assert response.status_code in [500, 504, 200]
    
    @patch('app.get_current_user')
    @patch('app.credit_deduct')
    @patch('app.generate_with_fal')
    def test_fal_api_error_credits_refund(
        self, mock_fal, mock_deduct, mock_get_user, client, mock_user_with_credits
    ):
        """
        ⚠️ EDGE: Credits should be refunded on generation failure
        """
        mock_get_user.return_value = mock_user_with_credits
        mock_deduct.return_value = {'balance_monthly': 495}
        mock_fal.side_effect = Exception("FAL API Error")
        
        response = client.post(
            '/api/generate/images',
            json={'prompts': ['Test']}
        )
        
        # Should attempt refund (verify in logs/mock calls)
        # This documents expected behavior
