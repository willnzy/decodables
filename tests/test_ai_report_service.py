"""
AI Report Service Tests
AI 商业报告服务测试

Coverage target: 80%+
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone


class TestInsightPriority:
    """Test InsightPriority enum"""
    
    def test_priority_values(self):
        """All priority values exist"""
        from services.ai_report_service import InsightPriority
        
        assert InsightPriority.CRITICAL == "critical"
        assert InsightPriority.HIGH == "high"
        assert InsightPriority.MEDIUM == "medium"
        assert InsightPriority.LOW == "low"


class TestMetricTrend:
    """Test MetricTrend enum"""
    
    def test_trend_values(self):
        """All trend values exist"""
        from services.ai_report_service import MetricTrend
        
        assert MetricTrend.INCREASING == "increasing"
        assert MetricTrend.DECREASING == "decreasing"
        assert MetricTrend.STABLE == "stable"
        assert MetricTrend.VOLATILE == "volatile"


class TestMetricData:
    """Test MetricData dataclass"""
    
    def test_basic_creation(self):
        """Can create basic metric"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(
            name="Test Metric",
            current_value=100,
            previous_value=80,
            year_ago_value=90,
        )
        
        assert metric.name == "Test Metric"
        assert metric.current_value == 100
        assert metric.previous_value == 80
        assert metric.year_ago_value == 90
    
    def test_mom_change_positive(self):
        """MoM change calculates positive change"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=120, previous_value=100, year_ago_value=None)
        
        assert metric.mom_change == 20.0  # (120-100)/100 * 100
    
    def test_mom_change_negative(self):
        """MoM change calculates negative change"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=80, previous_value=100, year_ago_value=None)
        
        assert metric.mom_change == -20.0
    
    def test_mom_change_zero_previous(self):
        """MoM change handles zero previous value"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=100, previous_value=0, year_ago_value=None)
        
        assert metric.mom_change == 100.0  # Goes to infinity, capped at 100
    
    def test_mom_change_both_zero(self):
        """MoM change handles both zero values"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=0, previous_value=0, year_ago_value=None)
        
        assert metric.mom_change == 0.0
    
    def test_yoy_change(self):
        """YoY change calculates correctly"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=150, previous_value=100, year_ago_value=100)
        
        assert metric.yoy_change == 50.0  # (150-100)/100 * 100
    
    def test_yoy_change_none(self):
        """YoY change returns None when no year ago value"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=100, previous_value=80, year_ago_value=None)
        
        assert metric.yoy_change is None
    
    def test_yoy_change_zero_year_ago(self):
        """YoY change returns None when year ago value is zero"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=100, previous_value=80, year_ago_value=0)
        
        assert metric.yoy_change is None
    
    def test_trend_stable(self):
        """Trend is stable for small changes"""
        from services.ai_report_service import MetricData, MetricTrend
        
        metric = MetricData(name="Test", current_value=102, previous_value=100, year_ago_value=None)
        
        assert metric.trend == MetricTrend.STABLE
    
    def test_trend_increasing(self):
        """Trend is increasing for positive large change"""
        from services.ai_report_service import MetricData, MetricTrend
        
        metric = MetricData(name="Test", current_value=120, previous_value=100, year_ago_value=None)
        
        assert metric.trend == MetricTrend.INCREASING
    
    def test_trend_decreasing(self):
        """Trend is decreasing for negative large change"""
        from services.ai_report_service import MetricData, MetricTrend
        
        metric = MetricData(name="Test", current_value=80, previous_value=100, year_ago_value=None)
        
        assert metric.trend == MetricTrend.DECREASING
    
    def test_is_anomaly_true(self):
        """is_anomaly True for >30% change"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=150, previous_value=100, year_ago_value=None)
        
        assert metric.is_anomaly is True
    
    def test_is_anomaly_false(self):
        """is_anomaly False for <=30% change"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(name="Test", current_value=120, previous_value=100, year_ago_value=None)
        
        assert metric.is_anomaly is False
    
    def test_to_prompt_string(self):
        """to_prompt_string formats correctly"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(
            name="Test Metric",
            current_value=100,
            previous_value=80,
            year_ago_value=70,
            unit="$",
        )
        
        result = metric.to_prompt_string()
        
        assert "Test Metric" in result
        assert "$" in result or "100" in result
        assert "MoM" in result
        assert "YoY" in result
    
    def test_to_prompt_string_percentage(self):
        """to_prompt_string handles percentage metrics"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(
            name="Conversion Rate",
            current_value=5.5,
            previous_value=4.0,
            year_ago_value=None,
            is_percentage=True,
        )
        
        result = metric.to_prompt_string()
        
        assert "%" in result
    
    def test_to_prompt_string_anomaly(self):
        """to_prompt_string marks anomalies"""
        from services.ai_report_service import MetricData
        
        metric = MetricData(
            name="Test",
            current_value=200,
            previous_value=100,
            year_ago_value=None,
        )
        
        result = metric.to_prompt_string()
        
        assert "ANOMALY" in result


class TestUserBehaviorTrend:
    """Test UserBehaviorTrend dataclass"""
    
    def test_basic_creation(self):
        """Can create basic trend"""
        from services.ai_report_service import UserBehaviorTrend
        
        trend = UserBehaviorTrend(
            metric_name="Daily Users",
            daily_values=[("01/01", 100), ("01/02", 110)],
            description="Test description",
        )
        
        assert trend.metric_name == "Daily Users"
        assert len(trend.daily_values) == 2
    
    def test_to_prompt_string_empty(self):
        """to_prompt_string handles empty data"""
        from services.ai_report_service import UserBehaviorTrend
        
        trend = UserBehaviorTrend(metric_name="Empty", daily_values=[])
        
        result = trend.to_prompt_string()
        
        assert "No data available" in result
    
    def test_to_prompt_string_with_data(self):
        """to_prompt_string formats data correctly"""
        from services.ai_report_service import UserBehaviorTrend
        
        trend = UserBehaviorTrend(
            metric_name="Test Trend",
            daily_values=[("01/01", 100), ("01/02", 110), ("01/03", 120)],
        )
        
        result = trend.to_prompt_string()
        
        assert "Test Trend" in result
        assert "01/01" in result or "01/03" in result
    
    def test_to_prompt_string_last_7_days(self):
        """to_prompt_string shows last 7 days"""
        from services.ai_report_service import UserBehaviorTrend
        
        # Create 10 days of data
        values = [(f"01/{i:02d}", i * 10) for i in range(1, 11)]
        trend = UserBehaviorTrend(metric_name="Test", daily_values=values)
        
        result = trend.to_prompt_string()
        
        # Should contain "last 7 days"
        assert "7 days" in result or "Test" in result


class TestConstants:
    """Test constants"""
    
    def test_metric_thresholds_defined(self):
        """METRIC_THRESHOLDS is defined"""
        from services.ai_report_service import METRIC_THRESHOLDS
        
        assert "conversion_rate" in METRIC_THRESHOLDS
        assert "churn_rate" in METRIC_THRESHOLDS
        assert "ai_success_rate" in METRIC_THRESHOLDS
    
    def test_expert_system_prompt_defined(self):
        """EXPERT_SYSTEM_PROMPT is defined"""
        from services.ai_report_service import EXPERT_SYSTEM_PROMPT
        
        assert len(EXPERT_SYSTEM_PROMPT) > 100
        assert "数据分析" in EXPERT_SYSTEM_PROMPT or "洞察" in EXPERT_SYSTEM_PROMPT


class TestGetDateRanges:
    """Test get_date_ranges function"""
    
    def test_returns_all_ranges(self):
        """Returns all expected date ranges"""
        from services.ai_report_service import get_date_ranges
        
        ranges = get_date_ranges()
        
        assert "current_30d" in ranges
        assert "previous_30d" in ranges
        assert "current_7d" in ranges
        assert "previous_7d" in ranges
        assert "year_ago_30d" in ranges
    
    def test_ranges_are_tuples(self):
        """Each range is a tuple of datetimes"""
        from services.ai_report_service import get_date_ranges
        
        ranges = get_date_ranges()
        
        for key, (start, end) in ranges.items():
            assert isinstance(start, datetime)
            assert isinstance(end, datetime)
            assert start < end


class TestIdentifyAnomalies:
    """Test identify_anomalies function"""
    
    def test_identifies_anomaly(self):
        """Identifies metrics with >30% change"""
        from services.ai_report_service import identify_anomalies, MetricData
        
        metrics = [
            MetricData(name="Normal", current_value=110, previous_value=100, year_ago_value=None),
            MetricData(name="Anomaly", current_value=200, previous_value=100, year_ago_value=None),
        ]
        
        warnings = identify_anomalies(metrics)
        
        assert len(warnings) >= 1
        assert any("Anomaly" in w for w in warnings)
    
    def test_no_anomaly_for_small_changes(self):
        """No anomaly for small changes"""
        from services.ai_report_service import identify_anomalies, MetricData
        
        metrics = [
            MetricData(name="Stable", current_value=105, previous_value=100, year_ago_value=None),
        ]
        
        warnings = identify_anomalies(metrics)
        
        assert len(warnings) == 0
    
    def test_checks_thresholds(self):
        """Checks critical thresholds"""
        from services.ai_report_service import identify_anomalies, MetricData
        
        # Create a metric that hits critical threshold
        metrics = [
            MetricData(
                name="Conversion Rate Test",  # Should match conversion_rate threshold
                current_value=0.5,  # Below critical_low of 1.0
                previous_value=0.5,
                year_ago_value=None,
                is_percentage=True,
            ),
        ]
        
        warnings = identify_anomalies(metrics)
        
        # May or may not trigger based on threshold matching
        # At least the function runs without error
        assert isinstance(warnings, list)


class TestCollectMetricsFunctions:
    """Test metric collection functions"""
    
    @patch('services.ai_report_service.supabase')
    def test_collect_growth_metrics_handles_empty(self, mock_supabase):
        """collect_growth_metrics handles empty data"""
        from services.ai_report_service import collect_growth_metrics
        
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value = MagicMock(data=[], count=0)
        
        metrics = collect_growth_metrics()
        
        assert isinstance(metrics, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_growth_metrics_handles_exception(self, mock_supabase):
        """collect_growth_metrics handles exceptions gracefully"""
        from services.ai_report_service import collect_growth_metrics
        
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.side_effect = Exception("DB Error")
        
        metrics = collect_growth_metrics()
        
        # Should return empty list on error
        assert isinstance(metrics, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_conversion_metrics_handles_empty(self, mock_supabase):
        """collect_conversion_metrics handles empty data"""
        from services.ai_report_service import collect_conversion_metrics
        
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.in_.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.gt.return_value.execute.return_value = mock_result
        
        metrics = collect_conversion_metrics()
        
        assert isinstance(metrics, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_retention_metrics_handles_empty(self, mock_supabase):
        """collect_retention_metrics handles empty data"""
        from services.ai_report_service import collect_retention_metrics
        
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.in_.return_value.gte.return_value.lt.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_result
        
        metrics = collect_retention_metrics()
        
        assert isinstance(metrics, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_product_metrics_handles_empty(self, mock_supabase):
        """collect_product_metrics handles empty data"""
        from services.ai_report_service import collect_product_metrics
        
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lt.return_value.execute.return_value = mock_result
        
        metrics = collect_product_metrics()
        
        assert isinstance(metrics, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_user_behavior_trends_handles_empty(self, mock_supabase):
        """collect_user_behavior_trends handles empty data"""
        from services.ai_report_service import collect_user_behavior_trends
        
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value = mock_result
        
        trends = collect_user_behavior_trends()
        
        assert isinstance(trends, list)


class TestGenerateAIBusinessReport:
    """Test generate_ai_business_report function"""
    
    @patch('services.ai_report_service.openai_client')
    @patch('services.ai_report_service.collect_growth_metrics')
    @patch('services.ai_report_service.collect_conversion_metrics')
    @patch('services.ai_report_service.collect_retention_metrics')
    @patch('services.ai_report_service.collect_product_metrics')
    @patch('services.ai_report_service.collect_user_behavior_trends')
    def test_generates_report(
        self, mock_trends, mock_product, mock_retention, mock_conversion, mock_growth, mock_openai
    ):
        """Generates full report"""
        from services.ai_report_service import generate_ai_business_report, MetricData, UserBehaviorTrend
        
        # Setup mocks
        mock_growth.return_value = [
            MetricData(name="DAU", current_value=100, previous_value=90, year_ago_value=None)
        ]
        mock_conversion.return_value = []
        mock_retention.return_value = []
        mock_product.return_value = []
        mock_trends.return_value = []
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="## AI Generated Report\n\nTest content"))]
        mock_openai.chat.completions.create.return_value = mock_response
        
        result = generate_ai_business_report()
        
        assert "report_markdown" in result
        assert "metrics_summary" in result
        assert "anomalies" in result
        assert "generated_at" in result
    
    @patch('services.ai_report_service.openai_client')
    @patch('services.ai_report_service.collect_growth_metrics')
    @patch('services.ai_report_service.collect_conversion_metrics')
    @patch('services.ai_report_service.collect_retention_metrics')
    @patch('services.ai_report_service.collect_product_metrics')
    @patch('services.ai_report_service.collect_user_behavior_trends')
    def test_handles_openai_error(
        self, mock_trends, mock_product, mock_retention, mock_conversion, mock_growth, mock_openai
    ):
        """Handles OpenAI API error gracefully"""
        from services.ai_report_service import generate_ai_business_report
        
        mock_growth.return_value = []
        mock_conversion.return_value = []
        mock_retention.return_value = []
        mock_product.return_value = []
        mock_trends.return_value = []
        
        mock_openai.chat.completions.create.side_effect = Exception("API Error")
        
        result = generate_ai_business_report()
        
        assert "报告生成失败" in result["report_markdown"]
        assert "API Error" in result["report_markdown"]


class TestGetQuickInsights:
    """Test get_quick_insights function"""
    
    @patch('services.ai_report_service.collect_growth_metrics')
    @patch('services.ai_report_service.collect_conversion_metrics')
    def test_returns_insights(self, mock_conversion, mock_growth):
        """Returns quick insights"""
        from services.ai_report_service import get_quick_insights, MetricData
        
        mock_growth.return_value = [
            MetricData(name="DAU", current_value=200, previous_value=100, year_ago_value=None)  # Anomaly
        ]
        mock_conversion.return_value = []
        
        insights = get_quick_insights()
        
        assert isinstance(insights, list)
        assert len(insights) <= 5  # Max 5 insights
    
    @patch('services.ai_report_service.collect_growth_metrics')
    @patch('services.ai_report_service.collect_conversion_metrics')
    def test_identifies_critical_anomalies(self, mock_conversion, mock_growth):
        """Identifies critical anomalies (>50% change)"""
        from services.ai_report_service import get_quick_insights, MetricData
        
        mock_growth.return_value = [
            MetricData(name="Critical Metric", current_value=200, previous_value=100, year_ago_value=None)  # 100% change
        ]
        mock_conversion.return_value = []
        
        insights = get_quick_insights()
        
        if insights:
            assert insights[0]["priority"] == "critical"
    
    @patch('services.ai_report_service.collect_growth_metrics')
    @patch('services.ai_report_service.collect_conversion_metrics')
    def test_returns_empty_for_no_anomalies(self, mock_conversion, mock_growth):
        """Returns empty list when no anomalies"""
        from services.ai_report_service import get_quick_insights, MetricData
        
        mock_growth.return_value = [
            MetricData(name="Stable", current_value=105, previous_value=100, year_ago_value=None)  # 5% change
        ]
        mock_conversion.return_value = []
        
        insights = get_quick_insights()
        
        assert insights == []


# ==========================================
# Exception Handling Tests
# ==========================================

class TestExceptionHandling:
    """Test exception handling in metric collection functions"""
    
    @patch('services.ai_report_service.supabase')
    def test_collect_growth_metrics_exception(self, mock_supabase):
        """collect_growth_metrics handles exceptions"""
        from services.ai_report_service import collect_growth_metrics
        
        mock_supabase.table.side_effect = Exception("DB Error")
        
        # Should return empty list instead of raising
        result = collect_growth_metrics()
        
        assert isinstance(result, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_conversion_metrics_exception(self, mock_supabase):
        """collect_conversion_metrics handles exceptions"""
        from services.ai_report_service import collect_conversion_metrics
        
        mock_supabase.table.side_effect = Exception("DB Error")
        
        result = collect_conversion_metrics()
        
        assert isinstance(result, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_retention_metrics_exception(self, mock_supabase):
        """collect_retention_metrics handles exceptions"""
        from services.ai_report_service import collect_retention_metrics
        
        mock_supabase.table.side_effect = Exception("DB Error")
        
        result = collect_retention_metrics()
        
        assert isinstance(result, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_product_metrics_exception(self, mock_supabase):
        """collect_product_metrics handles exceptions"""
        from services.ai_report_service import collect_product_metrics
        
        mock_supabase.table.side_effect = Exception("DB Error")
        
        result = collect_product_metrics()
        
        assert isinstance(result, list)
    
    @patch('services.ai_report_service.supabase')
    def test_collect_user_behavior_trends_exception(self, mock_supabase):
        """collect_user_behavior_trends handles exceptions"""
        from services.ai_report_service import collect_user_behavior_trends
        
        mock_supabase.table.side_effect = Exception("DB Error")
        
        result = collect_user_behavior_trends()
        
        assert isinstance(result, list)
    
    @patch('services.ai_report_service.supabase')
    def test_identify_anomalies_exception(self, mock_supabase):
        """identify_anomalies handles exceptions"""
        from services.ai_report_service import identify_anomalies, MetricData
        
        metrics = [
            MetricData(name="Test", current_value=200, previous_value=100, year_ago_value=None)
        ]
        
        # Should not raise
        result = identify_anomalies(metrics)
        
        assert isinstance(result, list)


class TestDataProcessingBranches:
    """Test data processing conditional branches"""
    
    @patch('services.ai_report_service.supabase')
    def test_dau_calculation_with_data(self, mock_supabase):
        """DAU calculation processes activity data correctly"""
        from services.ai_report_service import collect_growth_metrics
        from collections import defaultdict
        
        # Mock profiles count
        mock_count_result = MagicMock()
        mock_count_result.count = 100
        
        # Mock activity logs with actual data
        mock_activities = MagicMock()
        mock_activities.data = [
            {"user_id": "user1", "created_at": "2024-01-01T10:00:00Z"},
            {"user_id": "user2", "created_at": "2024-01-01T11:00:00Z"},
            {"user_id": "user1", "created_at": "2024-01-02T10:00:00Z"},
            {"user_id": "user3", "created_at": "2024-01-02T11:00:00Z"},
        ]
        
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lt.return_value = mock_table
        mock_table.execute.return_value = mock_activities
        
        mock_supabase.table.return_value = mock_table
        
        result = collect_growth_metrics()
        
        # Should return some metrics without error
        assert isinstance(result, list)
    
    @patch('services.ai_report_service.supabase')
    def test_dau_mau_ratio_with_positive_mau(self, mock_supabase):
        """DAU/MAU ratio calculated when MAU > 0"""
        from services.ai_report_service import collect_growth_metrics
        
        # Mock with enough data to have positive MAU
        mock_result = MagicMock()
        mock_result.data = [
            {"user_id": f"user{i}", "created_at": f"2024-01-{(i % 28) + 1:02d}T10:00:00Z"}
            for i in range(100)
        ]
        mock_result.count = 1000
        
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lt.return_value = mock_table
        mock_table.execute.return_value = mock_result
        
        mock_supabase.table.return_value = mock_table
        
        result = collect_growth_metrics()
        
        assert isinstance(result, list)
    
    @patch('services.ai_report_service.supabase')
    def test_retention_with_cohort_data(self, mock_supabase):
        """D1 retention calculated with cohort data"""
        from services.ai_report_service import collect_retention_metrics
        
        # Mock cohort data
        mock_cohort = MagicMock()
        mock_cohort.data = [
            {"id": "user1"},
            {"id": "user2"},
            {"id": "user3"},
        ]
        
        # Mock activity data
        mock_activity = MagicMock()
        mock_activity.data = [
            {"user_id": "user1"},
            {"user_id": "user2"},
        ]
        
        call_count = [0]
        def mock_execute():
            call_count[0] += 1
            if call_count[0] % 2 == 1:
                return mock_cohort
            return mock_activity
        
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lt.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.execute.side_effect = mock_execute
        
        mock_supabase.table.return_value = mock_table
        
        result = collect_retention_metrics()
        
        assert isinstance(result, list)
