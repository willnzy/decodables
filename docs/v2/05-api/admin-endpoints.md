# Admin API 端点清单

**状态**: needs-review  
**版本**: 1.1.0  
**版本日期**: 2026-01-20  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

> 说明：本清单来源于集成测试清单，用于分模块验证。

## 快速测试命令

```bash
python -m pytest tests/integration/staging/admin/{module}/ -v --tb=short
```

## 测试状态图例

| 状态 | 说明 |
|------|------|
| ✅ | 测试通过 |
| ⏭️ | 跳过 (预期行为) |
| ❌ | 测试失败，需要修复 |
| 🔧 | 已修复代码，等待部署验证 |
| ⏳ | 待测试 |

---

## Admin 用户配置

Admin 测试需要配置以下环境变量:

```bash
export TEST_ADMIN_TOKEN='eyJhbG...'
export CLERK_SECRET_KEY='sk_test_...'
export TEST_ADMIN_SESSION_ID='sess_...'
```

**Admin 用户信息**:
- user_id: `user_38J7ztkfxMPma40Q5FQ2ryO80eg`
- email: `willnzy@gmail.com`
- tier: `t1`
- role: `admin`

---

## 模块清单

### 1. Users (用户管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/users` | GET | 30/min | ⏳ |
| `/api/admin/users/by-tier/{tier}` | GET | 30/min | ⏳ |
| `/api/admin/users/{user_id}` | GET | 30/min | ⏳ |
| `/api/admin/users/{user_id}/credits` | POST | 10/min | ⏳ |
| `/api/admin/users/{user_id}` | PATCH | 10/min | ⏳ |
| `/api/admin/users/{user_id}/discount` | POST | 10/min | ⏳ |
| `/api/admin/users/{user_id}/payments` | GET | 30/min | ⏳ |
| `/api/admin/users/{user_id}/projects` | GET | 30/min | ⏳ |
| `/api/admin/users/{user_id}/asset-usage` | GET | 30/min | ⏳ |
| `/api/admin/users/{user_id}/env-stats` | GET | 30/min | ⏳ |
| `/api/admin/projects/{project_id}/restore` | POST | 10/min | ⏳ |
| `/api/admin/projects/feed` | GET | 30/min | ⏳ |

### 2. Subscriptions (订阅管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/subscriptions/refund` | POST | 10/min | ⏳ |
| `/api/admin/subscriptions/subscription/cancel` | POST | 10/min | ⏳ |
| `/api/admin/subscriptions/subscription/downgrade` | POST | 10/min | ⏳ |

### 3. Config (系统配置)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/config` | GET | 30/min | ⏳ |
| `/api/v2/admin/config/{config_key}` | GET | 30/min | ⏳ |
| `/api/v2/admin/config` | PUT | 10/min | ⏳ |
| `/api/v2/admin/config/batch` | PUT | 10/min | ⏳ |
| `/api/v2/admin/config/rate-limits` | GET | 30/min | ⏳ |
| `/api/v2/admin/config/rate-limits/preset` | POST | 10/min | ⏳ |
| `/api/v2/admin/config/rate-limits/presets` | GET | 30/min | ⏳ |
| `/api/v2/admin/config/cache/clear` | POST | 10/min | ⏳ |

### 4. Tiers (Tier 配置管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/tiers` | GET | 30/min | ⏳ |
| `/api/v2/admin/tiers/{tier_code}` | GET | 30/min | ⏳ |
| `/api/v2/admin/tiers/{tier_code}` | PUT | 10/min | ⏳ |

### 5. Feature Flags (功能开关)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/feature-flags` | GET | - | ⏳ |
| `/api/v2/admin/feature-flags` | POST | - | ⏳ |
| `/api/v2/admin/feature-flags/{key}` | GET | - | ⏳ |
| `/api/v2/admin/feature-flags/{key}` | PATCH | - | ⏳ |
| `/api/v2/admin/feature-flags/{key}/toggle` | POST | - | ⏳ |
| `/api/v2/admin/feature-flags/{key}` | DELETE | - | ⏳ |
| `/api/v2/admin/feature-flags/test-evaluation` | POST | - | ⏳ |
| `/api/v2/admin/feature-flags/{key}/audit` | GET | - | ⏳ |
| `/api/v2/admin/feature-flags/client/flags` | GET | - | ⏳ |

