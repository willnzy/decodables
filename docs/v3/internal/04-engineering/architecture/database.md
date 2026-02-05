# 数据库设计

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `migrations/v2/*.sql`

---

## 一、概述

### 1.1 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| 数据库 | PostgreSQL 15+ | 托管于 Supabase |
| 扩展 | ltree, pg_trgm | 层级树 + 模糊搜索 |
| UUID | gen_random_uuid() | PostgreSQL 14+ 内置 |

### 1.2 Schema 文件结构

```
migrations/v2/
├── 01_core_business.sql      # 核心业务表 (4067 行)
├── 02_platform_services.sql  # 平台服务表 (1735 行)
├── 03_infrastructure.sql     # 基础设施表 (2223 行)
└── README.md                 # Schema 说明
```

**执行顺序**: 01 → 02 → 03 (按依赖关系)

---

## 二、核心业务表 (01_core_business.sql)

### 2.1 用户相关

| 表名 | 说明 | 行数估计 |
|------|------|----------|
| `profiles` | 用户信息 + 积分 + 订阅状态 | 核心表 |
| `auth_users` | 认证凭据 (密码哈希) | 与 profiles 1:1 |
| `sessions` | 用户会话 | 每用户多条 |
| `otp_codes` | OTP 验证码 | 临时数据 |

**profiles 核心字段**:

```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    user_code TEXT UNIQUE NOT NULL,  -- 26位用户码
    
    -- 用户等级
    tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3', 't4')),
    
    -- 积分余额 (核心!)
    credits_monthly INTEGER NOT NULL DEFAULT 0,    -- 月度积分
    credits_permanent INTEGER NOT NULL DEFAULT 0,  -- 永久积分
    
    -- Stripe 订阅
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT,
    subscription_status TEXT,
    
    -- 审计字段
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT FALSE
);
```

### 2.2 项目相关

| 表名 | 说明 |
|------|------|
| `projects` | 用户项目 |
| `folders` | 文件夹系统 |
| `workspaces` | 工作空间 |

**projects 核心字段**:

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(id),
    workspace_id UUID REFERENCES workspaces(id),
    folder_id UUID REFERENCES folders(id),
    
    name TEXT NOT NULL,
    thumbnail_url TEXT,
    canvas_data JSONB,  -- Fabric.js 画布数据
    
    is_starred BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### 2.3 素材市场

| 表名 | 说明 |
|------|------|
| `marketplace_listings` | 素材上架记录 |
| `assets` | 用户素材 |
| `asset_categories` | 素材分类 (10 类) |
| `tags` | 用户标签 |

### 2.4 积分相关

| 表名 | 说明 |
|------|------|
| `credit_transactions` | 积分流水 |
| `credit_packages` | 积分充值包 |

---

## 三、平台服务表 (02_platform_services.sql)

### 3.1 Feature Flag

| 表名 | 说明 |
|------|------|
| `feature_flags` | 功能开关定义 |
| `flag_exposures` | Flag 曝光记录 |
| `flag_audit_logs` | Flag 变更审计 |

### 3.2 实验系统

| 表名 | 说明 |
|------|------|
| `experiments` | A/B 实验定义 |
| `experiment_configs` | 实验配置 |
| `experiment_assignments` | 用户分组 |
| `experiment_exposures` | 曝光记录 |
| `experiment_conversions` | 转化记录 |

### 3.3 分析追踪

| 表名 | 说明 |
|------|------|
| `analytics_events` | 事件追踪 |
| `user_events` | 用户行为事件 |
| `activity_logs` | 活动日志 |
| `aggregated_stats` | 聚合统计 |
| `daily_metrics` | 日指标 |
| `monthly_metrics` | 月指标 |

### 3.4 营销活动

| 表名 | 说明 |
|------|------|
| `campaigns` | 营销活动 |
| `campaign_participations` | 参与记录 |
| `daily_themes` | 每日主题 |
| `referrals` | 推荐记录 |

### 3.5 通知系统

| 表名 | 说明 |
|------|------|
| `notifications` | 用户通知 |
| `notification_templates` | 通知模板 |

### 3.6 Webhook

| 表名 | 说明 |
|------|------|
| `stripe_webhook_events` | Stripe Webhook 记录 |
| `clerk_webhook_events` | (已废弃) |

---

## 四、基础设施表 (03_infrastructure.sql)

### 4.1 系统配置

| 表名 | 说明 |
|------|------|
| `system_configs` | 系统配置 (Tier 权益、价格等) |
| `pricing_plans` | 定价方案 |
| `pricing_history` | 价格变更历史 |

### 4.2 日志系统

| 表名 | 说明 |
|------|------|
| `api_logs` | API 调用日志 |
| `error_logs` | 错误日志 |
| `ai_call_logs` | AI 调用日志 |
| `admin_operations` | 管理员操作日志 |
| `scheduled_task_logs` | 定时任务日志 |

### 4.3 支付记录

| 表名 | 说明 |
|------|------|
| `payment_records` | 支付记录 |

### 4.4 客服支持

| 表名 | 说明 |
|------|------|
| `support_tickets` | 工单 |
| `support_replies` | 工单回复 |

---

## 五、核心约束

### 5.1 Tier 约束

```sql
tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3', 't4'))
```

| 代码 | 简称 | 显示名称 |
|------|------|----------|
| t1 | First Tier | Free Plan |
| t2 | Second Tier | Starter Plan |
| t3 | Third Tier | Pro Plan |
| t4 | Fourth Tier | (预留) |

### 5.2 积分约束

```sql
credits_monthly INTEGER NOT NULL DEFAULT 0 
    CHECK (credits_monthly >= 0 AND credits_monthly <= 1000000),
credits_permanent INTEGER NOT NULL DEFAULT 0 
    CHECK (credits_permanent >= 0 AND credits_permanent <= 10000000),
```

