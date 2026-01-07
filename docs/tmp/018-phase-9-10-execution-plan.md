# Phase 9-10 执行计划

> 基于 016-phase-9-10-architecture-cleanup-plan.md 创建的详细执行计划
>
> **创建时间**: 2026-01-08
> **目标**: 将 routers/ (v1) 迁移到 api/ (v2 DDD)，并重构 services/ 目录

---

## 📋 总体目标

### Phase 9: routers/ → api/ 迁移
- **删除**: 40 个文件，8,756 行代码
- **策略**: 补全 v2 缺失端点 → 渐进式切换 → 删除旧代码

### Phase 10: services/ 重构
- **拆分**: 57 个文件，11,060 行代码
- **目标**: 符合 DDD 分层原则 (domains/application/infrastructure)

---

## 🎯 Stage 1: 评估 v1/v2 功能差异 (2-3 天)

### 1.1 已知重复的 17 对路由

| v1 (routers/) | v2 (api/) | 状态 | 优先级 |
|---------------|-----------|------|--------|
| routers/analytics.py | api/analytics_api.py | 需对比 | 🟡 中 |
| routers/campaigns.py | api/campaigns_api.py | 需对比 | 🟠 高 |
| routers/config.py | api/config_api.py | 需对比 | 🟡 中 |
| routers/export.py | api/export_api.py | 需对比 | 🟢 低 |
| routers/generation.py | api/generation_api.py | 需对比 | 🔴 极高 |
| routers/generations.py | api/generations_api.py | 需对比 | 🔴 极高 |
| routers/logs.py | api/logs_api.py | 需对比 | 🟢 低 |
| routers/marketplace.py | api/marketplace_api.py | 需对比 | 🟠 高 |
| routers/payment.py | api/payment_api.py | 需对比 | 🔴 极高 |
| routers/projects.py | api/projects_api.py | 需对比 | 🟠 高 |
| routers/resources.py | api/resources_api.py | 需对比 | 🟡 中 |
| routers/support.py | api/support_api.py | 需对比 | 🟢 低 |
| routers/tasks.py | api/tasks_api.py | 需对比 | 🟡 中 |
| routers/templates.py | api/templates_api.py | 需对比 | 🟠 高 |
| routers/themes.py | api/themes_api.py | 需对比 | 🟡 中 |
| routers/tools.py | api/tools_api.py | 需对比 | 🟢 低 |
| routers/webhooks.py | api/webhooks_api.py | 需对比 | 🔴 极高 |

### 1.2 可能只存在于 v1 的路由

需要逐个检查 routers/ 下的所有文件，确认是否在 api/ 中缺失：

```bash
# 检查方法
cd /Users/zhangyi/Code_all/AI-WEB/decodables
comm -23 <(cd routers && ls *.py | sort) <(cd api && ls *_api.py | sed 's/_api.py/.py/' | sort)
```

**预期需要检查的文件**:
- routers/admin/ 下的 14 个文件 (admin APIs)
- routers/ 根目录下可能存在的其他文件

### 1.3 对比检查清单

对每对路由执行以下检查：

#### A. 端点覆盖度
```python
# v1 示例
@router.get("/api/marketplace/listings")
@router.post("/api/marketplace/listings")
@router.get("/api/marketplace/listings/{listing_id}")
@router.put("/api/marketplace/listings/{listing_id}")
@router.delete("/api/marketplace/listings/{listing_id}")

# v2 对应检查
# ✅ 是否所有端点都有对应实现?
# ❌ 是否有缺失的端点?
```

#### B. 功能等价性
- 请求参数是否一致?
- 响应格式是否兼容?
- 业务逻辑是否完整?

#### C. 依赖检查
```python
# v1 (旧模式)
from services.db import db_service

# v2 (DDD 模式)
from application.commands.billing import DeductCreditsCommand
from application.handlers.billing import BillingCommandHandler
```

### 1.4 输出产物

创建 **功能差异对比表** (Excel 或 Markdown):

