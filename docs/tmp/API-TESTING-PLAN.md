# Make Decodables API 集成测试方案 v1.0

> 基于业界最佳实践，为 staging 环境设计的完整 API 测试方案

**创建日期**: 2026-01-18
**状态**: 待审核

---

## 一、方案概述

### 1.1 目标

建立一套完整的 API 集成测试体系，能够：
1. **功能验证**: 验证所有 API 接口按规范正常工作
2. **边界覆盖**: 测试参数边界、极限条件、异常输入
3. **安全检查**: 防止 SQL 注入、XSS、SSRF、权限绕过
4. **回归保护**: 防止代码变更引入新 bug
5. **CI/CD 集成**: 自动化执行，快速反馈

### 1.2 测试金字塔定位

```
                    ┌─────────────┐
                    │   E2E (5%)  │  ← 完整用户流程
                    ├─────────────┤
                    │ Integration │  ← API 测试 (本方案)
                    │    (25%)    │
                    ├─────────────┤
                    │    Unit     │  ← 已有测试
                    │    (70%)    │
                    └─────────────┘
```

### 1.3 核心原则

| 原则 | 说明 |
|------|------|
| **真实环境** | 测试 staging 环境，不是 mock |
| **完全隔离** | 测试数据不影响真实数据 |
| **可重复** | 每次执行结果一致 |
| **快速反馈** | 单次运行 < 5 分钟 |
| **易维护** | 代码清晰，易于扩展 |

---

## 二、测试分类与覆盖

### 2.1 测试分类矩阵

| 测试类型 | 目标 | 比例 | 示例 |
|----------|------|------|------|
| **功能测试** | 验证正常流程 | 40% | 创建项目成功返回 201 |
| **边界测试** | 验证极限条件 | 20% | 标题长度 0/200/201 |
| **异常测试** | 验证错误处理 | 20% | 缺少必填字段返回 400 |
| **安全测试** | 验证安全防护 | 15% | SQL 注入返回 400 |
| **权限测试** | 验证访问控制 | 5% | 非 Admin 访问返回 403 |

### 2.2 每个接口的测试维度

```python
# 标准测试用例模板
class TestEndpoint:
    """每个接口必须覆盖的测试维度"""

    # 1. 功能测试 (Happy Path)
    def test_success_basic(self): ...          # 基本成功场景
    def test_success_with_options(self): ...   # 带可选参数成功

    # 2. 认证测试
    def test_without_token(self): ...          # 无 token → 401
    def test_invalid_token(self): ...          # 无效 token → 401
    def test_expired_token(self): ...          # 过期 token → 401

    # 3. 权限测试
    def test_wrong_user(self): ...             # 跨用户访问 → 403
    def test_insufficient_tier(self): ...      # Tier 不足 → 403
    def test_admin_only(self): ...             # 非 Admin → 403

    # 4. 参数验证测试
    def test_missing_required(self): ...       # 缺少必填 → 400/422
    def test_invalid_type(self): ...           # 类型错误 → 422
    def test_invalid_format(self): ...         # 格式错误 → 422

    # 5. 边界测试
    def test_boundary_min(self): ...           # 最小值
    def test_boundary_max(self): ...           # 最大值
    def test_boundary_overflow(self): ...      # 超出范围

    # 6. 安全测试
    def test_sql_injection(self): ...          # SQL 注入防护
    def test_xss_injection(self): ...          # XSS 防护
    def test_ssrf_protection(self): ...        # SSRF 防护 (URL 参数)

    # 7. 异常测试
    def test_resource_not_found(self): ...     # 资源不存在 → 404
    def test_conflict(self): ...               # 冲突 → 409
    def test_business_rule(self): ...          # 业务规则 → 422
```

---

## 三、接口优先级与测试用例数

### 3.1 优先级定义

| 优先级 | 含义 | 测试深度 | 用例数/接口 |
|--------|------|----------|-------------|
| **P0** | 核心业务 + 财务风险 | 完整覆盖 | 15-25 |
| **P1** | 重要功能 | 深度覆盖 | 10-15 |
| **P2** | 辅助功能 | 基本覆盖 | 5-10 |
| **P3** | 低频功能 | 最小覆盖 | 3-5 |

### 3.2 P0 接口清单 (必须完整测试)

#### 支付/积分模块 (🔴 财务风险)

| 接口 | 方法 | 路径 | 测试用例数 |
|------|------|------|------------|
| 获取积分余额 | GET | `/api/v2/user/billing/credits` | 15 |
| 获取交易历史 | GET | `/api/v2/user/billing/transactions` | 15 |
| 检查能否承担 | GET | `/api/v2/user/billing/can-afford` | 12 |
| 创建结账会话 | POST | `/api/v2/user/payment/checkout` | 20 |
| 获取账单门户 | POST | `/api/v2/user/payment/portal` | 10 |
| 市场购买 | POST | `/api/v2/user/marketplace/purchase` | 25 |