### 5.3 Stripe ID 格式

```sql
CONSTRAINT check_stripe_customer_id_format 
    CHECK (stripe_customer_id IS NULL OR stripe_customer_id ~ '^cus_[A-Za-z0-9]+$'),
CONSTRAINT check_stripe_subscription_id_format 
    CHECK (stripe_subscription_id IS NULL OR stripe_subscription_id ~ '^sub_[A-Za-z0-9]+$'),
```

### 5.4 user_code 格式

```sql
-- 26位数字: YYMMDDHHMMSS + mmmm + UUUUUUU + RRR
CONSTRAINT check_user_code_format CHECK (user_code ~ '^[0-9]{26}$')
```

---

## 六、索引策略

### 6.1 常用索引模式

```sql
-- 主键索引 (自动)
PRIMARY KEY (id)

-- 唯一索引
CREATE UNIQUE INDEX idx_profiles_email_unique 
    ON profiles(LOWER(email)) WHERE is_deleted = FALSE;

-- 外键索引
CREATE INDEX idx_projects_user_id ON projects(user_id);

-- 复合索引
CREATE INDEX idx_projects_user_folder 
    ON projects(user_id, folder_id) WHERE is_deleted = FALSE;

-- 部分索引
CREATE INDEX idx_profiles_active 
    ON profiles(created_at DESC) WHERE is_deleted = FALSE;

-- GIN 索引 (JSONB)
CREATE INDEX idx_projects_canvas_data ON projects USING GIN (canvas_data);

-- Trigram 索引 (模糊搜索)
CREATE INDEX idx_profiles_username_trgm 
    ON profiles USING GIN (username gin_trgm_ops);
```

### 6.2 索引命名规范

```
idx_{table}_{column}           -- 单列索引
idx_{table}_{col1}_{col2}      -- 复合索引
idx_{table}_{column}_unique    -- 唯一索引
idx_{table}_{column}_partial   -- 部分索引
```

---

## 七、RPC 函数

### 7.1 用户相关

| 函数 | 用途 |
|------|------|
| `get_user_with_credits(user_id)` | 获取用户信息 + 积分 |
| `deduct_credits(user_id, amount)` | 原子扣除积分 |
| `add_credits(user_id, amount, type)` | 原子增加积分 |

### 7.2 项目相关

| 函数 | 用途 |
|------|------|
| `list_projects_with_stats(user_id)` | 项目列表 + 统计 |
| `move_projects_to_folder(project_ids, folder_id)` | 批量移动项目 |

### 7.3 素材市场

| 函数 | 用途 |
|------|------|
| `search_marketplace(query, filters)` | 全文搜索 |
| `get_listing_with_assets(listing_id)` | 上架详情 + 素材 |

---

## 八、迁移管理

### 8.1 原则

1. **直接修改主 Schema**: 不创建增量迁移脚本
2. **版本控制**: Git 管理 Schema 变更
3. **回滚策略**: 数据库备份 + Git 回滚

### 8.2 修改流程

```bash
# 1. 直接编辑 Schema 文件
vim migrations/v2/01_core_business.sql

# 2. 本地验证
psql -f migrations/v2/01_core_business.sql

# 3. 提交
git add migrations/v2/
git commit -m "db: 添加 xxx 字段"

# 4. 应用到生产
# (通过 Supabase Dashboard 或 CI/CD)
```

### 8.3 Seed 数据

```
migrations/seed/
├── articles_help_seed.sql     # 帮助文档
├── articles_news_seed.sql     # 新闻文章
├── platform_config_seed.sql   # 平台配置
└── static_pages_seed.sql      # 静态页面
```

---

## 九、ER 图 (核心表)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   profiles   │     │   projects   │     │    assets    │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id (PK)      │──┐  │ id (PK)      │──┐  │ id (PK)      │
│ email        │  │  │ user_id (FK) │◄─┘  │ user_id (FK) │◄─┐
│ user_code    │  └─▶│ workspace_id │     │ project_id   │◄─┼─┐
│ tier         │     │ folder_id    │     │ category_id  │  │ │
│ credits_*    │     │ name         │     │ url          │  │ │
│ stripe_*     │     │ canvas_data  │     │ metadata     │  │ │
└──────────────┘     └──────────────┘     └──────────────┘  │ │
       │                    │                    │          │ │
       │                    │                    │          │ │
       ▼                    ▼                    ▼          │ │
┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │ │
│  auth_users  │     │   folders    │     │ asset_cate.. │  │ │
├──────────────┤     ├──────────────┤     ├──────────────┤  │ │
│ id (PK/FK)   │     │ id (PK)      │     │ id (PK)      │  │ │
│ email        │     │ user_id (FK) │◄────│ path (ltree) │  │ │
│ password_hash│     │ name         │     │ name         │  │ │
└──────────────┘     │ color        │     └──────────────┘  │ │
                     └──────────────┘                       │ │
                                                            │ │
┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │ │
│ marketplace_ │     │ credit_      │     │ workspaces   │  │ │
│ listings     │     │ transactions │     ├──────────────┤  │ │
├──────────────┤     ├──────────────┤     │ id (PK)      │◄─┘ │
│ id (PK)      │     │ id (PK)      │     │ user_id (FK) │◄───┘
│ user_id (FK) │◄────│ user_id (FK) │     │ name         │
│ title        │     │ amount       │     └──────────────┘
│ price        │     │ type         │
└──────────────┘     └──────────────┘
```

---

## 十、相关文档

- [架构总览](./overview.md)
- [后端架构](./backend.md)
- [Tier 系统](../../05-business/tier-system/)
- [积分系统](../../05-business/credits-system/)

---

**END OF DOCUMENT**