| 路由对 | v1 端点数 | v2 端点数 | 缺失端点 | 功能差异 | 优先级 | 负责人 |
|--------|-----------|-----------|----------|----------|--------|--------|
| marketplace | 12 | 10 | POST /bulk-upload, DELETE /batch | 批量操作缺失 | 🟠 高 | - |
| payment | 8 | 8 | - | ✅ 功能等价 | 🔴 极高 | - |
| ... | ... | ... | ... | ... | ... | ... |

---

## 🛠️ Stage 2: 补全 v2 缺失端点 (1 周)

### 2.1 优先级划分

#### 🔴 P0 - 核心功能 (必须先补全)
- **payment** (支付/订阅)
- **generation** (AI 生成)
- **webhooks** (Clerk/Stripe)

#### 🟠 P1 - 高频功能
- **projects** (项目管理)
- **marketplace** (素材市场)
- **campaigns** (营销活动)
- **templates** (模板系统)

#### 🟡 P2 - 常用功能
- **analytics** (数据分析)
- **config** (配置管理)
- **resources** (资源管理)
- **tasks** (任务队列)
- **themes** (主题系统)

#### 🟢 P3 - 低频功能
- **export** (导出功能)
- **logs** (日志查询)
- **support** (客服支持)
- **tools** (工具类)

### 2.2 端点补全模板

以 marketplace 为例：

#### 步骤 1: 创建 Command/Query
```python
# application/commands/marketplace.py
from pydantic import BaseModel

class BulkUploadListingsCommand(BaseModel):
    """批量上传素材"""
    user_id: str
    listings: list[dict]  # 素材列表

    class Config:
        from_attributes = True
```

#### 步骤 2: 实现 Handler
```python
# application/handlers/marketplace.py
from domains.marketplace.repository import ListingRepository

class MarketplaceCommandHandler:
    def __init__(self, listing_repo: ListingRepository):
        self.listing_repo = listing_repo

    async def bulk_upload(self, cmd: BulkUploadListingsCommand) -> list[str]:
        """批量上传素材"""
        listing_ids = []
        for listing_data in cmd.listings:
            # 验证权限
            # 创建 Listing 聚合根
            # 保存到数据库
            listing_ids.append(listing_id)
        return listing_ids
```

#### 步骤 3: 添加 API 端点
```python
# api/marketplace_api.py
@router.post("/api/v2/marketplace/bulk-upload", tags=["marketplace-v2"])
async def bulk_upload_listings(
    request: BulkUploadListingsCommand,
    current_user: User = Depends(get_current_user)
):
    """批量上传素材"""
    handler = MarketplaceCommandHandler(listing_repo)
    listing_ids = await handler.bulk_upload(request)
    return {"listing_ids": listing_ids}
```

#### 步骤 4: 编写测试
```python
# tests/api/test_marketplace_api.py
async def test_bulk_upload_listings():
    """测试批量上传素材"""
    response = client.post(
        "/api/v2/marketplace/bulk-upload",
        json={
            "user_id": "user_123",
            "listings": [
                {"title": "Asset 1", "price": 9.99},
                {"title": "Asset 2", "price": 14.99}
            ]
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["listing_ids"]) == 2
```

### 2.3 补全计划 (1 周时间表)

| 天数 | 优先级 | 路由 | 预计新增端点 | 负责人 |
|------|--------|------|--------------|--------|
| Day 1-2 | 🔴 P0 | payment, webhooks | 0 (已完整) | - |
| Day 2-3 | 🔴 P0 | generation, generations | 2-3 | - |
| Day 3-4 | 🟠 P1 | projects, marketplace | 3-5 | - |
| Day 4-5 | 🟠 P1 | campaigns, templates | 2-4 | - |
| Day 5-7 | 🟡 P2 + 🟢 P3 | 其余路由 | 5-10 | - |

**预计新增**:
- Commands/Queries: 15-20 个
- Handlers: 10-15 个
- API 端点: 15-25 个
- 测试用例: 15-25 个

---

## 🔄 Stage 3: 创建新 v2 路由 (User/Admin 分离, 2-3 周)

### 3.1 当前问题

