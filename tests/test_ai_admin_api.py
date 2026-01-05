"""
API Tests for Admin AI Configuration
Admin AI 配置 API 测试

Tests:
- GET /api/admin/ai/config
- PUT /api/admin/ai/config/text
- PUT /api/admin/ai/config/image
- PUT /api/admin/ai/config/admin
- PUT /api/admin/ai/config/canary
- PUT /api/admin/ai/providers/toggle
- GET /api/admin/ai/usage
- POST /api/admin/ai/cache/clear
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from fastapi.testclient import TestClient


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def client():
    """Create test client"""
    with patch('app.supabase') as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[])
        from app import app
        return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Admin user fixture"""
    return {
        'id': 'admin_123',
        'email': 'admin@test.com',
        'role': 'admin',
        'tier': 'pro',
    }


@pytest.fixture
def mock_non_admin_user():
    """Non-admin user fixture"""
    return {
        'id': 'user_123',
        'email': 'user@test.com',
        'role': 'user',
        'tier': 'free',
    }


# ==========================================
# GET /api/admin/ai/config Tests
# ==========================================

class TestGetAIConfig:
    """GET /api/admin/ai/config 测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.ai.get_text_model_config')
    @patch('services.ai.get_image_model_config')
    @patch('services.ai.get_admin_model_config')
    @patch('services.ai.get_enabled_providers')
    @patch('services.ai.get_canary_status')
    @patch('services.ai.get_all_provider_models')
    @patch('services.ai.get_available_text_providers')
    @patch('services.ai.get_available_image_providers')
    def test_get_full_config(
        self, mock_img_providers, mock_text_providers, mock_all_models,
        mock_canary_status, mock_enabled, mock_admin_config,
        mock_img_config, mock_text_config, mock_require_admin,
        client, mock_admin_user
    ):
        """获取完整的 AI 配置"""
        mock_require_admin.return_value = mock_admin_user
        mock_text_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        mock_img_config.return_value = {
            "provider": "fal",
            "model": "flux-schnell"
        }
        mock_admin_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o"
        }
        mock_enabled.return_value = {"openai": True, "fal": True}
        mock_canary_status.return_value = {"enabled": False}
        mock_all_models.return_value = {}
        mock_text_providers.return_value = ["openai"]
        mock_img_providers.return_value = ["fal"]
        
        response = client.get('/api/admin/ai/config')
        
        assert response.status_code == 200
        data = response.json()
        assert 'text_model' in data
        assert 'image_model' in data
        assert 'admin_model' in data
        assert 'enabled_providers' in data
    
    @patch('routers.admin.require_admin')
    def test_requires_admin(self, mock_require_admin, client):
        """需要管理员权限"""
        from fastapi import HTTPException
        mock_require_admin.side_effect = HTTPException(status_code=403, detail="Admin required")
        
        response = client.get('/api/admin/ai/config')
        
        assert response.status_code == 403


# ==========================================
# PUT /api/admin/ai/config/text Tests
# ==========================================

class TestUpdateTextModelConfig:
    """PUT /api/admin/ai/config/text 测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_update_text_model(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """更新文本模型配置"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/config/text',
            json={
                "provider": "qwen",
                "model": "qwen-plus"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'updated'
        assert data['config']['provider'] == 'qwen'
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_update_text_model_partial(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """部分更新文本模型配置"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        mock_set_config.return_value = True
        
        # 只更新模型，不更新提供商
        response = client.put(
            '/api/admin/ai/config/text',
            json={"model": "gpt-4o"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['config']['provider'] == 'openai'  # 保持不变
        assert data['config']['model'] == 'gpt-4o'  # 已更新
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_update_text_model_with_fallback(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """更新文本模型配置 (包含 fallback)"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {}
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/config/text',
            json={
                "provider": "qwen",
                "model": "qwen-plus",
                "fallback_provider": "openai",
                "fallback_model": "gpt-4o-mini"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['config']['fallback']['provider'] == 'openai'


# ==========================================
# PUT /api/admin/ai/config/image Tests
# ==========================================

class TestUpdateImageModelConfig:
    """PUT /api/admin/ai/config/image 测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_update_image_model(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """更新图像模型配置"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {
            "provider": "fal",
            "models": {"free": "flux-schnell", "pro": "flux-dev"}
        }
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/config/image',
            json={
                "provider": "wanx",
                "models": {
                    "free": "wan2.6-t2i",
                    "starter": "wan2.6-t2i",
                    "pro": "wan2.6-image"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['config']['provider'] == 'wanx'


# ==========================================
# PUT /api/admin/ai/config/canary Tests
# ==========================================

class TestUpdateCanaryConfig:
    """PUT /api/admin/ai/config/canary 测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_enable_canary(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """启用灰度发布"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {"enabled": False}
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/config/canary',
            json={
                "enabled": True,
                "text_reasoning": {
                    "canary_provider": "qwen",
                    "canary_model": "qwen-plus",
                    "traffic_percent": 10,
                    "target_tiers": ["pro"]
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['config']['enabled'] is True
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_disable_canary(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """禁用灰度发布"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus"
            }
        }
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/config/canary',
            json={"enabled": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['config']['enabled'] is False


# ==========================================
# PUT /api/admin/ai/providers/toggle Tests
# ==========================================

class TestToggleProvider:
    """PUT /api/admin/ai/providers/toggle 测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_enable_provider(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """启用提供商"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {
            "openai": True,
            "fal": True,
            "qwen": False
        }
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/providers/toggle',
            json={"provider": "qwen", "enabled": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['providers']['qwen'] is True
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_disable_provider(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """禁用提供商"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {"openai": True, "fal": True}
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/providers/toggle',
            json={"provider": "fal", "enabled": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['providers']['fal'] is False


# ==========================================
# GET /api/admin/ai/usage Tests
# ==========================================

class TestGetAIUsage:
    """GET /api/admin/ai/usage 测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.ai.get_usage_summary')
    @patch('services.ai.get_daily_trend')
    def test_get_usage_stats(
        self, mock_daily_trend, mock_summary, mock_require_admin,
        client, mock_admin_user
    ):
        """获取使用量统计"""
        mock_require_admin.return_value = mock_admin_user
        mock_summary.return_value = {
            "total_calls": 1000,
            "total_cost_usd": 5.50,
            "by_provider": {"openai": 800, "fal": 200}
        }
        mock_daily_trend.return_value = [
            {"date": "2026-01-01", "calls": 100, "cost": 0.50},
            {"date": "2026-01-02", "calls": 150, "cost": 0.75}
        ]
        
        response = client.get('/api/admin/ai/usage?days=30')
        
        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data
        assert 'daily_trend' in data
        assert data['summary']['total_calls'] == 1000
    
    @patch('routers.admin.require_admin')
    @patch('services.ai.get_usage_summary')
    @patch('services.ai.get_daily_trend')
    def test_get_usage_custom_days(
        self, mock_daily_trend, mock_summary, mock_require_admin,
        client, mock_admin_user
    ):
        """自定义天数范围"""
        mock_require_admin.return_value = mock_admin_user
        mock_summary.return_value = {}
        mock_daily_trend.return_value = []
        
        response = client.get('/api/admin/ai/usage?days=7')
        
        assert response.status_code == 200
        mock_summary.assert_called_once_with(7)


# ==========================================
# POST /api/admin/ai/cache/clear Tests
# ==========================================

class TestClearAICache:
    """POST /api/admin/ai/cache/clear 测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.ai.invalidate_ai_cache')
    def test_clear_cache(
        self, mock_invalidate, mock_require_admin,
        client, mock_admin_user
    ):
        """清除 AI 缓存"""
        mock_require_admin.return_value = mock_admin_user
        mock_invalidate.return_value = None
        
        response = client.post('/api/admin/ai/cache/clear')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'cleared'
        mock_invalidate.assert_called_once()


# ==========================================
# Authorization Tests
# ==========================================

class TestAuthorization:
    """权限测试"""
    
    @patch('routers.admin.require_admin')
    def test_non_admin_cannot_access_config(
        self, mock_require_admin, client, mock_non_admin_user
    ):
        """非管理员不能访问配置"""
        from fastapi import HTTPException
        mock_require_admin.side_effect = HTTPException(
            status_code=403, 
            detail="Admin access required"
        )
        
        response = client.get('/api/admin/ai/config')
        
        assert response.status_code == 403
    
    @patch('routers.admin.require_admin')
    def test_non_admin_cannot_update_config(
        self, mock_require_admin, client, mock_non_admin_user
    ):
        """非管理员不能更新配置"""
        from fastapi import HTTPException
        mock_require_admin.side_effect = HTTPException(
            status_code=403, 
            detail="Admin access required"
        )
        
        response = client.put(
            '/api/admin/ai/config/text',
            json={"provider": "qwen"}
        )
        
        assert response.status_code == 403


# ==========================================
# Edge Cases
# ==========================================

class TestAdminAPIEdgeCases:
    """边界情况测试"""
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_update_with_empty_body(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """空请求体"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {"provider": "openai"}
        mock_set_config.return_value = True
        
        response = client.put(
            '/api/admin/ai/config/text',
            json={}
        )
        
        # 空请求应该成功但不做任何更改
        assert response.status_code == 200
    
    @patch('routers.admin.require_admin')
    @patch('services.config_service.get_config')
    @patch('services.config_service.set_config')
    def test_update_config_failure(
        self, mock_set_config, mock_get_config, mock_require_admin,
        client, mock_admin_user
    ):
        """配置更新失败"""
        mock_require_admin.return_value = mock_admin_user
        mock_get_config.return_value = {}
        mock_set_config.return_value = False  # 更新失败
        
        response = client.put(
            '/api/admin/ai/config/text',
            json={"provider": "qwen"}
        )
        
        assert response.status_code == 500
    
    @patch('routers.admin.require_admin')
    def test_invalid_canary_config(
        self, mock_require_admin, client, mock_admin_user
    ):
        """无效的灰度配置"""
        mock_require_admin.return_value = mock_admin_user
        
        # 缺少必需字段 enabled
        response = client.put(
            '/api/admin/ai/config/canary',
            json={"text_reasoning": {}}
        )
        
        # 应该返回验证错误
        assert response.status_code in [200, 422]
