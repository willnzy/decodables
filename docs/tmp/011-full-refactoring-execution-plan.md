# 后台 DDD 架构全量修复执行计划

> **创建日期**: 2026-01-08
> **目标**: 100% DDD 合规性
> **预计工作量**: 5-7 天

---

## 📊 当前状态摘要

| 目录 | 文件数 | 代码行数 | 问题 | 操作 |
|------|--------|----------|------|------|
| schemas/ | 13 | 882 | ❌ 违反 DDD 分层 | 迁移到 api/schemas/ |
| scheduled_tasks/ | 24 | 3,216 | ⚠️ 混合多层关注点 | 拆分到各 DDD 层 |
| timezone_utils.py | 1 | ~400 | ⚠️ 位置不当 | 移动到 core/utils/ |
| api/user/generation*.py | 5 | ~46K | ⚠️ 可能冗余 | 分析并清理 |

---

## 🎯 执行顺序

```
Phase 1 → Phase 3 → Phase 4 → Phase 2 → Phase 5
(简单)    (简单)    (分析)    (复杂)    (验证)
```

**说明**: 先完成简单迁移，积累经验，再处理复杂的 scheduled_tasks。

---

## Phase 1: 迁移 schemas/ 目录 (预计 1 天)

### 1.1 当前 schemas/ 结构

```
schemas/
├── __init__.py       # 聚合导出
├── base.py           # ApiResponse, PaginatedResponse
├── users.py          # UserProfile, CreditTransaction, TimezoneUpdateRequest
├── projects.py       # ProjectCreate/Update/Response
├── assets.py         # CreateAssetFromUrlRequest
├── generation.py     # StoryGenRequest, ImageGenRequest, PdfGenRequest, etc.
├── marketplace.py    # ListingCreate/Update/Response, etc.
├── admin.py          # Admin 相关 schemas (26 个)
├── analytics.py      # AnalyticsEvent, etc.
├── logs.py           # ErrorLogRequest, etc.
├── support.py        # SupportTicketRequest, etc.
├── checkout.py       # CheckoutRequest
└── system_resources.py # ResourceCreate/Update/BatchAction
```

### 1.2 迁移策略

**目标位置**: `api/schemas/` (新建目录)

```
api/
└── schemas/
    ├── __init__.py      # 聚合导出 (保持向后兼容)
    ├── base.py          # 基础 schemas
    ├── user/            # 用户相关
    │   ├── __init__.py
    │   ├── users.py
    │   ├── generation.py
    │   ├── projects.py
    │   ├── assets.py
    │   ├── marketplace.py
    │   ├── support.py
    │   └── checkout.py
    └── admin/           # Admin 相关
        ├── __init__.py
        ├── admin.py
        ├── analytics.py
        ├── logs.py
        └── system_resources.py
```

### 1.3 执行步骤

```bash
# Step 1: 创建目标目录
mkdir -p api/schemas/user api/schemas/admin

# Step 2: 移动文件
mv schemas/base.py api/schemas/
mv schemas/users.py api/schemas/user/
mv schemas/generation.py api/schemas/user/
mv schemas/projects.py api/schemas/user/
mv schemas/assets.py api/schemas/user/
mv schemas/marketplace.py api/schemas/user/
mv schemas/support.py api/schemas/user/
mv schemas/checkout.py api/schemas/user/
mv schemas/admin.py api/schemas/admin/
mv schemas/analytics.py api/schemas/admin/
mv schemas/logs.py api/schemas/admin/
mv schemas/system_resources.py api/schemas/admin/

# Step 3: 创建 __init__.py 文件
# Step 4: 更新导入路径
# Step 5: 创建向后兼容的 schemas/__init__.py
# Step 6: 删除旧 schemas/ 目录
```

### 1.4 导入路径更新

| 旧路径 | 新路径 |
|--------|--------|
| `from schemas.generation import StoryGenRequest` | `from api.schemas.user.generation import StoryGenRequest` |
| `from schemas.system_resources import ResourceCreate` | `from api.schemas.admin.system_resources import ResourceCreate` |
| `from schemas import ApiResponse` | `from api.schemas import ApiResponse` |

### 1.5 受影响文件

