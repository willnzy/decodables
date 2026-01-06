"""
Database Users Service Tests
services/db/users.py 模块测试

覆盖目标: 95%+
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


@pytest.fixture
def mock_supabase():
    """创建 mock Supabase 客户端"""
    return MagicMock()


class TestGetUserProfile:
    """测试 get_user_profile"""
    
    @patch('services.db.users.supabase')
    def test_returns_user_when_found(self, mock_supabase):
        """返回用户资料"""
        from services.db.users import get_user_profile
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_001", "tier": "pro", "credits_monthly": 1000}]
        )
        
        result = get_user_profile("user_001")
        
        assert result is not None
        assert result["id"] == "user_001"
    
    @patch('services.db.users.supabase')
    def test_returns_none_when_not_found(self, mock_supabase):
        """用户不存在返回 None"""
        from services.db.users import get_user_profile
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_user_profile("nonexistent")
        
        assert result is None
    
    @patch('services.db.users.supabase', None)
    def test_returns_none_when_supabase_not_available(self):
        """Supabase 不可用时返回 None"""
        from services.db.users import get_user_profile
        result = get_user_profile("user_001")
        assert result is None
    
    @patch('services.db.users.supabase')
    def test_returns_none_for_empty_user_id(self, mock_supabase):
        """空用户 ID 返回 None"""
        from services.db.users import get_user_profile
        result = get_user_profile("")
        assert result is None


class TestCreateUserProfile:
    """测试 create_user_profile"""
    
    @patch('services.db.users.log_credit_transaction')
    @patch('services.db.users.generate_user_code')
    @patch('services.db.users.supabase')
    def test_creates_profile_with_signup_bonus(self, mock_supabase, mock_gen_code, mock_log):
        """创建用户时给予 50 永久积分"""
        from services.db.users import create_user_profile
        
        mock_gen_code.return_value = "ABC123"
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new_user", "credits_permanent": 50}]
        )
        
        # 使用完整的参数签名
        result = create_user_profile(
            user_id="new_user", 
            email="test@example.com",
            username="testuser",
            avatar_url="https://example.com/avatar.png"
        )
        
        assert result is not None
        # 验证 insert 被调用
        mock_supabase.table.return_value.insert.assert_called_once()
        # 验证 credits_permanent 为 50
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args.get("credits_permanent") == 50
        assert call_args.get("username") == "testuser"
        # 验证 log_credit_transaction 被调用
        mock_log.assert_called_once()
    
    @patch('services.db.users.generate_user_code')
    @patch('services.db.users.supabase', None)
    def test_returns_none_when_supabase_not_available(self, mock_gen_code):
        """Supabase 不可用时返回 None"""
        from services.db.users import create_user_profile
        result = create_user_profile("u1", "e@e.com", "user", "https://avatar.com/u.png")
        assert result is None


class TestUpdateSubscriptionTier:
    """测试 update_subscription_tier"""
    
    @patch('services.db.users.supabase')
    def test_updates_tier_and_status(self, mock_supabase):
        """更新订阅等级和状态"""
        from services.db.users import update_subscription_tier
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_001", "tier": "pro", "subscription_status": "active"}]
        )
        
        result = update_subscription_tier("user_001", "pro", subscription_status="active")
        
        assert result is not None
        mock_supabase.table.return_value.update.assert_called()


class TestUpdateUserTimezone:
    """测试 update_user_timezone"""
    
    @patch('services.db.users.supabase')
    def test_updates_timezone(self, mock_supabase):
        """更新用户时区"""
        from services.db.users import update_user_timezone
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_001", "timezone": "Asia/Shanghai"}]
        )
        
        result = update_user_timezone("user_001", "Asia/Shanghai")
        
        assert result is not None


class TestGetUserTimezone:
    """测试 get_user_timezone"""
    
    @patch('services.db.users.supabase')
    def test_returns_timezone(self, mock_supabase):
        """返回用户时区"""
        from services.db.users import get_user_timezone
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"timezone": "America/New_York"}]
        )
        
        result = get_user_timezone("user_001")
        
        assert result == "America/New_York"
    
    @patch('services.db.users.supabase')
    def test_returns_default_when_not_set(self, mock_supabase):
        """未设置时区返回默认值"""
        from services.db.users import get_user_timezone
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"timezone": None}]
        )
        
        result = get_user_timezone("user_001")
        
        assert result == "UTC"  # 默认 UTC


class TestGenerateUserCode:
    """测试 generate_user_code"""
    
    @patch('services.db.users.supabase')
    def test_generates_6_char_code(self, mock_supabase):
        """生成 6 位用户码"""
        from services.db.users import generate_user_code
        
        # 模拟没有重复的 user_code
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        code = generate_user_code()
        
        # 函数生成 6 位码, 如果前 10 次都失败则返回 8 位
        assert len(code) in [6, 8]
        assert code.isalnum()
    
    @patch('services.db.users.supabase')
    def test_retries_on_collision_and_fallback_to_8_char(self, mock_supabase):
        """碰撞重试后回退到 8 位码"""
        from services.db.users import generate_user_code
        
        # 模拟所有 6 位码都有冲突
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "existing"}]
        )
        
        code = generate_user_code()
        
        # 10 次碰撞后返回 8 位
        assert len(code) == 8


class TestRefreshMonthlyCredits:
    """测试 refresh_monthly_credits"""
    
    @patch('services.db.users.log_credit_transaction')
    @patch('services.db.users.supabase')
    def test_starter_gets_500_credits(self, mock_supabase, mock_log):
        """Starter 重置为 500 积分"""
        from services.db.users import refresh_monthly_credits
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_001", "credits_monthly": 500}]
        )
        
        result = refresh_monthly_credits("user_001", "starter")
        
        assert result is not None
        assert result["credits_monthly"] == 500
    
    @patch('services.db.users.log_credit_transaction')
    @patch('services.db.users.supabase')
    def test_pro_gets_1000_credits(self, mock_supabase, mock_log):
        """Pro 重置为 1000 积分"""
        from services.db.users import refresh_monthly_credits
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_001", "credits_monthly": 1000}]
        )
        
        result = refresh_monthly_credits("user_001", "pro")
        
        assert result is not None
        assert result["credits_monthly"] == 1000
    
    @patch('services.db.users.supabase')
    def test_free_tier_gets_no_refresh(self, mock_supabase):
        """Free 用户不重置"""
        from services.db.users import refresh_monthly_credits
        
        result = refresh_monthly_credits("user_001", "free")
        
        assert result is None


class TestCreditDeduct:
    """测试 credit_deduct"""
    
    @patch('services.db.users.supabase')
    def test_deducts_via_rpc(self, mock_supabase):
        """通过 RPC 扣除积分"""
        from services.db.users import credit_deduct
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": True,
            "balance_monthly": 70,
            "balance_permanent": 50,
            "total_balance": 120,
            "deducted_from": "monthly"
        })
        
        result = credit_deduct("user_001", 30, "generation", "Test")
        
        assert result["success"] is True
        assert result["deducted_from"] == "monthly"
    
    @patch('services.db.users.supabase')
    def test_returns_error_on_insufficient_credits(self, mock_supabase):
        """积分不足时返回错误"""
        from services.db.users import credit_deduct
        
        # 模拟 RPC 抛出异常
        mock_supabase.rpc.return_value.execute.side_effect = Exception("INSUFFICIENT_CREDITS")
        
        result = credit_deduct("user_001", 1000, "generation", "Test")
        
        assert result["success"] is False
        assert "INSUFFICIENT" in result["error"]
    
    @patch('services.db.users.supabase')
    def test_returns_error_on_no_data(self, mock_supabase):
        """RPC 无数据返回错误"""
        from services.db.users import credit_deduct
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=None)
        
        result = credit_deduct("user_001", 30, "generation", "Test")
        
        assert result["success"] is False


class TestAddCredits:
    """测试 add_credits 系列函数"""
    
    @patch('services.db.users.supabase')
    def test_add_permanent_credits(self, mock_supabase):
        """添加永久积分"""
        from services.db.users import add_credits_permanent
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"balance_permanent": 150}
        )
        
        result = add_credits_permanent("user_001", 50, "Market sale")
        
        assert result is not None
    
    @patch('services.db.users.supabase')
    def test_add_monthly_credits(self, mock_supabase):
        """添加月度积分"""
        from services.db.users import add_credits_monthly
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"balance_monthly": 200}
        )
        
        result = add_credits_monthly("user_001", 100, "Bonus")
        
        assert result is not None


class TestGetCreditHistory:
    """测试 get_credit_history"""
    
    @patch('services.db.users.supabase')
    def test_returns_credit_transactions(self, mock_supabase):
        """返回积分交易历史"""
        from services.db.users import get_credit_history
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": 1, "amount": -5, "type": "generation"},
            {"id": 2, "amount": 100, "type": "sub_grant"}
        ]
        mock_result.count = 2
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        result = get_credit_history("user_001", limit=10)
        
        assert len(result["items"]) == 2
        assert result["total"] == 2


class TestSearchUsers:
    """测试 search_users"""
    
    @patch('services.db.users.supabase')
    def test_searches_by_email(self, mock_supabase):
        """按邮箱搜索用户"""
        from services.db.users import search_users
        
        mock_supabase.table.return_value.select.return_value.or_.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_001", "email": "test@example.com"}]
        )
        
        result = search_users("test@")
        
        assert len(result) == 1


class TestGetUsersByTier:
    """测试 get_users_by_tier"""
    
    @patch('services.db.users.supabase')
    def test_filters_by_tier(self, mock_supabase):
        """按等级筛选用户"""
        from services.db.users import get_users_by_tier
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "user_001"},
                {"id": "user_002"}
            ]
        )
        
        result = get_users_by_tier("pro")
        
        assert len(result) == 2
        assert "user_001" in result


class TestGetUserDiscount:
    """测试 get_user_discount"""
    
    @patch('services.db.users.supabase')
    def test_returns_discount_when_exists(self, mock_supabase):
        """返回用户折扣"""
        from services.db.users import get_user_discount
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"discount_percent": 20, "valid_until": "2026-12-31"}]
        )
        
        result = get_user_discount("user_001")
        
        assert result["discount_percent"] == 20
    
    @patch('services.db.users.supabase')
    def test_returns_none_when_no_discount(self, mock_supabase):
        """无折扣时返回 None"""
        from services.db.users import get_user_discount
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        result = get_user_discount("user_001")
        
        assert result is None


class TestCreateUserDiscount:
    """测试 create_user_discount"""
    
    @patch('services.db.users.supabase')
    def test_creates_discount(self, mock_supabase):
        """创建用户折扣"""
        from services.db.users import create_user_discount
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"user_id": "user_001", "discount_percent": 15}]
        )
        
        # 正确的参数签名: (user_id, discount_percent, valid_days, target_plan=None)
        result = create_user_discount("user_001", 15, 30, "pro")
        
        assert result is not None


class TestLogCreditTransaction:
    """测试 log_credit_transaction"""
    
    @patch('services.db.users.supabase')
    def test_logs_transaction(self, mock_supabase):
        """记录积分交易"""
        from services.db.users import log_credit_transaction
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        
        # 不抛异常即为成功
        log_credit_transaction("user_001", 50, "permanent", "signup_bonus", "Welcome")
        
        mock_supabase.table.return_value.insert.assert_called_once()
    
    @patch('services.db.users.supabase')
    def test_handles_error_gracefully(self, mock_supabase):
        """错误时不抛异常"""
        from services.db.users import log_credit_transaction
        
        mock_supabase.table.return_value.insert.side_effect = Exception("DB error")
        
        # 不应抛出异常
        log_credit_transaction("user_001", 50, "permanent", "signup_bonus", "Welcome")


class TestCheckAndResetMonthlyCreditsIfNeeded:
    """测试 check_and_reset_monthly_credits_if_needed"""
    
    @patch('services.db.users.refresh_monthly_credits')
    @patch('services.db.users.get_user_profile')
    @patch('services.db.users.supabase')
    def test_resets_when_30_days_passed(self, mock_supabase, mock_get_profile, mock_refresh):
        """30 天后重置"""
        from services.db.users import check_and_reset_monthly_credits_if_needed
        from datetime import timedelta
        
        # 31 天前的重置时间
        old_reset = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "starter",
            "credits_reset_at": old_reset
        }
        
        check_and_reset_monthly_credits_if_needed("user_001")
        
        mock_refresh.assert_called_once_with("user_001", "starter")
    
    @patch('services.db.users.refresh_monthly_credits')
    @patch('services.db.users.get_user_profile')
    @patch('services.db.users.supabase')
    def test_no_reset_when_less_than_30_days(self, mock_supabase, mock_get_profile, mock_refresh):
        """不足 30 天不重置"""
        from services.db.users import check_and_reset_monthly_credits_if_needed
        from datetime import timedelta
        
        # 15 天前的重置时间
        recent_reset = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "pro",
            "credits_reset_at": recent_reset
        }
        
        check_and_reset_monthly_credits_if_needed("user_001")
        
        mock_refresh.assert_not_called()
    
    @patch('services.db.users.refresh_monthly_credits')
    @patch('services.db.users.get_user_profile')
    @patch('services.db.users.supabase')
    def test_skips_free_users(self, mock_supabase, mock_get_profile, mock_refresh):
        """Free 用户跳过"""
        from services.db.users import check_and_reset_monthly_credits_if_needed
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "tier": "free",
        }
        
        check_and_reset_monthly_credits_if_needed("user_001")
        
        mock_refresh.assert_not_called()
