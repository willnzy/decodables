# Admin API 接口清单 (按模块分组)

> 方便逐个模块测试验证，减少日志量和部署等待时间
>
> **更新日期**: 2026-01-18

---

## 快速测试命令

```bash
# 测试单个模块
python -m pytest tests/integration/staging/admin/{module}/ -v --tb=short

# 示例
python -m pytest tests/integration/staging/admin/users/ -v --tb=short
python -m pytest tests/integration/staging/admin/config/ -v --tb=short
```

---

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
# 方式 1: 直接设置 Token
export TEST_ADMIN_TOKEN='eyJhbG...'

# 方式 2: 通过 Clerk API 自动获取
export CLERK_SECRET_KEY='sk_test_...'
export TEST_ADMIN_SESSION_ID='sess_...'
```

**Admin 用户信息** (配置在 `test_users.py`):
- **user_id**: `user_38J7ztkfxMPma40Q5FQ2ryO80eg`
- **email**: `willnzy@gmail.com`
- **tier**: `t1`
- **role**: `admin`

---

## 模块清单

### 1. Users (用户管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/users/ -v --tb=short
```

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

**说明**: 12 个端点，用户搜索、积分调整、Tier 更新、项目管理等

---

### 2. Subscriptions (订阅管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/subscriptions/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/subscriptions/refund` | POST | 10/min | ⏳ |
| `/api/admin/subscriptions/subscription/cancel` | POST | 10/min | ⏳ |
| `/api/admin/subscriptions/subscription/downgrade` | POST | 10/min | ⏳ |

**说明**: 3 个端点，退款、取消订阅、降级等敏感操作

---

### 3. Config (系统配置) ⏳

```bash
python -m pytest tests/integration/staging/admin/config/ -v --tb=short
```

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

**说明**: 8 个端点，配置查询/更新、Rate Limit 管理、缓存清理

---

### 4. Tiers (Tier 配置管理) ⏳ 🆕

```bash
python -m pytest tests/integration/staging/admin/tiers/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/tiers` | GET | 30/min | ⏳ |
| `/api/v2/admin/tiers/{tier_code}` | GET | 30/min | ⏳ |
| `/api/v2/admin/tiers/{tier_code}` | PUT | 10/min | ⏳ |

**说明**: 3 个端点，Tier 配置查询/更新 (display_name, monthly_credits, max_projects, pricing, features)

**返回数据结构**:
```json
{
  "tiers": [
    {
      "tier_code": "t1",
      "display_name": "Free Plan",
      "enabled": true,
      "monthly_credits": 0,
      "max_projects": 1,
      "price_original": 0.0,
      "price_current": 0.0,
      "ai_queue_priority": "low",
      "topup_discount": 1.0,
      "features": { "pdf_export": true, "zip_export": "trial", ... }
    }
  ]
}
```

---

### 5. Feature Flags (功能开关) ⏳

> 注: 后续模块编号因新增 Tiers 模块而 +1

```bash
python -m pytest tests/integration/staging/admin/feature_flags/ -v --tb=short
```

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

**说明**: 9 个端点，Flag CRUD、开关控制、测试评估、审计日志

---

### 5. Asset Categories (素材分类) ⏳

```bash
python -m pytest tests/integration/staging/admin/asset_categories/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/asset-categories` | GET | - | ⏳ |
| `/api/v2/admin/asset-categories/tree` | GET | - | ⏳ |
| `/api/v2/admin/asset-categories` | POST | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}` | PATCH | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}/move` | PUT | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}` | DELETE | - | ⏳ |
| `/api/v2/admin/asset-categories/{slug}/resources` | GET | - | ⏳ |

**说明**: 7 个端点，分类 CRUD、树形结构、层级移动

---

### 6. Themes (主题管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/themes/ -v --tb=short
```

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

**说明**: 13 个端点，主题 CRUD、AI 批量生成、审核工作流

---

### 7. Campaigns (营销活动) ⏳

```bash
python -m pytest tests/integration/staging/admin/campaigns/ -v --tb=short
```

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

**说明**: 8 个端点，活动 CRUD、激活/暂停、统计

---

### 8. Experiments (A/B 实验) ⏳

```bash
python -m pytest tests/integration/staging/admin/experiments/ -v --tb=short
```

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

**说明**: 14 个端点，实验 CRUD、结果聚合、AI 分析、趋势

---

### 9. Events (事件分析) ⏳