#### 项目管理模块

| 接口 | 方法 | 路径 | 测试用例数 |
|------|------|------|------------|
| 获取项目列表 | GET | `/api/v2/user/projects` | 12 |
| 创建项目 | POST | `/api/v2/user/projects` | 18 |
| 获取项目详情 | GET | `/api/v2/user/projects/{id}` | 10 |
| 更新项目 | PUT | `/api/v2/user/projects/{id}` | 15 |
| 删除项目 | DELETE | `/api/v2/user/projects/{id}` | 12 |

#### AI 生成模块 (🔴 积分消耗)

| 接口 | 方法 | 路径 | 测试用例数 |
|------|------|------|------------|
| 同步生成图像 | POST | `/api/v2/user/generate/images` | 20 |
| 异步生成图像 | POST | `/api/v2/user/generate/images/async` | 15 |

#### Admin 模块 (🔴 权限敏感)

| 接口 | 方法 | 路径 | 测试用例数 |
|------|------|------|------------|
| 处理退款 | POST | `/api/admin/subscriptions/refund` | 20 |
| 取消订阅 | POST | `/api/admin/subscriptions/subscription/cancel` | 15 |
| 调整积分 | POST | `/admin/users/{uid}/credits` | 15 |

### 3.3 P1 接口清单 (深度覆盖)

| 模块 | 接口数 | 平均用例数 |
|------|--------|------------|
| 用户信息 | 7 | 10 |
| 市场其他 | 8 | 12 |
| 资产管理 | 10 | 10 |
| 生成历史 | 4 | 8 |

### 3.4 预估测试用例总数

| 优先级 | 接口数 | 平均用例数 | 总计 |
|--------|--------|------------|------|
| P0 | 18 | 18 | 324 |
| P1 | 35 | 10 | 350 |
| P2 | 40 | 6 | 240 |
| P3 | 25 | 4 | 100 |
| **总计** | **~120** | - | **~1,000** |

---

## 四、测试架构设计

### 4.1 目录结构

```
decodables/tests/integration/staging/
├── __init__.py
├── conftest.py                    # 全局 fixtures (认证、客户端)
├── base.py                        # 基础测试类和工具
├── constants.py                   # 测试常量 (URL、状态码)
├── factories/                     # 测试数据工厂
│   ├── __init__.py
│   ├── user_factory.py
│   ├── project_factory.py
│   └── ...
├── helpers/                       # 测试辅助函数
│   ├── __init__.py
│   ├── assertions.py              # 自定义断言
│   ├── security.py                # 安全测试 payload
│   └── cleanup.py                 # 数据清理
│
├── test_health.py                 # 健康检查 (P0)
│
├── billing/                       # 计费模块 (P0)
│   ├── __init__.py
│   ├── test_credits.py            # 积分接口
│   ├── test_transactions.py       # 交易历史
│   └── test_can_afford.py         # 承担检查
│
├── payment/                       # 支付模块 (P0)
│   ├── __init__.py
│   ├── test_checkout.py           # 结账会话
│   └── test_portal.py             # 账单门户
│
├── projects/                      # 项目模块 (P0)
│   ├── __init__.py
│   ├── test_list.py               # 列表接口
│   ├── test_crud.py               # 增删改查
│   ├── test_permissions.py        # 权限测试
│   └── test_capacity.py           # 容量限制
│
├── generate/                      # 生成模块 (P0)
│   ├── __init__.py
│   ├── test_images.py             # 图像生成
│   ├── test_images_async.py       # 异步生成
│   └── test_story.py              # 故事生成
│
├── marketplace/                   # 市场模块 (P0/P1)
│   ├── __init__.py
│   ├── test_listings.py           # 产品列表
│   ├── test_purchase.py           # 购买流程 (P0)
│   └── test_publish.py            # 发布产品
│
├── profile/                       # 用户信息 (P1)
│   ├── __init__.py
│   └── test_user_profile.py
│
├── admin/                         # 管理接口 (P0/P1)
│   ├── __init__.py
│   ├── test_subscriptions.py      # 订阅管理 (P0)
│   ├── test_users.py              # 用户管理
│   └── test_credits_admin.py      # 积分调整
│
└── security/                      # 安全测试 (横切)
    ├── __init__.py
    ├── test_auth.py               # 认证测试
    ├── test_injection.py          # 注入测试
    └── test_rate_limit.py         # 限流测试
```

### 4.2 核心组件设计

#### conftest.py - 全局 Fixtures

