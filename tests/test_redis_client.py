"""
Redis Client Tests
Redis 客户端测试

基于 BUSINESS_LOGIC_SPEC.md Section 11 的业务规则测试

核心业务规则:
1. 连接管理:
   - 单例模式 + 连接池
   - 健康检查
   - 优雅关闭

2. 降级策略:
   - REDIS_URL 未配置时返回 None
   - 连接失败时返回 None

@module tests/test_redis_client
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock


# ==========================================
# get_redis_client Tests
# ==========================================

class TestGetRedisClient:
    """
    获取 Redis 客户端测试
    """
    
    @patch.dict('os.environ', {'REDIS_URL': ''}, clear=False)
    def test_returns_none_when_url_not_configured(self):
        """【业务规则 11.1】REDIS_URL 未配置时返回 None"""
        # 需要重新导入以应用环境变量
        import importlib
        import services.cache.redis_client as rc
        
        # 重置单例
        rc._redis_client = None
        rc._redis_pool = None
        rc.REDIS_URL = None
        
        result = rc.get_redis_client()
        
        assert result is None
    
    @patch('services.cache.redis_client.redis')
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'}, clear=False)
    def test_creates_client_with_connection_pool(self, mock_redis):
        """【业务规则 11.1】使用连接池创建客户端"""
        import services.cache.redis_client as rc
        
        # 重置单例
        rc._redis_client = None
        rc._redis_pool = None
        rc.REDIS_URL = 'redis://localhost:6379'
        
        mock_pool = MagicMock()
        mock_client = MagicMock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client
        mock_client.ping.return_value = True
        
        result = rc.get_redis_client()
        
        assert result is not None
        mock_redis.ConnectionPool.from_url.assert_called_once()
        mock_client.ping.assert_called_once()
    
    @patch('services.cache.redis_client.redis')
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'}, clear=False)
    def test_returns_existing_client(self, mock_redis):
        """【业务规则 11.1】返回已存在的客户端 (单例模式)"""
        import services.cache.redis_client as rc
        
        mock_client = MagicMock()
        rc._redis_client = mock_client
        rc.REDIS_URL = 'redis://localhost:6379'
        
        result = rc.get_redis_client()
        
        assert result == mock_client
        # 不应该创建新的连接池
        mock_redis.ConnectionPool.from_url.assert_not_called()
    
    @patch('services.cache.redis_client.redis')
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'}, clear=False)
    def test_handles_connection_error(self, mock_redis):
        """【业务规则 11.1】连接错误时返回 None"""
        import services.cache.redis_client as rc
        import redis as real_redis
        
        # 重置单例
        rc._redis_client = None
        rc._redis_pool = None
        rc.REDIS_URL = 'redis://localhost:6379'
        
        # 使用真实的 ConnectionError
        mock_redis.ConnectionError = real_redis.ConnectionError
        mock_redis.ConnectionPool.from_url.side_effect = real_redis.ConnectionError("Connection refused")
        
        result = rc.get_redis_client()
        
        assert result is None


# ==========================================
# is_redis_available Tests
# ==========================================

class TestIsRedisAvailable:
    """
    Redis 可用性检查测试
    """
    
    @patch('services.cache.redis_client.get_redis_client')
    def test_returns_false_when_client_none(self, mock_get_client):
        """【业务规则 11.1】客户端为 None 时返回 False"""
        from services.cache.redis_client import is_redis_available
        
        mock_get_client.return_value = None
        
        result = is_redis_available()
        
        assert result is False
    
    @patch('services.cache.redis_client.get_redis_client')
    def test_returns_true_when_ping_succeeds(self, mock_get_client):
        """【业务规则 11.1】ping 成功时返回 True"""
        from services.cache.redis_client import is_redis_available
        
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_get_client.return_value = mock_client
        
        result = is_redis_available()
        
        assert result is True
        mock_client.ping.assert_called_once()
    
    @patch('services.cache.redis_client.get_redis_client')
    def test_returns_false_when_ping_fails(self, mock_get_client):
        """【业务规则 11.1】ping 失败时返回 False"""
        from services.cache.redis_client import is_redis_available
        
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection lost")
        mock_get_client.return_value = mock_client
        
        result = is_redis_available()
        
        assert result is False


# ==========================================
# close_redis Tests
# ==========================================

class TestCloseRedis:
    """
    关闭 Redis 连接测试
    """
    
    def test_closes_client_and_pool(self):
        """【业务规则 11.1】关闭客户端和连接池"""
        import services.cache.redis_client as rc
        
        mock_client = MagicMock()
        mock_pool = MagicMock()
        
        rc._redis_client = mock_client
        rc._redis_pool = mock_pool
        
        rc.close_redis()
        
        mock_client.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert rc._redis_client is None
        assert rc._redis_pool is None
    
    def test_handles_close_error_gracefully(self):
        """【业务规则 11.1】优雅处理关闭错误"""
        import services.cache.redis_client as rc
        
        mock_client = MagicMock()
        mock_client.close.side_effect = Exception("Error closing")
        
        rc._redis_client = mock_client
        rc._redis_pool = None
        
        # 不应该抛出异常
        rc.close_redis()
        
        assert rc._redis_client is None
    
    def test_handles_none_client_gracefully(self):
        """【业务规则 11.1】处理 None 客户端"""
        import services.cache.redis_client as rc
        
        rc._redis_client = None
        rc._redis_pool = None
        
        # 不应该抛出异常
        rc.close_redis()


# ==========================================
# get_redis_info Tests
# ==========================================

class TestGetRedisInfo:
    """
    获取 Redis 信息测试
    """
    
    @patch('services.cache.redis_client.get_redis_client')
    def test_returns_unavailable_when_no_client(self, mock_get_client):
        """【业务规则 11.1】无客户端时返回 unavailable"""
        from services.cache.redis_client import get_redis_info
        
        mock_get_client.return_value = None
        
        result = get_redis_info()
        
        assert result["status"] == "unavailable"
        assert "REDIS_URL" in result["reason"]
    
    @patch('services.cache.redis_client.get_redis_client')
    def test_returns_info_when_connected(self, mock_get_client):
        """【业务规则 11.1】连接时返回服务器信息"""
        from services.cache.redis_client import get_redis_info
        
        mock_client = MagicMock()
        mock_client.info.return_value = {
            "redis_version": "7.0.0",
            "connected_clients": 5,
            "used_memory_human": "1.5M",
            "uptime_in_seconds": 86400
        }
        mock_get_client.return_value = mock_client
        
        result = get_redis_info()
        
        assert result["status"] == "connected"
        assert result["redis_version"] == "7.0.0"
        assert result["connected_clients"] == 5
    
    @patch('services.cache.redis_client.get_redis_client')
    def test_returns_error_on_exception(self, mock_get_client):
        """【业务规则 11.1】异常时返回错误信息"""
        from services.cache.redis_client import get_redis_info
        
        mock_client = MagicMock()
        mock_client.info.side_effect = Exception("Connection failed")
        mock_get_client.return_value = mock_client
        
        result = get_redis_info()
        
        assert result["status"] == "error"
        assert "Connection failed" in result["reason"]


# ==========================================
# Configuration Constants Tests
# ==========================================

class TestConfigurationConstants:
    """
    配置常量测试
    """
    
    def test_pool_max_connections(self):
        """【业务规则】连接池最大连接数"""
        from services.cache.redis_client import POOL_MAX_CONNECTIONS
        
        assert POOL_MAX_CONNECTIONS == 10
    
    def test_socket_timeout(self):
        """【业务规则】Socket 超时时间"""
        from services.cache.redis_client import SOCKET_TIMEOUT
        
        assert SOCKET_TIMEOUT == 5
    
    def test_socket_connect_timeout(self):
        """【业务规则】连接超时时间"""
        from services.cache.redis_client import SOCKET_CONNECT_TIMEOUT
        
        assert SOCKET_CONNECT_TIMEOUT == 5
    
    def test_health_check_interval(self):
        """【业务规则】健康检查间隔"""
        from services.cache.redis_client import HEALTH_CHECK_INTERVAL
        
        assert HEALTH_CHECK_INTERVAL == 30
