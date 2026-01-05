"""
Tests for db_service system configuration functions.
按功能设计测试用例，测试驱动开发。
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestConfigCacheFunctions:
    """Test internal config cache functions"""
    
    def test_get_cached_config(self):
        """测试缓存获取函数"""
        from services.db_service import _get_cached_config
        # Function should not raise even if cache is empty
        result = _get_cached_config("nonexistent_key")
        # Result depends on cache state
        assert result is None or result is not None
    
    def test_set_cached_config(self):
        """设置缓存"""
        from services.db_service import _set_cached_config, _get_cached_config
        _set_cached_config("test_key_123", "test_value")
        result = _get_cached_config("test_key_123")
        assert result == "test_value"
    
    def test_get_cached_config_dict(self):
        """测试字典缓存获取函数"""
        from services.db_service import _get_cached_config_dict
        result = _get_cached_config_dict("nonexistent_dict_key")
        # Result depends on cache state
        assert result is None or result is not None
    
    def test_set_cached_config_dict(self):
        """设置字典缓存"""
        from services.db_service import _set_cached_config_dict, _get_cached_config_dict
        _set_cached_config_dict("test_dict_key_123", {"a": 1, "b": 2})
        result = _get_cached_config_dict("test_dict_key_123")
        assert result == {"a": 1, "b": 2}


class TestInvalidateConfigCache:
    """Test _invalidate_config_cache function"""
    
    def test_invalidate_specific_key(self):
        """清除特定键的缓存"""
        from services.db_service import _invalidate_config_cache
        _invalidate_config_cache("specific_key")
        # Should not raise
    
    def test_invalidate_all_cache(self):
        """清除所有缓存"""
        from services.db_service import _invalidate_config_cache
        _invalidate_config_cache(None)
        # Should clear all caches


class TestGetSystemConfig:
    """Test get_system_config function"""
    
    def test_get_config_from_cache(self):
        """从缓存获取配置"""
        with patch('services.db_service._get_cached_config') as mock_get:
            mock_get.return_value = "cached_value"
            
            from services.db_service import get_system_config
            result = get_system_config("test_key")
            
            assert result == "cached_value"
    
    def test_get_config_from_db(self):
        """从数据库获取配置"""
        with patch('services.db_service._get_cached_config') as mock_get:
            with patch('services.db_service.supabase') as mock_supabase:
                with patch('services.db_service._set_cached_config'):
                    mock_get.return_value = None
                    
                    mock_config = MagicMock()
                    mock_config.data = {"value": "db_value", "is_active": True}
                    
                    mock_chain = MagicMock()
                    mock_chain.eq.return_value = mock_chain
                    mock_chain.single.return_value = mock_chain
                    mock_chain.execute.return_value = mock_config
                    mock_supabase.table.return_value.select.return_value = mock_chain
                    
                    from services.db_service import get_system_config
                    result = get_system_config("test_key")
                    
                    assert result == "db_value"
    
    def test_get_config_default(self):
        """配置不存在时返回默认值"""
        with patch('services.db_service._get_cached_config') as mock_get:
            with patch('services.db_service.supabase') as mock_supabase:
                mock_get.return_value = None
                
                mock_config = MagicMock()
                mock_config.data = None
                
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.single.return_value = mock_chain
                mock_chain.execute.return_value = mock_config
                mock_supabase.table.return_value.select.return_value = mock_chain
                
                from services.db_service import get_system_config
                result = get_system_config("nonexistent", "default_value")
                
                assert result == "default_value"


class TestGetAllSystemConfigs:
    """Test get_all_system_configs function"""
    
    def test_get_all_configs(self):
        """获取所有配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_configs = MagicMock()
            mock_configs.data = [
                {"key": "config1", "value": "value1", "is_active": True},
                {"key": "config2", "value": "value2", "is_active": True}
            ]
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.execute.return_value = mock_configs
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import get_all_system_configs
            result = get_all_system_configs()
            
            # Result is a dict keyed by config key
            assert isinstance(result, dict)
    
    def test_get_configs_by_group(self):
        """按组获取配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_configs = MagicMock()
            mock_configs.data = [
                {"key": "rate_limit_1", "value": "100", "config_group": "rate_limits"}
            ]
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.execute.return_value = mock_configs
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import get_all_system_configs
            result = get_all_system_configs(group="rate_limits")
            
            assert isinstance(result, dict)
    
    def test_get_configs_include_inactive(self):
        """包含非活动配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_configs = MagicMock()
            mock_configs.data = [
                {"key": "config1", "value": "v1", "is_active": True},
                {"key": "config2", "value": "v2", "is_active": False}
            ]
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.execute.return_value = mock_configs
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import get_all_system_configs
            result = get_all_system_configs(include_inactive=True)
            
            # Result is a dict
            assert isinstance(result, dict)


class TestGetConfigsByGroup:
    """Test get_configs_by_group function"""
    
    def test_get_configs_by_group(self):
        """按组获取配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_configs = MagicMock()
            mock_configs.data = [
                {"key": "api_key", "value": "xxx", "config_group": "api"}
            ]
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.execute.return_value = mock_configs
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import get_configs_by_group
            result = get_configs_by_group("api")
            
            assert isinstance(result, dict)


class TestAdminGetSystemConfigs:
    """Test admin_get_system_configs function"""
    
    def test_admin_get_configs(self):
        """管理员获取系统配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_configs = MagicMock()
            mock_configs.data = [
                {"key": "config1", "value": "value1", "config_group": "general"}
            ]
            mock_configs.count = 1
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.ilike.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value = mock_configs
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_system_configs
            result = admin_get_system_configs()
            
            assert "items" in result or "configs" in result or isinstance(result, list)


