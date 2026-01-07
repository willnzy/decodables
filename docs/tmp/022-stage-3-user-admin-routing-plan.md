# Stage 3: User/Admin 路由结构创建计划

> **创建时间**: 2026-01-08
> **预计时间**: 2-3 周
> **目标**: 将现有 v2 API 按角色分离为 User 和 Admin 两层

---

## 📋 任务概述

### 当前状态

```
api/
├── __init__.py
├── billing_api.py
├── projects_api.py
├── marketplace_api.py
├── payment_api.py
├── support_api.py
├── ... (24 个用户端 API)
└── admin/
    ├── analytics_api.py
    ├── campaigns_api.py
    ├── ... (14 个管理端 API)
```

**问题**:
- ❌ 用户端和管理端 API 混在一起
- ❌ URL 前缀不统一 (`/api/v2/*`)
- ❌ 没有明确的角色分离
- ❌ 难以实现细粒度的权限控制

### 目标结构

```
api/
├── __init__.py
├── user/                    # 用户端 API (24 个文件)
│   ├── __init__.py
│   ├── analytics.py         # /api/v2/user/analytics
│   ├── billing.py           # /api/v2/user/billing
│   ├── campaigns.py         # /api/v2/user/campaigns
│   ├── config.py            # /api/v2/user/config
│   ├── export.py            # /api/v2/user/export
│   ├── generation.py        # /api/v2/user/generation
│   ├── generations.py       # /api/v2/user/generations
│   ├── logs.py              # /api/v2/user/logs
│   ├── marketplace.py       # /api/v2/user/marketplace
│   ├── payment.py           # /api/v2/user/payment
│   ├── projects.py          # /api/v2/user/projects
│   ├── resources.py         # /api/v2/user/resources
│   ├── support.py           # /api/v2/user/support
│   ├── tasks.py             # /api/v2/user/tasks
│   ├── templates.py         # /api/v2/user/templates
│   ├── themes.py            # /api/v2/user/themes
│   ├── tools.py             # /api/v2/user/tools
│   └── webhooks.py          # /api/v2/user/webhooks
│
└── admin/                   # 管理端 API (14 个文件)
    ├── __init__.py
    ├── ai.py                # /api/v2/admin/ai
    ├── analytics.py         # /api/v2/admin/analytics
    ├── campaigns.py         # /api/v2/admin/campaigns
    ├── config.py            # /api/v2/admin/config
    ├── events.py            # /api/v2/admin/events
    ├── experiments.py       # /api/v2/admin/experiments
    ├── feature_flags.py     # /api/v2/admin/feature-flags
    ├── logs.py              # /api/v2/admin/logs
    ├── metrics.py           # /api/v2/admin/metrics
    ├── monitoring.py        # /api/v2/admin/monitoring
    ├── resources.py         # /api/v2/admin/resources
    ├── subscriptions.py     # /api/v2/admin/subscriptions
    ├── themes.py            # /api/v2/admin/themes
    └── users.py             # /api/v2/admin/users
```

**收益**:
- ✅ 清晰的角色分离 (User vs Admin)
- ✅ 统一的 URL 前缀 (`/api/v2/user/*` vs `/api/v2/admin/*`)
- ✅ 便于实现细粒度权限控制
- ✅ 便于 Feature Flag 灰度发布
- ✅ API 文档更清晰 (按角色分组)

---

## 🗺️ 迁移路线图

### Week 1: 核心用户端 API (P0 + P1)

| 优先级 | 原文件 | 新文件 | URL 前缀 | 端点数 | 状态 |
|--------|--------|--------|----------|--------|------|
| 🔴 P0 | api/billing_api.py | api/user/billing.py | `/api/v2/user/billing` | 2 | ⏳ 待开始 |
| 🔴 P0 | api/generation_api.py | api/user/generation.py | `/api/v2/user/generation` | 4 | ⏳ 待开始 |
| 🔴 P0 | api/webhooks_api.py | api/user/webhooks.py | `/api/v2/user/webhooks` | 2 | ⏳ 待开始 |
| 🟠 P1 | api/projects_api.py | api/user/projects.py | `/api/v2/user/projects` | 10 | ⏳ 待开始 |
| 🟠 P1 | api/marketplace_api.py | api/user/marketplace.py | `/api/v2/user/marketplace` | 11 | ⏳ 待开始 |