```python
# ❌ 问题: v2 API 都混在 api/ 根目录
api/
├── analytics_api.py       # 既有 User 又有 Admin
├── billing_api.py         # User only
├── marketplace_api.py     # User + Admin
└── ...
```

### 3.2 目标结构

```python
# ✅ 目标: 按角色分离
api/
├── user/                  # 用户端 API
│   ├── __init__.py
│   ├── analytics.py
│   ├── billing.py
│   ├── marketplace.py
│   └── ...
└── admin/                 # 管理端 API
    ├── __init__.py
    ├── analytics.py
    ├── campaigns.py
    ├── experiments.py
    └── ...
```

### 3.3 路由分配表

#### User APIs (用户端, 24 个文件)

| 原文件 | 新路径 | URL 前缀 | 说明 |
|--------|--------|----------|------|
| api/billing_api.py | api/user/billing.py | `/api/v2/user/billing` | 积分/订阅管理 |
| api/generation_api.py | api/user/generation.py | `/api/v2/user/generation` | AI 生成 |
| api/marketplace_api.py | api/user/marketplace.py | `/api/v2/user/marketplace` | 素材市场 |
| api/projects_api.py | api/user/projects.py | `/api/v2/user/projects` | 项目管理 |
| api/templates_api.py | api/user/templates.py | `/api/v2/user/templates` | 模板库 |
| api/themes_api.py | api/user/themes.py | `/api/v2/user/themes` | 主题系统 |
| api/export_api.py | api/user/export.py | `/api/v2/user/export` | 导出功能 |
| ... | ... | ... | ... |

#### Admin APIs (管理端, 14 个文件)

| 原文件 | 新路径 | URL 前缀 | 说明 |
|--------|--------|----------|------|
| api/admin_analytics_api.py | api/admin/analytics.py | `/api/v2/admin/analytics` | 数据分析 |
| api/admin_campaigns_api.py | api/admin/campaigns.py | `/api/v2/admin/campaigns` | 营销活动管理 |
| api/admin_experiments_api.py | api/admin/experiments.py | `/api/v2/admin/experiments` | A/B 实验管理 |
| api/admin_logs_api.py | api/admin/logs.py | `/api/v2/admin/logs` | 日志查询 |
| api/admin_metrics_api.py | api/admin/metrics.py | `/api/v2/admin/metrics` | 指标监控 |
| api/admin_users_api.py | api/admin/users.py | `/api/v2/admin/users` | 用户管理 |
| ... | ... | ... | ... |

### 3.4 迁移步骤 (每个文件)

#### Step 1: 创建新文件
```bash
# 示例: 迁移 billing_api.py
mkdir -p api/user
touch api/user/billing.py
```

#### Step 2: 复制并调整代码
```python
# api/user/billing.py
from fastapi import APIRouter, Depends
from application.commands.billing import PurchaseCreditsCommand
from application.handlers.billing import BillingCommandHandler

router = APIRouter(
    prefix="/api/v2/user/billing",  # ✅ 新前缀
    tags=["billing-v2-user"]        # ✅ 新 tag
)

@router.post("/purchase-credits")
async def purchase_credits(
    command: PurchaseCreditsCommand,
    current_user: User = Depends(get_current_user)
):
    """购买积分 (v2 用户端)"""
    handler = BillingCommandHandler()
    return await handler.purchase_credits(command)
```

#### Step 3: 更新 app.py 导入
```python
# app.py
from api.user import billing as user_billing_router
from api.admin import analytics as admin_analytics_router

app.include_router(user_billing_router.router)
app.include_router(admin_analytics_router.router)
```

#### Step 4: 编写测试
```python
# tests/api/user/test_billing.py
def test_purchase_credits_v2_user():
    """测试 v2 用户端购买积分"""
    response = client.post(
        "/api/v2/user/billing/purchase-credits",
        json={"amount": 100, "user_id": "user_123"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
```

### 3.5 迁移顺序 (3 周计划)

