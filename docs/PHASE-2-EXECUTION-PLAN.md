# Phase 2 执行计划 - 测试覆盖率提升

> 目标：60% → 80%+ 测试覆盖率

**时间**: Week 2-3 (预估 24h，实际可能更快)
**状态**: 🚧 执行中

---

## 📊 当前状态分析

### ✅ 已有测试（约 60% 覆盖率）

| 层级 | 已有测试 | 文件数 | 覆盖率估算 |
|------|----------|--------|------------|
| **API 层** | 5 个 | 5/38 (13%) | 🔴 低 |
| **Application 层** | 2 个 | 2/4 (50%) | 🟡 中 |
| **Domain 层** | 3 个 | 3/5 (60%) | 🟡 中 |
| **Services 层** | 30+ 个 | 高 | 🟢 高 (~80%) |
| **Edge Cases** | 若干 | - | 🟢 高 |
| **Business Rules** | 若干 | - | 🟢 高 |

### ⚠️ 需要补充的测试

**API 层缺失** (33 个文件):
- 19 个公开 API 测试
- 14 个 Admin API 测试

**Application 层缺失** (估计 2 个):
- Identity 相关 handlers
- Marketplace 相关 handlers

**Domain 层缺失** (估计 2 个):
- Marketplace domain
- Platform domain

---

## 🎯 Phase 2 核心任务

### 任务拆解（3 周计划）

```
Week 2.1 (8h):  API 层测试 - 公开 API (19 个)
Week 2.2 (6h):  API 层测试 - Admin API (14 个)
Week 2.3 (4h):  Application 层测试 (2 个)
Week 2.4 (2h):  Domain 层测试 (2 个)
Week 2.5 (2h):  集成测试补充
Week 2.6 (2h):  覆盖率验证和优化
─────────────────────────────────────
Total:     24h
```

---

## 📋 详细任务清单

### Week 2.1: 公开 API 测试 (19 个，8h)

#### 1. Billing & Credits (2 个)

**tests/api/test_billing_api.py** (新建)
```python
"""
测试 api/billing_api.py

端点:
- POST /api/v2/billing/deduct - 扣减积分
- GET /api/v2/billing/balance - 查询余额

测试用例:
- ✅ 正常扣减（200）
- ✅ 余额不足（400）
- ✅ 未认证（401）
- ✅ 查询余额（200）
"""
```

**tests/api/test_credits_api.py** (新建)
```python
"""
测试 api/credits_api.py

端点:
- GET /api/v2/credits - 获取用户积分
- GET /api/v2/credits/history - 积分历史

测试用例:
- ✅ 获取积分（200）
- ✅ 未认证（401）
- ✅ 获取历史（200）
- ✅ 分页测试
"""
```

#### 2. Marketplace & Platform (2 个)

**tests/api/test_marketplace_api.py** (新建)
**tests/api/test_platform_api.py** (新建)

#### 3. Payment & Resources (2 个)

**tests/api/test_payment_api.py** (新建)
**tests/api/test_resources_api.py** (新建)

#### 4. Assets & Tasks (2 个)

**tests/api/test_assets_api.py** (新建)
**tests/api/test_tasks_api.py** (新建)

#### 5. Templates & Themes (2 个)

**tests/api/test_templates_api.py** (新建)
**tests/api/test_themes_api.py** (新建)

#### 6. Campaigns & Analytics (2 个)

**tests/api/test_campaigns_api.py** (新建)
**tests/api/test_analytics_api.py** (新建)

#### 7. Tools & Generations (2 个)

**tests/api/test_tools_api.py** (新建)
**tests/api/test_generations_api.py** (新建)

#### 8. Support & Config (2 个)

**tests/api/test_support_api.py** (新建)
**tests/api/test_config_api.py** (新建)

#### 9. Logs & Experiments (2 个)

**tests/api/test_logs_api.py** (新建)
**tests/api/test_experiments_api.py** (新建)

#### 10. Webhooks (1 个)

**tests/api/test_webhooks_api.py** (新建)
```python
"""
测试 api/webhooks_api.py

端点:
- POST /api/v2/webhooks/clerk - Clerk webhook
- POST /api/v2/webhooks/stripe - Stripe webhook

测试用例:
- ✅ Clerk user.created 事件
- ✅ Clerk user.updated 事件
- ✅ Stripe checkout.session.completed
- ✅ Stripe invoice.payment_succeeded
- ✅ Webhook 签名验证失败（400）
- ✅ Webhook 幂等性测试
"""
```

---

### Week 2.2: Admin API 测试 (14 个，6h)

