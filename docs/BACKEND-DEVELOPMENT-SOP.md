# Make Decodables 后端开发 SOP (标准操作流程)

> 从当前状态到生产就绪的完整执行计划

**文档版本**: v1.0
**更新日期**: 2026-01-07
**执行者**: 后端团队
**预计周期**: 4-6 周

---

## 📋 目录

1. [当前状态评估](#1-当前状态评估)
2. [架构迁移完成度](#2-架构迁移完成度)
3. [Phase 1: API 层完善 (Week 1-2)](#phase-1-api-层完善-week-1-2)
4. [Phase 2: 测试覆盖 (Week 2-3)](#phase-2-测试覆盖-week-2-3)
5. [Phase 3: 集成测试 (Week 3-4)](#phase-3-集成测试-week-3-4)
6. [Phase 4: 清理 v1 代码 (Week 4)](#phase-4-清理-v1-代码-week-4)
7. [Phase 5: 生产部署 (Week 5)](#phase-5-生产部署-week-5)
8. [Phase 6: 监控与优化 (Week 6+)](#phase-6-监控与优化-week-6)
9. [检查清单](#检查清单)
10. [风险评估与应对](#风险评估与应对)

---

## 1. 当前状态评估

### 1.1 已完成的工作 ✅

#### 架构层完成度

| 层级 | 状态 | 完成度 | 备注 |
|------|------|--------|------|
| **Core 层** | ✅ 完成 | 100% | exceptions, cache, database, auth, middleware, utils |
| **Shared 层** | ✅ 完成 | 100% | ai, payment, storage |
| **Domains 层** | ✅ 完成 | 100% | billing, identity, creation, marketplace, platform |
| **Infrastructure 层** | ✅ 完成 | 100% | database, cache, storage, ai, payment |
| **Application 层** | ✅ 完成 | 100% | commands, queries, use cases |
| **API 层** | ✅ 完成 | 100% | 38 个 API 文件 + 14 个 Admin API |

#### API 迁移完成度

| 模块 | v2 API 文件数 | 状态 |
|------|--------------|------|
| 公开 API | 23 个 | ✅ 完成 |
| Admin API | 14 个 | ✅ 完成 |
| Webhooks | 1 个 | ✅ 完成 |
| 总计 | **38 个** | ✅ 完成 |

### 1.2 待完成的工作 ⏳

| 任务 | 优先级 | 预计工时 | 状态 |
|------|--------|----------|------|
| **API 集成测试** | 🔴 高 | 16h | ⏳ 待开始 |
| **单元测试补全** | 🔴 高 | 24h | ⏳ 部分完成 |
| **main.py 路由注册** | 🔴 高 | 2h | ⏳ 待开始 |
| **环境变量迁移** | 🟡 中 | 4h | ⏳ 待开始 |
| **数据库迁移验证** | 🟡 中 | 8h | ⏳ 待开始 |
| **删除 v1 代码** | 🟢 低 | 2h | ⏳ 待命令 |
| **性能测试** | 🟡 中 | 8h | ⏳ 待开始 |
| **文档完善** | 🟢 低 | 8h | ⏳ 进行中 |

### 1.3 当前代码结构

```
decodables/
├── core/              ✅ 框架层 (100% 完成)
├── shared/            ✅ 共享层 (100% 完成)
├── domains/           ✅ 领域层 (100% 完成)
├── infrastructure/    ✅ 基础设施层 (100% 完成)
├── application/       ✅ 应用层 (100% 完成)
├── api/               ✅ API v2 层 (100% 完成)
│   ├── __init__.py
│   ├── *_api.py       (23 个公开 API)
│   ├── webhooks_api.py
│   └── admin/         (14 个 Admin API)
├── routers/           ⚠️ 待删除的 v1 代码 (40 个文件)
├── services/          ⚠️ 待重构的旧服务 (逐步废弃)
├── main.py            ⚠️ 待更新 (注册 v2 路由)
└── tests/             ⏳ 测试覆盖 60% (目标 80%)
```

---

## 2. 架构迁移完成度

### 2.1 DDD 架构分层对比

| 传统分层 (v1) | DDD 分层 (v2) | 迁移状态 |
|--------------|--------------|----------|
| `routers/` | `api/` | ✅ 100% |
| `services/` | `domains/` + `application/` + `infrastructure/` | ✅ 90% |
| `utils/` | `core/utils/` | ✅ 100% |
| `middleware/` | `core/middleware/` | ✅ 100% |
| - | `shared/` (ai, payment, storage) | ✅ 100% |

### 2.2 依赖倒置实现

```
✅ api → application → domains ← infrastructure
                         ↓
                  core + shared
```

**验证方式**:
```bash
# 检查是否有反向依赖
grep -r "from infrastructure" domains/
# 应该返回空 (domains 不应依赖 infrastructure)

grep -r "from routers" api/
# 应该返回空 (api 不应依赖旧 routers)
```

---

## Phase 1: API 层完善 (Week 1-2)

**目标**: 确保 v2 API 完全可用，main.py 正确注册所有路由

### 1.1 更新 main.py (2h)

**当前问题**: main.py 可能仍在使用旧的 routers

**操作步骤**:

1. **检查当前 main.py**:
   ```bash
   cat main.py | grep -A 10 "include_router"
   ```

2. **更新为 v2 路由**:
   ```python
   # main.py

   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware

   from api import api_router  # ✅ 使用新的 v2 API
   from core.middleware import (
       request_id_middleware,
       logging_middleware,
   )

   app = FastAPI(
       title="Make Decodables API",
       version="2.0.0",
       description="DDD-based API with clean architecture",
   )

   # Middleware
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   app.middleware("http")(request_id_middleware)
   app.middleware("http")(logging_middleware)

   # Include API v2 router
   app.include_router(api_router)  # ✅ 所有 v2 API

   # Health check
   @app.get("/health")
   def health_check():
       return {"status": "healthy", "version": "2.0.0"}

   # ❌ 移除所有旧的 routers 导入
   # from routers import xxx  # 删除
   ```

3. **验证路由注册**:
   ```bash
   # 启动服务
   uvicorn main:app --reload

   # 访问 API 文档
   open http://localhost:8000/docs

   # 确认所有 v2 端点存在
   curl http://localhost:8000/openapi.json | jq '.paths | keys'
   ```

**检查清单**:
- [ ] main.py 不再导入 `routers/` 中的任何模块
- [ ] 所有 v2 API 端点在 Swagger 中可见
- [ ] `/api/v2/user/profile` 等端点可正常访问
- [ ] `/api/v2/admin/users` 等端点需要管理员权限
- [ ] `/api/v2/webhooks/clerk` 和 `/stripe` 可接收请求

### 1.2 验证所有 API 端点 (4h)

**创建端点验证脚本**:

```bash
# scripts/verify_api_endpoints.sh

#!/bin/bash

BASE_URL="http://localhost:8000"
TOKEN="your_test_token"

echo "🔍 验证 API v2 端点..."

# 公开 API
curl -f "$BASE_URL/api/v2/user/profile" -H "Authorization: Bearer $TOKEN" || echo "❌ User API 失败"
curl -f "$BASE_URL/api/v2/credits" -H "Authorization: Bearer $TOKEN" || echo "❌ Credits API 失败"
curl -f "$BASE_URL/api/v2/projects" -H "Authorization: Bearer $TOKEN" || echo "❌ Projects API 失败"

# Admin API
curl -f "$BASE_URL/api/v2/admin/users" -H "Authorization: Bearer $ADMIN_TOKEN" || echo "❌ Admin Users API 失败"

# Webhooks (POST only)
echo "⏭️  Webhooks 需要有效签名，跳过自动验证"

echo "✅ API 端点验证完成"
```

**检查清单**:
- [ ] 23 个公开 API 端点可访问
- [ ] 14 个 Admin API 端点可访问 (需管理员权限)
- [ ] 认证中间件正常工作
- [ ] 限流中间件正常工作
- [ ] CORS 配置正确

### 1.3 环境变量迁移 (4h)

**操作步骤**:

1. **检查旧环境变量**:
   ```bash
   grep -r "os.getenv" routers/ services/ | grep -v "__pycache__"
   ```

2. **创建环境变量清单**:
   ```bash
   # .env.example

   # === Database ===
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_KEY=eyJxxx

   # === Authentication ===
   CLERK_PUBLISHABLE_KEY=pk_xxx
   CLERK_SECRET_KEY=sk_xxx
   CLERK_WEBHOOK_SECRET=whsec_xxx

   # === Payment ===
   STRIPE_SECRET_KEY=sk_test_xxx
   STRIPE_WEBHOOK_SECRET=whsec_xxx
   STRIPE_STARTER_MONTHLY_PRICE_ID=price_xxx
   STRIPE_PRO_MONTHLY_PRICE_ID=price_xxx

   # === AI Services ===
   FAL_KEY=xxx
   OPENAI_API_KEY=sk-xxx

   # === Storage ===
   CLOUDFLARE_ACCOUNT_ID=xxx
   CLOUDFLARE_R2_ACCESS_KEY_ID=xxx
   CLOUDFLARE_R2_SECRET_ACCESS_KEY=xxx

   # === Cache ===
   REDIS_URL=redis://localhost:6379

   # === Feature Flags ===
   ENABLE_EXPERIMENTS=true
   ENABLE_CACHE=true
   ```

3. **验证所有环境变量已加载**:
   ```python
   # scripts/check_env.py

   import os

   REQUIRED_VARS = [
       "SUPABASE_URL",
       "SUPABASE_SERVICE_KEY",
       "CLERK_SECRET_KEY",
       "STRIPE_SECRET_KEY",
       # ... 添加所有必需变量
   ]

   missing = [var for var in REQUIRED_VARS if not os.getenv(var)]

   if missing:
       print(f"❌ 缺少环境变量: {missing}")
       exit(1)
   else:
       print("✅ 所有环境变量已配置")
   ```

**检查清单**:
- [ ] `.env.example` 包含所有必需变量
- [ ] 本地 `.env` 文件配置正确
- [ ] Staging 环境变量已同步
- [ ] Production 环境变量已准备 (但未启用)

---

## Phase 2: 测试覆盖 (Week 2-3)

**目标**: 测试覆盖率从 60% 提升到 80%+

### 2.1 单元测试补全 (16h)

**当前测试覆盖**:
```bash
pytest --cov=. --cov-report=term-missing
```

**测试优先级**:

| 模块 | 当前覆盖率 | 目标覆盖率 | 优先级 |
|------|-----------|-----------|--------|
| domains/billing | 70% | 90% | 🔴 高 |
| domains/identity | 60% | 85% | 🔴 高 |
| domains/creation | 50% | 80% | 🔴 高 |
| application/commands | 40% | 80% | 🔴 高 |
| application/queries | 40% | 80% | 🔴 高 |
| infrastructure/* | 30% | 70% | 🟡 中 |
| api/* | 0% | 70% | 🔴 高 |

**测试模板**:

```python
# tests/api/test_user_api.py

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    return {"Authorization": "Bearer test_token"}

def test_get_user_profile(auth_headers, mock_db):
    """Test GET /api/v2/user/profile"""
    response = client.get("/api/v2/user/profile", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "user_code" in data
    assert "tier" in data

def test_update_user_profile(auth_headers, mock_db):
    """Test PUT /api/v2/user/profile"""
    payload = {"username": "newusername"}
    response = client.put(
        "/api/v2/user/profile",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["username"] == "newusername"
```

**检查清单**:
- [ ] 每个 API 端点至少有 1 个测试
- [ ] 每个 Domain 聚合根有完整测试
- [ ] 每个 Command/Query Handler 有测试
- [ ] 关键业务逻辑有集成测试
- [ ] 测试覆盖率 ≥ 80%

### 2.2 集成测试 (8h)

**创建端到端测试**:

```python
# tests/integration/test_credits_flow.py

def test_credits_purchase_flow(test_client, test_user):
    """测试积分购买完整流程"""

    # 1. 创建 Stripe checkout session
    response = test_client.post("/api/v2/payment/checkout", json={
        "plan_type": "credits_100"
    })
    assert response.status_code == 200
    session_url = response.json()["session_url"]

    # 2. 模拟 Stripe webhook (checkout.session.completed)
    webhook_payload = create_mock_stripe_event("checkout.session.completed", {
        "metadata": {"user_id": test_user.id, "plan_type": "credits_100"}
    })

    response = test_client.post(
        "/api/v2/webhooks/stripe",
        data=webhook_payload,
        headers={"stripe-signature": "valid_signature"}
    )
    assert response.status_code == 200

    # 3. 验证积分增加
    response = test_client.get("/api/v2/credits")
    assert response.json()["credits_permanent"] == 150  # 50 初始 + 100 购买
```

**检查清单**:
- [ ] 用户注册流程测试
- [ ] 积分购买流程测试
- [ ] 订阅开通流程测试
- [ ] AI 生成流程测试
- [ ] 项目导出流程测试

---

## Phase 3: 集成测试 (Week 3-4)

**目标**: 在 Staging 环境进行完整的系统测试

### 3.1 Staging 环境部署 (4h)

**部署清单**:

1. **更新 Railway/Docker 配置**:
   ```yaml
   # railway.toml (或 docker-compose.yml)

   [build]
   builder = "NIXPACKS"

   [deploy]
   startCommand = "uvicorn main:app --host 0.0.0.0 --port 8000"
   healthcheckPath = "/health"

   [[envVars]]
   # 所有环境变量从 Railway Dashboard 配置
   ```

2. **部署步骤**:
   ```bash
   # 推送到 staging 分支
   git checkout -b staging
   git push origin staging

   # 触发 Railway 部署
   railway up --environment staging

   # 等待部署完成
   railway logs --environment staging

   # 验证健康检查
   curl https://your-staging-domain.com/health
   ```

**检查清单**:
- [ ] Staging 环境可访问
- [ ] 健康检查返回 200
- [ ] 数据库连接正常
- [ ] Redis 连接正常
- [ ] 所有环境变量已配置

### 3.2 Webhook 测试 (按照 WEBHOOK-V2-STAGING-TESTING-GUIDE.md)

**执行**:
```bash
# 按照文档逐项测试
cat docs/WEBHOOK-V2-STAGING-TESTING-GUIDE.md
```

**检查清单** (24 项):
- [ ] Clerk webhook 8 项测试通过
- [ ] Stripe webhook 8 项测试通过
- [ ] 性能指标 4 项达标
- [ ] 生产准备 4 项完成

### 3.3 性能测试 (8h)

**使用 Locust 进行负载测试**:

```python
# tests/performance/locustfile.py

from locust import HttpUser, task, between

class MakeDecodablesUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # 模拟登录
        self.client.headers = {"Authorization": "Bearer test_token"}

    @task(3)
    def get_user_profile(self):
        self.client.get("/api/v2/user/profile")

    @task(2)
    def get_credits(self):
        self.client.get("/api/v2/credits")

    @task(1)
    def list_projects(self):
        self.client.get("/api/v2/projects")
```

**运行测试**:
```bash
locust -f tests/performance/locustfile.py --host=https://staging.makedecodables.com

# 目标指标:
# - 100 并发用户
# - 响应时间 P95 < 500ms
# - 错误率 < 1%
```

**检查清单**:
- [ ] P50 响应时间 < 200ms
- [ ] P95 响应时间 < 500ms
- [ ] P99 响应时间 < 1s
- [ ] 错误率 < 1%
- [ ] 无内存泄漏

---

## Phase 4: 清理 v1 代码 (Week 4)

**⚠️ 此阶段需要明确指令才能执行**

### 4.1 确认 v2 完全可用

**前提条件** (必须全部满足):
- [ ] 所有测试通过 (单元 + 集成 + 性能)
- [ ] Staging 环境稳定运行 7 天
- [ ] 无关键 Bug
- [ ] 性能指标达标
- [ ] 前端已完成对接测试

### 4.2 删除 v1 代码 (2h)

**⚠️ 需要明确指令: "删除 v1 代码"**

**操作步骤**:

```bash
# 1. 创建备份分支
git checkout -b backup-v1-code
git push origin backup-v1-code

# 2. 回到 develop 分支
git checkout develop

# 3. 删除 v1 目录和文件
rm -rf routers/
rm -rf services/  # (部分保留，逐步迁移)

# 4. 更新 imports (检查是否有遗漏)
grep -r "from routers" . --exclude-dir=.git
grep -r "from services" . --exclude-dir=.git

# 5. 提交删除
git add -A
git commit -m "chore: remove v1 routers and legacy code

All functionality migrated to api/ layer with DDD architecture.
Backup preserved in backup-v1-code branch.

Breaking changes:
- Removed routers/ directory (40 files)
- Removed legacy services/ (replaced by domains/, application/, infrastructure/)

Migration complete: 100%
Test coverage: 80%+
"

# 6. 推送
git push origin develop
```

**删除清单**:
- [ ] `routers/` 目录 (40 个文件)
- [ ] `services/` 中已迁移的模块
- [ ] 旧的测试文件 (如果有)
- [ ] 废弃的配置文件

**保留清单** (暂不删除):
- [ ] `services/db_service.py` - 逐步迁移到 infrastructure
- [ ] `services/payment_service.py` - 已在 shared/payment 中
- [ ] `services/ai_*.py` - 已在 shared/ai 中
- [ ] 其他仍被引用的 services (需要逐个检查)

### 4.3 更新文档 (2h)

**删除 v1 文档引用**:

1. **更新 README.md**:
   ```markdown
   # Make Decodables Backend

   **架构**: DDD + Clean Architecture
   **API 版本**: v2.0
   **测试覆盖率**: 80%+

   ## 目录结构

   ```
   decodables/
   ├── core/              # 框架层
   ├── shared/            # 共享层
   ├── domains/           # 领域层 (业务核心)
   ├── application/       # 应用层 (用例编排)
   ├── infrastructure/    # 基础设施层
   ├── api/               # API 层 (v2)
   └── tests/             # 测试
   ```
   ```

2. **更新 API 文档**:
   - 移除所有 v1 端点说明
   - 标注所有端点为 v2
   - 更新示例代码

**检查清单**:
- [ ] README.md 不再提及 v1
- [ ] API 文档只包含 v2 端点
- [ ] 架构图更新为 DDD 架构
- [ ] 部署文档更新

---

## Phase 5: 生产部署 (Week 5)

**目标**: v2 API 上线生产环境

### 5.1 生产环境准备 (8h)

**部署清单**:

1. **数据库迁移验证**:
   ```bash
   # 在生产副本上测试所有迁移
   psql $DATABASE_URL_STAGING < migrations/0001_initial.sql
   psql $DATABASE_URL_STAGING < migrations/0002_add_experiments.sql
   # ... 所有迁移

   # 验证数据完整性
   python scripts/verify_database.py
   ```

2. **环境变量配置**:
   ```bash
   # Railway Dashboard → Production Environment → Variables

   # 必需变量 (逐个检查)
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_KEY=***
   CLERK_SECRET_KEY=***
   STRIPE_SECRET_KEY=sk_live_***  # ⚠️ 使用 Live mode
   STRIPE_WEBHOOK_SECRET=whsec_***  # ⚠️ 生产环境 secret
   # ... 其他变量
   ```

3. **监控配置**:
   ```yaml
   # sentry.yaml
   dsn: https://xxx@sentry.io/xxx
   environment: production
   traces_sample_rate: 0.1
   ```

**检查清单**:
- [ ] 数据库迁移在生产副本上测试通过
- [ ] 所有环境变量配置为生产值
- [ ] Sentry 监控已配置
- [ ] 日志聚合已配置 (Datadog/LogRocket)
- [ ] 告警规则已设置

### 5.2 灰度发布 (4h)

**发布策略**: 使用 feature flag 控制流量

```python
# config.py

ENABLE_V2_API = os.getenv("ENABLE_V2_API", "false").lower() == "true"

# main.py

if ENABLE_V2_API:
    app.include_router(api_router)  # v2 API
else:
    # 如果需要回滚，可以临时启用 v1
    pass
```

**发布步骤**:

1. **10% 流量**:
   ```bash
   # Railway Dashboard → Production → Environment Variables
   ENABLE_V2_API=true
   TRAFFIC_PERCENTAGE=10
   ```

2. **监控 1 小时**:
   - 错误率 < 1%
   - P95 响应时间 < 500ms
   - 无严重告警

3. **50% 流量**:
   ```bash
   TRAFFIC_PERCENTAGE=50
   ```

4. **监控 4 小时**:
   - 同上

5. **100% 流量**:
   ```bash
   TRAFFIC_PERCENTAGE=100
   ```

**检查清单**:
- [ ] 10% 流量运行稳定 1h
- [ ] 50% 流量运行稳定 4h
- [ ] 100% 流量运行稳定 24h
- [ ] 无性能劣化
- [ ] 无数据丢失

### 5.3 Webhook 切换 (按照 WEBHOOK-V2-STAGING-TESTING-GUIDE.md)

**生产环境切换步骤**:

1. **Clerk 生产 webhook**:
   - Dashboard → Production → Webhooks
   - 添加 `https://api.makedecodables.com/api/v2/webhooks/clerk`
   - 订阅事件
   - 复制 signing secret 到环境变量

2. **Stripe 生产 webhook**:
   - Dashboard → Live mode → Webhooks
   - 添加 `https://api.makedecodables.com/api/v2/webhooks/stripe`
   - 订阅事件
   - 复制 signing secret 到环境变量

3. **观察期 7 天**:
   - 监控 webhook 成功率
   - 验证支付流程正常
   - 验证用户注册正常

**检查清单**:
- [ ] Clerk webhook 生产环境配置完成
- [ ] Stripe webhook 生产环境配置完成
- [ ] Webhook 成功率 > 99%
- [ ] 7 天观察期无问题

---

## Phase 6: 监控与优化 (Week 6+)

**目标**: 持续监控，优化性能

### 6.1 监控指标

**关键指标 (每日检查)**:

| 指标 | 目标值 | 告警阈值 |
|------|--------|----------|
| API 可用性 | > 99.9% | < 99.5% |
| P95 响应时间 | < 500ms | > 1s |
| 错误率 | < 0.1% | > 1% |
| Webhook 成功率 | > 99% | < 95% |
| 数据库连接池 | < 80% | > 90% |
| Redis 命中率 | > 90% | < 80% |

**监控工具**:
- **Sentry**: 错误追踪
- **Datadog/New Relic**: APM 性能监控
- **Railway Metrics**: 基础设施监控
- **Supabase Dashboard**: 数据库性能

### 6.2 性能优化

**优化清单** (按需执行):

1. **数据库优化**:
   - [ ] 添加缺失的索引
   - [ ] 优化慢查询 (> 100ms)
   - [ ] 实施连接池优化

2. **缓存优化**:
   - [ ] 识别高频查询
   - [ ] 实施 Redis 缓存
   - [ ] 设置合理的 TTL

3. **API 优化**:
   - [ ] 实施响应压缩
   - [ ] 优化序列化性能
   - [ ] 实施请求批处理

### 6.3 持续改进

**每周**:
- [ ] 审查错误日志
- [ ] 检查性能指标
- [ ] 优化慢端点

**每月**:
- [ ] 代码审查
- [ ] 安全审计
- [ ] 依赖更新

**每季度**:
- [ ] 架构评审
- [ ] 容量规划
- [ ] 灾难恢复演练

---

## 检查清单

### 总体进度

- [ ] **Phase 1**: API 层完善 (Week 1-2)
  - [ ] 更新 main.py
  - [ ] 验证所有端点
  - [ ] 环境变量迁移

- [ ] **Phase 2**: 测试覆盖 (Week 2-3)
  - [ ] 单元测试 ≥ 80%
  - [ ] 集成测试完成

- [ ] **Phase 3**: 集成测试 (Week 3-4)
  - [ ] Staging 部署
  - [ ] Webhook 测试 (24 项)
  - [ ] 性能测试通过

- [ ] **Phase 4**: 清理 v1 代码 (Week 4)
  - [ ] ⚠️ 需要明确指令
  - [ ] 删除 routers/
  - [ ] 更新文档

- [ ] **Phase 5**: 生产部署 (Week 5)
  - [ ] 灰度发布 (10% → 50% → 100%)
  - [ ] Webhook 生产切换
  - [ ] 7 天观察期

- [ ] **Phase 6**: 监控与优化 (Week 6+)
  - [ ] 监控指标达标
  - [ ] 性能优化完成
  - [ ] 持续改进机制建立

---

## 风险评估与应对

### 高风险项

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| **数据库迁移失败** | 中 | 高 | 在生产副本上充分测试，准备回滚脚本 |
| **性能不达标** | 低 | 高 | Staging 环境充分负载测试，准备扩容方案 |
| **Webhook 丢失** | 低 | 高 | 幂等性机制 + Stripe/Clerk 自动重试 |
| **前后端对接问题** | 中 | 中 | 提前与前端同步 API 变更，提供 Postman collection |

### 回滚计划

**触发条件**:
- 错误率 > 5%
- P95 响应时间 > 2s
- 关键功能不可用
- 数据丢失/损坏

**回滚步骤**:
1. 立即将流量切回 0% (如使用 feature flag)
2. 通知团队
3. 排查问题根因
4. 修复后重新发布
5. 或回滚代码到上一个稳定版本

---

## 附录

### A. 快速命令参考

```bash
# 本地开发
uvicorn main:app --reload

# 运行测试
pytest --cov=. --cov-report=html

# 检查代码质量
flake8 .
black .
mypy .

# 部署到 staging
git push origin staging

# 部署到 production
git push origin main

# 查看日志
railway logs --environment production

# 数据库迁移
psql $DATABASE_URL < migrations/latest.sql
```

### B. 联系人

| 角色 | 负责人 | 联系方式 |
|------|--------|----------|
| 后端负责人 | TBD | backend@makedecodables.com |
| DevOps | TBD | devops@makedecodables.com |
| 前端负责人 | TBD | frontend@makedecodables.com |

---

**版本历史**:
- v1.0 (2026-01-07): 初始版本
- v1.1 (TBD): 根据执行反馈更新

**审批**:
- [ ] 后端负责人
- [ ] 技术负责人
- [ ] 产品负责人