| 周次 | 优先级 | 路由组 | 文件数 | 说明 |
|------|--------|--------|--------|------|
| Week 1 | 🔴 P0 | User: billing, generation, webhooks | 3 | 核心功能 |
| Week 1 | 🟠 P1 | User: projects, marketplace | 2 | 高频功能 |
| Week 2 | 🟠 P1 | User: campaigns, templates, themes | 3 | 高频功能 |
| Week 2 | 🟡 P2 | User: analytics, config, resources | 5 | 常用功能 |
| Week 3 | 🟢 P3 | User: export, logs, support, tools | 11 | 低频功能 |
| Week 3 | 🟠 P1 | Admin: 所有管理端 API | 14 | 管理功能 |

**总计**: 38 个文件迁移到新结构

### 3.6 最终产物

```python
api/
├── __init__.py
├── user/
│   ├── __init__.py
│   ├── analytics.py
│   ├── billing.py          # ✅ 从 api/billing_api.py 迁移
│   ├── campaigns.py        # ✅ 从 api/campaigns_api.py 迁移
│   ├── config.py
│   ├── export.py
│   ├── generation.py       # ✅ 从 api/generation_api.py 迁移
│   ├── generations.py
│   ├── logs.py
│   ├── marketplace.py      # ✅ 从 api/marketplace_api.py 迁移
│   ├── payment.py          # ✅ 从 api/payment_api.py 迁移
│   ├── projects.py         # ✅ 从 api/projects_api.py 迁移
│   ├── resources.py
│   ├── support.py
│   ├── tasks.py
│   ├── templates.py        # ✅ 从 api/templates_api.py 迁移
│   ├── themes.py           # ✅ 从 api/themes_api.py 迁移
│   └── tools.py
│
└── admin/
    ├── __init__.py
    ├── ai.py
    ├── analytics.py        # ✅ 从 api/admin_analytics_api.py 迁移
    ├── campaigns.py        # ✅ 从 api/admin_campaigns_api.py 迁移
    ├── config.py
    ├── events.py
    ├── experiments.py      # ✅ 从 api/admin_experiments_api.py 迁移
    ├── feature_flags.py
    ├── logs.py             # ✅ 从 api/admin_logs_api.py 迁移
    ├── metrics.py          # ✅ 从 api/admin_metrics_api.py 迁移
    ├── monitoring.py
    ├── resources.py
    ├── subscriptions.py
    ├── themes.py
    └── users.py            # ✅ 从 api/admin_users_api.py 迁移
```

---

## 🚀 Stage 4: 灰度发布 v2 API (2-3 周)

### 4.1 Feature Flag 配置

```python
# domains/platform/feature_flags.py
class FeatureFlags:
    """Feature Flag 定义"""

    # API 版本切换
    USE_V2_MARKETPLACE = "use_v2_marketplace_api"
    USE_V2_BILLING = "use_v2_billing_api"
    USE_V2_GENERATION = "use_v2_generation_api"
    # ... 其他 API
```

### 4.2 流量切换中间件

```python
# core/middleware/api_version_router.py
from domains.platform.service import ExperimentService

async def route_api_version(request: Request, call_next):
    """根据 Feature Flag 路由到 v1 或 v2"""

    # 检查是否是 API 请求
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # 获取用户 ID
    user_id = request.state.user.id if hasattr(request.state, "user") else None

    # 检查 Feature Flag
    exp_service = ExperimentService()

    # 示例: marketplace API
    if "/api/marketplace" in request.url.path:
        if exp_service.is_enabled(FeatureFlags.USE_V2_MARKETPLACE, user_id):
            # 重写 URL: /api/marketplace -> /api/v2/user/marketplace
            new_path = request.url.path.replace("/api/marketplace", "/api/v2/user/marketplace")
            request.scope["path"] = new_path

    return await call_next(request)
```

### 4.3 灰度发布策略

#### Phase 4.1: 内部测试 (10% 流量, 1 周)

```python
# 配置 Feature Flag
exp_service.create_experiment(
    flag=FeatureFlags.USE_V2_MARKETPLACE,
    allocation_percent=10,  # 10% 用户
    target_users=[
        "user_internal_1",  # 内部测试用户
        "user_internal_2",
        # ... 最多 10 个内部用户
    ]
)
```

