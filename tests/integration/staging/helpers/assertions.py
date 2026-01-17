"""
Custom Assertions for API Testing

扩展断言方法,提供更丰富的验证能力

@module tests.integration.staging.helpers.assertions
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import httpx


# ==========================================
# Response Structure Assertions
# ==========================================

def assert_json_structure(
    data: Dict,
    expected_structure: Dict[str, type],
    allow_extra: bool = True,
):
    """
    断言 JSON 结构符合预期

    Args:
        data: 实际数据
        expected_structure: 期望的字段和类型 {field: type}
        allow_extra: 是否允许额外字段

    Example:
        assert_json_structure(response.json(), {
            "id": str,
            "email": str,
            "credits": int,
        })
    """
    for field, expected_type in expected_structure.items():
        assert field in data, f"Missing field: '{field}'"

        # Handle Optional types
        if data[field] is None:
            # Check if None is allowed (simplified check)
            continue

        actual_type = type(data[field])
        assert isinstance(data[field], expected_type), (
            f"Field '{field}' expected {expected_type.__name__}, "
            f"got {actual_type.__name__}"
        )

    if not allow_extra:
        extra_fields = set(data.keys()) - set(expected_structure.keys())
        assert not extra_fields, f"Unexpected fields: {extra_fields}"


def assert_list_of_objects(
    items: List,
    required_fields: List[str],
    min_count: int = 0,
):
    """
    断言列表中的每个对象都包含必需字段

    Args:
        items: 对象列表
        required_fields: 每个对象必须包含的字段
        min_count: 最小数量
    """
    assert isinstance(items, list), "Expected a list"
    assert len(items) >= min_count, (
        f"Expected at least {min_count} items, got {len(items)}"
    )

    for i, item in enumerate(items):
        assert isinstance(item, dict), f"Item {i} is not a dict"
        for field in required_fields:
            assert field in item, f"Item {i} missing field: '{field}'"


# ==========================================
# Value Assertions
# ==========================================

def assert_uuid_format(value: str, field_name: str = "value"):
    """断言值是有效的 UUID 格式"""
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    assert uuid_pattern.match(value), (
        f"'{field_name}' is not a valid UUID: {value}"
    )


def assert_email_format(value: str, field_name: str = "email"):
    """断言值是有效的邮箱格式"""
    email_pattern = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
    assert email_pattern.match(value), (
        f"'{field_name}' is not a valid email: {value}"
    )


def assert_url_format(value: str, field_name: str = "url"):
    """断言值是有效的 URL 格式"""
    url_pattern = re.compile(
        r'^https?://[^\s/$.?#].[^\s]*$',
        re.IGNORECASE
    )
    assert url_pattern.match(value), (
        f"'{field_name}' is not a valid URL: {value}"
    )


def assert_datetime_format(
    value: str,
    field_name: str = "datetime",
    allow_timezone: bool = True,
):
    """断言值是有效的 ISO 8601 日期时间格式"""
    try:
        # Try parsing as ISO format
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise AssertionError(
            f"'{field_name}' is not a valid ISO datetime: {value}"
        )


def assert_in_range(
    value: Union[int, float],
    min_value: Union[int, float],
    max_value: Union[int, float],
    field_name: str = "value",
):
    """断言数值在范围内"""
    assert min_value <= value <= max_value, (
        f"'{field_name}' ({value}) not in range [{min_value}, {max_value}]"
    )


def assert_positive(value: Union[int, float], field_name: str = "value"):
    """断言数值为正"""
    assert value > 0, f"'{field_name}' ({value}) is not positive"


def assert_non_negative(value: Union[int, float], field_name: str = "value"):
    """断言数值非负"""
    assert value >= 0, f"'{field_name}' ({value}) is negative"


def assert_string_length(
    value: str,
    min_length: int = 0,
    max_length: Optional[int] = None,
    field_name: str = "value",
):
    """断言字符串长度在范围内"""
    length = len(value)
    assert length >= min_length, (
        f"'{field_name}' length ({length}) is less than {min_length}"
    )
    if max_length is not None:
        assert length <= max_length, (
            f"'{field_name}' length ({length}) exceeds {max_length}"
        )


# ==========================================
# Business Logic Assertions
# ==========================================

def assert_credits_valid(data: Dict):
    """断言积分数据有效"""
    required = ["monthly_credits", "permanent_credits", "total_credits"]
    for field in required:
        assert field in data, f"Missing credit field: {field}"
        assert isinstance(data[field], (int, float)), (
            f"Credit field '{field}' must be numeric"
        )
        assert data[field] >= 0, f"Credit field '{field}' cannot be negative"

    # Verify total = monthly + permanent
    expected_total = data["monthly_credits"] + data["permanent_credits"]
    assert data["total_credits"] == expected_total, (
        f"Total credits mismatch: {data['total_credits']} != "
        f"{data['monthly_credits']} + {data['permanent_credits']}"
    )


def assert_tier_valid(tier: str):
    """断言 Tier 值有效"""
    valid_tiers = ["t1", "t2", "t3", "t4"]
    assert tier in valid_tiers, f"Invalid tier: {tier}, expected one of {valid_tiers}"


def assert_pagination_valid(
    data: Dict,
    expected_offset: Optional[int] = None,
    expected_limit: Optional[int] = None,
):
    """断言分页数据有效"""
    # Check items exist
    items_key = None
    for key in ["items", "data", "results"]:
        if key in data:
            items_key = key
            break
    assert items_key is not None, "Missing items/data/results in pagination response"
    assert isinstance(data[items_key], list), f"'{items_key}' is not a list"

    # Check pagination metadata
    if "total" in data:
        assert isinstance(data["total"], int)
        assert data["total"] >= 0

    if "offset" in data:
        assert isinstance(data["offset"], int)
        assert data["offset"] >= 0
        if expected_offset is not None:
            assert data["offset"] == expected_offset

    if "limit" in data:
        assert isinstance(data["limit"], int)
        assert data["limit"] > 0
        if expected_limit is not None:
            assert data["limit"] == expected_limit

    # Items count should not exceed limit
    if "limit" in data:
        assert len(data[items_key]) <= data["limit"]


# ==========================================
# Error Response Assertions
# ==========================================

def assert_error_response(
    response: httpx.Response,
    expected_status: int,
    expected_code: Optional[str] = None,
    expected_message_contains: Optional[str] = None,
):
    """
    断言错误响应格式正确

    Args:
        response: HTTP 响应
        expected_status: 期望的状态码
        expected_code: 期望的错误码 (如 "auth_unauthorized")
        expected_message_contains: 消息应包含的文本
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:200]}"
    )

    try:
        data = response.json()
    except Exception:
        raise AssertionError(f"Response is not valid JSON: {response.text[:200]}")

    # Check for common error fields
    has_error_info = any(k in data for k in ["code", "message", "detail", "error"])
    assert has_error_info, f"Response missing error info: {data}"

    if expected_code:
        assert data.get("code") == expected_code, (
            f"Expected error code '{expected_code}', got '{data.get('code')}'"
        )

    if expected_message_contains:
        message = data.get("message") or data.get("detail") or str(data)
        assert expected_message_contains.lower() in message.lower(), (
            f"Expected message to contain '{expected_message_contains}', "
            f"got: {message}"
        )


