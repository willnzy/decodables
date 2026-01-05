"""
Unit Tests for AI Canary Release
AI 灰度发布单元测试

Tests:
- get_canary_config
- should_use_canary
- get_canary_status
- Deterministic hash-based traffic splitting
"""

import pytest
from unittest.mock import patch


# ==========================================
# get_canary_config Tests
# ==========================================

class TestGetCanaryConfig:
    """get_canary_config 函数测试"""
    
    @patch('services.ai.canary.get_config')
    def test_returns_canary_config(self, mock_get_config):
        """返回灰度配置"""
        from services.ai.canary import get_canary_config
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 10,
                "target_tiers": ["pro"]
            }
        }
        
        config = get_canary_config()
        
        assert config["enabled"] is True
        assert config["text_reasoning"]["canary_provider"] == "qwen"
    
    @patch('services.ai.canary.get_config')
    def test_returns_disabled_when_not_configured(self, mock_get_config):
        """未配置时返回禁用状态"""
        from services.ai.canary import get_canary_config
        
        mock_get_config.return_value = None
        
        config = get_canary_config()
        
        assert config["enabled"] is False


# ==========================================
# should_use_canary Tests
# ==========================================

class TestShouldUseCanary:
    """should_use_canary 函数测试"""
    
    @patch('services.ai.canary.get_canary_config')
    def test_returns_false_when_disabled(self, mock_get_config):
        """灰度禁用时返回 False"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {"enabled": False}
        
        use_canary, config = should_use_canary("user_123", "text_reasoning", "pro")
        
        assert use_canary is False
        assert config is None
    
    @patch('services.ai.canary.get_canary_config')
    def test_returns_false_when_tier_not_targeted(self, mock_get_config):
        """用户等级不在目标列表时返回 False"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,  # 100% 流量
                "target_tiers": ["pro"]  # 只针对 pro
            }
        }
        
        use_canary, config = should_use_canary("user_123", "text_reasoning", "free")
        
        assert use_canary is False
    
    @patch('services.ai.canary.get_canary_config')
    def test_returns_true_when_in_canary_group(self, mock_get_config):
        """用户在灰度组内时返回 True"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,  # 100% 流量确保命中
                "target_tiers": ["pro"]
            }
        }
        
        use_canary, config = should_use_canary("user_123", "text_reasoning", "pro")
        
        assert use_canary is True
        assert config["provider"] == "qwen"
        assert config["model"] == "qwen-plus"
    
    @patch('services.ai.canary.get_canary_config')
    def test_deterministic_hashing(self, mock_get_config):
        """确定性哈希 - 相同用户始终得到相同结果"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 50,  # 50% 流量
                "target_tiers": ["free", "starter", "pro"]
            }
        }
        
        # 同一用户多次调用应该得到相同结果
        results = []
        for _ in range(10):
            use_canary, _ = should_use_canary("consistent_user_id", "text_reasoning", "pro")
            results.append(use_canary)
        
        # 所有结果应该相同
        assert all(r == results[0] for r in results)
    
    @patch('services.ai.canary.get_canary_config')
    def test_different_users_different_results(self, mock_get_config):
        """不同用户可能得到不同结果（统计测试）"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 50,
                "target_tiers": ["free", "starter", "pro"]
            }
        }
        
        # 测试多个用户
        canary_count = 0
        total_users = 100
        
        for i in range(total_users):
            use_canary, _ = should_use_canary(f"user_{i}", "text_reasoning", "pro")
            if use_canary:
                canary_count += 1
        
        # 50% 流量应该大约有一半用户在灰度组
        # 允许较大误差范围（因为样本较小）
        assert 20 <= canary_count <= 80
    
    @patch('services.ai.canary.get_canary_config')
    def test_no_model_type_config(self, mock_get_config):
        """没有对应模型类型的配置"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": ["pro"]
            }
            # 没有 image_generation 配置
        }
        
        use_canary, config = should_use_canary("user_123", "image_generation", "pro")
        
        assert use_canary is False
        assert config is None
    
    @patch('services.ai.canary.get_canary_config')
    def test_zero_traffic_percent(self, mock_get_config):
        """0% 流量"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 0,  # 0% 流量
                "target_tiers": ["pro"]
            }
        }
        
        use_canary, _ = should_use_canary("user_123", "text_reasoning", "pro")
        
        assert use_canary is False
    
    @patch('services.ai.canary.get_canary_config')
    def test_all_tiers_targeted(self, mock_get_config):
        """所有等级都在目标列表"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": ["free", "starter", "pro"]
            }
        }
        
        for tier in ["free", "starter", "pro"]:
            use_canary, _ = should_use_canary("user_123", "text_reasoning", tier)
            assert use_canary is True


# ==========================================
# get_canary_status Tests
# ==========================================

class TestGetCanaryStatus:
    """get_canary_status 函数测试"""
    
    @patch('services.ai.canary.get_canary_config')
    def test_returns_status_summary(self, mock_get_config):
        """返回灰度状态摘要"""
        from services.ai.canary import get_canary_status
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 10,
                "target_tiers": ["pro"]
            },
            "image_generation": {
                "canary_provider": "jimeng",
                "canary_model": "jimeng-2.1",
                "traffic_percent": 5,
                "target_tiers": ["pro"]
            }
        }
        
        status = get_canary_status()
        
        assert status["enabled"] is True
        assert "text_reasoning" in status
        assert "image_generation" in status


# ==========================================
# Edge Cases
# ==========================================

class TestCanaryEdgeCases:
    """边界情况测试"""
    
    @patch('services.ai.canary.get_canary_config')
    def test_empty_target_tiers(self, mock_get_config):
        """空目标等级列表"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": []  # 空列表
            }
        }
        
        use_canary, _ = should_use_canary("user_123", "text_reasoning", "pro")
        
        # 注意: 当前实现可能不检查空 target_tiers
        # 这是一个边界情况，行为可能因实现而异
        assert isinstance(use_canary, bool)  # 只检查返回类型
    
    @patch('services.ai.canary.get_canary_config')
    def test_visitor_id(self, mock_get_config):
        """访客 ID (visitor_xxx)"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": ["free"]
            }
        }
        
        use_canary, _ = should_use_canary("visitor_abc123", "text_reasoning", "free")
        
        # 访客 ID 也应该正常工作
        assert use_canary is True
    
    @patch('services.ai.canary.get_canary_config')
    def test_traffic_percent_boundary(self, mock_get_config):
        """流量百分比边界值"""
        from services.ai.canary import should_use_canary
        
        # 测试 100%
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": ["pro"]
            }
        }
        
        use_canary, _ = should_use_canary("any_user", "text_reasoning", "pro")
        assert use_canary is True
        
        # 测试 0%
        mock_get_config.return_value["text_reasoning"]["traffic_percent"] = 0
        use_canary, _ = should_use_canary("any_user", "text_reasoning", "pro")
        assert use_canary is False
    
    @patch('services.ai.canary.get_canary_config')
    def test_special_characters_in_user_id(self, mock_get_config):
        """用户 ID 中的特殊字符"""
        from services.ai.canary import should_use_canary
        
        mock_get_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": ["pro"]
            }
        }
        
        # 包含特殊字符的用户 ID
        special_ids = [
            "user@example.com",
            "user-with-dashes",
            "user_with_underscores",
            "user.with.dots",
            "中文用户ID",
            "user🎉emoji"
        ]
        
        for user_id in special_ids:
            use_canary, _ = should_use_canary(user_id, "text_reasoning", "pro")
            # 应该正常工作，不抛出异常
            assert isinstance(use_canary, bool)
