# 数据库-代码同步修复计划 (DB-Code Sync Plan)

**创建时间**: 2026-01-10
**目标**: 修复数据库 Schema 与后端 Repository 代码的不一致问题
**审查范围**: 47 个数据库表 × 26 个 Repository 文件

---

## 执行概览

**问题总数**: 70+ issues
**关键问题**: 42 个 Critical/High 优先级问题
**预计工作量**: 8-12 小时（分 5 个 Phase）
**风险等级**: 🔴 **HIGH** (影响核心业务逻辑)

---

## 一、问题分类统计

| 问题类型 | 数量 | 严重程度 | 影响 |
|---------|------|----------|------|
| 表名不匹配 | 13 | 🔴 CRITICAL | 运行时 "relation does not exist" 错误 |
| 字段名不匹配 | 12 | 🔴 CRITICAL | SELECT/UPDATE 失败 |
| 主键/ID 字段不一致 | 5 | 🟡 HIGH | JOIN 失败 |
| 外键引用错误 | 8 | 🟡 HIGH | 数据完整性问题 |
| 缺失表定义 | 13 | 🔴 CRITICAL | 功能完全失效 |
| 孤立表（有表无代码）| 8 | 🟡 MEDIUM | 数据无法访问 |

**总影响**:
- ❌ 6 个核心功能完全失效（用户管理、错误日志、事件分析、支持系统、项目管理、管理员操作）
- ⚠️ 3 个功能部分失效（积分系统、市场、指标统计）
- 📝 3 个功能缺失实现（定价系统、新手引导、主题系统）

---

## 二、核心问题详解

### 2.1 🔴 Critical Issue #1: users vs profiles 表混乱

**问题**:
`user_repository.py` 在不同地方混用 `users` 表（不存在）和 `profiles` 表（正确）。

**影响范围**:
- ❌ 23 处代码引用不存在的 `users` 表
- ❌ 字段名不匹配：`user_id` (代码) vs `id` (Schema)
- ❌ 缺失字段：`first_name`, `last_name`, `onboarding_step`, `preferences`

**具体代码位置**:
```python
# infrastructure/repositories/user_repository.py
Line 57:  self.client.table("users").select("user_id, ...")  # ❌ 错误
Line 78:  self.client.table("users").upsert(...)             # ❌ 错误
Line 141: self.client.table("users").select("user_id")       # ❌ 错误
Line 158: self.client.table("users").select("*")             # ❌ 错误
Line 174: self.client.table("users").select("*")             # ❌ 错误
Line 199: self.client.table("users").update(...)             # ❌ 错误
Line 221: self.client.table("users").update(...)             # ❌ 错误

# 正确示例:
Line 45:  self.client.table("profiles").select("*")          # ✅ 正确
```

**修复方案**:
1. **代码修复**: 将所有 `table("users")` 改为 `table("profiles")`
2. **字段映射**: `user_id` → `id`（在查询时使用 `id as user_id`）
3. **Schema 增强**: 添加缺失字段到 `profiles` 表

---

### 2.2 🔴 Critical Issue #2: 13 个表在代码中引用但 Schema 不存在

| 表名 | 使用位置 | 用途 | 优先级 |
|------|----------|------|--------|
| `user_events` | events_repository.py | 用户行为追踪 | P0 |
| `aggregated_stats` | events_repository.py | 统计聚合 | P0 |
| `error_logs` | error_logs_repository.py | 错误日志 | P0 |
| `support_tickets` | support_repository.py | 支持工单 | P0 |
| `support_replies` | support_repository.py | 工单回复 | P0 |
| `admin_operations` | admin_repository.py | 管理员操作日志 | P1 |
| `listing_usages` | listing_repository.py | 资产使用追踪 | P1 |
| `marketplace_reports` | listing_repository.py | 市场报告 | P1 |
| `daily_metrics` | metrics_repository.py | 每日指标 | P1 |
| `monthly_metrics` | metrics_repository.py | 月度指标 | P1 |
| `generation_tasks` | logging_repository.py | AI 生成任务 | P2 |
| `page_prompt_templates` | logging_repository.py | 页面模板 | P2 |
| `payment_records` | support_repository.py | 支付记录 | P2 |

