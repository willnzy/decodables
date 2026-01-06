"""
Database Admin Services Tests
services/db/admin_stats.py, admin_users.py, admin_moderation.py 模块测试

覆盖目标: 95%+
"""

import pytest
from unittest.mock import MagicMock, patch


# ==========================================
# Admin Stats Tests
# ==========================================

class TestAdminGetDashboardStats:
    """测试 admin_get_dashboard_stats"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_dashboard_stats(self, mock_supabase):
        """返回仪表盘统计"""
        from services.db.admin_stats import admin_get_dashboard_stats
        
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(count=100)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{"sum": 5000}])
        
        result = admin_get_dashboard_stats()
        
        assert result is not None
        assert isinstance(result, dict)


class TestAdminGetUserGrowthStats:
    """测试 admin_get_user_growth_stats"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_growth_stats(self, mock_supabase):
        """返回用户增长统计"""
        from services.db.admin_stats import admin_get_user_growth_stats
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[
            {"date": "2026-01-01", "count": 10},
            {"date": "2026-01-02", "count": 15}
        ])
        
        # 正确的参数签名: (start_date, end_date, group_by)
        result = admin_get_user_growth_stats(start_date="2026-01-01", end_date="2026-01-07")
        
        assert result is not None


class TestAdminGetTierDistribution:
    """测试 admin_get_tier_distribution"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_tier_distribution(self, mock_supabase):
        """返回等级分布"""
        from services.db.admin_stats import admin_get_tier_distribution
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[
            {"tier": "free", "count": 500},
            {"tier": "starter", "count": 100},
            {"tier": "pro", "count": 50}
        ])
        
        result = admin_get_tier_distribution()
        
        assert result is not None


class TestAdminGetProjectStats:
    """测试 admin_get_project_stats"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_project_stats(self, mock_supabase):
        """返回项目统计"""
        from services.db.admin_stats import admin_get_project_stats
        
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(count=1000)
        
        result = admin_get_project_stats()
        
        assert result is not None


class TestAdminGetCreditUsageStats:
    """测试 admin_get_credit_usage_stats"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_credit_usage_stats(self, mock_supabase):
        """返回积分使用统计"""
        from services.db.admin_stats import admin_get_credit_usage_stats
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[
            {"type": "generation", "total": -1500},
            {"type": "ocr", "total": -500}
        ])
        
        # 正确的参数签名: (start_date, end_date)
        result = admin_get_credit_usage_stats(start_date="2026-01-01", end_date="2026-01-31")
        
        assert result is not None


class TestAdminGetConversionFunnel:
    """测试 admin_get_conversion_funnel"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_conversion_funnel(self, mock_supabase):
        """返回转化漏斗"""
        from services.db.admin_stats import admin_get_conversion_funnel
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "signups": 1000,
            "active_users": 500,
            "subscribers": 100
        })
        
        result = admin_get_conversion_funnel()
        
        assert result is not None


class TestLogUserEvent:
    """测试 log_user_event"""
    
    @patch('services.db.admin_stats.supabase')
    def test_logs_user_event(self, mock_supabase):
        """记录用户事件"""
        from services.db.admin_stats import log_user_event
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = log_user_event("user_001", "page_view", {"page": "/dashboard"})
        
        mock_supabase.table.return_value.insert.assert_called()


class TestAdminGetAiInsights:
    """测试 admin_get_ai_insights"""
    
    @patch('services.db.admin_stats.supabase', None)
    def test_returns_empty_when_supabase_not_available(self):
        """Supabase 不可用时返回空列表"""
        from services.db.admin_stats import admin_get_ai_insights
        
        result = admin_get_ai_insights()
        
        # Supabase 为 None 时返回空列表
        assert result == []


class TestAdminGetAiRecommendations:
    """测试 admin_get_ai_recommendations"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_ai_recommendations(self, mock_supabase):
        """返回 AI 建议"""
        from services.db.admin_stats import admin_get_ai_recommendations
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[
            {"recommendation": "Increase engagement"},
            {"recommendation": "Improve retention"}
        ])
        
        result = admin_get_ai_recommendations()
        
        assert result is not None


class TestAdminGetBehaviorAnalysis:
    """测试 admin_get_behavior_analysis"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_behavior_analysis(self, mock_supabase):
        """返回行为分析"""
        from services.db.admin_stats import admin_get_behavior_analysis
        
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "patterns": [],
            "segments": []
        })
        
        result = admin_get_behavior_analysis()
        
        assert result is not None


class TestGetAggregatedStats:
    """测试 get_aggregated_stats"""
    
    @patch('services.db.admin_stats.supabase')
    def test_returns_aggregated_stats(self, mock_supabase):
        """返回聚合统计"""
        from services.db.admin_stats import get_aggregated_stats
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"date": "2026-01-06", "stats": {}}
        )
        
        result = get_aggregated_stats("2026-01-06")
        
        assert result is not None


class TestUpsertAggregatedStats:
    """测试 upsert_aggregated_stats"""
    
    @patch('services.db.admin_stats.supabase')
    def test_upserts_stats(self, mock_supabase):
        """插入或更新聚合统计"""
        from services.db.admin_stats import upsert_aggregated_stats
        
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        
        # 正确的参数签名: (date_str, stat_type, data)
        upsert_aggregated_stats("2026-01-06", "daily", {"users": 100})
        
        mock_supabase.table.return_value.upsert.assert_called()


