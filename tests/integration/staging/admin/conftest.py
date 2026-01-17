"""
Admin API Test Fixtures

管理员 API 测试专用 fixtures

业务规则:
1. 管理员接口需要 admin 权限认证
2. 部分接口支持普通用户访问 (如 feature-flags/client/flags)
3. 所有管理员操作都有审计日志

@module tests.integration.staging.admin.conftest
"""

import pytest

# Admin 测试使用 staging/conftest.py 中定义的 auth_client 和 anon_client
# 这里可以添加 admin 特定的 fixtures

# 注意: 由于是黑盒测试，我们使用现有的认证用户
# 如果该用户不是 admin，API 会返回 403
# 这是预期的测试行为，用于验证权限控制


@pytest.fixture
def test_user_id():
    """测试用的用户 ID (非真实 admin)"""
    return "user_test_12345"


@pytest.fixture
def test_campaign_id():
    """测试用的营销活动 ID"""
    return "campaign_test_12345"


@pytest.fixture
def test_theme_id():
    """测试用的主题 ID"""
    return "theme_test_12345"


@pytest.fixture
def test_flag_key():
    """测试用的 Feature Flag key"""
    return "test_flag_key_12345"


@pytest.fixture
def test_listing_id():
    """测试用的 Marketplace listing ID"""
    return "listing_test_12345"


@pytest.fixture
def test_report_id():
    """测试用的举报 ID"""
    return "report_test_12345"
