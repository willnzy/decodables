"""
Admin Stats API Tests (Black Box)

测试 /api/admin/stats 相关接口

业务规则:
1. 提供 Dashboard 统计数据
2. 支持多种时间周期: day, week, month, quarter, year
3. 支持多种分组方式: day, week, month
4. 包括用户增长、收入、项目、积分等统计

@module tests.integration.staging.admin.test_stats
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminStatsDashboard(BaseAPITest):
    """
    GET /api/admin/stats/dashboard 黑盒测试

    Dashboard 综合统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_DASHBOARD

    def test_dashboard_requires_admin(self, anon_client):
        """
        业务规则: Dashboard 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_dashboard_with_auth(self, auth_client):
        """
        业务规则: 获取 Dashboard 数据
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_dashboard_with_period(self, auth_client):
        """
        业务规则: 指定时间周期
        """
        for period in ["day", "week", "month", "quarter", "year"]:
            response = auth_client.get(
                self.ENDPOINT,
                params={"period": period}
            )
            assert response.status_code in [200, 403]

    def test_dashboard_invalid_period(self, auth_client):
        """
        业务规则: 无效的时间周期
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"period": "invalid_period"}
        )
        assert response.status_code in [400, 403]


@pytest.mark.p1
class TestAdminStatsUserGrowth(BaseAPITest):
    """
    GET /api/admin/stats/user-growth 黑盒测试

    用户增长统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_USER_GROWTH

    def test_user_growth_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_user_growth_with_auth(self, auth_client):
        """
        业务规则: 获取用户增长数据
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_user_growth_with_group_by(self, auth_client):
        """
        业务规则: 按不同维度分组
        """
        for group_by in ["day", "week", "month"]:
            response = auth_client.get(
                self.ENDPOINT,
                params={"group_by": group_by}
            )
            assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminStatsRevenue(BaseAPITest):
    """
    GET /api/admin/stats/revenue 黑盒测试

    收入统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_REVENUE

    def test_revenue_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_revenue_with_auth(self, auth_client):
        """
        业务规则: 获取收入数据
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminStatsProjects(BaseAPITest):
    """
    GET /api/admin/stats/projects 黑盒测试

    项目统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_PROJECTS

    def test_projects_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_projects_with_auth(self, auth_client):
        """
        业务规则: 获取项目统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminStatsCredits(BaseAPITest):
    """
    GET /api/admin/stats/credits 黑盒测试

    积分统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_CREDITS

    def test_credits_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_credits_with_auth(self, auth_client):
        """
        业务规则: 获取积分统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminStatsTierDistribution(BaseAPITest):
    """
    GET /api/admin/stats/tier-distribution 黑盒测试

    Tier 分布统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_TIER_DISTRIBUTION

    def test_tier_distribution_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_tier_distribution_with_auth(self, auth_client):
        """
        业务规则: 获取 tier 分布
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminStatsConversionFunnel(BaseAPITest):
    """
    GET /api/admin/stats/conversion-funnel 黑盒测试

    转化漏斗
    """

    ENDPOINT = Endpoints.ADMIN_STATS_CONVERSION_FUNNEL

    def test_funnel_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_funnel_with_auth(self, auth_client):
        """
        业务规则: 获取转化漏斗数据
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsExports(BaseAPITest):
    """
    GET /api/admin/stats/exports 黑盒测试

    导出统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_EXPORTS

    def test_exports_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_exports_with_auth(self, auth_client):
        """
        业务规则: 获取导出统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsAssets(BaseAPITest):
    """
    GET /api/admin/stats/assets 黑盒测试

    素材统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_ASSETS

    def test_assets_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_assets_with_auth(self, auth_client):
        """
        业务规则: 获取素材统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsTierActivity(BaseAPITest):
    """
    GET /api/admin/stats/tier-activity 黑盒测试

    Tier 活动统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_TIER_ACTIVITY

    def test_tier_activity_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_tier_activity_with_auth(self, auth_client):
        """
        业务规则: 获取 tier 活动数据
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsSubscriptionEvents(BaseAPITest):
    """
    GET /api/admin/stats/subscription-events 黑盒测试

    订阅事件统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_SUBSCRIPTION_EVENTS

    def test_subscription_events_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_subscription_events_with_auth(self, auth_client):
        """
        业务规则: 获取订阅事件
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsPageViews(BaseAPITest):
    """
    GET /api/admin/stats/page-views 黑盒测试

    页面浏览统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_PAGE_VIEWS

    def test_page_views_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_page_views_with_auth(self, auth_client):
        """
        业务规则: 获取页面浏览统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsProjectDetails(BaseAPITest):
    """
    GET /api/admin/stats/project-details 黑盒测试

    项目详情统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_PROJECT_DETAILS

    def test_project_details_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_project_details_with_auth(self, auth_client):
        """
        业务规则: 获取项目详情统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsReturningUsers(BaseAPITest):
    """
    GET /api/admin/stats/returning-users 黑盒测试

    回访用户统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_RETURNING_USERS

    def test_returning_users_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_returning_users_with_auth(self, auth_client):
        """
        业务规则: 获取回访用户统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsTierTrend(BaseAPITest):
    """
    GET /api/admin/stats/tier-trend 黑盒测试

    Tier 趋势统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_TIER_TREND

    def test_tier_trend_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_tier_trend_with_auth(self, auth_client):
        """
        业务规则: 获取 tier 趋势
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsTierConversion(BaseAPITest):
    """
    GET /api/admin/stats/tier-conversion 黑盒测试

    Tier 转化统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_TIER_CONVERSION

    def test_tier_conversion_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_tier_conversion_with_auth(self, auth_client):
        """
        业务规则: 获取 tier 转化数据
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsPerformance(BaseAPITest):
    """
    GET /api/admin/stats/performance 黑盒测试

    性能统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_PERFORMANCE

    def test_performance_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_performance_with_auth(self, auth_client):
        """
        业务规则: 获取性能统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminStatsUserDistribution(BaseAPITest):
    """
    GET /api/admin/stats/user-distribution 黑盒测试

    用户分布统计
    """

    ENDPOINT = Endpoints.ADMIN_STATS_USER_DISTRIBUTION

    def test_user_distribution_requires_admin(self, anon_client):
        """
        业务规则: 需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_user_distribution_with_auth(self, auth_client):
        """
        业务规则: 获取用户分布
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]