**修复策略**:
- **P0 (立即修复)**: 4 个表 - 创建表定义并迁移数据
- **P1 (高优先级)**: 6 个表 - 1 周内完成
- **P2 (中优先级)**: 3 个表 - 2 周内完成

---

### 2.3 🔴 Critical Issue #3: projects 表字段名不匹配

**问题**:
```python
# project_repository.py 使用的字段名:
- project_id  ❌ (Schema 中是 id)
- owner_id    ❌ (Schema 中是 user_id)

# Schema 中不存在的字段:
- listing_status            ❌
- is_permanently_deleted    ❌
- content_hash              ❌
```

**影响**:
- 所有项目查询失败 (project_id 字段不存在)
- JOIN 操作失败 (owner_id vs user_id)
- 删除逻辑失效 (is_permanently_deleted 字段缺失)

**修复方案**:
1. **代码修复**: 全局替换 `project_id` → `id`, `owner_id` → `user_id`
2. **Schema 补充**: 添加 `is_permanently_deleted BOOLEAN DEFAULT false`
3. **移除引用**: 删除 `listing_status`, `content_hash` 的引用（无需这些字段）

---

### 2.4 🔴 Critical Issue #4: marketplace_purchases 字段名错误

**问题**:
```python
# listing_repository.py 使用:
.eq("buyer_id", buyer_id)  # ❌ 字段不存在

# Schema 定义:
user_id TEXT  # ✅ 正确字段名（指代购买者）
```

**影响**: 所有购买查询失败

**修复**: `buyer_id` → `user_id`

---

### 2.5 🟡 High Issue: credit_transactions 字段名不一致

**问题**:
```python
# credit_repository.py:281
query = query.eq("tx_type", tx_type.value)  # ❌

# Schema 定义:
transaction_type TEXT  # ✅
```

**修复**: `tx_type` → `transaction_type`

---

### 2.6 🟡 Medium Issue: 8 个孤立表（有表无代码）

| 表名 | 用途 | 业务影响 |
|------|------|----------|
| `holidays` | 节假日定义 | 主题系统无法使用 |
| `daily_themes` | 每日主题推荐 | 功能缺失 |
| `onboarding_steps` | 新手引导配置 | 无法管理引导流程 |
| `user_onboarding_progress` | 用户引导进度 | 进度无法记录 |
| `pricing_plans` | 定价方案 | **关键业务数据无法管理** |
| `pricing_history` | 定价历史 | 审计缺失 |
| `user_price_overrides` | 用户特殊定价 | 功能缺失 |
| `subscription_history` | 订阅历史 | 审计缺失 |

**风险**: `pricing_plans` 是关键业务数据，缺失 Repository 会导致定价无法动态管理。

---

## 三、修复策略

### 3.1 两种修复路径

#### 路径 A: 代码适配 Schema（推荐）⭐
**优势**:
- ✅ Schema 是真实数据源（refactored_schema_v2.sql）
- ✅ 保持数据库规范性
- ✅ 符合"Schema First"原则

**劣势**:
- ⚠️ 需要修改 26 个 Repository 文件
- ⚠️ 需要创建 13 个新表定义
- ⚠️ 工作量较大（8-12 小时）

#### 路径 B: Schema 适配代码
**优势**:
- ✅ 代码改动较少

**劣势**:
- ❌ 违反"Schema First"原则
- ❌ 可能破坏数据库规范
- ❌ 未来维护困难

### 3.2 最终选择

**✅ 采用路径 A: 代码适配 Schema**

**理由**:
1. Schema 是经过 DDD 重构的 v4.0 版本，结构更合理
2. 代码中存在大量 legacy 引用（如 `users` 表），应该清理
3. 符合"数据库驱动设计"原则
4. 一次性修复，避免后续反复返工

---

## 四、分阶段执行计划

### Phase 1: 修复核心用户/项目表 (P0 - 立即执行)

**目标**: 修复最严重的 `users` vs `profiles` 和 `projects` 字段问题

#### 1.1 修复 user_repository.py

**文件**: `infrastructure/repositories/user_repository.py`

**改动清单**:
```python
# 全局替换 (23 处):
table("users") → table("profiles")
.eq("user_id", ...) → .eq("id", ...)
.select("user_id, ...") → .select("id as user_id, ...")
row.get("user_id") → row.get("id")
```

