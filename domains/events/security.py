"""
Events Domain Security Module
事件领域安全模块

提供输入验证、数据脱敏、SQL注入防护等安全功能

@module domains.events.security
@version 1.0.0 (created for v3.27 security enhancement)
"""

import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 敏感字段列表
SENSITIVE_KEYS = {
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token", "api_key", "secret", "private_key",
    "credit_card", "card_number", "cvv", "ssn",
    "email", "phone", "address"
}

# SQL 注入危险模式
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
    r"(--|;|/\*|\*/|xp_|sp_)",
    r"('|(\\'))",  # Single quotes
]

# XSS 危险模式
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",  # onclick=, onload=, etc.
]


def sanitize_sql_input(value: str) -> str:
    """
    防止 SQL 注入攻击的输入清理

    Args:
        value: 用户输入字符串

    Returns:
        清理后的安全字符串

    Raises:
        ValueError: 如果输入包含危险模式
    """
    if not isinstance(value, str):
        return value

    # 检查 SQL 注入模式
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"[Security] SQL injection attempt detected: {value[:50]}")
            raise ValueError(f"Invalid input: potential SQL injection detected")

    return value


def sanitize_xss_input(value: str) -> str:
    """
    防止 XSS 攻击的输入清理

    Args:
        value: 用户输入字符串

    Returns:
        清理后的安全字符串

    Raises:
        ValueError: 如果输入包含危险模式
    """
    if not isinstance(value, str):
        return value

    # 检查 XSS 模式
    for pattern in XSS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"[Security] XSS attempt detected: {value[:50]}")
            raise ValueError(f"Invalid input: potential XSS attack detected")

    return value


def sanitize_event_data(event_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    脱敏 event_data 中的敏感信息

    Args:
        event_data: 事件数据字典

    Returns:
        脱敏后的事件数据

    Examples:
        >>> sanitize_event_data({"email": "user@example.com", "page": "/home"})
        {"email": "u***@example.com", "page": "/home"}

        >>> sanitize_event_data({"password": "secret123"})
        {"password": "***"}
    """
    if event_data is None:
        return None

    if not isinstance(event_data, dict):
        return event_data

    sanitized = {}

    for key, value in event_data.items():
        key_lower = key.lower()

        # 完全隐藏的敏感字段
        if any(sensitive in key_lower for sensitive in ["password", "token", "secret", "key", "cvv", "ssn"]):
            sanitized[key] = "***"

        # 部分隐藏的字段 (email, phone)
        elif "email" in key_lower and isinstance(value, str) and "@" in value:
            # user@example.com → u***@example.com
            parts = value.split("@")
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                masked_username = username[0] + "***" if len(username) > 0 else "***"
                sanitized[key] = f"{masked_username}@{domain}"
            else:
                sanitized[key] = "***"

        elif "phone" in key_lower and isinstance(value, str):
            # 13912345678 → 139****5678
            if len(value) >= 8:
                sanitized[key] = value[:3] + "****" + value[-4:]
            else:
                sanitized[key] = "***"

        elif "card" in key_lower and isinstance(value, str):
            # 1234567890123456 → 1234 **** **** 3456
            if len(value) >= 8:
                sanitized[key] = value[:4] + " **** **** " + value[-4:]
            else:
                sanitized[key] = "***"

        # 递归处理嵌套字典
        elif isinstance(value, dict):
            sanitized[key] = sanitize_event_data(value)

        # 其他字段保持原样
        else:
            sanitized[key] = value

    return sanitized


def validate_user_id(user_id: str) -> str:
    """
    验证 user_id 格式

    Args:
        user_id: 用户ID

    Returns:
        验证后的 user_id

    Raises:
        ValueError: 如果格式无效
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")

    # 检查长度
    if len(user_id) > 255:
        raise ValueError("user_id too long (max 255 characters)")

    # 检查 SQL 注入
    user_id = sanitize_sql_input(user_id)

    # 检查格式 (允许字母、数字、下划线、连字符)
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        raise ValueError("user_id contains invalid characters (allowed: a-zA-Z0-9_-)")

    return user_id


def validate_event_type(event_type: str) -> str:
    """
    验证 event_type 格式

    Args:
        event_type: 事件类型

    Returns:
        验证后的 event_type

    Raises:
        ValueError: 如果格式无效
    """
    if not event_type or not isinstance(event_type, str):
        raise ValueError("event_type must be a non-empty string")

    # 检查长度
    if len(event_type) > 100:
        raise ValueError("event_type too long (max 100 characters)")

    # 检查 SQL 注入
    event_type = sanitize_sql_input(event_type)

    # 检查格式 (允许字母、数字、下划线、连字符、点号)
    if not re.match(r'^[a-zA-Z0-9_.-]+$', event_type):
        raise ValueError("event_type contains invalid characters (allowed: a-zA-Z0-9_.-)")

    return event_type


def sanitize_audit_details(details: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    脱敏审计日志详情

    Args:
        details: 审计详情字典

    Returns:
        脱敏后的审计详情
    """
    if details is None:
        return None

    if not isinstance(details, dict):
        return details

    # 对审计日志也进行脱敏
    return sanitize_event_data(details)


# Security validation wrapper
def validate_and_sanitize(
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    一次性验证和脱敏所有输入

    Args:
        user_id: 用户ID
        event_type: 事件类型
        event_data: 事件数据

    Returns:
        (validated_user_id, validated_event_type, sanitized_event_data)

    Raises:
        ValueError: 如果任何输入无效
    """
    validated_user_id = validate_user_id(user_id) if user_id else None
    validated_event_type = validate_event_type(event_type) if event_type else None
    sanitized_data = sanitize_event_data(event_data) if event_data else None

    return validated_user_id, validated_event_type, sanitized_data
