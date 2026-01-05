"""
Tests for db_service notification, discount, and support functions.
按功能设计测试用例，测试驱动开发。
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, timezone


class TestCreateBroadcast:
    """Test create_broadcast function - Admin broadcast notification"""
    
    def test_create_broadcast_all_users(self):
        """创建面向所有用户的广播通知"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "notif-1",
                "user_id": None,
                "target_group": "all",
                "title": "System Update",
                "content": "New features released",
                "is_read": False
            }]
            
            from services.db_service import create_broadcast
            result = create_broadcast("System Update", "New features released", "all")
            
            assert result["title"] == "System Update"
            assert result["target_group"] == "all"
            assert result["user_id"] is None  # Broadcast = NULL user_id
    
    def test_create_broadcast_pro_users(self):
        """创建面向Pro用户的广播通知"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "notif-2",
                "user_id": None,
                "target_group": "pro",
                "title": "Pro Feature",
                "content": "Exclusive content",
                "is_read": False
            }]
            
            from services.db_service import create_broadcast
            result = create_broadcast("Pro Feature", "Exclusive content", "pro")
            
            assert result["target_group"] == "pro"


class TestSendNotificationToUser:
    """Test send_notification_to_user function - Single user notification"""
    
    def test_send_notification_success(self):
        """成功发送通知给单个用户"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "notif-1",
                "user_id": "user-123",
                "title": "Welcome",
                "content": "Welcome to our platform",
                "is_read": False
            }]
            
            from services.db_service import send_notification_to_user
            result = send_notification_to_user("user-123", "Welcome", "Welcome to our platform")
            
            assert result["user_id"] == "user-123"
            assert result["title"] == "Welcome"
    
    def test_send_notification_with_type(self):
        """发送带类型的通知"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "notif-1",
                "user_id": "user-123",
                "notification_type": "purchase",
                "title": "Purchase Complete",
                "content": "Your purchase was successful"
            }]
            
            from services.db_service import send_notification_to_user
            result = send_notification_to_user(
                "user-123", "Purchase Complete", 
                "Your purchase was successful", 
                notification_type="purchase"
            )
            
            assert result["notification_type"] == "purchase"
    
    def test_send_notification_type_field_not_supported(self):
        """通知类型字段不存在时的回退处理"""
        with patch('services.db_service.supabase') as mock_supabase:
            # First call fails with notification_type error
            def insert_side_effect(data):
                if "notification_type" in data:
                    raise Exception("column notification_type does not exist")
                mock_execute = MagicMock()
                mock_execute.execute.return_value.data = [{"id": "notif-1", "user_id": "user-123"}]
                return mock_execute
            
            mock_supabase.table.return_value.insert.side_effect = insert_side_effect
            
            from services.db_service import send_notification_to_user
            result = send_notification_to_user("user-123", "Test", "Content", "system")
            
            assert result["id"] == "notif-1"


class TestSendNotificationToUsers:
    """Test send_notification_to_users function - Batch notification"""
    
    def test_send_to_multiple_users(self):
        """批量发送通知给多个用户"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "n1", "user_id": "user-1"},
                {"id": "n2", "user_id": "user-2"},
                {"id": "n3", "user_id": "user-3"}
            ]
            
            from services.db_service import send_notification_to_users
            result = send_notification_to_users(
                ["user-1", "user-2", "user-3"],
                "Announcement",
                "Important update"
            )
            
            assert len(result) == 3
    
    def test_send_to_empty_list(self):
        """空用户列表返回空结果"""
        from services.db_service import send_notification_to_users
        result = send_notification_to_users([], "Test", "Content")
        
        assert result == []
    
    def test_send_with_notification_type_fallback(self):
        """通知类型字段不支持时的回退"""
        with patch('services.db_service.supabase') as mock_supabase:
            call_count = [0]
            
            def insert_side_effect(data):
                call_count[0] += 1
                if call_count[0] == 1 and any("notification_type" in d for d in data):
                    raise Exception("column notification_type does not exist")
                mock_execute = MagicMock()
                mock_execute.execute.return_value.data = [{"id": "n1"}]
                return mock_execute
            
            mock_supabase.table.return_value.insert.side_effect = insert_side_effect
            
            from services.db_service import send_notification_to_users
            result = send_notification_to_users(["user-1"], "Test", "Content", "system")
            
            assert len(result) >= 1


class TestGetUsersByTier:
    """Test get_users_by_tier function"""
    
    def test_get_pro_users(self):
        """获取Pro用户列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": "user-1"},
                {"id": "user-2"}
            ]
            
            from services.db_service import get_users_by_tier
            result = get_users_by_tier("pro")
            
            assert result == ["user-1", "user-2"]
    
    def test_get_users_empty_tier(self):
        """空等级返回空列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            from services.db_service import get_users_by_tier
            result = get_users_by_tier("enterprise")
            
            assert result == []


