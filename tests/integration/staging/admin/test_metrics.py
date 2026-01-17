"""
Admin Metrics API Tests (Black Box)

测试 /api/admin/metrics 相关接口

业务规则:
1. 系统指标监控
2. 支持多种时间周期: 7d, 14d, 30d, 60d, 90d
3. 包括日活、留存、漏斗等指标
4. 支持手动刷新缓存

@module tests.integration.staging.admin.test_metrics
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminMetricsDaily(BaseAPITest):
    """
    GET /api/admin/metrics/daily 黑盒测试

    日度指标
    """

    ENDPOINT = Endpoints.ADMIN_METRICS_DAILY

    def test_daily_requires_admin(self, anon_client):
        """
        业务规则: 获取日度指标需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_daily_with_auth(self, auth_client):
        """
        业务规则: 获取日度指标
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_daily_with_period(self, auth_client):
        """
        业务规则: 指定时间周期
        """
        for period in ["7d", "14d", "30d", "60d", "90d"]:
            response = auth_client.get(
                self.ENDPOINT,
                params={"period": period}
            )
            assert response.status_code in [200, 403]

    def test_daily_invalid_period(self, auth_client):
        """
        业务规则: 无效的时间周期
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"period": "invalid_period"}
        )
        assert response.status_code in [400, 403]


@pytest.mark.p1
class TestAdminMetricsMonthly(BaseAPITest):
    """
    GET /api/admin/metrics/monthly 黑盒测试

    月度指标
    """

    ENDPOINT = Endpoints.ADMIN_METRICS_MONTHLY

    def test_monthly_requires_admin(self, anon_client):
        """
        业务规则: 获取月度指标需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_monthly_with_auth(self, auth_client):
        """
        业务规则: 获取月度指标
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_monthly_with_months(self, auth_client):
        """
        业务规则: 指定月数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"months": 6}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminMetricsRetention(BaseAPITest):
    """
    GET /api/admin/metrics/retention 黑盒测试

    留存指标
    """

    ENDPOINT = Endpoints.ADMIN_METRICS_RETENTION

    def test_retention_requires_admin(self, anon_client):
        """
        业务规则: 获取留存指标需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_retention_with_auth(self, auth_client):
        """
        业务规则: 获取留存指标
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_retention_with_period(self, auth_client):
        """
        业务规则: 指定留存周期
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"period": "30d"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminMetricsFunnel(BaseAPITest):
    """
    GET /api/admin/metrics/funnel 黑盒测试

    转化漏斗
    """

    ENDPOINT = Endpoints.ADMIN_METRICS_FUNNEL

    def test_funnel_requires_admin(self, anon_client):
        """
        业务规则: 获取漏斗指标需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_funnel_with_auth(self, auth_client):
        """
        业务规则: 获取转化漏斗数据
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminMetricsErrors(BaseAPITest):
    """
    GET /api/admin/metrics/errors 黑盒测试

    错误指标
    """

    ENDPOINT = Endpoints.ADMIN_METRICS_ERRORS

    def test_errors_requires_admin(self, anon_client):
        """
        业务规则: 获取错误指标需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_errors_with_auth(self, auth_client):
        """
        业务规则: 获取错误指标
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_errors_with_period(self, auth_client):
        """
        业务规则: 指定时间周期
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"period": "7d"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminMetricsDAUTrend(BaseAPITest):
    """
    GET /api/admin/metrics/dau-trend 黑盒测试

    DAU 趋势
    """

    ENDPOINT = Endpoints.ADMIN_METRICS_DAU_TREND

    def test_dau_trend_requires_admin(self, anon_client):
        """
        业务规则: 获取 DAU 趋势需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_dau_trend_with_auth(self, auth_client):
        """
        业务规则: 获取 DAU 趋势
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_dau_trend_with_days(self, auth_client):
        """
        业务规则: 指定天数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"days": 30}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminMetricsRefresh(BaseAPITest):
    """
    POST /api/admin/metrics/refresh 黑盒测试

    刷新指标缓存
    """

    ENDPOINT = Endpoints.ADMIN_METRICS_REFRESH

    def test_refresh_requires_admin(self, anon_client):
        """
        业务规则: 刷新缓存需要管理员权限
        """
        response = anon_client.post(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_refresh_with_auth(self, auth_client):
        """
        业务规则: 刷新指标缓存
        """
        response = auth_client.post(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 202, 403]

    def test_refresh_specific_metric(self, auth_client):
        """
        业务规则: 刷新特定指标
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"metric_type": "daily"}
        )
        assert response.status_code in [200, 202, 400, 403]


@pytest.mark.p2
class TestAdminMetricsValidation(BaseAPITest):
    """
    Admin Metrics API 参数验证测试
    """

    def test_daily_invalid_period_format(self, auth_client):
        """
        业务规则: 无效的时间周期格式
        """
        response = auth_client.get(
            Endpoints.ADMIN_METRICS_DAILY,
            params={"period": "100"}  # 缺少单位
        )
        assert response.status_code in [400, 403]

    def test_monthly_invalid_months(self, auth_client):
        """
        业务规则: 无效的月数
        """
        response = auth_client.get(
            Endpoints.ADMIN_METRICS_MONTHLY,
            params={"months": -1}
        )
        assert response.status_code in [400, 403, 422]

    def test_dau_invalid_days(self, auth_client):
        """
        业务规则: 无效的天数
        """
        response = auth_client.get(
            Endpoints.ADMIN_METRICS_DAU_TREND,
            params={"days": 0}
        )
        assert response.status_code in [400, 403, 422]

    def test_metrics_very_long_period(self, auth_client):
        """
        业务规则: 过长的时间周期
        """
        response = auth_client.get(
            Endpoints.ADMIN_METRICS_DAILY,
            params={"period": "365d"}  # 超过支持范围
        )
        # 可能不支持或被截断
        assert response.status_code in [200, 400, 403]

    def test_refresh_invalid_metric_type(self, auth_client):
        """
        业务规则: 无效的指标类型
        """
        response = auth_client.post(
            Endpoints.ADMIN_METRICS_REFRESH,
            json={"metric_type": "invalid_type"}
        )
        assert response.status_code in [200, 400, 403, 422]