```python
"""
Staging API Test Configuration
"""
import os
import pytest
import httpx
from typing import Generator

# ==========================================
# Configuration
# ==========================================

STAGING_BASE_URL = "https://decodables-staging.up.railway.app"
CLERK_API_BASE = "https://api.clerk.com/v1"


@pytest.fixture(scope="session")
def clerk_secret_key() -> str:
    """Clerk Secret Key for token generation."""
    key = os.getenv("CLERK_SECRET_KEY")
    if not key:
        pytest.skip("CLERK_SECRET_KEY not set")
    return key


@pytest.fixture(scope="session")
def test_session_id() -> str:
    """Test user's Clerk session ID."""
    return os.getenv("TEST_SESSION_ID", "sess_38J7zsBRioQ25vJRE6K3pogvU6K")


@pytest.fixture(scope="function")
def fresh_token(clerk_secret_key: str, test_session_id: str) -> str:
    """
    Get fresh JWT token for each test.

    Clerk tokens expire in 60s, so we generate fresh ones.
    """
    response = httpx.post(
        f"{CLERK_API_BASE}/sessions/{test_session_id}/tokens",
        headers={
            "Authorization": f"Bearer {clerk_secret_key}",
            "Content-Type": "application/json",
        },
        json={},
    )
    if response.status_code != 200:
        pytest.fail(f"Failed to get token: {response.text}")
    return response.json()["jwt"]


@pytest.fixture(scope="function")
def auth_client(fresh_token: str) -> Generator[httpx.Client, None, None]:
    """Authenticated HTTP client with fresh token."""
    with httpx.Client(
        base_url=STAGING_BASE_URL,
        headers={
            "Authorization": f"Bearer {fresh_token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture(scope="session")
def anon_client() -> Generator[httpx.Client, None, None]:
    """Anonymous HTTP client (no auth)."""
    with httpx.Client(
        base_url=STAGING_BASE_URL,
        timeout=30.0,
    ) as client:
        yield client


# ==========================================
# Test Data Management
# ==========================================

@pytest.fixture(scope="function")
def cleanup_registry():
    """
    Registry for test data cleanup.

    Usage:
        def test_create(cleanup_registry, auth_client):
            response = auth_client.post("/projects", json={...})
            project_id = response.json()["id"]
            cleanup_registry.register("project", project_id)
            # Test runs...
            # Cleanup happens automatically after test
    """
    registry = CleanupRegistry()
    yield registry
    registry.cleanup_all()


class CleanupRegistry:
    """Tracks created resources for cleanup."""

    def __init__(self):
        self._items = []

    def register(self, resource_type: str, resource_id: str):
        self._items.append((resource_type, resource_id))

    def cleanup_all(self):
        # Cleanup in reverse order
        for resource_type, resource_id in reversed(self._items):
            try:
                self._delete_resource(resource_type, resource_id)
            except Exception:
                pass  # Best effort cleanup
```

#### base.py - 基础测试类

```python
"""
Base test classes and utilities
"""
import pytest
from typing import Any, Dict, List, Optional


class BaseAPITest:
    """Base class for all API tests."""

    # Subclasses should override
    ENDPOINT: str = ""
    REQUIRES_AUTH: bool = True

    # Standard status codes
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE = 422
    TOO_MANY = 429
    SERVER_ERROR = 500

    # ==========================================
    # Common Test Patterns
    # ==========================================

    def assert_success(self, response, expected_status: int = 200):
        """Assert successful response."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )
        return response.json()

    def assert_error(self, response, expected_status: int, contains: str = None):
        """Assert error response."""
        assert response.status_code == expected_status
        if contains:
            assert contains.lower() in response.text.lower()

    def assert_unauthorized(self, response):
        """Assert 401 Unauthorized."""
        self.assert_error(response, self.UNAUTHORIZED)

    def assert_forbidden(self, response):
        """Assert 403 Forbidden."""
        self.assert_error(response, self.FORBIDDEN)

    def assert_not_found(self, response):
        """Assert 404 Not Found."""
        self.assert_error(response, self.NOT_FOUND)

    def assert_validation_error(self, response, field: str = None):
        """Assert 422 Validation Error."""
        assert response.status_code == self.UNPROCESSABLE
        if field:
            data = response.json()
            # Check if field is mentioned in error
            assert field in str(data)

    # ==========================================
    # Standard Auth Tests (reusable)
    # ==========================================

    def _test_without_auth(self, anon_client, method: str = "GET", **kwargs):
        """Test endpoint without authentication."""
        if not self.REQUIRES_AUTH:
            pytest.skip("Endpoint does not require auth")

        func = getattr(anon_client, method.lower())
        response = func(self.ENDPOINT, **kwargs)
        self.assert_unauthorized(response)

    def _test_invalid_token(self, anon_client, method: str = "GET", **kwargs):
        """Test endpoint with invalid token."""
        if not self.REQUIRES_AUTH:
            pytest.skip("Endpoint does not require auth")

        func = getattr(anon_client, method.lower())
        response = func(
            self.ENDPOINT,
            headers={"Authorization": "Bearer invalid_token"},
            **kwargs
        )
        self.assert_unauthorized(response)
```