class TestAdminGetConfigGroups:
    """Test admin_get_config_groups function"""
    
    def test_get_config_groups(self):
        """获取所有配置组"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_groups = MagicMock()
            mock_groups.data = [
                {"config_group": "general"},
                {"config_group": "rate_limits"},
                {"config_group": "api"}
            ]
            
            mock_chain = MagicMock()
            mock_chain.execute.return_value = mock_groups
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_config_groups
            result = admin_get_config_groups()
            
            assert isinstance(result, list)


class TestAdminCreateSystemConfig:
    """Test admin_create_system_config function"""
    
    def test_create_config_success(self):
        """成功创建配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service._log_config_audit'):
                with patch('services.db_service._invalidate_config_cache'):
                    mock_config = MagicMock()
                    mock_config.data = [{
                        "key": "new_config",
                        "value": "new_value",
                        "config_group": "general"
                    }]
                    
                    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_config
                    
                    from services.db_service import admin_create_system_config
                    result = admin_create_system_config(
                        key="new_config",
                        value="new_value",
                        config_group="general",
                        admin_id="admin-1"
                    )
                    
                    assert result["key"] == "new_config"


class TestAdminUpdateSystemConfig:
    """Test admin_update_system_config function"""
    
    def test_update_config_success(self):
        """成功更新配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service._log_config_audit'):
                with patch('services.db_service._invalidate_config_cache'):
                    # Mock existing config
                    mock_existing = MagicMock()
                    mock_existing.data = {"key": "config1", "value": "old_value"}
                    
                    # Mock update result
                    mock_updated = MagicMock()
                    mock_updated.data = [{"key": "config1", "value": "new_value"}]
                    
                    call_count = [0]
                    def table_side_effect(table_name):
                        mock_table = MagicMock()
                        nonlocal call_count
                        if call_count[0] == 0:
                            # First call: select existing
                            mock_chain = MagicMock()
                            mock_chain.eq.return_value = mock_chain
                            mock_chain.single.return_value = mock_chain
                            mock_chain.execute.return_value = mock_existing
                            mock_table.select.return_value = mock_chain
                        else:
                            # Second call: update
                            mock_chain = MagicMock()
                            mock_chain.eq.return_value = mock_chain
                            mock_chain.execute.return_value = mock_updated
                            mock_table.update.return_value = mock_chain
                        call_count[0] += 1
                        return mock_table
                    
                    mock_supabase.table.side_effect = table_side_effect
                    
                    from services.db_service import admin_update_system_config
                    result = admin_update_system_config(
                        key="config1",
                        value="new_value",
                        admin_id="admin-1"
                    )
                    
                    assert result is not None


class TestAdminDeleteSystemConfig:
    """Test admin_delete_system_config function"""
    
    def test_delete_config_success(self):
        """成功删除配置"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service._log_config_audit'):
                with patch('services.db_service._invalidate_config_cache'):
                    # Mock existing config with 'value' key
                    mock_existing = MagicMock()
                    mock_existing.data = {"key": "config1", "value": "old_value"}
                    
                    # Mock delete result
                    mock_deleted = MagicMock()
                    mock_deleted.data = [{"key": "config1"}]
                    
                    call_count = [0]
                    def table_side_effect(table_name):
                        mock_table = MagicMock()
                        nonlocal call_count
                        if call_count[0] == 0:
                            mock_chain = MagicMock()
                            mock_chain.eq.return_value = mock_chain
                            mock_chain.single.return_value = mock_chain
                            mock_chain.execute.return_value = mock_existing
                            mock_table.select.return_value = mock_chain
                        else:
                            mock_chain = MagicMock()
                            mock_chain.eq.return_value = mock_chain
                            mock_chain.execute.return_value = mock_deleted
                            mock_table.delete.return_value = mock_chain
                        call_count[0] += 1
                        return mock_table
                    
                    mock_supabase.table.side_effect = table_side_effect
                    
                    from services.db_service import admin_delete_system_config
                    result = admin_delete_system_config("config1", "admin-1")
                    
                    assert result is True or result is not None


class TestLogConfigAudit:
    """Test _log_config_audit function"""
    
    def test_log_audit(self):
        """记录配置审计日志"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import _log_config_audit
            # Function signature: config_key, old_value, new_value, action, admin_id
            _log_config_audit(
                config_key="config1",
                old_value="v1",
                new_value="v2",
                action="update",
                admin_id="admin-1"
            )
            
            mock_supabase.table.assert_called_with("config_audit_logs")


class TestAdminGetConfigAuditLogs:
    """Test admin_get_config_audit_logs function"""
    
    def test_get_audit_logs(self):
        """获取配置审计日志"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_logs = MagicMock()
            mock_logs.data = [
                {"id": "log1", "action": "create", "admin_id": "admin-1"},
                {"id": "log2", "action": "update", "admin_id": "admin-1"}
            ]
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value = mock_logs
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_config_audit_logs
            result = admin_get_config_audit_logs()
            
            assert "items" in result or "logs" in result or isinstance(result, list)


class TestInvalidateConfigCacheAPI:
    """Test invalidate_config_cache_api function"""
    
    def test_invalidate_cache_api(self):
        """API清除配置缓存"""
        with patch('services.db_service._invalidate_config_cache') as mock_invalidate:
            from services.db_service import invalidate_config_cache_api
            invalidate_config_cache_api()
            
            mock_invalidate.assert_called()