**监控指标**:
- ✅ 错误率 < 0.1%
- ✅ P95 延迟 < 200ms
- ✅ 功能正确性 100%

#### Phase 4.2: 小范围公测 (50% 流量, 1 周)

```python
# 扩大到 50%
exp_service.update_experiment(
    flag=FeatureFlags.USE_V2_MARKETPLACE,
    allocation_percent=50
)
```

**监控指标**:
- ✅ 错误率 < 0.5%
- ✅ P95 延迟增长 < 10%
- ✅ 用户反馈无严重问题

#### Phase 4.3: 全量发布 (100% 流量, 1 周)

```python
# 全量切换
exp_service.update_experiment(
    flag=FeatureFlags.USE_V2_MARKETPLACE,
    allocation_percent=100
)
```

**观察期**: 1 周稳定后，移除 Feature Flag

### 4.4 回滚策略

**触发条件** (任一满足):
1. 错误率 > 1%
2. P95 延迟增长 > 50%
3. 严重功能 Bug

**回滚操作**:
```python
# 立即回滚到 v1
exp_service.disable_experiment(FeatureFlags.USE_V2_MARKETPLACE)

# 或降低流量
exp_service.update_experiment(
    flag=FeatureFlags.USE_V2_MARKETPLACE,
    allocation_percent=0  # 全部流量回到 v1
)
```

### 4.5 API 发布顺序 (3 周计划)

| 周次 | API | 流量 | 监控重点 | 回滚方案 |
|------|-----|------|----------|----------|
| Week 1 | marketplace | 10% → 50% → 100% | 素材上传/购买 | Feature Flag |
| Week 1 | billing | 10% → 50% → 100% | 积分扣费/订阅 | Feature Flag |
| Week 2 | generation | 10% → 50% → 100% | AI 生成成功率 | Feature Flag |
| Week 2 | projects | 10% → 50% → 100% | 项目创建/更新 | Feature Flag |
| Week 3 | 其他 User APIs | 50% → 100% | 整体错误率 | Feature Flag |
| Week 3 | Admin APIs | 100% (直接) | 管理功能 | 代码回滚 |

---

## 🗑️ Stage 5: 删除 routers/ 旧代码 (1-2 天)

### 5.1 前置条件检查

**必须满足以下所有条件**:

- [ ] v2 API 全量发布 100% 流量 ≥ 1 周
- [ ] 错误率 < 0.1%
- [ ] P95 延迟无明显增长
- [ ] 无严重用户投诉
- [ ] 前端已全部切换到 v2 API

### 5.2 依赖检查

```bash
# 检查是否还有代码引用 routers/
cd /Users/zhangyi/Code_all/AI-WEB/decodables
grep -r "from routers" --include="*.py" --exclude-dir=routers
grep -r "import routers" --include="*.py" --exclude-dir=routers
```

**预期结果**: 只有 `app.py` 有引用

### 5.3 删除步骤

#### Step 1: 备份 (以防万一)
```bash
cd /Users/zhangyi/Code_all/AI-WEB/decodables
git checkout -b backup/routers-deletion
tar -czf ~/routers-backup-$(date +%Y%m%d).tar.gz routers/
```

#### Step 2: 移除 app.py 引用
```python
# app.py (删除这些行)
# ❌ 删除所有 routers/ 导入
# from routers import analytics
# from routers import campaigns
# ... 共 40 行左右

# ❌ 删除所有 include_router
# app.include_router(analytics.router)
# app.include_router(campaigns.router)
# ... 共 40 行左右
```

#### Step 3: 删除整个 routers/ 目录
```bash
git rm -r routers/
```

#### Step 4: 运行测试
```bash
# 确保所有测试通过
pytest tests/ -v --tb=short

# 确保应用能启动
python -m uvicorn app:app --host 0.0.0.0 --port 8000 &
sleep 5
curl http://localhost:8000/health
kill %1
```