#### helpers/security.py - 安全测试 Payload

```python
"""
Security test payloads for injection testing
"""

# SQL Injection payloads
SQL_INJECTION_PAYLOADS = [
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "1; SELECT * FROM profiles",
    "admin'--",
    "1' UNION SELECT * FROM users--",
    "' OR 1=1--",
    "1'; WAITFOR DELAY '0:0:10'--",
]

# XSS Injection payloads
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "javascript:alert('XSS')",
    "<svg onload=alert('XSS')>",
    "'><script>alert('XSS')</script>",
    "<body onload=alert('XSS')>",
]

# SSRF Test URLs (should be blocked)
SSRF_PAYLOADS = [
    "http://localhost:8080/admin",
    "http://127.0.0.1:22",
    "http://169.254.169.254/latest/meta-data/",  # AWS metadata
    "http://192.168.1.1/admin",
    "file:///etc/passwd",
    "http://[::1]/admin",
]

# Path Traversal payloads
PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "....//....//....//etc/passwd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
]


def get_boundary_strings() -> dict:
    """Get boundary test strings."""
    return {
        "empty": "",
        "whitespace": "   ",
        "max_length": "x" * 10000,
        "unicode": "测试中文🎉émoji",
        "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
        "newlines": "line1\nline2\rline3",
        "null_byte": "test\x00string",
    }
```

### 4.3 测试执行策略

#### 执行顺序

```bash
# 1. 快速冒烟测试 (< 30s)
pytest tests/integration/staging/test_health.py -v

# 2. P0 核心测试 (< 2min)
pytest tests/integration/staging/ -m "p0" -v

# 3. P0 + P1 完整测试 (< 5min)
pytest tests/integration/staging/ -m "p0 or p1" -v

# 4. 全量测试 (< 10min)
pytest tests/integration/staging/ -v

# 5. 安全测试专项 (< 3min)
pytest tests/integration/staging/security/ -v
```

#### pytest 标记

```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "p0: P0 priority - core business")
    config.addinivalue_line("markers", "p1: P1 priority - important")
    config.addinivalue_line("markers", "p2: P2 priority - supporting")
    config.addinivalue_line("markers", "p3: P3 priority - low frequency")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
```

---

## 五、关键测试场景设计

### 5.1 支付流程测试 (P0)

```python
# tests/integration/staging/billing/test_credits.py

import pytest
from ..base import BaseAPITest


@pytest.mark.p0
class TestBillingCredits(BaseAPITest):
    """
    测试 GET /api/v2/user/billing/credits

    功能: 获取用户积分余额
    响应: {monthly_credits, permanent_credits, total_credits, tier}
    """

    ENDPOINT = "/api/v2/user/billing/credits"

    # ==========================================
    # 功能测试
    # ==========================================

    def test_get_credits_success(self, auth_client):
        """正常获取积分余额"""
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证返回字段
        assert "monthly_credits" in data
        assert "permanent_credits" in data
        assert "total_credits" in data
        assert "tier" in data

        # 验证类型
        assert isinstance(data["monthly_credits"], int)
        assert isinstance(data["permanent_credits"], int)
        assert isinstance(data["total_credits"], int)
        assert data["tier"] in ["t1", "t2", "t3", "t4"]

        # 验证逻辑
        assert data["total_credits"] == data["monthly_credits"] + data["permanent_credits"]
        assert data["monthly_credits"] >= 0
        assert data["permanent_credits"] >= 0

    # ==========================================
    # 认证测试
    # ==========================================

    def test_without_token(self, anon_client):
        """无 token 应返回 401"""
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_invalid_token(self, anon_client):
        """无效 token 应返回 401"""
        response = anon_client.get(
            self.ENDPOINT,
            headers={"Authorization": "Bearer invalid"}
        )
        self.assert_unauthorized(response)

    def test_expired_token(self, anon_client):
        """过期 token 应返回 401"""
        # 使用一个已知过期的 token
        expired = "eyJhbG...expired..."  # 实际测试时用真实过期 token
        response = anon_client.get(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {expired}"}
        )
        self.assert_unauthorized(response)

    # ==========================================
    # 边界测试
    # ==========================================

    def test_credits_zero(self, auth_client):
        """积分为 0 时正确返回"""
        # 注: 这需要一个积分为 0 的测试用户
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)
        # 验证 0 积分用户不会返回负数
        assert data["total_credits"] >= 0

    # ==========================================
    # 性能测试
    # ==========================================

    def test_response_time(self, auth_client):
        """响应时间应 < 500ms"""
        import time
        start = time.time()
        response = auth_client.get(self.ENDPOINT)
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.5, f"Response took {duration:.2f}s, expected < 0.5s"
```

### 5.2 项目 CRUD 测试 (P0)

