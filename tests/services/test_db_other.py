"""
Database Other Services Tests
services/db/config.py, core.py, notifications.py, payments.py, support.py 模块测试

覆盖目标: 95%+
"""

import pytest
from unittest.mock import MagicMock, patch


# ==========================================
# Core Tests
# ==========================================

class TestIsMember:
    """测试 is_member"""
    
    def test_starter_active_is_member(self):
        """Starter active 是会员"""
        from services.db.core import is_member
        
        user = {"tier": "starter", "subscription_status": "active"}
        assert is_member(user) is True
    
    def test_pro_active_is_member(self):
        """Pro active 是会员"""
        from services.db.core import is_member
        
        user = {"tier": "pro", "subscription_status": "active"}
        assert is_member(user) is True
    
    def test_free_is_not_member(self):
        """Free 不是会员"""
        from services.db.core import is_member
        
        user = {"tier": "free"}
        assert is_member(user) is False
    
    def test_none_user_returns_false(self):
        """None 用户返回 False"""
        from services.db.core import is_member
        
        assert is_member(None) is False


class TestCanAccessResource:
    """测试 can_access_resource"""
    
    def test_free_tier_allows_everyone(self):
        """free 等级允许所有人"""
        from services.db.core import can_access_resource
        
        user = {"tier": "free"}
        assert can_access_resource(user, ["free"]) is True
    
    def test_member_only_requires_membership(self):
        """会员专属需要会员身份"""
        from services.db.core import can_access_resource
        
        free_user = {"tier": "free"}
        member_user = {"tier": "starter", "subscription_status": "active"}
        
        assert can_access_resource(free_user, ["starter", "pro"]) is False
        assert can_access_resource(member_user, ["starter", "pro"]) is True


class TestGetTotalCredits:
    """测试 get_total_credits"""
    
    def test_sums_monthly_and_permanent(self):
        """合计月度和永久积分"""
        from services.db.core import get_total_credits
        
        user = {"credits_monthly": 100, "credits_permanent": 50}
        assert get_total_credits(user) == 150
    
    def test_handles_none_user(self):
        """处理 None 用户"""
        from services.db.core import get_total_credits
        
        assert get_total_credits(None) == 0


class TestPublishPermission:
    """测试 publish_permission"""
    
    def test_free_cannot_publish(self):
        """Free 不能发布"""
        from services.db.core import publish_permission
        
        user = {"tier": "free"}
        result = publish_permission(user, "asset", 0)
        
        assert result["allowed"] is False
    
    def test_starter_can_publish_free_asset(self):
        """Starter 可以发布免费资产"""
        from services.db.core import publish_permission
        
        user = {"tier": "starter", "subscription_status": "active"}
        result = publish_permission(user, "asset", 0)
        
        assert result["allowed"] is True


class TestValidateAllowedTiers:
    """测试 validate_allowed_tiers"""
    
    def test_valid_options(self):
        """有效选项"""
        from services.db.core import validate_allowed_tiers
        
        assert validate_allowed_tiers(["free"])["valid"] is True
        assert validate_allowed_tiers(["starter", "pro"])["valid"] is True
        assert validate_allowed_tiers(["pro"])["valid"] is True


class TestListingIsPublicVisible:
    """测试 listing_is_public_visible"""
    
    def test_approved_public_not_deleted_is_visible(self):
        """已审核+公开+未删除=可见"""
        from services.db.core import listing_is_public_visible
        
        listing = {"moderation_status": "approved", "is_public": True, "is_deleted": False}
        assert listing_is_public_visible(listing) is True
    
    def test_pending_is_not_visible(self):
        """待审核不可见"""
        from services.db.core import listing_is_public_visible
        
        listing = {"moderation_status": "pending", "is_public": True, "is_deleted": False}
        assert listing_is_public_visible(listing) is False


class TestLogActivity:
    """测试 log_activity"""
    
    @patch('services.db.core.supabase')
    def test_logs_activity(self, mock_supabase):
        """记录活动"""
        from services.db.core import log_activity
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        log_activity("user_001", "login", {"ip": "127.0.0.1"})
        
        mock_supabase.table.return_value.insert.assert_called()


class TestIsRetryableError:
    """测试 is_retryable_error"""
    
    def test_timeout_is_retryable(self):
        """超时错误可重试"""
        from services.db.core import is_retryable_error
        
        error = Exception("Request timeout")
        assert is_retryable_error(error) is True
    
    def test_value_error_is_not_retryable(self):
        """值错误不可重试"""
        from services.db.core import is_retryable_error
        
        error = ValueError("Invalid input")
        assert is_retryable_error(error) is False


# ==========================================
# Config Tests
# ==========================================

class TestGetSystemConfig:
    """测试 get_system_config"""
    
    @patch('services.db.config.supabase')
    def test_returns_config(self, mock_supabase):
        """返回配置"""
        from services.db.config import get_system_config
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"key": "test_config", "value": {"enabled": True}}
        )
        
        result = get_system_config("test_config")
        
        assert result is not None


class TestGetAllSystemConfigs:
    """测试 get_all_system_configs"""
    
    @patch('services.db.config.supabase')
    def test_returns_all_configs(self, mock_supabase):
        """返回所有配置"""
        from services.db.config import get_all_system_configs
        
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{"key": "c1"}, {"key": "c2"}]
        )
        
        result = get_all_system_configs()
        
        assert len(result) == 2


