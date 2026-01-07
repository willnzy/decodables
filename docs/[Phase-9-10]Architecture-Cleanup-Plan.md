# 后台架构完整清理计划 (Phase 9-10)

> **文档版本**: 2.0.0 (已修正)
> **创建日期**: 2026-01-07
> **状态**: Phase 8 已完成，Phase 9-10 待执行
> **作者**: Claude Sonnet 4.5
> **⚠️ 重要更正**: 本文档 v1.0.0 存在严重架构理解错误，已在 v2.0.0 修正

---

## ⚠️ 架构理解纠正

### 错误理解 (v1.0.0)
- ❌ 认为 `api/` 是旧代码，应该删除
- ❌ 认为 `routers/` 是正确位置，应该保留

### 正确理解 (v2.0.0)
- ✅ `api/` = **NEW DDD v2 架构** (使用 Commands/Queries，URL: `/api/v2/*`)
- ✅ `routers/` = **OLD v1 架构** (直接调用 services/db，URL: `/api/*`)
- ✅ 两套系统目前**并行运行**在生产环境

### 证据

#### 1. URL 模式差异

```python
# api/ - 新架构 (v2)
api/billing_api.py:     router = APIRouter(prefix="/api/v2/billing", tags=["billing-v2"])
api/credits_api.py:     router = APIRouter(prefix="/api/v2/credits", tags=["credits-v2"])
api/marketplace_api.py: router = APIRouter(prefix="/api/v2/marketplace", tags=["marketplace-v2"])

# routers/ - 旧架构 (v1/v3)
routers/marketplace.py: router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])
routers/projects.py:    router = APIRouter(prefix="/api/projects", tags=["projects"])
routers/payment.py:     router = APIRouter(prefix="/api/payment", tags=["payment"])
```

#### 2. 代码调用方式差异

```python
# api/ - 使用 Commands/Queries (DDD)
# api/billing_api.py
from application.queries.billing import GetUserCreditsQuery
from application.commands.billing import DeductCreditsCommand

@router.get("/credits")
async def get_credits(user_id: str = Depends(get_current_user)):
    query = GetUserCreditsQuery(user_id=user_id)
    result = await get_user_credits_handler(query)
    return result

# routers/ - 直接调用 services.db (旧方式)
# routers/marketplace.py
from services import db as services_db

@router.get("/listings")
async def get_listings(user_id: str = Depends(get_current_user)):
    listings = await services_db.get_marketplace_listings(limit=100)
    return listings
```

#### 3. app.py 同时注册两套系统

```python
# app.py (lines 208-309)

# OLD v1 系统 - 36 个 routers
from routers.marketplace import router as marketplace_router
from routers.projects import router as projects_router
# ... 34 more routers
app.include_router(marketplace_router)
app.include_router(projects_router)
# ... 34 more

# NEW v2 DDD 系统 - 1 个聚合 router
from api import api_router as ddd_api_router
app.include_router(ddd_api_router)  # 包含 24 个 v2 子路由
```

#### 4. 设计文档明确定义

`docs/BACKEND_ARCHITECTURE_GUIDE.md` 第 2.6 节:

```markdown
### 2.6 api/ - API 层 (HTTP 入口)

**定义**: HTTP 路由层，处理请求验证、响应格式化，调用 application 层。

**职责**:
- ✅ 路由定义 (`@router.post("/credits/deduct")`)
- ✅ 请求参数验证 (Pydantic models)
- ✅ 响应格式化 (200/400/500 等)
- ✅ 认证授权 (调用 core/auth)
- ✅ 调用 application commands/queries

**示例**:
```python
# ✅ api/routers/credits.py
@router.post("/credits/deduct")
async def deduct_credits(
    request: DeductCreditsRequest,
    user_id: str = Depends(get_current_user_id),
    repo: ICreditRepository = Depends(get_credit_repo)
):
    # 调用 application 层
    command = DeductCreditsCommand(...)
    result = await deduct_credits_handler(command, repo)
    return {"success": True, "transaction": result.dict()}
```
```

---