```
api/user/generation_story.py   # from schemas.generation import ...
api/user/generation_pdf.py     # from schemas.generation import ...
api/user/generation_images.py  # from schemas.generation import ...
api/user/system_resources.py   # from schemas.system_resources import ...
```

---

## Phase 2: 重构 scheduled_tasks/ 目录 (预计 3 天)

### 2.1 当前 scheduled_tasks/ 结构

```
scheduled_tasks/
├── task_logger.py           # TaskLogger 类
├── aggregate_stats.py       # 主入口 (run_hourly_tasks, run_daily_tasks)
├── aggregators/             # 数据聚合器 (7 个文件)
│   ├── __init__.py
│   ├── base.py
│   ├── user_stats.py
│   ├── revenue_stats.py
│   ├── project_stats.py
│   ├── usage_stats.py
│   ├── marketplace_stats.py
│   └── analytics_stats.py
├── campaign_scheduler.py    # Campaign 调度入口
├── campaign_scheduler/      # Campaign 调度模块 (6 个文件)
│   ├── __init__.py
│   ├── campaigns.py
│   ├── themes.py
│   ├── reporter.py
│   ├── date_utils.py
│   └── utils.py
├── experiment_aggregator.py # A/B 实验聚合
├── metrics_etl.py           # Metrics ETL 入口
├── metrics_etl/             # Metrics ETL 模块 (4 个文件)
│   ├── __init__.py
│   ├── etl.py
│   ├── calculator.py
│   └── utils.py
└── storage_cleanup.py       # 存储清理
```

### 2.2 迁移映射表

| 原位置 | 新位置 | DDD 层 | 原因 |
|--------|--------|--------|------|
| task_logger.py | infrastructure/logging/task_logger.py | Infrastructure | 日志基础设施 |
| storage_cleanup.py | infrastructure/tasks/storage_cleanup.py | Infrastructure | 存储清理任务 |
| aggregators/ | application/services/aggregators/ | Application | 数据聚合服务 |
| metrics_etl/ | application/services/metrics/ | Application | ETL 处理服务 |
| campaign_scheduler/ | application/services/campaigns/ | Application | Campaign 服务 |
| campaign_scheduler/date_utils.py | core/utils/datetime_ext.py | Core | 日期工具函数 |
| experiment_aggregator.py | application/services/experiments/aggregator.py | Application | 实验聚合服务 |

### 2.3 新目录结构

```
# Infrastructure 层
infrastructure/
├── logging/
│   └── task_logger.py      # ← scheduled_tasks/task_logger.py
└── tasks/
    └── storage_cleanup.py  # ← scheduled_tasks/storage_cleanup.py

# Application 层
application/
└── services/
    ├── aggregators/        # ← scheduled_tasks/aggregators/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── user_stats.py
    │   ├── revenue_stats.py
    │   ├── project_stats.py
    │   ├── usage_stats.py
    │   ├── marketplace_stats.py
    │   └── analytics_stats.py
    ├── metrics/            # ← scheduled_tasks/metrics_etl/
    │   ├── __init__.py
    │   ├── etl.py
    │   ├── calculator.py
    │   └── utils.py
    ├── campaigns/          # ← scheduled_tasks/campaign_scheduler/
    │   ├── __init__.py
    │   ├── scheduler.py    # ← campaign_scheduler.py
    │   ├── campaigns.py
    │   ├── themes.py
    │   ├── reporter.py
    │   └── utils.py
    └── experiments/
        └── aggregator.py   # ← experiment_aggregator.py

# Core 层
core/
└── utils/
    └── datetime_ext.py     # ← campaign_scheduler/date_utils.py
```

### 2.4 执行步骤

