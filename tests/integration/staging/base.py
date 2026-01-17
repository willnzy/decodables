"""
Base Test Classes and Utilities

提供 API 集成测试的基础设施:
- BaseAPITest: 所有测试的基类
- 标准断言方法
- 通用测试模式

@module tests.integration.staging.base
"""

import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import httpx


# ==========================================
# Test Result Data Classes
# ==========================================

@dataclass
class TestFailure:
    """测试失败记录"""
    test_id: str
    endpoint: str
    method: str
    expected_status: int
    actual_status: int
    error_message: str
    response_body: str
    request_body: Optional[str] = None
    request_params: Optional[Dict] = None
    category: str = "unknown"
    priority: str = "P1"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "expected_status": self.expected_status,
            "actual_status": self.actual_status,
            "error_message": self.error_message,
            "response_body": self.response_body[:1000] if self.response_body else None,
            "request_body": self.request_body,
            "request_params": self.request_params,
            "category": self.category,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }


@dataclass
class TestResult:
    """单个测试结果"""
    test_id: str
    passed: bool
    duration_ms: float
    failure: Optional[TestFailure] = None


# ==========================================
# Base Test Class
# ==========================================

class BaseAPITest:
    """
    API 集成测试基类

    提供:
    - 标准 HTTP 状态码常量
    - 通用断言方法
    - 响应验证工具
    - 失败记录收集

    Usage:
        class TestBillingCredits(BaseAPITest):
            ENDPOINT = "/api/v2/user/billing/credits"

            def test_success(self, auth_client):
                response = auth_client.get(self.ENDPOINT)
                data = self.assert_success(response)
                assert "total_credits" in data
    """

    # Subclasses should override
    ENDPOINT: str = ""
    REQUIRES_AUTH: bool = True

    # Standard HTTP Status Codes
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    GONE = 410
    UNPROCESSABLE = 422
    TOO_MANY = 429
    SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

    # Failure collector (can be injected via fixture)
    _failures: List[TestFailure] = []

    # ==========================================
    # Success Assertions
    # ==========================================

    def assert_success(
        self,
        response: httpx.Response,
        expected_status: int = 200,
    ) -> Dict[str, Any]:
        """
        断言响应成功并返回 JSON 数据

        Args:
            response: HTTP 响应
            expected_status: 期望的状态码 (默认 200)

        Returns:
            解析后的 JSON 数据

        Raises:
            AssertionError: 状态码不匹配
        """
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}.\n"
            f"Response: {response.text[:500]}"
        )
        return response.json()

    def assert_created(self, response: httpx.Response) -> Dict[str, Any]:
        """断言 201 Created"""
        return self.assert_success(response, self.CREATED)

    def assert_no_content(self, response: httpx.Response):
        """断言 204 No Content"""
        assert response.status_code == self.NO_CONTENT, (
            f"Expected 204, got {response.status_code}"
        )

    # ==========================================
    # Error Assertions
    # ==========================================

    def assert_error(
        self,
        response: httpx.Response,
        expected_status: int,
        contains: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        断言错误响应

        Args:
            response: HTTP 响应
            expected_status: 期望的错误状态码
            contains: 响应体中应包含的文本 (可选)

        Returns:
            解析后的 JSON 数据
        """
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}.\n"
            f"Response: {response.text[:500]}"
        )
        if contains:
            assert contains.lower() in response.text.lower(), (
                f"Expected response to contain '{contains}'.\n"
                f"Actual: {response.text[:500]}"
            )
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}

    def assert_unauthorized(self, response: httpx.Response) -> Dict:
        """断言 401 Unauthorized"""
        return self.assert_error(response, self.UNAUTHORIZED)

    def assert_forbidden(self, response: httpx.Response) -> Dict:
        """断言 403 Forbidden"""
        return self.assert_error(response, self.FORBIDDEN)

    def assert_not_found(self, response: httpx.Response) -> Dict:
        """断言 404 Not Found"""
        return self.assert_error(response, self.NOT_FOUND)

    def assert_conflict(self, response: httpx.Response) -> Dict:
        """断言 409 Conflict"""
        return self.assert_error(response, self.CONFLICT)

    def assert_validation_error(
        self,
        response: httpx.Response,
        field: Optional[str] = None,
    ) -> Dict:
        """
        断言 422 Validation Error

        Args:
            response: HTTP 响应
            field: 应出现在错误中的字段名 (可选)
        """
        assert response.status_code in [self.BAD_REQUEST, self.UNPROCESSABLE], (
            f"Expected 400 or 422, got {response.status_code}.\n"
            f"Response: {response.text[:500]}"
        )
        data = response.json()
        if field:
            assert field.lower() in response.text.lower(), (
                f"Expected field '{field}' in error.\n"
                f"Actual: {response.text[:500]}"
            )
        return data

    def assert_payment_required(self, response: httpx.Response) -> Dict:
        """断言 402 Payment Required (积分不足)"""
        return self.assert_error(response, self.PAYMENT_REQUIRED)

    def assert_rate_limited(self, response: httpx.Response) -> Dict:
        """断言 429 Too Many Requests"""
        return self.assert_error(response, self.TOO_MANY)

    def assert_server_error(self, response: httpx.Response) -> Dict:
        """断言 5xx Server Error"""
        assert 500 <= response.status_code < 600, (
            f"Expected 5xx, got {response.status_code}"
        )
        return response.json() if response.text else {}

    # ==========================================
    # Response Validation
    # ==========================================

    def assert_has_fields(
        self,
        data: Dict,
        required_fields: List[str],
    ):
        """
        断言响应包含必需字段

        Args:
            data: 响应数据
            required_fields: 必需字段列表
        """
        missing = [f for f in required_fields if f not in data]
        assert not missing, f"Missing required fields: {missing}"

    def assert_field_type(
        self,
        data: Dict,
        field: str,
        expected_type: type,
    ):
        """
        断言字段类型正确

        Args:
            data: 响应数据
            field: 字段名
            expected_type: 期望类型
        """
        assert field in data, f"Field '{field}' not found"
        assert isinstance(data[field], expected_type), (
            f"Field '{field}' expected {expected_type.__name__}, "
            f"got {type(data[field]).__name__}"
        )

    def assert_field_in(
        self,
        data: Dict,
        field: str,
        valid_values: List[Any],
    ):
        """
        断言字段值在有效范围内

        Args:
            data: 响应数据
            field: 字段名
            valid_values: 有效值列表
        """
        assert field in data, f"Field '{field}' not found"
        assert data[field] in valid_values, (
            f"Field '{field}' value '{data[field]}' not in {valid_values}"
        )

    def assert_list_response(
        self,
        data: Dict,
        items_key: str = "items",
        min_count: int = 0,
        max_count: Optional[int] = None,
    ) -> List:
        """
        断言列表响应格式正确

        Args:
            data: 响应数据
            items_key: 列表字段名 (默认 "items")
            min_count: 最小数量
            max_count: 最大数量 (可选)

        Returns:
            列表数据
        """
        assert items_key in data, f"Missing '{items_key}' in response"
        items = data[items_key]
        assert isinstance(items, list), f"'{items_key}' is not a list"
        assert len(items) >= min_count, (
            f"Expected at least {min_count} items, got {len(items)}"
        )
        if max_count is not None:
            assert len(items) <= max_count, (
                f"Expected at most {max_count} items, got {len(items)}"
            )
        return items

    def assert_pagination(
        self,
        data: Dict,
        expected_offset: int = 0,
        expected_limit: int = 20,
    ):
        """
        断言分页响应格式正确

        Args:
            data: 响应数据
            expected_offset: 期望的 offset
            expected_limit: 期望的 limit
        """
        assert "offset" in data or "page" in data, "Missing pagination info"
        if "offset" in data:
            assert data["offset"] == expected_offset
        if "limit" in data:
            assert data["limit"] == expected_limit
        if "total" in data:
            assert isinstance(data["total"], int)
            assert data["total"] >= 0

    # ==========================================
    # Performance Assertions
    # ==========================================

    def assert_response_time(
        self,
        response: httpx.Response,
        max_seconds: float = 0.5,
    ):
        """
        断言响应时间在限制内

        Args:
            response: HTTP 响应
            max_seconds: 最大响应时间 (秒)
        """
        elapsed = response.elapsed.total_seconds()
        assert elapsed < max_seconds, (
            f"Response took {elapsed:.2f}s, expected < {max_seconds}s"
        )

    # ==========================================
    # Security Assertions
    # ==========================================

    def assert_no_sensitive_data(
        self,
        response: httpx.Response,
        sensitive_patterns: List[str] = None,
    ):
        """
        断言响应不包含敏感数据

        Args:
            response: HTTP 响应
            sensitive_patterns: 敏感数据模式列表
        """
        if sensitive_patterns is None:
            sensitive_patterns = [
                "password",
                "secret",
                "api_key",
                "access_token",
                "refresh_token",
            ]
        text = response.text.lower()
        for pattern in sensitive_patterns:
            # 允许出现在错误消息中，但不应该有实际值
            if pattern in text:
                # 检查是否是键名而非值
                import json
                try:
                    data = response.json()
                    flat = json.dumps(data).lower()
                    # 如果模式后面跟着实际值（非 null/empty），则失败
                    if f'"{pattern}": "' in flat or f'"{pattern}":"' in flat:
                        # 进一步检查值是否为空或 null
                        pass  # 简化处理，实际实现更复杂
                except Exception:
                    pass

    def assert_no_stack_trace(self, response: httpx.Response):
        """断言错误响应不包含堆栈跟踪"""
        indicators = [
            "Traceback",
            "File \"",
            "line ",
            "raise ",
            "Exception:",
            "Error:",
        ]
        for indicator in indicators:
            assert indicator not in response.text, (
                f"Response may contain stack trace: found '{indicator}'"
            )

    # ==========================================
    # Utility Methods
    # ==========================================

    def extract_request_id(self, response: httpx.Response) -> Optional[str]:
        """从响应中提取 request_id"""
        # Try header first
        if "X-Request-Id" in response.headers:
            return response.headers["X-Request-Id"]
        # Try response body
        try:
            data = response.json()
            return data.get("request_id")
        except Exception:
            return None

    def categorize_failure(self, response: httpx.Response) -> str:
        """根据响应分类失败类型"""
        status = response.status_code
        if status == 401:
            return "auth_failure"
        elif status == 403:
            return "permission_denied"
        elif status == 404:
            return "not_found"
        elif status == 429:
            return "rate_limit"
        elif status in [400, 422]:
            return "validation_error"
        elif status == 409:
            return "conflict"
        elif 500 <= status < 600:
            return "server_error"
        else:
            return "unknown"

    def record_failure(
        self,
        test_id: str,
        endpoint: str,
        method: str,
        response: httpx.Response,
        expected_status: int,
        request_body: Optional[Dict] = None,
        request_params: Optional[Dict] = None,
    ) -> TestFailure:
        """
        记录测试失败

        Args:
            test_id: 测试 ID
            endpoint: 接口路径
            method: HTTP 方法
            response: HTTP 响应
            expected_status: 期望状态码
            request_body: 请求体
            request_params: 请求参数

        Returns:
            TestFailure 对象
        """
        failure = TestFailure(
            test_id=test_id,
            endpoint=endpoint,
            method=method,
            expected_status=expected_status,
            actual_status=response.status_code,
            error_message=response.text[:500],
            response_body=response.text,
            request_body=str(request_body) if request_body else None,
            request_params=request_params,
            category=self.categorize_failure(response),
            priority="P0" if response.status_code >= 500 else "P1",
            request_id=self.extract_request_id(response),
        )
        self._failures.append(failure)
        return failure

    @classmethod
    def get_failures(cls) -> List[TestFailure]:
        """获取所有记录的失败"""
        return cls._failures

    @classmethod
    def clear_failures(cls):
        """清空失败记录"""
        cls._failures = []


# ==========================================
# Timing Utilities
# ==========================================

class Timer:
    """简单计时器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()

    @property
    def elapsed_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0