#### Step 5: 提交
```bash
git add app.py
git commit -m "refactor(api): delete routers/ directory, fully migrated to api/

- Deleted 40 files, 8,756 lines of v1 API code
- All functionality migrated to api/user/ and api/admin/
- v2 API stable at 100% traffic for 1+ week

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### 5.4 验证清单

- [ ] 应用启动无错误
- [ ] 所有 API 端点可访问 (v2)
- [ ] 前端功能正常
- [ ] Webhooks 正常接收 (Clerk/Stripe)
- [ ] 监控无异常告警

---

## 🔧 Stage 6-9: 拆分 services/ 目录 (2-3 周)

### 6.1 services/ 目录现状

```
services/
├── 14 个根级文件 (1,540 lines)
│   ├── access_control.py          → domains/shared/ ✅ 已完成
│   ├── ai_chat_service.py         → application/services/
│   ├── ai_report_service.py       → application/services/
│   ├── analytics_service.py       → domains/platform/
│   ├── capi_service.py            → application/services/
│   ├── config_service.py          → domains/platform/
│   ├── db_service.py              → infrastructure/ ✅ 已完成
│   ├── experiment_ai_service.py   → domains/platform/
│   ├── experiment_service.py      → domains/platform/
│   ├── generation_helpers.py      → application/services/
│   ├── payment_service.py         → domains/billing/
│   ├── rate_limiter.py            → infrastructure/
│   ├── setup_assistant.py         → application/services/
│   └── system_resource_helpers.py → domains/content/
│
└── 7 个子目录 (9,520 lines)
    ├── ai/ (20 files, 5,213 lines)      → shared/ai/ ✅ 已存在
    ├── ai_reports/ (4 files, 532 lines) → application/services/
    ├── capi/ (4 files, 443 lines)       → application/services/
    ├── db/ (1 file, 236 lines)          → ✅ 已完成迁移
    ├── experiments/ (7 files, 929 lines)→ domains/platform/
    ├── task_queue/ (4 files, 845 lines) → infrastructure/
    └── websocket/ (2 files, 342 lines)  → infrastructure/
```

### 6.2 Stage 6: 基础设施迁移 (2-3 天)

#### 6.2.1 rate_limiter.py → infrastructure/

```bash
# Step 1: 创建新文件
cp services/rate_limiter.py infrastructure/rate_limiter.py

# Step 2: 更新导入路径
# 所有 "from services.rate_limiter import" 改为 "from infrastructure.rate_limiter import"

# Step 3: 删除旧文件
git rm services/rate_limiter.py
```

**影响文件检查**:
```bash
grep -r "from services.rate_limiter" --include="*.py"
```

#### 6.2.2 task_queue/ → infrastructure/

```bash
# 移动整个目录
git mv services/task_queue infrastructure/task_queue

# 更新导入
# "from services.task_queue" → "from infrastructure.task_queue"
```

**预计影响**: 5-10 个文件需要更新导入

#### 6.2.3 websocket/ → infrastructure/

```bash
git mv services/websocket infrastructure/websocket
```

**预计影响**: 3-5 个文件需要更新导入

**验证**:
```bash
pytest tests/infrastructure/ -v
```

### 6.3 Stage 7: 应用服务迁移 (3-5 天)

#### 6.3.1 创建 application/services/ 目录

```bash
mkdir -p application/services
touch application/services/__init__.py
```

#### 6.3.2 迁移文件列表

| 原路径 | 新路径 | 行数 | 说明 |
|--------|--------|------|------|
| services/ai_chat_service.py | application/services/ai_chat.py | ~200 | AI 聊天服务 |
| services/ai_report_service.py | application/services/ai_report.py | ~150 | AI 报告生成 |
| services/capi_service.py | application/services/capi.py | ~180 | CAPI 集成 |
| services/generation_helpers.py | application/services/generation_helpers.py | ~250 | 生成辅助函数 |
| services/setup_assistant.py | application/services/setup_assistant.py | ~120 | 设置向导 |
| services/ai_reports/ | application/services/ai_reports/ | 532 | AI 报告模块 |
| services/capi/ | application/services/capi/ | 443 | CAPI 模块 |

**总计**: ~1,875 行

#### 6.3.3 迁移模板

```bash
# 示例: ai_chat_service.py
git mv services/ai_chat_service.py application/services/ai_chat.py