**新增 Schema 字段**:
```sql
ALTER TABLE profiles
ADD COLUMN first_name TEXT,
ADD COLUMN last_name TEXT,
ADD COLUMN onboarding_step TEXT DEFAULT 'not_started',
ADD COLUMN preferences JSONB DEFAULT '{}',
ADD COLUMN credits_reset_at TIMESTAMPTZ;
```

**验证**:
- ✅ 运行 `test_user_repository.py` 所有测试
- ✅ 手动测试 `get_user_by_id()`, `update_credits()`, `update_profile()`

**预计时间**: 1.5 小时

---

#### 1.2 修复 project_repository.py

**文件**: `infrastructure/repositories/project_repository.py`

**改动清单**:
```python
# 全局替换:
.eq("project_id", ...) → .eq("id", ...)
.eq("owner_id", ...) → .eq("user_id", ...)
.select("project_id, ...") → .select("id as project_id, ...")
.select("owner_id") → .select("user_id as owner_id")

# 移除字段引用:
listing_status  # 完全移除
content_hash    # 完全移除

# 移除表引用:
table("project_pages")  # 移除所有引用（表不存在）
```

**新增 Schema 字段**:
```sql
ALTER TABLE projects
ADD COLUMN is_permanently_deleted BOOLEAN DEFAULT false;
```

**验证**:
- ✅ 测试项目 CRUD 操作
- ✅ 测试项目-市场关联查询

**预计时间**: 2 小时

---

#### 1.3 修复 credit_repository.py

**文件**: `infrastructure/repositories/credit_repository.py`

**改动清单**:
```python
# Line 281:
.eq("tx_type", tx_type.value) → .eq("transaction_type", tx_type.value)

# Line 354-356:
table("users") → table("profiles")

# Line 641:
移除 credits_reset_at 引用（将字段添加到 profiles 表）
```

**验证**:
- ✅ 测试积分扣减
- ✅ 测试交易历史查询

**预计时间**: 1 小时

---

#### 1.4 修复 listing_repository.py

**文件**: `infrastructure/repositories/listing_repository.py`

**改动清单**:
```python
# Line 103, 116:
.eq("buyer_id", buyer_id) → .eq("user_id", buyer_id)
.insert({"buyer_id": ...}) → .insert({"user_id": ...})

# 注释掉 listing_usages 和 marketplace_reports 引用（暂时）
# 等 Phase 2 创建表后再启用
```

**预计时间**: 0.5 小时

---

**Phase 1 总计**: ~5 小时

---

### Phase 2: 创建缺失的核心表 (P0 - 1-2 天内)

**目标**: 创建 4 个 P0 优先级的缺失表

#### 2.1 创建 user_events 表

**表定义**:
```sql
CREATE TABLE user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    session_id TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_event_type CHECK (
        event_type IN (
            'page_view', 'button_click', 'form_submit',
            'feature_used', 'error_occurred', 'api_call'
        )
    )
);

CREATE INDEX idx_user_events_user_id ON user_events(user_id);
CREATE INDEX idx_user_events_event_type ON user_events(event_type);
CREATE INDEX idx_user_events_created_at ON user_events(created_at DESC);
```

**Repository 修复**:
- ✅ `events_repository.py` 无需修改（已正确引用表名）

**预计时间**: 0.5 小时

---

#### 2.2 创建 aggregated_stats 表

**表定义**:
```sql
CREATE TABLE aggregated_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type TEXT NOT NULL,  -- 'daily', 'weekly', 'monthly'
    stat_key TEXT NOT NULL,   -- 事件类型或指标名
    stat_value NUMERIC DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_stat_type CHECK (
        stat_type IN ('daily', 'weekly', 'monthly', 'custom')
    ),
    CONSTRAINT unique_aggregated_stat UNIQUE (stat_type, stat_key, period_start)
);

CREATE INDEX idx_aggregated_stats_period ON aggregated_stats(period_start DESC);
CREATE INDEX idx_aggregated_stats_type_key ON aggregated_stats(stat_type, stat_key);
```

**预计时间**: 0.5 小时

---

#### 2.3 创建 error_logs 表