```bash
# Step 1: 创建目标目录
mkdir -p infrastructure/logging infrastructure/tasks
mkdir -p application/services/aggregators
mkdir -p application/services/metrics
mkdir -p application/services/campaigns
mkdir -p application/services/experiments

# Step 2: 移动基础设施代码
mv scheduled_tasks/task_logger.py infrastructure/logging/
mv scheduled_tasks/storage_cleanup.py infrastructure/tasks/

# Step 3: 移动应用层代码
mv scheduled_tasks/aggregators/* application/services/aggregators/
mv scheduled_tasks/metrics_etl/etl.py application/services/metrics/
mv scheduled_tasks/metrics_etl/calculator.py application/services/metrics/
mv scheduled_tasks/metrics_etl/utils.py application/services/metrics/
mv scheduled_tasks/campaign_scheduler/campaigns.py application/services/campaigns/
mv scheduled_tasks/campaign_scheduler/themes.py application/services/campaigns/
mv scheduled_tasks/campaign_scheduler/reporter.py application/services/campaigns/
mv scheduled_tasks/campaign_scheduler/utils.py application/services/campaigns/
mv scheduled_tasks/experiment_aggregator.py application/services/experiments/aggregator.py

# Step 4: 移动工具代码到 core
mv scheduled_tasks/campaign_scheduler/date_utils.py core/utils/datetime_ext.py

# Step 5: 创建入口文件
# - application/services/aggregators/__init__.py (包含 run_hourly_tasks, run_daily_tasks)
# - application/services/metrics/__init__.py (包含 run_hourly_etl, run_daily_etl)
# - application/services/campaigns/scheduler.py (campaign_scheduler.py 内容)

# Step 6: 更新 scheduler.py 导入路径
# Step 7: 删除旧 scheduled_tasks/ 目录
```

### 2.5 scheduler.py 导入更新

| 旧导入 | 新导入 |
|--------|--------|
| `from scheduled_tasks.metrics_etl import run_hourly_etl` | `from application.services.metrics import run_hourly_etl` |
| `from scheduled_tasks.aggregate_stats import run_hourly_tasks` | `from application.services.aggregators import run_hourly_tasks` |
| `from scheduled_tasks.experiment_aggregator import run_hourly_experiment_tasks` | `from application.services.experiments import run_hourly_experiment_tasks` |
| `from scheduled_tasks.storage_cleanup import run_storage_cleanup` | `from infrastructure.tasks.storage_cleanup import run_storage_cleanup` |

---

## Phase 3: 移动 timezone_utils.py (预计 0.5 天)

### 3.1 当前状态

```
位置: /decodables/timezone_utils.py (根目录)
行数: ~400 行
导出: get_request_timezone, timezone_middleware, etc.
```

### 3.2 迁移目标

```
新位置: /decodables/core/utils/timezone.py
```

### 3.3 受影响文件

```
app.py                         # from timezone_utils import get_request_timezone
api/user/user_assets.py        # from timezone_utils import get_request_timezone
api/user/generation.py         # from timezone_utils import get_request_timezone
api/user/generation_images.py  # from timezone_utils import get_request_timezone
api/user/tools.py              # from timezone_utils import get_request_timezone
tests/test_timezone_utils.py   # from timezone_utils import ...
```

### 3.4 执行步骤

```bash
# Step 1: 移动文件
mv timezone_utils.py core/utils/timezone.py

# Step 2: 更新导入路径
# 旧: from timezone_utils import get_request_timezone
# 新: from core.utils.timezone import get_request_timezone

# Step 3: 创建向后兼容文件 (可选)
# echo "from core.utils.timezone import *" > timezone_utils.py

# Step 4: 更新测试文件路径
```

---

## Phase 4: 清理 api/user/generation 冗余 (预计 0.5 天)

### 4.1 当前文件分析

| 文件 | 大小 | 用途 |
|------|------|------|
| generation.py | 18.5K | 主生成 API (图片、PDF、故事) |
| generation_images.py | 15K | 图片生成专用 |
| generation_pdf.py | 1.7K | PDF 生成专用 |
| generation_story.py | 5.2K | 故事生成专用 |
| generations.py | 6.3K | ❓ 用途不明 |

### 4.2 需要确认的问题

1. `generation.py` vs `generation_*.py` 是否重复?
2. `generations.py` (复数) 的实际用途?
3. app.py 中哪些路由在使用?

### 4.3 决策选项

**选项 A: 保留拆分结构**
- 删除 `generation.py` (如果功能已在 `generation_*.py` 中)
- 重命名 `generations.py` 以避免混淆

**选项 B: 合并回单文件**
- 保留 `generation.py` 作为主入口
- 删除 `generation_*.py` 子文件

**选项 C: 保持现状**
- 添加注释说明结构
- 不做改动

### 4.4 执行步骤