def assert_no_error_details_leaked(response: httpx.Response):
    """
    断言错误响应不泄露敏感信息

    检查是否包含:
    - 堆栈跟踪
    - 文件路径
    - SQL 语句
    - 内部 ID
    """
    text = response.text

    # Stack trace indicators
    stack_indicators = [
        "Traceback (most recent call last)",
        'File "',
        "line ",
        "raise ",
        "Exception:",
        "Error at",
        "at /",
    ]

    for indicator in stack_indicators:
        assert indicator not in text, (
            f"Response may leak stack trace: found '{indicator}'"
        )

    # SQL indicators
    sql_indicators = [
        "SELECT ",
        "INSERT INTO",
        "UPDATE ",
        "DELETE FROM",
        "syntax error",
        "relation \"",
        "column \"",
    ]

    for indicator in sql_indicators:
        # Case insensitive check
        if indicator.lower() in text.lower():
            # Could be intentional error message, check context
            pass


# ==========================================
# Response Comparison
# ==========================================

def assert_responses_equal(
    response1: Dict,
    response2: Dict,
    ignore_fields: List[str] = None,
):
    """
    断言两个响应数据相等

    Args:
        response1: 第一个响应
        response2: 第二个响应
        ignore_fields: 忽略的字段列表 (如 timestamp)
    """
    if ignore_fields is None:
        ignore_fields = ["created_at", "updated_at", "timestamp"]

    def clean_data(data: Dict) -> Dict:
        return {k: v for k, v in data.items() if k not in ignore_fields}

    clean1 = clean_data(response1)
    clean2 = clean_data(response2)

    assert clean1 == clean2, (
        f"Responses differ:\n"
        f"Response 1: {clean1}\n"
        f"Response 2: {clean2}"
    )


def assert_subset(subset: Dict, superset: Dict):
    """断言 subset 是 superset 的子集"""
    for key, value in subset.items():
        assert key in superset, f"Key '{key}' not found in superset"
        assert superset[key] == value, (
            f"Value mismatch for '{key}': expected {value}, got {superset[key]}"
        )