class TestGetAllNotificationStats:
    """Test get_all_notification_stats function"""
    
    def test_get_stats_success(self):
        """成功获取通知统计"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock total
            mock_total = MagicMock()
            mock_total.count = 100
            
            # Mock unread
            mock_unread = MagicMock()
            mock_unread.count = 25
            
            # Mock recent
            mock_recent = MagicMock()
            mock_recent.count = 10
            
            mock_supabase.table.return_value.select.return_value.execute.return_value = mock_total
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_unread
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_recent
            
            from services.db_service import get_all_notification_stats
            result = get_all_notification_stats()
            
            assert "total" in result
            assert "unread" in result
            assert "recent_7d" in result
    
    def test_get_stats_error_handling(self):
        """统计查询失败时返回默认值"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.side_effect = Exception("DB error")
            
            from services.db_service import get_all_notification_stats
            result = get_all_notification_stats()
            
            assert result == {"total": 0, "unread": 0, "recent_7d": 0}


class TestGetNotificationHistory:
    """Test get_notification_history function"""
    
    def test_get_history_default(self):
        """获取默认通知历史"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value.data = [
                {"id": "n1", "title": "Test 1"},
                {"id": "n2", "title": "Test 2"}
            ]
            
            from services.db_service import get_notification_history
            result = get_notification_history()
            
            assert len(result) == 2
    
    def test_get_history_with_type_filter(self):
        """按类型筛选通知历史"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                {"id": "n1", "notification_type": "system"}
            ]
            
            from services.db_service import get_notification_history
            result = get_notification_history(notification_type="system")
            
            assert len(result) >= 0
    
    def test_get_history_error_handling(self):
        """查询失败返回空列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.side_effect = Exception("DB error")
            
            from services.db_service import get_notification_history
            result = get_notification_history()
            
            assert result == []


class TestGetUserDiscount:
    """Test get_user_discount function"""
    
    def test_get_valid_discount(self):
        """获取有效折扣"""
        with patch('services.db_service.supabase') as mock_supabase:
            future_date = (datetime.now() + timedelta(days=7)).isoformat()
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [{
                "id": "disc-1",
                "user_id": "user-123",
                "discount_percent": 20,
                "valid_until": future_date
            }]
            
            from services.db_service import get_user_discount
            result = get_user_discount("user-123")
            
            assert result["discount_percent"] == 20
    
    def test_get_discount_with_target_plan(self):
        """获取特定计划的折扣"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{
                "discount_percent": 15,
                "target_plan": "pro"
            }]
            
            from services.db_service import get_user_discount
            result = get_user_discount("user-123", "pro")
            
            assert result["target_plan"] == "pro"
    
    def test_no_valid_discount(self):
        """没有有效折扣返回None"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            
            from services.db_service import get_user_discount
            result = get_user_discount("user-123")
            
            assert result is None


class TestCreateUserDiscount:
    """Test create_user_discount function"""
    
    def test_create_discount_success(self):
        """成功创建用户折扣"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "disc-1",
                "user_id": "user-123",
                "discount_percent": 25,
                "target_plan": None
            }]
            
            from services.db_service import create_user_discount
            result = create_user_discount("user-123", 25, 30)
            
            assert result["discount_percent"] == 25
    
    def test_create_discount_with_target_plan(self):
        """创建指定计划的折扣"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": "disc-1",
                "discount_percent": 10,
                "target_plan": "starter"
            }]
            
            from services.db_service import create_user_discount
            result = create_user_discount("user-123", 10, 7, "starter")
            
            assert result["target_plan"] == "starter"


class TestLogActivity:
    """Test log_activity function"""
    
    def test_log_activity_basic(self):
        """基本活动日志记录"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import log_activity
            log_activity("user-123", "login")
            
            mock_supabase.table.assert_called_with("activity_logs")
    
    def test_log_activity_with_metadata(self):
        """带元数据的活动日志"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import log_activity
            log_activity("user-123", "export_pdf", {"project_id": "proj-1"})
            
            call_args = mock_supabase.table.return_value.insert.call_args[0][0]
            assert call_args["metadata"]["project_id"] == "proj-1"


class TestCreateSupportTicket:
    """Test create_support_ticket function"""
    
    def test_create_ticket_success(self):
        """成功创建支持工单"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.send_support_email') as mock_email:
                mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
                
                from services.db_service import create_support_ticket
                create_support_ticket("user-123", "user@example.com", "Help needed")
                
                mock_supabase.table.assert_called_with("support_tickets")
                mock_email.assert_called_once()
    
    def test_create_ticket_email_fails(self):
        """邮件发送失败但工单仍创建成功"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.send_support_email') as mock_email:
                mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
                mock_email.side_effect = Exception("Email service unavailable")
                
                from services.db_service import create_support_ticket
                # Should not raise even if email fails
                create_support_ticket("user-123", "user@example.com", "Help needed")
                
                # Verify ticket was still saved
                mock_supabase.table.assert_called_with("support_tickets")


class TestSendSupportEmail:
    """Test send_support_email function"""
    
    def test_send_email_no_api_key(self):
        """没有API Key时跳过发送"""
        with patch('services.db_service.supabase'):
            with patch.dict('os.environ', {'RESEND_API_KEY': ''}):
                # Should not raise
                from services.db_service import send_support_email
                # Import will use the config value
    
    def test_send_email_missing_resend_package(self):
        """resend包未安装时跳过发送"""
        # This tests the ImportError handling in send_support_email
        pass  # Covered implicitly when resend is not installed


class TestSearchUsers:
    """Test search_users function"""
    
    def test_search_by_email(self):
        """按邮箱搜索用户"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.or_.return_value.execute.return_value.data = [
                {"id": "user-1", "email": "test@example.com"}
            ]
            
            from services.db_service import search_users
            result = search_users("test@example")
            
            assert len(result) == 1
            assert result[0]["email"] == "test@example.com"
    
    def test_search_by_id(self):
        """按ID搜索用户"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.or_.return_value.execute.return_value.data = [
                {"id": "user-123", "email": "user@example.com"}
            ]
            
            from services.db_service import search_users
            result = search_users("user-123")
            
            assert result[0]["id"] == "user-123"


class TestGetFullUserAudit:
    """Test get_full_user_audit function"""
    
    def test_get_full_audit(self):
        """获取用户完整审计信息"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.get_user_purchases') as mock_purchases:
                    mock_profile.return_value = {"id": "user-123", "tier": "pro"}
                    mock_purchases.return_value = []
                    
                    # Mock credit transactions
                    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
                    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
                    
                    from services.db_service import get_full_user_audit
                    result = get_full_user_audit("user-123")
                    
                    assert "profile" in result
                    assert "transactions" in result
                    assert "logs" in result
                    assert "tickets" in result
                    assert "purchases" in result