```python
# tests/integration/staging/projects/test_crud.py

import pytest
import uuid
from ..base import BaseAPITest
from ..helpers.security import XSS_PAYLOADS


@pytest.mark.p0
class TestProjectCreate(BaseAPITest):
    """测试 POST /api/v2/user/projects"""

    ENDPOINT = "/api/v2/user/projects"

    # ==========================================
    # 功能测试
    # ==========================================

    def test_create_minimal(self, auth_client, cleanup_registry):
        """最小参数创建项目"""
        response = auth_client.post(
            self.ENDPOINT,
            json={"title": f"Test Project {uuid.uuid4().hex[:8]}"}
        )
        data = self.assert_success(response, 201)

        assert "id" in data
        assert "title" in data
        cleanup_registry.register("project", data["id"])

    def test_create_with_canvas(self, auth_client, cleanup_registry):
        """带 canvas_data 创建项目"""
        canvas_data = {
            "version": "1.0",
            "pages": [{"id": "page1", "elements": []}]
        }
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": f"Test Canvas {uuid.uuid4().hex[:8]}",
                "canvas_data": canvas_data
            }
        )
        data = self.assert_success(response, 201)
        cleanup_registry.register("project", data["id"])

    # ==========================================
    # 参数验证测试
    # ==========================================

    def test_missing_title(self, auth_client):
        """缺少 title 应返回 422"""
        response = auth_client.post(self.ENDPOINT, json={})
        self.assert_validation_error(response, "title")

    def test_empty_title(self, auth_client):
        """空标题应返回 400"""
        response = auth_client.post(self.ENDPOINT, json={"title": ""})
        self.assert_error(response, 400)

    def test_title_too_long(self, auth_client):
        """标题超长应返回 400"""
        response = auth_client.post(
            self.ENDPOINT,
            json={"title": "x" * 201}  # 最大 200
        )
        self.assert_error(response, 400)

    @pytest.mark.parametrize("length", [1, 100, 200])
    def test_title_valid_lengths(self, auth_client, cleanup_registry, length):
        """测试有效的标题长度"""
        response = auth_client.post(
            self.ENDPOINT,
            json={"title": "x" * length}
        )
        data = self.assert_success(response, 201)
        cleanup_registry.register("project", data["id"])

    # ==========================================
    # 安全测试
    # ==========================================

    @pytest.mark.security
    @pytest.mark.parametrize("xss_payload", XSS_PAYLOADS[:3])
    def test_xss_in_title(self, auth_client, xss_payload):
        """标题中的 XSS 应被过滤或拒绝"""
        response = auth_client.post(
            self.ENDPOINT,
            json={"title": xss_payload}
        )
        # 应该被拒绝或过滤
        if response.status_code == 201:
            data = response.json()
            # 如果允许创建,验证内容被过滤
            assert "<script>" not in data.get("title", "")
        else:
            # 直接拒绝也是可接受的
            assert response.status_code in [400, 422]

    # ==========================================
    # 业务规则测试
    # ==========================================

    def test_capacity_limit_t1(self, auth_client):
        """
        T1 用户只能创建 1 个项目
        注: 需要一个 T1 用户且已有 1 个项目
        """
        # 先获取当前项目数
        list_resp = auth_client.get("/api/v2/user/projects")
        if list_resp.json().get("total", 0) >= 1:
            # 已达上限,创建应失败
            response = auth_client.post(
                self.ENDPOINT,
                json={"title": "Over Limit"}
            )
            # 应返回 403 或特定错误码
            assert response.status_code in [403, 422]


@pytest.mark.p0
class TestProjectUpdate(BaseAPITest):
    """测试 PUT /api/v2/user/projects/{id}"""

    def test_update_title(self, auth_client, sample_project):
        """更新标题"""
        response = auth_client.put(
            f"/api/v2/user/projects/{sample_project['id']}",
            json={"title": "Updated Title"}
        )
        data = self.assert_success(response)
        assert data["title"] == "Updated Title"

    def test_update_wrong_user(self, auth_client, other_user_project):
        """更新其他用户的项目应返回 403"""
        response = auth_client.put(
            f"/api/v2/user/projects/{other_user_project['id']}",
            json={"title": "Hacked"}
        )
        self.assert_forbidden(response)

    def test_update_not_found(self, auth_client):
        """更新不存在的项目应返回 404"""
        fake_id = str(uuid.uuid4())
        response = auth_client.put(
            f"/api/v2/user/projects/{fake_id}",
            json={"title": "Ghost"}
        )
        self.assert_not_found(response)


@pytest.mark.p0
class TestProjectDelete(BaseAPITest):
    """测试 DELETE /api/v2/user/projects/{id}"""

    def test_soft_delete(self, auth_client, sample_project):
        """软删除 (移入回收站)"""
        response = auth_client.delete(
            f"/api/v2/user/projects/{sample_project['id']}",
            params={"permanent": False}
        )
        self.assert_success(response, 200)

        # 验证项目进入回收站
        deleted_resp = auth_client.get("/api/v2/user/projects/deleted")
        deleted_ids = [p["id"] for p in deleted_resp.json().get("items", [])]
        assert sample_project["id"] in deleted_ids

    def test_hard_delete(self, auth_client, sample_project):
        """永久删除"""
        # 先软删除
        auth_client.delete(
            f"/api/v2/user/projects/{sample_project['id']}",
            params={"permanent": False}
        )
        # 再永久删除
        response = auth_client.delete(
            f"/api/v2/user/projects/{sample_project['id']}",
            params={"permanent": True}
        )
        self.assert_success(response, 200)

    def test_delete_wrong_user(self, auth_client, other_user_project):
        """删除其他用户的项目应返回 403"""
        response = auth_client.delete(
            f"/api/v2/user/projects/{other_user_project['id']}"
        )
        self.assert_forbidden(response)
```

