# Repository vs SQL Schema 全面审计计划

## 审计目标
确保后端所有 Repository 代码使用的表和字段在 SQL Schema 中都正确定义。

## 审计范围

### Repository 文件清单 (29个，排除 __init__.py 和 base_repository.py)

| # | Repository 文件 | 主要操作表 | 优先级 |
|---|----------------|-----------|--------|
| 1 | user_repository.py | profiles, user_discounts | P0 |
| 2 | credit_repository.py | profiles, credit_transactions | P0 |
| 3 | project_repository.py | projects, project_pages, marketplace_purchases | P0 |
| 4 | listing_repository.py | marketplace_listings, marketplace_purchases | P0 |
| 5 | asset_repository.py | assets | P0 |
| 6 | payment_repository.py | payment_records, profiles | P0 |
| 7 | subscription_repository.py | profiles, credit_transactions | P0 |
| 8 | notification_repository.py | notifications | P1 |
| 9 | support_repository.py | support_tickets, support_replies, content_reports | P1 |
| 10 | admin_repository.py | admin_operations, aggregated_stats, profiles | P1 |
| 11 | feature_flag_repository.py | feature_flags, flag_exposures, flag_audit_logs | P1 |
| 12 | experiment_repository.py | experiments, experiment_assignments, experiment_results | P1 |
| 13 | campaign_repository.py | campaigns, campaign_participations, campaign_dismissals | P1 |
| 14 | analytics_repository.py | analytics_aggregation, daily_metrics, monthly_metrics | P2 |
| 15 | analytics_events_repository.py | analytics_events, user_events | P2 |
| 16 | events_repository.py | user_events | P2 |
| 17 | error_logs_repository.py | error_logs | P2 |
| 18 | logging_repository.py | api_logs, activity_logs | P2 |
| 19 | metrics_repository.py | daily_metrics, monthly_metrics | P2 |
| 20 | config_repository.py | system_configs | P2 |
| 21 | webhook_repository.py | stripe_webhook_events, clerk_webhook_events | P2 |
| 22 | article_repository.py | articles | P2 |
| 23 | themes_repository.py | daily_themes, holidays | P2 |
| 24 | category_repository_impl.py | asset_categories, asset_tags | P2 |
| 25 | system_resource_repository.py | system_resources | P2 |
| 26 | system_resources_admin_repository.py | system_resources, system_resource_audit_logs | P2 |
| 27 | tasks_repository.py | scheduled_task_logs | P2 |
| 28 | templates_repository.py | projects (templates) | P2 |
| 29 | field_mappings.py | (字段映射配置) | P3 |

### SQL Schema 文件
- `01_core_business.sql` - 核心业务表
- `02_platform_services.sql` - 平台服务表
- `03_infrastructure.sql` - 基础设施表

## 审计方法

### Phase 1: 自动提取 (使用脚本)
对每个 Repository 文件提取:
1. 所有 `.table("xxx")` 调用 → 使用的表名
2. 所有 `.insert({...})` 中的字段 → 写入字段
3. 所有 `.select("xxx")` 中的字段 → 读取字段
4. 所有 `.eq("xxx", ...)` 中的字段 → 查询条件字段
5. 所有 `.update({...})` 中的字段 → 更新字段
6. 所有 RPC 函数调用 → 使用的 RPC 函数名和参数

### Phase 2: 人工交叉验证
1. 对比提取的字段与 SQL 定义
2. 检查字段类型是否匹配
3. 检查约束是否兼容
4. 检查索引是否足够

### Phase 3: 问题分类
- **CRITICAL**: 表不存在、必填字段缺失
- **HIGH**: 字段名不匹配、字段类型错误
- **MEDIUM**: 缺少索引、缺少约束
- **LOW**: 字段顺序、注释缺失

## 检查清单

### 每个 Repository 需检查项:

- [ ] 表是否存在
- [ ] 所有读取字段是否存在
- [ ] 所有写入字段是否存在
- [ ] 所有查询条件字段是否存在
- [ ] 字段类型是否匹配
- [ ] RPC 函数是否存在
- [ ] RPC 函数参数是否匹配
- [ ] RPC 函数返回值是否匹配

---
**创建时间**: 2026-01-12
**执行状态**: 待开始