### 6. Asset Categories (素材分类)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/asset-categories` | GET | - | ⏳ |
| `/api/v2/admin/asset-categories/tree` | GET | - | ⏳ |
| `/api/v2/admin/asset-categories` | POST | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}` | PATCH | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}/move` | PUT | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}` | DELETE | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}/resources` | GET | - | ⏳ |

### 7. Themes (主题管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/themes` | GET | 60/min | ⏳ |
| `/api/v2/admin/themes/{id}` | GET | 60/min | ⏳ |
| `/api/v2/admin/themes` | POST | 30/min | ⏳ |
| `/api/v2/admin/themes/{id}` | PUT | 30/min | ⏳ |
| `/api/v2/admin/themes/{id}` | DELETE | 20/min | ⏳ |
| `/api/v2/admin/themes/batch-generate` | POST | 5/min | ⏳ |
| `/api/v2/admin/themes/generation-status` | GET | 30/min | ⏳ |
| `/api/v2/admin/themes/calendar` | GET | 30/min | ⏳ |
| `/api/v2/admin/themes/review/pending` | GET | 30/min | ⏳ |
| `/api/v2/admin/themes/{id}/review` | POST | 30/min | ⏳ |
| `/api/v2/admin/themes/{id}/regenerate` | POST | 10/min | ⏳ |
| `/api/v2/admin/themes/{id}/history` | GET | 30/min | ⏳ |
| `/api/v2/admin/themes/review/batch-approve` | POST | 10/min | ⏳ |

### 8. Campaigns (营销活动)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/campaigns` | GET | 30/min | ⏳ |
| `/api/v2/admin/campaigns/{id}` | GET | 30/min | ⏳ |
| `/api/v2/admin/campaigns` | POST | 20/min | ⏳ |
| `/api/v2/admin/campaigns/{id}` | PUT | 20/min | ⏳ |
| `/api/v2/admin/campaigns/{id}` | DELETE | 10/min | ⏳ |
| `/api/v2/admin/campaigns/{id}/activate` | POST | 10/min | ⏳ |
| `/api/v2/admin/campaigns/{id}/pause` | POST | 10/min | ⏳ |
| `/api/v2/admin/campaigns/{id}/stats` | GET | 30/min | ⏳ |

### 9. Experiments (A/B 实验)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/experiments` | GET | 30/min | ⏳ |
| `/api/v2/admin/experiments` | POST | 20/min | ⏳ |
| `/api/v2/admin/experiments/{key}` | GET | 30/min | ⏳ |
| `/api/v2/admin/experiments/{key}` | PUT | 20/min | ⏳ |
| `/api/v2/admin/experiments/{key}` | DELETE | 10/min | ⏳ |
| `/api/v2/admin/experiments/{key}/status` | PUT | 20/min | ⏳ |
| `/api/v2/admin/experiments/{key}/results` | GET | 30/min | ⏳ |
| `/api/v2/admin/experiments/{key}/aggregate` | POST | 10/min | ⏳ |
| `/api/v2/admin/experiments/aggregate-all` | POST | 5/min | ⏳ |
| `/api/v2/admin/experiments/cache/clear` | POST | 10/min | ⏳ |
| `/api/v2/admin/experiments/{key}/ai-analysis` | POST | 10/min | ⏳ |
| `/api/v2/admin/experiments/{key}/quick-recommendation` | GET | 30/min | ⏳ |
| `/api/v2/admin/experiments/{key}/trend` | GET | 20/min | ⏳ |
| `/api/v2/admin/experiments/{key}/hourly-trend` | GET | 20/min | ⏳ |

### 10. Events (事件分析)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/events/events` | GET | 30/min | ⏳ |
| `/api/admin/events/events/stats` | GET | 30/min | ⏳ |
| `/api/admin/events/aggregated/{stat_type}` | GET | 30/min | ⏳ |
| `/api/admin/events/aggregated/{stat_type}/range` | GET | 30/min | ⏳ |
| `/api/admin/events/aggregation/run` | POST | 5/min | ⏳ |

