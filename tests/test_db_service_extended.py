"""
db_service 扩展测试 - 覆盖更多函数
目标: 将覆盖率从 11% 提升到 90%+

模块函数清单:
- retry_on_network_error (装饰器)
- create_user_profile
- update_subscription_tier
- update_user_profile
- get_user_timezone
- check_and_reset_monthly_credits_if_needed
- log_credit_transaction
- log_payment_record
- add_credits_monthly
- get_credit_history
- get_user_projects
- get_project_detail
- permanently_hide_project
- get_dashboard_projects
- user_restore_project
- update_project_hash
- get_all_projects_feed
- get_dashboard_assets
- get_user_deleted_assets
- get_user_deleted_projects
- get_marketplace_listings
- get_marketplace_item
- get_seller_listings
- unpublish_listing
- update_listing
- execute_purchase
- 管理员函数 (admin_*)
- 系统配置函数 (get_system_config, etc.)
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone, timedelta
import time


# ==========================================
# retry_on_network_error Decorator Tests
# ==========================================

class TestRetryOnNetworkError:
    """重试装饰器测试"""
    
    def test_no_retry_on_success(self):
        """成功时不重试"""
        from services.db_service import retry_on_network_error
        
        call_count = 0
        
        @retry_on_network_error(max_retries=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_network_error(self):
        """网络错误时重试"""
        from services.db_service import retry_on_network_error
        
        call_count = 0
        
        @retry_on_network_error(max_retries=3, delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("connection timeout")
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert call_count == 3
    
    def test_no_retry_on_business_error(self):
        """业务错误不重试"""
        from services.db_service import retry_on_network_error
        
        call_count = 0
        
        @retry_on_network_error(max_retries=3)
        def business_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")
        
        with pytest.raises(ValueError):
            business_error_func()
        
        assert call_count == 1
    
    def test_max_retries_exceeded(self):
        """超出最大重试次数后抛出异常"""
        from services.db_service import retry_on_network_error
        
        call_count = 0
        
        @retry_on_network_error(max_retries=2, delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("connection reset")
        
        with pytest.raises(Exception) as exc_info:
            always_fail()
        
        assert "connection reset" in str(exc_info.value)
        assert call_count == 3  # 1 initial + 2 retries


# ==========================================
# User Profile Management Tests
# ==========================================

class TestCreateUserProfile:
    """创建用户档案测试"""
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    @patch('services.db_service.generate_user_code')
    def test_create_user_profile_success(self, mock_gen_code, mock_supabase, mock_log):
        """成功创建用户档案"""
        from services.db_service import create_user_profile
        
        mock_gen_code.return_value = "202512301430251230000001"
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        create_user_profile(
            user_id="user_001",
            email="test@example.com",
            username="testuser",
            avatar_url="https://example.com/avatar.jpg",
            first_name="Test",
            last_name="User",
            timezone="America/New_York"
        )
        
        # 验证 insert 被调用
        mock_supabase.table.return_value.insert.assert_called_once()
        insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
        
        assert insert_call["id"] == "user_001"
        assert insert_call["email"] == "test@example.com"
        assert insert_call["credits_permanent"] == 50  # 注册奖励
        assert insert_call["tier"] == "free"
        
        # 验证记录交易
        mock_log.assert_called_once()


class TestUpdateSubscriptionTier:
    """更新订阅等级测试"""
    
    @patch('services.db_service.supabase')
    def test_update_to_pro(self, mock_supabase):
        """升级到 Pro"""
        from services.db_service import update_subscription_tier
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        update_subscription_tier("user_001", "pro", "cus_123")
        
        mock_supabase.table.return_value.update.assert_called_once()
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        
        assert update_call["tier"] == "pro"
        assert update_call["subscription_status"] == "active"
        assert update_call["stripe_customer_id"] == "cus_123"
    
    @patch('services.db_service.supabase')
    def test_downgrade_to_free(self, mock_supabase):
        """降级到 Free"""
        from services.db_service import update_subscription_tier
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        update_subscription_tier("user_001", "free", subscription_status="canceled")
        
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["tier"] == "free"
        assert update_call["subscription_status"] == "canceled"


class TestUpdateUserProfile:
    """更新用户档案测试"""
    
    @patch('services.db_service.supabase')
    def test_update_multiple_fields(self, mock_supabase):
        """更新多个字段"""
        from services.db_service import update_user_profile
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = update_user_profile(
            user_id="user_001",
            avatar_url="https://new-avatar.jpg",
            username="newname",
            timezone="Asia/Shanghai"
        )
        
        assert result is True
        mock_supabase.table.return_value.update.assert_called_once()
    
    @patch('services.db_service.supabase')
    def test_update_no_fields(self, mock_supabase):
        """没有字段更新时返回 False"""
        from services.db_service import update_user_profile
        
        result = update_user_profile(user_id="user_001")
        
        assert result is False
        mock_supabase.table.return_value.update.assert_not_called()


class TestGetUserTimezone:
    """获取用户时区测试"""
    
    @patch('services.db_service.supabase')
    def test_get_user_timezone_exists(self, mock_supabase):
        """用户有设置时区"""
        from services.db_service import get_user_timezone
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"timezone": "Asia/Tokyo"}
        )
        
        tz = get_user_timezone("user_001")
        
        assert tz == "Asia/Tokyo"
    
    @patch('services.db_service.supabase')
    def test_get_user_timezone_default_utc(self, mock_supabase):
        """用户没有时区，返回 UTC"""
        from services.db_service import get_user_timezone
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        
        tz = get_user_timezone("user_001")
        
        assert tz == "UTC"


# ==========================================
# Monthly Credits Reset Tests
# ==========================================

class TestCheckAndResetMonthlyCredits:
    """检查并重置月度积分测试"""
    
    @patch('services.db_service.refresh_monthly_credits')
    @patch('services.db_service.get_user_profile')
    def test_free_user_no_reset(self, mock_get_profile, mock_refresh):
        """Free 用户不需要重置"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "free",
            "subscription_status": "inactive"
        }
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        assert result is False
        mock_refresh.assert_not_called()
    
    @patch('services.db_service.refresh_monthly_credits')
    @patch('services.db_service.get_user_profile')
    def test_no_anchor_triggers_refresh(self, mock_get_profile, mock_refresh):
        """没有 cycle_anchor 时触发刷新"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "pro",
            "subscription_status": "active",
            "monthly_credits_cycle_anchor": None
        }
        mock_refresh.return_value = True
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        assert result is True
        mock_refresh.assert_called_once_with("user_001", "pro")
    
    @patch('services.db_service.refresh_monthly_credits')
    @patch('services.db_service.get_user_profile')
    def test_anchor_over_30_days_triggers_refresh(self, mock_get_profile, mock_refresh):
        """超过 30 天触发刷新"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        old_anchor = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "starter",
            "subscription_status": "active",
            "monthly_credits_cycle_anchor": old_anchor
        }
        mock_refresh.return_value = True
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        assert result is True
        mock_refresh.assert_called_once()
    
    @patch('services.db_service.refresh_monthly_credits')
    @patch('services.db_service.get_user_profile')
    def test_recent_anchor_no_refresh(self, mock_get_profile, mock_refresh):
        """最近刷新过，不需要再刷新"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        recent_anchor = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "pro",
            "subscription_status": "active",
            "monthly_credits_cycle_anchor": recent_anchor
        }
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        assert result is False
        mock_refresh.assert_not_called()
    
    @patch('services.db_service.refresh_monthly_credits')
    @patch('services.db_service.get_user_profile')
    def test_invalid_anchor_triggers_refresh(self, mock_get_profile, mock_refresh):
        """无效的 anchor 格式触发刷新"""
        from services.db_service import check_and_reset_monthly_credits_if_needed
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "pro",
            "subscription_status": "active",
            "monthly_credits_cycle_anchor": "invalid-date"
        }
        mock_refresh.return_value = True
        
        result = check_and_reset_monthly_credits_if_needed("user_001")
        
        assert result is True


# ==========================================
# Transaction Logging Tests
# ==========================================

class TestLogCreditTransaction:
    """积分交易日志测试"""
    
    @patch('services.db_service.supabase')
    def test_log_transaction_success(self, mock_supabase):
        """成功记录交易"""
        from services.db_service import log_credit_transaction
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        log_credit_transaction(
            user_id="user_001",
            amount=50,
            bucket="monthly",
            balance_monthly_after=450,
            balance_permanent_after=100,
            type="generation",
            description="AI Image Generation",
            timezone="America/New_York"
        )
        
        insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
        
        assert insert_call["user_id"] == "user_001"
        assert insert_call["amount"] == 50
        assert insert_call["bucket"] == "monthly"
        assert insert_call["timezone"] == "America/New_York"


class TestLogPaymentRecord:
    """支付记录测试"""
    
    @patch('services.db_service.supabase')
    def test_log_payment_success(self, mock_supabase):
        """成功记录支付"""
        from services.db_service import log_payment_record
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        log_payment_record(
            user_id="user_001",
            amount_cents=2490,
            currency="USD",
            type="sub_payment",
            description="Pro subscription"
        )
        
        mock_supabase.table.return_value.insert.assert_called_once()


# ==========================================
# Credits Management Tests
# ==========================================

class TestAddCreditsMonthly:
    """添加月度积分测试 (v3.22: 使用 RPC)"""
    
    @patch('services.db_service.supabase')
    def test_add_monthly_credits(self, mock_supabase):
        """添加月度积分 (RPC 实现)"""
        from services.db_service import add_credits_monthly
        
        # Mock RPC 返回添加结果
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": True,
            "balance_monthly": 600,
            "balance_permanent": 50
        })
        
        result = add_credits_monthly("user_001", 500, "Monthly subscription grant")
        
        assert result["balance_monthly"] == 600
        assert result["balance_permanent"] == 50


class TestGetCreditHistory:
    """获取积分历史测试"""
    
    @patch('services.db_service.supabase')
    def test_get_credit_history_with_pagination(self, mock_supabase):
        """分页获取积分历史"""
        from services.db_service import get_credit_history
        
        mock_items = [
            {"id": "tx_001", "amount": -5, "type": "generation"},
            {"id": "tx_002", "amount": -5, "type": "generation"},
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=mock_items)
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(count=50)
        
        result = get_credit_history("user_001", page=2, limit=20)
        
        assert "items" in result
        assert "total" in result


# ==========================================
# Project Management Extended Tests
# ==========================================

class TestGetUserProjects:
    """获取用户项目测试"""
    
    @patch('services.db_service.supabase')
    def test_get_projects_with_search(self, mock_supabase):
        """带搜索的项目获取"""
        from services.db_service import get_user_projects
        
        mock_projects = [{"id": "proj_001", "title": "Cat Story"}]
        mock_listings = []
        
        # Mock project query
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.ilike.return_value.range.return_value.order.return_value.execute.return_value = MagicMock(data=mock_projects)
        
        # Mock listings query
        mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(data=mock_listings)
        
        result = get_user_projects("user_001", search="Cat")
        
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_get_projects_without_canvas_data(self, mock_supabase):
        """不包含画布数据的项目获取"""
        from services.db_service import get_user_projects
        
        mock_projects = [{"id": "proj_001", "title": "Test"}]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.range.return_value.order.return_value.execute.return_value = MagicMock(data=mock_projects)
        mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_user_projects("user_001", include_canvas_data=False)
        
        assert isinstance(result, list)


class TestGetProjectDetail:
    """获取项目详情测试"""
    
    @patch('services.db_service.supabase')
    def test_get_project_with_canvas_data(self, mock_supabase):
        """获取包含画布数据的项目"""
        from services.db_service import get_project_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "proj_001",
            "canvas_data": {"pages": [{"canvasJson": {"objects": []}}]}
        })
        
        result = get_project_detail("proj_001", "user_001")
        
        assert result is not None
        assert "canvas_data" in result
    
    @patch('services.db_service.supabase')
    def test_get_project_not_found(self, mock_supabase):
        """项目不存在"""
        from services.db_service import get_project_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        
        result = get_project_detail("nonexistent", "user_001")
        
        assert result is None


class TestPermanentlyHideProject:
    """永久隐藏项目测试"""
    
    @patch('services.db_service.supabase')
    def test_permanently_hide_success(self, mock_supabase):
        """成功永久隐藏项目"""
        from services.db_service import permanently_hide_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "proj_001"}])
        
        result = permanently_hide_project("proj_001", "user_001")
        
        mock_supabase.table.return_value.update.assert_called_once()


class TestUserRestoreProject:
    """用户恢复项目测试"""
    
    @patch('services.db_service.supabase')
    def test_restore_project_success(self, mock_supabase):
        """成功恢复项目"""
        from services.db_service import user_restore_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "proj_001"}])
        
        result = user_restore_project("proj_001", "user_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestUpdateProjectHash:
    """更新项目哈希测试"""
    
    @patch('services.db_service.supabase')
    def test_update_hash(self, mock_supabase):
        """更新项目哈希"""
        from services.db_service import update_project_hash
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        update_project_hash("proj_001", "abc123hash")
        
        mock_supabase.table.return_value.update.assert_called()


class TestGetAllProjectsFeed:
    """获取所有项目订阅测试"""
    
    @patch('services.db_service.supabase')
    def test_get_feed(self, mock_supabase):
        """获取项目订阅"""
        from services.db_service import get_all_projects_feed
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {"id": "proj_001", "title": "Test"}
        ])
        
        result = get_all_projects_feed(page=1, limit=10)
        
        assert isinstance(result, list)


# ==========================================
# Deleted Items Tests
# ==========================================

class TestGetUserDeletedProjects:
    """获取用户已删除项目测试"""
    
    @patch('services.db_service.supabase')
    def test_get_deleted_projects(self, mock_supabase):
        """获取已删除项目"""
        from services.db_service import get_user_deleted_projects
        
        # Mock count query
        mock_count = MagicMock()
        mock_count.count = 1
        
        # Mock data query
        mock_data = MagicMock()
        mock_data.data = [{"id": "proj_001", "is_deleted": True}]
        
        # 根据实际代码的调用链
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.range.return_value.execute.return_value = mock_data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = mock_count
        
        result = get_user_deleted_projects("user_001")
        
        assert "items" in result
        assert "total" in result


class TestGetUserDeletedAssets:
    """获取用户已删除资产测试"""
    
    @patch('services.db_service.supabase')
    def test_get_deleted_assets(self, mock_supabase):
        """获取已删除资产"""
        from services.db_service import get_user_deleted_assets
        
        # Mock count query
        mock_count = MagicMock()
        mock_count.count = 1
        
        # Mock data query
        mock_data = MagicMock()
        mock_data.data = [{"id": "asset_001", "is_deleted": True}]
        
        # 根据实际代码的调用链
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.range.return_value.execute.return_value = mock_data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = mock_count
        
        result = get_user_deleted_assets("user_001")
        
        assert "items" in result
        assert "total" in result


# ==========================================
# Marketplace Tests
# ==========================================

class TestGetMarketplaceListings:
    """获取市场商品列表测试"""
    
    @patch('services.db_service.supabase')
    def test_get_public_listings(self, mock_supabase):
        """获取公开商品列表"""
        from services.db_service import get_marketplace_listings
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {"id": "listing_001", "title": "Cool Asset"}
        ])
        
        result = get_marketplace_listings()
        
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_get_my_listings(self, mock_supabase):
        """获取我的商品列表"""
        from services.db_service import get_marketplace_listings
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {"id": "listing_001", "seller_id": "user_001"}
        ])
        
        result = get_marketplace_listings(mine=True, user_id="user_001")
        
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_get_listings_with_filters(self, mock_supabase):
        """带过滤条件获取商品"""
        from services.db_service import get_marketplace_listings
        
        mock_result = MagicMock()
        mock_result.data = []
        
        # 链式调用返回 mock_result
        mock_query = MagicMock()
        mock_query.range.return_value.execute.return_value = mock_result
        mock_query.order.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.contains.return_value = mock_query
        
        mock_supabase.table.return_value.select.return_value = mock_query
        
        result = get_marketplace_listings(
            resource_type="asset",
            tier_filter="pro",
            price_filter="free",
            sort="popular"
        )
        
        assert result == []


class TestGetMarketplaceItem:
    """获取市场商品详情测试"""
    
    @patch('services.db_service.supabase')
    def test_get_item_as_buyer(self, mock_supabase):
        """买家获取商品详情"""
        from services.db_service import get_marketplace_item
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "listing_001",
            "seller_id": "seller_001",
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False
        })
        
        result = get_marketplace_item("listing_001", user_id="buyer_001")
        
        assert result is not None
    
    @patch('services.db_service.supabase')
    def test_get_item_as_seller(self, mock_supabase):
        """卖家获取自己的商品（包括未审核）"""
        from services.db_service import get_marketplace_item
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "listing_001",
            "seller_id": "seller_001",
            "moderation_status": "pending",
            "is_public": True,
            "is_deleted": False
        })
        
        result = get_marketplace_item("listing_001", user_id="seller_001")
        
        assert result is not None
    
    @patch('services.db_service.supabase')
    def test_get_hidden_item_forbidden(self, mock_supabase):
        """非卖家不能获取未审核商品"""
        from services.db_service import get_marketplace_item
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "listing_001",
            "seller_id": "seller_001",
            "moderation_status": "pending",
            "is_public": True,
            "is_deleted": False
        })
        
        result = get_marketplace_item("listing_001", user_id="other_user")
        
        assert result is None


class TestGetSellerListings:
    """获取卖家商品列表测试"""
    
    @patch('services.db_service.supabase')
    def test_get_seller_listings(self, mock_supabase):
        """获取卖家商品"""
        from services.db_service import get_seller_listings
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {"id": "listing_001"}
        ])
        
        result = get_seller_listings("seller_001")
        
        assert isinstance(result, list)


class TestUnpublishListing:
    """下架商品测试"""
    
    @patch('services.db_service.supabase')
    def test_unpublish_success(self, mock_supabase):
        """成功下架商品"""
        from services.db_service import unpublish_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "listing_001"}])
        
        result = unpublish_listing("listing_001", "seller_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestSubmitListingForReview:
    """提交商品审核测试"""
    
    @patch('services.db_service.supabase')
    def test_submit_draft_for_review(self, mock_supabase):
        """提交草稿审核"""
        from services.db_service import submit_listing_for_review
        
        # Mock get listing
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "listing_001",
            "moderation_status": "draft"
        })
        
        # Mock update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "listing_001",
            "moderation_status": "pending"
        }])
        
        result = submit_listing_for_review("listing_001", "seller_001")
        
        assert result is not None
    
    @patch('services.db_service.supabase')
    def test_submit_approved_fails(self, mock_supabase):
        """已审核的商品不能再提交"""
        from services.db_service import submit_listing_for_review
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "listing_001",
            "moderation_status": "approved"
        })
        
        result = submit_listing_for_review("listing_001", "seller_001")
        
        assert result.get("error") is not None


# ==========================================
# System Config Tests
# ==========================================

class TestGetSystemConfig:
    """获取系统配置测试"""
    
    @patch('services.db_service._get_cached_config')
    def test_get_config_from_cache(self, mock_cache):
        """从缓存获取配置"""
        from services.db_service import get_system_config
        
        mock_cache.return_value = "cached_value"
        
        result = get_system_config("test_key")
        
        assert result == "cached_value"
    
    @patch('services.db_service._set_cached_config')
    @patch('services.db_service._get_cached_config')
    @patch('services.db_service.supabase')
    def test_get_config_from_db(self, mock_supabase, mock_cache_get, mock_cache_set):
        """从数据库获取配置"""
        from services.db_service import get_system_config
        
        mock_cache_get.return_value = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "value": "db_value",
            "value_type": "string",
            "is_active": True
        })
        
        result = get_system_config("test_key")
        
        assert result == "db_value"
        mock_cache_set.assert_called()
    
    @patch('services.db_service._get_cached_config')
    @patch('services.db_service.supabase')
    def test_get_config_default(self, mock_supabase, mock_cache):
        """配置不存在返回默认值"""
        from services.db_service import get_system_config
        
        mock_cache.return_value = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("Not found")
        
        result = get_system_config("nonexistent", default_value="default")
        
        assert result == "default"


class TestGetAllSystemConfigs:
    """获取所有系统配置测试"""
    
    @patch('services.db_service._get_cached_config_dict')
    def test_get_all_from_cache(self, mock_cache):
        """从缓存获取所有配置"""
        from services.db_service import get_all_system_configs
        
        mock_cache.return_value = {"key1": {"value": "val1"}}
        
        result = get_all_system_configs()
        
        assert result == {"key1": {"value": "val1"}}
    
    @patch('services.db_service._set_cached_config_dict')
    @patch('services.db_service._get_cached_config_dict')
    @patch('services.db_service.supabase')
    def test_get_all_from_db(self, mock_supabase, mock_cache_get, mock_cache_set):
        """从数据库获取所有配置"""
        from services.db_service import get_all_system_configs
        
        mock_cache_get.return_value = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.execute.return_value = MagicMock(data=[
            {"key": "key1", "value": "val1"}
        ])
        
        result = get_all_system_configs()
        
        assert "key1" in result


class TestGetConfigsByGroup:
    """按组获取配置测试"""
    
    @patch('services.db_service._set_cached_config_dict')
    @patch('services.db_service._get_cached_config_dict')
    @patch('services.db_service.supabase')
    def test_get_by_group(self, mock_supabase, mock_cache_get, mock_cache_set):
        """按组获取配置"""
        from services.db_service import get_configs_by_group
        
        mock_cache_get.return_value = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"key": "rate_limit.default", "value": "100/minute"}
        ])
        
        result = get_configs_by_group("rate_limit")
        
        assert "rate_limit.default" in result


class TestInvalidateConfigCache:
    """缓存失效测试"""
    
    @patch('services.db_service.cache_service')
    def test_invalidate_single_key(self, mock_cache):
        """失效单个键"""
        from services.db_service import _invalidate_config_cache
        
        _invalidate_config_cache("test_key")
        
        mock_cache.delete.assert_called()
        mock_cache.delete_pattern.assert_called()
    
    @patch('services.db_service.cache_service')
    def test_invalidate_all(self, mock_cache):
        """失效所有配置"""
        from services.db_service import _invalidate_config_cache
        
        _invalidate_config_cache(None)
        
        mock_cache.delete_pattern.assert_called()


# ==========================================
# Dashboard Tests
# ==========================================

class TestGetDashboardProjects:
    """Dashboard 项目测试"""
    
    @patch('services.db_service.supabase')
    def test_get_dashboard_all_projects(self, mock_supabase):
        """获取 Dashboard 所有项目"""
        from services.db_service import get_dashboard_projects
        
        # Mock count
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(count=10)
        
        # Mock data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {"id": "proj_001"}
        ])
        
        result = get_dashboard_projects("user_001", view_type="all")
        
        assert "items" in result or isinstance(result, list)


class TestGetDashboardAssets:
    """Dashboard 资产测试"""
    
    @patch('services.db_service.supabase')
    def test_get_dashboard_assets(self, mock_supabase):
        """获取 Dashboard 资产"""
        from services.db_service import get_dashboard_assets
        
        # Mock count
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(count=5)
        
        # Mock data with proper chain
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[{"id": "asset_001"}])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_dashboard_assets("user_001", view_type="all")
        
        assert "items" in result or isinstance(result, list)


# ==========================================
# Backward Compatibility Tests
# ==========================================

class TestBackwardCompatibility:
    """向后兼容函数测试"""
    
    @patch('services.db_service.credit_deduct')
    def test_deduct_credits_atomic(self, mock_deduct):
        """deduct_credits_atomic 调用 credit_deduct"""
        from services.db_service import deduct_credits_atomic
        
        mock_deduct.return_value = {"success": True}
        
        result = deduct_credits_atomic("user_001", 50, "generation", "Test")
        
        assert result is True
        mock_deduct.assert_called_once()
    
    @patch('services.db_service.add_credits_permanent')
    def test_add_credits(self, mock_add):
        """add_credits 调用 add_credits_permanent"""
        from services.db_service import add_credits
        
        mock_add.return_value = {"balance_permanent": 150}
        
        result = add_credits("user_001", 100, "Purchase")
        
        mock_add.assert_called_once()


# ==========================================
# Admin Functions Tests
# ==========================================

class TestAdminGetSystemConfigs:
    """管理员获取系统配置测试"""
    
    @patch('services.db_service.supabase')
    def test_admin_get_configs_paginated(self, mock_supabase):
        """管理员分页获取配置"""
        from services.db_service import admin_get_system_configs
        
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {"key": "config1", "value": "val1"}
        ])
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(count=1)
        
        result = admin_get_system_configs(page=1, limit=10)
        
        assert "items" in result


class TestAdminGetConfigGroups:
    """管理员获取配置组测试"""
    
    @patch('services.db_service.supabase')
    def test_get_config_groups(self, mock_supabase):
        """获取配置组列表"""
        from services.db_service import admin_get_config_groups
        
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=[
            {"config_group": "rate_limit"},
            {"config_group": "ai"},
        ])
        
        result = admin_get_config_groups()
        
        assert isinstance(result, list)


class TestAdminCreateSystemConfig:
    """管理员创建系统配置测试"""
    
    @patch('services.db_service._log_config_audit')
    @patch('services.db_service._invalidate_config_cache')
    @patch('services.db_service.supabase')
    def test_create_config_success(self, mock_supabase, mock_invalidate, mock_log):
        """成功创建配置"""
        from services.db_service import admin_create_system_config
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "key": "new_config",
            "value": "new_value"
        }])
        
        result = admin_create_system_config(
            key="new_config",
            value="new_value",
            value_type="string",
            config_group="test",
            admin_id="admin_001"
        )
        
        assert result is not None
        mock_invalidate.assert_called()


class TestAdminUpdateSystemConfig:
    """管理员更新系统配置测试"""
    
    @patch('services.db_service._log_config_audit')
    @patch('services.db_service._invalidate_config_cache')
    @patch('services.db_service.supabase')
    def test_update_config_success(self, mock_supabase, mock_invalidate, mock_log):
        """成功更新配置"""
        from services.db_service import admin_update_system_config
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "key": "test_config",
            "value": "old_value"
        })
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "key": "test_config",
            "value": "new_value"
        }])
        
        result = admin_update_system_config(
            key="test_config",
            value="new_value",
            admin_id="admin_001"
        )
        
        assert result is not None
        mock_invalidate.assert_called()


class TestAdminDeleteSystemConfig:
    """管理员删除系统配置测试"""
    
    @patch('services.db_service._log_config_audit')
    @patch('services.db_service._invalidate_config_cache')
    @patch('services.db_service.supabase')
    def test_delete_config_success(self, mock_supabase, mock_invalidate, mock_log):
        """成功删除配置"""
        from services.db_service import admin_delete_system_config
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "key": "test_config",
            "value": "value"
        })
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = admin_delete_system_config("test_config", admin_id="admin_001")
        
        assert result is True
        mock_invalidate.assert_called()


class TestInvalidateConfigCacheApi:
    """API 缓存失效测试"""
    
    @patch('services.db_service._invalidate_config_cache')
    def test_invalidate_cache_api(self, mock_invalidate):
        """API 调用缓存失效"""
        from services.db_service import invalidate_config_cache_api
        
        result = invalidate_config_cache_api()
        
        # 检查是否调用了 _invalidate_config_cache
        mock_invalidate.assert_called_once()
        assert result is True