**Week 1 小计**: 5 个文件, 29 个端点

### Week 2: 高频用户端 API (P1 + P2)

| 优先级 | 原文件 | 新文件 | URL 前缀 | 端点数 | 状态 |
|--------|--------|--------|----------|--------|------|
| 🟠 P1 | api/campaigns_api.py | api/user/campaigns.py | `/api/v2/user/campaigns` | 3 | ⏳ 待开始 |
| 🟠 P1 | api/templates_api.py | api/user/templates.py | `/api/v2/user/templates` | 5 | ⏳ 待开始 |
| 🟠 P1 | api/themes_api.py | api/user/themes.py | `/api/v2/user/themes` | 2 | ⏳ 待开始 |
| 🟡 P2 | api/analytics_api.py | api/user/analytics.py | `/api/v2/user/analytics` | 2 | ⏳ 待开始 |
| 🟡 P2 | api/config_api.py | api/user/config.py | `/api/v2/user/config` | 2 | ⏳ 待开始 |
| 🟡 P2 | api/resources_api.py | api/user/resources.py | `/api/v2/user/resources` | 4 | ⏳ 待开始 |
| 🟡 P2 | api/payment_api.py | api/user/payment.py | `/api/v2/user/payment` | 2 | ⏳ 待开始 |
| 🟡 P2 | api/support_api.py | api/user/support.py | `/api/v2/user/support` | 4 | ⏳ 待开始 |

**Week 2 小计**: 8 个文件, 24 个端点

### Week 3: 低频用户端 + 全部管理端 API

#### 用户端 (P3)

| 优先级 | 原文件 | 新文件 | URL 前缀 | 端点数 | 状态 |
|--------|--------|--------|----------|--------|------|
| 🟢 P3 | api/export_api.py | api/user/export.py | `/api/v2/user/export` | 4 | ⏳ 待开始 |
| 🟢 P3 | api/logs_api.py | api/user/logs.py | `/api/v2/user/logs` | 1 | ⏳ 待开始 |
| 🟢 P3 | api/tools_api.py | api/user/tools.py | `/api/v2/user/tools` | 2 | ⏳ 待开始 |
| 🟢 P3 | api/tasks_api.py | api/user/tasks.py | `/api/v2/user/tasks` | 3 | ⏳ 待开始 |
| 🟢 P3 | api/generations_api.py | api/user/generations.py | `/api/v2/user/generations` | 2 | ⏳ 待开始 |
| 🟢 P3 | api/experiments_api.py | api/user/experiments.py | `/api/v2/user/experiments` | 2 | ⏳ 待开始 |

#### 管理端 (P1)

| 优先级 | 原文件 | 新文件 | URL 前缀 | 端点数 | 状态 |
|--------|--------|--------|----------|--------|------|
| 🟠 P1 | api/admin/analytics_api.py | api/admin/analytics.py | `/api/v2/admin/analytics` | 8 | ⏳ 待开始 |
| 🟠 P1 | api/admin/campaigns_api.py | api/admin/campaigns.py | `/api/v2/admin/campaigns` | 6 | ⏳ 待开始 |
| 🟠 P1 | api/admin/experiments_api.py | api/admin/experiments.py | `/api/v2/admin/experiments` | 5 | ⏳ 待开始 |
| 🟠 P1 | api/admin/logs_api.py | api/admin/logs.py | `/api/v2/admin/logs` | 3 | ⏳ 待开始 |
| 🟠 P1 | api/admin/metrics_api.py | api/admin/metrics.py | `/api/v2/admin/metrics` | 4 | ⏳ 待开始 |
| 🟠 P1 | api/admin/users_api.py | api/admin/users.py | `/api/v2/admin/users` | 10 | ⏳ 待开始 |

