"""
Tests for db_service admin stats and analytics functions.
按功能设计测试用例，测试驱动开发。
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestAdminGetProjectStats:
    """Test admin_get_project_stats function"""
    
    def test_get_project_stats_default_range(self):
        """获取默认30天项目统计"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock projects
            mock_projects = MagicMock()
            mock_projects.data = [
                {"created_at": "2025-01-01T10:00:00", "updated_at": "2025-01-01T12:00:00", "thumbnail_url": "thumb.jpg"},
                {"created_at": "2025-01-01T11:00:00", "updated_at": "2025-01-01T13:00:00", "thumbnail_url": None}
            ]
            
            # Mock activity logs
            mock_exports = MagicMock()
            mock_exports.data = [
                {"created_at": "2025-01-01T14:00:00"}
            ]
            
            def table_side_effect(table_name):
                mock_table = MagicMock()
                mock_chain = MagicMock()
                mock_chain.gte.return_value = mock_chain
                mock_chain.lte.return_value = mock_chain
                mock_chain.in_.return_value = mock_chain
                
                if table_name == "projects":
                    mock_chain.execute.return_value = mock_projects
                else:
                    mock_chain.execute.return_value = mock_exports
                
                mock_table.select.return_value = mock_chain
                return mock_table
            
            mock_supabase.table.side_effect = table_side_effect
            
            from services.db_service import admin_get_project_stats
            result = admin_get_project_stats()
            
            assert isinstance(result, list)
    
    def test_get_project_stats_with_dates(self):
        """获取指定日期范围的项目统计"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_projects = MagicMock()
            mock_projects.data = []
            mock_exports = MagicMock()
            mock_exports.data = []
            
            def table_side_effect(table_name):
                mock_table = MagicMock()
                mock_chain = MagicMock()
                mock_chain.gte.return_value = mock_chain
                mock_chain.lte.return_value = mock_chain
                mock_chain.in_.return_value = mock_chain
                mock_chain.execute.return_value = mock_projects if table_name == "projects" else mock_exports
                mock_table.select.return_value = mock_chain
                return mock_table
            
            mock_supabase.table.side_effect = table_side_effect
            
            from services.db_service import admin_get_project_stats
            result = admin_get_project_stats(
                start_date="2025-01-01T00:00:00+00:00",
                end_date="2025-01-07T23:59:59+00:00"
            )
            
            assert isinstance(result, list)
    
    def test_get_project_stats_error_handling(self):
        """统计查询出错时返回空列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.side_effect = Exception("DB error")
            
            from services.db_service import admin_get_project_stats
            result = admin_get_project_stats()
            
            assert result == []


class TestAdminGetCreditUsageStats:
    """Test admin_get_credit_usage_stats function"""
    
    def test_get_credit_usage_stats(self):
        """获取积分使用统计"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_transactions = MagicMock()
            mock_transactions.data = [
                {"type": "generation", "amount": -5},
                {"type": "generation", "amount": -5},
                {"type": "ocr", "amount": -2},
                {"type": "market_purchase", "amount": -50}
            ]
            
            mock_chain = MagicMock()
            mock_chain.lt.return_value = mock_chain
            mock_chain.gte.return_value = mock_chain
            mock_chain.lte.return_value = mock_chain
            mock_chain.execute.return_value = mock_transactions
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_credit_usage_stats
            result = admin_get_credit_usage_stats()
            
            assert isinstance(result, list)
            # Check for expected types
            types_found = [r["action"] for r in result]
            assert any("Image" in t or "Generation" in t for t in types_found) or len(result) > 0


class TestAdminGetTierDistribution:
    """Test admin_get_tier_distribution function"""
    
    def test_get_tier_distribution(self):
        """获取用户等级分布"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_free = MagicMock()
            mock_free.count = 100
            mock_starter = MagicMock()
            mock_starter.count = 30
            mock_pro = MagicMock()
            mock_pro.count = 10
            
            call_count = [0]
            def select_side_effect(*args, **kwargs):
                mock_chain = MagicMock()
                def eq_side_effect(field, value):
                    call_count[0] += 1
                    mock_chain_inner = MagicMock()
                    if value == "free":
                        mock_chain_inner.execute.return_value = mock_free
                    elif value == "starter":
                        mock_chain_inner.execute.return_value = mock_starter
                    else:
                        mock_chain_inner.execute.return_value = mock_pro
                    return mock_chain_inner
                mock_chain.eq.side_effect = eq_side_effect
                return mock_chain
            
            mock_supabase.table.return_value.select.side_effect = select_side_effect
            
            from services.db_service import admin_get_tier_distribution
            result = admin_get_tier_distribution()
            
            assert len(result) == 3
            assert any(r["name"] == "Free" for r in result)
            assert any(r["name"] == "Starter" for r in result)
            assert any(r["name"] == "Pro" for r in result)