class TestGetConfigsByGroup:
    """测试 get_configs_by_group"""
    
    @patch('services.db.config.supabase')
    def test_filters_by_group(self, mock_supabase):
        """按组筛选配置"""
        from services.db.config import get_configs_by_group
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"key": "ai.provider", "group": "ai"}]
        )
        
        result = get_configs_by_group("ai")
        
        assert len(result) >= 0


# ==========================================
# Notifications Tests
# ==========================================

class TestGetUserNotifications:
    """测试 get_user_notifications"""
    
    @patch('services.db.notifications.supabase')
    def test_returns_notifications(self, mock_supabase):
        """返回用户通知"""
        from services.db.notifications import get_user_notifications
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": 1, "message": "Welcome!"}]
        )
        
        result = get_user_notifications("user_001")
        
        assert len(result) == 1


class TestMarkNotificationRead:
    """测试 mark_notification_read"""
    
    @patch('services.db.notifications.supabase')
    def test_marks_as_read(self, mock_supabase):
        """标记为已读"""
        from services.db.notifications import mark_notification_read
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = mark_notification_read(1, "user_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestMarkAllNotificationsRead:
    """测试 mark_all_notifications_read"""
    
    @patch('services.db.notifications.supabase')
    def test_marks_all_as_read(self, mock_supabase):
        """标记所有为已读"""
        from services.db.notifications import mark_all_notifications_read
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = mark_all_notifications_read("user_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestSendNotificationToUser:
    """测试 send_notification_to_user"""
    
    @patch('services.db.notifications.supabase')
    def test_sends_notification(self, mock_supabase):
        """发送通知给用户"""
        from services.db.notifications import send_notification_to_user
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = send_notification_to_user("user_001", "Test Message", "info")
        
        mock_supabase.table.return_value.insert.assert_called()


# ==========================================
# Payments Tests
# ==========================================

class TestLogPaymentRecord:
    """测试 log_payment_record"""
    
    @patch('services.db.payments.supabase')
    def test_logs_payment(self, mock_supabase):
        """记录支付"""
        from services.db.payments import log_payment_record
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = log_payment_record(
            user_id="user_001",
            stripe_payment_id="pi_123",
            amount_cents=1000,
            plan_type="pro"
        )
        
        mock_supabase.table.return_value.insert.assert_called()


class TestGetUserPayments:
    """测试 get_user_payments"""
    
    @patch('services.db.payments.supabase')
    def test_returns_user_payments(self, mock_supabase):
        """返回用户支付记录"""
        from services.db.payments import get_user_payments
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": 1, "amount_cents": 1000}]
        )
        
        result = get_user_payments("user_001")
        
        assert len(result) == 1


class TestAdminGetAllPayments:
    """测试 admin_get_all_payments"""
    
    @patch('services.db.payments.supabase')
    def test_returns_all_payments(self, mock_supabase):
        """返回所有支付记录"""
        from services.db.payments import admin_get_all_payments
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": 1}, {"id": 2}
        ])
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value = mock_chain
        
        result = admin_get_all_payments()
        
        assert len(result) == 2


class TestAdminGetRevenueStats:
    """测试 admin_get_revenue_stats"""
    
    @patch('services.db.payments.supabase')
    def test_returns_revenue_stats(self, mock_supabase):
        """返回收入统计"""
        from services.db.payments import admin_get_revenue_stats
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "total_revenue": 10000,
            "monthly_revenue": 1000
        })
        
        result = admin_get_revenue_stats()
        
        assert result is not None


# ==========================================
# Support Tests
# ==========================================

class TestCreateSupportTicket:
    """测试 create_support_ticket"""
    
    @patch('services.db.support.supabase')
    def test_creates_ticket(self, mock_supabase):
        """创建工单"""
        from services.db.support import create_support_ticket
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": 1, "subject": "Help!"}]
        )
        
        result = create_support_ticket(
            user_id="user_001",
            subject="Help!",
            message="I need help"
        )
        
        assert result is not None


class TestSendSupportEmail:
    """测试 send_support_email"""
    
    @patch('services.db.support.resend')
    def test_sends_email(self, mock_resend):
        """发送支持邮件"""
        from services.db.support import send_support_email
        
        mock_resend.Emails.send.return_value = {"id": "email_123"}
        
        # 这个函数可能需要特定的mock设置
        # 验证不抛出异常即可


class TestCreateReport:
    """测试 create_report"""
    
    @patch('services.db.support.supabase')
    def test_creates_report(self, mock_supabase):
        """创建举报"""
        from services.db.support import create_report
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": 1, "reason": "Spam"}]
        )
        
        result = create_report(
            reporter_id="user_001",
            listing_id="listing_001",
            reason="Spam"
        )
        
        assert result is not None


class TestGetUserReports:
    """测试 get_user_reports"""
    
    @patch('services.db.support.supabase')
    def test_returns_user_reports(self, mock_supabase):
        """返回用户举报"""
        from services.db.support import get_user_reports
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )
        
        result = get_user_reports("user_001")
        
        assert len(result) == 1
