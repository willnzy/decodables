# Services 层迁移计划

> **版本**: v1.0
> **日期**: 2026-01-07
> **目标**: 将 services/ 目录下的文件迁移到 v2 架构

---

## 目录

1. [迁移原则](#1-迁移原则)
2. [Services 目录分析](#2-services-目录分析)
3. [迁移映射表](#3-迁移映射表)
4. [迁移优先级](#4-迁移优先级)
5. [迁移步骤](#5-迁移步骤)

---

## 1. 迁移原则

### 1.1 决策树

```
这个 service 做什么?
│
├─ 是否包含业务规则? (积分计算、等级判断、项目限制)
│  └─> YES → domains/{domain}/service.py
│
├─ 是否是用例编排? (创建项目、扣除积分、购买 Asset)
│  └─> YES → application/commands/ 或 application/queries/
│
├─ 是否是数据库查询? (CRUD 操作)
│  └─> YES → infrastructure/repositories/
│
├─ 是否是外部服务集成? (AI、支付、存储)
│  └─> YES → shared/{service}/providers/
│
├─ 是否是框架级工具? (缓存、认证、中间件)
│  └─> YES → core/
│
└─ 是否是业务工具? (任务队列、WebSocket、实验系统)
   └─> YES → infrastructure/ 或 application/
```

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| **业务规则归domains** | 积分扣除优先级、等级权限判断等 |
| **用例编排归application** | 调用多个领域对象完成任务 |
| **数据访问归infrastructure** | 所有数据库查询 |
| **外部服务归shared** | AI、支付、存储等 |
| **框架工具归core** | 可在任何项目复用的代码 |

---

## 2. Services 目录分析

### 2.1 目录结构

```
services/
├── 🔴 核心业务服务 (需要拆分到 domains + application)
│   ├── credit_service.py          → domains/billing/ + application/commands/
│   ├── marketplace_service.py     → domains/marketplace/ + application/commands/
│   ├── resource_service.py        → domains/creation/ + application/commands/
│   └── db_service.py              → infrastructure/repositories/ (部分已迁移)
│
├── 🟡 数据库查询服务 (迁移到 infrastructure/repositories)
│   └── db/
│       ├── users.py               → infrastructure/repositories/user_repo.py
│       ├── projects.py            → infrastructure/repositories/project_repo.py
│       ├── marketplace.py         → infrastructure/repositories/marketplace_repo.py
│       ├── payments.py            → infrastructure/repositories/payment_repo.py
│       ├── assets.py              → infrastructure/repositories/asset_repo.py
│       ├── config.py              → infrastructure/repositories/config_repo.py
│       ├── notifications.py       → infrastructure/repositories/notification_repo.py
│       ├── admin_*.py             → infrastructure/repositories/admin/
│       └── support.py             → infrastructure/repositories/support_repo.py
│
├── ✅ AI 服务 (已有抽象,需要整合到 shared/ai)
│   ├── ai/
│   │   ├── adapters/              → shared/ai/providers/ (已完成)
│   │   ├── unified_text_service.py → application/services/ai_text_service.py
│   │   ├── unified_image_service.py → application/services/ai_image_service.py
│   │   ├── ai_cache.py            → 保留 (已更新导入)
│   │   ├── model_config.py        → 保留或移到 infrastructure/config/
│   │   ├── prompt_templates.py    → domains/ai_generation/templates.py
│   │   ├── story_generator.py     → application/services/story_service.py
│   │   ├── zine_generator.py      → application/services/zine_service.py
│   │   └── usage_tracker.py       → infrastructure/tracking/ai_usage.py
│   │
│   ├── ai_chat_service.py         → application/services/ai_chat_service.py
│   └── ai_report_service.py       → application/services/ai_report_service.py
│
├── ✅ 支付服务 (已有抽象,已完成)
│   └── payment_service.py         → shared/payment/providers/ (已完成)
│
├── 🟢 实验系统 (迁移到 domains/platform 或 infrastructure)
│   ├── experiment_service.py      → domains/platform/service.py
│   ├── experiment_ai_service.py   → application/services/experiment_ai.py
│   └── experiments/
│       ├── core.py                → domains/platform/experiment_core.py
│       ├── assignment.py          → domains/platform/assignment.py
│       ├── tracking.py            → infrastructure/tracking/experiment.py
│       ├── analysis.py            → application/queries/experiment_analysis.py
│       └── crud.py                → infrastructure/repositories/experiment_repo.py
│
├── 🟢 分析追踪 (迁移到 shared/analytics 或 infrastructure)
│   ├── analytics_service.py       → shared/analytics/providers/
│   ├── capi_service.py            → shared/analytics/providers/capi_provider.py
│   └── capi/
│       ├── service.py             → shared/analytics/providers/capi_provider.py
│       ├── models.py              → shared/analytics/types.py
│       └── providers.py           → shared/analytics/providers/
│
├── 🔵 基础设施服务 (迁移到 infrastructure 或 core)
│   ├── config_service.py          → infrastructure/config/ 或 core/config/
│   ├── rate_limiter.py            → core/middleware/rate_limiter.py
│   ├── access_control.py          → core/auth/ 或 domains/identity/
│   ├── task_queue/                → infrastructure/task_queue/
│   │   ├── queue_service.py
│   │   ├── task_handlers.py
│   │   └── progress_tracker.py
│   └── websocket/                 → infrastructure/websocket/
│       └── connection_manager.py
│
├── 🟣 工具服务 (迁移到 application 或 infrastructure)
│   ├── service_factory.py         → infrastructure/factories/ 或删除
│   ├── setup_assistant.py         → application/services/setup_assistant.py
│   ├── generation_helpers.py      → application/services/generation_helpers.py
│   └── system_resource_helpers.py → application/services/resource_helpers.py
│
└── 📊 AI 报告 (迁移到 application)
    └── ai_reports/
        ├── report_generator.py    → application/services/ai_report_generator.py
        ├── collectors.py          → application/services/ai_report_collectors.py
        └── models.py              → application/types/ai_report.py
```

---

## 3. 迁移映射表

### 3.1 高优先级迁移 (核心业务逻辑)

| 源文件 | 目标位置 | 迁移类型 | 原因 |
|--------|---------|---------|------|
| **credit_service.py** | `domains/billing/service.py` + `application/commands/billing/` | 拆分 | 包含业务规则(先月度后永久) |
| **marketplace_service.py** | `domains/marketplace/service.py` + `application/commands/marketplace/` | 拆分 | 包含购买逻辑、审核规则 |
| **resource_service.py** | `domains/creation/service.py` + `application/commands/creation/` | 拆分 | 包含项目限制、资源管理 |
| **db_service.py** | `infrastructure/repositories/` | 拆分 | 已部分迁移,继续完成 |

### 3.2 中优先级迁移 (数据访问层)

| 源目录 | 目标位置 | 迁移类型 | 说明 |
|--------|---------|---------|------|
| **db/users.py** | `infrastructure/repositories/user_repo.py` | 移动+改造 | 实现 IUserRepository |
| **db/projects.py** | `infrastructure/repositories/project_repo.py` | 移动+改造 | 实现 IProjectRepository |
| **db/marketplace.py** | `infrastructure/repositories/marketplace_repo.py` | 移动+改造 | 实现 IMarketplaceRepository |
| **db/payments.py** | `infrastructure/repositories/payment_repo.py` | 移动+改造 | 支付记录查询 |
| **db/assets.py** | `infrastructure/repositories/asset_repo.py` | 移动+改造 | 素材查询 |
| **db/config.py** | `infrastructure/repositories/config_repo.py` | 移动+改造 | 配置查询 |
| **db/notifications.py** | `infrastructure/repositories/notification_repo.py` | 移动+改造 | 通知查询 |
| **db/admin_*.py** | `infrastructure/repositories/admin/` | 移动+改造 | 管理后台查询 |

### 3.3 低优先级迁移 (辅助服务)

| 源文件/目录 | 目标位置 | 迁移类型 | 说明 |
|-------------|---------|---------|------|
| **ai/** | `application/services/ai/` + `infrastructure/config/` | 整合 | AI 相关应用服务 |
| **experiments/** | `domains/platform/` + `infrastructure/tracking/` | 拆分 | 实验系统 |
| **analytics_service.py** | `shared/analytics/providers/` | 移动 | 分析追踪 |
| **capi/** | `shared/analytics/providers/capi/` | 移动 | CAPI 集成 |
| **task_queue/** | `infrastructure/task_queue/` | 移动 | 任务队列 |
| **websocket/** | `infrastructure/websocket/` | 移动 | WebSocket |
| **ai_reports/** | `application/services/ai_reports/` | 移动 | AI 报告生成 |

---

## 4. 迁移优先级

### Phase 7: 核心业务服务迁移 (Week 1-2)

**优先级**: 🔴 最高

**目标**: 将核心业务逻辑迁移到 domains 和 application 层

**任务清单**:

```
Week 1: 积分服务迁移
├─ 7.1.1 分析 credit_service.py 业务规则
├─ 7.1.2 将业务规则提取到 domains/billing/service.py
├─ 7.1.3 将用例编排移到 application/commands/billing/
├─ 7.1.4 更新所有调用方导入
├─ 7.1.5 测试验证
└─ 7.1.6 删除 services/credit_service.py

Week 2: 市场和资源服务迁移
├─ 7.2.1 迁移 marketplace_service.py
├─ 7.2.2 迁移 resource_service.py
├─ 7.2.3 更新 API 路由导入
├─ 7.2.4 集成测试
└─ 7.2.5 提交代码
```

### Phase 8: 数据访问层重构 (Week 3)

**优先级**: 🟡 高

**目标**: 统一数据访问到 infrastructure/repositories

**任务清单**:

```
Week 3: 仓储层统一
├─ 8.1 创建所有 Repository 接口
├─ 8.2 实现 Supabase Repository
├─ 8.3 迁移 services/db/*.py
├─ 8.4 更新依赖注入
└─ 8.5 测试验证
```

### Phase 9: AI 服务整合 (Week 4)

**优先级**: 🟢 中

**目标**: 整合 AI 相关服务

**任务清单**:

```
Week 4: AI 服务整合
├─ 9.1 整合 unified_text_service/unified_image_service
├─ 9.2 迁移 prompt_templates 到 domains
├─ 9.3 迁移 story/zine generator 到 application
├─ 9.4 整合 AI 使用追踪
└─ 9.5 测试验证
```

### Phase 10: 实验和分析系统 (Week 5)

**优先级**: 🔵 中低

**目标**: 迁移实验系统和分析追踪

**任务清单**:

```
Week 5: 实验和分析
├─ 10.1 迁移 experiments/ 到 domains/platform
├─ 10.2 迁移 analytics/capi 到 shared/analytics
├─ 10.3 更新配置和依赖
└─ 10.4 测试验证
```

### Phase 11: 基础设施服务 (Week 6)

**优先级**: 🟣 低

**目标**: 迁移基础设施服务

**任务清单**:

```
Week 6: 基础设施
├─ 11.1 迁移 config_service
├─ 11.2 迁移 rate_limiter
├─ 11.3 迁移 task_queue
├─ 11.4 迁移 websocket
└─ 11.5 清理 services/ 目录
```

---

## 5. 迁移步骤

### 5.1 标准迁移流程

对于每个 service 文件,遵循以下步骤:

```
1. 📖 阅读和分析
   ├─ 识别业务规则 (→ domains)
   ├─ 识别用例编排 (→ application)
   ├─ 识别数据访问 (→ infrastructure)
   └─ 识别外部服务 (→ shared)

2. 🏗️ 创建目标文件
   ├─ 创建领域服务/聚合根
   ├─ 创建应用层命令/查询
   ├─ 创建仓储接口和实现
   └─ 创建服务提供者

3. 🔄 迁移代码
   ├─ 复制相关代码到目标位置
   ├─ 调整导入路径
   ├─ 适配新的接口
   └─ 更新依赖注入

4. 📝 更新调用方
   ├─ 查找所有导入该 service 的文件
   ├─ 更新导入路径
   └─ 调整调用方式 (如有必要)

5. ✅ 测试验证
   ├─ 运行单元测试
   ├─ 运行集成测试
   ├─ 手动测试关键功能
   └─ 确认无回归

6. 🧹 清理
   ├─ 删除原 service 文件
   ├─ 提交代码
   └─ 更新文档
```

### 5.2 迁移示例: credit_service.py

#### Step 1: 分析

```python
# services/credit_service.py 包含:

# 🔴 业务规则 → domains/billing/service.py
def deduct_credits(user_id: str, amount: int):
    # 先扣月度积分,再扣永久积分 (业务规则)
    pass

def check_sufficient_credits(user_id: str, amount: int) -> bool:
    # 检查积分是否充足 (业务规则)
    pass

# 🟡 用例编排 → application/commands/billing/deduct_credits.py
async def deduct_credits_for_ai_generation(user_id: str, model: str):
    # 1. 计算成本
    # 2. 检查积分
    # 3. 扣除积分
    # 4. 记录交易
    # 5. 发布事件
    pass

# 🟢 数据访问 → infrastructure/repositories/credit_repo.py (已迁移)
async def get_user_credits(user_id: str):
    # 数据库查询
    pass
```

#### Step 2: 创建目标文件

```python
# domains/billing/service.py
class BillingService:
    """积分领域服务 - 包含业务规则"""

    def calculate_deduction_plan(
        self,
        credits: UserCredits,
        amount: int
    ) -> DeductionPlan:
        """计算积分扣除方案 (业务规则)"""
        # 先月度后永久的逻辑
        pass

# application/commands/billing/deduct_credits.py
@dataclass
class DeductCreditsCommand:
    user_id: str
    amount: int
    reason: str

async def handle(cmd: DeductCreditsCommand, repo: ICreditRepository) -> TransactionRecord:
    """用例编排: 扣除积分"""
    # 1. 加载聚合
    credits = await repo.get_by_user_id(cmd.user_id)

    # 2. 执行业务逻辑
    record = credits.deduct(cmd.amount)

    # 3. 持久化
    await repo.save(credits)

    # 4. 发布事件
    await event_bus.publish(CreditsDeductedEvent(...))

    return record
```

#### Step 3: 更新调用方

```python
# 之前: api/routers/credits.py
from services.credit_service import deduct_credits

@router.post("/deduct")
async def deduct(request: DeductRequest):
    result = await deduct_credits(user_id, amount)
    return result

# 之后: api/routers/credits.py
from application.commands.billing.deduct_credits import DeductCreditsCommand, handle as deduct_credits_handler

@router.post("/deduct")
async def deduct(
    request: DeductRequest,
    user_id: str = Depends(get_current_user_id),
    repo: ICreditRepository = Depends(get_credit_repo)
):
    command = DeductCreditsCommand(
        user_id=user_id,
        amount=request.amount,
        reason=request.reason
    )
    result = await deduct_credits_handler(command, repo)
    return result
```

---

## 6. 验收标准

### 6.1 代码质量

- [ ] 所有业务规则在 domains/ 里
- [ ] 所有用例编排在 application/ 里
- [ ] 所有数据访问在 infrastructure/ 里
- [ ] 所有外部服务在 shared/ 里
- [ ] 测试覆盖率 ≥ 60%

### 6.2 功能验证

- [ ] 积分扣除功能正常
- [ ] 市场购买功能正常
- [ ] 项目创建功能正常
- [ ] AI 生成功能正常
- [ ] 无功能回归

### 6.3 架构验证

- [ ] services/ 目录为空或仅保留必要文件
- [ ] 依赖方向正确 (api → application → domains ← infrastructure)
- [ ] 所有导入路径正确
- [ ] 文件大小符合规范 (≤300 行指标)

---

## 7. 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **循环依赖** | 高 | 严格遵循依赖方向,domains 不依赖 infrastructure |
| **功能回归** | 高 | 每次迁移后立即测试,增量提交 |
| **导入路径混乱** | 中 | 使用 grep 查找所有引用,一次性更新 |
| **测试覆盖不足** | 中 | 迁移前补充测试,迁移后验证通过 |
| **性能下降** | 低 | 保持相同的查询逻辑,不引入额外层级 |

---

## 8. 下一步行动

### 立即行动 (本周)

1. **分析 credit_service.py**
   - 识别所有业务规则
   - 识别所有用例
   - 列出所有调用方

2. **创建迁移 PR 模板**
   - 标准化迁移流程
   - 统一 commit message 格式

3. **开始第一个迁移**
   - 选择 credit_service.py
   - 按标准流程执行
   - 验证成功后作为模板

### 本月目标

- [ ] 完成 Phase 7: 核心业务服务迁移
- [ ] 完成 Phase 8: 数据访问层重构
- [ ] 开始 Phase 9: AI 服务整合

---

**文档版本**: v1.0
**最后更新**: 2026-01-07
**维护者**: Make Decodables Team