### 11. Stats (数据统计)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/stats/dashboard` | GET | 30/min | ⏳ |
| `/api/admin/stats/user-growth` | GET | 30/min | ⏳ |
| `/api/admin/stats/revenue` | GET | 30/min | ⏳ |
| `/api/admin/stats/projects` | GET | 30/min | ⏳ |
| `/api/admin/stats/credits` | GET | 30/min | ⏳ |
| `/api/admin/stats/tier-distribution` | GET | 30/min | ⏳ |
| `/api/admin/stats/conversion-funnel` | GET | 30/min | ⏳ |
| `/api/admin/stats/exports` | GET | 30/min | ⏳ |
| `/api/admin/stats/assets` | GET | 30/min | ⏳ |
| `/api/admin/stats/tier-activity` | GET | 30/min | ⏳ |
| `/api/admin/stats/subscription-events` | GET | 30/min | ⏳ |
| `/api/admin/stats/page-views` | GET | 30/min | ⏳ |
| `/api/admin/stats/project-details` | GET | 30/min | ⏳ |
| `/api/admin/stats/returning-users` | GET | 30/min | ⏳ |
| `/api/admin/stats/tier-trend` | GET | 30/min | ⏳ |
| `/api/admin/stats/tier-conversion` | GET | 30/min | ⏳ |
| `/api/admin/stats/performance` | GET | 30/min | ⏳ |
| `/api/admin/stats/user-distribution` | GET | 30/min | ⏳ |

### 12. Metrics (系统指标)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/metrics/daily` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/monthly` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/retention` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/funnel` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/errors` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/dau-trend` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/refresh` | POST | 5/min | ⏳ |

### 13. Logs (日志管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/logs/errors` | GET | 30/min | ⏳ |
| `/api/v2/admin/logs/errors/stats` | GET | 30/min | ⏳ |
| `/api/v2/admin/logs/operations` | GET | 30/min | ⏳ |
| `/api/v2/admin/logs/operations/export` | GET | 10/min | ⏳ |
| `/api/v2/admin/logs/audit` | GET | 30/min | ⏳ |

### 14. System (系统管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/system/configs` | GET | 30/min | ⏳ |
| `/api/v2/admin/system/configs/groups` | GET | 30/min | ⏳ |
| `/api/v2/admin/system/configs` | POST | 10/min | ⏳ |
| `/api/v2/admin/system/configs/{key}` | PUT | 10/min | ⏳ |
| `/api/v2/admin/system/configs/{key}` | DELETE | 10/min | ⏳ |
| `/api/v2/admin/system/configs/audit` | GET | 30/min | ⏳ |
| `/api/v2/admin/system/configs/cache/invalidate` | POST | 5/min | ⏳ |
| `/api/v2/admin/system/system/cache/status` | GET | 30/min | ⏳ |
| `/api/v2/admin/system/system/cache/keys` | GET | 30/min | ⏳ |
| `/api/v2/admin/system/system/cache/key/{key}` | DELETE | 10/min | ⏳ |
| `/api/v2/admin/system/system/cache/clear-all/confirm` | POST | 1/10min | ⏳ |
| `/api/v2/admin/system/system/cache/clear-all` | POST | 1/10min | ⏳ |

### 15. Moderation (内容审核)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/moderation/marketplace/moderation/list` | GET | - | ⏳ |
| `/api/admin/moderation/marketplace/moderation/{id}` | GET | - | ⏳ |
| `/api/admin/moderation/marketplace/moderation/{id}/approve` | POST | - | ⏳ |
| `/api/admin/moderation/marketplace/moderation/{id}/reject` | POST | - | ⏳ |
| `/api/admin/moderation/marketplace/moderation/{id}/delete` | POST | - | ⏳ |
| `/api/admin/moderation/marketplace/moderation/{id}/unpublish` | POST | - | ⏳ |
| `/api/admin/moderation/reports` | GET | - | ⏳ |
| `/api/admin/moderation/reports/stats` | GET | - | ⏳ |
| `/api/admin/moderation/reports/{id}` | GET | - | ⏳ |
| `/api/admin/moderation/reports/{id}/respond` | POST | - | ⏳ |

### 16. Notifications (通知管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/notifications/broadcast` | POST | - | ⏳ |
| `/api/admin/notifications/notification/send` | POST | - | ⏳ |
| `/api/admin/notifications/notification/batch` | POST | - | ⏳ |
| `/api/admin/notifications/notification/stats` | GET | - | ⏳ |
| `/api/admin/notifications/notification/history` | GET | - | ⏳ |