# 更新导入
# 旧: from services.ai_chat_service import AIChatService
# 新: from application.services.ai_chat import AIChatService
```

**批量更新导入**:
```bash
# 查找所有需要更新的文件
grep -r "from services.ai_chat_service" --include="*.py" -l | xargs -I {} sed -i '' 's/from services\.ai_chat_service/from application.services.ai_chat/g' {}
```

### 6.4 Stage 8: 领域服务迁移 (5-7 天)

#### 6.4.1 Platform Domain

| 原路径 | 新路径 | 行数 | 说明 |
|--------|--------|------|------|
| services/analytics_service.py | domains/platform/analytics_service.py | ~300 | 数据分析 |
| services/config_service.py | domains/platform/config_service.py | ~150 | 配置管理 |
| services/experiment_service.py | domains/platform/service.py | ~200 | 实验服务 (扩展现有) |
| services/experiment_ai_service.py | domains/platform/ai_service.py | ~180 | AI 实验 |
| services/experiments/ | domains/platform/experiments/ | 929 | 实验模块 |

**总计**: ~1,759 行

**迁移策略**:
```python
# domains/platform/service.py (现有文件)
# 需要将 services/experiment_service.py 的逻辑合并进来

# Step 1: 读取两个文件，对比差异
# Step 2: 合并业务逻辑
# Step 3: 保留 DDD 架构风格
```

#### 6.4.2 Billing Domain

```bash
# payment_service.py 迁移
git mv services/payment_service.py domains/billing/payment_service.py

# 或者合并到现有的 domains/billing/service.py
```

**需要检查**:
- 是否与 `domains/billing/service.py` 有重复逻辑?
- 是否需要重构为 Domain Service?

#### 6.4.3 Content Domain

```bash
# system_resource_helpers.py 迁移
git mv services/system_resource_helpers.py domains/content/helpers.py
```

### 6.5 Stage 9: 删除重复代码 (1-2 天)

#### 9.1 services/ai/ vs shared/ai/

**对比检查**:
```bash
# 比较文件列表
diff <(ls services/ai/) <(ls shared/ai/)

# 比较文件内容 (每对文件)
diff services/ai/client.py shared/ai/client.py
```

**预期结果**:
- `shared/ai/` 是新版本 (DDD 重构后)
- `services/ai/` 是旧版本

**删除操作**:
```bash
# 确认 shared/ai/ 功能完整后
git rm -r services/ai/
```

#### 9.2 最终清理

```bash
# 检查 services/ 是否还有残留
ls -la services/