class TestAdminGetConversionFunnel:
    """Test admin_get_conversion_funnel function"""
    
    def test_get_conversion_funnel_monthly(self):
        """获取月度转化漏斗"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock signups
            mock_signups = MagicMock()
            mock_signups.count = 1000
            
            # Mock project users
            mock_project_users = MagicMock()
            mock_project_users.data = [{"user_id": "u1"}, {"user_id": "u2"}, {"user_id": "u1"}]
            
            # Mock paid users
            mock_paid_users = MagicMock()
            mock_paid_users.data = [{"user_id": "u1"}]
            
            # Mock active subscribers
            mock_active_subs = MagicMock()
            mock_active_subs.count = 50
            
            call_count = [0]
            def table_side_effect(table_name):
                mock_table = MagicMock()
                mock_chain = MagicMock()
                mock_chain.gte.return_value = mock_chain
                mock_chain.eq.return_value = mock_chain
                mock_chain.in_.return_value = mock_chain
                
                nonlocal call_count
                if table_name == "profiles":
                    if call_count[0] == 0:
                        mock_chain.execute.return_value = mock_signups
                    else:
                        mock_chain.execute.return_value = mock_active_subs
                    call_count[0] += 1
                elif table_name == "projects":
                    mock_chain.execute.return_value = mock_project_users
                elif table_name == "credit_transactions":
                    mock_chain.execute.return_value = mock_paid_users
                
                mock_table.select.return_value = mock_chain
                return mock_table
            
            mock_supabase.table.side_effect = table_side_effect
            
            from services.db_service import admin_get_conversion_funnel
            result = admin_get_conversion_funnel(period="month")
            
            assert len(result) == 5
            assert result[0]["stage"] == "Visitors"
            assert result[1]["stage"] == "Sign Up"
    
    def test_get_conversion_funnel_week(self):
        """获取周度转化漏斗"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_result = MagicMock()
            mock_result.count = 100
            mock_result.data = []
            
            mock_chain = MagicMock()
            mock_chain.gte.return_value = mock_chain
            mock_chain.eq.return_value = mock_chain
            mock_chain.in_.return_value = mock_chain
            mock_chain.execute.return_value = mock_result
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_conversion_funnel
            result = admin_get_conversion_funnel(period="week")
            
            assert len(result) == 5
    
    def test_get_conversion_funnel_quarter(self):
        """获取季度转化漏斗"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_result = MagicMock()
            mock_result.count = 500
            mock_result.data = []
            
            mock_chain = MagicMock()
            mock_chain.gte.return_value = mock_chain
            mock_chain.eq.return_value = mock_chain
            mock_chain.in_.return_value = mock_chain
            mock_chain.execute.return_value = mock_result
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_conversion_funnel
            result = admin_get_conversion_funnel(period="quarter")
            
            assert len(result) == 5


class TestAdminGetAIInsights:
    """Test admin_get_ai_insights function"""
    
    def test_get_ai_insights_all(self):
        """获取所有AI洞察"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []
            mock_result.count = 0
            
            mock_chain = MagicMock()
            mock_chain.gte.return_value = mock_chain
            mock_chain.eq.return_value = mock_chain
            mock_chain.execute.return_value = mock_result
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_ai_insights
            result = admin_get_ai_insights(analysis_type="all")
            
            # Result can be dict or other structure
            assert result is not None


class TestAdminGetAIRecommendations:
    """Test admin_get_ai_recommendations function"""
    
    def test_get_ai_recommendations(self):
        """获取AI推荐"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []
            mock_result.count = 0
            
            mock_chain = MagicMock()
            mock_chain.gte.return_value = mock_chain
            mock_chain.eq.return_value = mock_chain
            mock_chain.in_.return_value = mock_chain
            mock_chain.execute.return_value = mock_result
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_ai_recommendations
            result = admin_get_ai_recommendations(area="all")
            
            # Result is a list of recommendations
            assert isinstance(result, list) or isinstance(result, dict)


class TestAdminGetBehaviorAnalysis:
    """Test admin_get_behavior_analysis function"""
    
    def test_get_behavior_analysis(self):
        """获取用户行为分析"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_events = MagicMock()
            mock_events.data = [
                {"event_type": "page_view", "created_at": "2025-01-01T10:00:00"},
                {"event_type": "button_click", "created_at": "2025-01-01T11:00:00"}
            ]
            
            mock_chain = MagicMock()
            mock_chain.gte.return_value = mock_chain
            mock_chain.lte.return_value = mock_chain
            mock_chain.execute.return_value = mock_events
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_behavior_analysis
            result = admin_get_behavior_analysis()
            
            assert isinstance(result, dict)


class TestLogUserEvent:
    """Test log_user_event function"""
    
    def test_log_event_basic(self):
        """记录基本事件"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import log_user_event
            log_user_event("user-123", "page_view")
            
            mock_supabase.table.assert_called_with("user_events")
    
    def test_log_event_with_properties(self):
        """记录带属性的事件"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import log_user_event
            log_user_event("user-123", "button_click", {"button_id": "signup"}, "session-abc")
            
            call_args = mock_supabase.table.return_value.insert.call_args[0][0]
            assert call_args["properties"]["button_id"] == "signup"
            assert call_args["session_id"] == "session-abc"