```bash
# Step 1: 分析 app.py 路由注册
grep -n "generation" app.py

# Step 2: 检查 __init__.py 导出
cat api/user/__init__.py | grep generation

# Step 3: 根据分析结果决定清理策略
# Step 4: 执行清理
# Step 5: 更新文档
```

---

## Phase 5: 测试验证 (预计 1 天)

### 5.1 测试策略

```bash
# 1. 运行全量测试
pytest tests/ -v

# 2. 检查导入错误
python -c "from api.schemas import *"
python -c "from application.services.aggregators import *"
python -c "from infrastructure.logging.task_logger import TaskLogger"
python -c "from core.utils.timezone import get_request_timezone"

# 3. 启动服务验证
uvicorn app:app --reload

# 4. 测试定时任务
python -c "from scheduler import run_aggregation_now; run_aggregation_now('hourly')"
```

### 5.2 回滚策略

每个 Phase 完成后立即 commit，便于回滚:

```bash
# Phase 1 完成
git add . && git commit -m "refactor(schemas): migrate schemas/ to api/schemas/"

# Phase 2 完成
git add . && git commit -m "refactor(tasks): migrate scheduled_tasks/ to DDD layers"

# Phase 3 完成
git add . && git commit -m "refactor(utils): move timezone_utils.py to core/utils/"

# Phase 4 完成
git add . && git commit -m "refactor(api): cleanup generation redundant files"
```

---

## 📋 检查清单

### Phase 1: schemas/
- [ ] 创建 api/schemas/ 目录结构
- [ ] 移动所有 schema 文件
- [ ] 创建 __init__.py 聚合导出
- [ ] 更新所有导入路径 (4 个文件)
- [ ] 创建向后兼容层 (可选)
- [ ] 删除旧 schemas/ 目录
- [ ] 运行测试
- [ ] Git commit

### Phase 2: scheduled_tasks/
- [ ] 创建目标目录结构
- [ ] 移动 task_logger.py → infrastructure/logging/
- [ ] 移动 storage_cleanup.py → infrastructure/tasks/
- [ ] 移动 aggregators/ → application/services/aggregators/
- [ ] 移动 metrics_etl/ → application/services/metrics/
- [ ] 移动 campaign_scheduler/ → application/services/campaigns/
- [ ] 移动 experiment_aggregator.py → application/services/experiments/
- [ ] 移动 date_utils.py → core/utils/datetime_ext.py
- [ ] 创建入口 __init__.py 文件
- [ ] 更新 scheduler.py 导入
- [ ] 删除旧 scheduled_tasks/ 目录
- [ ] 运行测试
- [ ] Git commit

### Phase 3: timezone_utils.py
- [ ] 移动到 core/utils/timezone.py
- [ ] 更新所有导入路径 (6 个文件)
- [ ] 创建向后兼容层 (可选)
- [ ] 更新测试文件
- [ ] 运行测试
- [ ] Git commit

### Phase 4: generation 清理
- [ ] 分析文件使用情况
- [ ] 确定清理策略
- [ ] 执行清理
- [ ] 更新文档
- [ ] 运行测试
- [ ] Git commit

### Phase 5: 最终验证
- [ ] 运行全量测试 (pytest)
- [ ] 验证导入无错误
- [ ] 验证服务启动正常
- [ ] 验证定时任务正常

---

## 📊 预期成果

| 指标 | 当前 | 目标 |
|------|------|------|
| DDD 合规率 | 73% | 100% |
| schemas/ 文件 | 13 | 0 (迁移到 api/schemas/) |
| scheduled_tasks/ 文件 | 24 | 0 (迁移到 DDD 各层) |
| 根目录 .py 文件 | 7 | 6 (移除 timezone_utils.py) |
| 冗余 generation 文件 | 1-2 | 0 |

---

## ⚠️ 风险和注意事项

1. **测试覆盖**: 每次迁移后必须运行测试
2. **导入路径**: 使用 IDE 重构功能或脚本批量更新
3. **向后兼容**: 考虑创建兼容层避免外部依赖中断
4. **定时任务**: scheduler.py 更新后需验证任务正常运行
5. **回滚准备**: 每个 Phase 单独 commit，便于回滚

---

**状态**: ✅ 计划完成，等待执行确认
