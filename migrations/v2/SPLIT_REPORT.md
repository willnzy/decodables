# SQL Schema 切分报告

**原始文件**: refactored_schema_v2.sql
**总表数**: 60
**总函数数**: 11
**总视图数**: 1
**生成时间**: 2026-01-10

## 文件分类

### 文件 1: 01_core_business.sql
**分类**: 核心业务
**表数量**: 20
**包含的表**:

- `asset_categories`
- `asset_prompt_templates`
- `assets`
- `credit_purchases`
- `credit_transactions`
- `generation_tasks`
- `listing_usages`
- `marketplace_favorites`
- `marketplace_listings`
- `marketplace_purchases`
- `marketplace_reports`
- `marketplace_reviews`
- `page_prompt_templates`
- `profiles`
- `project_versions`
- `projects`
- `subscription_history`
- `system_assets`
- `user_discounts`
- `user_generations`

### 文件 2: 02_platform_services.sql
**分类**: 平台服务
**表数量**: 28
**包含的表**:

- `activity_logs`
- `aggregated_stats`
- `ai_usage_daily`
- `analytics_aggregation`
- `analytics_events`
- `campaign_dismissals`
- `campaign_participations`
- `campaigns`
- `clerk_webhook_events`
- `config_audit_logs`
- `content_reports`
- `daily_metrics`
- `daily_themes`
- `experiment_assignments`
- `experiment_conversions`
- `experiment_exposures`
- `experiment_results`
- `experiments`
- `feature_flags`
- `holidays`
- `monthly_metrics`
- `notifications`
- `onboarding_steps`
- `referrals`
- `stripe_webhook_events`
- `system_resource_audit_logs`
- `user_events`
- `user_onboarding_progress`

### 文件 3: 03_infrastructure.sql
**分类**: 基础设施
**表数量**: 12
**函数数量**: 11
**视图数量**: 1
**初始数据**: 包含所有 INSERT 语句
**包含的表**:

- `admin_operations`
- `ai_call_logs`
- `api_logs`
- `error_logs`
- `payment_records`
- `pricing_history`
- `pricing_plans`
- `scheduled_task_logs`
- `support_replies`
- `support_tickets`
- `system_configs`
- `user_price_overrides`