```bash
python -m pytest tests/integration/staging/admin/events/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/events/events` | GET | 30/min | ⏳ |
| `/api/admin/events/events/stats` | GET | 30/min | ⏳ |
| `/api/admin/events/aggregated/{stat_type}` | GET | 30/min | ⏳ |
| `/api/admin/events/aggregated/{stat_type}/range` | GET | 30/min | ⏳ |
| `/api/admin/events/aggregation/run` | POST | 5/min | ⏳ |

**说明**: 5 个端点，用户事件查询、聚合统计

---

### 10. Stats (数据统计) ⏳

```bash
python -m pytest tests/integration/staging/admin/stats/ -v --tb=short
```

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

**说明**: 18 个端点，Dashboard KPI、用户增长、收入、转化漏斗等

---

### 11. Metrics (系统指标) ⏳

```bash
python -m pytest tests/integration/staging/admin/metrics/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/metrics/daily` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/monthly` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/retention` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/funnel` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/errors` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/dau-trend` | GET | 30/min | ⏳ |
| `/api/v2/admin/metrics/refresh` | POST | 5/min | ⏳ |

**说明**: 7 个端点，日/月指标、留存、漏斗、DAU 趋势

---

### 12. Logs (日志管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/logs/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/logs/errors` | GET | 30/min | ⏳ |
| `/api/v2/admin/logs/errors/stats` | GET | 30/min | ⏳ |
| `/api/v2/admin/logs/operations` | GET | 30/min | ⏳ |
| `/api/v2/admin/logs/operations/export` | GET | 10/min | ⏳ |
| `/api/v2/admin/logs/audit` | GET | 30/min | ⏳ |

**说明**: 5 个端点，错误日志、操作日志、审计日志

---

### 13. System (系统管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/system/ -v --tb=short
```

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

**说明**: 12 个端点，系统配置管理、Redis 缓存管理

---

### 14. Moderation (内容审核) ⏳

```bash
python -m pytest tests/integration/staging/admin/moderation/ -v --tb=short
```

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

**说明**: 10 个端点，市场审核、举报管理

---

### 15. Notifications (通知管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/notifications/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/notifications/broadcast` | POST | - | ⏳ |
| `/api/admin/notifications/notification/send` | POST | - | ⏳ |
| `/api/admin/notifications/notification/batch` | POST | - | ⏳ |
| `/api/admin/notifications/notification/stats` | GET | - | ⏳ |
| `/api/admin/notifications/notification/history` | GET | - | ⏳ |

**说明**: 5 个端点，广播、单发、批量发送、统计

---

### 16. AI Insights (AI 洞察) ⏳

```bash
python -m pytest tests/integration/staging/admin/ai/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/ai/insights` | GET | - | ⏳ |
| `/api/admin/ai/recommendations` | GET | - | ⏳ |
| `/api/admin/ai/behavior-analysis` | GET | - | ⏳ |
| `/api/admin/ai/generate-report` | POST | - | ⏳ |
| `/api/admin/ai/quick-insights` | GET | - | ⏳ |

**说明**: 5 个端点，AI 洞察、行为分析、报告生成

---

### 17. Static Pages (静态页面管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/static_pages/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/static-pages` | GET | - | ⏳ |
| `/api/v2/admin/static-pages/{id}` | GET | - | ⏳ |
| `/api/v2/admin/static-pages` | POST | - | ⏳ |
| `/api/v2/admin/static-pages/{id}` | PUT | - | ⏳ |
| `/api/v2/admin/static-pages/{id}` | DELETE | - | ⏳ |
| `/api/v2/admin/static-pages/{id}/publish` | POST | - | ⏳ |
| `/api/v2/admin/static-pages/{id}/unpublish` | POST | - | ⏳ |

**说明**: 7 个端点，静态页面 CRUD、发布/取消发布

---

### 18. Articles (文章管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/articles/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/articles` | GET | - | ⏳ |
| `/api/v2/admin/articles/{id}` | GET | - | ⏳ |
| `/api/v2/admin/articles` | POST | - | ⏳ |
| `/api/v2/admin/articles/{id}` | PUT | - | ⏳ |
| `/api/v2/admin/articles/{id}` | DELETE | - | ⏳ |
| `/api/v2/admin/articles/{id}/publish` | POST | - | ⏳ |
| `/api/v2/admin/articles/{id}/unpublish` | POST | - | ⏳ |

**说明**: 7 个端点，文章 CRUD、发布/取消发布

---

### 19. Webhooks (Webhook 重试) ⏳

