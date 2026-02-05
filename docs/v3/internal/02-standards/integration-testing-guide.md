# 集成测试指南

> 前后端集成测试规范与最佳实践

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]

---

## 一、概述

集成测试验证多个组件/模块协同工作的正确性，是测试金字塔的中间层。

---

## 二、测试范围

### 2.1 后端集成测试

| 类型 | 描述 | 示例 |
|------|------|------|
| API 集成 | 完整请求-响应流程 | 登录 → 获取 Token → 访问资源 |
| 数据库集成 | Service + Repository | 创建用户 → 查询用户 |
| 外部服务 | Mock 第三方服务 | Stripe Webhook 处理 |

### 2.2 前端集成测试

| 类型 | 描述 | 示例 |
|------|------|------|
| 组件集成 | 多组件交互 | Form 提交 → Loading → 结果 |
| Store 集成 | UI + 状态管理 | 按钮点击 → Store 更新 → UI 变化 |
| API 集成 | 组件 + Mock API | 列表加载 → 分页 → 筛选 |

---

## 三、后端集成测试

### 3.1 测试结构

```
tests/
├── integration/
│   ├── conftest.py          # 共享 fixtures
│   ├── test_auth_flow.py    # 认证流程
│   ├── test_billing_flow.py # 计费流程
│   ├── test_project_flow.py # 项目流程
│   └── test_marketplace.py  # 市场流程
```

### 3.2 Fixtures

```python
# conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def test_client(app):
    """测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_db(db_session: AsyncSession):
    """测试数据库会话"""
    yield db_session
    await db_session.rollback()

@pytest.fixture
async def authenticated_client(test_client, test_user):
    """认证客户端"""
    response = await test_client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "test_password"
    })
    token = response.json()["access_token"]
    test_client.headers["Authorization"] = f"Bearer {token}"
    yield test_client
```

### 3.3 测试示例

```python
# test_auth_flow.py
import pytest

@pytest.mark.asyncio
class TestAuthFlow:
    """认证流程集成测试"""
    
    async def test_complete_auth_flow(self, test_client, test_db):
        """完整认证流程: 注册 → 验证 → 登录 → 刷新"""
        # 1. 注册
        register_response = await test_client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!"
        })
        assert register_response.status_code == 201
        
        # 2. 模拟邮箱验证 (测试环境直接激活)
        user_id = register_response.json()["user_id"]
        await activate_user(test_db, user_id)
        
        # 3. 登录
        login_response = await test_client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "SecurePass123!"
        })
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        
        # 4. 使用 Token 访问资源
        test_client.headers["Authorization"] = f"Bearer {data['access_token']}"
        profile_response = await test_client.get("/api/v1/profile")
        assert profile_response.status_code == 200
        
        # 5. 刷新 Token
        refresh_response = await test_client.post("/api/v1/auth/refresh", json={
            "refresh_token": data["refresh_token"]
        })
        assert refresh_response.status_code == 200
```

### 3.4 外部服务 Mock

```python
# test_billing_flow.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
class TestBillingFlow:
    """计费流程集成测试"""
    
    @patch("shared.payment.stripe_client")
    async def test_subscription_flow(self, mock_stripe, authenticated_client, test_user):
        """订阅流程: 创建 → Webhook → 激活"""
        # Mock Stripe API
        mock_stripe.checkout.Session.create = AsyncMock(return_value={
            "id": "cs_test_123",
            "url": "https://checkout.stripe.com/..."
        })
        
        # 1. 创建订阅会话
        response = await authenticated_client.post("/api/v1/billing/subscribe", json={
            "tier": "t2"
        })
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        
        # 2. 模拟 Webhook
        webhook_payload = create_stripe_webhook_payload(
            event_type="checkout.session.completed",
            session_id=session_id,
            customer_id="cus_test",
            subscription_id="sub_test"
        )
        
        webhook_response = await authenticated_client.post(
            "/api/v1/webhooks/stripe",
            content=webhook_payload,
            headers={"Stripe-Signature": "test_sig"}
        )
        assert webhook_response.status_code == 200
        
        # 3. 验证订阅激活
        profile = await authenticated_client.get("/api/v1/profile")
        assert profile.json()["tier"] == "t2"
```

---

## 四、前端集成测试

### 4.1 测试结构

```
tests/
├── integration/
│   ├── setup.ts             # 测试配置
│   ├── auth.test.tsx        # 认证流程
│   ├── editor.test.tsx      # 编辑器流程
│   ├── marketplace.test.tsx # 市场流程
│   └── checkout.test.tsx    # 结账流程
```

### 4.2 测试配置

```typescript
// setup.ts
import { setupServer } from 'msw/node'
import { rest } from 'msw'

// Mock API handlers
export const handlers = [
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    return res(ctx.json({
      access_token: 'mock_token',
      refresh_token: 'mock_refresh'
    }))
  }),
  
  rest.get('/api/v1/profile', (req, res, ctx) => {
    return res(ctx.json({
      id: 'user_123',
      email: 'test@example.com',
      tier: 't1'
    }))
  }),
]

export const server = setupServer(...handlers)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

### 4.3 测试示例

```typescript
// auth.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from '@/app/(auth)/login/page'
import { TestProviders } from '../utils/test-providers'