**Week 3 小计**: 12 个文件, ~50 个端点

---

## 📝 迁移标准流程

### Step 1: 创建目录结构

```bash
mkdir -p api/user
mkdir -p api/admin
touch api/user/__init__.py
touch api/admin/__init__.py
```

### Step 2: 迁移单个文件 (示例: billing_api.py)

#### 2.1 创建新文件

```bash
cp api/billing_api.py api/user/billing.py
```

#### 2.2 更新路由前缀

```python
# api/user/billing.py

# 修改前
router = APIRouter(prefix="/api/v2/billing", tags=["billing-v2"])

# 修改后
router = APIRouter(prefix="/api/v2/user/billing", tags=["user-billing-v2"])
```

#### 2.3 更新依赖导入 (如需要)

```python
# 保持不变,仍然使用 DDD 层
from application.commands.billing import PurchaseCreditsCommand
from application.handlers.billing import BillingCommandHandler
from dependencies import get_current_user
```

#### 2.4 更新文档字符串

```python
"""
User Billing API - Credit management and subscription endpoints.

@module api.user.billing
@version 2.0.0

Endpoints:
- GET /api/v2/user/billing/credits - Get user credits
- POST /api/v2/user/billing/purchase - Purchase credits
"""
```

### Step 3: 更新 app.py 路由注册

```python
# app.py

# 修改前
from api import api_router

# 修改后 (逐步添加)
from api.user import billing as user_billing_router
from api.user import projects as user_projects_router
from api.admin import analytics as admin_analytics_router

app.include_router(user_billing_router.router)
app.include_router(user_projects_router.router)
app.include_router(admin_analytics_router.router)
```

### Step 4: 更新测试文件

```bash
# 创建新测试目录
mkdir -p tests/api/user
mkdir -p tests/api/admin

# 复制并更新测试
cp tests/api/test_billing_api.py tests/api/user/test_billing.py
```

```python
# tests/api/user/test_billing.py

# 更新 URL
response = client.get(
    "/api/v2/user/billing/credits",  # 新 URL
    headers=auth_headers,
)
```

### Step 5: 验证迁移

```bash
# 运行测试
pytest tests/api/user/test_billing.py -v

# 启动服务器
uvicorn app:app --reload

# 访问 API 文档
# http://localhost:8000/docs
# 验证新端点在 "user-billing-v2" tag 下
```

### Step 6: 保留旧文件 (向后兼容)

```python
# api/billing_api.py (保留但标记为废弃)

"""
⚠️ DEPRECATED: This module is deprecated and will be removed in v3.0.0
Please use api.user.billing instead.
"""

from api.user.billing import router

# 旧路由重定向到新路由
# app.py 中同时注册新旧两个 router
```

---

## 🎯 Week 1 执行计划 (Day 1-5)

### Day 1: 创建基础结构 + Billing API

**任务**:
1. 创建 `api/user/` 和 `api/admin/` 目录
2. 创建 `__init__.py` 文件
3. 迁移 `billing_api.py` → `api/user/billing.py`
4. 更新测试文件
5. 验证功能

**产出**:
- ✅ api/user/__init__.py
- ✅ api/user/billing.py
- ✅ tests/api/user/test_billing.py

### Day 2: Generation + Webhooks API

**任务**:
1. 迁移 `generation_api.py` → `api/user/generation.py`
2. 迁移 `webhooks_api.py` → `api/user/webhooks.py`
3. 更新测试文件
4. 验证功能

**产出**:
- ✅ api/user/generation.py
- ✅ api/user/webhooks.py
- ✅ tests/api/user/test_generation.py
- ✅ tests/api/user/test_webhooks.py

### Day 3-4: Projects API

**任务**:
1. 迁移 `projects_api.py` → `api/user/projects.py` (10 个端点)
2. 更新测试文件 (35 个测试用例)
3. 验证所有功能