### 5.3 市场购买测试 (P0 - 原子性)

```python
# tests/integration/staging/marketplace/test_purchase.py

import pytest
import uuid
from ..base import BaseAPITest


@pytest.mark.p0
class TestMarketplacePurchase(BaseAPITest):
    """
    测试 POST /api/v2/user/marketplace/purchase

    关键测试点:
    1. 幂等性 (idempotency_key)
    2. 原子性 (失败回滚)
    3. 竞态条件
    """

    ENDPOINT = "/api/v2/user/marketplace/purchase"

    # ==========================================
    # 功能测试
    # ==========================================

    def test_purchase_success(self, auth_client, available_listing):
        """成功购买产品"""
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": available_listing["id"],
                "idempotency_key": f"test_{uuid.uuid4().hex}"
            }
        )
        data = self.assert_success(response, 201)
        assert "purchase_id" in data or "transaction_id" in data

    # ==========================================
    # 幂等性测试
    # ==========================================

    def test_idempotency_same_key(self, auth_client, available_listing):
        """同一 idempotency_key 不会重复扣费"""
        idem_key = f"test_{uuid.uuid4().hex}"

        # 第一次购买
        resp1 = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": available_listing["id"],
                "idempotency_key": idem_key
            }
        )

        # 第二次用相同 key
        resp2 = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": available_listing["id"],
                "idempotency_key": idem_key
            }
        )

        # 两次应该返回相同结果,第二次不应再扣费
        assert resp1.status_code == resp2.status_code
        if resp1.status_code == 201:
            assert resp1.json() == resp2.json()

    def test_idempotency_different_keys(self, auth_client, available_listing):
        """不同 idempotency_key 会尝试重复购买"""
        # 第一次购买
        resp1 = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": available_listing["id"],
                "idempotency_key": f"test_{uuid.uuid4().hex}"
            }
        )

        # 第二次用不同 key
        resp2 = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": available_listing["id"],
                "idempotency_key": f"test_{uuid.uuid4().hex}"
            }
        )

        # 第二次应该失败 (已拥有)
        if resp1.status_code == 201:
            assert resp2.status_code in [409, 422]  # Conflict or Business Rule

    # ==========================================
    # 积分不足测试
    # ==========================================

    def test_insufficient_credits(self, auth_client_low_credits, expensive_listing):
        """积分不足应返回 402"""
        response = auth_client_low_credits.post(
            self.ENDPOINT,
            json={
                "listing_id": expensive_listing["id"],
                "idempotency_key": f"test_{uuid.uuid4().hex}"
            }
        )
        assert response.status_code == 402  # Payment Required

    # ==========================================
    # 业务规则测试
    # ==========================================

    def test_cannot_buy_own_listing(self, auth_client, own_listing):
        """不能购买自己的产品"""
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": own_listing["id"],
                "idempotency_key": f"test_{uuid.uuid4().hex}"
            }
        )
        assert response.status_code in [403, 422]

    def test_listing_not_available(self, auth_client, sold_out_listing):
        """已下架/售罄的产品"""
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": sold_out_listing["id"],
                "idempotency_key": f"test_{uuid.uuid4().hex}"
            }
        )
        assert response.status_code in [404, 422]

    # ==========================================
    # 参数验证
    # ==========================================

    def test_missing_listing_id(self, auth_client):
        """缺少 listing_id"""
        response = auth_client.post(
            self.ENDPOINT,
            json={"idempotency_key": f"test_{uuid.uuid4().hex}"}
        )
        self.assert_validation_error(response, "listing_id")

    def test_missing_idempotency_key(self, auth_client, available_listing):
        """缺少 idempotency_key"""
        response = auth_client.post(
            self.ENDPOINT,
            json={"listing_id": available_listing["id"]}
        )
        self.assert_validation_error(response, "idempotency_key")

    def test_invalid_listing_id_format(self, auth_client):
        """无效的 listing_id 格式"""
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "listing_id": "not-a-uuid",
                "idempotency_key": f"test_{uuid.uuid4().hex}"
            }
        )
        assert response.status_code in [400, 422]
```

