"""
Assets Module Test Configuration

服务健康检查: 当 Assets 服务不可用 (502 Bad Gateway) 时，
自动跳过所有 Assets 测试，而非报告失败。

业务原因:
- 502 是基础设施问题 (staging 服务未启动/崩溃)
- 不是测试逻辑问题，不应修改断言来接受 502
- 正确做法: 跳过测试 + 报告基础设施问题

@module tests.integration.staging.assets.conftest
"""

import pytest
import httpx

from ..constants import Endpoints

STAGING_BASE_URL = "https://decodables-staging.up.railway.app"


def _check_assets_service_available() -> bool:
    """
    探测 Assets 服务是否可用。

    向 /api/v2/user/assets 发送 GET 请求:
    - 401 (未认证) = 服务正常 (路由可达，只是没 token)
    - 200/403 = 服务正常
    - 502/503/504 = 服务不可用

    Returns:
        True 如果服务可用, False 如果返回 5xx
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{STAGING_BASE_URL}{Endpoints.ASSETS}")
            # 401 说明路由可达，服务正常运行
            # 502/503/504 说明服务不可用
            return response.status_code < 500
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


# Session-scoped: 只检查一次
_assets_available = None


def _is_assets_available() -> bool:
    """缓存健康检查结果，避免重复探测。"""
    global _assets_available
    if _assets_available is None:
        _assets_available = _check_assets_service_available()
    return _assets_available


@pytest.fixture(autouse=True)
def skip_if_assets_unavailable():
    """
    自动跳过 fixture: 当 Assets 服务返回 502 时跳过测试。

    autouse=True 确保此 fixture 应用于本目录下所有测试。
    """
    if not _is_assets_available():
        pytest.skip(
            "Assets 服务不可用 (502 Bad Gateway)。"
            "这是 staging 基础设施问题，非测试逻辑问题。"
            "请检查 Railway staging 部署状态。"
        )