## 📊 当前状态总览 (已修正)

### 代码量统计

| 层级 | 文件数 | 代码行数 | 状态 | 说明 |
|------|--------|----------|------|------|
| **✅ DDD 正确层** |  |  |  |  |
| `core/` | 28 | 2,893 | ✅ 已完成 | 框架层 (Auth/Cache/Database/Exceptions/Middleware/Utils) |
| `shared/` | 15 | 1,963 | ✅ 已完成 | 共享层 (AI/Payment/Storage 抽象) |
| `domains/` | 46 | 7,216 | ✅ 已完成 | 6个领域 (Billing/Identity/Creation/Marketplace/Platform/Content) |
| `application/` | 18 | 2,743 | ✅ 已完成 | 应用层 (Commands/Queries/Handlers) |
| `infrastructure/` | 26 | 7,082 | ✅ 已完成 | 基础设施 (Repositories/db_compat/logging) |
| `api/` | 40 | 9,765 | ✅ **正确** | **NEW v2 DDD API** (使用 Commands/Queries) |
| **小计** | **173** | **31,662** |  |  |
| | | | | |
| **❌ 需要处理的旧层** |  |  |  |  |
| `routers/` | 40 | 8,756 | ❌ **应迁移到 api/** | OLD v1 API (直接调用 services/db) |
| `services/` | 57 | 11,060 | ❌ 应拆分 | 旧服务层，应拆分到 domains/application |
| **小计** | **97** | **19,816** |  |  |
| | | | | |
| **总计** | **270** | **51,478** |  |  |

### 架构对比

| 特性 | api/ (NEW v2) | routers/ (OLD v1) |
|------|--------------|-------------------|
| URL 模式 | `/api/v2/*` | `/api/*` (无v2) |
| 调用方式 | Commands/Queries | 直接调用 services.db |
| 架构模式 | DDD 三层架构 | 传统 MVC |
| 依赖注入 | ✅ 使用 container | ❌ 硬编码导入 |
| 测试性 | ✅ 易于测试 | ❌ 难以 mock |
| 状态 | ✅ 保留并扩展 | ❌ 应迁移 |

---

## 🔴 问题 1: `routers/` 使用旧架构，应迁移到 `api/`

### 问题描述
- `routers/` 目录有 40 个文件，8,756 行代码
- 使用旧的直接调用 `services.db` 的方式
- 不符合 DDD 架构原则
- `app.py` 中注册了 36 个旧路由 + 1 个新 DDD 路由

### routers/ 目录结构
```
routers/
├── 36 个业务路由文件
│   ├── marketplace.py          → 应迁移到 api/marketplace_api.py
│   ├── projects.py             → 应迁移到 api/projects_api.py
│   ├── payment.py              → 应迁移到 api/payment_api.py
│   ├── analytics.py            → 应迁移到 api/analytics_api.py
│   ├── campaigns.py            → 应迁移到 api/campaigns_api.py
│   ├── resources.py            → 应迁移到 api/resources_api.py
│   ├── generations.py          → 应迁移到 api/generations_api.py
│   ├── logs.py                 → 应迁移到 api/logs_api.py
│   ├── config.py               → 应迁移到 api/config_api.py
│   ├── themes.py               → 应迁移到 api/themes_api.py
│   ├── tools.py                → 应迁移到 api/tools_api.py
│   ├── webhooks.py             → 应迁移到 api/webhooks_api.py
│   ├── generation_*.py (4个)   → 应整合到 api/generation_api.py
│   ├── user_*.py (2个)         → 应整合到 api/user_api.py
│   ├── experiments_public.py   → 应迁移到 api/experiments_api.py
│   └── admin_*.py (14个)       → 应迁移到 api/admin/
│
└── 4 个 WebSocket 路由
    └── websocket_*.py          → 应迁移到 api/websocket_api.py
```

### 已存在对应关系

**17 对文件已经有 v2 版本**:

| routers/ (OLD) | api/ (NEW) | 状态 |
|----------------|------------|------|
| analytics.py | analytics_api.py | ✅ v2 存在 |
| campaigns.py | campaigns_api.py | ✅ v2 存在 |
| config.py | config_api.py | ✅ v2 存在 |
| generations.py | generations_api.py | ✅ v2 存在 |
| logs.py | logs_api.py | ✅ v2 存在 |
| marketplace.py | marketplace_api.py | ✅ v2 存在 |
| payment.py | payment_api.py | ✅ v2 存在 |
| projects.py | projects_api.py | ✅ v2 存在 |
| resources.py | resources_api.py | ✅ v2 存在 |
| themes.py | themes_api.py | ✅ v2 存在 |
| tools.py | tools_api.py | ✅ v2 存在 |
| webhooks.py | webhooks_api.py | ✅ v2 存在 |
| generation_*.py | generation_api.py | ✅ v2 存在 |
| experiments_public.py | experiments_api.py | ✅ v2 存在 |

**尚未迁移的路由** (需要创建 v2 版本):

| routers/ (OLD) | 需要创建的 api/ (NEW) |
|----------------|-----------------------|
| user_profile.py | user_api.py (扩展) |
| user_assets.py | assets_api.py (扩展) |
| admin_*.py (14个) | admin/*.py (14个) |

### 影响
- **架构不一致**: 两套并行的 API 系统
- **维护成本**: 需要维护两套代码
- **技术债务**: 旧代码难以测试和重构

### 解决方案
**逐步迁移 `routers/` → `api/`**
- ✅ 17 对已有 v2 版本的路由：测试后删除 v1
- ⚠️ 23 个尚未迁移的路由：创建 v2 版本后删除 v1

---

## 🟡 问题 2: `services/` 层不符合 DDD 架构

### 问题描述
- `services/` 有 57 个文件，11,060 行代码
- 混合了业务逻辑、应用服务、基础设施代码
- 违反 DDD 分层原则

### services/ 目录结构
```
services/
├── 14 个根级服务文件
│   ├── access_control.py          → ✅ 已迁移到 domains/shared/
│   ├── ai_chat_service.py         → 应移到 application/services/
│   ├── ai_report_service.py       → 应移到 application/services/
│   ├── analytics_service.py       → 应移到 domains/platform/
│   ├── capi_service.py            → 应移到 application/services/
│   ├── config_service.py          → 应移到 domains/platform/
│   ├── db_service.py              → ✅ 已完成 (兼容层聚合器)
│   ├── experiment_ai_service.py   → 应移到 domains/platform/
│   ├── experiment_service.py      → 应移到 domains/platform/
│   ├── generation_helpers.py      → 应移到 application/services/
│   ├── payment_service.py         → 应移到 domains/billing/
│   ├── rate_limiter.py            → 应移到 infrastructure/
│   ├── setup_assistant.py         → 应移到 application/services/
│   └── system_resource_helpers.py → 应移到 domains/content/
│
└── 7 个子目录
    ├── ai/ (20 files, 5,213 lines)      → ✅ 已在 shared/ai/
    ├── ai_reports/ (4 files, 532 lines) → 应移到 application/
    ├── capi/ (4 files, 443 lines)       → 应移到 application/
    ├── db/ (1 file, 236 lines)          → ✅ 已完成迁移
    ├── experiments/ (7 files, 929 lines)→ 应移到 domains/platform/
    ├── task_queue/ (4 files, 845 lines) → 应移到 infrastructure/
    └── websocket/ (2 files, 342 lines)  → 应移到 infrastructure/
```

### 需要拆分的模块

#### 2.1 应移到 `domains/` 的业务逻辑
```
services/access_control.py         → ✅ domains/shared/access_control.py (已完成)
services/analytics_service.py      → domains/platform/analytics_service.py
services/config_service.py         → domains/platform/config_service.py
services/experiment_service.py     → domains/platform/experiment_service.py
services/experiment_ai_service.py  → domains/platform/experiment_ai_service.py
services/payment_service.py        → domains/billing/payment_service.py
services/system_resource_helpers.py→ domains/content/resource_helpers.py
services/experiments/              → domains/platform/experiments/
```

#### 2.2 应移到 `application/services/` 的应用服务
```
services/ai_chat_service.py        → application/services/ai_chat_service.py
services/ai_report_service.py      → application/services/ai_report_service.py
services/capi_service.py           → application/services/capi_service.py
services/generation_helpers.py     → application/services/generation_helpers.py
services/setup_assistant.py        → application/services/setup_assistant.py
services/ai_reports/               → application/services/ai_reports/
services/capi/                     → application/services/capi/
```

#### 2.3 应移到 `infrastructure/` 的基础设施
```
services/rate_limiter.py           → infrastructure/rate_limiter.py
services/task_queue/               → infrastructure/task_queue/
services/websocket/                → infrastructure/websocket/
```

#### 2.4 已经在 `shared/` 的模块 (可删除重复)
```
services/ai/                       → ✅ shared/ai/ 已存在，检查差异后删除
```

### 影响
- **架构混乱**: 业务逻辑分散在 services/ 和 domains/
- **难以测试**: 依赖关系不清晰
- **重复代码**: services/ai/ 和 shared/ai/ 可能重复

---

## 🟢 问题 3: 已完成的部分

### ✅ 已完成迁移
1. **services/db/ → infrastructure/repositories/** (Phase 8 完成)
   - 12 个旧文件删除 (2,770 行)
   - 14 个新仓储文件创建 (3,575 行)
   - db_compat.py 兼容层 (1,200+ 行, 112 函数)

2. **utils.py → domains/shared/access_control.py** (Phase 8.10 完成)
   - 权限控制逻辑移到领域层
   - 活动日志移到 infrastructure/logging/

3. **DDD 核心层全部就绪**
   - core/ (28 files): 框架层完整
   - shared/ (15 files): AI/Payment/Storage 抽象完整
   - domains/ (46 files): 6 个领域模型完整
   - application/ (18 files): Commands/Queries 完整
   - infrastructure/ (26 files): Repositories 完整

4. **api/ NEW v2 DDD API 已部分完成**
   - api/ (40 files): 24 个 v2 路由已实现
   - 使用 Commands/Queries 模式
   - URL: `/api/v2/*`

---

## 📋 完整迁移计划 (已修正)

### Phase 9: 迁移 `routers/` 到 `api/`

**优先级**: 🔴 高 (架构统一，消除技术债)

#### 步骤

##### 9.1 评估已有 v2 版本的功能完整性

对于 17 对已有 v2 的路由，逐一对比：

```bash
# 对比功能差异
diff routers/marketplace.py api/marketplace_api.py
diff routers/projects.py api/projects_api.py
# ... 重复 17 次
```

**检查清单**:
- [ ] 所有端点都已迁移
- [ ] 业务逻辑等价
- [ ] 错误处理完整
- [ ] 权限验证正确
- [ ] 测试覆盖充分

##### 9.2 补全缺失的 v2 端点

如果 v1 有但 v2 缺失的端点：

```python
# 示例: routers/marketplace.py 有 20 个端点
# api/marketplace_api.py 只有 15 个端点
# 需要补充 5 个缺失端点到 api/marketplace_api.py
```

##### 9.3 创建尚未迁移路由的 v2 版本

**需要创建的新文件** (23 个):

```bash
# User 相关 (2个)
api/user_api.py           # 整合 user_profile.py
api/assets_api.py         # 扩展 user_assets.py 功能

# Admin 相关 (14个) - 在 api/admin/ 下
api/admin/ai_admin.py              # 整合 admin_ai.py + admin_ai_models.py
api/admin/campaigns_admin.py       # 对应 admin_campaigns.py
api/admin/config_admin.py          # 对应 admin_config.py
api/admin/events_admin.py          # 对应 admin_events.py
api/admin/experiments_admin.py     # 对应 experiments_admin.py
api/admin/logs_admin.py            # 对应 admin_logs.py
api/admin/metrics_admin.py         # 对应 admin_metrics.py
api/admin/moderation_admin.py      # 对应 admin_moderation.py
api/admin/notifications_admin.py   # 对应 admin_notifications.py
api/admin/stats_admin.py           # 对应 admin_stats.py
api/admin/subscriptions_admin.py   # 对应 admin_subscriptions.py
api/admin/system_admin.py          # 对应 admin_system.py
api/admin/tasks_admin.py           # 对应 admin_tasks_mgmt.py
api/admin/users_admin.py           # 对应 admin_users.py

# Generation 相关 (整合4个文件到1个)
api/generation_api.py     # 已存在，扩展功能整合:
                          # - generation_images.py
                          # - generation_pdf.py
                          # - generation_story.py

# WebSocket (4个文件整合到1个)
api/websocket_api.py      # 已存在，确认包含所有 ws 功能

# System Resources (1个)
api/admin/system_resources_admin.py  # 对应 system_resources.py
```

##### 9.4 渐进式切换

**不要立即删除 routers/！使用特性开关渐进切换**:

```python
# app.py
USE_V2_API = os.getenv("USE_V2_API", "false").lower() == "true"

if USE_V2_API:
    # 只注册 v2 路由
    from api import api_router as ddd_api_router
    app.include_router(ddd_api_router)
else:
    # 注册两套路由 (当前状态)
    # OLD v1
    from routers.marketplace import router as marketplace_router
    # ... 36 routers
    app.include_router(marketplace_router)
    # ... 35 more

    # NEW v2
    from api import api_router as ddd_api_router
    app.include_router(ddd_api_router)
```

##### 9.5 测试和验证

```bash
# 在测试环境启用 v2
export USE_V2_API=true
uvicorn app:app

# 运行集成测试
pytest tests/integration/

# 对比 v1 和 v2 响应
python scripts/compare_v1_v2_responses.py
```

##### 9.6 生产切换

```yaml
# 分阶段切换
Week 1: 10% 流量到 v2
Week 2: 50% 流量到 v2
Week 3: 100% 流量到 v2
Week 4: 删除 routers/ 目录
```

##### 9.7 删除 routers/

```bash
# 确认 v2 稳定运行 2 周后
git rm -r routers/
git commit -m "chore: remove old v1 routers after v2 migration"
```

**预计**: 删除 40 个文件，8,756 行代码

---

### Phase 10: 拆分 `services/` 目录

**优先级**: 🟡 中 (架构清理，提升可维护性)

#### 10.1 移动基础设施代码到 `infrastructure/`

```bash
# 简单移动，依赖少
git mv services/rate_limiter.py infrastructure/rate_limiter.py
git mv services/task_queue/ infrastructure/task_queue/
git mv services/websocket/ infrastructure/websocket/

# 更新导入路径
grep -r "from services.rate_limiter" --include="*.py" | cut -d: -f1 | xargs sed -i '' 's/from services\.rate_limiter/from infrastructure.rate_limiter/g'
grep -r "from services.task_queue" --include="*.py" | cut -d: -f1 | xargs sed -i '' 's/from services\.task_queue/from infrastructure.task_queue/g'
grep -r "from services.websocket" --include="*.py" | cut -d: -f1 | xargs sed -i '' 's/from services\.websocket/from infrastructure.websocket/g'
```

**预计**: 3 个模块，~1,200 行

#### 10.2 移动应用服务到 `application/services/`

```bash
mkdir -p application/services

# 移动文件
git mv services/ai_chat_service.py application/services/ai_chat_service.py
git mv services/ai_report_service.py application/services/ai_report_service.py
git mv services/capi_service.py application/services/capi_service.py
git mv services/generation_helpers.py application/services/generation_helpers.py
git mv services/setup_assistant.py application/services/setup_assistant.py
git mv services/ai_reports/ application/services/ai_reports/
git mv services/capi/ application/services/capi/

# 更新导入路径
find . -type f -name "*.py" -exec sed -i '' 's/from services\.ai_chat_service/from application.services.ai_chat_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.ai_report_service/from application.services.ai_report_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.capi_service/from application.services.capi_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.generation_helpers/from application.services.generation_helpers/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.setup_assistant/from application.services.setup_assistant/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.ai_reports/from application.services.ai_reports/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.capi/from application.services.capi/g' {} +
```

**预计**: 7 个模块，~1,800 行

#### 10.3 移动业务逻辑到 `domains/`

```bash
# Platform domain
git mv services/analytics_service.py domains/platform/analytics_service.py
git mv services/config_service.py domains/platform/config_service.py
git mv services/experiment_service.py domains/platform/experiment_service.py
git mv services/experiment_ai_service.py domains/platform/experiment_ai_service.py
git mv services/experiments/ domains/platform/experiments/

# Billing domain
git mv services/payment_service.py domains/billing/payment_service.py

# Content domain
git mv services/system_resource_helpers.py domains/content/resource_helpers.py

# 更新导入路径
find . -type f -name "*.py" -exec sed -i '' 's/from services\.analytics_service/from domains.platform.analytics_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.config_service/from domains.platform.config_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.experiment_service/from domains.platform.experiment_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.experiment_ai_service/from domains.platform.experiment_ai_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.experiments/from domains.platform.experiments/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.payment_service/from domains.billing.payment_service/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from services\.system_resource_helpers/from domains.content.resource_helpers/g' {} +
```

**预计**: 8 个模块，~2,500 行

#### 10.4 删除重复代码

```bash
# 对比 services/ai/ 和 shared/ai/
diff -r services/ai/ shared/ai/

# 如果内容一致，删除 services/ai/
git rm -r services/ai/

# 如果有差异，合并后删除
# (需要人工检查差异)
```

**预计**: 删除 ~20 个文件，~5,213 行

#### 10.5 最终清理

```bash
# 此时 services/ 应该只剩下:
services/
├── db_service.py     # 兼容层聚合器 (保留)
└── db/               # 兼容层 (保留)
    └── db_compat.py

# 确认没有其他文件
ls -la services/
```

---

## 📈 迁移后的收益

### 代码量变化
```
删除:
  routers/          -8,756 行
  services/* (除db)  -10,824 行
  ────────────────────────
  总删除:         -19,580 行

迁移到正确位置:
  api/               +2,000 行 (补全缺失端点)
  infrastructure/    +1,200 行
  application/       +1,800 行
  domains/           +2,500 行
  ────────────────────────
  总增加:         +7,500 行

  净删除:         -12,080 行 (代码整理和去重后)
```

### 架构收益
1. **统一的 API 层**: 只有一套 DDD API (`api/`)
2. **清晰的分层**: 严格遵循 DDD 分层原则
3. **单一职责**: 每个模块职责明确
4. **易于测试**: 依赖关系清晰，使用依赖注入
5. **可维护性**: 业务逻辑集中在 `domains/`
6. **可扩展性**: 新功能知道该加在哪里

---

## 🎯 推荐执行顺序

### 阶段 1: 评估现状 (2-3 天)
1. **对比 v1/v2 功能差异** (Phase 9.1)
   - 检查 17 对已有 v2 的路由
   - 列出缺失功能
   - 评估迁移工作量

### 阶段 2: 补全 v2 功能 (1 周)
2. **补全缺失端点** (Phase 9.2)
   - 补充 v2 缺失的端点
   - 编写测试用例
   - ~500 行代码

### 阶段 3: 创建新 v2 路由 (2-3 周)
3. **创建尚未迁移的 v2 版本** (Phase 9.3)
   - User/Assets 路由 (2个)
   - Admin 路由 (14个)
   - 整合 Generation/WebSocket
   - ~2,000 行代码

### 阶段 4: 渐进切换 (2-3 周)
4. **灰度发布 v2 API** (Phase 9.4-9.6)
   - Week 1: 10% 流量
   - Week 2: 50% 流量
   - Week 3: 100% 流量
   - 监控错误率和性能

### 阶段 5: 删除旧代码 (1-2 天)
5. **删除 routers/ 目录** (Phase 9.7)
   - 确认 v2 稳定 2 周
   - 删除 40 个文件
   - ~8,756 行代码

### 阶段 6: 基础设施迁移 (2-3 天)
6. **移动基础设施代码** (Phase 10.1)
   - rate_limiter, task_queue, websocket
   - 依赖少，容易迁移
   - ~1,200 行代码

### 阶段 7: 应用层迁移 (3-5 天)
7. **移动应用服务** (Phase 10.2)
   - AI chat, reports, CAPI, generation helpers
   - ~1,800 行代码
   - 需要更新导入路径

### 阶段 8: 领域层迁移 (5-7 天)
8. **移动业务逻辑** (Phase 10.3)
   - Analytics, config, experiments, payment
   - ~2,500 行代码
   - 需要仔细测试业务逻辑

### 阶段 9: 最终清理 (1-2 天)
9. **删除重复和旧代码** (Phase 10.4-10.5)
   - 删除 services/ai/
   - 清理 services/ 目录
   - ~5,213 行代码

---

## ⚠️ 风险和注意事项

1. **测试覆盖**: 每次迁移后必须运行完整测试
2. **导入路径**: 所有引用都要更新
3. **循环依赖**: 小心 domains 之间的依赖
4. **数据库兼容**: 保持 db_compat 层完整
5. **API 兼容**: 保持对外 API 行为不变 (即使 URL 改变)
6. **灰度发布**: 使用特性开关渐进切换，避免一次性切换风险
7. **回滚准备**: 保留 routers/ 至少 2 周，确保可以快速回滚
8. **监控告警**: 切换过程中密切监控错误率和性能指标

---

## 📊 总结

| 项目 | 当前状态 | 目标状态 | 变化 |
|------|----------|----------|------|
| 总文件数 | 270 | ~190 | -80 files (-30%) |
| 总代码行数 | 51,478 | ~39,000 | -12,000 lines (-23%) |
| DDD 层完整性 | 70% | 100% | +30% |
| 代码重复率 | ~20% | <5% | -15% |
| 架构一致性 | 混合 (v1+v2) | 统一 (v2) | 显著提升 |
| API 版本 | 双版本运行 | 单一 v2 | 简化运维 |

**核心问题** (已修正):
- ❌ `routers/` 使用旧 v1 架构 (8,756 行) - 应迁移到 `api/`
- ❌ `services/` 层不符合 DDD (11,060 行) - 应拆分到 domains/application/infrastructure

**推荐优先级**:
1. 🔴 **立即开始**: 评估 v1/v2 差异，补全 v2 功能
2. 🔴 **近期 (1-2月)**: 完成 routers/ → api/ 迁移
3. 🟡 **中期 (2-3月)**: 拆分 services/ 目录

**预期结果**:
- 清晰的 DDD 架构
- 统一的 v2 API 层
- 减少 12,000+ 行冗余代码
- 提升可维护性和可扩展性
- 消除技术债务

---

## 🙏 致歉说明

本文档 v1.0.0 存在严重的架构理解错误，错误地认为应该删除 `api/` 目录保留 `routers/` 目录，这与实际的 DDD v2 架构设计完全相反。

**错误原因**: 未仔细阅读 `docs/BACKEND_ARCHITECTURE_GUIDE.md` 就进行分析。

**已采取措施**:
1. 重新完整阅读设计文档
2. 检查实际代码实现
3. 确认 URL 模式和调用方式
4. 完全重写本文档 (v2.0.0)

**经验教训**: 在进行架构分析前，必须首先完整阅读所有相关设计文档。

---

## 📚 参考文档

- [BACKEND_ARCHITECTURE_GUIDE.md](./BACKEND_ARCHITECTURE_GUIDE.md) - 后端 DDD 架构设计 (第 2.6 节定义 api/ 层)
- [后台业务逻辑说明.md](./后台业务逻辑说明.md) - 业务规则和数据库设计
- [TEST_COVERAGE_PLAN.md](./TEST_COVERAGE_PLAN.md) - 测试覆盖计划

---

**变更历史**:
- v1.0.0 (2026-01-07): 初始版本 (包含严重错误)
- v2.0.0 (2026-01-07): 修正架构理解，完全重写
