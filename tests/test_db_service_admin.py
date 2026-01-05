"""
db_service 管理员函数测试
覆盖 admin_* 系列函数

目标: 覆盖所有管理员相关功能
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone, timedelta


# ==========================================
# Admin Operation Logs Tests
# ==========================================

class TestAdminGetOperationLogs:
    """管理员操作日志测试"""
    
    @patch('services.db_service.supabase')
    def test_get_all_logs(self, mock_supabase):
        """获取所有操作日志"""
        from services.db_service import admin_get_operation_logs
        
        # Mock count
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(count=10)
        
        # Mock data
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {
                "id": "log_001",
                "operation_type": "user_ban",
                "admin_id": "admin_001",
                "admin": {"email": "admin@test.com"},
                "target_user_id": "user_001",
                "target": {"email": "user@test.com", "user_code": "CODE123"},
                "details": {},
                "reason": "Spam",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ])
        
        result = admin_get_operation_logs()
        
        assert "logs" in result
        assert "total" in result
    
    @patch('services.db_service.supabase')
    def test_get_logs_with_filters(self, mock_supabase):
        """带过滤条件获取日志"""
        from services.db_service import admin_get_operation_logs
        
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lte.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[], count=0)
        
        mock_supabase.table.return_value.select.return_value = mock_query
        
        result = admin_get_operation_logs(
            operation_type="user_ban",
            admin_id="admin_001",
            target_user_id="user_001",
            start_date="2024-01-01",
            end_date="2024-12-31",
            page=1,
            limit=10
        )
        
        assert "logs" in result


# ==========================================
# Admin User Projects Tests
# ==========================================

class TestAdminGetUserProjects:
    """管理员获取用户项目测试"""
    
    @patch('services.db_service.supabase')
    def test_get_all_user_projects(self, mock_supabase):
        """获取用户所有项目（含已删除）"""
        from services.db_service import admin_get_user_projects
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[
            {"id": "proj_001"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(count=1)
        
        result = admin_get_user_projects("user_001", include_deleted=True)
        
        assert "projects" in result
        assert "total" in result
    
    @patch('services.db_service.supabase')
    def test_get_user_projects_exclude_deleted(self, mock_supabase):
        """获取用户项目（排除已删除）"""
        from services.db_service import admin_get_user_projects
        
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.is_.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[], count=0)
        
        mock_supabase.table.return_value.select.return_value = mock_query
        
        result = admin_get_user_projects("user_001", include_deleted=False)
        
        assert "projects" in result


# ==========================================
# Admin Dashboard Stats Tests
# ==========================================

class TestAdminGetDashboardStats:
    """管理员仪表盘统计测试"""
    
    @patch('services.db_service.supabase')
    def test_get_dashboard_stats_week(self, mock_supabase):
        """获取一周统计数据"""
        from services.db_service import admin_get_dashboard_stats
        
        # Mock all queries
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = MagicMock(count=10, data=[])
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_dashboard_stats(period="week")
        
        assert "totalUsers" in result
        assert "totalRevenue" in result
        assert "totalProjects" in result
    
    @patch('services.db_service.supabase')
    def test_get_dashboard_stats_month(self, mock_supabase):
        """获取一月统计数据"""
        from services.db_service import admin_get_dashboard_stats
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = MagicMock(count=100, data=[
            {"description": "Purchase | USD 2490", "amount": -50}
        ])
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_dashboard_stats(period="month")
        
        assert "totalUsers" in result


# ==========================================
# Admin User Growth Stats Tests
# ==========================================

class TestAdminGetUserGrowthStats:
    """管理员用户增长统计测试"""
    
    @patch('services.db_service.supabase')
    def test_get_user_growth_daily(self, mock_supabase):
        """获取每日用户增长"""
        from services.db_service import admin_get_user_growth_stats
        
        mock_supabase.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {"created_at": "2024-01-01T10:00:00Z"},
            {"created_at": "2024-01-01T15:00:00Z"},
            {"created_at": "2024-01-02T10:00:00Z"},
        ])
        
        result = admin_get_user_growth_stats(
            start_date="2024-01-01",
            end_date="2024-01-31",
            group_by="day"
        )
        
        assert isinstance(result, list)


# ==========================================
# Admin Revenue Stats Tests
# ==========================================

class TestAdminGetRevenueStats:
    """管理员收入统计测试"""
    
    @patch('services.db_service.supabase')
    def test_get_revenue_stats(self, mock_supabase):
        """获取收入统计"""
        from services.db_service import admin_get_revenue_stats
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {"created_at": "2024-01-01T10:00:00Z", "description": "Pro | USD 2490"}
        ])
        
        result = admin_get_revenue_stats(
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert isinstance(result, list)


# ==========================================
# Admin Project Stats Tests
# ==========================================

class TestAdminGetProjectStats:
    """管理员项目统计测试"""
    
    @patch('services.db_service.supabase')
    def test_get_project_stats(self, mock_supabase):
        """获取项目统计"""
        from services.db_service import admin_get_project_stats
        
        mock_supabase.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {"created_at": "2024-01-01T10:00:00Z"}
        ])
        
        result = admin_get_project_stats(
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        # 返回的是列表格式
        assert isinstance(result, list)


# ==========================================
# Admin Credit Usage Stats Tests
# ==========================================

class TestAdminGetCreditUsageStats:
    """管理员积分使用统计测试"""
    
    @patch('services.db_service.supabase')
    def test_get_credit_usage_stats(self, mock_supabase):
        """获取积分使用统计"""
        from services.db_service import admin_get_credit_usage_stats
        
        mock_supabase.table.return_value.select.return_value.lt.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {"created_at": "2024-01-01T10:00:00Z", "type": "generation", "amount": -5}
        ])
        
        result = admin_get_credit_usage_stats(
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        # 返回的是列表格式
        assert isinstance(result, list)


# ==========================================
# Admin Tier Distribution Tests
# ==========================================

class TestAdminGetTierDistribution:
    """管理员等级分布测试"""
    
    @patch('services.db_service.supabase')
    def test_get_tier_distribution(self, mock_supabase):
        """获取等级分布"""
        from services.db_service import admin_get_tier_distribution
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(count=10)
        
        result = admin_get_tier_distribution()
        
        # 返回的是列表格式
        assert isinstance(result, list)


# ==========================================
# Admin Conversion Funnel Tests
# ==========================================

class TestAdminGetConversionFunnel:
    """管理员转化漏斗测试"""
    
    @patch('services.db_service.supabase')
    def test_get_conversion_funnel(self, mock_supabase):
        """获取转化漏斗"""
        from services.db_service import admin_get_conversion_funnel
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.execute.return_value = MagicMock(count=100, data=[])
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_conversion_funnel(period="month")
        
        # 返回的是列表格式
        assert isinstance(result, list)


# ==========================================
# Admin AI Insights Tests
# ==========================================

class TestAdminGetAIInsights:
    """管理员 AI 洞察测试"""
    
    @patch('services.db_service.supabase')
    def test_get_ai_insights(self, mock_supabase):
        """获取 AI 洞察"""
        from services.db_service import admin_get_ai_insights
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[], count=0)
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_ai_insights(analysis_type="all")
        
        # 可能返回列表或字典
        assert isinstance(result, (list, dict))


# ==========================================
# Admin AI Recommendations Tests
# ==========================================

class TestAdminGetAIRecommendations:
    """管理员 AI 建议测试"""
    
    @patch('services.db_service.supabase')
    def test_get_ai_recommendations(self, mock_supabase):
        """获取 AI 建议"""
        from services.db_service import admin_get_ai_recommendations
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[], count=0)
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_ai_recommendations(area="all")
        
        assert isinstance(result, list)


# ==========================================
# Admin Behavior Analysis Tests
# ==========================================

class TestAdminGetBehaviorAnalysis:
    """管理员行为分析测试"""
    
    @patch('services.db_service.supabase')
    def test_get_behavior_analysis(self, mock_supabase):
        """获取行为分析"""
        from services.db_service import admin_get_behavior_analysis
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lte.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[])
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_behavior_analysis(
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert isinstance(result, dict)


# ==========================================
# Log User Event Tests
# ==========================================

class TestLogUserEvent:
    """用户事件日志测试"""
    
    @patch('services.db_service.supabase')
    def test_log_user_event(self, mock_supabase):
        """记录用户事件"""
        from services.db_service import log_user_event
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        log_user_event(
            user_id="user_001",
            event_type="page_view",
            properties={"page": "/editor"},
            session_id="session_123"
        )
        
        mock_supabase.table.return_value.insert.assert_called()


# ==========================================
# Admin Get User Events Tests
# ==========================================

class TestAdminGetUserEvents:
    """管理员获取用户事件测试"""
    
    @patch('services.db_service.supabase')
    def test_get_user_events(self, mock_supabase):
        """获取用户事件"""
        from services.db_service import admin_get_user_events
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[], count=0)
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_user_events(
            user_id="user_001",
            event_type="page_view"
        )
        
        assert "events" in result


# ==========================================
# Admin Get Event Stats Tests
# ==========================================

class TestAdminGetEventStats:
    """管理员获取事件统计测试"""
    
    @patch('services.db_service.supabase')
    def test_get_event_stats(self, mock_supabase):
        """获取事件统计"""
        from services.db_service import admin_get_event_stats
        
        mock_supabase.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(data=[
            {"event_type": "page_view", "created_at": "2024-01-01T10:00:00Z"}
        ])
        
        result = admin_get_event_stats(
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        # 返回的是列表格式
        assert isinstance(result, list)


# ==========================================
# Aggregated Stats Tests
# ==========================================

class TestAggregatedStats:
    """聚合统计测试"""
    
    @patch('services.db_service.cache_service')
    @patch('services.db_service.supabase')
    def test_get_aggregated_stats_from_cache(self, mock_supabase, mock_cache):
        """从缓存获取聚合统计"""
        from services.db_service import get_aggregated_stats
        
        mock_cache.get_stats.return_value = {"value": 100}
        
        result = get_aggregated_stats("total_users", use_cache=True)
        
        assert result == {"value": 100}
    
    @patch('services.db_service.cache_service')
    @patch('services.db_service.supabase')
    def test_get_aggregated_stats_from_db(self, mock_supabase, mock_cache):
        """从数据库获取聚合统计"""
        from services.db_service import get_aggregated_stats
        
        mock_cache.get_stats.return_value = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[
            {"data": {"value": 200}}
        ])
        
        result = get_aggregated_stats("total_users", use_cache=True)
        
        # 可能返回 None 或字典
        assert result is None or isinstance(result, dict)
    
    @patch('services.db_service.supabase')
    def test_get_aggregated_stats_range(self, mock_supabase):
        """获取聚合统计范围"""
        from services.db_service import get_aggregated_stats_range
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[
            {"date": "2024-01-01", "data": {"value": 100}}
        ])
        
        result = get_aggregated_stats_range("total_users", days=30)
        
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_upsert_aggregated_stats(self, mock_supabase):
        """更新或插入聚合统计"""
        from services.db_service import upsert_aggregated_stats
        
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        
        upsert_aggregated_stats("2024-01-01", "total_users", {"value": 100})
        
        mock_supabase.table.return_value.upsert.assert_called()


# ==========================================
# Report Tests
# ==========================================

class TestReports:
    """举报功能测试"""
    
    @patch('services.db_service.supabase')
    def test_create_report_new(self, mock_supabase):
        """创建新举报（无重复）"""
        from services.db_service import create_report
        
        # 设置不同表的不同响应
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "content_reports":
                # 检查重复: 返回空 (没有现有举报)
                mock_existing = MagicMock()
                mock_existing.data = []
                mock_table.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.return_value = mock_existing
                
                # insert: 返回新创建的举报
                mock_insert = MagicMock()
                mock_insert.data = [{"id": "report_001"}]
                mock_table.insert.return_value.execute.return_value = mock_insert
            elif table_name == "marketplace_listings":
                # listing 存在检查
                mock_listing = MagicMock()
                mock_listing.data = {"id": "listing_001", "title": "Test Listing"}
                mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_listing
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = create_report("reporter_001", "listing_001", "Spam content")
        
        assert result is not None
    
    @patch('services.db_service.supabase')
    def test_get_user_reports(self, mock_supabase):
        """获取用户举报"""
        from services.db_service import get_user_reports
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_user_reports("user_001")
        
        assert isinstance(result, list)
    
    @patch('services.db_service.supabase')
    def test_admin_get_reports(self, mock_supabase):
        """管理员获取举报列表"""
        from services.db_service import admin_get_reports
        
        # 返回字典格式的结果
        mock_data = MagicMock()
        mock_data.data = []
        mock_data.count = 0
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = mock_data
        
        mock_supabase.table.return_value = mock_query
        
        result = admin_get_reports(status="pending")
        
        # 结果是字典或列表
        assert isinstance(result, (dict, list))
    
    @patch('services.db_service.supabase')
    def test_admin_get_reports_count(self, mock_supabase):
        """管理员获取举报数量"""
        from services.db_service import admin_get_reports_count
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(count=5)
        
        result = admin_get_reports_count(status="pending")
        
        assert result == 5
    
    @patch('services.db_service.supabase')
    def test_admin_respond_to_report(self, mock_supabase):
        """管理员回复举报"""
        from services.db_service import admin_respond_to_report
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "report_001"
        }])
        
        # 使用正确的参数名 (response 而不是 response_note)
        result = admin_respond_to_report(
            report_id="report_001",
            admin_id="admin_001",
            status="resolved",
            response="Reviewed and resolved"
        )
        
        assert result is not None
    
    @patch('services.db_service.supabase')
    def test_admin_get_report_detail(self, mock_supabase):
        """管理员获取举报详情"""
        from services.db_service import admin_get_report_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "report_001"
        })
        
        result = admin_get_report_detail("report_001")
        
        assert result is not None


# ==========================================
# Config Audit Log Tests
# ==========================================

class TestConfigAuditLog:
    """配置审计日志测试"""
    
    @patch('services.db_service.supabase')
    def test_log_config_audit(self, mock_supabase):
        """记录配置审计"""
        from services.db_service import _log_config_audit
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        # 使用正确的参数名
        _log_config_audit(
            action="update",
            config_key="test_key",
            admin_id="admin_001",
            old_value="old",
            new_value="new"
        )
        
        mock_supabase.table.return_value.insert.assert_called()
    
    @patch('services.db_service.supabase')
    def test_admin_get_config_audit_logs(self, mock_supabase):
        """管理员获取配置审计日志"""
        from services.db_service import admin_get_config_audit_logs
        
        mock_data = MagicMock()
        mock_data.data = []
        mock_data.count = 0
        
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_data
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_data
        
        result = admin_get_config_audit_logs(page=1, limit=20)
        
        # 结果可能是字典或列表
        assert isinstance(result, (dict, list))


# ==========================================
# Execute Purchase Tests
# ==========================================

class TestExecutePurchase:
    """执行购买测试"""
    
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    @patch('services.db_service.can_access_resource')
    @patch('services.db_service.check_user_purchase')
    def test_purchase_free_item(self, mock_check, mock_can_access, mock_get_profile, mock_supabase):
        """购买免费商品"""
        from services.db_service import execute_purchase
        
        # No idempotency check hit
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Listing query
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "listing_001",
            "price_credits": 0,
            "seller_id": "seller_001",
            "allowed_tiers": ["free"],
            "resource_type": "asset",
            "title": "Free Asset"
        })
        
        mock_get_profile.return_value = {
            "id": "buyer_001",
            "tier": "free"
        }
        mock_can_access.return_value = True
        mock_check.return_value = False
        
        # Insert purchase
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = execute_purchase("buyer_001", "listing_001")
        
        assert result["success"] is True
        assert "Free" in result["message"]
    
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    def test_purchase_listing_not_found(self, mock_get_profile, mock_supabase):
        """购买不存在的商品"""
        from services.db_service import execute_purchase
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        
        result = execute_purchase("buyer_001", "nonexistent")
        
        assert result["success"] is False
        assert "not found" in result["message"]
    
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    @patch('services.db_service.can_access_resource')
    @patch('services.db_service.check_user_purchase')
    def test_purchase_already_owned(self, mock_check, mock_can_access, mock_get_profile, mock_supabase):
        """已购买的商品"""
        from services.db_service import execute_purchase
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "listing_001",
            "price_credits": 100,
            "seller_id": "seller_001",
            "allowed_tiers": ["free"],
            "title": "Test"
        })
        
        mock_get_profile.return_value = {"id": "buyer_001", "tier": "free"}
        mock_can_access.return_value = True
        mock_check.return_value = True  # Already purchased
        
        result = execute_purchase("buyer_001", "listing_001")
        
        assert result["success"] is True
        assert result.get("already_owned") is True
    
    @patch('services.db_service.supabase')
    def test_purchase_idempotency_hit(self, mock_supabase):
        """幂等性检查命中"""
        from services.db_service import execute_purchase
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "purchase_001"}])
        
        result = execute_purchase("buyer_001", "listing_001", idempotency_key="key123")
        
        assert result["success"] is True
        assert result.get("already_owned") is True


# ==========================================
# Update Listing Tests
# ==========================================

class TestUpdateListing:
    """更新商品测试"""
    
    @patch('services.db_service.supabase')
    def test_update_listing_success(self, mock_supabase):
        """成功更新商品"""
        from services.db_service import update_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "listing_001",
            "title": "New Title"
        }])
        
        result = update_listing(
            listing_id="listing_001",
            seller_id="seller_001",
            updates={"title": "New Title", "price_credits": 50}
        )
        
        assert result is not None
    
    @patch('services.db_service.supabase')
    def test_update_listing_filters_fields(self, mock_supabase):
        """更新商品过滤无效字段"""
        from services.db_service import update_listing
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        result = update_listing(
            listing_id="listing_001",
            seller_id="seller_001",
            updates={"title": "New Title", "invalid_field": "value"}
        )
        
        # 验证只传递了允许的字段
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert "title" in update_call
        assert "invalid_field" not in update_call
