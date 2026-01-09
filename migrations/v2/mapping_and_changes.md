# 数据库字段映射表

> **项目**: Make Decodables (MagicZine AI)
> **版本**: v3.24 → v4.0 (Refactored)
> **日期**: 2026-01-09
> **说明**: 本文档记录了数据库重构中所有表和字段的变更，用于代码迁移和全局替换

---

## 目录

- [1. 核心业务表](#1-核心业务表)
  - [1.1 profiles (用户档案)](#11-profiles-用户档案)
  - [1.2 user_discounts (用户折扣)](#12-user_discounts-用户折扣)
  - [1.3 credit_transactions (积分交易)](#13-credit_transactions-积分交易)
- [2. 项目与素材表](#2-项目与素材表)
  - [2.1 projects (项目)](#21-projects-项目)
  - [2.2 assets (素材)](#22-assets-素材)
- [3. 市场系统表](#3-市场系统表)
  - [3.1 marketplace_listings (市场商品)](#31-marketplace_listings-市场商品)
  - [3.2 user_purchases (用户购买)](#32-user_purchases-用户购买)
  - [3.3 listing_usages (商品使用)](#33-listing_usages-商品使用)
- [4. 系统配置表](#4-系统配置表)
  - [4.1 system_configs (系统配置)](#41-system_configs-系统配置)
  - [4.2 config_audit_logs (配置审计)](#42-config_audit_logs-配置审计)
  - [4.3 system_resources (系统资源)](#43-system_resources-系统资源)
  - [4.4 system_resource_audit_logs (资源审计)](#44-system_resource_audit_logs-资源审计)
- [5. 通知与日志表](#5-通知与日志表)
  - [5.1 notifications (通知)](#51-notifications-通知)
  - [5.2 activity_logs (活动日志)](#52-activity_logs-活动日志)
  - [5.3 admin_operation_logs (管理员操作)](#53-admin_operation_logs-管理员操作)
  - [5.4 error_logs (错误日志)](#54-error_logs-错误日志)
- [6. 分析系统表](#6-分析系统表)
  - [6.1 user_events (用户事件)](#61-user_events-用户事件)
  - [6.2 analytics_events (分析事件)](#62-analytics_events-分析事件)
  - [6.3 aggregated_stats (聚合统计)](#63-aggregated_stats-聚合统计)
  - [6.4 analytics_daily_metrics (日度指标)](#64-analytics_daily_metrics-日度指标)
  - [6.5 analytics_monthly_metrics (月度指标)](#65-analytics_monthly_metrics-月度指标)
  - [6.6 analytics_user_cohorts (用户群组)](#66-analytics_user_cohorts-用户群组)
  - [6.7 analytics_cohort_retention (群组留存)](#67-analytics_cohort_retention-群组留存)
  - [6.8 analytics_error_summary (错误汇总)](#68-analytics_error_summary-错误汇总)
  - [6.9 analytics_funnel_metrics (漏斗指标)](#69-analytics_funnel_metrics-漏斗指标)
- [7. AI与生成表](#7-ai与生成表)
  - [7.1 asset_prompt_templates (素材模板)](#71-asset_prompt_templates-素材模板)
  - [7.2 page_prompt_templates (页面模板)](#72-page_prompt_templates-页面模板)
  - [7.3 user_generations (生成历史)](#73-user_generations-生成历史)
  - [7.4 generation_tasks (生成任务)](#74-generation_tasks-生成任务)
  - [7.5 ai_usage_daily (AI使用统计)](#75-ai_usage_daily-ai使用统计)
- [8. 营销与活动表](#8-营销与活动表)
  - [8.1 holiday_themes (节日主题)](#81-holiday_themes-节日主题)
  - [8.2 campaigns (营销活动)](#82-campaigns-营销活动)
  - [8.3 campaign_claims (活动领取)](#83-campaign_claims-活动领取)
  - [8.4 campaign_dismissals (活动关闭)](#84-campaign_dismissals-活动关闭)
- [9. 实验系统表](#9-实验系统表)
  - [9.1 experiments (实验配置)](#91-experiments-实验配置)
  - [9.2 experiment_assignments (实验分配)](#92-experiment_assignments-实验分配)
  - [9.3 experiment_results (实验结果)](#93-experiment_results-实验结果)
- [10. 其他支持表](#10-其他支持表)
  - [10.1 support_tickets (支持工单)](#101-support_tickets-支持工单)
  - [10.2 content_reports (内容举报)](#102-content_reports-内容举报)
  - [10.3 leaderboard_snapshots (排行榜)](#103-leaderboard_snapshots-排行榜)
  - [10.4 scheduled_task_logs (定时任务日志)](#104-scheduled_task_logs-定时任务日志)
  - [10.5 webhook_events (Webhook事件)](#105-webhook_events-webhook事件)
- [11. 变更汇总](#11-变更汇总)
- [12. 冗余字段说明](#12-冗余字段说明)

---

## 图例说明

| 改动类型 | 符号 | 说明 |
|---------|------|------|
| 保持不变 | - | 字段名和类型都不变 |
| 重命名 | 🔄 | 字段名变更，类型不变 |
| 类型变更 | 🔧 | 类型改变 |
| 新增 | ✨ | 新增的字段 |
| 删除 | ❌ | 删除的字段 |

---

## 1. 核心业务表

### 1.1 profiles (用户档案)

**表名变更**: 无（保持 `profiles`）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | TEXT PRIMARY KEY | - | Clerk ID，格式: user_2xxx... |
| email | email | TEXT | - | 用户邮箱 |
| username | username | TEXT | - | 用户名 |
| first_name | first_name | TEXT | - | 名 |
| last_name | last_name | TEXT | - | 姓 |
| avatar_url | avatar_url | TEXT | - | 头像URL |
| user_code | user_code | TEXT UNIQUE | - | 用户识别码（包含注册时间） |
| credits_monthly | credits_monthly | INTEGER | - | 月度积分 |
| credits_permanent | credits_permanent | INTEGER | - | 永久积分 |
| tier | tier | TEXT | - | 用户等级: free/starter/pro |
| subscription_status | subscription_status | TEXT | - | 订阅状态 |
| subscription_valid_until | subscription_valid_until | TIMESTAMPTZ | - | 订阅有效期 |
| monthly_credits_cycle_anchor | monthly_credits_cycle_anchor | TIMESTAMPTZ | - | 月度积分重置锚点 |
| stripe_customer_id | stripe_customer_id | TEXT | - | Stripe客户ID |
| role | role | TEXT | - | 角色: user/admin |
| cohort_month | cohort_month | TEXT | - | 注册月份群组 |
| timezone | timezone | TEXT | - | 用户时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| - | updated_at | TIMESTAMPTZ | ✨ | **新增**: 更新时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |
| - | last_active_at | TIMESTAMPTZ | ✨ | **新增**: 最后活跃时间（冗余字段） |
| - | project_count | INTEGER | ✨ | **新增**: 项目数量（冗余字段） |

**重要提示**:
- ⚠️ `id` 字段是 **TEXT** 类型（Clerk ID），不是 UUID！
- ✅ 保持双ID系统：`id` (系统内部) + `user_code` (用户可见)
- ✅ 新增的冗余字段通过触发器自动维护

---

### 1.2 user_discounts (用户折扣)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| discount_percent | discount_percent | INTEGER | - | 折扣百分比 |
| valid_until | valid_until | TIMESTAMPTZ | - | 有效期 |
| target_plan | target_plan | TEXT | - | 目标计划 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| - | updated_at | TIMESTAMPTZ | ✨ | **新增**: 更新时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |
| - | is_active | BOOLEAN | ✨ | **新增**: 是否激活 |

---

### 1.3 credit_transactions (积分交易)

**表名变更**: 无（保持 `credit_transactions`）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| amount | amount | INTEGER | - | 积分变动量（正=收入，负=支出） |
| bucket | bucket | TEXT | - | 积分桶: monthly/permanent |
| balance_monthly_after | balance_monthly_after | INTEGER | - | 交易后月度余额（快照） |
| balance_permanent_after | balance_permanent_after | INTEGER | - | 交易后永久余额（快照） |
| type | type | TEXT | - | 交易类型 |
| description | description | TEXT | - | 描述 |
| idempotency_key | idempotency_key | TEXT UNIQUE | - | 幂等性键 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |

**重要提示**:
- ⚠️ **Append-Only** 表：有防UPDATE/DELETE触发器
- ✅ `idempotency_key` 保证幂等性（UNIQUE约束）
- ✅ `balance_*_after` 字段用于审计和对账
- ❌ **不添加** `updated_at` / `is_deleted`（Append-Only特性）

---

## 2. 项目与素材表

### 2.1 projects (项目)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| title | title | TEXT | - | 项目标题 |
| canvas_data | canvas_data | JSONB | - | Fabric.js画布数据 |
| thumbnail_url | thumbnail_url | TEXT | - | 缩略图URL |
| last_downloaded_hash | last_downloaded_hash | TEXT | - | 最后下载哈希 |
| is_deleted | is_deleted | BOOLEAN | - | 软删除标志 |
| deleted_at | deleted_at | TIMESTAMPTZ | - | 删除时间 |
| is_hidden_from_trash | is_hidden_from_trash | BOOLEAN | - | 从垃圾箱隐藏 |
| contains_locked_elements | contains_locked_elements | BOOLEAN | - | 包含锁定元素 |
| source_listing_id | source_listing_id | UUID | - | 来源商品ID |
| is_purchased | is_purchased | BOOLEAN | - | 是否购买而来 |
| origin_owner_id | origin_owner_id | TEXT | - | 原始拥有者ID |
| listing_status | listing_status | TEXT | - | 商品状态 |
| marketplace_listing_id | marketplace_listing_id | UUID | - | 关联的市场商品ID |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| updated_at_local | updated_at_local | TIMESTAMP | - | 更新时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间（UTC） |
| - | asset_count | INTEGER | ✨ | **新增**: 关联素材数量（冗余） |
| - | last_opened_at | TIMESTAMPTZ | ✨ | **新增**: 最后打开时间 |
| - | ext_json | JSONB | ✨ | **新增**: 扩展字段 |

**新增冗余字段说明**:
- `asset_count`: 通过触发器维护（`trigger on assets INSERT/DELETE`）
- `last_opened_at`: API更新，用于"最近打开"排序

---

### 2.2 assets (素材)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| project_id | project_id | UUID REFERENCES projects(id) | - | 项目ID（可选） |
| url | url | TEXT | - | 资源URL |
| type | type | TEXT | - | 类型: image/sticker/background等 |
| prompt | prompt | TEXT | - | 生成提示词 |
| description | description | TEXT | - | 描述 |
| metadata | metadata | JSONB | - | 元数据（尺寸、大小等） |
| is_deleted | is_deleted | BOOLEAN | - | 软删除标志 |
| deleted_at | deleted_at | TIMESTAMPTZ | - | 删除时间 |
| is_hidden_from_trash | is_hidden_from_trash | BOOLEAN | - | 从垃圾箱隐藏 |
| source_listing_id | source_listing_id | UUID | - | 来源商品ID |
| is_purchased | is_purchased | BOOLEAN | - | 是否购买而来 |
| origin_owner_id | origin_owner_id | TEXT | - | 原始拥有者ID |
| listing_status | listing_status | TEXT | - | 商品状态 |
| marketplace_listing_id | marketplace_listing_id | UUID | - | 关联的市场商品ID |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| - | updated_at | TIMESTAMPTZ | ✨ | **新增**: 更新时间 |
| - | ext_json | JSONB | ✨ | **新增**: 扩展字段 |

---

## 3. 市场系统表

### 3.1 marketplace_listings (市场商品)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| seller_id | seller_id | TEXT REFERENCES profiles(id) | - | 卖家ID |
| title | title | TEXT | - | 标题 |
| description | description | TEXT | - | 描述 |
| thumbnail_url | thumbnail_url | TEXT | - | 缩略图 |
| resource_url | resource_url | TEXT | - | 资源URL |
| resource_type | resource_type | TEXT | - | 资源类型: asset/project |
| category | category | TEXT | - | 分类（14+类别） |
| source | source | TEXT | - | 来源: system/user/ai/community (v3.26) |
| resource_id | resource_id | UUID | - | 关联的资源ID |
| price_credits | price_credits | INTEGER | - | 售价（积分） |
| allowed_tiers | allowed_tiers | TEXT[] | - | 允许访问的用户等级 |
| usage_count | usage_count | BIGINT | - | 使用次数（v3.14+） |
| sales_count | sales_count | INTEGER | - | 销售次数 |
| unique_buyers_count | unique_buyers_count | INTEGER | - | 独立买家数 |
| total_revenue | total_revenue | INTEGER | - | 总收益（积分） |
| is_public | is_public | BOOLEAN | - | 是否公开 |
| is_deleted | is_deleted | BOOLEAN | - | 软删除标志 |
| moderation_status | moderation_status | TEXT | - | 审核状态 |
| moderation_note | moderation_note | TEXT | - | 审核备注 |
| moderated_by | moderated_by | TEXT | - | 审核人 |
| moderated_at | moderated_at | TIMESTAMPTZ | - | 审核时间 |
| version | version | VARCHAR(20) | - | 版本号 |
| changelog | changelog | TEXT | - | 变更日志 |
| version_history | version_history | JSONB | - | 版本历史 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| - | updated_at | TIMESTAMPTZ | ✨ | **新增**: 更新时间 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |
| - | ext_json | JSONB | ✨ | **新增**: 扩展字段 |

**重要字段说明**:
- `category`: CHECK约束（14+枚举值）
- `source`: v3.26新增的二级分类字段
- `usage_count`: v3.14新增，通过触发器维护
- 统计字段（sales_count等）通过触发器自动更新

---

### 3.2 user_purchases (用户购买)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 买家ID |
| listing_id | listing_id | UUID REFERENCES marketplace_listings(id) | - | 商品ID |
| price_paid | price_paid | INTEGER | - | 支付价格 |
| purchased_at | purchased_at | TIMESTAMPTZ | - | 购买时间 |
| idempotency_key | idempotency_key | TEXT UNIQUE | - | 幂等性键 |
| snapshot_title | snapshot_title | TEXT | - | 快照-标题 |
| snapshot_thumbnail_url | snapshot_thumbnail_url | TEXT | - | 快照-缩略图 |
| snapshot_description | snapshot_description | TEXT | - | 快照-描述 |
| snapshot_version | snapshot_version | TEXT | - | 快照-版本 |
| snapshot_resource_type | snapshot_resource_type | TEXT | - | 快照-资源类型 |
| snapshot_resource_id | snapshot_resource_id | UUID | - | 快照-资源ID |
| utm_source | utm_source | TEXT | - | UTM来源 |
| utm_medium | utm_medium | TEXT | - | UTM媒介 |
| utm_campaign | utm_campaign | TEXT | - | UTM活动 |
| referral_context | referral_context | TEXT | - | 推荐上下文 |
| timezone | timezone | TEXT | - | 时区 |
| purchased_at_local | purchased_at_local | TIMESTAMP | - | 购买时间（本地） |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间（等同purchased_at） |
| - | ext_json | JSONB | ✨ | **新增**: 扩展字段 |

**UNIQUE约束**: `(user_id, listing_id)` - 防止重复购买

---

### 3.3 listing_usages (商品使用)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| listing_id | listing_id | UUID REFERENCES marketplace_listings(id) | - | 商品ID |
| used_by_user_id | used_by_user_id | TEXT REFERENCES profiles(id) | - | 使用者ID |
| project_id | project_id | UUID REFERENCES projects(id) | - | 项目ID |
| used_at | used_at | TIMESTAMPTZ | - | 使用时间 |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间（等同used_at） |

**UNIQUE约束**: `(listing_id, used_by_user_id, project_id)` - 去重

---

## 4. 系统配置表

### 4.1 system_configs (系统配置)

**表名变更**: 无（v3.10已重构）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| key | key | TEXT PRIMARY KEY | - | 配置键 |
| value | value | TEXT | - | 配置值 |
| value_type | value_type | TEXT | - | 值类型: text/number/boolean/json |
| config_group | config_group | TEXT | - | 配置分组 |
| description | description | TEXT | - | 描述 |
| is_active | is_active | BOOLEAN | - | 是否激活 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |
| updated_by | updated_by | TEXT | - | 更新人 |

**配置分组**:
- `rate_limit`: 限流配置
- `feature_flag`: 功能开关
- `limits`: 限额配置
- `credits`: 积分消耗
- `pricing`: 价格配置
- `ai_providers`: AI模型配置
- `ai_models`: AI模型选择
- `ui`: 界面文案
- `marketing`: 营销文案
- `tooltip`: 提示文本

---

### 4.2 config_audit_logs (配置审计)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| config_key | config_key | TEXT | - | 配置键 |
| old_value | old_value | TEXT | - | 旧值 |
| new_value | new_value | TEXT | - | 新值 |
| action | action | TEXT | - | 操作类型 |
| changed_by | changed_by | TEXT | - | 修改人 |
| changed_at | changed_at | TIMESTAMPTZ | - | 修改时间 |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间（等同changed_at） |

---

### 4.3 system_resources (系统资源)

**表名变更**: 无（v3.17已增强）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| type | type | TEXT | - | 资源类型 |
| category | category | TEXT | - | 分类 |
| url | url | TEXT | - | 资源URL |
| allowed_tiers | allowed_tiers | TEXT[] | - | 允许访问的等级 |
| name | name | TEXT | - | 名称 |
| description | description | TEXT | - | 描述 |
| thumbnail_url | thumbnail_url | TEXT | - | 缩略图 |
| tags | tags | TEXT[] | - | 标签 |
| is_active | is_active | BOOLEAN | - | 是否激活 |
| sort_order | sort_order | INTEGER | - | 排序 |
| file_size | file_size | INTEGER | - | 文件大小 |
| file_type | file_type | TEXT | - | 文件类型 |
| dimensions | dimensions | JSONB | - | 尺寸 |
| metadata | metadata | JSONB | - | 元数据 |
| created_by | created_by | TEXT | - | 创建人 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |
| updated_by | updated_by | TEXT | - | 更新人 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |

---

### 4.4 system_resource_audit_logs (资源审计)

**表名变更**: 无（v3.17新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| resource_id | resource_id | UUID | - | 资源ID |
| action | action | TEXT | - | 操作类型 |
| old_data | old_data | JSONB | - | 旧数据 |
| new_data | new_data | JSONB | - | 新数据 |
| changed_by | changed_by | TEXT | - | 修改人 |
| changed_at | changed_at | TIMESTAMPTZ | - | 修改时间 |
| ip_address | ip_address | TEXT | - | IP地址 |
| user_agent | user_agent | TEXT | - | User Agent |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间（等同changed_at） |

---

## 5. 通知与日志表

### 5.1 notifications (通知)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID（可为空，全局通知） |
| target_group | target_group | TEXT | - | 目标群组 |
| notification_type | notification_type | TEXT | - | 通知类型 |
| title | title | TEXT | - | 标题 |
| content | content | TEXT | - | 内容 |
| is_read | is_read | BOOLEAN | - | 是否已读 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| - | updated_at | TIMESTAMPTZ | ✨ | **新增**: 更新时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |
| - | read_at | TIMESTAMPTZ | ✨ | **新增**: 阅读时间 |

---

### 5.2 activity_logs (活动日志)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| action | action | TEXT | - | 操作类型 |
| metadata | metadata | JSONB | - | 元数据 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |

---

### 5.3 admin_operation_logs (管理员操作)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| admin_id | admin_id | TEXT REFERENCES profiles(id) | - | 管理员ID |
| operation_type | operation_type | TEXT | - | 操作类型 |
| target_user_id | target_user_id | TEXT REFERENCES profiles(id) | - | 目标用户ID |
| details | details | TEXT | - | 详情 |
| reason | reason | TEXT | - | 原因 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |

---

### 5.4 error_logs (错误日志)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| error_id | error_id | VARCHAR(100) | - | 错误ID |
| error_type | error_type | VARCHAR(50) | - | 错误类型（CHECK约束） |
| error_code | error_code | VARCHAR(50) | - | 错误代码 |
| message | message | TEXT | - | 错误消息 |
| status_code | status_code | INTEGER | - | HTTP状态码 |
| endpoint | endpoint | VARCHAR(500) | - | 端点 |
| method | method | VARCHAR(10) | - | HTTP方法 |
| user_id | user_id | VARCHAR(100) | - | 用户ID |
| user_code | user_code | VARCHAR(30) | - | 用户识别码 |
| session_id | session_id | VARCHAR(100) | - | 会话ID |
| page_url | page_url | TEXT | - | 页面URL |
| user_agent | user_agent | TEXT | - | User Agent |
| stack_trace | stack_trace | TEXT | - | 堆栈追踪 |
| context | context | JSONB | - | 上下文 |
| client_timestamp | client_timestamp | TIMESTAMPTZ | - | 客户端时间戳 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |

**CHECK约束**: `error_type IN ('API', 'NETWORK', 'JS_ERROR', 'UNHANDLED_REJECTION', 'REACT_ERROR', 'CORS', 'OTHER')`

---

## 6. 分析系统表

### 6.1 user_events (用户事件)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| event_type | event_type | TEXT | - | 事件类型 |
| properties | properties | JSONB | - | 事件属性 |
| session_id | session_id | TEXT | - | 会话ID |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| event_id | event_id | VARCHAR(100) | - | 事件ID（v3.19，CAPI去重） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |

---

### 6.2 analytics_events (分析事件)

**表名变更**: 无（v3.11已增强）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT | - | 用户ID |
| event_type | event_type | TEXT | - | 事件类型 |
| event_name | event_name | TEXT | - | 事件名称（v3.11） |
| event_level | event_level | TEXT | - | 事件级别（v3.11） |
| event_data | event_data | JSONB | - | 事件数据 |
| context | context | JSONB | - | 上下文（v3.11） |
| session_id | session_id | TEXT | - | 会话ID |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| event_id | event_id | VARCHAR(100) | - | 事件ID（v3.19） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |

---

### 6.3 aggregated_stats (聚合统计)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| date | date | DATE | - | 日期 |
| stat_type | stat_type | TEXT | - | 统计类型 |
| data | data | JSONB | - | 统计数据 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间 |

**UNIQUE约束**: `(date, stat_type)`

---

### 6.4 analytics_daily_metrics (日度指标)

**表名变更**: 无（v3.12新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| metric_date | metric_date | DATE UNIQUE | - | 指标日期 |
| dau | dau | INTEGER | - | 日活跃用户 |
| new_users | new_users | INTEGER | - | 新用户数 |
| returning_users | returning_users | INTEGER | - | 回归用户数 |
| total_sessions | total_sessions | INTEGER | - | 总会话数 |
| avg_session_duration_sec | avg_session_duration_sec | INTEGER | - | 平均会话时长（秒） |
| pages_per_session | pages_per_session | REAL | - | 每会话页面数 |
| ai_generations | ai_generations | INTEGER | - | AI生成次数 |
| ai_credits_used | ai_credits_used | INTEGER | - | AI消耗积分 |
| marketplace_purchases | marketplace_purchases | INTEGER | - | 市场购买次数 |
| marketplace_revenue | marketplace_revenue | INTEGER | - | 市场收益 |
| projects_created | projects_created | INTEGER | - | 创建项目数 |
| projects_exported | projects_exported | INTEGER | - | 导出项目数 |
| raw_data | raw_data | JSONB | - | 原始数据 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |

---

### 6.5 analytics_monthly_metrics (月度指标)

**表名变更**: 无（v3.12新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| metric_month | metric_month | DATE UNIQUE | - | 指标月份 |
| mau | mau | INTEGER | - | 月活跃用户 |
| new_users | new_users | INTEGER | - | 新用户数 |
| churned_users | churned_users | INTEGER | - | 流失用户数 |
| mrr | mrr | DECIMAL(12,2) | - | 月度经常性收入 |
| arr | arr | DECIMAL(12,2) | - | 年度经常性收入 |
| arpu | arpu | DECIMAL(8,2) | - | 每用户平均收入 |
| trial_to_paid_rate | trial_to_paid_rate | REAL | - | 试用转付费率 |
| free_to_paid_rate | free_to_paid_rate | REAL | - | 免费转付费率 |
| tier_distribution | tier_distribution | JSONB | - | 等级分布 |
| raw_data | raw_data | JSONB | - | 原始数据 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |

---

### 6.6 analytics_user_cohorts (用户群组)

**表名变更**: 无（v3.12新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| cohort_date | cohort_date | DATE | - | 群组日期 |
| cohort_type | cohort_type | TEXT | - | 群组类型 |
| first_action_at | first_action_at | TIMESTAMPTZ | - | 首次操作时间 |
| metadata | metadata | JSONB | - | 元数据 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |

**UNIQUE约束**: `(user_id, cohort_type)`

---

### 6.7 analytics_cohort_retention (群组留存)

**表名变更**: 无（v3.12新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| cohort_date | cohort_date | DATE | - | 群组日期 |
| cohort_type | cohort_type | TEXT | - | 群组类型 |
| cohort_size | cohort_size | INTEGER | - | 群组大小 |
| retention_d1 | retention_d1 | REAL | - | 第1天留存率 |
| retention_d7 | retention_d7 | REAL | - | 第7天留存率 |
| retention_d14 | retention_d14 | REAL | - | 第14天留存率 |
| retention_d30 | retention_d30 | REAL | - | 第30天留存率 |
| retention_d60 | retention_d60 | REAL | - | 第60天留存率 |
| retention_d90 | retention_d90 | REAL | - | 第90天留存率 |
| raw_data | raw_data | JSONB | - | 原始数据 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |

**UNIQUE约束**: `(cohort_date, cohort_type)`

---

### 6.8 analytics_error_summary (错误汇总)

**表名变更**: 无（v3.12新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| summary_date | summary_date | DATE | - | 汇总日期 |
| error_type | error_type | TEXT | - | 错误类型 |
| error_code | error_code | TEXT | - | 错误代码 |
| endpoint | endpoint | TEXT | - | 端点 |
| occurrence_count | occurrence_count | INTEGER | - | 发生次数 |
| affected_users | affected_users | INTEGER | - | 受影响用户数 |
| sample_message | sample_message | TEXT | - | 样例消息 |
| sample_request_id | sample_request_id | TEXT | - | 样例请求ID |
| trend_vs_previous | trend_vs_previous | REAL | - | 相对前一天趋势 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |

**UNIQUE约束**: `(summary_date, error_type, error_code, endpoint)`

---

### 6.9 analytics_funnel_metrics (漏斗指标)

**表名变更**: 无（v3.12新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| metric_date | metric_date | DATE | - | 指标日期 |
| funnel_type | funnel_type | TEXT | - | 漏斗类型 |
| stage_visitors | stage_visitors | INTEGER | - | 访客数 |
| stage_signups | stage_signups | INTEGER | - | 注册数 |
| stage_activated | stage_activated | INTEGER | - | 激活数 |
| stage_engaged | stage_engaged | INTEGER | - | 参与数 |
| stage_converted | stage_converted | INTEGER | - | 转化数 |
| conversion_rates | conversion_rates | JSONB | - | 转化率 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |

**UNIQUE约束**: `(metric_date, funnel_type)`

---

## 7. AI与生成表

### 7.1 asset_prompt_templates (素材模板)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT | - | 用户ID |
| name | name | TEXT | - | 模板名称 |
| description | description | TEXT | - | 描述 |
| who_type | who_type | TEXT | - | Who类型 |
| who_custom | who_custom | TEXT | - | Who自定义 |
| what_type | what_type | TEXT | - | What类型 |
| what_custom | what_custom | TEXT | - | What自定义 |
| where_type | where_type | TEXT | - | Where类型 |
| where_custom | where_custom | TEXT | - | Where自定义 |
| style | style | TEXT | - | 风格 |
| moods | moods | TEXT[] | - | 情绪 |
| aspect_ratio | aspect_ratio | TEXT | - | 宽高比 |
| creativity_level | creativity_level | REAL | - | 创意度 |
| negative_prompt | negative_prompt | TEXT | - | 负面提示词 |
| use_count | use_count | INTEGER | - | 使用次数 |
| last_used_at | last_used_at | TIMESTAMPTZ | - | 最后使用时间 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |

---

### 7.2 page_prompt_templates (页面模板)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT | - | 用户ID |
| name | name | TEXT | - | 模板名称 |
| layout | layout | TEXT | - | 布局 |
| story_theme | story_theme | TEXT | - | 故事主题 |
| main_character | main_character | TEXT | - | 主角 |
| style | style | TEXT | - | 风格 |
| creativity_level | creativity_level | REAL | - | 创意度 |
| negative_prompt | negative_prompt | TEXT | - | 负面提示词 |
| generation_mode | generation_mode | TEXT | - | 生成模式 |
| use_count | use_count | INTEGER | - | 使用次数 |
| last_used_at | last_used_at | TIMESTAMPTZ | - | 最后使用时间 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |

---

### 7.3 user_generations (生成历史)

**表名变更**: 无（v3.24新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| image_url | image_url | TEXT | - | 图片URL |
| original_prompt | original_prompt | TEXT | - | 原始提示词 |
| enhanced_prompt | enhanced_prompt | TEXT | - | 增强提示词 |
| negative_prompt | negative_prompt | TEXT | - | 负面提示词 |
| style | style | VARCHAR(50) | - | 风格 |
| moods | moods | TEXT[] | - | 情绪 |
| aspect_ratio | aspect_ratio | VARCHAR(50) | - | 宽高比 |
| generation_mode | generation_mode | VARCHAR(20) | - | 生成模式 |
| creativity_level | creativity_level | REAL | - | 创意度 |
| who_param | who_param | TEXT | - | Who参数 |
| what_param | what_param | TEXT | - | What参数 |
| where_param | where_param | TEXT | - | Where参数 |
| has_reference | has_reference | BOOLEAN | - | 是否有参考图 |
| reference_strength | reference_strength | REAL | - | 参考强度 |
| batch_id | batch_id | VARCHAR(50) | - | 批次ID |
| batch_index | batch_index | INTEGER | - | 批次索引 |
| credits_used | credits_used | INTEGER | - | 消耗积分 |
| model_used | model_used | VARCHAR(100) | - | 使用的模型 |
| generation_time_ms | generation_time_ms | INTEGER | - | 生成时长（毫秒） |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |

---

### 7.4 generation_tasks (生成任务)

**表名变更**: 无（v3.23新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| task_id | task_id | VARCHAR(32) UNIQUE | - | 任务ID |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| task_type | task_type | VARCHAR(50) | - | 任务类型 |
| priority | priority | INTEGER | - | 优先级 |
| params | params | JSONB | - | 参数 |
| status | status | VARCHAR(20) | - | 状态 |
| progress | progress | INTEGER | - | 进度（0-100） |
| current_step | current_step | INTEGER | - | 当前步骤 |
| total_steps | total_steps | INTEGER | - | 总步骤数 |
| progress_message | progress_message | VARCHAR(500) | - | 进度消息 |
| result | result | JSONB | - | 结果 |
| error_message | error_message | TEXT | - | 错误消息 |
| error_code | error_code | VARCHAR(50) | - | 错误代码 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| queued_at | queued_at | TIMESTAMPTZ | - | 入队时间 |
| started_at | started_at | TIMESTAMPTZ | - | 开始时间 |
| completed_at | completed_at | TIMESTAMPTZ | - | 完成时间 |
| worker_id | worker_id | VARCHAR(100) | - | Worker ID |
| retry_count | retry_count | INTEGER | - | 重试次数 |
| max_retries | max_retries | INTEGER | - | 最大重试次数 |
| expires_at | expires_at | TIMESTAMPTZ | - | 过期时间 |

---

### 7.5 ai_usage_daily (AI使用统计)

**表名变更**: 无（v3.21新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| date | date | DATE | - | 日期 |
| provider | provider | TEXT | - | 提供商 |
| model | model | TEXT | - | 模型 |
| call_type | call_type | TEXT | - | 调用类型 |
| total_calls | total_calls | INTEGER | - | 总调用次数 |
| successful_calls | successful_calls | INTEGER | - | 成功次数 |
| failed_calls | failed_calls | INTEGER | - | 失败次数 |
| total_input_tokens | total_input_tokens | BIGINT | - | 总输入token |
| total_output_tokens | total_output_tokens | BIGINT | - | 总输出token |
| total_images | total_images | INTEGER | - | 总图片数 |
| avg_latency_ms | avg_latency_ms | INTEGER | - | 平均延迟 |
| min_latency_ms | min_latency_ms | INTEGER | - | 最小延迟 |
| max_latency_ms | max_latency_ms | INTEGER | - | 最大延迟 |
| estimated_cost_usd | estimated_cost_usd | DECIMAL(10,4) | - | 估计成本（美元） |
| error_counts | error_counts | JSONB | - | 错误统计 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |

**UNIQUE约束**: `(date, provider, model, call_type)`

---

## 8. 营销与活动表

### 8.1 holiday_themes (节日主题)

**表名变更**: 无（v3.13新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | TEXT PRIMARY KEY | - | 主题ID（如: christmas, halloween） |
| name | name | TEXT | - | 主题名称 |
| date_rule | date_rule | JSONB | - | 日期规则 |
| theme_config | theme_config | JSONB | - | 主题配置 |
| priority | priority | INTEGER | - | 优先级 |
| is_active | is_active | BOOLEAN | - | 是否激活 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |

---

### 8.2 campaigns (营销活动)

**表名变更**: 无（v3.13新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| name | name | TEXT | - | 活动名称 |
| description | description | TEXT | - | 描述 |
| type | type | TEXT | - | 活动类型 |
| config | config | JSONB | - | 配置 |
| target_type | target_type | TEXT | - | 目标类型 |
| target_config | target_config | JSONB | - | 目标配置 |
| notification_channels | notification_channels | TEXT[] | - | 通知渠道 |
| notification_config | notification_config | JSONB | - | 通知配置 |
| start_at | start_at | TIMESTAMPTZ | - | 开始时间 |
| end_at | end_at | TIMESTAMPTZ | - | 结束时间 |
| timezone | timezone | TEXT | - | 时区 |
| usage_limit | usage_limit | INTEGER | - | 使用限额 |
| usage_per_user | usage_per_user | INTEGER | - | 每用户限额 |
| usage_count | usage_count | INTEGER | - | 使用次数（v3.27原子增量） |
| status | status | TEXT | - | 状态 |
| is_active | is_active | BOOLEAN | - | 是否激活 |
| created_by | created_by | TEXT REFERENCES profiles(id) | - | 创建人 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |

---

### 8.3 campaign_claims (活动领取)

**表名变更**: 无（v3.13新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| campaign_id | campaign_id | UUID REFERENCES campaigns(id) | - | 活动ID |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| credits_received | credits_received | INTEGER | - | 获得积分 |
| claimed_at | claimed_at | TIMESTAMPTZ | - | 领取时间 |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间（等同claimed_at） |

**UNIQUE约束**: `(campaign_id, user_id)`

---

### 8.4 campaign_dismissals (活动关闭)

**表名变更**: 无（v3.13新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| campaign_id | campaign_id | UUID REFERENCES campaigns(id) | - | 活动ID |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| channel | channel | TEXT | - | 渠道 |
| dismissed_at | dismissed_at | TIMESTAMPTZ | - | 关闭时间 |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间（等同dismissed_at） |

**UNIQUE约束**: `(campaign_id, user_id, channel)`

---

## 9. 实验系统表

### 9.1 experiments (实验配置)

**表名变更**: 无（v3.20新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| experiment_key | experiment_key | VARCHAR(100) UNIQUE | - | 实验键 |
| name | name | VARCHAR(255) | - | 实验名称 |
| description | description | TEXT | - | 描述 |
| experiment_type | experiment_type | VARCHAR(20) | - | 实验类型 |
| status | status | VARCHAR(20) | - | 状态 |
| variants | variants | JSONB | - | 变体配置 |
| targeting | targeting | JSONB | - | 目标配置 |
| traffic_allocation | traffic_allocation | INTEGER | - | 流量分配（0-100） |
| metrics | metrics | JSONB | - | 指标 |
| fallback_variant | fallback_variant | VARCHAR(100) | - | 降级变体 |
| winning_variant | winning_variant | VARCHAR(100) | - | 获胜变体 |
| start_at | start_at | TIMESTAMPTZ | - | 开始时间 |
| end_at | end_at | TIMESTAMPTZ | - | 结束时间 |
| created_by | created_by | TEXT | - | 创建人 |
| updated_by | updated_by | TEXT | - | 更新人 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |

---

### 9.2 experiment_assignments (实验分配)

**表名变更**: 无（v3.20新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| experiment_id | experiment_id | UUID REFERENCES experiments(id) | - | 实验ID |
| experiment_key | experiment_key | VARCHAR(100) | - | 实验键 |
| user_identifier | user_identifier | VARCHAR(100) | - | 用户标识符 |
| identifier_type | identifier_type | VARCHAR(20) | - | 标识符类型 |
| variant_key | variant_key | VARCHAR(100) | - | 变体键 |
| context | context | JSONB | - | 上下文 |
| assigned_at | assigned_at | TIMESTAMPTZ | - | 分配时间 |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间（等同assigned_at） |

**UNIQUE约束**: `(experiment_id, user_identifier)`

---

### 9.3 experiment_results (实验结果)

**表名变更**: 无（v3.20新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| experiment_id | experiment_id | UUID REFERENCES experiments(id) | - | 实验ID |
| variant_key | variant_key | VARCHAR(100) | - | 变体键 |
| date | date | DATE | - | 日期 |
| hour | hour | INTEGER | - | 小时 |
| participants | participants | INTEGER | - | 参与者数 |
| exposures | exposures | INTEGER | - | 曝光数 |
| conversions | conversions | INTEGER | - | 转化数 |
| conversion_rate | conversion_rate | DECIMAL(10,6) | - | 转化率 |
| metrics_data | metrics_data | JSONB | - | 指标数据 |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |
| - | created_at | TIMESTAMPTZ | ✨ | **新增**: 创建时间 |

**UNIQUE约束**: `(experiment_id, variant_key, date, hour)`

---

## 10. 其他支持表

### 10.1 support_tickets (支持工单)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| user_id | user_id | TEXT REFERENCES profiles(id) | - | 用户ID |
| admin_id | admin_id | TEXT REFERENCES profiles(id) | - | 管理员ID |
| category | category | TEXT | - | 类别 |
| content | content | TEXT | - | 内容 |
| metadata | metadata | JSONB | - | 元数据 |
| status | status | TEXT | - | 状态 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |
| - | updated_at | TIMESTAMPTZ | ✨ | **新增**: 更新时间 |
| - | is_deleted | BOOLEAN | ✨ | **新增**: 软删除标志 |
| - | deleted_at | TIMESTAMPTZ | ✨ | **新增**: 删除时间 |

---

### 10.2 content_reports (内容举报)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| reporter_id | reporter_id | TEXT REFERENCES profiles(id) | - | 举报人ID |
| listing_id | listing_id | UUID REFERENCES marketplace_listings(id) | - | 商品ID |
| reason | reason | TEXT | - | 原因 |
| status | status | TEXT | - | 状态 |
| admin_response | admin_response | TEXT | - | 管理员回复 |
| reviewed_by | reviewed_by | TEXT REFERENCES profiles(id) | - | 审核人 |
| reviewed_at | reviewed_at | TIMESTAMPTZ | - | 审核时间 |
| timezone | timezone | TEXT | - | 时区 |
| created_at_local | created_at_local | TIMESTAMP | - | 创建时间（本地） |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间（UTC） |
| updated_at | updated_at | TIMESTAMPTZ | - | 更新时间 |

**UNIQUE约束**: `(reporter_id, listing_id) WHERE status IN ('pending', 'reviewed')`

---

### 10.3 leaderboard_snapshots (排行榜)

**表名变更**: 无

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| period_start | period_start | DATE | - | 周期开始 |
| period_end | period_end | DATE | - | 周期结束 |
| board_type | board_type | TEXT | - | 排行榜类型 |
| top_list | top_list | JSONB | - | 排行数据 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |

**UNIQUE约束**: `(period_start, period_end, board_type)`

---

### 10.4 scheduled_task_logs (定时任务日志)

**表名变更**: 无（v3.15新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| task_name | task_name | TEXT | - | 任务名称 |
| task_type | task_type | TEXT | - | 任务类型 |
| started_at | started_at | TIMESTAMPTZ | - | 开始时间 |
| completed_at | completed_at | TIMESTAMPTZ | - | 完成时间 |
| duration_ms | duration_ms | INTEGER | - | 持续时长（毫秒） |
| status | status | TEXT | - | 状态 |
| result_summary | result_summary | JSONB | - | 结果摘要 |
| error_message | error_message | TEXT | - | 错误消息 |
| error_stack | error_stack | TEXT | - | 错误堆栈 |
| hostname | hostname | TEXT | - | 主机名 |
| pid | pid | INTEGER | - | 进程ID |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |

---

### 10.5 webhook_events (Webhook事件)

**表名变更**: 无（v3.22新增）

| 旧字段名 | 新字段名 | 类型 | 改动类型 | 说明 |
|---------|---------|------|---------|------|
| id | id | UUID PRIMARY KEY | - | 主键 |
| event_id | event_id | TEXT UNIQUE | - | 事件ID（幂等性） |
| event_type | event_type | TEXT | - | 事件类型 |
| processed_at | processed_at | TIMESTAMPTZ | - | 处理时间 |
| payload | payload | JSONB | - | 载荷 |
| result | result | JSONB | - | 结果 |
| created_at | created_at | TIMESTAMPTZ | - | 创建时间 |

---

## 11. 变更汇总

### 11.1 新增标准字段统计

| 字段 | 新增表数量 | 说明 |
|------|-----------|------|
| `updated_at` | 15张 | 之前缺少updated_at的表 |
| `is_deleted` | 12张 | 之前缺少软删除的表 |
| `deleted_at` | 12张 | 之前缺少软删除的表 |
| `created_at` (补充) | 8张 | 部分表只有特殊时间字段 |
| `ext_json` | 5张 | 核心业务表预留扩展 |

### 11.2 新增冗余字段统计

| 表 | 新增冗余字段 | 维护方式 |
|---|-------------|---------|
| profiles | project_count, last_active_at | 触发器 + 定时任务 |
| projects | asset_count, last_opened_at | 触发器 + API |
| marketplace_listings | - | 已有完整统计字段 |

### 11.3 特殊表说明

| 表 | 不添加字段 | 原因 |
|---|-----------|------|
| credit_transactions | updated_at, is_deleted | Append-Only特性 |
| user_events | updated_at | 日志表，无需更新 |
| analytics_events | updated_at | 日志表，无需更新 |
| activity_logs | updated_at | 日志表，无需更新 |
| error_logs | updated_at | 日志表，无需更新 |

---

## 12. 冗余字段说明

### 12.1 冗余字段设计原则

1. **仅用于高频查询**：Dashboard、列表页等
2. **必须注明维护策略**：触发器 vs 定时任务
3. **保持一致性**：使用触发器自动更新

### 12.2 详细说明

#### profiles表

| 字段 | 用途 | 维护策略 | 一致性 |
|-----|------|---------|--------|
| project_count | Dashboard统计 | `trigger on projects INSERT/DELETE` | 实时 |
| last_active_at | 用户活跃度分析 | 定时任务每日更新 | 延迟24h |

**收益**：避免 `COUNT(*) FROM projects WHERE user_id = ?` 查询

#### projects表

| 字段 | 用途 | 维护策略 | 一致性 |
|-----|------|---------|--------|
| asset_count | 项目详情页显示 | `trigger on assets INSERT/DELETE` | 实时 |
| last_opened_at | "最近打开"排序 | API更新 | 实时 |

**收益**：避免 `COUNT(*) FROM assets WHERE project_id = ?` 查询

#### marketplace_listings表

| 字段 | 用途 | 维护策略 | 一致性 |
|-----|------|---------|--------|
| sales_count | 销售排行 | `trigger on user_purchases INSERT` | 实时 |
| unique_buyers_count | 买家数统计 | `trigger on user_purchases INSERT` | 实时 |
| total_revenue | 收益统计 | `trigger on user_purchases INSERT` | 实时 |
| usage_count | 使用排行 | `trigger on listing_usages INSERT` (v3.14+) | 实时 |

**说明**：这些字段已存在，通过触发器维护，无需新增

---

## 13. 代码迁移建议

### 13.1 全局搜索替换（谨慎）

由于大部分字段名保持不变，只需处理新增字段：

```bash
# 示例：添加updated_at字段到查询
# 查找所有profiles的SELECT语句，添加updated_at

# 旧代码
SELECT id, email, tier, created_at FROM profiles

# 新代码
SELECT id, email, tier, created_at, updated_at FROM profiles
```

### 13.2 Repository层修改

**新增字段需要在Entity中添加**：

```python
# domains/identity/entities.py

@dataclass
class Profile:
    id: str
    email: str
    tier: str
    created_at: datetime
    updated_at: datetime  # ✨ 新增
    is_deleted: bool = False  # ✨ 新增
    deleted_at: Optional[datetime] = None  # ✨ 新增
    last_active_at: Optional[datetime] = None  # ✨ 新增（冗余字段）
    project_count: int = 0  # ✨ 新增（冗余字段）
```

### 13.3 特殊注意事项

**⚠️ profiles.id 是TEXT，不是UUID**：

```python
# ❌ 错误
user_id = UUID(clerk_user_id)

# ✅ 正确
user_id = clerk_user_id  # 直接使用TEXT
```

**✅ 积分交易的Append-Only特性**：

```python
# ❌ 错误 - 不允许UPDATE
UPDATE credit_transactions SET amount = 10 WHERE id = ?

# ✅ 正确 - 插入反向记录
INSERT INTO credit_transactions (user_id, amount, bucket, ...)
VALUES (user_id, -5, 'monthly', ...)  # 负金额=退款
```

---

## 14. 测试清单

### 14.1 数据迁移验证

- [ ] 所有表的记录数一致（迁移前后）
- [ ] profiles表的user_id格式正确（TEXT，非UUID）
- [ ] credit_transactions的余额快照准确
- [ ] 冗余字段值正确（project_count等）
- [ ] 时区字段正确填充

### 14.2 业务逻辑验证

- [ ] 积分扣费顺序正确（月度→永久）
- [ ] 幂等性键有效（重复请求不重复扣费）
- [ ] 触发器正常工作（软删除、统计更新）
- [ ] RLS策略生效（权限控制）
- [ ] 外键约束生效（级联删除）

### 14.3 性能验证

- [ ] Dashboard查询性能（对比重构前后）
- [ ] 市场列表查询性能
- [ ] 积分交易历史查询性能
- [ ] 索引命中率 >95%

---

## 附录

### A. 字段类型对照表

| PostgreSQL类型 | Python类型 | 说明 |
|---------------|-----------|------|
| TEXT | str | 字符串 |
| VARCHAR(N) | str | 有长度限制的字符串 |
| INTEGER | int | 整数 |
| BIGINT | int | 大整数 |
| REAL | float | 单精度浮点 |
| DECIMAL(M,N) | Decimal | 精确小数 |
| BOOLEAN | bool | 布尔值 |
| TIMESTAMPTZ | datetime | 带时区时间戳 |
| TIMESTAMP | datetime | 无时区时间戳 |
| DATE | date | 日期 |
| UUID | UUID | 通用唯一标识符 |
| JSONB | dict | JSON对象 |
| TEXT[] | List[str] | 字符串数组 |

### B. 常用CHECK约束

```sql
-- 用户等级
tier TEXT CHECK (tier IN ('free', 'starter', 'pro'))

-- 积分桶
bucket TEXT CHECK (bucket IN ('monthly', 'permanent'))

-- 审核状态
moderation_status TEXT CHECK (moderation_status IN ('draft', 'pending', 'approved', 'rejected'))

-- 流量分配
traffic_allocation INTEGER CHECK (traffic_allocation >= 0 AND traffic_allocation <= 100)

-- 价格范围
price_credits INTEGER CHECK (price_credits >= 0 AND price_credits <= 500)
```

### C. 完整表清单（38张）

1. profiles
2. user_discounts
3. credit_transactions
4. projects
5. assets
6. marketplace_listings
7. user_purchases
8. listing_usages
9. system_configs
10. config_audit_logs
11. system_resources
12. system_resource_audit_logs
13. notifications
14. activity_logs
15. admin_operation_logs
16. error_logs
17. user_events
18. analytics_events
19. aggregated_stats
20. analytics_daily_metrics
21. analytics_monthly_metrics
22. analytics_user_cohorts
23. analytics_cohort_retention
24. analytics_error_summary
25. analytics_funnel_metrics
26. asset_prompt_templates
27. page_prompt_templates
28. user_generations
29. generation_tasks
30. ai_usage_daily
31. holiday_themes
32. campaigns
33. campaign_claims
34. campaign_dismissals
35. experiments
36. experiment_assignments
37. experiment_results
38. support_tickets
39. content_reports
40. leaderboard_snapshots
41. scheduled_task_logs
42. webhook_events

**总计**: 42张表（包含4张支持表）

---

**文档结束**

> **下一步**: 参考 `refactored_schema.sql` 执行数据库迁移
>
> **变更记录**:
> - 2026-01-09: v1.0 - 初始版本，完整的38+张表字段映射