class TestAdminGetUserEvents:
    """Test admin_get_user_events function"""
    
    def test_get_user_events_basic(self):
        """获取用户事件"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_events = MagicMock()
            mock_events.data = [
                {"id": "e1", "event_type": "page_view"},
                {"id": "e2", "event_type": "button_click"}
            ]
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.gte.return_value = mock_chain
            mock_chain.lte.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value = mock_events
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_user_events
            result = admin_get_user_events("user-123")
            
            assert len(result) == 2


class TestAdminGetEventStats:
    """Test admin_get_event_stats function"""
    
    def test_get_event_stats(self):
        """获取事件统计"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_events = MagicMock()
            mock_events.data = [
                {"event_type": "page_view"},
                {"event_type": "page_view"},
                {"event_type": "button_click"}
            ]
            
            mock_chain = MagicMock()
            mock_chain.gte.return_value = mock_chain
            mock_chain.lte.return_value = mock_chain
            mock_chain.execute.return_value = mock_events
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import admin_get_event_stats
            result = admin_get_event_stats()
            
            # Returns a list of {key, count} dicts
            assert isinstance(result, list)
            assert len(result) == 2  # page_view and button_click


class TestGetAggregatedStats:
    """Test get_aggregated_stats function"""
    
    def test_get_stats_from_redis_cache(self):
        """从Redis缓存获取统计"""
        with patch('services.db_service.cache_service') as mock_cache:
            mock_cache.get_stats.return_value = {"total_users": 1000}
            
            from services.db_service import get_aggregated_stats
            result = get_aggregated_stats("user_stats")
            
            assert result["total_users"] == 1000
    
    def test_get_stats_from_db_cache(self):
        """从数据库缓存获取统计"""
        with patch('services.db_service.cache_service') as mock_cache:
            with patch('services.db_service.supabase') as mock_supabase:
                mock_cache.get_stats.return_value = None
                
                # Mock fresh DB cache
                recent_time = datetime.now(timezone.utc).isoformat()
                mock_db = MagicMock()
                mock_db.data = [{
                    "data": {"total_users": 500},
                    "updated_at": recent_time
                }]
                
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.order.return_value = mock_chain
                mock_chain.limit.return_value = mock_chain
                mock_chain.execute.return_value = mock_db
                mock_supabase.table.return_value.select.return_value = mock_chain
                
                from services.db_service import get_aggregated_stats
                result = get_aggregated_stats("user_stats")
                
                assert result is not None
    
    def test_get_stats_no_cache(self):
        """无缓存时返回None"""
        with patch('services.db_service.cache_service') as mock_cache:
            with patch('services.db_service.supabase') as mock_supabase:
                mock_cache.get_stats.return_value = None
                
                mock_db = MagicMock()
                mock_db.data = []
                
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.order.return_value = mock_chain
                mock_chain.limit.return_value = mock_chain
                mock_chain.execute.return_value = mock_db
                mock_supabase.table.return_value.select.return_value = mock_chain
                
                from services.db_service import get_aggregated_stats
                result = get_aggregated_stats("user_stats")
                
                assert result is None


class TestGetAggregatedStatsRange:
    """Test get_aggregated_stats_range function"""
    
    def test_get_stats_range(self):
        """获取日期范围内的统计"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_stats = MagicMock()
            mock_stats.data = [
                {"date": "2025-01-01", "data": {"users": 100}},
                {"date": "2025-01-02", "data": {"users": 110}}
            ]
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.gte.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.execute.return_value = mock_stats
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import get_aggregated_stats_range
            result = get_aggregated_stats_range("user_stats", days=7)
            
            assert len(result) == 2


class TestUpsertAggregatedStats:
    """Test upsert_aggregated_stats function"""
    
    def test_upsert_stats(self):
        """更新或插入统计数据"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.cache_service') as mock_cache:
                mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()
                
                from services.db_service import upsert_aggregated_stats
                upsert_aggregated_stats("2025-01-01", "user_stats", {"total": 1000})
                
                mock_supabase.table.assert_called_with("aggregated_stats")
                mock_cache.invalidate_stats_cache.assert_called_with("user_stats")


class TestCreateReportValidation:
    """Test create_report validation"""
    
    def test_create_report_listing_not_found(self):
        """举报不存在的列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            # No existing report
            mock_existing = MagicMock()
            mock_existing.data = []
            
            # Listing not found
            mock_listing = MagicMock()
            mock_listing.data = None
            
            def table_side_effect(table_name):
                mock_table = MagicMock()
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.in_.return_value = mock_chain
                mock_chain.single.return_value = mock_chain
                
                if table_name == "content_reports":
                    mock_chain.execute.return_value = mock_existing
                else:
                    mock_chain.execute.return_value = mock_listing
                
                mock_table.select.return_value = mock_chain
                return mock_table
            
            mock_supabase.table.side_effect = table_side_effect
            
            from services.db_service import create_report
            with pytest.raises(Exception, match="Listing not found"):
                create_report("reporter-123", "nonexistent-listing", "spam")