describe('Login Flow', () => {
  it('should complete login flow', async () => {
    const user = userEvent.setup()
    
    render(
      <TestProviders>
        <LoginPage />
      </TestProviders>
    )
    
    // 1. 填写表单
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    
    // 2. 提交
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    // 3. 等待加载
    expect(screen.getByText(/signing in/i)).toBeInTheDocument()
    
    // 4. 验证跳转
    await waitFor(() => {
      expect(window.location.pathname).toBe('/dashboard')
    })
  })
  
  it('should show error on invalid credentials', async () => {
    server.use(
      rest.post('/api/v1/auth/login', (req, res, ctx) => {
        return res(ctx.status(401), ctx.json({ detail: 'Invalid credentials' }))
      })
    )
    
    const user = userEvent.setup()
    render(<TestProviders><LoginPage /></TestProviders>)
    
    await user.type(screen.getByLabelText(/email/i), 'wrong@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })
})
```

### 4.4 Store 集成测试

```typescript
// editor.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Editor } from '@/app/editor/[id]/page'
import { useEditorStore } from '@/stores/editor'
import { TestProviders } from '../utils/test-providers'

describe('Editor Integration', () => {
  beforeEach(() => {
    useEditorStore.getState().reset()
  })
  
  it('should update store when adding object', async () => {
    const user = userEvent.setup()
    
    render(<TestProviders><Editor params={{ id: 'project_123' }} /></TestProviders>)
    
    // 等待编辑器加载
    await waitFor(() => {
      expect(screen.getByTestId('canvas')).toBeInTheDocument()
    })
    
    // 添加文本
    await user.click(screen.getByRole('button', { name: /add text/i }))
    
    // 验证 Store 更新
    const { objects } = useEditorStore.getState()
    expect(objects).toHaveLength(1)
    expect(objects[0].type).toBe('text')
  })
})
```

---

## 五、E2E 测试

### 5.1 Playwright 配置

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
})
```

### 5.2 E2E 示例

```typescript
// e2e/checkout.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Checkout Flow', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login')
    await page.fill('[name="email"]', 'test@example.com')
    await page.fill('[name="password"]', 'password123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/dashboard')
  })
  
  test('should complete subscription upgrade', async ({ page }) => {
    // 1. 进入定价页
    await page.goto('/pricing')
    
    // 2. 选择计划
    await page.click('[data-tier="t2"] button')
    
    // 3. 等待 Stripe Checkout
    await page.waitForURL(/checkout\.stripe\.com/)
    
    // 4. 填写测试卡信息
    const stripeFrame = page.frameLocator('iframe[name*="stripe"]')
    await stripeFrame.locator('[name="cardNumber"]').fill('4242424242424242')
    await stripeFrame.locator('[name="cardExpiry"]').fill('1234')
    await stripeFrame.locator('[name="cardCvc"]').fill('123')
    
    // 5. 提交
    await page.click('button[type="submit"]')
    
    // 6. 验证成功
    await page.waitForURL('/dashboard?upgraded=true')
    await expect(page.locator('[data-tier]')).toHaveText('Starter')
  })
})
```

---

## 六、关键路径清单

### 6.1 必须覆盖的路径

| 路径 | 描述 |
|------|------|
| 注册 → 验证 → 登录 | 完整认证流程 |
| 创建项目 → 编辑 → 保存 | 核心编辑流程 |
| 选择计划 → 支付 → 激活 | 订阅流程 |
| 上传 → 导出 | 资产操作流程 |
| 购买 → 下载 | Marketplace 流程 |

### 6.2 边界场景

| 场景 | 测试点 |
|------|--------|
| Token 过期 | 自动刷新 |
| 网络断开 | 离线提示 |
| 并发操作 | 乐观锁冲突 |
| 支付失败 | 错误恢复 |

---

## 七、测试数据

### 7.1 种子数据

```python
# seeds/test_data.py
TEST_USERS = [
    {"email": "free@test.com", "tier": "t1"},
    {"email": "starter@test.com", "tier": "t2"},
    {"email": "pro@test.com", "tier": "t3"},
]

TEST_PROJECTS = [
    {"name": "Test Project 1", "owner": "free@test.com"},
    {"name": "Test Project 2", "owner": "pro@test.com"},
]
```

### 7.2 数据隔离

```python
@pytest.fixture(autouse=True)
async def isolate_test_data(test_db):
    """每个测试使用独立数据"""
    await test_db.execute("BEGIN")
    yield
    await test_db.execute("ROLLBACK")
```

---

## 八、相关文档

- [测试指南](./testing-guide.md)
- [API 端点文档](../04-engineering/api/user-endpoints.md)