# 预期只剩:
# - services/__init__.py
# - services/db_service.py (兼容层, 保留)
```

### 6.6 拆分计划时间表

| 阶段 | 天数 | 任务 | 文件数 | 代码行数 |
|------|------|------|--------|----------|
| Stage 6 | 2-3 | 基础设施迁移 (rate_limiter, task_queue, websocket) | 7 | ~1,200 |
| Stage 7 | 3-5 | 应用服务迁移 (AI chat, reports, CAPI, helpers) | 11 | ~1,875 |
| Stage 8 | 5-7 | 领域服务迁移 (platform, billing, content) | 13 | ~2,500 |
| Stage 9 | 1-2 | 删除重复 (services/ai/, 清理) | 26 | ~5,485 |
| **总计** | **11-17 天** | **services/ 完全拆分** | **57** | **~11,060** |

---

## 📊 总体进度追踪

### Phase 9: routers/ 迁移

| Stage | 任务 | 预计时间 | 状态 | 完成日期 |
|-------|------|----------|------|----------|
| 1 | 评估 v1/v2 功能差异 | 2-3 天 | ⏳ 待开始 | - |
| 2 | 补全 v2 缺失端点 | 1 周 | ⏳ 待开始 | - |
| 3 | 创建新 v2 路由 (User/Admin) | 2-3 周 | ⏳ 待开始 | - |
| 4 | 灰度发布 v2 API | 2-3 周 | ⏳ 待开始 | - |
| 5 | 删除 routers/ 旧代码 | 1-2 天 | ⏳ 待开始 | - |
| **小计** | **Phase 9 总计** | **6-8 周** | **0/5** | - |

### Phase 10: services/ 拆分

| Stage | 任务 | 预计时间 | 状态 | 完成日期 |
|-------|------|----------|------|----------|
| 6 | 基础设施迁移 | 2-3 天 | ⏳ 待开始 | - |
| 7 | 应用服务迁移 | 3-5 天 | ⏳ 待开始 | - |
| 8 | 领域服务迁移 | 5-7 天 | ⏳ 待开始 | - |
| 9 | 删除重复代码 | 1-2 天 | ⏳ 待开始 | - |
| **小计** | **Phase 10 总计** | **11-17 天** | **0/4** | - |

### 总体目标

| 指标 | 当前 | 目标 | 变化 |
|------|------|------|------|
| 文件数 | 270 | ~180 | -90 (-33%) |
| 代码行数 | 51,478 | ~36,000 | -15,478 (-30%) |
| DDD 完整性 | 60% | 100% | +40% |
| 代码重复率 | ~20% | <5% | -15% |

---

## ⚠️ 风险和注意事项

### 🔴 高风险模块

1. **支付/订阅 (payment_api.py, billing_api.py)**
   - 涉及 Stripe webhooks
   - 积分扣费逻辑
   - **必须**: 100% 功能等价性验证

2. **AI 生成 (generation_api.py)**
   - 积分扣费
   - 异步任务
   - **必须**: 灰度发布，监控错误率

3. **Webhooks (webhooks_api.py)**
   - Clerk 用户同步
   - Stripe 支付回调
   - **必须**: 幂等性测试

### 🟡 中风险模块

1. **项目管理 (projects_api.py)**
   - 用户核心功能
   - 数据一致性要求高

2. **素材市场 (marketplace_api.py)**
   - 素材上传/下载
   - 支付集成

### 🟢 低风险模块

- logs, export, support, tools 等低频功能

### 回滚策略

| 阶段 | 回滚方式 | 预计时间 |
|------|----------|----------|
| Stage 1-2 | 代码回滚 (git revert) | < 10 分钟 |
| Stage 3-4 | Feature Flag 关闭 | < 1 分钟 |
| Stage 5 | 恢复 routers/ 备份 | < 30 分钟 |
| Stage 6-9 | 代码回滚 (git revert) | < 10 分钟 |

---

## 📝 下一步行动

### 立即可开始 (Stage 1)

```bash
# 1. 创建功能对比脚本
cat > scripts/compare_v1_v2.py <<'EOF'
#!/usr/bin/env python3
"""对比 v1 (routers/) 和 v2 (api/) 的端点差异"""

import ast
import os
from pathlib import Path

def extract_endpoints(file_path):
    """提取文件中的所有 API 端点"""
    # 解析 Python AST
    # 查找所有 @router.get/@router.post 等装饰器
    # 返回端点列表
    pass

def compare_route_pair(v1_file, v2_file):
    """对比一对路由文件"""
    v1_endpoints = extract_endpoints(v1_file)
    v2_endpoints = extract_endpoints(v2_file)

    missing = set(v1_endpoints) - set(v2_endpoints)
    return missing

# 主逻辑
if __name__ == "__main__":
    # 对比 17 对已知重复的路由
    # 输出差异报告
    pass
EOF

chmod +x scripts/compare_v1_v2.py
```

### 本周目标 (Week 1)

- [ ] 完成 Stage 1: 评估 v1/v2 功能差异
- [ ] 输出功能差异对比表 (Excel/Markdown)
- [ ] 识别所有缺失端点
- [ ] 启动 Stage 2: 开始补全 P0 优先级端点

---

## 📚 参考文档

- 016-phase-9-10-architecture-cleanup-plan.md (本计划来源)
- TEST_COVERAGE_PLAN.md (测试策略)
- CI-TESTING-LIMITATIONS.md (CI 配置)
- 后台业务逻辑说明.md (业务规则)

---

**创建日期**: 2026-01-08
**预计完成**: 2026-03-31 (Phase 9) + 2026-04-15 (Phase 10)
**负责人**: 待分配