#### Admin API 测试目录结构
```
tests/api/admin/
├── __init__.py
├── test_users_api.py          # 用户管理
├── test_stats_api.py          # 统计数据
├── test_config_api.py         # 系统配置
├── test_campaigns_api.py      # 营销活动
├── test_moderation_api.py     # 内容审核
├── test_notifications_api.py  # 通知管理
├── test_system_api.py         # 系统操作
├── test_tasks_api.py          # 任务队列
├── test_ai_api.py             # AI 管理
├── test_logs_api.py           # 日志查询
├── test_metrics_api.py        # 指标统计
├── test_subscriptions_api.py  # 订阅管理
├── test_events_api.py         # 事件管理
└── test_experiments_api.py    # 实验管理
```

#### 通用测试模式（所有 Admin API）

每个 Admin API 测试文件包含:
```python
"""
测试 api/admin/xxx_api.py

测试用例:
- ✅ 正常请求（200/201）
- ✅ 未认证（401）
- ✅ 非管理员（403）- 重要！
- ✅ 参数验证（422）
- ✅ 业务逻辑验证
"""

def test_admin_endpoint_requires_auth():
    """未认证应返回 401"""
    response = client.get("/api/v2/admin/xxx")
    assert response.status_code == 401

def test_admin_endpoint_requires_admin_role():
    """非管理员应返回 403"""
    response = client.get(
        "/api/v2/admin/xxx",
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response.status_code == 403

def test_admin_endpoint_success():
    """管理员请求成功"""
    response = client.get(
        "/api/v2/admin/xxx",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
```

---

### Week 2.3: Application 层测试 (2 个，4h)

#### 缺失的 Application 层测试

**tests/application/test_identity_handlers.py** (新建)
```python
"""
测试 application/identity/

测试 Commands:
- UpdateUserProfileCommand
- DeleteUserCommand

测试 Queries:
- GetUserProfileQuery
- GetUserByEmailQuery

测试用例:
- ✅ 更新用户资料
- ✅ 删除用户
- ✅ 查询用户资料
- ✅ 通过邮箱查询用户
- ✅ 用户不存在处理
"""
```

**tests/application/test_marketplace_handlers.py** (新建)
```python
"""
测试 application/marketplace/

测试 Commands:
- CreateListingCommand
- PurchaseAssetCommand

测试 Queries:
- GetListingsQuery
- GetListingByIdQuery

测试用例:
- ✅ 创建 Listing
- ✅ 购买资产
- ✅ 积分不足处理
- ✅ 卖家收入计算（90%）
- ✅ 查询 Listings
"""
```

---

### Week 2.4: Domain 层测试 (2 个，2h)

#### 缺失的 Domain 层测试

**tests/domains/test_marketplace_domain.py** (新建)
```python
"""
测试 domains/marketplace/listing.py

测试 Listing Aggregate:
- create_listing()
- update_listing()
- publish()
- unpublish()
- purchase()

测试用例:
- ✅ 创建 Listing（价格验证）
- ✅ 发布/下架 Listing
- ✅ 购买流程
- ✅ 价格限制（最大 $500）
- ✅ 卖家分成（90%）
"""
```

**tests/domains/test_platform_domain.py** (新建)
```python
"""
测试 domains/platform/

测试 FeatureFlag:
- is_enabled()
- get_variant()

测试 Experiment:
- assign_variant()
- track_exposure()
- track_conversion()

测试用例:
- ✅ Feature Flag 启用/禁用
- ✅ Tier-based Flag
- ✅ Experiment 变体分配
- ✅ 确定性分配（同一用户总是同一变体）
- ✅ Exposure/Conversion 追踪
"""
```

---

### Week 2.5: 集成测试补充 (2h)

#### 端到端业务流程测试

**tests/integration/test_credit_purchase_flow.py** (新建)
```python
"""
端到端测试：积分购买流程

流程:
1. 用户创建 Stripe checkout session
2. Webhook 接收 checkout.session.completed
3. 积分增加到用户账户
4. 积分历史记录创建

测试用例:
- ✅ 完整购买流程
- ✅ Webhook 幂等性
- ✅ 积分正确增加
- ✅ 历史记录正确
"""
```

**tests/integration/test_subscription_flow.py** (新建)
```python
"""
端到端测试：订阅流程

流程:
1. 用户订阅 Starter/Pro
2. Webhook 接收 checkout.session.completed
3. Tier 升级
4. 月度积分分配
5. 每月续费（invoice.payment_succeeded）
6. 月度积分刷新

测试用例:
- ✅ 订阅开通流程
- ✅ Tier 升级
- ✅ 月度积分分配
- ✅ 续费刷新积分
- ✅ 取消订阅降级
"""
```

