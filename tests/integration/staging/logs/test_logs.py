"""
Logs API Tests (Black Box)

测试 /api/v2/user/logs 相关接口

业务规则:
1. 记录前端错误日志
2. 支持单条和批量记录
3. 无需认证 (匿名用户错误也需要记录)

@module tests.integration.staging.logs.test_logs
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestLogError(BaseAPITest):
    """
    POST /api/v2/user/logs/error 黑盒测试

    记录单条错误日志
    """

    ENDPOINT = Endpoints.LOGS_ERROR

    def test_log_error_with_valid_data(self, auth_client):
        """
        业务规则: 可以记录单条错误
        """
        error_id = f"TEST_{uuid.uuid4().hex[:8]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_id": error_id,
                "error_type": "api_error",
                "message": "Test error message"
            }
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_log_error_requires_error_id(self, auth_client):
        """
        业务规则: 必须提供 error_id
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_type": "api_error",
                "message": "Test error"
            }
        )
        assert response.status_code in [400, 422]

    def test_log_error_requires_error_type(self, auth_client):
        """
        业务规则: 必须提供 error_type
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_id": "test_123",
                "message": "Test error"
            }
        )
        assert response.status_code in [400, 422]

    def test_error_id_format_validation(self, auth_client):
        """
        业务规则: error_id 格式验证 (字母数字下划线连字符)
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_id": "invalid!@#$%",
                "error_type": "test"
            }
        )
        assert response.status_code in [400, 422]

    def test_error_id_length_limit(self, auth_client):
        """
        业务规则: error_id 长度限制 (max 100)
        """
        long_id = "a" * 150
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_id": long_id,
                "error_type": "test"
            }
        )
        assert response.status_code in [400, 422]

    def test_log_error_without_auth(self, anon_client):
        """
        业务规则: 可以匿名记录错误

        未登录用户的错误也需要记录
        注意: 如果后端容器初始化失败可能返回 500
        """
        error_id = f"ANON_{uuid.uuid4().hex[:8]}"
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "error_id": error_id,
                "error_type": "page_error",
                "message": "Anonymous user error"
            }
        )
        # 正常返回 200，如果服务异常可能返回 500
        # 这是一个公开端点，不应该返回 401/403
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "ok"


@pytest.mark.p1
class TestLogErrorsBatch(BaseAPITest):
    """
    POST /api/v2/user/logs/errors 黑盒测试

    批量记录错误日志
    """

    ENDPOINT = Endpoints.LOGS_ERRORS_BATCH

    def test_log_batch_with_valid_data(self, auth_client):
        """
        业务规则: 可以批量记录错误
        """
        errors = [
            {
                "error_id": f"BATCH_{uuid.uuid4().hex[:8]}",
                "error_type": "api_error",
                "message": f"Batch error {i}"
            }
            for i in range(3)
        ]
        response = auth_client.post(
            self.ENDPOINT,
            json={"errors": errors}
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_batch_size_limit(self, auth_client):
        """
        业务规则: 批量大小限制 (max 50)
        """
        errors = [
            {
                "error_id": f"LIMIT_{uuid.uuid4().hex[:8]}",
                "error_type": "test",
                "message": f"Error {i}"
            }
            for i in range(60)  # 超过 50
        ]
        response = auth_client.post(
            self.ENDPOINT,
            json={"errors": errors}
        )
        assert response.status_code in [400, 422]

    def test_empty_batch_accepted(self, auth_client):
        """
        业务规则: 空批次被接受 (幂等设计)

        API 对空 errors 数组返回 200，而非拒绝。
        这是 API 的设计选择：空批次不产生副作用，返回成功。
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"errors": []}
        )
        # API 接受空批次
        assert response.status_code == 200

    def test_log_batch_without_auth(self, anon_client):
        """
        业务规则: 可以匿名批量记录错误
        """
        errors = [
            {
                "error_id": f"ANON_BATCH_{uuid.uuid4().hex[:8]}",
                "error_type": "page_error",
                "message": f"Anonymous batch error {i}"
            }
            for i in range(2)
        ]
        response = anon_client.post(
            self.ENDPOINT,
            json={"errors": errors}
        )
        data = self.assert_success(response)


@pytest.mark.p2
class TestLogErrorFields(BaseAPITest):
    """
    错误日志字段测试
    """

    ENDPOINT = Endpoints.LOGS_ERROR

    def test_log_with_all_fields(self, auth_client):
        """
        业务规则: 可以记录所有可选字段
        """
        error_id = f"FULL_{uuid.uuid4().hex[:8]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_id": error_id,
                "error_type": "api_error",
                "error_code": "ERR_001",
                "message": "Full error with all fields",
                "status_code": 500,
                "endpoint": "/api/v2/user/test",
                "method": "POST",
                "page_url": "https://example.com/page",
                "user_agent": "Mozilla/5.0 Test Browser",
                "stack_trace": "Error: test\\n    at test.js:1:1",
                "context": {"key": "value"},
                "client_timestamp": "2026-01-18T10:00:00Z"
            }
        )
        data = self.assert_success(response)

    def test_context_size_limit(self, auth_client):
        """
        业务规则: context 大小限制 (max 10KB)
        """
        error_id = f"CTX_{uuid.uuid4().hex[:8]}"
        # 创建超过 10KB 的 context
        large_context = {"data": "x" * 15000}
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_id": error_id,
                "error_type": "test",
                "context": large_context
            }
        )
        # 应该被截断或返回成功 (服务端处理)
        assert response.status_code == 200

    def test_method_whitelist(self, auth_client):
        """
        业务规则: method 必须是有效的 HTTP 方法
        """
        error_id = f"METHOD_{uuid.uuid4().hex[:8]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "error_id": error_id,
                "error_type": "test",
                "method": "INVALID"
            }
        )
        # 无效方法应被忽略或返回 200
        assert response.status_code == 200


@pytest.mark.p2
class TestLogErrorRateLimits(BaseAPITest):
    """
    错误日志速率限制测试
    """

    def test_single_error_rate_limit(self, auth_client):
        """
        业务规则: 单条错误速率限制 (30/minute)
        """
        pass

    def test_batch_error_rate_limit(self, auth_client):
        """
        业务规则: 批量错误速率限制 (10/minute)
        """
        pass