### 17. AI Insights (AI 洞察)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/ai/insights` | GET | - | ⏳ |
| `/api/admin/ai/recommendations` | GET | - | ⏳ |
| `/api/admin/ai/behavior-analysis` | GET | - | ⏳ |
| `/api/admin/ai/generate-report` | POST | - | ⏳ |
| `/api/admin/ai/quick-insights` | GET | - | ⏳ |

### 18. Static Pages (静态页面管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/static-pages` | GET | - | ⏳ |
| `/api/v2/admin/static-pages/{id}` | GET | - | ⏳ |
| `/api/v2/admin/static-pages` | POST | - | ⏳ |
| `/api/v2/admin/static-pages/{id}` | PUT | - | ⏳ |
| `/api/v2/admin/static-pages/{id}` | DELETE | - | ⏳ |
| `/api/v2/admin/static-pages/{id}/publish` | POST | - | ⏳ |
| `/api/v2/admin/static-pages/{id}/unpublish` | POST | - | ⏳ |

### 19. Articles (文章管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/articles` | GET | - | ⏳ |
| `/api/v2/admin/articles/{id}` | GET | - | ⏳ |
| `/api/v2/admin/articles` | POST | - | ⏳ |
| `/api/v2/admin/articles/{id}` | PUT | - | ⏳ |
| `/api/v2/admin/articles/{id}` | DELETE | - | ⏳ |
| `/api/v2/admin/articles/{id}/publish` | POST | - | ⏳ |
| `/api/v2/admin/articles/{id}/unpublish` | POST | - | ⏳ |

### 20. Webhooks (Webhook 重试)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/webhooks/retry` | POST | 10/hour | ⏳ |
| `/api/v2/admin/webhooks/failed` | GET | 30/min | ⏳ |

### 21. Tasks Management (任务管理)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/tasks/management/status` | GET | - | ⏳ |
| `/api/admin/tasks/management/logs` | GET | - | ⏳ |
| `/api/admin/tasks/management/health` | GET | - | ⏳ |
| `/api/admin/tasks/management/{task_name}/run` | POST | - | ⏳ |

### 22. User Creation Monitoring (用户创建监控)

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/monitoring/user-creation/stats` | GET | - | ⏳ |
| `/api/admin/monitoring/user-creation/health` | GET | - | ⏳ |
| `/api/admin/monitoring/user-creation/events` | GET | - | ⏳ |

---

## 推荐测试顺序

1. Users  
2. Subscriptions  
3. Config  
4. Tiers  
5. Feature Flags  
6. Stats  
7. Metrics  
8. Events  
9. Experiments  
10. Asset Categories  
11. Themes  
12. Static Pages  
13. Articles  
14. Campaigns  
15. Moderation  
16. Notifications  
17. System  
18. Logs  
19. Tasks Management  
20. Webhooks  
21. Monitoring  
22. AI Insights

---

## 汇总统计

| 分类 | 模块数 | 端点数 | 已通过 | 已修复待验证 | 待测试 |
|------|--------|--------|--------|--------------|--------|
| 核心管理 | 5 | 35 | 0 | 0 | 35 |
| 数据分析 | 4 | 44 | 0 | 0 | 44 |
| 内容管理 | 4 | 34 | 0 | 0 | 34 |
| 运营功能 | 3 | 23 | 0 | 0 | 23 |
| 系统运维 | 6 | 31 | 0 | 0 | 31 |
| **总计** | **22** | **167** | 0 | 0 | 167 |

---

## 注意事项

### 敏感操作

| 端点 | 风险级别 | 说明 |
|------|----------|------|
| `POST /subscriptions/refund` | 🔴 极高 | 退款操作 |
| `POST /subscriptions/subscription/cancel` | 🔴 极高 | 取消订阅 |
| `POST /users/{id}/credits` | 🔴 极高 | 积分调整 |
| `POST /system/cache/clear-all` | 🔴 极高 | 清空所有缓存 |
| `DELETE /experiments/{key}` | 🟠 高 | 删除实验 |
| `DELETE /campaigns/{id}` | 🟠 高 | 删除活动 |

### Rate Limit 说明

- 查询接口: 30/minute
- 修改操作: 10/minute
- 敏感操作: 5/minute 或更低
- Webhook 重试: 10/hour

### DDD 架构

```
API → Container → Service → Repository
```
