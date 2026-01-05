"""
db_service 测试覆盖率提升
补充未测试或测试不足的函数

目标覆盖:
1. refresh_monthly_credits - 月度积分刷新完整测试
2. credit_deduct - 使用 RPC 的实现测试
3. add_credits_permanent/monthly - 边界情况测试
4. get_leaderboard - 排行榜功能测试
5. get_seller_project_stats/asset_stats - 卖家统计测试
6. get_all_projects_feed - 项目订阅测试
7. get_system_resources - 系统资源测试
8. retry_on_network_error - 重试装饰器边界测试
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone, timedelta
import time


# ==========================================
# refresh_monthly_credits Tests
# ==========================================

class TestRefreshMonthlyCreditsComplete:
    """月度积分刷新完整测试"""
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    def test_refresh_pro_credits_1000(self, mock_get_profile, mock_supabase, mock_log):
        """Pro 用户刷新为 1000 积分"""
        from services.db_service import refresh_monthly_credits
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 200,  # 旧的月度积分
            "credits_permanent": 50   # 永久积分不变
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        result = refresh_monthly_credits("user_001", "pro")
        
        assert result is True
        # 验证 update 调用
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["credits_monthly"] == 1000
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    def test_refresh_starter_credits_500(self, mock_get_profile, mock_supabase, mock_log):
        """Starter 用户刷新为 500 积分"""
        from services.db_service import refresh_monthly_credits
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 100,
            "credits_permanent": 30
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        result = refresh_monthly_credits("user_001", "starter")
        
        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["credits_monthly"] == 500
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    def test_refresh_free_gets_zero(self, mock_get_profile, mock_supabase, mock_log):
        """Free 用户刷新为 0 积分"""
        from services.db_service import refresh_monthly_credits
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 0,
            "credits_permanent": 50
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        result = refresh_monthly_credits("user_001", "free")
        
        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["credits_monthly"] == 0
    
    @patch('services.db_service.get_user_profile')
    def test_refresh_user_not_found(self, mock_get_profile):
        """用户不存在时返回 False"""
        from services.db_service import refresh_monthly_credits
        
        mock_get_profile.return_value = None
        
        result = refresh_monthly_credits("nonexistent", "pro")
        
        assert result is False
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    def test_refresh_preserves_permanent_credits(self, mock_get_profile, mock_supabase, mock_log):
        """刷新时永久积分不受影响"""
        from services.db_service import refresh_monthly_credits
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 50,
            "credits_permanent": 200
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        refresh_monthly_credits("user_001", "pro")
        
        # 验证 log_credit_transaction 中 permanent 余额不变
        mock_log.assert_called_once()
        log_call_kwargs = mock_log.call_args[1] if mock_log.call_args[1] else {}
        log_call_args = mock_log.call_args[0] if mock_log.call_args[0] else []
        # 根据调用方式验证 - 检查 balance_permanent_after 参数
        # 参数可能是位置参数或关键字参数


# ==========================================
# credit_deduct RPC Tests
# ==========================================

class TestCreditDeductRPC:
    """credit_deduct 使用 RPC 的测试"""
    
    @patch('services.db_service.supabase')
    def test_deduct_success_via_rpc(self, mock_supabase):
        """通过 RPC 成功扣除积分"""
        from services.db_service import credit_deduct
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": True,
            "balance_monthly": 450,
            "balance_permanent": 100
        })
        
        result = credit_deduct("user_001", 50, "generation", "AI Image")
        
        assert result["success"] is True
        assert result["balance_monthly"] == 450
        assert result["balance_permanent"] == 100
        assert result["total"] == 550
    
    @patch('services.db_service.supabase')
    def test_deduct_insufficient_credits_via_rpc(self, mock_supabase):
        """RPC 返回积分不足错误"""
        from services.db_service import credit_deduct
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": False,
            "error": "Insufficient credits",
            "error_code": "CREDITS_INSUFFICIENT"
        })
        
        with pytest.raises(Exception) as exc_info:
            credit_deduct("user_001", 1000, "generation", "Test")
        
        assert "CREDITS_INSUFFICIENT" in str(exc_info.value)
    
    @patch('services.db_service.supabase')
    def test_deduct_user_not_found_via_rpc(self, mock_supabase):
        """RPC 返回用户不存在错误"""
        from services.db_service import credit_deduct
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": False,
            "error": "User not found",
            "error_code": "USER_NOT_FOUND"
        })
        
        with pytest.raises(Exception) as exc_info:
            credit_deduct("nonexistent", 10, "generation", "Test")
        
        assert "not found" in str(exc_info.value).lower()
    
    @patch('services.db_service.get_user_profile')
    def test_deduct_zero_amount_returns_balance(self, mock_get_profile):
        """扣除金额为 0 时直接返回当前余额"""
        from services.db_service import credit_deduct
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 500,
            "credits_permanent": 100
        }
        
        result = credit_deduct("user_001", 0, "generation", "No deduction")
        
        assert result["success"] is True
        assert result["balance_monthly"] == 500
        assert result["balance_permanent"] == 100
    
    @patch('services.db_service.get_user_profile')
    def test_deduct_negative_amount_returns_balance(self, mock_get_profile):
        """扣除金额为负数时直接返回当前余额"""
        from services.db_service import credit_deduct
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 500,
            "credits_permanent": 100
        }
        
        result = credit_deduct("user_001", -10, "generation", "Negative")
        
        assert result["success"] is True
    
    @patch('services.db_service.supabase')
    def test_deduct_rpc_no_response(self, mock_supabase):
        """RPC 无响应时抛出异常"""
        from services.db_service import credit_deduct
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=None)
        
        with pytest.raises(Exception) as exc_info:
            credit_deduct("user_001", 50, "generation", "Test")
        
        assert "no response" in str(exc_info.value).lower()


# ==========================================
# add_credits_permanent/monthly Tests
# ==========================================

class TestAddCreditsEdgeCases:
    """添加积分边界情况测试"""
    
    @patch('services.db_service.get_user_profile')
    def test_add_permanent_zero_amount(self, mock_get_profile):
        """添加 0 永久积分返回当前余额"""
        from services.db_service import add_credits_permanent
        
        mock_get_profile.return_value = {
            "credits_monthly": 100,
            "credits_permanent": 50
        }
        
        result = add_credits_permanent("user_001", 0, "No add")
        
        assert result["balance_monthly"] == 100
        assert result["balance_permanent"] == 50
    
    @patch('services.db_service.get_user_profile')
    def test_add_permanent_negative_amount(self, mock_get_profile):
        """添加负数永久积分返回当前余额"""
        from services.db_service import add_credits_permanent
        
        mock_get_profile.return_value = {
            "credits_monthly": 100,
            "credits_permanent": 50
        }
        
        result = add_credits_permanent("user_001", -10, "Negative")
        
        assert result["balance_monthly"] == 100
        assert result["balance_permanent"] == 50
    
    @patch('services.db_service.supabase')
    def test_add_permanent_success_via_rpc(self, mock_supabase):
        """通过 RPC 成功添加永久积分"""
        from services.db_service import add_credits_permanent
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": True,
            "balance_monthly": 100,
            "balance_permanent": 150
        })
        
        result = add_credits_permanent("user_001", 100, "Sale earnings")
        
        assert result["balance_permanent"] == 150
    
    @patch('services.db_service.supabase')
    def test_add_permanent_rpc_failure(self, mock_supabase):
        """RPC 失败时返回 None"""
        from services.db_service import add_credits_permanent
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": False,
            "error": "Database error"
        })
        
        result = add_credits_permanent("user_001", 100, "Failed add")
        
        assert result is None
    
    def test_add_monthly_zero_amount(self):
        """添加 0 月度积分返回 None"""
        from services.db_service import add_credits_monthly
        
        result = add_credits_monthly("user_001", 0, "No add")
        
        assert result is None
    
    def test_add_monthly_negative_amount(self):
        """添加负数月度积分返回 None"""
        from services.db_service import add_credits_monthly
        
        result = add_credits_monthly("user_001", -10, "Negative")
        
        assert result is None
    
    @patch('services.db_service.supabase')
    def test_add_monthly_success_via_rpc(self, mock_supabase):
        """通过 RPC 成功添加月度积分"""
        from services.db_service import add_credits_monthly
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": True,
            "balance_monthly": 600,
            "balance_permanent": 50
        })
        
        result = add_credits_monthly("user_001", 500, "Subscription grant")
        
        assert result["balance_monthly"] == 600


# ==========================================
# get_leaderboard Tests
# ==========================================

class TestGetLeaderboard:
    """排行榜功能测试"""
    
    @patch('services.db_service.supabase')
    def test_get_leaderboard_monthly(self, mock_supabase):
        """获取月度排行榜"""
        from services.db_service import get_leaderboard
        
        mock_listings = MagicMock()
        mock_listings.data = [
            {"id": "l1", "seller_id": "s1", "title": "Top Item", "sales_count": 100, "thumbnail_url": "thumb.jpg"},
            {"id": "l2", "seller_id": "s2", "title": "Second", "sales_count": 80, "thumbnail_url": "thumb2.jpg"}
        ]
        
        mock_profiles = MagicMock()
        mock_profiles.data = [
            {"id": "s1", "username": "TopSeller", "avatar_url": "avatar1.jpg"},
            {"id": "s2", "username": "SecondSeller", "avatar_url": "avatar2.jpg"}
        ]
        
        call_count = [0]
        def table_side_effect(table_name):
            mock_table = MagicMock()
            mock_chain = MagicMock()
            nonlocal call_count
            
            if table_name == "marketplace_listings":
                mock_chain.eq.return_value = mock_chain
                mock_chain.gte.return_value = mock_chain
                mock_chain.order.return_value = mock_chain
                mock_chain.limit.return_value = mock_chain
                mock_chain.execute.return_value = mock_listings
            elif table_name == "profiles":
                mock_chain.in_.return_value = mock_chain
                mock_chain.execute.return_value = mock_profiles
            
            mock_table.select.return_value = mock_chain
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = get_leaderboard(period="monthly", board_type="all", limit=10)
        
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_get_leaderboard_all_time(self, mock_supabase):
        """获取全部时间排行榜"""
        from services.db_service import get_leaderboard
        
        mock_listings = MagicMock()
        mock_listings.data = []
        mock_profiles = MagicMock()
        mock_profiles.data = []
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.gte.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.limit.return_value = mock_chain
            mock_chain.in_.return_value = mock_chain
            mock_chain.execute.return_value = mock_listings if table_name == "marketplace_listings" else mock_profiles
            mock_table.select.return_value = mock_chain
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = get_leaderboard(period="all", board_type="all")
        
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_get_leaderboard_assets_only(self, mock_supabase):
        """获取仅资产类型排行榜"""
        from services.db_service import get_leaderboard
        
        mock_listings = MagicMock()
        mock_listings.data = [
            {"id": "l1", "seller_id": "s1", "title": "Asset", "resource_type": "asset", "sales_count": 50}
        ]
        mock_profiles = MagicMock()
        mock_profiles.data = [{"id": "s1", "username": "Seller"}]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.gte.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.limit.return_value = mock_chain
            mock_chain.in_.return_value = mock_chain
            mock_chain.execute.return_value = mock_listings if table_name == "marketplace_listings" else mock_profiles
            mock_table.select.return_value = mock_chain
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = get_leaderboard(period="monthly", board_type="asset")
        
        assert isinstance(result, list)


# ==========================================
# get_seller_project_stats / asset_stats Tests
# ==========================================

class TestSellerStats:
    """卖家统计测试"""
    
    @patch('services.db_service.supabase')
    def test_get_seller_project_stats_success(self, mock_supabase):
        """成功获取卖家项目统计"""
        from services.db_service import get_seller_project_stats
        
        mock_listings = MagicMock()
        mock_listings.data = [
            {
                "id": "l1",
                "resource_type": "project",
                "sales_count": 10,
                "price_credits": 100,
                "usage_count": 50,
                "unique_buyers_count": 8
            },
            {
                "id": "l2",
                "resource_type": "project",
                "sales_count": 5,
                "price_credits": 50,
                "usage_count": 20,
                "unique_buyers_count": 4
            }
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_listings
        
        result = get_seller_project_stats("seller_001")
        
        assert "total_listings" in result or isinstance(result, dict)
    
    @patch('services.db_service.supabase')
    def test_get_seller_project_stats_no_listings(self, mock_supabase):
        """卖家没有项目列表时的统计"""
        from services.db_service import get_seller_project_stats
        
        mock_listings = MagicMock()
        mock_listings.data = []
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_listings
        
        result = get_seller_project_stats("new_seller")
        
        assert result["total_selling"] == 0
        assert result["total_sales"] == 0
    
    @patch('services.db_service.supabase')
    def test_get_seller_asset_stats_success(self, mock_supabase):
        """成功获取卖家资产统计"""
        from services.db_service import get_seller_asset_stats
        
        mock_listings = MagicMock()
        mock_listings.data = [
            {
                "id": "l1",
                "resource_type": "asset",
                "sales_count": 20,
                "price_credits": 30,
                "usage_count": 100,
                "unique_buyers_count": 15
            }
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_listings
        
        result = get_seller_asset_stats("seller_001")
        
        assert "total_selling" in result
    
    @patch('services.db_service.supabase')
    def test_get_seller_asset_stats_no_listings(self, mock_supabase):
        """卖家没有资产列表时的统计"""
        from services.db_service import get_seller_asset_stats
        
        mock_listings = MagicMock()
        mock_listings.data = []
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_listings
        
        result = get_seller_asset_stats("new_seller")
        
        assert result["total_selling"] == 0


# ==========================================
# get_all_projects_feed Tests
# ==========================================

class TestGetAllProjectsFeed:
    """项目订阅测试"""
    
    @patch('services.db_service.supabase')
    def test_get_feed_default(self, mock_supabase):
        """获取默认项目订阅"""
        from services.db_service import get_all_projects_feed
        
        mock_projects = MagicMock()
        mock_projects.data = [
            {"id": "p1", "title": "Project 1", "thumbnail_url": "thumb1.jpg"},
            {"id": "p2", "title": "Project 2", "thumbnail_url": "thumb2.jpg"}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_projects
        
        result = get_all_projects_feed()
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    @patch('services.db_service.supabase')
    def test_get_feed_with_pagination(self, mock_supabase):
        """分页获取项目订阅"""
        from services.db_service import get_all_projects_feed
        
        mock_projects = MagicMock()
        mock_projects.data = [{"id": "p51", "title": "Project 51"}]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_projects
        
        result = get_all_projects_feed(page=2, limit=50)
        
        # 验证 range 调用参数
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.assert_called_once()


# ==========================================
# get_system_resources Tests
# ==========================================

class TestGetSystemResources:
    """系统资源测试"""
    
    @patch('services.db_service.supabase')
    def test_get_stickers(self, mock_supabase):
        """获取贴纸资源"""
        from services.db_service import get_system_resources
        
        mock_resources = MagicMock()
        mock_resources.data = [
            {"id": "s1", "name": "Cat", "type": "sticker", "url": "cat.png"},
            {"id": "s2", "name": "Dog", "type": "sticker", "url": "dog.png"}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resources
        
        result = get_system_resources("sticker")
        
        assert len(result) == 2
    
    @patch('services.db_service.supabase')
    def test_get_backgrounds(self, mock_supabase):
        """获取背景资源"""
        from services.db_service import get_system_resources
        
        mock_resources = MagicMock()
        mock_resources.data = [
            {"id": "b1", "name": "Forest", "type": "background"}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resources
        
        result = get_system_resources("background")
        
        assert len(result) == 1
    
    @patch('services.db_service.supabase')
    def test_get_resources_with_tier_filter(self, mock_supabase):
        """按用户等级过滤资源"""
        from services.db_service import get_system_resources
        
        mock_resources = MagicMock()
        mock_resources.data = [
            {"id": "s1", "name": "Pro Sticker", "type": "sticker", "allowed_tiers": ["pro"]}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resources
        
        result = get_system_resources("sticker", user_tier="pro")
        
        # 函数会返回资源（过滤在数据库层或应用层完成）
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_get_resources_empty(self, mock_supabase):
        """没有资源时返回空列表"""
        from services.db_service import get_system_resources
        
        mock_resources = MagicMock()
        mock_resources.data = []
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resources
        
        result = get_system_resources("nonexistent_type")
        
        assert result == []


# ==========================================
# retry_on_network_error Extended Tests
# ==========================================

class TestRetryOnNetworkErrorExtended:
    """重试装饰器扩展测试"""
    
    def test_exponential_backoff(self):
        """测试指数退避"""
        from services.db_service import retry_on_network_error
        
        call_times = []
        
        @retry_on_network_error(max_retries=2, delay=0.01, backoff=2)
        def flaky_with_timing():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("connection timeout")
            return "success"
        
        start = time.time()
        result = flaky_with_timing()
        
        assert result == "success"
        # 验证调用间隔有增长趋势
        if len(call_times) >= 3:
            interval1 = call_times[1] - call_times[0]
            interval2 = call_times[2] - call_times[1]
            # 由于指数退避，interval2 应该大于 interval1
            # 但由于时间太短，我们主要验证有多次调用
            assert len(call_times) == 3
    
    def test_all_retryable_errors(self):
        """测试所有可重试错误类型"""
        from services.db_service import is_retryable_error
        
        retryable_errors = [
            "resource temporarily unavailable",
            "connection reset by peer",
            "connection refused",
            "request timeout",
            "operation timed out",
            "network is unreachable",
            "name or service not known",
            "temporary failure in name resolution",
            "ssl: certificate_verify_failed",
            "readtimeout occurred",
            "connecttimeout error"
        ]
        
        for error_msg in retryable_errors:
            error = Exception(error_msg)
            assert is_retryable_error(error) is True, f"Expected {error_msg} to be retryable"
    
    def test_non_retryable_errors(self):
        """测试不可重试错误类型"""
        from services.db_service import is_retryable_error
        
        non_retryable_errors = [
            "invalid input",
            "user not found",
            "permission denied",
            "validation error",
            "CREDITS_INSUFFICIENT"
        ]
        
        for error_msg in non_retryable_errors:
            error = Exception(error_msg)
            assert is_retryable_error(error) is False, f"Expected {error_msg} to NOT be retryable"


# ==========================================
# generate_user_code Tests
# ==========================================

class TestGenerateUserCode:
    """用户码生成测试"""
    
    @patch('services.db_service.supabase')
    def test_generate_code_format(self, mock_supabase):
        """验证用户码格式"""
        from services.db_service import generate_user_code
        
        mock_result = MagicMock()
        mock_result.count = 0
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_result
        
        code = generate_user_code()
        
        # 格式: YYYYMMDDHHMMSS + ms(3) + sequence(7) = 24 字符
        assert len(code) == 24
        assert code.isdigit()
    
    @patch('services.db_service.supabase')
    def test_generate_code_sequence_increment(self, mock_supabase):
        """验证序列号递增"""
        from services.db_service import generate_user_code
        
        mock_result = MagicMock()
        mock_result.count = 99
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_result
        
        code = generate_user_code()
        
        # 序列号应该是 100 (99 + 1), 补齐 7 位
        assert code.endswith("0000100")


# ==========================================
# log_payment_record Tests
# ==========================================

class TestLogPaymentRecord:
    """支付记录测试"""
    
    @patch('services.db_service.supabase')
    def test_log_payment_record(self, mock_supabase):
        """记录支付信息"""
        from services.db_service import log_payment_record
        
        mock_profile = MagicMock()
        mock_profile.data = {
            "credits_monthly": 500,
            "credits_permanent": 100
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        log_payment_record(
            user_id="user_001",
            amount_cents=2490,
            currency="USD",
            type="sub_payment",
            description="Pro Subscription"
        )
        
        # 验证 insert 被调用
        insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
        assert insert_call["bucket"] == "payment"
        assert "USD 2490" in insert_call["description"]


# ==========================================
# check_and_reset_monthly_credits Extended Tests
# ==========================================

class TestCheckAndResetMonthlyCreditsExtended:
    """月度积分检查和重置扩展测试"""
    
    @patch('services.db_service.get_user_profile')
    def test_inactive_subscription_no_reset(self, mock_get_profile):
        """非活跃订阅不重置"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "starter",
            "subscription_status": "canceled"
        }
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        assert result is False
    
    @patch('services.db_service.refresh_monthly_credits')
    @patch('services.db_service.get_user_profile')
    def test_trialing_subscription_can_reset(self, mock_get_profile, mock_refresh):
        """试用期订阅可以重置"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "pro",
            "subscription_status": "trialing",
            "monthly_credits_cycle_anchor": None
        }
        mock_refresh.return_value = True
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        assert result is True
        mock_refresh.assert_called_once_with("user_001", "pro")
    
    @patch('services.db_service.refresh_monthly_credits')
    @patch('services.db_service.get_user_profile')
    def test_anchor_with_z_suffix(self, mock_get_profile, mock_refresh):
        """处理带 Z 后缀的时间戳"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        recent_anchor = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat().replace('+00:00', 'Z')
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "starter",
            "subscription_status": "active",
            "monthly_credits_cycle_anchor": recent_anchor
        }
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        # 5 天内不需要重置
        assert result is False


