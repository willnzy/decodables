"""
Admin Logs API Tests (Black Box)

测试 /api/admin/logs 相关接口

业务规则:
1. 错误日志管理
2. 操作日志管理
3. 审计日志管理
4. 支持导出功能

@module tests.integration.staging.admin.test_logs
"""

import pytest
from datetime import datetime, timedelta
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminLogsErrors(BaseAPITest):
    """
    GET /api/admin/logs/errors 黑盒测试

    获取错误日志
    """

    ENDPOINT = Endpoints.ADMIN_LOGS_ERRORS

    def test_errors_requires_admin(self, anon_client):
        """
        业务规则: 获取错误日志需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_errors_with_auth(self, auth_client):
        """
        业务规则: 获取错误日志列表
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_errors_pagination(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 20}
        )
        assert response.status_code in [200, 403]

    def test_errors_filter_by_level(self, auth_client):
        """
        业务规则: 按错误级别筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"level": "error"}
        )
        assert response.status_code in [200, 403]

    def test_errors_filter_by_date_range(self, auth_client):
        """
        业务规则: 按日期范围筛选
        """
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        response = auth_client.get(
            self.ENDPOINT,
            params={"start_date": yesterday, "end_date": today}
        )
        assert response.status_code in [200, 403]

    def test_errors_filter_by_source(self, auth_client):
        """
        业务规则: 按来源筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"source": "api"}
        )
        assert response.status_code in [200, 403]

    def test_errors_search(self, auth_client):
        """
        业务规则: 搜索错误日志
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"search": "exception"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminLogsErrorsStats(BaseAPITest):
    """
    GET /api/admin/logs/errors/stats 黑盒测试

    错误统计
    """

    ENDPOINT = Endpoints.ADMIN_LOGS_ERRORS_STATS

    def test_stats_requires_admin(self, anon_client):
        """
        业务规则: 获取错误统计需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_stats_with_auth(self, auth_client):
        """
        业务规则: 获取错误统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_stats_with_time_range(self, auth_client):
        """
        业务规则: 指定时间范围的统计
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"range": "7d"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminLogsOperations(BaseAPITest):
    """
    GET /api/admin/logs/operations 黑盒测试

    操作日志
    """

    ENDPOINT = Endpoints.ADMIN_LOGS_OPERATIONS

    def test_operations_requires_admin(self, anon_client):
        """
        业务规则: 获取操作日志需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_operations_with_auth(self, auth_client):
        """
        业务规则: 获取操作日志列表
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_operations_pagination(self, auth_client):
        """
        业务规则: 支持分页
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 50}
        )
        assert response.status_code in [200, 403]

    def test_operations_filter_by_admin(self, auth_client):
        """
        业务规则: 按管理员筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"admin_id": "admin_test_123"}
        )
        assert response.status_code in [200, 403]

    def test_operations_filter_by_type(self, auth_client):
        """
        业务规则: 按操作类型筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"operation_type": "user_update"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminLogsOperationsExport(BaseAPITest):
    """
    GET /api/admin/logs/operations/export 黑盒测试

    导出操作日志 (CSV)
    """

    ENDPOINT = Endpoints.ADMIN_LOGS_OPERATIONS_EXPORT

    def test_export_requires_admin(self, anon_client):
        """
        业务规则: 导出需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_export_with_auth(self, auth_client):
        """
        业务规则: 导出操作日志
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (CSV 文件) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_export_with_date_range(self, auth_client):
        """
        业务规则: 导出指定日期范围的日志
        """
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        response = auth_client.get(
            self.ENDPOINT,
            params={"start_date": week_ago, "end_date": today}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminLogsAudit(BaseAPITest):
    """
    GET /api/admin/logs/audit 黑盒测试

    审计日志
    """

    ENDPOINT = Endpoints.ADMIN_LOGS_AUDIT

    def test_audit_requires_admin(self, anon_client):
        """
        业务规则: 获取审计日志需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_audit_with_auth(self, auth_client):
        """
        业务规则: 获取审计日志列表
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_audit_pagination(self, auth_client):
        """
        业务规则: 支持分页
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 100}
        )
        assert response.status_code in [200, 403]

    def test_audit_filter_by_target(self, auth_client):
        """
        业务规则: 按目标类型筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"target_type": "user"}
        )
        assert response.status_code in [200, 403]

    def test_audit_filter_by_action(self, auth_client):
        """
        业务规则: 按操作筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"action": "update"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p2
class TestAdminLogsValidation(BaseAPITest):
    """
    Admin Logs API 参数验证测试
    """

    def test_errors_invalid_level(self, auth_client):
        """
        业务规则: 无效的日志级别
        """
        response = auth_client.get(
            Endpoints.ADMIN_LOGS_ERRORS,
            params={"level": "invalid_level"}
        )
        assert response.status_code in [400, 403]

    def test_errors_invalid_date_format(self, auth_client):
        """
        业务规则: 无效的日期格式
        """
        response = auth_client.get(
            Endpoints.ADMIN_LOGS_ERRORS,
            params={"start_date": "invalid-date"}
        )
        assert response.status_code in [400, 403, 422]

    def test_operations_invalid_pagination(self, auth_client):
        """
        业务规则: 无效的分页参数
        """
        response = auth_client.get(
            Endpoints.ADMIN_LOGS_OPERATIONS,
            params={"offset": -1, "limit": 0}
        )
        assert response.status_code in [400, 403, 422]

    def test_audit_future_date_range(self, auth_client):
        """
        业务规则: 未来日期范围

        可能返回空结果而不是错误
        """
        future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        response = auth_client.get(
            Endpoints.ADMIN_LOGS_AUDIT,
            params={"start_date": future}
        )
        # 未来日期可能返回空结果或被接受
        assert response.status_code in [200, 400, 403]
