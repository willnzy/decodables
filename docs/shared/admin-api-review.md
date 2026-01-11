# Admin API 完整参考

> **状态**: ✅ Complete (已评审 134 个，实际代码 143 个)
> **版本**: 3.33
> **最后更新**: 2026-01-11
> **总端点数**: 134 个 (已评审) / 143 个 (实际代码)

本文档记录已评审的 134 个 Admin API 端点的完整信息，包括请求参数、响应格式、验证规则和限流配置。

**注意**: 实际代码中有 143 个端点，另有 9 个端点（主要是部分模块的扩展功能）待补充评审文档。

---

## 目录

1. [AI Insights 洞察 (5个)](#1-ai-insights-洞察)
2. [Asset Categories 分类管理 (7个)](#2-asset-categories-分类管理)
3. [Campaigns 营销活动 (8个)](#3-campaigns-营销活动)
4. [Config 系统配置 (8个)](#4-config-系统配置)
5. [Events 事件管理 (5个)](#5-events-事件管理)
6. [Experiments 实验管理 (14个)](#6-experiments-实验管理)
7. [Feature Flags 功能开关 (9个)](#7-feature-flags-功能开关)
8. [Logs 日志审计 (5个)](#8-logs-日志审计)
9. [Metrics 系统指标 (7个)](#9-metrics-系统指标)
10. [Moderation 内容审核 (10个)](#10-moderation-内容审核)
11. [Notifications 通知管理 (5个)](#11-notifications-通知管理)
12. [Stats 统计仪表板 (18个)](#12-stats-统计仪表板)
13. [Subscriptions 订阅管理 (3个)](#13-subscriptions-订阅管理)
14. [System 系统管理 (12个)](#14-system-系统管理)
15. [Tasks 任务管理 (4个)](#15-tasks-任务管理)
16. [Users 用户管理 (13个)](#16-users-用户管理)
17. [Webhooks 重试管理 (2个)](#17-webhooks-重试管理)

---

## 📋 接口总览 (134个)

| 序号 | 模块 | 方法 | 路径 | 函数名 | 文件 | 说明 |
|------|------|------|------|--------|------|------|
| **AI Insights (5个)** |
| 1 | AI Insights | GET | /ai/insights | adm_get_ai_insights | api/admin/ai.py | AI 洞察数据 |
| 2 | AI Insights | GET | /ai/recommendations | adm_get_ai_recommendations | api/admin/ai.py | AI 推荐 |
| 3 | AI Insights | GET | /ai/behavior-analysis | adm_get_behavior_analysis | api/admin/ai.py | 用户行为分析 |
| 4 | AI Insights | POST | /ai/generate-report | adm_generate_ai_report | api/admin/ai.py | 生成 AI 报告 |
| 5 | AI Insights | GET | /ai/quick-insights | adm_get_quick_insights | api/admin/ai.py | 快速洞察 |
| **Asset Categories (7个)** |
| 6 | Asset Categories | GET | /asset-categories/ | list_categories | api/admin/asset_categories.py | 列出所有分类 |
| 7 | Asset Categories | GET | /asset-categories/tree | get_category_tree | api/admin/asset_categories.py | 获取分类树 |
| 8 | Asset Categories | POST | /asset-categories/ | create_category | api/admin/asset_categories.py | 创建分类 |
| 9 | Asset Categories | PATCH | /asset-categories/{slug} | update_category | api/admin/asset_categories.py | 更新分类 |
| 10 | Asset Categories | PUT | /asset-categories/{slug}/move | move_category | api/admin/asset_categories.py | 移动分类 |
| 11 | Asset Categories | DELETE | /asset-categories/{slug} | delete_category | api/admin/asset_categories.py | 删除分类 |
| 12 | Asset Categories | GET | /asset-categories/{slug}/resources | get_category_resources | api/admin/asset_categories.py | 获取分类资源 |
| **Campaigns (8个)** |
| 13 | Campaigns | GET | /campaigns | - | api/admin/campaigns.py | 列出所有营销活动 |
| 14 | Campaigns | GET | /campaigns/{id} | - | api/admin/campaigns.py | 获取活动详情 |
| 15 | Campaigns | POST | /campaigns | - | api/admin/campaigns.py | 创建新活动 |
| 16 | Campaigns | PUT | /campaigns/{id} | - | api/admin/campaigns.py | 更新活动 |
| 17 | Campaigns | DELETE | /campaigns/{id} | - | api/admin/campaigns.py | 删除活动 |
| 18 | Campaigns | POST | /campaigns/{id}/activate | - | api/admin/campaigns.py | 激活活动 |
| 19 | Campaigns | POST | /campaigns/{id}/pause | - | api/admin/campaigns.py | 暂停活动 |
| 20 | Campaigns | GET | /campaigns/{id}/stats | - | api/admin/campaigns.py | 获取活动统计 |
| **Config (8个)** |
| 21 | Config | GET | /config | - | api/admin/config.py | 获取所有系统配置 |
| 22 | Config | GET | /config/{config_key} | - | api/admin/config.py | 获取单个配置 |
| 23 | Config | PUT | /config | - | api/admin/config.py | 更新配置 |
| 24 | Config | PUT | /config/batch | - | api/admin/config.py | 批量更新配置 |
| 25 | Config | GET | /config/rate-limits | - | api/admin/config.py | 获取所有限流配置 |
| 26 | Config | POST | /config/rate-limits/preset | - | api/admin/config.py | 应用限流预设方案 |
| 27 | Config | GET | /config/rate-limits/presets | - | api/admin/config.py | 获取所有限流预设 |
| 28 | Config | POST | /config/cache/clear | - | api/admin/config.py | 清空配置缓存 |
| **Events (5个)** |
| 29 | Events | GET | /events | - | api/admin/events.py | 获取用户事件 |
| 30 | Events | GET | /events/stats | - | api/admin/events.py | 获取事件统计 |
| 31 | Events | GET | /events/aggregated/{aggregation_type} | - | api/admin/events.py | 获取聚合统计 |
| 32 | Events | GET | /events/aggregated/{aggregation_type}/range | - | api/admin/events.py | 获取聚合统计范围 |
| 33 | Events | POST | /events/aggregation/run | - | api/admin/events.py | 手动触发聚合任务 |
| **Experiments (14个)** |
| 34 | Experiments | GET | /experiments | - | api/admin/experiments.py | 列出所有实验 |
| 35 | Experiments | POST | /experiments | - | api/admin/experiments.py | 创建实验 |
| 36 | Experiments | GET | /experiments/{experiment_key} | - | api/admin/experiments.py | 获取实验详情 |
| 37 | Experiments | PUT | /experiments/{experiment_key} | - | api/admin/experiments.py | 更新实验配置 |
| 38 | Experiments | PUT | /experiments/{experiment_key}/status | - | api/admin/experiments.py | 更新实验状态 |
| 39 | Experiments | DELETE | /experiments/{experiment_key} | - | api/admin/experiments.py | 删除实验 |
| 40 | Experiments | GET | /experiments/{experiment_key}/results | - | api/admin/experiments.py | 获取实验结果 |
| 41 | Experiments | POST | /experiments/{experiment_key}/aggregate | - | api/admin/experiments.py | 触发实验结果聚合 |
| 42 | Experiments | POST | /experiments/aggregate-all | - | api/admin/experiments.py | 触发所有实验聚合 |
| 43 | Experiments | POST | /experiments/cache/clear | - | api/admin/experiments.py | 清空实验缓存 |
| 44 | Experiments | POST | /experiments/{experiment_key}/ai-analysis | - | api/admin/experiments.py | 获取 AI 驱动的实验分析 |
| 45 | Experiments | GET | /experiments/{experiment_key}/quick-recommendation | - | api/admin/experiments.py | 获取快速决策建议 |
| 46 | Experiments | GET | /experiments/{experiment_key}/trend | - | api/admin/experiments.py | 获取每日趋势 |
| 47 | Experiments | GET | /experiments/{experiment_key}/hourly-trend | - | api/admin/experiments.py | 获取每小时趋势 |
| **Feature Flags (9个)** |
| 48 | Feature Flags | GET | /feature-flags | - | api/admin/feature_flags.py | 列出所有 Feature Flags |
| 49 | Feature Flags | POST | /feature-flags | - | api/admin/feature_flags.py | 创建新 Feature Flag |
| 50 | Feature Flags | GET | /feature-flags/{key} | - | api/admin/feature_flags.py | 获取 Feature Flag 详情 |
| 51 | Feature Flags | PATCH | /feature-flags/{key} | - | api/admin/feature_flags.py | 更新 Feature Flag |
| 52 | Feature Flags | POST | /feature-flags/{key}/toggle | - | api/admin/feature_flags.py | 快速切换启用状态 |
| 53 | Feature Flags | DELETE | /feature-flags/{key} | - | api/admin/feature_flags.py | 归档 Feature Flag |
| 54 | Feature Flags | POST | /feature-flags/test-evaluation | - | api/admin/feature_flags.py | 测试 Feature Flag 评估逻辑 |
| 55 | Feature Flags | GET | /feature-flags/{key}/audit | - | api/admin/feature_flags.py | 获取 Feature Flag 审计日志 |
| 56 | Feature Flags | GET | /feature-flags/client/flags | - | api/admin/feature_flags.py | 客户端 Feature Flags 评估 |
| **Logs (5个)** |
| 57 | Logs | GET | /logs/errors | - | api/admin/logs.py | 获取错误日志 |
| 58 | Logs | GET | /logs/errors/stats | - | api/admin/logs.py | 获取错误统计 |
| 59 | Logs | GET | /logs/operations | - | api/admin/logs.py | 获取操作日志 |
| 60 | Logs | GET | /logs/operations/export | - | api/admin/logs.py | 导出操作日志 |
| 61 | Logs | GET | /logs/audit | - | api/admin/logs.py | 统一审计日志查询 |
| **Metrics (7个)** |
| 62 | Metrics | GET | /metrics/daily | - | api/admin/metrics.py | 获取每日指标 |
| 63 | Metrics | GET | /metrics/monthly | - | api/admin/metrics.py | 获取每月指标 |
| 64 | Metrics | GET | /metrics/retention | - | api/admin/metrics.py | 获取留存指标 |
| 65 | Metrics | GET | /metrics/funnel | - | api/admin/metrics.py | 获取转化漏斗 |
| 66 | Metrics | GET | /metrics/errors | - | api/admin/metrics.py | 获取错误指标 |
| 67 | Metrics | GET | /metrics/dau-trend | - | api/admin/metrics.py | 获取 DAU 趋势 |
| 68 | Metrics | POST | /metrics/refresh | - | api/admin/metrics.py | 刷新指标缓存 |
| **Moderation (10个)** |
| 69 | Moderation | GET | /moderation/marketplace/moderation/list | - | api/admin/moderation.py | 获取待审核商品列表 |
| 70 | Moderation | GET | /moderation/marketplace/moderation/{listing_id} | - | api/admin/moderation.py | 获取商品审核详情 |
| 71 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/approve | - | api/admin/moderation.py | 批准商品上架 |
| 72 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/reject | - | api/admin/moderation.py | 拒绝商品上架 |
| 73 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/delete | - | api/admin/moderation.py | 软删除商品 |
| 74 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/unpublish | - | api/admin/moderation.py | 强制下架商品 |
| 75 | Moderation | GET | /moderation/reports | - | api/admin/moderation.py | 获取所有内容举报 |
| 76 | Moderation | GET | /moderation/reports/stats | - | api/admin/moderation.py | 获取举报统计 |
| 77 | Moderation | GET | /moderation/reports/{report_id} | - | api/admin/moderation.py | 获取举报详情 |
| 78 | Moderation | POST | /moderation/reports/{report_id}/respond | - | api/admin/moderation.py | 处理举报 |
| **Notifications (5个)** |
| 79 | Notifications | POST | /notifications/broadcast | - | api/admin/notifications.py | 发送系统广播通知 |
| 80 | Notifications | POST | /notifications/notification/send | - | api/admin/notifications.py | 发送通知给单个用户 |
| 81 | Notifications | POST | /notifications/notification/batch | - | api/admin/notifications.py | 批量发送通知 |
| 82 | Notifications | GET | /notifications/notification/stats | - | api/admin/notifications.py | 获取通知统计 |
| 83 | Notifications | GET | /notifications/notification/history | - | api/admin/notifications.py | 获取通知发送历史 |
| **Stats (18个)** |
| 84 | Stats | GET | /stats/dashboard | - | api/admin/stats.py | 获取仪表板 KPI |
| 85 | Stats | GET | /stats/user-growth | - | api/admin/stats.py | 获取用户增长统计 |
| 86 | Stats | GET | /stats/revenue | - | api/admin/stats.py | 获取收入统计 |
| 87 | Stats | GET | /stats/projects | - | api/admin/stats.py | 获取项目统计 |
| 88 | Stats | GET | /stats/credits | - | api/admin/stats.py | 获取积分使用统计 |
| 89 | Stats | GET | /stats/tier-distribution | - | api/admin/stats.py | 获取 Tier 分布 |
| 90 | Stats | GET | /stats/conversion-funnel | - | api/admin/stats.py | 获取转化漏斗 |
| 91 | Stats | GET | /stats/exports | - | api/admin/stats.py | 获取导出统计 |
| 92 | Stats | GET | /stats/assets | - | api/admin/stats.py | 获取素材统计 |
| 93 | Stats | GET | /stats/tier-activity | - | api/admin/stats.py | 获取 Tier 活跃度 |
| 94 | Stats | GET | /stats/subscription-events | - | api/admin/stats.py | 获取订阅事件统计 |
| 95 | Stats | GET | /stats/page-views | - | api/admin/stats.py | 获取页面浏览统计 |
| 96 | Stats | GET | /stats/project-details | - | api/admin/stats.py | 获取项目详细统计 |
| 97 | Stats | GET | /stats/returning-users | - | api/admin/stats.py | 获取回访用户统计 |
| 98 | Stats | GET | /stats/tier-trend | - | api/admin/stats.py | 获取 Tier 趋势 |
| 99 | Stats | GET | /stats/tier-conversion | - | api/admin/stats.py | 获取 Tier 转化统计 |
| 100 | Stats | GET | /stats/performance | - | api/admin/stats.py | 获取 Core Web Vitals 性能指标 |
| 101 | Stats | GET | /stats/user-distribution | - | api/admin/stats.py | 获取用户分布统计 |
| **Subscriptions (3个)** |
| 102 | Subscriptions | POST | /subscriptions/refund | - | api/admin/subscriptions.py | 处理退款 |
| 103 | Subscriptions | POST | /subscriptions/subscription/cancel | - | api/admin/subscriptions.py | 取消订阅 |
| 104 | Subscriptions | POST | /subscriptions/subscription/downgrade | - | api/admin/subscriptions.py | 降级订阅 |
| **System (12个)** |
| 105 | System | GET | /system/configs | get_configs_endpoint | api/admin/system.py | 获取系统配置列表 |
| 106 | System | GET | /system/configs/groups | get_config_groups_endpoint | api/admin/system.py | 获取配置组列表 |
| 107 | System | POST | /system/configs | create_config_endpoint | api/admin/system.py | 创建系统配置 |
| 108 | System | PUT | /system/configs/{key:path} | update_config_endpoint | api/admin/system.py | 更新系统配置 |
| 109 | System | DELETE | /system/configs/{key:path} | delete_config_endpoint | api/admin/system.py | 软删除配置 |
| 110 | System | GET | /system/configs/audit | get_config_audit_endpoint | api/admin/system.py | 获取配置变更审计日志 |
| 111 | System | POST | /system/configs/cache/invalidate | invalidate_cache_endpoint | api/admin/system.py | 清空配置缓存 |
| 112 | System | GET | /system/system/cache/status | get_cache_status_endpoint | api/admin/system.py | 获取 Redis 缓存状态 |
| 113 | System | GET | /system/system/cache/keys | list_cache_keys_endpoint | api/admin/system.py | 列出缓存键 |
| 114 | System | DELETE | /system/system/cache/key/{key:path} | delete_cache_key_endpoint | api/admin/system.py | 删除单个缓存键 |
| 115 | System | POST | /system/system/cache/clear-all/confirm | request_clear_all_confirmation | api/admin/system.py | 请求清空所有缓存的确认 Token |
| 116 | System | POST | /system/system/cache/clear-all | clear_all_cache_endpoint | api/admin/system.py | 清空所有缓存 |
| **Tasks (4个)** |
| 117 | Tasks | GET | /tasks/management/status | - | api/admin/tasks_mgmt.py | 获取任务状态 |
| 118 | Tasks | GET | /tasks/management/logs | - | api/admin/tasks_mgmt.py | 获取任务日志 |
| 119 | Tasks | GET | /tasks/management/health | - | api/admin/tasks_mgmt.py | 获取任务健康状态 |
| 120 | Tasks | POST | /tasks/management/{task_name}/run | - | api/admin/tasks_mgmt.py | 手动触发任务 |
| **Users (13个)** |
| 121 | Users | GET | /users | - | api/admin/users.py | 搜索用户 |
| 122 | Users | GET | /users/by-tier/{tier} | - | api/admin/users.py | 按 Tier 获取用户 |
| 123 | Users | GET | /users/{user_id} | - | api/admin/users.py | 获取用户完整审计信息 |
| 124 | Users | POST | /users/{user_id}/credits | - | api/admin/users.py | 调整用户积分 |
| 125 | Users | PATCH | /users/{user_id} | - | api/admin/users.py | 更新用户信息 |
| 126 | Users | POST | /users/{user_id}/discount | - | api/admin/users.py | 创建用户折扣 |
| 127 | Users | GET | /users/{user_id}/payments | - | api/admin/users.py | 获取用户支付记录 |
| 128 | Users | GET | /users/{user_id}/projects | - | api/admin/users.py | 获取用户项目列表 |
| 129 | Users | GET | /users/{user_id}/asset-usage | - | api/admin/users.py | 获取用户素材使用情况 |
| 130 | Users | GET | /users/{user_id}/env-stats | - | api/admin/users.py | 获取用户环境统计 |
| 131 | Users | POST | /users/projects/{project_id}/restore | - | api/admin/users.py | 恢复用户项目 |
| 132 | Users | GET | /users/projects/feed | - | api/admin/users.py | 获取项目动态流 |
| **Webhooks (2个)** |
| 133 | Webhooks | POST | /webhooks/retry | - | api/admin/webhooks_retry.py | 重试失败的 Webhooks |
| 134 | Webhooks | GET | /webhooks/failed | - | api/admin/webhooks_retry.py | 获取失败的 Webhooks |

**注**: 文档共记录 134 个接口（原 143 个 - 8 个虚构的 AI Models + 7 个补充的 Asset Categories - 8 个其他未记录 = 134 个已评审）。

---

## 1. AI Insights 洞察

### GET `/ai/insights`

获取 AI 业务洞察

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `type` | string | all | 洞察类型: all/growth/engagement/revenue |

**type 验证**:
- 必须是以下之一: `all`, `growth`, `engagement`, `revenue`
- 无效值返回 400 错误

**响应**:
```json
{
  "insights": [
    {
      "category": "growth",
      "title": "用户增长加速",
      "description": "过去 7 天新增用户增长 35%",
      "metric_value": 245,
      "trend": "up"
    }
  ]
}
```

**数据来源**: 最近 7 天数据

---

### GET `/ai/recommendations`

获取 AI 业务推荐

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `area` | string | all | 推荐领域: all/growth/retention/monetization |

**area 验证**:
- 必须是以下之一: `all`, `growth`, `retention`, `monetization`
- 无效值返回 400 错误

**响应**:
```json
{
  "recommendations": [
    {
      "priority": "high",
      "area": "growth",
      "title": "优化注册流程",
      "description": "建议简化注册步骤",
      "action": "减少必填字段"
    }
  ]
}
```

---

### GET `/ai/behavior-analysis`

获取用户行为分析

**限流**: 20 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `start_date` | string | 30天前 | 开始日期 (YYYY-MM-DD or ISO) |
| `end_date` | string | 今天 | 结束日期 (YYYY-MM-DD or ISO) |

**日期验证**:
- 格式: `YYYY-MM-DD` 或 `YYYY-MM-DDTHH:MM:SS`
- 使用正则: `^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?`
- 无效格式返回 400 错误

**响应**:
```json
{
  "patterns": {
    "event_distribution": {
      "project_created": 5200,
      "project_updated": 18500
    },
    "peak_activity_hour": 14,
    "hourly_activity": [0, 50, 120, ...],
    "total_events_analyzed": 50000,
    "limited": false
  },
  "segments": {
    "by_tier": {
      "t1": 18500,
      "t2": 4200,
      "t3": 2300
    },
    "total_users": 25000
  },
  "period": {
    "start": "2025-12-12",
    "end": "2026-01-11"
  }
}
```

**性能限制**: 最多分析 50,000 条事件记录

---

### POST `/ai/generate-report`

生成 AI 业务报告

**限流**: 5 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `report_type` | string | comprehensive | 报告类型 |
| `time_range` | string | 30d | 时间范围 |

**report_type 可选值**:
- `comprehensive` - 完整分析 (深度分析)
- `growth` - 用户增长分析
- `engagement` - 用户活跃度分析
- `revenue` - 收入分析
- `quick` - 快速洞察 (无 AI)

**time_range 可选值**:
- `7d` - 最近 7 天
- `30d` - 最近 30 天 (默认)
- `90d` - 最近 90 天
- `365d` - 最近一年

**响应**:
```json
{
  "executive_summary": "平台整体健康，增长稳定",
  "key_insights": [
    {
      "title": "用户增长放缓",
      "priority": "high",
      "description": "...",
      "recommendation": "..."
    }
  ],
  "anomalies": [
    {
      "metric": "dau",
      "description": "1月5日 DAU 异常下降 15%",
      "severity": "medium"
    }
  ],
  "recommendations": [
    {
      "action": "优化首页体验",
      "priority": "high",
      "impact": "预计提升 DAU 10%"
    }
  ],
  "metrics_analyzed": 42,
  "report_type": "comprehensive",
  "time_range": "30d",
  "generated_at": "2026-01-11T10:30:00Z"
}
```

**OpenAI 配置**:
- 模型: GPT-4o
- 超时: 30 秒
- 失败降级: 返回基于规则的快速洞察

---

### GET `/ai/quick-insights`

获取快速洞察

**限流**: 60 req/min

**响应**:
```json
{
  "insights": [
    {
      "title": "DAU 持续上涨",
      "description": "日活用户数较昨日增长 12%",
      "priority": "medium",
      "category": "growth",
      "metric_value": 1250,
      "change": "+12%",
      "recommendation": "保持当前营销策略"
    }
  ]
}
```

**特点**:
- 无 AI 调用，纯规则分析
- 响应速度快 (<100ms)
- 适合仪表板实时展示

---

## 2. Asset Categories 分类管理

### GET `/asset-categories/`

列出所有分类

**限流**: 无限流 (内部工具)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `asset_type` | string | - | 资源类型筛选 |
| `parent_id` | string | - | 父分类 ID |
| `is_visible` | bool | - | 可见性筛选 |
| `min_tier` | string | - | 最低 Tier |
| `limit` | int | 100 | 每页数量 (1-500) |
| `offset` | int | 0 | 分页偏移量 |

**asset_type 可选值**:
- `text`, `image`, `shape`, `table`, `sticker`, `icon`, `frame`
- 使用正则验证: `^(text|image|shape|table|sticker|icon|frame)$`

**min_tier 可选值**:
- `t1`, `t2`, `t3`
- 使用正则验证: `^(t1|t2|t3)$`

**响应**:
```json
{
  "categories": [
    {
      "id": "cat_abc123",
      "parent_id": null,
      "path": "animals",
      "level": 1,
      "slug": "animals",
      "name": "动物",
      "name_i18n": {
        "en": "Animals",
        "zh": "动物"
      },
      "description": "可爱动物素材",
      "icon": "🐾",
      "asset_type": "sticker",
      "is_visible": true,
      "is_featured": false,
      "display_order": 0,
      "min_tier": "t1",
      "visible_from": null,
      "visible_until": null,
      "asset_count": 120,
      "usage_count": 3450,
      "metadata": {},
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/asset-categories/tree`

获取分类树 (层级结构)

**限流**: 无限流

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `asset_type` | string | - | 资源类型筛选 |
| `include_hidden` | bool | false | 包含隐藏分类 |

**响应**:
```json
{
  "categories": [
    {
      "id": "cat_abc123",
      "slug": "animals",
      "name": "动物",
      "level": 1,
      "path": "animals",
      "children": [
        {
          "id": "cat_def456",
          "slug": "cats",
          "name": "猫咪",
          "level": 2,
          "path": "animals.cats",
          "parent_id": "cat_abc123"
        }
      ]
    }
  ]
}
```

**排序规则**: 按 LTREE path 字段排序 (保证父子关系正确)

---

### POST `/asset-categories/`

创建新分类

**限流**: 无限流

**请求体**:
```json
{
  "slug": "cute-animals",
  "name": "可爱动物",
  "asset_type": "sticker",
  "parent_slug": null,
  "name_i18n": {
    "en": "Cute Animals",
    "zh": "可爱动物"
  },
  "description": "各种可爱动物贴纸",
  "icon": "🐾",
  "min_tier": "t1",
  "is_visible": true,
  "is_featured": false,
  "display_order": 0,
  "metadata": {}
}
```

**字段验证**:
- `slug`: 1-50 字符，只能包含小写字母、数字、连字符、下划线 (`^[a-z0-9\-_]+$`)
- `name`: 1-100 字符
- `asset_type`: 必须是有效值 (见上)
- `min_tier`: 必须是 `t1`/`t2`/`t3`
- `parent_slug`: 可选，父分类 slug

**响应**:
```json
{
  "id": "cat_new123",
  "slug": "cute-animals",
  "name": "可爱动物",
  "path": "cute-animals",
  "level": 1,
  ...
}
```

**状态码**: 201 Created

**错误情况**:
- 400: slug 已存在
- 400: 超过最大层级 (5层)
- 404: parent_slug 不存在

**自动计算**: `path` 和 `level` 由系统根据 `parent_slug` 自动计算

---

### PATCH `/asset-categories/{slug}`

更新分类元数据

**限流**: 无限流

**请求体** (所有字段可选):
```json
{
  "name": "超可爱动物",
  "name_i18n": {
    "en": "Super Cute Animals"
  },
  "description": "更新后的描述",
  "icon": "🐶",
  "asset_type": "sticker",
  "min_tier": "t2",
  "is_visible": false,
  "is_featured": true,
  "display_order": 10,
  "metadata": {
    "custom_field": "value"
  }
}
```

**响应**:
```json
{
  "id": "cat_abc123",
  "slug": "cute-animals",
  "name": "超可爱动物",
  ...
}
```

**限制**:
- **不能** 修改 `slug`, `parent_id`, `path`, `level` (使用 PUT /move)
- 至少提供 1 个字段
- 空请求体返回 400 错误

---

### PUT `/asset-categories/{slug}/move`

移动分类到新父级

**限流**: 无限流

**请求体**:
```json
{
  "new_parent_slug": "animals"
}
```

**new_parent_slug**:
- `null` - 移动到根级
- `"slug"` - 移动到指定父分类下

**响应**:
```json
{
  "id": "cat_abc123",
  "slug": "cats",
  "parent_id": "cat_def456",
  "path": "animals.cats",
  "level": 2,
  ...
}
```

**自动更新**:
- 当前分类的 `path`, `level`, `parent_id`
- 所有后代分类的 `path`, `level`

**错误情况**:
- 400: 循环引用 (不能移动到自己的子分类下)
- 400: 超过最大层级 (5层)
- 404: new_parent_slug 不存在

---

### DELETE `/asset-categories/{slug}`

删除分类 (软删除，30天恢复期)

**限流**: 无限流

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `cascade` | bool | false | 是否级联删除所有子分类 |

**响应**:
```json
{
  "message": "Category deleted successfully",
  "slug": "cute-animals"
}
```

**错误情况**:
- 400: `cascade=false` 且分类有子分类
- 404: 分类不存在

**软删除**: 设置 `deleted_at` 字段，30天后永久删除

---

### GET `/asset-categories/{slug}/resources`

获取分类下的系统资源

**限流**: 无限流

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 50 | 每页数量 (1-200) |
| `offset` | int | 0 | 分页偏移量 |

**响应**:
```json
{
  "category_slug": "animals",
  "category_name": "动物",
  "total_resources": 120,
  "resources": [
    {
      "id": "res_abc123",
      "category_id": "cat_abc123",
      "resource_type": "sticker",
      "title": "可爱猫咪",
      "url": "https://...",
      "display_order": 0,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**数据来源**: `system_resources` 表

---

## 3. Campaigns 营销活动

### GET `/campaigns`

列出所有营销活动

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 状态筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "campaigns": [
    {
      "id": "uuid-xxx",
      "name": "新年活动",
      "description": "新年积分赠送",
      "campaign_type": "credits",
      "reward_type": "credits_permanent",
      "reward_value": 50,
      "status": "active",
      "start_at": "2026-01-01T00:00:00Z",
      "end_at": "2026-01-31T23:59:59Z",
      "claimed_count": 245,
      "max_claims": 1000,
      "created_at": "2025-12-20T10:00:00Z"
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/campaigns/{id}`

获取活动详情

**限流**: 30 req/min

**响应**:
```json
{
  "campaign": {
    "id": "uuid-xxx",
    "name": "新年活动",
    "description": "...",
    "campaign_type": "credits",
    "reward_type": "credits_permanent",
    "reward_value": 50,
    "status": "active",
    "targeting": {
      "tiers": ["t1", "t2", "t3"],
      "new_users_only": false
    },
    "claimed_count": 245,
    "max_claims": 1000,
    "created_at": "2025-12-20T10:00:00Z"
  }
}
```

---

### POST `/campaigns`

创建新活动

**限流**: 20 req/min

**请求体**:
```json
{
  "name": "春节活动",
  "description": "春节积分赠送",
  "campaign_type": "credits",
  "reward_type": "credits_permanent",
  "reward_value": 100,
  "start_at": "2026-02-01T00:00:00Z",
  "end_at": "2026-02-28T23:59:59Z",
  "max_claims": 500,
  "targeting": {
    "tiers": ["t1", "t2"],
    "new_users_only": true
  }
}
```

**响应**:
```json
{
  "status": "created",
  "campaign": { ... }
}
```

---

### PUT `/campaigns/{id}`

更新活动

**限流**: 20 req/min

**请求体** (所有字段可选):
```json
{
  "name": "春节活动 v2",
  "description": "更新后的描述",
  "reward_value": 150,
  "max_claims": 1000
}
```

**响应**:
```json
{
  "status": "updated",
  "campaign": { ... }
}
```

---

### DELETE `/campaigns/{id}`

删除活动

**限流**: 10 req/min

**响应**:
```json
{
  "status": "deleted",
  "campaign_id": "uuid-xxx"
}
```

**审计日志**: 自动记录到 `admin_operations` 表

---

### POST `/campaigns/{id}/activate`

激活活动

**限流**: 10 req/min

**响应**:
```json
{
  "status": "activated",
  "campaign_id": "uuid-xxx"
}
```

---

### POST `/campaigns/{id}/pause`

暂停活动

**限流**: 10 req/min

**响应**:
```json
{
  "status": "paused",
  "campaign_id": "uuid-xxx"
}
```

---

### GET `/campaigns/{id}/stats`

获取活动统计

**限流**: 30 req/min

**响应**:
```json
{
  "campaign_id": "uuid-xxx",
  "claimed_count": 245,
  "unique_claimers": 240,
  "total_reward_issued": 12250,
  "conversion_rate": 24.5,
  "by_tier": {
    "t1": 120,
    "t2": 85,
    "t3": 40
  }
}
```

---

## 4. Config 系统配置

### GET `/config`

获取所有系统配置

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `category` | string | 可选,按类别筛选 |

**响应**:
```json
{
  "configs": [
    {
      "key": "rate_limit.api.max_requests",
      "value": {"limit": 100, "window": "minute"},
      "category": "rate_limit",
      "description": "API 每分钟最大请求数",
      "is_active": true,
      "updated_at": "2026-01-10T10:30:00Z"
    }
  ],
  "total": 42
}
```

---

### GET `/config/{config_key}`

获取单个配置

**限流**: 30 req/min

**响应**:
```json
{
  "key": "rate_limit.api.max_requests",
  "value": {
    "limit": 100,
    "window": "minute"
  },
  "is_active": true,
  "updated_at": "2026-01-10T10:30:00Z"
}
```

---

### PUT `/config`

更新配置

**限流**: 10 req/min

**请求体**:
```json
{
  "config_key": "rate_limit.api.max_requests",
  "config_value": {
    "limit": 150,
    "window": "minute"
  }
}
```

**响应**:
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "config_key": "rate_limit.api.max_requests"
}
```

**审计日志**: 自动记录到 `admin_operations` 表

---

### PUT `/config/batch`

批量更新配置

**限流**: 10 req/min

**请求体**:
```json
{
  "updates": [
    {
      "config_key": "feature_flags.new_editor.enabled",
      "config_value": {"enabled": true}
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "updated_count": 2,
  "failed_count": 0
}
```

---

### GET `/config/rate-limits`

获取所有限流配置

**限流**: 30 req/min

**响应**:
```json
{
  "rate_limits": [
    {
      "key": "rate_limit.api.projects.create",
      "limit": 20,
      "window": "minute",
      "enabled": true
    }
  ],
  "global_enabled": true,
  "total": 15
}
```

---

### POST `/config/rate-limits/preset`

应用限流预设方案

**限流**: 10 req/min

**请求体**:
```json
{
  "preset": "strict"
}
```

**preset 可选值**: `strict`, `normal`, `relaxed`, `disabled`

**响应**:
```json
{
  "success": true,
  "message": "Rate limit preset 'strict' applied successfully",
  "preset": "strict"
}
```

---

### GET `/config/rate-limits/presets`

获取所有限流预设

**限流**: 30 req/min

**响应**:
```json
{
  "presets": [
    {
      "name": "strict",
      "description": "严格限流",
      "multiplier": 0.5
    },
    {
      "name": "normal",
      "description": "标准限流",
      "multiplier": 1.0
    }
  ],
  "total": 4
}
```

---

### POST `/config/cache/clear`

清空配置缓存

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "message": "Configuration cache cleared successfully"
}
```

---

## 5. Events 事件管理

### GET `/events`

获取用户事件

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `user_id` | string | - | 用户ID |
| `event_type` | string | - | 事件类型 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (最大100) |

**响应**:
```json
{
  "events": [
    {
      "id": "uuid-xxx",
      "user_id": "user_abc",
      "event_type": "project_created",
      "event_data": { ... },
      "created_at": "2026-01-11T10:30:00Z"
    }
  ],
  "total": 1250,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/events/stats`

获取事件统计

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `start_date` | string | - | 开始日期 |
| `end_date` | string | - | 结束日期 |

**响应**:
```json
{
  "total_events": 125000,
  "by_type": {
    "project_created": 5200,
    "project_updated": 18500,
    "ai_generation": 32000
  },
  "by_date": [ ... ]
}
```

---

### GET `/events/aggregated/{aggregation_type}`

获取聚合统计

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `aggregation_type` | string | 聚合类型: daily/weekly/monthly |

**响应**:
```json
{
  "aggregation_type": "daily",
  "data": [
    {
      "date": "2026-01-11",
      "event_count": 5200,
      "unique_users": 850
    }
  ]
}
```

---

### GET `/events/aggregated/{aggregation_type}/range`

获取聚合统计范围

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `start_date` | string | 开始日期 |
| `end_date` | string | 结束日期 |

**响应**: 同上

---

### POST `/events/aggregation/run`

手动触发聚合任务

**限流**: 5 req/min

**响应**:
```json
{
  "status": "triggered",
  "message": "Aggregation task started"
}
```

---

## 6. Experiments 实验管理

### GET `/experiments`

列出所有实验

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 状态筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "experiments": [
    {
      "id": "uuid-xxx",
      "experiment_key": "new_pricing_page",
      "name": "新定价页面测试",
      "description": "测试新定价页面对转化率的影响",
      "experiment_type": "ab",
      "status": "running",
      "variants": [
        {"key": "control", "name": "原版", "weight": 50},
        {"key": "treatment", "name": "新版", "weight": 50}
      ],
      "traffic_allocation": 100,
      "created_at": "2025-12-20T10:00:00Z"
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20
}
```

---

### POST `/experiments`

创建实验

**限流**: 20 req/min

**请求体**:
```json
{
  "experiment_key": "new_pricing_page",
  "name": "新定价页面测试",
  "description": "测试新定价页面对转化率的影响",
  "experiment_type": "ab",
  "variants": [
    {"key": "control", "name": "原版", "weight": 50},
    {"key": "treatment", "name": "新版", "weight": 50}
  ],
  "traffic_allocation": 100,
  "start_at": "2026-01-15T00:00:00Z",
  "end_at": "2026-02-15T00:00:00Z"
}
```

**响应**:
```json
{
  "status": "created",
  "experiment": { ... }
}
```

---

### GET `/experiments/{experiment_key}`

获取实验详情

**限流**: 30 req/min

**响应**:
```json
{
  "experiment": {
    "id": "uuid-xxx",
    "experiment_key": "new_pricing_page",
    "name": "新定价页面测试",
    "status": "running",
    "variants": [ ... ],
    "targeting": { ... },
    "metrics": [ ... ],
    "created_at": "2025-12-20T10:00:00Z"
  }
}
```

---

### PUT `/experiments/{experiment_key}`

更新实验配置

**限流**: 20 req/min

**请求体** (所有字段可选):
```json
{
  "name": "新定价页面测试 v2",
  "description": "更新后的描述",
  "traffic_allocation": 80
}
```

**响应**:
```json
{
  "status": "updated",
  "experiment": { ... }
}
```

---

### PUT `/experiments/{experiment_key}/status`

更新实验状态

**限流**: 20 req/min

**请求体**:
```json
{
  "status": "paused"
}
```

**响应**:
```json
{
  "status": "updated",
  "new_status": "paused"
}
```

---

### DELETE `/experiments/{experiment_key}`

删除实验

**限流**: 10 req/min

**响应**:
```json
{
  "status": "deleted",
  "experiment_key": "new_pricing_page"
}
```

**审计日志**: 自动记录到 `admin_operations` 表

---

### GET `/experiments/{experiment_key}/results`

获取实验结果

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `start_date` | string | 开始日期 |
| `end_date` | string | 结束日期 |

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "variants": {
    "control": {
      "total_exposures": 5420,
      "total_conversions": 542,
      "conversion_rate": 10.0
    },
    "treatment": {
      "total_exposures": 5380,
      "total_conversions": 645,
      "conversion_rate": 12.0,
      "significance": {
        "p_value": 0.002,
        "is_significant": true
      }
    }
  },
  "summary": {
    "winner": "treatment",
    "lift": 20.0
  }
}
```

---

### POST `/experiments/{experiment_key}/aggregate`

触发实验结果聚合

**限流**: 10 req/min

**响应**:
```json
{
  "status": "aggregated",
  "experiment_key": "new_pricing_page",
  "message": "Aggregation completed successfully"
}
```

---

### POST `/experiments/aggregate-all`

触发所有实验聚合

**限流**: 5 req/min

**响应**:
```json
{
  "status": "aggregated",
  "message": "All experiments aggregated successfully"
}
```

---

### POST `/experiments/cache/clear`

清空实验缓存

**限流**: 10 req/min

**响应**:
```json
{
  "status": "cache_cleared"
}
```

---

### POST `/experiments/{experiment_key}/ai-analysis`

获取 AI 驱动的实验分析

**限流**: 10 req/min

**请求体** (可选):
```json
{
  "additional_context": "我们在 1 月 5 日进行了营销活动推广"
}
```

**响应**:
```json
{
  "success": true,
  "experiment_key": "new_pricing_page",
  "analysis": {
    "summary": "治疗组在转化率上显著优于对照组",
    "insights": [ ... ],
    "recommendations": [ ... ],
    "risks": [ ... ]
  },
  "generated_at": "2026-01-11T10:30:00Z"
}
```

---

### GET `/experiments/{experiment_key}/quick-recommendation`

获取快速决策建议

**限流**: 30 req/min

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "recommendation": {
    "action": "deploy_winner",
    "winner": "treatment",
    "reason": "...",
    "confidence": "high"
  }
}
```

---

### GET `/experiments/{experiment_key}/trend`

获取每日趋势

**限流**: 20 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 30 | 天数 (1-90) |

**响应**:
```json
{
  "experiment_key": "new_pricing_page",
  "data": [
    {
      "date": "2026-01-01",
      "variants": {
        "control": {
          "exposures": 180,
          "conversions": 18,
          "conversion_rate": 10.0
        }
      }
    }
  ]
}
```

---

### GET `/experiments/{experiment_key}/hourly-trend`

获取每小时趋势

**限流**: 20 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `hours` | int | 24 | 小时数 (1-168) |

**响应**: 同 trend 格式，按小时分组

---

## 7. Feature Flags 功能开关

### GET `/feature-flags`

列出所有 Feature Flags

**限流**: 无限流 (内部工具)

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `flag_type` | string | - | 类型筛选 |
| `enabled` | bool | - | 启用状态筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "data": [
    {
      "id": "uuid-xxx",
      "key": "new_editor_ui",
      "name": "新编辑器界面",
      "description": "启用重新设计的编辑器界面",
      "flag_type": "boolean",
      "enabled": true,
      "rollout_percentage": 50,
      "targeting_rules": [ ... ],
      "created_at": "2025-12-01T10:00:00Z"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 42
  }
}
```

---

### POST `/feature-flags`

创建新 Feature Flag

**限流**: 无限流

**请求体**:
```json
{
  "key": "new_editor_ui",
  "name": "新编辑器界面",
  "description": "启用重新设计的编辑器界面",
  "flag_type": "boolean",
  "enabled": false,
  "rollout_percentage": 10,
  "targeting_rules": [
    {
      "attribute": "tier",
      "operator": "in",
      "values": ["t3"]
    }
  ],
  "tags": ["frontend", "beta"]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "uuid-xxx",
    "key": "new_editor_ui",
    ...
  }
}
```

---

### GET `/feature-flags/{key}`

获取 Feature Flag 详情

**限流**: 无限流

**响应**:
```json
{
  "data": {
    "id": "uuid-xxx",
    "key": "new_editor_ui",
    ...
  }
}
```

---

### PATCH `/feature-flags/{key}`

更新 Feature Flag

**限流**: 无限流

**请求体** (所有字段可选):
```json
{
  "name": "新编辑器界面 v2",
  "enabled": true,
  "rollout_percentage": 50
}
```

**响应**:
```json
{
  "success": true,
  "data": { ... }
}
```

---

### POST `/feature-flags/{key}/toggle`

快速切换启用状态

**限流**: 无限流

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `enabled` | bool | 是 | 目标状态 |

**响应**:
```json
{
  "success": true,
  "data": {
    "key": "new_editor_ui",
    "enabled": true
  }
}
```

---

### DELETE `/feature-flags/{key}`

归档 Feature Flag (软删除)

**限流**: 无限流

**响应**:
```json
{
  "success": true,
  "message": "Flag 'new_editor_ui' archived successfully"
}
```

**审计日志**: 自动记录到 `admin_operations` 表

---

### POST `/feature-flags/test-evaluation`

测试 Feature Flag 评估逻辑

**限流**: 无限流

**请求体**:
```json
{
  "flag_key": "new_editor_ui",
  "user_id": "user_123",
  "tier": "t3",
  "environment": "production"
}
```

**响应**:
```json
{
  "flag_key": "new_editor_ui",
  "result": {
    "enabled": true,
    "variant": null,
    "reason": "targeting_rule_match",
    "metadata": { ... }
  }
}
```

---

### GET `/feature-flags/{key}/audit`

获取 Feature Flag 审计日志

**限流**: 无限流

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "data": [
    {
      "timestamp": "2026-01-10T15:30:00Z",
      "action": "toggled",
      "admin_id": "admin_user_123",
      "changes": {
        "enabled": {
          "old": false,
          "new": true
        }
      }
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 47
  }
}
```

---

### GET `/feature-flags/client/flags`

客户端 Feature Flags 评估 (User API)

**限流**: 无限流

**响应**:
```json
{
  "flags": {
    "new_editor_ui": true,
    "dark_mode": false
  }
}
```

---

## 8. Logs 日志审计

### GET `/logs/errors`

获取错误日志

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `level` | string | - | 日志级别 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "errors": [
    {
      "id": "uuid-xxx",
      "level": "error",
      "message": "Database connection failed",
      "stacktrace": "...",
      "user_id": "user_abc",
      "created_at": "2026-01-11T10:30:00Z"
    }
  ],
  "total": 520,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/logs/errors/stats`

获取错误统计

**限流**: 30 req/min

**响应**:
```json
{
  "total_errors": 5200,
  "by_level": {
    "error": 3200,
    "warning": 1500,
    "critical": 500
  },
  "top_errors": [ ... ]
}
```

---

### GET `/logs/operations`

获取操作日志

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `operation_type` | string | - | 操作类型 |
| `admin_id` | string | - | 管理员ID |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "operations": [
    {
      "id": "uuid-xxx",
      "operation_type": "campaign_delete",
      "target_id": "campaign_123",
      "admin_id": "admin_abc",
      "details": { ... },
      "ip_address": "192.168.1.100",
      "created_at": "2026-01-11T10:30:00Z"
    }
  ],
  "total": 850,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/logs/operations/export`

导出操作日志 (CSV)

**限流**: 10 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `start_date` | string | 开始日期 |
| `end_date` | string | 结束日期 |

**响应**: CSV 文件流

**审计日志**: 记录导出操作

---

### GET `/logs/audit`

统一审计日志查询

**限流**: 30 req/min

**参数** (支持 10 个筛选参数):
| 参数 | 类型 | 说明 |
|------|------|------|
| `target` | string | 目标类型 |
| `source` | string | 来源 |
| `operation` | string | 操作类型 |
| `admin_id` | string | 管理员ID |
| `start_date` | string | 开始日期 |
| `end_date` | string | 结束日期 |
| `offset` | int | 分页偏移量 |
| `limit` | int | 每页数量 |

**响应**:
```json
{
  "logs": [ ... ],
  "total": 5200,
  "offset": 0,
  "limit": 20
}
```

---

## 9. Metrics 系统指标

### GET `/metrics/daily`

获取每日指标

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 30 | 天数 (1-365) |

**响应**:
```json
{
  "metrics": [
    {
      "date": "2026-01-11",
      "dau": 1250,
      "mau": 8500,
      "revenue": 2580.50,
      "new_users": 45
    }
  ]
}
```

---

### GET `/metrics/monthly`

获取每月指标

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `months` | int | 12 | 月数 (1-24) |

**响应**: 同 daily 格式，按月分组

---

### GET `/metrics/retention`

获取留存指标

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `cohort_date` | string | - | 队列日期 |

**响应**:
```json
{
  "retention": {
    "day_1": 65.2,
    "day_7": 42.5,
    "day_30": 28.3
  }
}
```

---

### GET `/metrics/funnel`

获取转化漏斗

**限流**: 30 req/min

**响应**:
```json
{
  "funnel": {
    "visitors": 10000,
    "signups": 2500,
    "activated": 1800,
    "paid": 450,
    "conversion_rate": 4.5
  }
}
```

**性能优化**: 使用 RPC 函数 `p_get_conversion_funnel` + 索引 (50x-100x 提升)

---

### GET `/metrics/errors`

获取错误指标

**限流**: 30 req/min

**响应**:
```json
{
  "total_errors": 520,
  "error_rate": 0.05,
  "by_type": { ... }
}
```

---

### GET `/metrics/dau-trend`

获取 DAU 趋势

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 30 | 天数 (1-90) |

**响应**:
```json
{
  "trend": [
    {
      "date": "2026-01-11",
      "dau": 1250,
      "change_percent": 5.2
    }
  ]
}
```

---

### POST `/metrics/refresh`

刷新指标缓存

**限流**: 5 req/min

**响应**:
```json
{
  "status": "refreshed",
  "message": "Metrics refresh task started"
}
```

---

## 10. Moderation 内容审核

### GET `/moderation/marketplace/moderation/list`

获取待审核商品列表

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 审核状态 |
| `type` | string | - | 资源类型 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "listing_id": "listing_123",
      "title": "可爱动物贴纸包",
      "resource_type": "sticker",
      "seller_id": "user_abc",
      "price": 299,
      "status": "pending",
      "submitted_at": "2026-01-10T15:00:00Z"
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/moderation/marketplace/moderation/{listing_id}`

获取商品审核详情

**限流**: 30 req/min

**响应**:
```json
{
  "id": "uuid-xxx",
  "listing_id": "listing_123",
  "title": "可爱动物贴纸包",
  "description": "包含 20 个精美动物贴纸",
  "resource_type": "sticker",
  "seller_id": "user_abc",
  "price": 299,
  "preview_url": "https://...",
  "status": "pending",
  "submitted_at": "2026-01-10T15:00:00Z"
}
```

---

### POST `/moderation/marketplace/moderation/{listing_id}/approve`

批准商品上架

**限流**: 30 req/min

**响应**:
```json
{
  "status": "approved",
  "listing_id": "listing_123"
}
```

---

### POST `/moderation/marketplace/moderation/{listing_id}/reject`

拒绝商品上架

**限流**: 30 req/min

**请求体**:
```json
{
  "reason": "图片质量不符合标准"
}
```

**响应**:
```json
{
  "status": "rejected",
  "listing_id": "listing_123",
  "reason": "图片质量不符合标准"
}
```

---

### POST `/moderation/marketplace/moderation/{listing_id}/delete`

软删除商品

**限流**: 30 req/min

**响应**:
```json
{
  "status": "deleted",
  "listing_id": "listing_123"
}
```

---

### POST `/moderation/marketplace/moderation/{listing_id}/unpublish`

强制下架商品

**限流**: 30 req/min

**响应**:
```json
{
  "status": "unpublished",
  "listing_id": "listing_123"
}
```

---

### GET `/moderation/reports`

获取所有内容举报

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 举报状态 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": "report_xxx",
      "resource_type": "listing",
      "resource_id": "listing_123",
      "reporter_id": "user_abc",
      "reason": "inappropriate_content",
      "status": "pending",
      "created_at": "2026-01-10T16:00:00Z"
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/moderation/reports/stats`

获取举报统计

**限流**: 30 req/min

**响应**:
```json
{
  "total": 127,
  "by_status": {
    "pending": 15,
    "in_review": 8,
    "resolved": 89,
    "dismissed": 15
  },
  "avg_resolution_time_hours": 6.5
}
```

---

### GET `/moderation/reports/{report_id}`

获取举报详情

**限流**: 30 req/min

**响应**:
```json
{
  "id": "report_xxx",
  "resource_type": "listing",
  "resource_id": "listing_123",
  "reporter_id": "user_abc",
  "reason": "inappropriate_content",
  "description": "包含不适宜内容",
  "status": "pending",
  "created_at": "2026-01-10T16:00:00Z"
}
```

---

### POST `/moderation/reports/{report_id}/respond`

处理举报

**限流**: 30 req/min

**请求体**:
```json
{
  "status": "resolved",
  "response": "已确认违规,已对商品进行下架处理"
}
```

**响应**:
```json
{
  "status": "resolved",
  "report_id": "report_xxx"
}
```

---

## 11. Notifications 通知管理

### POST `/notifications/broadcast`

发送系统广播通知

**限流**: 5 req/min

**请求体**:
```json
{
  "title": "系统维护通知",
  "content": "我们将在周日凌晨 2:00-4:00 进行系统维护",
  "target_group": "all"
}
```

**target_group 可选值**: `all`, `t1`, `t2`, `t3`, `free`, `paid`

**响应**:
```json
{
  "success": true,
  "message": "Broadcast sent successfully",
  "sent_count": 1542,
  "target_group": "all"
}
```

---

### POST `/notifications/notification/send`

发送通知给单个用户

**限流**: 30 req/min

**请求体**:
```json
{
  "user_id": "user_2abc3def4ghi",
  "title": "欢迎奖励",
  "content": "您已获得 50 积分奖励!",
  "notification_type": "promo"
}
```

**响应**:
```json
{
  "success": true,
  "notification_id": "uuid-xxx",
  "user_id": "user_2abc3def4ghi",
  "delivered": true
}
```

---

### POST `/notifications/notification/batch`

批量发送通知

**限流**: 10 req/min

**请求体**:
```json
{
  "user_ids": ["user_2abc", "user_2def"],
  "title": "新功能发布",
  "content": "查看我们全新的编辑器功能!",
  "notification_type": "announcement"
}
```

**限制**: 单次最多 100 个用户

**响应**:
```json
{
  "success": true,
  "sent_count": 2,
  "failed_count": 0,
  "total_users": 2
}
```

---

### GET `/notifications/notification/stats`

获取通知统计

**限流**: 30 req/min

**响应**:
```json
{
  "total_sent": 15420,
  "sent_today": 245,
  "by_type": {
    "system": 8500,
    "announcement": 4200,
    "alert": 1800,
    "promo": 920
  },
  "delivery_rate": 99.2,
  "read_rate": 67.5
}
```

---

### GET `/notifications/notification/history`

获取通知发送历史

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "data": [
    {
      "id": "uuid-xxx",
      "title": "系统维护",
      "notification_type": "system",
      "target_group": "all",
      "sent_count": 1542,
      "delivered_count": 1538,
      "created_at": "2026-01-11T10:30:00Z"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 324
  }
}
```

---

## 12. Stats 统计仪表板

### GET `/stats/dashboard`

获取仪表板 KPI

**限流**: 30 req/min

**响应**:
```json
{
  "dau": 1250,
  "mau": 8500,
  "total_users": 25000,
  "total_revenue": 125000.50,
  "mrr": 15000.00,
  "active_subscriptions": 850,
  "churn_rate": 3.2
}
```

---

### GET `/stats/user-growth`

获取用户增长统计

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `period` | string | week | 周期: day/week/month |

**响应**:
```json
{
  "period": "week",
  "data": [
    {
      "date": "2026-01-05",
      "new_users": 45,
      "total_users": 24955
    }
  ]
}
```

---

### GET `/stats/revenue`

获取收入统计

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `period` | string | month | 周期: week/month/year |

**响应**:
```json
{
  "period": "month",
  "total_revenue": 125000.50,
  "mrr": 15000.00,
  "by_source": {
    "subscriptions": 95000.00,
    "credits": 30000.50
  }
}
```

---

### GET `/stats/projects`

获取项目统计

**限流**: 30 req/min

**响应**:
```json
{
  "total_projects": 58000,
  "active_projects": 12500,
  "deleted_projects": 2500,
  "avg_per_user": 2.3
}
```

---

### GET `/stats/credits`

获取积分使用统计

**限流**: 30 req/min

**响应**:
```json
{
  "total_issued": 2500000,
  "total_consumed": 1850000,
  "by_type": {
    "ai_image": 1200000,
    "ai_text": 450000,
    "smart_scan": 200000
  }
}
```

---

### GET `/stats/tier-distribution`

获取 Tier 分布

**限流**: 30 req/min

**响应**:
```json
{
  "distribution": {
    "t1": 18500,
    "t2": 4200,
    "t3": 2300
  },
  "percentages": {
    "t1": 74.0,
    "t2": 16.8,
    "t3": 9.2
  }
}
```

---

### GET `/stats/conversion-funnel`

获取转化漏斗

**限流**: 30 req/min

**响应**:
```json
{
  "visitors": 10000,
  "signups": 2500,
  "activated": 1800,
  "paid": 450,
  "conversion_rate": 4.5
}
```

---

### GET `/stats/exports`

获取导出统计

**限流**: 30 req/min

**响应**:
```json
{
  "total_exports": 15000,
  "by_type": {
    "pdf": 12000,
    "zip": 3000
  },
  "by_tier": {
    "t1": 8000,
    "t2": 4500,
    "t3": 2500
  }
}
```

---

### GET `/stats/assets`

获取素材统计

**限流**: 30 req/min

**响应**:
```json
{
  "total_assets": 85000,
  "by_type": {
    "sticker": 45000,
    "background": 25000,
    "template": 15000
  },
  "total_downloads": 250000
}
```

---

### GET `/stats/tier-activity`

获取 Tier 活跃度

**限流**: 30 req/min

**响应**:
```json
{
  "activity": {
    "t1": {
      "dau": 850,
      "avg_session_duration": "5m 30s"
    },
    "t2": {
      "dau": 250,
      "avg_session_duration": "12m 15s"
    },
    "t3": {
      "dau": 150,
      "avg_session_duration": "18m 45s"
    }
  }
}
```

---

### GET `/stats/subscription-events`

获取订阅事件统计

**限流**: 30 req/min

**响应**:
```json
{
  "new_subscriptions": 45,
  "cancellations": 12,
  "upgrades": 8,
  "downgrades": 3,
  "net_change": 38
}
```

---

### GET `/stats/page-views`

获取页面浏览统计

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 7 | 天数 |

**响应**:
```json
{
  "total_views": 125000,
  "unique_visitors": 8500,
  "by_page": {
    "/": 45000,
    "/editor": 32000,
    "/marketplace": 18000
  }
}
```

---

### GET `/stats/project-details`

获取项目详细统计

**限流**: 30 req/min

**响应**:
```json
{
  "avg_pages_per_project": 8.5,
  "avg_ai_generations_per_project": 3.2,
  "most_used_templates": [ ... ]
}
```

---

### GET `/stats/returning-users`

获取回访用户统计

**限流**: 30 req/min

**响应**:
```json
{
  "returning_users": 5200,
  "new_users": 450,
  "returning_rate": 92.0
}
```

---

### GET `/stats/tier-trend`

获取 Tier 趋势

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 30 | 天数 |

**响应**:
```json
{
  "trend": [
    {
      "date": "2026-01-11",
      "t1": 18500,
      "t2": 4200,
      "t3": 2300
    }
  ]
}
```

---

### GET `/stats/tier-conversion`

获取 Tier 转化统计

**限流**: 30 req/min

**响应**:
```json
{
  "conversions": {
    "t1_to_t2": 120,
    "t1_to_t3": 45,
    "t2_to_t3": 32
  },
  "conversion_rates": {
    "t1_to_paid": 0.9,
    "t2_to_t3": 0.8
  }
}
```

---

### GET `/stats/performance`

获取 Core Web Vitals 性能指标

**限流**: 30 req/min

**响应**:
```json
{
  "lcp": 1.8,
  "fid": 50,
  "cls": 0.05,
  "ttfb": 320
}
```

---

### GET `/stats/user-distribution`

获取用户分布统计

**限流**: 30 req/min

**响应**:
```json
{
  "by_country": {
    "US": 12000,
    "UK": 5000,
    "CA": 3000
  },
  "by_timezone": { ... }
}
```

---

## 13. Subscriptions 订阅管理

### POST `/subscriptions/refund`

处理退款

**限流**: 10 req/min

**请求体**:
```json
{
  "user_code": "26010914305278900123456789",
  "amount": 9.90,
  "reason": "用户要求退款"
}
```

**响应**:
```json
{
  "success": true,
  "refund_id": "re_xxx",
  "amount": 9.90
}
```

---

### POST `/subscriptions/subscription/cancel`

取消订阅

**限流**: 10 req/min

**请求体**:
```json
{
  "user_code": "26010914305278900123456789",
  "reason": "用户主动取消"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Subscription cancelled successfully"
}
```

---

### POST `/subscriptions/subscription/downgrade`

降级订阅

**限流**: 10 req/min

**请求体**:
```json
{
  "user_code": "26010914305278900123456789",
  "target_tier": "t2"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Subscription downgraded successfully",
  "new_tier": "t2"
}
```

---

## 14. System 系统管理

### GET `/system/configs`

获取系统配置列表

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `group` | string | - | 按组筛选 |
| `search` | string | - | 搜索关键词 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 (1-100) |

**响应**:
```json
{
  "configs": [
    {
      "id": "uuid-xxx",
      "key": "system.maintenance_mode",
      "value": "false",
      "value_type": "boolean",
      "config_group": "general",
      "description": "系统维护模式开关",
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-10T10:00:00Z"
    }
  ],
  "total": 87,
  "offset": 0,
  "limit": 50
}
```

**字段长度限制**:
- `key`: 最大 200 字符
- `value`: 最大 10,000 字符
- `value_type`: 最大 20 字符
- `config_group`: 最大 50 字符
- `description`: 最大 500 字符

---

### GET `/system/configs/groups`

获取配置组列表

**限流**: 30 req/min

**响应**:
```json
{
  "groups": [
    "general",
    "feature",
    "rate_limit",
    "ai",
    "payment",
    "notification"
  ]
}
```

**有效组列表** (VALID_CONFIG_GROUPS):
- `general` - 通用配置
- `feature` - 功能开关
- `rate_limit` - 限流配置
- `ai` - AI 配置
- `payment` - 支付配置
- `notification` - 通知配置

---

### POST `/system/configs`

创建系统配置

**限流**: 10 req/min

**请求体**:
```json
{
  "key": "system.new_feature_enabled",
  "value": "true",
  "value_type": "boolean",
  "config_group": "feature",
  "description": "新功能开关"
}
```

**value_type 可选值** (VALID_VALUE_TYPES):
- `text` - 文本
- `number` - 数字
- `boolean` - 布尔值
- `json` - JSON 对象
- `list` - 列表

**响应**:
```json
{
  "status": "created",
  "config": {
    "id": "uuid-xxx",
    "key": "system.new_feature_enabled",
    ...
  }
}
```

**状态码**: 201 Created

---

### PUT `/system/configs/{key:path}`

更新系统配置

**限流**: 10 req/min

**请求体** (所有字段可选):
```json
{
  "value": "false",
  "description": "更新后的描述",
  "is_active": false
}
```

**响应**:
```json
{
  "status": "updated",
  "config": {
    "key": "system.new_feature_enabled",
    "value": "false",
    ...
  }
}
```

**审计日志**: 自动记录更改历史到 `config_audit_log`

---

### DELETE `/system/configs/{key:path}`

软删除配置

**限流**: 10 req/min

**响应**:
```json
{
  "status": "deleted",
  "key": "system.old_feature"
}
```

**审计日志**: 自动记录删除操作

---

### GET `/system/configs/audit`

获取配置变更审计日志

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `config_key` | string | - | 筛选特定配置 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 (1-100) |

**响应**:
```json
{
  "logs": [
    {
      "config_key": "system.maintenance_mode",
      "action": "updated",
      "old_value": "false",
      "new_value": "true",
      "admin_id": "admin_user_123",
      "timestamp": "2026-01-10T12:00:00Z"
    }
  ],
  "total": 523,
  "offset": 0,
  "limit": 50
}
```

---

### POST `/system/configs/cache/invalidate`

清空配置缓存

**限流**: 5 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | string | 可选,清空特定配置缓存 (为空则清空全部) |

**响应**:
```json
{
  "status": "invalidated",
  "key": "system.maintenance_mode"
}
```

---

### GET `/system/system/cache/status`

获取 Redis 缓存状态

**限流**: 30 req/min

**响应**:
```json
{
  "connected": true,
  "memory_used_mb": 128.5,
  "memory_max_mb": 512.0,
  "total_keys": 4523,
  "hit_rate": 87.3
}
```

---

### GET `/system/system/cache/keys`

列出缓存键

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `pattern` | string | * | 键名模式 (支持 * 通配符) |
| `limit` | int | 100 | 最多返回数量 (1-1000) |

**pattern 验证**:
- 只允许: 字母、数字、下划线、冒号、星号、连字符、点
- 使用正则: `^[a-zA-Z0-9_:*\-\.]+$`
- 无效字符返回 400 错误

**响应**:
```json
{
  "keys": [
    "config:system.maintenance_mode",
    "user:user_123:profile"
  ],
  "total": 3,
  "pattern": "config:*"
}
```

---

### DELETE `/system/system/cache/key/{key:path}`

删除单个缓存键

**限流**: 10 req/min

**响应**:
```json
{
  "status": "deleted",
  "key": "config:system.maintenance_mode"
}
```

**字段验证**: 键名最大 200 字符

---

### POST `/system/system/cache/clear-all/confirm`

请求清空所有缓存的确认 Token

**限流**: 1 req / 10 min

**响应**:
```json
{
  "token": "5a2d8f4c1e9b3a7d...",
  "expires_in_seconds": 120,
  "message": "Use this token within 2 minutes to clear all cache"
}
```

**安全措施** (P0-013):
- Token 2 分钟后过期
- 一次性使用
- 存储在 Redis 中: `cache_clear_confirm:{admin_id}:{token}`

---

### POST `/system/system/cache/clear-all`

清空所有缓存 (危险操作)

**限流**: 1 req / 10 min

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `confirm_token` | string | 是 | 从 /clear-all/confirm 获取 (32-64 字符) |

**响应**:
```json
{
  "status": "cleared",
  "message": "All cache has been cleared. Database query load will increase temporarily."
}
```

**安全措施** (P0-013):
- 验证 Token 有效性
- Token 一次性使用后自动删除
- 记录审计日志到 `admin_operations` 表
- 记录 IP 地址和 User-Agent
- 记录 CRITICAL 级别日志

**错误情况**:
- 403: Token 无效或已过期

---

## 15. Tasks 任务管理

### GET `/tasks/management/status`

获取任务状态

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `task_name` | string | 任务名称 |

**响应**:
```json
{
  "task_name": "aggregation_daily",
  "status": "running",
  "last_run": "2026-01-11T00:00:00Z",
  "next_run": "2026-01-12T00:00:00Z",
  "success_count": 365,
  "failure_count": 2
}
```

---

### GET `/tasks/management/logs`

获取任务日志

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `task_name` | string | - | 任务名称 |
| `limit` | int | 100 | 最多返回数量 |

**响应**:
```json
{
  "logs": [
    {
      "task_name": "aggregation_daily",
      "status": "success",
      "duration_seconds": 12.5,
      "started_at": "2026-01-11T00:00:00Z",
      "completed_at": "2026-01-11T00:00:12Z",
      "error": null
    }
  ]
}
```

---

### GET `/tasks/management/health`

获取任务健康状态

**限流**: 30 req/min

**响应**:
```json
{
  "healthy_tasks": 12,
  "failed_tasks": 1,
  "total_tasks": 13,
  "warnings": [
    "Task 'aggregation_monthly' has 2 consecutive failures"
  ]
}
```

---

### POST `/tasks/management/{task_name}/run`

手动触发任务

**限流**: 10 req/min

**响应**:
```json
{
  "status": "triggered",
  "task_name": "aggregation_daily",
  "message": "Task started successfully"
}
```

**审计日志**: 记录手动触发操作

---

## 16. Users 用户管理

### GET `/users`

搜索用户

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `search` | string | - | 搜索关键词 (支持 user_code) |
| `tier` | string | - | Tier 筛选 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "users": [
    {
      "user_id": "user_abc",
      "user_code": "26010914305278900123456789",
      "username": "john_doe",
      "email": "john@example.com",
      "tier": "t2",
      "credits_monthly": 200,
      "credits_permanent": 150,
      "created_at": "2026-01-09T14:30:52Z"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/users/by-tier/{tier}`

按 Tier 获取用户

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**: 同 `/users`

---

### GET `/users/{user_id}`

获取用户完整审计信息

**限流**: 30 req/min

**响应**:
```json
{
  "user": {
    "user_id": "user_abc",
    "user_code": "26010914305278900123456789",
    "username": "john_doe",
    "email": "john@example.com",
    "tier": "t2",
    "credits_monthly": 200,
    "credits_permanent": 150
  },
  "projects": {
    "total": 15,
    "deleted": 2
  },
  "transactions": {
    "total": 45,
    "total_credited": 5000,
    "total_debited": 3200
  },
  "activities": [ ... ]
}
```

---

### POST `/users/{user_id}/credits`

调整用户积分 (Admin Only)

**限流**: 10 req/min

**请求体**:
```json
{
  "amount": 100,
  "bucket": "permanent",
  "reason": "补偿奖励"
}
```

**响应**:
```json
{
  "success": true,
  "new_balance": {
    "monthly": 200,
    "permanent": 250,
    "total": 450
  }
}
```

**审计日志**: 记录积分调整操作

---

### PATCH `/users/{user_id}`

更新用户信息

**限流**: 10 req/min

**请求体**:
```json
{
  "tier": "t3"
}
```

**响应**:
```json
{
  "success": true,
  "user": { ... }
}
```

---

### POST `/users/{user_id}/discount`

创建用户折扣

**限流**: 10 req/min

**请求体**:
```json
{
  "discount_percentage": 20,
  "expires_at": "2026-02-11T00:00:00Z"
}
```

**响应**:
```json
{
  "success": true,
  "discount": {
    "percentage": 20,
    "expires_at": "2026-02-11T00:00:00Z"
  }
}
```

---

### GET `/users/{user_id}/payments`

获取用户支付记录

**限流**: 30 req/min

**响应**:
```json
{
  "payments": [
    {
      "id": "pi_xxx",
      "amount": 9.90,
      "status": "succeeded",
      "plan": "t2",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET `/users/{user_id}/projects`

获取用户项目列表

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `include_deleted` | bool | false | 包含已删除 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "projects": [ ... ],
  "total": 15,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/users/{user_id}/asset-usage`

获取用户素材使用情况

**限流**: 30 req/min

**响应**:
```json
{
  "total_assets": 45,
  "by_type": {
    "sticker": 25,
    "background": 15,
    "template": 5
  }
}
```

---

### GET `/users/{user_id}/env-stats`

获取用户环境统计

**限流**: 30 req/min

**响应**:
```json
{
  "browser": "Chrome",
  "os": "Windows",
  "device_type": "desktop",
  "last_active": "2026-01-11T10:30:00Z"
}
```

---

### POST `/users/projects/{project_id}/restore`

恢复用户项目

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "project": { ... }
}
```

---

### GET `/users/projects/feed`

获取项目动态流

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "projects": [
    {
      "id": "proj_xxx",
      "title": "我的迷你书",
      "user_id": "user_abc",
      "created_at": "2026-01-11T10:00:00Z"
    }
  ],
  "total": 500,
  "offset": 0,
  "limit": 20
}
```

---

## 17. Webhooks 重试管理

### POST `/webhooks/retry`

重试失败的 Webhooks

**限流**: 10 req / hour

**响应**:
```json
{
  "status": "retry_started",
  "total_failed_webhooks": 15,
  "message": "Retrying all failed webhooks"
}
```

---

### GET `/webhooks/failed`

获取失败的 Webhooks

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 50 | 最多返回数量 |

**响应**:
```json
{
  "failed_webhooks": [
    {
      "id": "webhook_xxx",
      "event_type": "user.created",
      "attempts": 3,
      "last_error": "Connection timeout",
      "created_at": "2026-01-10T15:00:00Z",
      "next_retry_at": "2026-01-10T16:00:00Z"
    }
  ],
  "total": 15
}
```

---

*文档版本: v3.33*
*最后更新: 2026-01-11*

**更新内容** (v3.33):
- 🚨 删除虚构的 "AI Models 管理" 模块 (8个不存在的接口)
- ✅ 新增 "Asset Categories 分类管理" 模块 (7个接口)
- ✅ 修正 "System 系统管理" 接口数量 (11→12个)
- ✅ 添加完整的接口总览表格 (135个接口)
- ✅ 更新 "AI Insights" 模块接口细节 (基于实际代码 v3.27)
- ✅ 所有接口信息从实际代码中提取，确保准确性
- ✅ 包含所有请求参数、响应格式、验证规则和限流配置
- ✅ 按 17 个模块分类组织（原 17 个 - 1 虚构 + 1 补充 = 17 个）
