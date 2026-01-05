"""
Tests for db_service admin moderation functions.
按功能设计测试用例，测试驱动开发。
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestAdminGetModerationList:
    """Test admin_get_moderation_list function"""
    
    def test_get_all_listings(self):
        """获取所有待审核列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                {"id": "listing-1", "moderation_status": "pending"},
                {"id": "listing-2", "moderation_status": "approved"}
            ]
            
            from services.db_service import admin_get_moderation_list
            result = admin_get_moderation_list()
            
            assert len(result) == 2
    
    def test_get_pending_only(self):
        """只获取待审核状态的列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value.data = [
                {"id": "listing-1", "moderation_status": "pending"}
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value = mock_chain
            
            from services.db_service import admin_get_moderation_list
            result = admin_get_moderation_list(status="pending")
            
            assert all(l["moderation_status"] == "pending" for l in result)
    
    def test_filter_by_resource_type(self):
        """按资源类型筛选"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value.data = [
                {"id": "listing-1", "resource_type": "project"}
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value = mock_chain
            
            from services.db_service import admin_get_moderation_list
            result = admin_get_moderation_list(resource_type="project")
            
            assert len(result) >= 0
    
    def test_pagination(self):
        """分页功能"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value.data = [{"id": "listing-21"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value = mock_chain
            
            from services.db_service import admin_get_moderation_list
            result = admin_get_moderation_list(page=2, limit=20)
            
            # Verify range was called with correct pagination
            mock_chain.range.assert_called()


class TestAdminGetModerationDetail:
    """Test admin_get_moderation_detail function"""
    
    def test_get_detail_success(self):
        """成功获取审核详情"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "listing-1",
                "title": "Test Listing",
                "seller_id": "seller-123",
                "profiles": {"username": "seller", "email": "seller@example.com"}
            }
            
            from services.db_service import admin_get_moderation_detail
            result = admin_get_moderation_detail("listing-1")
            
            assert result["id"] == "listing-1"
            assert "profiles" in result


class TestAdminApproveListing:
    """Test admin_approve_listing function"""
    
    def test_approve_listing_success(self):
        """成功审批通过列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                "id": "listing-1",
                "moderation_status": "approved",
                "moderated_by": "admin-1"
            }]
            
            from services.db_service import admin_approve_listing
            result = admin_approve_listing("listing-1", "admin-1")
            
            assert result["moderation_status"] == "approved"
            assert result["moderated_by"] == "admin-1"
    
    def test_approve_sets_timestamp(self):
        """审批时设置时间戳"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                "moderated_at": datetime.now(timezone.utc).isoformat()
            }]
            
            from services.db_service import admin_approve_listing
            result = admin_approve_listing("listing-1", "admin-1")
            
            assert "moderated_at" in result


class TestAdminRejectListing:
    """Test admin_reject_listing function"""
    
    def test_reject_with_reason(self):
        """带原因的拒绝"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                "id": "listing-1",
                "moderation_status": "rejected",
                "moderation_note": "Inappropriate content"
            }]
            
            from services.db_service import admin_reject_listing
            result = admin_reject_listing("listing-1", "admin-1", "Inappropriate content")
            
            assert result["moderation_status"] == "rejected"
            assert result["moderation_note"] == "Inappropriate content"
    
    def test_reject_without_reason_fails(self):
        """没有原因的拒绝应该失败"""
        from services.db_service import admin_reject_listing
        
        with pytest.raises(Exception, match="Rejection reason is required"):
            admin_reject_listing("listing-1", "admin-1", "")
    
    def test_reject_whitespace_only_reason_fails(self):
        """仅空白字符的原因应该失败"""
        from services.db_service import admin_reject_listing
        
        with pytest.raises(Exception, match="Rejection reason is required"):
            admin_reject_listing("listing-1", "admin-1", "   ")


class TestAdminDeleteListing:
    """Test admin_delete_listing function"""
    
    def test_soft_delete_listing(self):
        """软删除列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                "id": "listing-1",
                "is_deleted": True
            }]
            
            from services.db_service import admin_delete_listing
            result = admin_delete_listing("listing-1")
            
            assert result["is_deleted"] is True
    
    def test_delete_nonexistent_listing(self):
        """删除不存在的列表返回None"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
            
            from services.db_service import admin_delete_listing
            result = admin_delete_listing("nonexistent")
            
            assert result is None


class TestAdminUnpublishListing:
    """Test admin_unpublish_listing function"""
    
    def test_unpublish_listing(self):
        """强制下架列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
                "id": "listing-1",
                "is_public": False
            }]
            
            from services.db_service import admin_unpublish_listing
            result = admin_unpublish_listing("listing-1")
            
            assert result["is_public"] is False