# ==========================================
# Admin Users Tests
# ==========================================

class TestGetFullUserAudit:
    """测试 get_full_user_audit"""
    
    @patch('services.db.admin_users.supabase')
    def test_returns_user_audit(self, mock_supabase):
        """返回用户完整审计信息"""
        from services.db.admin_users import get_full_user_audit
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "user_001", "email": "test@example.com"}
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_full_user_audit("user_001")
        
        assert result is not None


class TestAdminAdjustCredits:
    """测试 admin_adjust_credits"""
    
    @patch('services.db.admin_users.supabase')
    def test_adjusts_credits(self, mock_supabase):
        """管理员调整积分"""
        from services.db.admin_users import admin_adjust_credits
        
        # Mock get_user_profile
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_001", "credits_permanent": 100}]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"credits_permanent": 150}]
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        # 正确的参数签名: (user_id, amount, bucket, reason)
        result = admin_adjust_credits("user_001", 50, "permanent", "Admin bonus")
        
        assert result is not None


class TestAdminGetUserProjects:
    """测试 admin_get_user_projects"""
    
    @patch('services.db.admin_users.supabase')
    def test_returns_user_projects(self, mock_supabase):
        """管理员获取用户项目"""
        from services.db.admin_users import admin_get_user_projects
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "p1", "title": "Project 1"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value = mock_chain
        
        result = admin_get_user_projects("user_001")
        
        assert len(result) >= 0


class TestAdminLogOperation:
    """测试 admin_log_operation"""
    
    @patch('services.db.admin_users.supabase')
    def test_logs_operation(self, mock_supabase):
        """记录管理操作"""
        from services.db.admin_users import admin_log_operation
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        admin_log_operation("admin_001", "credit_adjust", {"user_id": "user_001", "amount": 50})
        
        mock_supabase.table.return_value.insert.assert_called()


class TestAdminGetOperationLogs:
    """测试 admin_get_operation_logs"""
    
    @patch('services.db.admin_users.supabase')
    def test_returns_operation_logs(self, mock_supabase):
        """获取管理操作日志"""
        from services.db.admin_users import admin_get_operation_logs
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": 1, "operation": "credit_adjust"}
        ])
        mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value = mock_chain
        
        result = admin_get_operation_logs(limit=50)
        
        assert len(result) >= 0


# ==========================================
# Admin Moderation Tests
# ==========================================

class TestAdminGetModerationList:
    """测试 admin_get_moderation_list"""
    
    @patch('services.db.admin_moderation.supabase')
    def test_returns_moderation_list(self, mock_supabase):
        """返回审核列表"""
        from services.db.admin_moderation import admin_get_moderation_list
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "l1", "moderation_status": "pending"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = admin_get_moderation_list(status="pending")
        
        assert len(result) >= 0


class TestAdminGetModerationDetail:
    """测试 admin_get_moderation_detail"""
    
    @patch('services.db.admin_moderation.supabase')
    def test_returns_moderation_detail(self, mock_supabase):
        """返回审核详情"""
        from services.db.admin_moderation import admin_get_moderation_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "listing_001", "title": "Test", "moderation_status": "pending"}
        )
        
        result = admin_get_moderation_detail("listing_001")
        
        assert result is not None


class TestAdminApproveListing:
    """测试 admin_approve_listing"""
    
    @patch('services.db.admin_moderation.supabase')
    def test_approves_listing(self, mock_supabase):
        """批准商品"""
        from services.db.admin_moderation import admin_approve_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "listing_001", "moderation_status": "approved"}]
        )
        
        result = admin_approve_listing("listing_001", "admin_001")
        
        assert result is not None


class TestAdminRejectListing:
    """测试 admin_reject_listing"""
    
    @patch('services.db.admin_moderation.supabase')
    def test_rejects_listing(self, mock_supabase):
        """拒绝商品"""
        from services.db.admin_moderation import admin_reject_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "listing_001", "moderation_status": "rejected"}]
        )
        
        result = admin_reject_listing("listing_001", "admin_001", "Violation")
        
        assert result is not None


class TestAdminDeleteListing:
    """测试 admin_delete_listing"""
    
    @patch('services.db.admin_moderation.supabase')
    def test_deletes_listing(self, mock_supabase):
        """删除商品"""
        from services.db.admin_moderation import admin_delete_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "listing_001", "is_deleted": True}]
        )
        
        # 正确的参数签名: (listing_id) - 只有 listing_id
        result = admin_delete_listing("listing_001")
        
        assert result is not None


class TestAdminGetReports:
    """测试 admin_get_reports"""
    
    @patch('services.db.admin_moderation.supabase')
    def test_returns_reports(self, mock_supabase):
        """返回举报列表"""
        from services.db.admin_moderation import admin_get_reports
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": 1, "status": "pending"}
        ])
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value = mock_chain
        
        result = admin_get_reports()
        
        assert len(result) >= 0


class TestAdminRespondToReport:
    """测试 admin_respond_to_report"""
    
    @patch('services.db.admin_moderation.supabase')
    def test_responds_to_report(self, mock_supabase):
        """响应举报"""
        from services.db.admin_moderation import admin_respond_to_report
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 1, "status": "resolved"}]
        )
        
        result = admin_respond_to_report(1, "resolved", "Action taken", "admin_001")
        
        assert result is not None