**tests/integration/test_generation_flow.py** (新建)
```python
"""
端到端测试：AI 生成流程

流程:
1. 用户触发生成（检查积分）
2. 扣减积分（先月度后永久）
3. 调用 AI API
4. 保存生成结果
5. 创建积分历史记录

测试用例:
- ✅ 完整生成流程
- ✅ 积分扣减顺序（月度 → 永久）
- ✅ 积分不足处理
- ✅ AI API 失败回滚
"""
```

---

### Week 2.6: 覆盖率验证和优化 (2h)

#### 任务

1. **运行完整测试套件**
```bash
pytest tests/ \
       --cov=api \
       --cov=application \
       --cov=domains \
       --cov=infrastructure \
       --cov-report=html \
       --cov-report=term-missing \
       --cov-fail-under=80
```

2. **分析覆盖率报告**
```bash
open htmlcov/index.html

# 查看哪些文件/行未覆盖
# 补充缺失的测试用例
```

3. **优化低覆盖率文件**
- 目标：所有核心模块 > 80%
- 边缘用例补充
- 错误处理测试

4. **更新 GitHub Actions**
```yaml
# .github/workflows/test.yml
- name: Run all tests with coverage
  run: |
    pytest tests/ \
           --cov=. \
           --cov-report=xml \
           --cov-fail-under=80  # 提高到 80%
```

---

## 🛠️ 测试文件模板

### API 测试模板

```python
"""
测试 api/xxx_api.py

创建时间: 2026-01-07
"""

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


# Fixtures
@pytest.fixture
def auth_headers(test_user_token):
    """认证 headers"""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """管理员 headers"""
    return {"Authorization": f"Bearer {admin_token}"}


# 测试用例
class TestXxxAPI:
    """XXX API 测试"""

    def test_get_xxx_success(self, auth_headers):
        """正常获取 XXX"""
        response = client.get("/api/v2/xxx", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "xxx" in data

    def test_get_xxx_unauthorized(self):
        """未认证应返回 401"""
        response = client.get("/api/v2/xxx")
        assert response.status_code == 401

    def test_post_xxx_success(self, auth_headers):
        """创建 XXX 成功"""
        payload = {"name": "test", "value": 123}
        response = client.post(
            "/api/v2/xxx",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test"

    def test_post_xxx_validation_error(self, auth_headers):
        """参数验证失败"""
        payload = {"name": ""}  # 空名称
        response = client.post(
            "/api/v2/xxx",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 422


# Admin API 额外测试
class TestAdminXxxAPI:
    """Admin XXX API 测试"""

    def test_admin_xxx_requires_admin_role(self, auth_headers):
        """非管理员应返回 403"""
        response = client.get("/api/v2/admin/xxx", headers=auth_headers)
        assert response.status_code == 403

    def test_admin_xxx_success(self, admin_headers):
        """管理员请求成功"""
        response = client.get("/api/v2/admin/xxx", headers=admin_headers)
        assert response.status_code == 200
```

### Application 层测试模板

```python
"""
测试 application/xxx/

创建时间: 2026-01-07
"""

import pytest
from application.xxx.commands import XxxCommand
from application.xxx.queries import GetXxxQuery
from application.xxx.handlers import XxxCommandHandler, XxxQueryHandler


class TestXxxCommandHandler:
    """测试 XXX Command Handler"""

    def test_execute_command_success(self, container):
        """执行命令成功"""
        handler = XxxCommandHandler(container)
        command = XxxCommand(user_id="user_123", data={"name": "test"})

        result = handler.execute(command)

        assert result.success
        assert result.data["name"] == "test"

    def test_execute_command_validation_error(self, container):
        """命令验证失败"""
        handler = XxxCommandHandler(container)
        command = XxxCommand(user_id="user_123", data={})  # 缺少必填字段

        with pytest.raises(ValidationError):
            handler.execute(command)


class TestXxxQueryHandler:
    """测试 XXX Query Handler"""

    def test_execute_query_success(self, container):
        """执行查询成功"""
        handler = XxxQueryHandler(container)
        query = GetXxxQuery(user_id="user_123")

        result = handler.execute(query)

        assert result is not None
        assert result.user_id == "user_123"

    def test_execute_query_not_found(self, container):
        """查询不存在的资源"""
        handler = XxxQueryHandler(container)
        query = GetXxxQuery(user_id="nonexistent")

        with pytest.raises(NotFoundException):
            handler.execute(query)
```

### Domain 层测试模板