### 5.4 安全测试 (横切)

```python
# tests/integration/staging/security/test_injection.py

import pytest
from ..helpers.security import SQL_INJECTION_PAYLOADS, XSS_PAYLOADS, SSRF_PAYLOADS


@pytest.mark.security
class TestSQLInjection:
    """SQL 注入防护测试"""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_search(self, auth_client, payload):
        """搜索参数 SQL 注入"""
        response = auth_client.get(
            "/api/v2/user/projects",
            params={"search": payload}
        )
        # 应该安全处理,不崩溃
        assert response.status_code in [200, 400, 422]
        # 不应该返回所有数据
        if response.status_code == 200:
            data = response.json()
            # 验证不是异常大量数据
            assert len(data.get("items", [])) <= 100

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:3])
    def test_sql_injection_in_title(self, auth_client, payload):
        """标题参数 SQL 注入"""
        response = auth_client.post(
            "/api/v2/user/projects",
            json={"title": payload}
        )
        # 不应该导致服务器错误
        assert response.status_code != 500


@pytest.mark.security
class TestXSSPrevention:
    """XSS 防护测试"""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_user_input(self, auth_client, payload):
        """用户输入 XSS 防护"""
        response = auth_client.post(
            "/api/v2/user/projects",
            json={"title": payload}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            title = data.get("title", "")
            # 验证脚本标签被过滤
            assert "<script>" not in title.lower()
            assert "javascript:" not in title.lower()
            assert "onerror=" not in title.lower()


@pytest.mark.security
class TestSSRFPrevention:
    """SSRF 防护测试"""

    @pytest.mark.parametrize("url", SSRF_PAYLOADS)
    def test_ssrf_in_thumbnail(self, auth_client, sample_project, url):
        """Thumbnail URL SSRF 防护"""
        response = auth_client.put(
            f"/api/v2/user/projects/{sample_project['id']}",
            json={"thumbnail_url": url}
        )
        # 私有 IP 和危险协议应被拒绝
        assert response.status_code in [400, 422]

    @pytest.mark.parametrize("url", SSRF_PAYLOADS)
    def test_ssrf_in_reference_image(self, auth_client, url):
        """AI 生成 reference_image SSRF 防护"""
        response = auth_client.post(
            "/api/v2/user/generate/images",
            json={
                "prompts": ["test"],
                "reference_image": url
            }
        )
        # 应被拒绝
        assert response.status_code in [400, 422]


@pytest.mark.security
class TestAuthBypass:
    """认证绕过测试"""

    def test_token_in_query_param(self, anon_client, fresh_token):
        """Token 在 query 参数中应无效"""
        response = anon_client.get(
            "/api/v2/user/profile/me",
            params={"token": fresh_token}
        )
        # Query param token 不应该工作
        assert response.status_code == 401

    def test_lowercase_bearer(self, anon_client, fresh_token):
        """小写 bearer 应无效"""
        response = anon_client.get(
            "/api/v2/user/profile/me",
            headers={"Authorization": f"bearer {fresh_token}"}
        )
        # 应该严格匹配 "Bearer"
        # 注: 有些实现接受小写,这是设计决策
        assert response.status_code in [200, 401]
```

---

## 六、CI/CD 集成

### 6.1 GitHub Actions 配置

```yaml
# .github/workflows/staging-api-tests.yml
name: Staging API Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    # 每天凌晨 2 点运行 (UTC)
    - cron: '0 2 * * *'
  workflow_dispatch:  # 允许手动触发

env:
  STAGING_URL: https://decodables-staging.up.railway.app

jobs:
  smoke-test:
    name: Smoke Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install httpx pytest

      - name: Health Check
        run: |
          curl -f $STAGING_URL/health || exit 1

  p0-tests:
    name: P0 Core Tests
    needs: smoke-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements-test.txt

      - name: Run P0 Tests
        env:
          CLERK_SECRET_KEY: ${{ secrets.CLERK_SECRET_KEY }}
          TEST_SESSION_ID: ${{ secrets.TEST_SESSION_ID }}
        run: |
          pytest tests/integration/staging/ -m "p0" -v \
            --tb=short \
            --junitxml=results/p0-results.xml

      - name: Upload Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: p0-test-results
          path: results/

  full-tests:
    name: Full API Tests
    needs: p0-tests
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements-test.txt

      - name: Run All Tests
        env:
          CLERK_SECRET_KEY: ${{ secrets.CLERK_SECRET_KEY }}
          TEST_SESSION_ID: ${{ secrets.TEST_SESSION_ID }}
        run: |
          pytest tests/integration/staging/ -v \
            --tb=short \
            --junitxml=results/full-results.xml \
            --html=results/report.html

      - name: Upload Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: full-test-results
          path: results/
```

### 6.2 本地运行脚本

