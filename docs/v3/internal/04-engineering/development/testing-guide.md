# 测试指南

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `tests/` 目录, pytest 配置

---

## 一、概述

### 1.1 测试策略

- **单元测试优先**: 快速反馈，高覆盖率
- **关键业务流集成测试**: 验证端到端流程
- **覆盖率目标**: ≥ 60% (核心模块 ≥ 75%)

### 1.2 测试金字塔

```
          ┌──────────┐
          │   E2E    │  5%
          ├──────────┤
          │  集成    │  25%
          ├──────────┤
          │  单元    │  70%
          └──────────┘
```

---

## 二、后端测试 (Python/Pytest)

### 2.1 目录结构

```
decodables/tests/
├── unit/                    # 单元测试
│   ├── domains/            # 领域层测试
│   ├── application/        # 应用层测试
│   └── shared/             # 共享模块测试
├── integration/            # 集成测试
│   ├── staging/           # Staging 环境
│   └── production/        # Production 验证
├── conftest.py            # 全局 fixtures
└── pytest.ini             # Pytest 配置
```

### 2.2 运行命令

```bash
# 运行所有单元测试
pytest tests/unit -v

# 运行特定模块
pytest tests/unit/domains/billing -v

# 运行集成测试
pytest tests/integration/staging -v --tb=short

# 带覆盖率
pytest tests/unit --cov=domains --cov-report=html
```

### 2.3 测试命名规范

```python
# 文件命名
test_{module_name}.py

# 测试函数命名
def test_{action}_{scenario}_{expected_result}():
    """Given-When-Then 格式"""
    # Given: 准备数据
    # When: 执行操作
    # Then: 验证结果
```

### 2.4 常用 Fixtures

```python
# conftest.py

@pytest.fixture
def mock_supabase():
    """Mock Supabase 客户端"""
    with patch('core.database.get_supabase_client') as mock:
        yield mock

@pytest.fixture
def test_user():
    """测试用户数据"""
    return UserEntity(
        id=uuid4(),
        email="test@example.com",
        tier="t2",
        created_at=datetime.now()
    )

@pytest.fixture
async def auth_token(test_user):
    """生成测试 Token"""
    return create_access_token({"sub": str(test_user.id)})
```

### 2.5 单元测试示例

```python
# tests/unit/domains/billing/test_credits_service.py

import pytest
from unittest.mock import AsyncMock, patch
from domains.billing.service import CreditsService

class TestCreditsService:
    """积分服务测试"""
    
    @pytest.fixture
    def service(self, mock_repository):
        return CreditsService(repository=mock_repository)
    
    @pytest.mark.asyncio
    async def test_deduct_credits_success(self, service, test_user):
        """Given 用户有足够积分 When 扣减积分 Then 成功扣减"""
        # Given
        service.repository.get_balance.return_value = 100
        
        # When
        result = await service.deduct_credits(
            user_id=test_user.id,
            amount=10,
            reason="ai_generation"
        )
        
        # Then
        assert result.success is True
        assert result.new_balance == 90
    
    @pytest.mark.asyncio
    async def test_deduct_credits_insufficient(self, service, test_user):
        """Given 用户积分不足 When 扣减积分 Then 返回错误"""
        # Given
        service.repository.get_balance.return_value = 5
        
        # When
        result = await service.deduct_credits(
            user_id=test_user.id,
            amount=10,
            reason="ai_generation"
        )
        
        # Then
        assert result.success is False
        assert result.error_code == "INSUFFICIENT_CREDITS"
```

### 2.6 集成测试示例

```python
# tests/integration/staging/test_billing_api.py

import pytest
import httpx

class TestBillingAPI:
    """计费 API 集成测试"""
    
    @pytest.fixture
    def client(self, base_url, auth_headers):
        return httpx.AsyncClient(
            base_url=base_url,
            headers=auth_headers
        )
    
    @pytest.mark.asyncio
    async def test_get_credits_balance(self, client):
        """测试获取积分余额"""
        response = await client.get("/api/v2/user/billing/credits")
        
        assert response.status_code == 200
        data = response.json()
        assert "monthly" in data["data"]
        assert "permanent" in data["data"]
    
    @pytest.mark.asyncio
    async def test_can_afford_check(self, client):
        """测试积分是否足够检查"""
        response = await client.get(
            "/api/v2/user/billing/can-afford",
            params={"amount": 10}
        )
        
        assert response.status_code == 200
        assert "can_afford" in response.json()["data"]
```