**表定义**:
```sql
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    request_path TEXT,
    request_method TEXT,
    request_body JSONB,
    status_code INTEGER,
    severity TEXT DEFAULT 'error',
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_severity CHECK (
        severity IN ('debug', 'info', 'warning', 'error', 'critical')
    )
);

CREATE INDEX idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX idx_error_logs_resolved ON error_logs(resolved, created_at DESC);
CREATE INDEX idx_error_logs_severity ON error_logs(severity, created_at DESC);
```

**Repository 修复**:
- ✅ `error_logs_repository.py` 无需修改

**预计时间**: 0.5 小时

---

#### 2.4 创建 support_tickets 和 support_replies 表

**表定义**:
```sql
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    priority TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'open',
    assigned_to TEXT,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,

    CONSTRAINT check_priority CHECK (
        priority IN ('low', 'normal', 'high', 'urgent')
    ),
    CONSTRAINT check_status CHECK (
        status IN ('open', 'pending', 'in_progress', 'resolved', 'closed')
    )
);

CREATE TABLE support_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    is_staff BOOLEAN DEFAULT false,
    message TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_message_length CHECK (length(message) > 0)
);

CREATE INDEX idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX idx_support_tickets_status ON support_tickets(status, created_at DESC);
CREATE INDEX idx_support_replies_ticket_id ON support_replies(ticket_id, created_at);
```

**Repository 修复**:
- ✅ `support_repository.py` 无需修改

**预计时间**: 1 小时

---

**Phase 2 总计**: ~2.5 小时

---

### Phase 3: 创建 P1 优先级缺失表 (1 周内)

#### 3.1 创建管理员/市场/指标表

**表清单**:
1. `admin_operations` - 管理员操作日志
2. `listing_usages` - 资产使用追踪
3. `marketplace_reports` - 市场报告
4. `daily_metrics` - 每日指标
5. `monthly_metrics` - 月度指标

**表定义示例** (admin_operations):
```sql
CREATE TABLE admin_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    operation_type TEXT NOT NULL,
    target_type TEXT,  -- 'user', 'project', 'listing', etc.
    target_id TEXT,
    action TEXT NOT NULL,
    changes JSONB DEFAULT '{}',
    reason TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_operation_type CHECK (
        operation_type IN (
            'user_management', 'content_moderation', 'system_config',
            'billing_adjustment', 'feature_flag', 'data_migration'
        )
    )
);

CREATE INDEX idx_admin_operations_admin_id ON admin_operations(admin_id);
CREATE INDEX idx_admin_operations_target ON admin_operations(target_type, target_id);
CREATE INDEX idx_admin_operations_created_at ON admin_operations(created_at DESC);
```

**预计时间**: 3 小时（5 个表）

---

### Phase 4: 实现孤立表的 Repository (1-2 周)

**目标**: 为 8 个"有表无代码"的表创建 Repository

#### 4.1 创建 pricing_repository.py (P0)

**文件**: `infrastructure/repositories/pricing_repository.py`

**方法清单**:
```python
class PricingRepository:
    async def get_plan_by_code(self, plan_code: str) -> Optional[Dict]
    async def get_active_plans(self) -> List[Dict]
    async def create_plan(self, plan_data: Dict) -> Dict
    async def update_plan(self, plan_id: str, updates: Dict) -> Dict
    async def get_plan_history(self, plan_id: str) -> List[Dict]
    async def get_user_price_override(self, user_id: str) -> Optional[Dict]
    async def set_user_price_override(self, user_id: str, override_data: Dict) -> Dict
```

**预计时间**: 2 小时

---

#### 4.2 创建 onboarding_repository.py (P1)

**文件**: `infrastructure/repositories/onboarding_repository.py`

**方法清单**:
```python
class OnboardingRepository:
    async def get_onboarding_steps(self) -> List[Dict]
    async def get_user_progress(self, user_id: str) -> List[Dict]
    async def complete_step(self, user_id: str, step_key: str) -> bool
    async def reset_progress(self, user_id: str) -> bool
```

**预计时间**: 1.5 小时

---

#### 4.3 创建 themes_repository.py (P1)

**文件**: `infrastructure/repositories/themes_repository.py`

**方法清单**:
```python
class ThemesRepository:
    async def get_daily_theme(self, date: str) -> Optional[Dict]
    async def get_holiday_by_date(self, date: str) -> Optional[Dict]
    async def create_daily_theme(self, theme_data: Dict) -> Dict
    async def update_daily_theme(self, theme_id: str, updates: Dict) -> Dict
```

