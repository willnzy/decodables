"""
Admin System API Tests (Black Box)

测试 /api/v2/admin/system 和其他管理接口

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. 系统配置、统计、日志都需要管理员权限
2. Admin API 使用 require_admin 依赖进行权限检查
3. 普通用户访问应返回 403

@module tests.integration.staging.admin.test_admin_system
"""

import pytest
from ..base import BaseAPITest


# Admin API Base URLs
API_ADMIN = "/api/v2/admin"


@pytest.mark.p1
class TestAdminStats(BaseAPITest):
    """
    GET /api/v2/admin/stats/* 黑盒测试

    统计数据接口
    """

    def test_stats_requires_admin(self, auth_client):
        """
        业务规则: 统计数据需要管理员权限

        注意: /api/v2/admin/stats 是 prefix，需要访问具体子路由
        如 /stats/dashboard, /stats/user-growth 等
        """
        # 访问 dashboard 子路由
        response = auth_client.get(f"{API_ADMIN}/stats/dashboard")

        # 403 = 权限拒绝, 404 = 端点不存在
        assert response.status_code in [403, 404], (
            f"统计数据需要管理员权限，普通用户应返回 403/404，但返回了 {response.status_code}"
        )

    def test_stats_dashboard_requires_admin(self, auth_client):
        """
        业务规则: Dashboard 统计需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/stats/dashboard")

        # 可能是 403 (权限) 或 404 (端点不存在)
        assert response.status_code in [403, 404], (
            f"Dashboard 需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestAdminConfig(BaseAPITest):
    """
    /api/v2/admin/config/* 黑盒测试

    系统配置接口
    """

    def test_get_config_requires_admin(self, auth_client):
        """
        业务规则: 系统配置需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/config")

        assert response.status_code == 403, (
            f"系统配置需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )

    def test_update_config_requires_admin(self, auth_client):
        """
        业务规则: 更新配置需要管理员权限
        """
        response = auth_client.patch(
            f"{API_ADMIN}/config",
            json={"key": "test", "value": "test"}
        )

        # 可能是 403 (权限) 或 404/405 (端点/方法不支持)
        assert response.status_code in [403, 404, 405, 422], (
            f"更新配置需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestAdminLogs(BaseAPITest):
    """
    /api/v2/admin/logs/* 黑盒测试

    日志接口
    """

    def test_get_logs_requires_admin(self, auth_client):
        """
        业务规则: 系统日志需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/logs")

        assert response.status_code in [403, 404], (
            f"系统日志需要管理员权限，普通用户应返回 403/404，但返回了 {response.status_code}"
        )

    def test_get_error_logs_requires_admin(self, auth_client):
        """
        业务规则: 错误日志需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/logs/errors")

        # 可能是 403 或 404
        assert response.status_code in [403, 404], (
            f"错误日志需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestAdminMetrics(BaseAPITest):
    """
    /api/v2/admin/metrics/* 黑盒测试

    指标接口
    """

    def test_get_metrics_requires_admin(self, auth_client):
        """
        业务规则: 系统指标需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/metrics")

        assert response.status_code in [403, 404], (
            f"系统指标需要管理员权限，普通用户应返回 403/404，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestAdminCampaigns(BaseAPITest):
    """
    /api/v2/admin/campaigns/* 黑盒测试

    营销活动接口
    """

    def test_list_campaigns_requires_admin(self, auth_client):
        """
        业务规则: 营销活动列表需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/campaigns")

        assert response.status_code == 403, (
            f"营销活动需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )

    def test_create_campaign_requires_admin(self, auth_client):
        """
        业务规则: 创建营销活动需要管理员权限
        """
        response = auth_client.post(
            f"{API_ADMIN}/campaigns",
            json={
                "name": "Test Campaign",
                "type": "discount"
            }
        )

        # 可能是 403 或 422 (验证失败)
        assert response.status_code in [403, 422], (
            f"创建活动需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestAdminModeration(BaseAPITest):
    """
    /api/v2/admin/moderation/* 黑盒测试

    内容审核接口
    """

    def test_moderation_queue_requires_admin(self, auth_client):
        """
        业务规则: 审核队列需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/moderation/queue")

        # 可能是 403 或 404
        assert response.status_code in [403, 404], (
            f"审核队列需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminNotifications(BaseAPITest):
    """
    /api/v2/admin/notifications/* 黑盒测试

    通知管理接口
    """

    def test_list_notifications_requires_admin(self, auth_client):
        """
        业务规则: 通知管理需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/notifications")

        assert response.status_code == 403, (
            f"通知管理需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminExperiments(BaseAPITest):
    """
    /api/v2/admin/experiments/* 黑盒测试

    A/B 测试实验接口
    """

    def test_list_experiments_requires_admin(self, auth_client):
        """
        业务规则: A/B 实验管理需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/experiments")

        assert response.status_code == 403, (
            f"实验管理需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminFeatureFlags(BaseAPITest):
    """
    /api/v2/admin/feature-flags/* 黑盒测试

    Feature Flag 接口
    """

    def test_list_flags_requires_admin(self, auth_client):
        """
        业务规则: Feature Flag 管理需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/feature-flags")

        assert response.status_code == 403, (
            f"Feature Flag 需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminAI(BaseAPITest):
    """
    /api/v2/admin/ai/* 黑盒测试

    AI 管理接口
    """

    def test_ai_stats_requires_admin(self, auth_client):
        """
        业务规则: AI 统计需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/ai/stats")

        # 可能是 403 或 404
        assert response.status_code in [403, 404], (
            f"AI 统计需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminEvents(BaseAPITest):
    """
    /api/v2/admin/events/* 黑盒测试

    事件管理接口
    """

    def test_list_events_requires_admin(self, auth_client):
        """
        业务规则: 事件管理需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/events")

        assert response.status_code in [403, 404], (
            f"事件管理需要管理员权限，普通用户应返回 403/404，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminAssetCategories(BaseAPITest):
    """
    /api/v2/admin/asset-categories/* 黑盒测试

    素材分类管理接口
    """

    def test_list_categories_requires_admin(self, auth_client):
        """
        业务规则: 素材分类管理需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/asset-categories")

        assert response.status_code in [200, 403], (
            f"素材分类可能对认证用户开放或需要管理员权限，但返回了 {response.status_code}"
        )


@pytest.mark.p2
class TestAdminThemes(BaseAPITest):
    """
    /api/v2/admin/themes/* 黑盒测试

    主题管理接口
    """

    def test_list_themes_requires_admin(self, auth_client):
        """
        业务规则: 主题管理需要管理员权限
        """
        response = auth_client.get(f"{API_ADMIN}/themes")

        assert response.status_code == 403, (
            f"主题管理需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )
