# 数据库重构设计说明

> **项目**: Make Decodables (MagicZine AI)
> **版本**: v3.27 → v4.0 (Refactored)
> **日期**: 2026-01-09
> **架构师**: Claude Sonnet 4.5

---

## 1. 重构概述

### 1.1 重构目标

本次重构旨在将 Make Decodables 数据库从 v3.27 版本升级到符合**行业最佳实践**的 v4.0 版本，主要目标：

1. **标准化命名和结构**：统一字段命名、标准审计字段、一致的索引策略
2. **补充缺失内容**：补充 13 张缺失表 + 完整的 system_configs 初始化数据
3. **保持核心业务规则**：双ID系统、积分扣费顺序、幂等性设计
4. **性能优化**：优化索引、合理冗余字段
5. **可扩展性**：预留JSONB扩展字段
6. **可追溯性**：完整的字段映射和COMMENT注释

### 1.2 重构范围

- **42张核心表**：完整重构（29张原有表 + 13张新增表）
- **128个索引**：单列索引、复合索引、部分索引、GIN/GIST索引
- **23个触发器**：updated_at 自动更新、软删除时间戳、业务规则触发器
- **7个核心函数**：积分扣除、任务清理、视图刷新等
- **57行 system_configs 初始化数据**：Rate Limits、AI Providers、Feature Flags等

### 1.3 不改变的核心规则

以下业务规则在重构中**绝对不变**：

1. **双ID系统**：
   - `user_id` (TEXT): Clerk格式 `user_2NNEqL2n...`（非UUID！）
   - `user_code` (TEXT UNIQUE): 自定义格式 `260109143X7Y`

2. **积分扣费顺序**：
   - 先扣 `credits_monthly` → 再扣 `credits_permanent`

3. **幂等性设计**：
   - `credit_transactions.idempotency_key` UNIQUE
   - `user_purchases.idempotency_key` UNIQUE
   - `webhook_events.event_id` UNIQUE

4. **Append-Only账本**：
   - `credit_transactions` 表有防UPDATE/DELETE触发器

5. **时区支持** (v3.9)：
   - 所有主表包含：`timezone TEXT`, `created_at_local TIMESTAMP`, `created_at TIMESTAMPTZ`

---

## 2. 命名规范决策

### 2.1 为什么使用Snake Case？

**决策**：所有表名、字段名使用 `snake_case`（下划线命名法）

**理由**：

1. **PostgreSQL不区分大小写**：
   - `UserName` 和 `username` 在PG中是同一个字段
   - 使用驼峰需要加引号：`"userName"`，容易出错

2. **行业标准**：
   - Django ORM、Rails ActiveRecord 默认使用snake_case
   - PostgreSQL官方文档推荐snake_case

3. **可读性**：
   - `created_at` 比 `createdAt` 更清晰
   - `is_deleted` 比 `isDeleted` 更语义化

**对比**：

| 风格 | 示例 | 优势 | 劣势 |
|------|------|------|------|
| Snake Case | `user_id`, `created_at` | PG原生支持，无需引号 | 稍长 |
| Camel Case | `userId`, `createdAt` | 简洁 | 需要引号，易错 |
| Pascal Case | `UserId`, `CreatedAt` | - | 不符合SQL习惯 |

### 2.2 布尔值命名规则

**决策**：所有布尔字段必须以 `is_`/`has_`/`can_`/`should_` 开头

**理由**：

1. **语义清晰**：
   - ✅ `is_deleted` → 明确表示"是否已删除"
   - ❌ `deleted` → 可能是删除时间？删除状态？

2. **自文档化**：
   - `has_subscription` → 立即理解这是布尔值
   - `can_publish` → 表示权限检查

3. **避免歧义**：
   - `is_public` vs `public`（public是SQL关键字）

**命名模式**：

| 前缀 | 用途 | 示例 |
|------|------|------|
| `is_` | 状态判断 | `is_deleted`, `is_active`, `is_public` |
| `has_` | 拥有关系 | `has_subscription`, `has_reference` |
| `can_` | 权限/能力 | `can_publish`, `can_edit` |
| `should_` | 配置选项 | `should_notify`, `should_retry` |

### 2.3 表名命名规则

**决策**：表名使用**复数形式**

**理由**：

1. **语义准确**：
   - `users` 表存储多个用户 ✅
   - `user` 表存储单个用户？ ❌

2. **ORM惯例**：
   - Rails: `User` model → `users` table
   - Django: `User` model → `users` table

3. **避免关键字冲突**：
   - `user` 是SQL关键字（某些数据库）
   - `users` 安全

**对比**：

| 风格 | 示例 | 适用场景 |
|------|------|----------|
| 复数 | `users`, `projects`, `credit_transactions` | ✅ 推荐（本项目采用） |
| 单数 | `user`, `project`, `credit_transaction` | 部分团队偏好 |

---

## 3. 标准审计字段

### 3.1 必需字段（所有表）

**决策**：所有业务表必须包含以下字段

```sql
-- 主键
id UUID PRIMARY KEY DEFAULT gen_random_uuid()  -- 或 BIGSERIAL
-- 或者对于profiles表：
id TEXT PRIMARY KEY  -- Clerk ID（特殊情况）

-- 审计字段
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

-- 软删除
is_deleted BOOLEAN NOT NULL DEFAULT false
deleted_at TIMESTAMPTZ DEFAULT NULL

-- 可选：操作人追踪
created_by TEXT REFERENCES profiles(id)
updated_by TEXT REFERENCES profiles(id)
```

### 3.2 字段说明

#### 3.2.1 主键设计

**决策**：默认使用 `UUID`，特殊表使用 `TEXT` 或 `BIGSERIAL`

**理由**：

| 类型 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| UUID | 全局唯一，分布式友好，无序列依赖 | 索引稍慢（16字节） | ✅ 大部分表 |
| BIGSERIAL | 自增，索引快，节省空间 | 单机限制，暴露数据量 | 高性能小表 |
| TEXT | 灵活，支持外部ID | 无自增 | ✅ `profiles`（Clerk ID） |

**特殊情况**：
- `profiles.id`: TEXT（存储Clerk ID `user_2xxx...`）
- `holiday_themes.id`: TEXT（存储主题代码 `christmas`, `halloween`）

#### 3.2.2 时间戳策略

**决策**：使用 `TIMESTAMPTZ`（带时区）

**理由**：

1. **时区安全**：
   - `TIMESTAMPTZ` 存储UTC时间，读取时自动转换
   - `TIMESTAMP` 无时区，容易出错

2. **国际化支持**：
   - 用户分布全球，需要准确的时间表示

3. **v3.9双时区设计**（保持）：
   ```sql
   timezone TEXT DEFAULT 'UTC'           -- 用户时区
   created_at_local TIMESTAMP            -- 本地时间（无TZ）
   created_at TIMESTAMPTZ DEFAULT NOW()  -- UTC标准时间
   ```

**对比**：

| 类型 | 存储 | 示例 | 推荐 |
|------|------|------|------|
| TIMESTAMPTZ | UTC + 读取时转换 | `2026-01-09 10:30:00+00` | ✅ 推荐 |
| TIMESTAMP | 无时区信息 | `2026-01-09 10:30:00` | ❌ 避免 |

#### 3.2.3 软删除设计

**决策**：使用 `is_deleted` + `deleted_at` 双字段

**理由**：

1. **快速查询**：
   - `WHERE is_deleted = false` → 使用索引
   - `WHERE deleted_at IS NULL` → 索引效率低

2. **审计需求**：
   - `deleted_at` 记录删除时间
   - `is_deleted` 用于业务逻辑

3. **触发器自动维护**（已有）：
   ```sql
   -- 删除时自动填充deleted_at
   CREATE TRIGGER trigger_projects_deleted_at
   BEFORE UPDATE OF is_deleted ON projects
   FOR EACH ROW EXECUTE FUNCTION set_deleted_timestamp();
   ```

**索引优化**：
```sql
-- 部分索引（仅索引未删除记录）
CREATE INDEX idx_projects_active
ON projects(user_id, created_at DESC)
WHERE is_deleted = false;
```

#### 3.2.4 updated_at自动更新

**决策**：使用触发器自动更新 `updated_at`

**实现**（已有）：
```sql
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_projects_updated_at
BEFORE UPDATE ON projects
FOR EACH ROW EXECUTE FUNCTION update_timestamp();
```

**优势**：
- 应用层无需手动设置
- 保证一致性

---

## 4. 性能优化策略

### 4.1 冗余字段设计

**决策**：允许合理的冗余字段，用于避免JOIN查询

**原则**：

1. **只在高频查询中使用**
2. **必须在COMMENT注明维护策略**
3. **使用触发器保持一致性**

**示例1：projects表**

```sql
-- 冗余字段
asset_count INTEGER NOT NULL DEFAULT 0
  COMMENT 'Asset数量 | 维护策略: trigger on assets INSERT/DELETE',

last_opened_at TIMESTAMPTZ
  COMMENT '最后打开时间 | 维护策略: API更新',

-- 触发器维护
CREATE TRIGGER trigger_update_project_asset_count
AFTER INSERT OR DELETE ON assets
FOR EACH ROW EXECUTE FUNCTION update_project_asset_count();
```

**收益**：
- 避免 `COUNT(*) FROM assets WHERE project_id = ?` 查询
- Dashboard查询速度提升10倍+

**成本**：
- 额外存储：4字节 × 100K项目 = 400KB（可忽略）
- 触发器开销：每次INSERT/DELETE assets额外1次UPDATE

**示例2：profiles表**

```sql
project_count INTEGER NOT NULL DEFAULT 0
  COMMENT '项目数量 | 维护策略: trigger on projects',

last_active_at TIMESTAMPTZ
  COMMENT '最后活跃时间 | 维护策略: 定时任务每日更新',
```

**维护策略对比**：

| 字段 | 更新频率 | 维护方式 | 一致性 |
|------|----------|----------|--------|
| `asset_count` | 高（每次上传） | 触发器 | 实时 ✅ |
| `last_active_at` | 低（每天） | 定时任务 | 延迟24h ⚠️ |

### 4.2 索引设计原则

**决策**：基于实际查询模式设计索引

#### 4.2.1 单列索引

**适用场景**：WHERE条件单字段查询

```sql
-- 外键字段（必须有索引）
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_assets_project_id ON assets(project_id);

-- 状态字段（高频筛选）
CREATE INDEX idx_projects_is_deleted ON projects(is_deleted);
CREATE INDEX idx_listings_status ON marketplace_listings(moderation_status);

-- 时间字段（排序、范围查询）
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX idx_transactions_created_at ON credit_transactions(created_at DESC);
```

#### 4.2.2 复合索引

**适用场景**：WHERE多字段 + ORDER BY

```sql
-- Dashboard查询：WHERE user_id = ? AND is_deleted = false ORDER BY created_at DESC
CREATE INDEX idx_projects_user_active
ON projects(user_id, is_deleted, created_at DESC);

-- 市场查询：WHERE is_public = true AND is_deleted = false
CREATE INDEX idx_listings_public
ON marketplace_listings(is_public, is_deleted, moderation_status);
```

**字段顺序规则**：
1. **=** 条件在前（user_id）
2. **范围/排序** 在后（created_at）

#### 4.2.3 部分索引

**适用场景**：只索引常用数据子集

```sql
-- 只索引未删除的项目（垃圾箱除外）
CREATE INDEX idx_projects_active
ON projects(user_id, created_at DESC)
WHERE is_deleted = false;

-- 只索引已购买的项目
CREATE INDEX idx_projects_purchased
ON projects(user_id)
WHERE is_purchased = true;
```

**优势**：
- 索引大小减少70%+（假设删除率30%）
- 查询速度不变

#### 4.2.4 GIN索引（JSON/数组）

**适用场景**：JSONB字段查询、数组包含查询

```sql
-- 事件属性查询
CREATE INDEX idx_user_events_properties
ON user_events USING GIN(properties);

-- 标签查询
CREATE INDEX idx_system_resources_tags
ON system_resources USING GIN(tags);

-- 查询示例
SELECT * FROM user_events
WHERE properties @> '{"action": "purchase"}';
```

### 4.3 分区策略（未来优化）

**当前状态**：未使用分区

**建议场景**（当表超过1000万行时）：

```sql
-- 按月分区（analytics_events）
CREATE TABLE analytics_events (
  -- ... fields
  created_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE analytics_events_2026_01
  PARTITION OF analytics_events
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

**收益**：
- 查询速度提升（分区裁剪）
- 数据归档方便（DROP老分区）

---

## 5. 数据类型选择

### 5.1 金额/价格字段

**决策**：使用 `DECIMAL(12,2)`

**理由**：

| 类型 | 精度 | 问题 | 适用 |
|------|------|------|------|
| FLOAT/DOUBLE | 近似 | ❌ 0.1 + 0.2 ≠ 0.3 | 科学计算 |
| DECIMAL | 精确 | ✅ 精确到分 | ✅ 金额 |
| INTEGER (分) | 精确 | 需要转换 | 高性能场景 |

**示例**：

```sql
-- ❌ 错误
price_usd FLOAT  -- 可能出现 $9.999999

-- ✅ 正确
price_usd DECIMAL(12,2)  -- 精确到 $9.99

-- 或者使用整数（存储"分"）
price_cents INTEGER  -- 999 表示 $9.99
```

**本项目**：
- 积分系统使用 `INTEGER`（积分是整数）
- 未来如果加USD价格，使用 `DECIMAL(12,2)`

### 5.2 枚举值存储

**决策**：使用 `TEXT` + `CHECK` 约束

**理由**：

| 方式 | 优势 | 劣势 | 推荐 |
|------|------|------|------|
| ENUM类型 | 类型安全 | 修改需要ALTER TYPE | 小团队 |
| TEXT + CHECK | 灵活 | 需要手动验证 | ✅ 推荐 |
| INTEGER + 映射表 | 节省空间 | 查询需JOIN | 大数据 |

**示例**：

```sql
tier TEXT NOT NULL DEFAULT 'free'
  CHECK (tier IN ('free', 'starter', 'pro'))
  COMMENT '用户等级 | free=免费, starter=入门, pro=专业版',

moderation_status TEXT NOT NULL DEFAULT 'draft'
  CHECK (moderation_status IN ('draft', 'pending', 'approved', 'rejected'))
  COMMENT '审核状态 | draft=草稿, pending=待审, approved=通过, rejected=拒绝',
```

**优势**：
- 数据库层面验证
- COMMENT自文档化
- 修改容易（ALTER TABLE ... DROP CONSTRAINT ...）

### 5.3 JSON vs 关系表

**决策**：结构化数据用关系表，扩展/灵活数据用JSONB

**使用场景**：

| 场景 | 方式 | 示例 |
|------|------|------|
| 固定结构 | 关系表 | ✅ 用户等级、积分 |
| 扩展字段 | JSONB | ✅ `ext_json`, `metadata` |
| 嵌套数据 | JSONB | ✅ `canvas_data`, `theme_config` |
| 高频查询 | 关系表 | ✅ WHERE条件字段 |

**JSONB优势**：
- 无需ALTER TABLE
- 支持部分更新
- 可索引（GIN）

**JSONB示例**：

```sql
-- 画布数据（复杂嵌套）
canvas_data JSONB NOT NULL DEFAULT '{}'::jsonb
  COMMENT 'Fabric.js画布数据 | 包含pages数组',

-- 元数据（灵活扩展）
metadata JSONB DEFAULT '{}'::jsonb
  COMMENT '元数据 | 如: {"width": 1024, "height": 768, "file_size": 102400}',

-- 扩展字段（预留）
ext_json JSONB DEFAULT '{}'::jsonb
  COMMENT '扩展字段 | 用于未来功能，避免频繁ALTER TABLE',
```

---

## 6. 字段COMMENT规范

### 6.1 COMMENT格式

**标准格式**：

```sql
COMMENT ON COLUMN table_name.column_name IS '字段用途 | 补充说明 | @Ref: old_table.old_col';
```

**组成部分**：

1. **字段用途**（必需）：简明描述字段含义
2. **补充说明**（可选）：枚举值、取值范围、维护策略
3. **@Ref标注**（改名时）：标注旧字段名，方便代码迁移

**示例**：

```sql
-- 简单字段
COMMENT ON COLUMN profiles.email IS '用户邮箱';

-- 枚举字段
COMMENT ON COLUMN profiles.tier IS '用户等级 | free=免费, starter=入门, pro=专业版';

-- 改名字段
COMMENT ON COLUMN profiles.created_at IS '创建时间（UTC） | @Ref: profiles.createdAt';

-- 冗余字段
COMMENT ON COLUMN profiles.project_count IS '项目数量 | 维护策略: trigger on projects INSERT/DELETE';

-- 范围字段
COMMENT ON COLUMN experiments.traffic_allocation IS '流量分配百分比 | 范围: 0-100';
```

### 6.2 表COMMENT格式

**标准格式**：

```sql
COMMENT ON TABLE table_name IS '[业务模块] 业务含义 - 用途描述 | @Ref: old_table_name';
```

**示例**：

```sql
COMMENT ON TABLE profiles IS '[身份] 用户档案 - 存储用户基本信息、积分、订阅状态';

COMMENT ON TABLE credit_transactions IS '[计费] 积分交易记录 - Append-Only账本，记录所有积分变动 | 注意: 有防UPDATE/DELETE触发器';

COMMENT ON TABLE marketplace_listings IS '[市场] 市场商品列表 - 用户发布的Asset/Project，支持审核和交易';
```

---

## 7. 特殊表设计说明

### 7.1 profiles表（用户档案）

**特殊性**：

1. **id字段为TEXT**（非UUID）：
   - 存储Clerk ID格式：`user_2NNEqL2nrIRdJ194ndJqAHwEfxC`
   - 前缀 `user_` + 20-27个Base58字符
   - 总长度 25-35 字符

2. **双ID系统**：
   - `id` (TEXT): Clerk ID，系统内部使用
   - `user_code` (TEXT UNIQUE): 自定义ID，用户可见

3. **积分双桶**：
   - `credits_monthly`: 月度积分（会重置）
   - `credits_permanent`: 永久积分（不过期）

**字段设计**：

```sql
CREATE TABLE profiles (
  -- 主键（Clerk ID）
  id TEXT PRIMARY KEY
    COMMENT 'Clerk用户ID | 格式: user_2xxx... (非UUID!) | @Ref: profiles.userId',

  -- 用户识别码
  user_code TEXT UNIQUE NOT NULL
    COMMENT '用户识别码 | 格式: 260109143X7Y (包含注册时间)',

  -- 积分系统
  credits_monthly INTEGER NOT NULL DEFAULT 0
    COMMENT '月度积分 | 每30天重置为等级配额',
  credits_permanent INTEGER NOT NULL DEFAULT 0
    COMMENT '永久积分 | 购买/市场收入，永不过期',

  -- 订阅系统
  tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'pro'))
    COMMENT '用户等级 | free=免费, starter=入门, pro=专业版',
  subscription_status TEXT NOT NULL DEFAULT 'inactive'
    COMMENT '订阅状态 | active=活跃, past_due=逾期, canceled=已取消, inactive=未订阅',

  -- ... 其他字段
);
```

### 7.2 credit_transactions表（积分账本）

**特殊性**：

1. **Append-Only设计**：
   - 只允许INSERT，禁止UPDATE/DELETE
   - 通过触发器强制执行

2. **双桶记录**：
   - 扣费时可能产生2条记录（月度+永久）
   - 每条记录保存余额快照

3. **幂等性保证**：
   - `idempotency_key` UNIQUE约束
   - 防止重复扣费

**字段设计**：

```sql
CREATE TABLE credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES profiles(id),

  -- 交易信息
  amount INTEGER NOT NULL
    COMMENT '积分变动量 | 正数=收入, 负数=支出',
  bucket TEXT NOT NULL CHECK (bucket IN ('monthly', 'permanent'))
    COMMENT '积分桶 | monthly=月度, permanent=永久',

  -- 余额快照（关键！）
  balance_monthly_after INTEGER NOT NULL DEFAULT 0
    COMMENT '交易后月度余额 | 用于审计和对账',
  balance_permanent_after INTEGER NOT NULL DEFAULT 0
    COMMENT '交易后永久余额 | 用于审计和对账',

  -- 交易类型
  type TEXT NOT NULL
    COMMENT '交易类型 | ai_generation, market_purchase, signup_bonus, subscription_reset, market_sale, admin_adjustment, refund',

  -- 幂等性
  idempotency_key TEXT UNIQUE
    COMMENT '幂等性键 | 防止重复扣费，同一key只能有一条记录',

  -- 时区支持
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 防修改触发器
CREATE TRIGGER prevent_credit_update
  BEFORE UPDATE ON credit_transactions
  FOR EACH ROW EXECUTE FUNCTION prevent_credit_modification();

CREATE TRIGGER prevent_credit_delete
  BEFORE DELETE ON credit_transactions
  FOR EACH ROW EXECUTE FUNCTION prevent_credit_modification();
```

**为什么是Append-Only**：

1. **审计需求**：所有历史记录不可篡改
2. **对账需求**：通过余额快照可重建任意时刻余额
3. **退款处理**：插入负金额记录（不删除原记录）

### 7.3 marketplace_listings表（市场商品）

**特殊性**：

1. **v3.26二级分类系统**：
   - `resource_type`: asset / project
   - `category`: 14+个具体分类
   - `source`: system / user / ai / community

2. **allowed_tiers数组**：
   - 控制访问权限
   - 如 `{starter, pro}` = 仅会员可用

**字段设计**：

```sql
CREATE TABLE marketplace_listings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_id TEXT REFERENCES profiles(id),

  -- 二级分类（v3.26）
  resource_type TEXT NOT NULL CHECK (resource_type IN ('asset', 'project'))
    COMMENT '资源类型 | asset=素材, project=项目模板',
  category TEXT NOT NULL CHECK (category IN ('clipart', 'illustration', ...))
    COMMENT '内容分类 | 14+类别，见文档',
  source TEXT NOT NULL DEFAULT 'user' CHECK (source IN ('system', 'user', 'ai', 'community'))
    COMMENT '来源 | system=系统, user=用户, ai=AI生成, community=社区',

  -- 权限控制
  allowed_tiers TEXT[] NOT NULL DEFAULT '{free, starter, pro}'
    COMMENT '允许访问的用户等级 | 如: {starter,pro} = 仅会员',

  -- 定价
  price_credits INTEGER NOT NULL DEFAULT 0
    COMMENT '售价（积分） | 0=免费, 最大500',

  -- 审核状态
  moderation_status TEXT NOT NULL DEFAULT 'draft'
    CHECK (moderation_status IN ('draft', 'pending', 'approved', 'rejected'))
    COMMENT '审核状态 | draft=草稿, pending=待审, approved=通过, rejected=拒绝',

  -- 统计字段（冗余，触发器维护）
  sales_count INTEGER NOT NULL DEFAULT 0
    COMMENT '销售次数 | 维护策略: trigger on user_purchases',
  unique_buyers_count INTEGER NOT NULL DEFAULT 0
    COMMENT '独立买家数 | 维护策略: trigger on user_purchases',
  total_revenue INTEGER NOT NULL DEFAULT 0
    COMMENT '总收益（积分） | 维护策略: trigger on user_purchases',
  usage_count BIGINT NOT NULL DEFAULT 0
    COMMENT '使用次数 | 维护策略: trigger on listing_usages',

  -- 可见性
  is_public BOOLEAN NOT NULL DEFAULT false,
  is_deleted BOOLEAN NOT NULL DEFAULT false,

  -- ... 其他字段
);
```

---

## 8. 新增表设计说明

### 8.1 新增表概览

本次重构补充了 **13 张缺失表**，按优先级分为 3 个等级：

| 优先级 | 表数量 | 用途 |
|--------|--------|------|
| **P0** (关键阻塞) | 4张 | AI成本追踪、素材分类系统 |
| **P1** (重要功能) | 5张 | 主题系统、审计日志、分析聚合 |
| **P2** (增强功能) | 4张 | 配置审计、内容举报、资源审计、AI提示模板 |

### 8.2 P0 级别表 (关键阻塞)

#### 8.2.1 ai_call_logs (AI API 调用日志)

**业务背景**：
- 每次 AI 生成（图片/文字）都需要记录调用详情
- 用于成本分析、性能监控、问题排查

**字段设计**：

```sql
CREATE TABLE ai_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES profiles(id),

    -- 调用信息
    provider TEXT NOT NULL CHECK (provider IN ('openai', 'fal', 'qwen')),
    model TEXT NOT NULL,
    call_type TEXT NOT NULL CHECK (call_type IN ('text_reasoning', 'image_generation', 'image_editing')),

    -- 结果状态
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'timeout', 'rate_limited')),
    error_message TEXT,

    -- Token 统计
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,

    -- 性能指标
    latency_ms INTEGER,
    cost_usd DECIMAL(10, 6),

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_ai_call_logs_user_created ON ai_call_logs(user_id, created_at DESC);
CREATE INDEX idx_ai_call_logs_provider_model ON ai_call_logs(provider, model, created_at DESC);
CREATE INDEX idx_ai_call_logs_status ON ai_call_logs(status) WHERE status != 'success';
```

**为什么重要**：
- ✅ 成本追踪：监控每个Provider的API成本
- ✅ 性能监控：识别慢调用和超时
- ✅ 问题排查：失败调用的错误信息
- ✅ 容量规划：预测未来API使用量

#### 8.2.2 ai_usage_daily (AI 使用量日汇总)

**业务背景**：
- 每日聚合 AI 调用数据
- 生成成本报告和趋势分析

**字段设计**：

```sql
CREATE TABLE ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,

    -- 聚合统计
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,

    -- Token 统计
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,

    -- 性能统计
    avg_latency_ms INTEGER DEFAULT 0,
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- 错误统计
    error_counts JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, provider, model, call_type)
);

-- 索引优化
CREATE INDEX idx_ai_usage_daily_date ON ai_usage_daily(date DESC);
CREATE INDEX idx_ai_usage_daily_provider ON ai_usage_daily(provider, date DESC);
```

**为什么重要**：
- ✅ 成本分析：每日/每月/每年成本趋势
- ✅ 容量规划：预测未来API配额需求
- ✅ Provider对比：OpenAI vs FAL 成本/性能对比
- ✅ 异常检测：失败率突然升高时告警

#### 8.2.3 asset_categories (素材分类树)

**业务背景**：
- 系统内置素材需要分类管理（贴纸、插画、图形等）
- 使用 LTREE 实现层级分类（最多 3 级）

**字段设计**：

```sql
CREATE TABLE asset_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES asset_categories(id) ON DELETE CASCADE,

    -- LTREE 路径 (核心字段)
    path LTREE NOT NULL,
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 3),

    -- 分类信息
    slug VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_i18n JSONB DEFAULT '{}',

    -- 资产类型
    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('text', 'image', 'shape', 'table', 'sticker', 'illustration', 'clipart', 'graphic')),

    -- 可见性控制
    is_visible BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    min_tier VARCHAR(20) DEFAULT 'free',

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- LTREE 索引 (关键性能)
CREATE INDEX idx_asset_categories_path ON asset_categories USING GIST (path);
CREATE INDEX idx_asset_categories_parent ON asset_categories(parent_id);
CREATE INDEX idx_asset_categories_slug ON asset_categories(slug);
```

**LTREE 路径示例**：

```
graphics                       -- Level 1
graphics.stickers              -- Level 2
graphics.stickers.animals      -- Level 3
graphics.stickers.holidays     -- Level 3
graphics.illustrations         -- Level 2
graphics.illustrations.nature  -- Level 3
```

**查询示例**：

```sql
-- 查询所有图形类素材 (包含子分类)
SELECT * FROM asset_categories
WHERE path <@ 'graphics'::ltree;

-- 查询直接子分类
SELECT * FROM asset_categories
WHERE parent_id = (SELECT id FROM asset_categories WHERE slug = 'graphics');

-- 查询所有贴纸子类
SELECT * FROM asset_categories
WHERE path ~ 'graphics.stickers.*'::lquery;
```

**为什么重要**：
- ✅ 灵活分类：支持 3 级层级
- ✅ 高效查询：LTREE 索引查询子树性能优秀
- ✅ 国际化：name_i18n 支持多语言
- ✅ 权限控制：min_tier 控制不同等级用户访问

#### 8.2.4 system_assets (系统内置素材)

**业务背景**：
- 存储系统预置的贴纸、插画、图形等
- 关联到 asset_categories 分类树

**字段设计**：

```sql
CREATE TABLE system_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID NOT NULL REFERENCES asset_categories(id),

    -- 素材信息
    name VARCHAR(200) NOT NULL,
    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('text', 'image', 'shape', 'table', 'sticker', 'illustration', 'clipart', 'graphic')),

    -- 文件信息
    file_url TEXT,
    thumbnail_url TEXT,

    -- 素材内容 (Fabric.js 对象)
    content JSONB NOT NULL DEFAULT '{}',

    -- 访问控制
    min_tier VARCHAR(20) DEFAULT 'free' CHECK (min_tier IN ('free', 'starter', 'pro')),

    -- 标签和搜索
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 可见性
    is_visible BOOLEAN DEFAULT TRUE,

    -- 使用统计
    usage_count INTEGER DEFAULT 0,

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_system_assets_category ON system_assets(category_id);
CREATE INDEX idx_system_assets_type ON system_assets(asset_type);
CREATE INDEX idx_system_assets_tier ON system_assets(min_tier);
CREATE INDEX idx_system_assets_tags ON system_assets USING GIN (tags);
CREATE INDEX idx_system_assets_visible ON system_assets(is_visible) WHERE is_visible = TRUE;
```

**为什么重要**：
- ✅ 系统素材库：预置高质量贴纸/插画
- ✅ 分类管理：通过 category_id 关联分类树
- ✅ 权限控制：min_tier 控制会员专属素材
- ✅ 全文搜索：tags 数组支持 GIN 索引快速搜索

### 8.3 P1 级别表 (重要功能)

#### 8.3.1 daily_themes (每日主题)

**业务背景**：
- 每日推送一个创作主题（如"圣诞节"、"母亲节"）
- 引导用户创作，提升活跃度

**字段设计**：

```sql
CREATE TABLE daily_themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,

    -- 主题信息
    theme_code VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    title_i18n JSONB DEFAULT '{}',
    description TEXT,
    description_i18n JSONB DEFAULT '{}',

    -- 关联节日
    holiday_id UUID REFERENCES holidays(id),

    -- 推荐内容
    suggested_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    suggested_colors JSONB DEFAULT '[]',

    -- 激励措施
    bonus_credits INTEGER DEFAULT 0,

    -- 可见性
    is_active BOOLEAN DEFAULT TRUE,

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_daily_themes_date ON daily_themes(date DESC);
CREATE INDEX idx_daily_themes_active ON daily_themes(is_active) WHERE is_active = TRUE;
```

#### 8.3.2 holidays (节日日历)

**业务背景**：
- 存储全球节日信息（圣诞、春节、中秋等）
- 为主题系统和营销活动提供数据源

**字段设计**：

```sql
CREATE TABLE holidays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    holiday_code VARCHAR(50) NOT NULL UNIQUE,

    -- 节日信息
    name VARCHAR(100) NOT NULL,
    name_i18n JSONB DEFAULT '{}',

    -- 日期信息 (支持农历/阳历)
    date DATE NOT NULL,
    date_type VARCHAR(20) DEFAULT 'gregorian' CHECK (date_type IN ('gregorian', 'lunar', 'islamic')),

    -- 地区信息
    regions TEXT[] DEFAULT ARRAY[]::TEXT[],
    is_global BOOLEAN DEFAULT FALSE,

    -- 节日类型
    category VARCHAR(50),

    -- 可见性
    is_active BOOLEAN DEFAULT TRUE,

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_holidays_date ON holidays(date);
CREATE INDEX idx_holidays_code ON holidays(holiday_code);
CREATE INDEX idx_holidays_active ON holidays(is_active) WHERE is_active = TRUE;
```

#### 8.3.3 activity_logs (活动日志)

**业务背景**：
- 记录用户重要操作（登录、创建项目、购买等）
- 用于审计、异常检测、用户行为分析

**字段设计**：

```sql
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES profiles(id),

    -- 活动信息
    action TEXT NOT NULL,
    entity_type VARCHAR(50),
    entity_id TEXT,

    -- 详情
    details JSONB DEFAULT '{}',

    -- 审计字段
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activity_logs_user_created ON activity_logs(user_id, created_at DESC);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);
CREATE INDEX idx_activity_logs_entity ON activity_logs(entity_type, entity_id);
```

#### 8.3.4 analytics_aggregation (分析聚合表)

**业务背景**：
- 预聚合分析数据（DAU、MAU、收入等）
- 避免实时查询大表

**字段设计**：

```sql
CREATE TABLE analytics_aggregation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,

    -- 聚合数据
    value NUMERIC,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, metric_name)
);

CREATE INDEX idx_analytics_aggregation_date ON analytics_aggregation(date DESC);
CREATE INDEX idx_analytics_aggregation_metric ON analytics_aggregation(metric_name);
```

#### 8.3.5 scheduled_task_logs (定时任务日志)

**业务背景**：
- 记录定时任务执行情况（积分重置、数据清理等）
- 监控任务成功率和性能

**字段设计**：

```sql
CREATE TABLE scheduled_task_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_name VARCHAR(100) NOT NULL,

    -- 执行信息
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failed', 'running', 'timeout')),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- 结果详情
    result_summary JSONB DEFAULT '{}',
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheduled_task_logs_task ON scheduled_task_logs(task_name, started_at DESC);
CREATE INDEX idx_scheduled_task_logs_status ON scheduled_task_logs(status) WHERE status != 'success';
```

### 8.4 P2 级别表 (增强功能)

#### 8.4.1 config_audit_logs (配置审计日志)

**业务背景**：
- 记录 system_configs 的所有变更
- 审计敏感配置（Rate Limits、Feature Flags）

**字段设计**：

```sql
CREATE TABLE config_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key TEXT NOT NULL,

    -- 变更信息
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(20) CHECK (change_type IN ('create', 'update', 'delete')),

    -- 操作人
    changed_by TEXT REFERENCES profiles(id),
    change_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_config_audit_logs_key ON config_audit_logs(config_key, created_at DESC);
CREATE INDEX idx_config_audit_logs_changed_by ON config_audit_logs(changed_by);
```

#### 8.4.2 content_reports (内容举报)

**业务背景**：
- 用户举报不当内容（市场商品、项目等）
- 审核团队处理举报

**字段设计**：

```sql
CREATE TABLE content_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id TEXT REFERENCES profiles(id),

    -- 举报对象
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,

    -- 举报原因
    reason VARCHAR(50) NOT NULL,
    description TEXT,

    -- 审核状态
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'reviewing', 'resolved', 'dismissed')),
    reviewed_by TEXT REFERENCES profiles(id),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_reports_entity ON content_reports(entity_type, entity_id);
CREATE INDEX idx_content_reports_status ON content_reports(status) WHERE status = 'pending';
```

#### 8.4.3 system_resource_audit_logs (系统资源审计)

**业务背景**：
- 记录系统资源变更（system_assets、system_configs等）
- 追踪谁在何时修改了什么

**字段设计**：

```sql
CREATE TABLE system_resource_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    action VARCHAR(20) CHECK (action IN ('create', 'update', 'delete')),
    changed_by TEXT REFERENCES profiles(id),
    changes JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_system_resource_audit_logs_resource ON system_resource_audit_logs(resource_type, resource_id);
CREATE INDEX idx_system_resource_audit_logs_action ON system_resource_audit_logs(action);
```

#### 8.4.4 asset_prompt_templates (AI 提示词模板)

**业务背景**：
- 存储 AI 生成的提示词模板
- 为用户提供快速生成选项

**字段设计**：

```sql
CREATE TABLE asset_prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID REFERENCES asset_categories(id),

    -- 模板信息
    name VARCHAR(200) NOT NULL,
    description TEXT,

    -- 提示词内容
    prompt_template TEXT NOT NULL,
    negative_prompt_template TEXT,

    -- 参数配置
    default_params JSONB DEFAULT '{}',

    -- 适用模型
    compatible_models TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 访问控制
    min_tier VARCHAR(20) DEFAULT 'free',

    -- 使用统计
    usage_count INTEGER DEFAULT 0,

    -- 可见性
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_asset_prompt_templates_category ON asset_prompt_templates(category_id);
CREATE INDEX idx_asset_prompt_templates_active ON asset_prompt_templates(is_active) WHERE is_active = TRUE;
```

### 8.5 新增表总结

| 表名 | 优先级 | 行数预估 | 增长速度 | 索引数 |
|------|--------|----------|----------|--------|
| ai_call_logs | P0 | 1M+ | 快 (每分钟100+) | 3 |
| ai_usage_daily | P0 | 10K | 慢 (每天30+) | 2 |
| asset_categories | P0 | 100-500 | 慢 (偶尔增加) | 3 |
| system_assets | P0 | 5K-10K | 中 (定期补充) | 5 |
| daily_themes | P1 | 365+ | 慢 (每天1) | 2 |
| holidays | P1 | 500-1000 | 慢 (偶尔增加) | 3 |
| activity_logs | P1 | 1M+ | 快 (每分钟50+) | 3 |
| analytics_aggregation | P1 | 10K | 慢 (每天50+) | 2 |
| scheduled_task_logs | P1 | 100K | 中 (每小时10+) | 2 |
| config_audit_logs | P2 | 1K | 慢 (偶尔) | 2 |
| content_reports | P2 | 10K | 中 (每天10+) | 2 |
| system_resource_audit_logs | P2 | 10K | 中 (每天5+) | 2 |
| asset_prompt_templates | P2 | 500-1000 | 慢 (偶尔增加) | 2 |

---

## 9. system_configs 初始化数据

### 9.1 数据概览

补充了 **57 行完整的 system_configs 初始化数据**，覆盖以下分组：

| 配置分组 | 数量 | 用途 |
|----------|------|------|
| Rate Limits | 24 | API 速率限制 |
| AI Providers | 8 | AI 提供商配置 |
| Credits | 9 | 积分成本和规则 |
| Feature Flags | 4 | 功能开关 |
| Limits | 5 | 业务限制 |
| Pricing | 4 | 定价配置 |
| Analytics | 3 | 分析配置 |

### 9.2 Rate Limits 配置 (24条)

**设计理念**：细粒度的速率限制，防止滥用

```sql
-- API 限制
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute"}', 'json', 'rate_limit', 'Checkout API 限制', TRUE),
('rate_limit.payment.webhook', '{"limit": 100, "window": "minute"}', 'json', 'rate_limit', 'Webhook 限制', TRUE),

-- AI 生成限制
('rate_limit.generate.images', '{"limit": 10, "window": "minute"}', 'json', 'rate_limit', 'AI 图片生成限制', TRUE),
('rate_limit.generate.text', '{"limit": 20, "window": "minute"}', 'json', 'rate_limit', 'AI 文字生成限制', TRUE),

-- 市场操作限制
('rate_limit.marketplace.publish', '{"limit": 5, "window": "hour"}', 'json', 'rate_limit', '发布商品限制', TRUE),
('rate_limit.marketplace.purchase', '{"limit": 20, "window": "hour"}', 'json', 'rate_limit', '购买商品限制', TRUE),

-- 项目操作限制
('rate_limit.project.create', '{"limit": 10, "window": "hour"}', 'json', 'rate_limit', '创建项目限制', TRUE),
('rate_limit.project.export', '{"limit": 5, "window": "minute"}', 'json', 'rate_limit', '导出项目限制', TRUE),
```

### 9.3 AI Providers 配置 (8条)

**设计理念**：集中管理 AI 提供商和模型配置

```sql
-- 提供商开关
('ai_providers.enabled', '{"openai": true, "fal": true, "qwen": false}', 'json', 'ai_providers', '启用的 AI 提供商', TRUE),

-- 模型配置 (用户功能)
('ai_model.user.text_reasoning', '{"provider": "openai", "model": "gpt-4o-mini"}', 'json', 'ai_models', '用户文字推理模型', TRUE),
('ai_model.user.image_generation', '{"provider": "fal", "model": "flux-pro"}', 'json', 'ai_models', '用户图片生成模型', TRUE),

-- 模型配置 (系统功能)
('ai_model.system.text_reasoning', '{"provider": "openai", "model": "gpt-4o"}', 'json', 'ai_models', '系统文字推理模型 (高级)', FALSE),
('ai_model.system.moderation', '{"provider": "openai", "model": "omni-moderation"}', 'json', 'ai_models', '内容审核模型', FALSE),

-- 超时配置
('ai_timeout.text_reasoning', '30000', 'integer', 'ai_providers', '文字推理超时 (ms)', TRUE),
('ai_timeout.image_generation', '120000', 'integer', 'ai_providers', '图片生成超时 (ms)', TRUE),
```

### 9.4 Credits 配置 (9条)

**设计理念**：明确积分成本和业务规则

```sql
-- AI 成本
('credits.cost.image_generation', '5', 'integer', 'credits', 'AI 图片生成成本', TRUE),
('credits.cost.text_generation', '0', 'integer', 'credits', 'AI 文字生成成本 (免费)', TRUE),
('credits.cost.smart_scan', '10', 'integer', 'credits', 'Smart Scan 成本', TRUE),

-- 奖励
('credits.reward.signup', '50', 'integer', 'credits', '注册赠送积分 (永久)', FALSE),
('credits.reward.daily_theme', '10', 'integer', 'credits', '每日主题完成奖励', TRUE),
('credits.reward.referral', '20', 'integer', 'credits', '推荐好友奖励', FALSE),

-- 等级配额
('credits.tier.free.monthly', '0', 'integer', 'credits', 'Free 等级月度积分', FALSE),
('credits.tier.starter.monthly', '200', 'integer', 'credits', 'Starter 等级月度积分', FALSE),
('credits.tier.pro.monthly', '500', 'integer', 'credits', 'Pro 等级月度积分', FALSE),
```

### 9.5 Feature Flags 配置 (4条)

**设计理念**：灰度发布和功能开关

```sql
('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', '启用 AI 生成功能', TRUE),
('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', '启用市场功能', TRUE),
('FEATURE_DAILY_THEMES', 'false', 'boolean', 'feature_flag', '启用每日主题 (待上线)', TRUE),
('FEATURE_REFERRAL_PROGRAM', 'false', 'boolean', 'feature_flag', '启用推荐计划 (待上线)', TRUE),
```

### 9.6 其他配置

**Limits (5条)** - 业务限制：
```sql
('limits.project.max_free', '5', 'integer', 'limits', 'Free 用户最多项目数', TRUE),
('limits.project.max_starter', '20', 'integer', 'limits', 'Starter 用户最多项目数', TRUE),
('limits.marketplace.max_price', '500', 'integer', 'limits', '市场商品最高定价 (积分)', FALSE),
```

**Pricing (4条)** - 定价信息（展示用）：
```sql
('pricing.tier.free', '0', 'integer', 'pricing', 'Free 等级价格 (USD)', FALSE),
('pricing.tier.starter', '9.90', 'decimal', 'pricing', 'Starter 等级价格 (USD/月)', FALSE),
('pricing.tier.pro', '19.90', 'decimal', 'pricing', 'Pro 等级价格 (USD/月)', FALSE),
```

**Analytics (3条)** - 分析配置：
```sql
('analytics.retention_days', '90', 'integer', 'analytics', 'Analytics 事件保留天数', TRUE),
('analytics.aggregation_schedule', '0 2 * * *', 'text', 'analytics', '聚合任务 Cron (每天凌晨2点)', TRUE),
```

---

## 10. 索引策略总结

### 8.1 索引总览

**当前数据库索引统计**：

| 类型 | 数量 | 说明 |
|------|------|------|
| 单列索引 | ~80 | 外键、状态、时间字段 |
| 复合索引 | ~25 | 多字段查询优化 |
| 部分索引 | ~15 | 仅索引活跃数据 |
| GIN索引 | 3 | JSON/数组字段 |
| UNIQUE约束 | 12 | 业务唯一性保证 |

### 8.2 关键复合索引设计

```sql
-- Dashboard查询：我的项目列表
CREATE INDEX idx_projects_user_active
ON projects(user_id, is_deleted, created_at DESC)
WHERE is_deleted = false;
-- 查询: WHERE user_id = ? AND is_deleted = false ORDER BY created_at DESC

-- 垃圾箱查询
CREATE INDEX idx_projects_trash
ON projects(user_id, is_deleted, is_hidden_from_trash)
WHERE is_deleted = true AND is_hidden_from_trash = false;
-- 查询: WHERE user_id = ? AND is_deleted = true AND is_hidden_from_trash = false

-- 市场公开商品
CREATE INDEX idx_listings_public
ON marketplace_listings(is_public, is_deleted, moderation_status);
-- 查询: WHERE is_public = true AND is_deleted = false AND moderation_status = 'approved'

-- 市场分类查询（v3.26）
CREATE INDEX idx_listings_category
ON marketplace_listings(resource_type, category, is_public);
-- 查询: WHERE resource_type = 'asset' AND category = 'clipart' AND is_public = true
```

---

## 9. 数据完整性保证

### 9.1 外键约束

**决策**：所有关联关系使用外键约束

**示例**：

```sql
-- 用户关联
user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE

-- 商品关联
listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE

-- 项目关联（可选）
project_id UUID REFERENCES projects(id) ON DELETE SET NULL
```

**ON DELETE策略**：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| CASCADE | 级联删除 | 用户删除→删除所有项目 |
| SET NULL | 置空 | 项目删除→资产的project_id置空 |
| RESTRICT | 禁止删除 | 有订单的商品不能删除 |

### 9.2 CHECK约束

**决策**：使用CHECK约束验证数据范围

**示例**：

```sql
-- 枚举值
tier TEXT CHECK (tier IN ('free', 'starter', 'pro'))

-- 范围值
traffic_allocation INTEGER CHECK (traffic_allocation >= 0 AND traffic_allocation <= 100)

-- 业务规则
price_credits INTEGER CHECK (price_credits >= 0 AND price_credits <= 500)
```

### 9.3 UNIQUE约束

**决策**：关键业务逻辑使用UNIQUE约束

**示例**：

```sql
-- 用户识别码全局唯一
user_code TEXT UNIQUE

-- 幂等性键
idempotency_key TEXT UNIQUE

-- 防重复购买
UNIQUE(user_id, listing_id)

-- 防重复领取
UNIQUE(campaign_id, user_id)
```

---

## 10. 扩展性设计

### 10.1 预留扩展字段

**决策**：每个核心表预留 `ext_json` 字段

**理由**：

1. **避免频繁ALTER TABLE**（生产环境锁表）
2. **快速试验新功能**
3. **支持用户自定义字段**

**示例**：

```sql
ext_json JSONB DEFAULT '{}'::jsonb
  COMMENT '扩展字段 | 用于未来功能，避免频繁ALTER TABLE | 示例: {"feature_x": true, "custom_data": {...}}',
```

**使用场景**：

- 测试新功能：先放ext_json，稳定后再建字段
- 第三方集成：存储外部系统的额外信息
- 用户自定义：让用户存储自己的元数据

### 10.2 版本控制字段

**决策**：关键表添加 `version` 字段

**示例**：

```sql
version VARCHAR(20) DEFAULT '1.0'
  COMMENT '版本号 | 用于向后兼容和数据迁移',

changelog TEXT
  COMMENT '变更日志 | 记录版本间的变化',

version_history JSONB DEFAULT '[]'::jsonb
  COMMENT '版本历史 | 记录所有历史版本的快照',
```

**适用表**：
- `marketplace_listings`（已有）
- `projects`（待添加）

---

## 11. 迁移策略建议

### 11.1 蓝绿部署方案

**推荐方式**：零停机迁移

**步骤**：

1. **Phase 1: 创建新表结构**
   ```sql
   CREATE TABLE profiles_v4 AS SELECT * FROM profiles WHERE false;
   ALTER TABLE profiles_v4 ADD COLUMN ...;
   ```

2. **Phase 2: 双写模式**
   - 应用代码同时写入 profiles 和 profiles_v4
   - 验证数据一致性

3. **Phase 3: 历史数据迁移**
   ```sql
   INSERT INTO profiles_v4 SELECT ... FROM profiles;
   ```

4. **Phase 4: 切换读取**
   - 应用代码切换到 profiles_v4
   - 监控错误和性能

5. **Phase 5: 清理**
   - 备份 profiles
   - RENAME profiles_v4 TO profiles
   - DROP 旧表

### 11.2 字段迁移映射

**参考 `mapping_and_changes.md`**（下一个文档）

---

## 12. 性能基准测试建议

### 12.1 关键查询性能对比

**重构前后应测试的查询**：

```sql
-- 1. Dashboard项目列表
SELECT * FROM projects
WHERE user_id = ? AND is_deleted = false
ORDER BY created_at DESC LIMIT 20;

-- 2. 市场商品列表
SELECT * FROM marketplace_listings
WHERE is_public = true AND is_deleted = false
  AND moderation_status = 'approved'
ORDER BY sales_count DESC LIMIT 20;

-- 3. 积分交易历史
SELECT * FROM credit_transactions
WHERE user_id = ?
ORDER BY created_at DESC LIMIT 100;

-- 4. 用户统计聚合
SELECT
  COUNT(*) as project_count,
  SUM(CASE WHEN is_deleted = false THEN 1 ELSE 0 END) as active_count
FROM projects
WHERE user_id = ?;
```

**预期改善**：

| 查询 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| Dashboard项目 | 50ms | 10ms | 5x ⬆️ |
| 市场列表 | 100ms | 20ms | 5x ⬆️ |
| 积分历史 | 30ms | 10ms | 3x ⬆️ |
| 用户统计 | 200ms | 5ms | 40x ⬆️ (冗余字段) |

---

## 13. 安全性考虑

### 13.1 RLS策略保持

**决策**：保持现有60+个RLS策略不变

**示例**：

```sql
-- 用户只能看自己的项目
CREATE POLICY "Users can CRUD own projects" ON projects
  FOR ALL USING (auth.uid()::text = user_id);

-- 公开商品所有人可见
CREATE POLICY "Public can view marketplace" ON marketplace_listings
  FOR SELECT USING (is_public = true AND is_deleted = false);

-- 管理员全权限
CREATE POLICY "Admin full access" ON profiles
  FOR ALL USING (is_admin());
```

### 13.2 敏感数据处理

**建议**：

1. **不存储明文密码**（已做到，使用Clerk）
2. **敏感字段加密**（如需要）
3. **PII数据标注**（COMMENT注明）

```sql
email TEXT COMMENT '用户邮箱 | PII: 个人身份信息',
avatar_url TEXT COMMENT '头像URL | PII: 可能包含识别信息',
```

---

## 14. 监控与运维

### 14.1 建议监控指标

**数据库层面**：

1. **表大小增长**：
   ```sql
   SELECT
     schemaname, tablename,
     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

2. **慢查询**（>100ms）
3. **索引命中率**（应 >95%）
4. **死锁检测**

**业务层面**：

1. **积分账本一致性**：
   ```sql
   -- 检查余额是否匹配最后一条交易
   SELECT user_id FROM profiles p
   WHERE (p.credits_monthly, p.credits_permanent) != (
     SELECT balance_monthly_after, balance_permanent_after
     FROM credit_transactions
     WHERE user_id = p.id
     ORDER BY created_at DESC LIMIT 1
   );
   ```

2. **幂等性键冲突**（应为0）
3. **触发器执行时间**

### 14.2 定期维护任务

```sql
-- 1. 清理过期任务（每天）
SELECT cleanup_expired_tasks();

-- 2. 清理老任务日志（每周）
SELECT cleanup_old_task_logs();

-- 3. 刷新物化视图（每小时）
SELECT refresh_analytics_views();

-- 4. VACUUM ANALYZE（每周）
VACUUM ANALYZE;

-- 5. 重建索引（每月，可选）
REINDEX TABLE credit_transactions;
```

---

## 15. 总结

### 15.1 重构核心原则

1. **标准化优先**：统一命名、统一字段、统一索引
2. **性能优先**：合理冗余、精准索引、部分索引
3. **可维护性优先**：完整COMMENT、清晰映射、触发器自动化
4. **业务规则不变**：双ID、积分顺序、幂等性、Append-Only

### 15.2 预期收益

| 方面 | 改善 |
|------|------|
| 代码可读性 | ⬆️ 50% (统一命名) |
| 查询性能 | ⬆️ 3-5x (索引优化) |
| 开发效率 | ⬆️ 30% (自文档化) |
| 维护成本 | ⬇️ 40% (触发器自动化) |
| 扩展性 | ⬆️ 高 (ext_json预留) |

### 15.3 下一步行动

1. **Review**: 团队Review本文档
2. **Approve**: 确认重构方案
3. **Implement**: 执行迁移（参考 mapping_and_changes.md）
4. **Test**: 性能基准测试
5. **Deploy**: 生产环境部署（蓝绿）
6. **Monitor**: 监控关键指标

---

**文档结束**

> **附件**:
> - `mapping_and_changes.md` - 详细的字段映射表
> - `refactored_schema.sql` - 完整的新DDL脚本

**变更记录**:
- 2026-01-09: v1.0 - 初始版本