**预计时间**: 1.5 小时

---

**Phase 4 总计**: ~5 小时

---

### Phase 5: 测试与验证 (全面测试)

#### 5.1 单元测试

**创建/更新测试文件**:
```
tests/infrastructure/repositories/
├── test_user_repository.py          (更新)
├── test_project_repository.py       (更新)
├── test_credit_repository.py        (更新)
├── test_listing_repository.py       (更新)
├── test_events_repository.py        (更新)
├── test_error_logs_repository.py    (更新)
├── test_support_repository.py       (更新)
├── test_pricing_repository.py       (新建)
├── test_onboarding_repository.py    (新建)
└── test_themes_repository.py        (新建)
```

**测试覆盖**:
- ✅ 每个 Repository 方法的正常流程
- ✅ 边界条件测试
- ✅ 错误处理测试
- ✅ 数据完整性验证

**预计时间**: 4 小时

---

#### 5.2 集成测试

**测试场景**:
1. 用户注册 → 创建 profile → 初始化积分 → 分配新手引导
2. 项目创建 → 关联市场 → 购买流程
3. AI 生成 → 积分扣减 → 日志记录
4. 错误发生 → 错误日志 → 管理员查看

**预计时间**: 2 小时

---

#### 5.3 数据迁移验证

**检查项**:
- ✅ 所有表的数据完整性
- ✅ 外键约束正确
- ✅ 索引创建成功
- ✅ 无孤立数据

**预计时间**: 1 小时

---

**Phase 5 总计**: ~7 小时

---

## 五、总体时间估算

| Phase | 任务 | 预计时间 | 累计时间 |
|-------|------|---------|---------|
| Phase 1 | 修复核心表引用 | 5 小时 | 5 小时 |
| Phase 2 | 创建 P0 缺失表 | 2.5 小时 | 7.5 小时 |
| Phase 3 | 创建 P1 缺失表 | 3 小时 | 10.5 小时 |
| Phase 4 | 实现孤立表 Repository | 5 小时 | 15.5 小时 |
| Phase 5 | 测试与验证 | 7 小时 | 22.5 小时 |

**总计**: 22.5 小时（约 3 个工作日）

**分阶段交付**:
- 🎯 Day 1 结束: Phase 1 + Phase 2 完成（核心功能恢复）
- 🎯 Day 2 结束: Phase 3 + Phase 4 完成（所有功能完整）
- 🎯 Day 3 结束: Phase 5 完成（测试通过）

---

## 六、风险评估与缓解

### 6.1 风险清单

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 数据迁移失败 | 🟡 Medium | 🔴 High | 1. 提前备份数据库<br>2. 分批迁移<br>3. 回滚脚本准备 |
| 外键约束冲突 | 🟡 Medium | 🟡 Medium | 1. 先创建表，后添加外键<br>2. 使用 ON DELETE SET NULL |
| Repository 测试失败 | 🟢 Low | 🟡 Medium | 1. 增量测试<br>2. Mock 数据库测试 |
| 线上服务中断 | 🟢 Low | 🔴 High | 1. 灰度发布<br>2. Feature Flag 控制<br>3. 快速回滚机制 |

### 6.2 回滚策略

**触发条件**:
- ❌ 任何 Phase 测试失败率 > 10%
- ❌ 生产环境出现数据不一致
- ❌ 关键业务流程中断

**回滚步骤**:
1. 停止部署流程
2. 恢复数据库备份（如有数据变更）
3. 回滚代码到上一个稳定版本
4. 验证核心功能
5. 重新评估问题并调整方案

---

## 七、成功标准

### 7.1 技术指标

✅ **代码层面**:
- 所有 Repository 文件不再引用不存在的表
- 所有字段名与 Schema 100% 匹配
- 所有外键引用正确
- 代码质量：无 pylint/mypy 错误

✅ **数据库层面**:
- Schema 与实际表结构一致
- 所有索引创建成功
- 外键约束生效
- 无孤立表/孤立字段

✅ **测试层面**:
- 单元测试覆盖率 ≥ 80%
- 所有 Repository 测试通过
- 集成测试通过率 100%
- 无数据完整性问题