```bash
python -m pytest tests/integration/staging/admin/webhooks/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/v2/admin/webhooks/retry` | POST | 10/hour | ⏳ |
| `/api/v2/admin/webhooks/failed` | GET | 30/min | ⏳ |

**说明**: 2 个端点，手动触发 Webhook 重试、查看失败事件

---

### 20. Tasks Management (任务管理) ⏳

```bash
python -m pytest tests/integration/staging/admin/tasks/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/tasks/management/status` | GET | - | ⏳ |
| `/api/admin/tasks/management/logs` | GET | - | ⏳ |
| `/api/admin/tasks/management/health` | GET | - | ⏳ |
| `/api/admin/tasks/management/{task_name}/run` | POST | - | ⏳ |

**说明**: 4 个端点，后台任务状态、日志、手动触发

---

### 21. User Creation Monitoring (用户创建监控) ⏳

```bash
python -m pytest tests/integration/staging/admin/monitoring/ -v --tb=short
```

| 端点 | 方法 | Rate Limit | 状态 |
|------|------|------------|------|
| `/api/admin/monitoring/user-creation/stats` | GET | - | ⏳ |
| `/api/admin/monitoring/user-creation/health` | GET | - | ⏳ |
| `/api/admin/monitoring/user-creation/events` | GET | - | ⏳ |

**说明**: 3 个端点，用户创建统计、健康检查、事件列表

---

## 推荐测试顺序

### 第一批 - 核心管理 (建议优先)

1. ⏳ **Users** - 用户管理 (12 端点)
2. ⏳ **Subscriptions** - 订阅管理 (3 端点)
3. ⏳ **Config** - 系统配置 (8 端点)
4. ⏳ **Tiers** - Tier 配置管理 (3 端点) 🆕
5. ⏳ **Feature Flags** - 功能开关 (9 端点)

### 第二批 - 数据分析

6. ⏳ **Stats** - 数据统计 (18 端点)
7. ⏳ **Metrics** - 系统指标 (7 端点)
8. ⏳ **Events** - 事件分析 (5 端点)
9. ⏳ **Experiments** - A/B 实验 (14 端点)

### 第三批 - 内容管理

10. ⏳ **Asset Categories** - 素材分类 (7 端点)
11. ⏳ **Themes** - 主题管理 (13 端点)
12. ⏳ **Static Pages** - 静态页面 (7 端点)
13. ⏳ **Articles** - 文章管理 (7 端点)

### 第四批 - 运营功能

14. ⏳ **Campaigns** - 营销活动 (8 端点)
15. ⏳ **Moderation** - 内容审核 (10 端点)
16. ⏳ **Notifications** - 通知管理 (5 端点)

### 第五批 - 系统运维

17. ⏳ **System** - 系统管理 (12 端点)
18. ⏳ **Logs** - 日志管理 (5 端点)
19. ⏳ **Tasks Management** - 任务管理 (4 端点)
20. ⏳ **Webhooks** - Webhook 重试 (2 端点)
21. ⏳ **Monitoring** - 用户监控 (3 端点)
22. ⏳ **AI Insights** - AI 洞察 (5 端点)

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

> 🆕 v1.1 (2026-01-20): 新增 Tiers 模块 (3 端点)

---

## 注意事项

### 敏感操作

以下端点涉及敏感操作，测试时需谨慎:

| 端点 | 风险级别 | 说明 |
|------|----------|------|
| `POST /subscriptions/refund` | 🔴 极高 | 退款操作 |
| `POST /subscriptions/subscription/cancel` | 🔴 极高 | 取消订阅 |
| `POST /users/{id}/credits` | 🔴 极高 | 积分调整 |
| `POST /system/cache/clear-all` | 🔴 极高 | 清空所有缓存 |
| `DELETE /experiments/{key}` | 🟠 高 | 删除实验 |
| `DELETE /campaigns/{id}` | 🟠 高 | 删除活动 |

### Rate Limit 说明

- 大多数查询接口: 30/minute
- 修改操作: 10/minute
- 敏感操作 (如缓存清空): 5/minute 或更低
- Webhook 重试: 10/hour (资源密集型)

### DDD 架构

所有 Admin API 都遵循 Container-based DI 架构:

```
API → Container → Service → Repository
```

测试时确保:
1. Service 层正确调用
2. Repository 返回正确数据格式
3. 审计日志正确记录

---

**文档版本**: v1.1
**更新日期**: 2026-01-20
**变更记录**: 新增 Tiers (Tier 配置管理) 模块，共 3 个端点