**产出**:
- ✅ api/user/projects.py
- ✅ tests/api/user/test_projects.py

### Day 5: Marketplace API

**任务**:
1. 迁移 `marketplace_api.py` → `api/user/marketplace.py` (11 个端点)
2. 更新测试文件 (34 个测试用例)
3. 验证所有功能
4. Week 1 总结

**产出**:
- ✅ api/user/marketplace.py
- ✅ tests/api/user/test_marketplace.py
- 📄 Week 1 完成报告

---

## ✅ 验收标准

### 每个迁移文件必须满足:

1. **URL 前缀正确**
   ```python
   # User API
   router = APIRouter(prefix="/api/v2/user/{module}", ...)

   # Admin API
   router = APIRouter(prefix="/api/v2/admin/{module}", ...)
   ```

2. **Tag 命名规范**
   ```python
   # User API
   tags=["user-{module}-v2"]

   # Admin API
   tags=["admin-{module}-v2"]
   ```

3. **测试覆盖率 100%**
   - 所有端点都有对应测试
   - 所有测试用例都通过

4. **文档完整性**
   - 模块级 docstring
   - 每个端点的 docstring
   - 参数说明
   - 返回值说明

5. **向后兼容**
   - 旧 URL 仍然可用 (通过保留旧文件)
   - 旧测试仍然通过

---

## 📊 进度追踪

### 总体进度

| 阶段 | 文件数 | 端点数 | 完成 | 进度 |
|------|--------|--------|------|------|
| Week 1 | 5 | 29 | 0 | 0% |
| Week 2 | 8 | 24 | 0 | 0% |
| Week 3 | 12 | ~50 | 0 | 0% |
| **总计** | **25** | **~103** | **0** | **0%** |

### Week 1 详细进度

| Day | 文件 | 端点 | 状态 | 备注 |
|-----|------|------|------|------|
| Day 1 | billing.py | 2 | ⏳ | 基础结构 + Billing |
| Day 2 | generation.py, webhooks.py | 6 | ⏳ | P0 核心 API |
| Day 3 | projects.py (part 1) | 5 | ⏳ | 前 5 个端点 |
| Day 4 | projects.py (part 2) | 5 | ⏳ | 后 5 个端点 |
| Day 5 | marketplace.py | 11 | ⏳ | P1 高频 API |

---

## 🚨 风险和注意事项

### 风险点

1. **URL 变化导致前端不兼容**
   - **缓解**: 保留旧 URL 重定向
   - **缓解**: Feature Flag 灰度发布

2. **测试迁移遗漏**
   - **缓解**: 每个文件都要求 100% 测试覆盖
   - **缓解**: CI/CD 自动检查

3. **依赖关系错误**
   - **缓解**: 每次迁移后立即运行完整测试套件
   - **缓解**: 保持 DDD 层依赖不变

4. **权限控制变化**
   - **缓解**: User API 保持原有权限
   - **缓解**: Admin API 添加 `require_admin` 依赖

### 关键决策

1. **是否删除旧文件?**
   - ❌ Week 1-3 不删除
   - ✅ Stage 5 统一删除
   - 原因: 保持向后兼容,便于灰度发布

2. **是否同时迁移测试?**
   - ✅ 必须同时迁移
   - 原因: 确保新 API 功能正确

3. **是否更新 DDD 层?**
   - ❌ 不更新
   - 原因: 只调整路由层,业务逻辑不变

---

## 📚 参考文档

- [Phase 9-10 总体规划](./018-phase-9-10-execution-plan.md)
- [v1/v2 API 对比](./020-v1-v2-api-comparison-corrected.md)
- [Stage 1-2 完成总结](./021-stage-1-2-completion-summary.md)
- [DDD 架构设计](../shared/[重构后]System-Refactoring-Proposal-v2.md)

---

**创建日期**: 2026-01-08
**下一步**: 开始 Week 1 Day 1 - 创建基础结构 + Billing API