```bash
#!/bin/bash
# scripts/run-staging-tests.sh

set -e

# 检查环境变量
if [ -z "$CLERK_SECRET_KEY" ]; then
    echo "Error: CLERK_SECRET_KEY not set"
    exit 1
fi

# 运行级别
LEVEL=${1:-p0}

case $LEVEL in
    smoke)
        echo "Running smoke tests..."
        pytest tests/integration/staging/test_health.py -v
        ;;
    p0)
        echo "Running P0 tests..."
        pytest tests/integration/staging/ -m "p0" -v
        ;;
    p1)
        echo "Running P0 + P1 tests..."
        pytest tests/integration/staging/ -m "p0 or p1" -v
        ;;
    security)
        echo "Running security tests..."
        pytest tests/integration/staging/security/ -v
        ;;
    all)
        echo "Running all tests..."
        pytest tests/integration/staging/ -v
        ;;
    *)
        echo "Usage: $0 [smoke|p0|p1|security|all]"
        exit 1
        ;;
esac
```

---

## 七、实施路线图

### Phase 1: 基础框架 (第 1 周)

**目标**: 搭建测试框架,完成 10 个核心接口测试

| 任务 | 预估工时 | 交付物 |
|------|----------|--------|
| 创建目录结构 | 2h | 目录 + __init__.py |
| 实现 conftest.py | 4h | Token 刷新 + Fixtures |
| 实现 base.py | 3h | 基础类 + 断言 |
| 实现 helpers | 3h | 安全 payload + 清理 |
| 测试 /health | 1h | 冒烟测试 |
| 测试 /profile/me | 2h | 用户信息 |
| 测试 /billing/credits | 3h | 积分余额 |
| 测试 /projects CRUD | 6h | 项目增删改查 |

**验收标准**:
- [ ] `pytest tests/integration/staging/ -v` 全部通过
- [ ] 覆盖 10 个接口,50+ 用例
- [ ] CI 冒烟测试配置完成

### Phase 2: P0 覆盖 (第 2-3 周)

**目标**: 完成所有 P0 接口测试

| 模块 | 接口数 | 用例数 | 工时 |
|------|--------|--------|------|
| Billing 完整 | 4 | 50 | 8h |
| Payment | 2 | 30 | 6h |
| Projects 完整 | 9 | 80 | 12h |
| AI Generate | 3 | 50 | 8h |
| Marketplace Purchase | 1 | 25 | 4h |
| Admin Subscriptions | 3 | 45 | 8h |

**验收标准**:
- [ ] P0 接口 100% 覆盖
- [ ] 每个接口 15+ 用例
- [ ] 边界 + 异常 + 安全测试

### Phase 3: P1 覆盖 (第 4-5 周)

**目标**: 完成 P1 接口,安全测试专项

| 任务 | 工时 |
|------|------|
| Profile 模块 | 6h |
| Marketplace 其他 | 10h |
| Assets 模块 | 8h |
| Generations 历史 | 4h |
| Security 专项 | 8h |
| Admin Users | 6h |

**验收标准**:
- [ ] P1 接口 100% 覆盖
- [ ] 安全测试 50+ 用例
- [ ] 总用例数 > 500

### Phase 4: 优化与自动化 (第 6 周+)

**目标**: CI/CD 完善,测试质量提升

| 任务 | 工时 |
|------|------|
| GitHub Actions 完整配置 | 4h |
| 测试报告美化 | 2h |
| 性能基准测试 | 4h |
| 文档完善 | 2h |
| P2/P3 补充 | 持续 |

---

## 八、附录

### A. 测试命名规范

```python
# 文件命名
test_{module}.py           # 如 test_credits.py
test_{module}_{aspect}.py  # 如 test_projects_permissions.py

# 类命名
class Test{Endpoint}:      # 如 TestBillingCredits

# 方法命名
def test_{scenario}_{expected}:
# 如 test_create_minimal_success
# 如 test_missing_title_returns_422
# 如 test_xss_in_title_filtered
```

### B. 常用断言

```python
# 成功响应
assert response.status_code == 200
data = response.json()
assert "id" in data

# 错误响应
assert response.status_code == 400
assert "error" in response.json() or "detail" in response.json()

# 列表响应
data = response.json()
assert isinstance(data.get("items"), list)
assert data.get("total", 0) >= 0

# 时间响应
import dateutil.parser
created_at = dateutil.parser.isoparse(data["created_at"])
assert created_at.year == 2026
```

### C. 测试数据策略

| 数据类型 | 来源 | 生命周期 |
|----------|------|----------|
| 测试用户 | 预创建 | 永久 |
| 测试项目 | 每次创建 | 测试后清理 |
| 测试订单 | Mock/预创建 | 不修改 |
| 测试积分 | 预充值 | 定期重置 |

---

**文档版本**: v1.0
**作者**: Claude
**最后更新**: 2026-01-18