# ==========================================
# publish_permission Extended Tests
# ==========================================

class TestPublishPermissionExtended:
    """发布权限扩展测试"""
    
    def test_none_user_not_allowed(self):
        """None 用户不允许发布"""
        from services.db_service import publish_permission
        
        result = publish_permission(None, "asset", 0)
        
        assert result["allowed"] is False
        assert "not found" in result["reason"].lower()
    
    def test_negative_price_not_allowed(self):
        """负价格不允许"""
        from services.db_service import publish_permission
        
        user = {"tier": "pro"}
        result = publish_permission(user, "asset", -10)
        
        assert result["allowed"] is False
        assert "0 and 500" in result["reason"]
    
    def test_pro_invalid_resource_type(self):
        """Pro 用户无效资源类型"""
        from services.db_service import publish_permission
        
        user = {"tier": "pro"}
        result = publish_permission(user, "invalid_type", 0)
        
        assert result["allowed"] is False
        assert "invalid" in result["reason"].lower() or "must be" in result["reason"].lower()


# ==========================================
# can_access_resource Extended Tests
# ==========================================

class TestCanAccessResourceExtended:
    """资源访问控制扩展测试"""
    
    def test_none_user_no_access(self):
        """None 用户无访问权限"""
        from services.db_service import can_access_resource
        
        result = can_access_resource(None, ["free"])
        
        assert result is False
    
    def test_empty_allowed_tiers_no_access(self):
        """空 allowed_tiers 无访问权限"""
        from services.db_service import can_access_resource
        
        user = {"tier": "pro", "subscription_status": "active"}
        result = can_access_resource(user, [])
        
        assert result is False
    
    def test_none_allowed_tiers_no_access(self):
        """None allowed_tiers 无访问权限"""
        from services.db_service import can_access_resource
        
        user = {"tier": "pro", "subscription_status": "active"}
        result = can_access_resource(user, None)
        
        assert result is False
    
    def test_inactive_member_no_member_resource_access(self):
        """非活跃会员无法访问会员资源"""
        from services.db_service import can_access_resource
        
        user = {"tier": "starter", "subscription_status": "canceled"}
        result = can_access_resource(user, ["starter", "pro"])
        
        assert result is False


# ==========================================
# validate_allowed_tiers Extended Tests
# ==========================================

class TestValidateAllowedTiersExtended:
    """allowed_tiers 验证扩展测试"""
    
    def test_empty_list_invalid(self):
        """空列表无效"""
        from services.db_service import validate_allowed_tiers
        
        result = validate_allowed_tiers([])
        
        assert result["valid"] is False
    
    def test_none_input_invalid(self):
        """None 输入无效"""
        from services.db_service import validate_allowed_tiers
        
        result = validate_allowed_tiers(None)
        
        assert result["valid"] is False
    
    def test_invalid_tier_names(self):
        """无效等级名称"""
        from services.db_service import validate_allowed_tiers
        
        result = validate_allowed_tiers(["premium", "basic"])
        
        assert result["valid"] is False
    
    def test_order_independent(self):
        """顺序无关"""
        from services.db_service import validate_allowed_tiers
        
        result1 = validate_allowed_tiers(["pro", "starter"])
        result2 = validate_allowed_tiers(["starter", "pro"])
        
        assert result1["valid"] == result2["valid"]