```python
"""
测试 domains/xxx/

创建时间: 2026-01-07
"""

import pytest
from domains.xxx.aggregate import XxxAggregate


class TestXxxAggregate:
    """测试 XXX Aggregate"""

    def test_create_xxx(self):
        """创建 XXX"""
        xxx = XxxAggregate.create(
            user_id="user_123",
            name="Test XXX",
            value=100
        )

        assert xxx.user_id == "user_123"
        assert xxx.name == "Test XXX"
        assert xxx.value == 100

    def test_create_xxx_validation(self):
        """创建 XXX 参数验证"""
        with pytest.raises(ValueError):
            XxxAggregate.create(
                user_id="user_123",
                name="",  # 空名称
                value=-1   # 负数
            )

    def test_xxx_business_rule(self):
        """测试业务规则"""
        xxx = XxxAggregate.create(user_id="user_123", name="Test", value=100)

        # 执行业务操作
        result = xxx.do_something()

        # 验证业务规则
        assert result == expected_value
```

---

## 📊 测试覆盖率目标

### 分层目标

| 层级 | 当前 | Phase 2 目标 | 验收标准 |
|------|------|-------------|----------|
| **API 层** | 13% (5/38) | **90%+** (34+/38) | ✅ 所有端点有测试 |
| **Application 层** | 50% (2/4) | **100%** (4/4) | ✅ 所有 handlers 测试 |
| **Domain 层** | 60% (3/5) | **100%** (5/5) | ✅ 所有 aggregates 测试 |
| **Services 层** | 80% | **80%+** (保持) | ✅ 核心服务覆盖 |
| **Infrastructure 层** | 60% | **70%+** | ✅ 关键基础设施测试 |
| **Overall** | **~60%** | **≥80%** | ✅ pytest --cov-fail-under=80 |

### 验收标准

```bash
# 必须通过以下命令
pytest tests/ \
       --cov=api \
       --cov=application \
       --cov=domains \
       --cov=infrastructure \
       --cov-report=term-missing \
       --cov-fail-under=80 \
       -v

# 输出应该显示
# TOTAL coverage: ≥80%
```

---

## 🚀 执行方式

### 选项 A: 批量创建所有测试文件（推荐）

**优点**:
- 快速搭建测试框架
- 一次性完成所有模板
- 后续只需填充具体测试逻辑

**我会做**:
1. 创建所有 37 个测试文件（19 公开 + 14 Admin + 2 Application + 2 Domain）
2. 每个文件包含基础测试用例
3. 提交到 git
4. GitHub Actions 自动运行

**你只需要**:
- 指令: `批量创建所有测试文件`
- 等待 5-10 分钟
- 查看 GitHub Actions 结果

---

### 选项 B: 分步创建（适合学习）

**优点**:
- 逐步理解测试逻辑
- 可以针对性调整
- 更可控

**执行步骤**:
1. **Day 1**: 创建 API 层测试（19 个公开 API）
2. **Day 2**: 创建 Admin API 测试（14 个）
3. **Day 3**: 创建 Application + Domain 层测试（4 个）
4. **Day 4**: 创建集成测试（3 个）
5. **Day 5**: 验证覆盖率，优化

**你需要**:
- 每天给我指令: `创建第 X 批测试`
- 审查测试逻辑
- 决定是否调整

---

### 选项 C: 只创建关键测试（最小化）

**优点**:
- 快速达到 80% 覆盖率
- 专注核心业务逻辑

**我会创建**:
1. **高优先级 API** (15 个):
   - billing, credits, user, projects, marketplace
   - payment, generation, webhooks
   - admin: users, stats, ai, subscriptions

2. **Application 层** (全部 4 个)
3. **Domain 层** (全部 5 个)
4. **集成测试** (3 个关键流程)

**跳过的低优先级 API** (18 个):
- resources, assets, tasks, templates, themes
- campaigns, analytics, tools, generations
- support, config, logs, experiments
- admin: config, campaigns, moderation, notifications, system, tasks, logs, metrics, events, experiments

---

## 💡 我的推荐

### 🎯 推荐：选项 A（批量创建）

**理由**:
1. ✅ 快速完成 Phase 2（2-3 小时 vs 24 小时估算）
2. ✅ 一次性搭建完整测试框架
3. ✅ 后续只需维护和优化
4. ✅ GitHub Actions 自动验证
5. ✅ 达到 80%+ 覆盖率

**时间对比**:

| 方式 | 创建时间 | 填充逻辑 | 总时间 |
|------|----------|----------|--------|
| 选项 A (批量) | 2-3h | 按需 | 2-3h (立即可用) |
| 选项 B (分步) | 5 天 | 同步 | 5 天 |
| 选项 C (最小) | 1-2h | 按需 | 1-2h (部分覆盖) |

---

## 📝 下一步行动

**告诉我你的选择**:

**选项 A** (推荐):
```
批量创建所有测试文件
```

**选项 B**:
```
分步创建，先创建公开 API 测试
```

**选项 C**:
```
只创建关键测试
```

**或者**:
```
我想调整计划（告诉我你的想法）
```

---

**准备好了吗？告诉我你的选择！** 🚀