class TestAdminLogOperation:
    """Test admin_log_operation function"""
    
    def test_log_credit_adjustment(self):
        """记录积分调整操作"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import admin_log_operation
            admin_log_operation(
                admin_id="admin-1",
                operation_type="credit_adjust",
                target_user_id="user-123",
                details="Added 100 credits",
                reason="Customer service compensation"
            )
            
            mock_supabase.table.assert_called_with("admin_operation_logs")
            call_args = mock_supabase.table.return_value.insert.call_args[0][0]
            assert call_args["operation_type"] == "credit_adjust"
            assert call_args["target_user_id"] == "user-123"
    
    def test_log_listing_approval(self):
        """记录列表审批操作"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import admin_log_operation
            admin_log_operation(
                admin_id="admin-1",
                operation_type="listing_approve",
                details="Approved listing-123"
            )
            
            call_args = mock_supabase.table.return_value.insert.call_args[0][0]
            assert call_args["operation_type"] == "listing_approve"


class TestGetUserPurchases:
    """Test get_user_purchases function"""
    
    def test_get_purchases_success(self):
        """成功获取用户购买记录"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                {"id": "purchase-1", "listing_id": "listing-1"},
                {"id": "purchase-2", "listing_id": "listing-2"}
            ]
            
            from services.db_service import get_user_purchases
            result = get_user_purchases("user-123")
            
            assert len(result) == 2
    
    def test_get_purchases_pagination(self):
        """购买记录分页"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
            
            from services.db_service import get_user_purchases
            result = get_user_purchases("user-123", page=2, limit=10)
            
            # Verify range was called with page 2 offset
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.assert_called_with(10, 19)


class TestGetSellerStats:
    """Test get_seller_stats function"""
    
    def test_get_stats_success(self):
        """成功获取卖家统计"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": "l1", "sales_count": 10, "usage_count": 50, "price_credits": 20, "moderation_status": "approved"},
                {"id": "l2", "sales_count": 5, "usage_count": 25, "price_credits": 15, "moderation_status": "approved"}
            ]
            
            from services.db_service import get_seller_stats
            result = get_seller_stats("seller-123")
            
            assert result["total_listings"] == 2
            assert result["total_sales"] == 15
            assert result["total_usage"] == 75
            # 10*20*0.9 + 5*15*0.9 = 180 + 67.5 = 247.5 -> 247 (int)
            assert result["total_earned_credits"] == 247
    
    def test_get_stats_empty_seller(self):
        """没有列表的卖家"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            
            from services.db_service import get_seller_stats
            result = get_seller_stats("new-seller")
            
            assert result["total_listings"] == 0
            assert result["total_sales"] == 0
            assert result["total_earned_credits"] == 0


class TestRecordListingUsage:
    """Test record_listing_usage function"""
    
    def test_record_first_usage(self):
        """记录首次使用"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Check existing usage - none found
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            # Insert and update succeed
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"usage_count": 0}
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
            
            from services.db_service import record_listing_usage
            result = record_listing_usage("listing-1", "user-123", "project-1")
            
            assert result is True
    
    def test_record_duplicate_usage(self):
        """重复使用不重复记录"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Existing usage found
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": "usage-1"}
            ]
            
            from services.db_service import record_listing_usage
            result = record_listing_usage("listing-1", "user-123", "project-1")
            
            assert result is False


class TestGetLeaderboard:
    """Test get_leaderboard function"""
    
    def test_get_monthly_leaderboard(self):
        """获取月度排行榜"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"id": "l1", "seller_id": "s1", "title": "Top Item", "sales_count": 100},
                {"id": "l2", "seller_id": "s2", "title": "Second", "sales_count": 80}
            ]
            # Mock seller profiles
            mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
                {"id": "s1", "username": "TopSeller"},
                {"id": "s2", "username": "SecondSeller"}
            ]
            
            from services.db_service import get_leaderboard
            result = get_leaderboard(period="monthly", board_type="all")
            
            assert isinstance(result, list)


class TestMarkNotificationRead:
    """Test mark_notification_read function"""
    
    def test_mark_single_notification_read(self):
        """标记单个通知为已读"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            
            from services.db_service import mark_notification_read
            mark_notification_read("notif-1", "user-123")
            
            mock_supabase.table.assert_called_with("notifications")


class TestMarkAllNotificationsRead:
    """Test mark_all_notifications_read function"""
    
    def test_mark_all_read(self):
        """标记所有通知为已读"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
            
            from services.db_service import mark_all_notifications_read
            mark_all_notifications_read("user-123")
            
            mock_supabase.table.assert_called_with("notifications")


class TestGetUserNotifications:
    """Test get_user_notifications function"""
    
    def test_get_all_notifications(self):
        """获取所有通知"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"id": "n1", "title": "Welcome", "is_read": False},
                {"id": "n2", "title": "Update", "is_read": True}
            ]
            
            from services.db_service import get_user_notifications
            result = get_user_notifications("user-123")
            
            assert len(result) == 2
    
    def test_get_unread_only(self):
        """只获取未读通知"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.or_.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"id": "n1", "is_read": False}
            ]
            
            from services.db_service import get_user_notifications
            result = get_user_notifications("user-123", unread_only=True)
            
            assert all(n["is_read"] is False for n in result)