### 7.2 业务指标

✅ **功能恢复**:
- 用户管理功能正常
- 项目管理功能正常
- 积分系统正常
- 市场功能正常
- 错误日志正常
- 支持系统正常

✅ **新功能启用**:
- 定价系统可管理
- 新手引导系统可用
- 主题系统可用

---

## 八、执行检查清单

### Phase 1: 核心表修复
- [ ] user_repository.py 修改完成
- [ ] profiles 表字段补充完成
- [ ] project_repository.py 修改完成
- [ ] projects 表字段补充完成
- [ ] credit_repository.py 修改完成
- [ ] listing_repository.py 修改完成
- [ ] 单元测试通过

### Phase 2: P0 表创建
- [ ] user_events 表创建
- [ ] aggregated_stats 表创建
- [ ] error_logs 表创建
- [ ] support_tickets 表创建
- [ ] support_replies 表创建
- [ ] Repository 测试通过

### Phase 3: P1 表创建
- [ ] admin_operations 表创建
- [ ] listing_usages 表创建
- [ ] marketplace_reports 表创建
- [ ] daily_metrics 表创建
- [ ] monthly_metrics 表创建
- [ ] 索引创建完成

### Phase 4: Repository 实现
- [ ] pricing_repository.py 创建
- [ ] onboarding_repository.py 创建
- [ ] themes_repository.py 创建
- [ ] Container 注册完成
- [ ] Service 层集成完成

### Phase 5: 测试验证
- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 数据迁移验证完成
- [ ] 性能测试通过
- [ ] 文档更新完成

---

## 九、后续优化建议

### 9.1 架构优化

1. **Schema 版本管理**
   - 使用 Alembic 或 Flyway 进行 Schema 版本控制
   - 每次 Schema 变更生成迁移脚本
   - 自动化 Schema 同步检查

2. **Repository 接口规范化**
   - 统一 Repository 方法命名
   - 统一返回类型（Entity vs Dict）
   - 统一错误处理

3. **自动化检测**
   - CI/CD 中集成 Schema-Code 一致性检查
   - 自动生成 Repository 代码（基于 Schema）
   - 自动化测试数据生成

### 9.2 技术债务清理

1. **移除 Legacy 代码**
   - 删除所有 `project_pages` 引用
   - 删除 `listing_status` 逻辑
   - 清理未使用的导入

2. **统一命名规范**
   - 所有表使用 snake_case
   - 所有主键统一命名为 `id`
   - 外键统一命名为 `<table>_id`

3. **性能优化**
   - 审查所有查询，添加缺失索引
   - 优化 N+1 查询问题
   - 添加查询缓存

---

## 十、附录

### A. 关键文件清单

**需要修改的文件**:
```
infrastructure/repositories/
├── user_repository.py           (23 处修改)
├── project_repository.py        (18 处修改)
├── credit_repository.py         (5 处修改)
├── listing_repository.py        (8 处修改)
├── events_repository.py         (无需修改，但需建表)
├── error_logs_repository.py     (无需修改，但需建表)
├── support_repository.py        (无需修改，但需建表)
├── admin_repository.py          (需建表)
├── metrics_repository.py        (需建表)

新建文件:
├── pricing_repository.py        (新建)
├── onboarding_repository.py     (新建)
└── themes_repository.py         (新建)
```

**需要更新的 Schema**:
```
migrations/v2/
├── refactored_schema_v2.sql     (作为参考，不修改)
└── patches/
    ├── 001_add_profiles_fields.sql
    ├── 002_add_projects_fields.sql
    ├── 003_create_user_events.sql
    ├── 004_create_aggregated_stats.sql
    ├── 005_create_error_logs.sql
    ├── 006_create_support_tables.sql
    ├── 007_create_admin_operations.sql
    ├── 008_create_marketplace_tables.sql
    └── 009_create_metrics_tables.sql
```

### B. 数据库变更 SQL 模板

见各 Phase 的详细说明。

### C. 测试数据脚本

```python
# scripts/tools/generate_test_data.py
# 生成符合新 Schema 的测试数据
```

---

**文档版本**: v1.0
**最后更新**: 2026-01-10
**审查人**: Claude Sonnet 4.5
**状态**: 待用户确认后执行