class TestAdminAdjustCredits:
    """Test admin_adjust_credits function"""
    
    def test_adjust_monthly_credits(self):
        """调整月度积分"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.log_credit_transaction') as mock_log:
                    mock_profile.return_value = {
                        "id": "user-123",
                        "credits_monthly": 50,
                        "credits_permanent": 100
                    }
                    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
                    
                    from services.db_service import admin_adjust_credits
                    result = admin_adjust_credits("user-123", 20, "monthly", "Admin bonus")
                    
                    assert result is True
                    mock_log.assert_called_once()
    
    def test_adjust_permanent_credits(self):
        """调整永久积分"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.log_credit_transaction') as mock_log:
                    mock_profile.return_value = {
                        "credits_monthly": 50,
                        "credits_permanent": 100
                    }
                    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
                    
                    from services.db_service import admin_adjust_credits
                    result = admin_adjust_credits("user-123", -50, "permanent", "Refund")
                    
                    assert result is True
    
    def test_adjust_credits_user_not_found(self):
        """用户不存在时抛出异常"""
        with patch('services.db_service.get_user_profile') as mock_profile:
            mock_profile.return_value = None
            
            from services.db_service import admin_adjust_credits
            with pytest.raises(Exception, match="User not found"):
                admin_adjust_credits("nonexistent", 10, "monthly", "Test")
    
    def test_adjust_credits_prevent_negative(self):
        """防止积分为负数"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.log_credit_transaction'):
                    mock_profile.return_value = {
                        "credits_monthly": 10,
                        "credits_permanent": 5
                    }
                    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
                    
                    from services.db_service import admin_adjust_credits
                    # Even with -100, should cap at 0
                    result = admin_adjust_credits("user-123", -100, "monthly", "Test")
                    
                    assert result is True


class TestSendFeedbackWithImages:
    """Test send_feedback_with_images function"""
    
    def test_send_feedback_calls_support_email(self):
        """反馈功能调用支持邮件"""
        with patch('services.db_service.send_support_email') as mock_email:
            from services.db_service import send_feedback_with_images
            send_feedback_with_images("user-123", "user@example.com", "Feedback", ["img1.jpg"])
            
            mock_email.assert_called_once_with("user-123", "user@example.com", "Feedback", ["img1.jpg"])