---

## 三、前端测试 (Jest/React Testing Library)

### 3.1 目录结构

```
decodables-fe/
├── __tests__/              # 测试目录
│   ├── components/        # 组件测试
│   ├── hooks/             # Hooks 测试
│   ├── utils/             # 工具函数测试
│   └── integration/       # 集成测试
├── jest.config.js         # Jest 配置
└── jest.setup.ts          # 测试环境设置
```

### 3.2 运行命令

```bash
# 运行所有测试
npm test

# 监听模式
npm test -- --watch

# 带覆盖率
npm test -- --coverage

# 运行特定文件
npm test -- __tests__/components/Button.test.tsx
```

### 3.3 组件测试示例

```typescript
// __tests__/components/Button.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when loading', () => {
    render(<Button loading>Click me</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### 3.4 Hooks 测试示例

```typescript
// __tests__/hooks/useCredits.test.ts

import { renderHook, act } from '@testing-library/react';
import { useCredits } from '@/hooks/useCredits';

describe('useCredits', () => {
  it('fetches credits on mount', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useCredits());
    
    expect(result.current.loading).toBe(true);
    
    await waitForNextUpdate();
    
    expect(result.current.loading).toBe(false);
    expect(result.current.credits).toBeDefined();
  });

  it('refreshes credits', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useCredits());
    
    await waitForNextUpdate();
    
    await act(async () => {
      await result.current.refresh();
    });
    
    expect(result.current.credits).toBeDefined();
  });
});
```

---

## 四、E2E 测试 (Playwright)

### 4.1 配置

```typescript
// playwright.config.ts

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 2,
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
  ],
});
```

### 4.2 E2E 测试示例

```typescript
// e2e/auth.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('user can login', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('shows error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('[data-testid="email-input"]', 'wrong@example.com');
    await page.fill('[data-testid="password-input"]', 'wrong');
    await page.click('[data-testid="login-button"]');
    
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  });
});
```

---

## 五、测试最佳实践

### 5.1 测试原则

| 原则 | 说明 |
|------|------|
| 单一职责 | 每个测试只验证一个行为 |
| 独立性 | 测试之间互不依赖 |
| 可重复 | 每次运行结果一致 |
| 快速 | 单元测试应在毫秒级完成 |
| 清晰 | 测试名称描述预期行为 |

### 5.2 Mock 策略

```python
# 好的做法: Mock 外部依赖
@patch('services.email.send_email')
async def test_registration(mock_email):
    mock_email.return_value = True
    # 测试注册逻辑

# 避免: Mock 被测试的代码本身
```

### 5.3 测试数据管理

```python
# 使用 Factory 模式
class UserFactory:
    @staticmethod
    def create(**kwargs):
        defaults = {
            "email": f"user_{uuid4().hex[:8]}@test.com",
            "tier": "t1",
            "created_at": datetime.now()
        }
        defaults.update(kwargs)
        return UserEntity(**defaults)

# 使用
def test_user_upgrade():
    user = UserFactory.create(tier="t1")
    # ...
```

### 5.4 异步测试

```python
# Pytest 异步测试
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None

# 使用 asyncio fixture
@pytest.fixture
async def async_client():
    async with AsyncClient() as client:
        yield client
```

---

## 六、CI/CD 集成

### 6.1 GitHub Actions 示例

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest tests/unit --cov=domains --cov-report=xml
      - uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test -- --coverage
```

---

## 七、相关文档

- [集成测试指南](./integration-testing-guide.md)
- [后端架构](../architecture/backend.md)
- [前端架构](../architecture/frontend.md)

---

**END OF DOCUMENT**
