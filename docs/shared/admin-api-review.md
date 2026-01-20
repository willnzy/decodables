# Admin API 完整参考

> **状态**: ✅ Complete (已评审 187 个)
> **版本**: 3.43
> **最后更新**: 2026-01-20
> **总端点数**: 187 个

本文档记录已评审的 187 个 Admin API 端点的完整信息，包括请求参数、响应格式、验证规则和限流配置。

**v3.43 更新**:
- 新增 Notifications Template CRUD 端点 (6个): GET/POST/PUT/DELETE /notifications, POST /notifications/{id}/send

---

## 目录

1. [AI Insights 洞察 (5个)](#1-ai-insights-洞察)
2. [AI Models 管理 (8个)](#2-ai-models-管理)
3. [Articles 文章管理 (7个)](#3-articles-文章管理)
4. [Asset Categories 分类管理 (7个)](#4-asset-categories-分类管理)
5. [Campaigns 营销活动 (8个)](#5-campaigns-营销活动)
6. [Config 系统配置 (8个)](#6-config-系统配置)
7. [Events 事件管理 (5个)](#7-events-事件管理)
8. [Experiments 实验管理 (14个)](#8-experiments-实验管理)
9. [Feature Flags 功能开关 (15个)](#9-feature-flags-功能开关)
10. [Logs 日志审计 (5个)](#10-logs-日志审计)
11. [Metrics 系统指标 (7个)](#11-metrics-系统指标)
12. [Moderation 内容审核 (10个)](#12-moderation-内容审核)
13. [Notifications 通知管理 (11个)](#13-notifications-通知管理) **UPDATED**
14. [Static Pages 静态页面管理 (7个)](#14-static-pages-静态页面管理) **UPDATED**
15. [Stats 统计仪表板 (18个)](#15-stats-统计仪表板)
16. [Subscriptions 订阅管理 (3个)](#16-subscriptions-订阅管理)
17. [System 系统管理 (12个)](#17-system-系统管理)
18. [Tasks 任务管理 (4个)](#18-tasks-任务管理)
19. [Themes 主题管理 (13个)](#19-themes-主题管理)
20. [Tiers 配置管理 (3个)](#20-tiers-配置管理) **NEW**
21. [Users 用户管理 (13个)](#21-users-用户管理)
22. [User Creation Monitoring 用户创建监控 (3个)](#22-user-creation-monitoring-用户创建监控)
23. [Webhooks 重试管理 (2个)](#23-webhooks-重试管理)

---

## 📋 接口总览 (181个)

| 序号 | 模块 | 方法 | 路径 | 函数名 | 文件 | 说明 |
|------|------|------|------|--------|------|------|
| **AI Insights (5个)** |
| 1 | AI Insights | GET | /ai/insights | adm_get_ai_insights | api/admin/ai.py | AI 洞察数据 |
| 2 | AI Insights | GET | /ai/recommendations | adm_get_ai_recommendations | api/admin/ai.py | AI 推荐 |
| 3 | AI Insights | GET | /ai/behavior-analysis | adm_get_behavior_analysis | api/admin/ai.py | 用户行为分析 |
| 4 | AI Insights | POST | /ai/generate-report | adm_generate_ai_report | api/admin/ai.py | 生成 AI 报告 |
| 5 | AI Insights | GET | /ai/quick-insights | adm_get_quick_insights | api/admin/ai.py | 快速洞察 |
| **AI Models (8个)** |
| 6 | AI Models | GET | /ai/models/config | get_ai_config | api/admin/ai_models.py | 获取 AI 模型配置 |
| 7 | AI Models | PUT | /ai/models/config/text | update_text_config | api/admin/ai_models.py | 更新文本生成模型 |
| 8 | AI Models | PUT | /ai/models/config/image | update_image_config | api/admin/ai_models.py | 更新图像生成模型 |
| 9 | AI Models | PUT | /ai/models/config/admin | update_admin_config | api/admin/ai_models.py | 更新管理员专用配置 |
| 10 | AI Models | PUT | /ai/models/config/canary | update_canary_config_endpoint | api/admin/ai_models.py | 更新灰度发布配置 |
| 11 | AI Models | PUT | /ai/models/providers/toggle | toggle_provider_endpoint | api/admin/ai_models.py | 启用/禁用 AI 提供商 |
| 12 | AI Models | GET | /ai/models/usage | get_usage | api/admin/ai_models.py | 获取 AI 使用统计 |
| 13 | AI Models | POST | /ai/models/cache/clear | clear_cache_endpoint | api/admin/ai_models.py | 清除 AI 缓存 |
| **Articles 文章管理 (7个)** **NEW** |
| 14 | Articles | GET | /articles | list_articles | api/admin/articles.py | 获取所有文章列表 |
| 15 | Articles | GET | /articles/{id} | get_article | api/admin/articles.py | 获取文章详情 (by ID) |
| 16 | Articles | POST | /articles | create_article | api/admin/articles.py | 创建新文章 |
| 17 | Articles | PUT | /articles/{id} | update_article | api/admin/articles.py | 更新文章 |
| 18 | Articles | DELETE | /articles/{id} | delete_article | api/admin/articles.py | 删除文章 |
| 19 | Articles | POST | /articles/{id}/publish | publish_article | api/admin/articles.py | 发布文章 |
| 20 | Articles | POST | /articles/{id}/unpublish | unpublish_article | api/admin/articles.py | 取消发布 |
| **Asset Categories (7个)** |
| 21 | Asset Categories | GET | /asset-categories/ | list_categories | api/admin/asset_categories.py | 列出所有分类 |
| 22 | Asset Categories | GET | /asset-categories/tree | get_category_tree | api/admin/asset_categories.py | 获取分类树 |
| 23 | Asset Categories | POST | /asset-categories/ | create_category | api/admin/asset_categories.py | 创建分类 |
| 24 | Asset Categories | PATCH | /asset-categories/{slug} | update_category | api/admin/asset_categories.py | 更新分类 |
| 25 | Asset Categories | PUT | /asset-categories/{slug}/move | move_category | api/admin/asset_categories.py | 移动分类 |
| 26 | Asset Categories | DELETE | /asset-categories/{slug} | delete_category | api/admin/asset_categories.py | 删除分类 |
| 27 | Asset Categories | GET | /asset-categories/{slug}/resources | get_category_resources | api/admin/asset_categories.py | 获取分类资源 |
| **Campaigns (8个)** |
| 28 | Campaigns | GET | /campaigns | - | api/admin/campaigns.py | 列出所有营销活动 |
| 29 | Campaigns | GET | /campaigns/{id} | - | api/admin/campaigns.py | 获取活动详情 |
| 30 | Campaigns | POST | /campaigns | - | api/admin/campaigns.py | 创建新活动 |
| 31 | Campaigns | PUT | /campaigns/{id} | - | api/admin/campaigns.py | 更新活动 |
| 32 | Campaigns | DELETE | /campaigns/{id} | - | api/admin/campaigns.py | 删除活动 |
| 33 | Campaigns | POST | /campaigns/{id}/activate | - | api/admin/campaigns.py | 激活活动 |
| 34 | Campaigns | POST | /campaigns/{id}/pause | - | api/admin/campaigns.py | 暂停活动 |
| 35 | Campaigns | GET | /campaigns/{id}/stats | - | api/admin/campaigns.py | 获取活动统计 |
| **Config (8个)** |
| 36 | Config | GET | /config | - | api/admin/config.py | 获取所有系统配置 |
| 37 | Config | GET | /config/{config_key} | - | api/admin/config.py | 获取单个配置 |
| 38 | Config | PUT | /config | - | api/admin/config.py | 更新配置 |
| 39 | Config | PUT | /config/batch | - | api/admin/config.py | 批量更新配置 |
| 40 | Config | GET | /config/rate-limits | - | api/admin/config.py | 获取所有限流配置 |
| 41 | Config | POST | /config/rate-limits/preset | - | api/admin/config.py | 应用限流预设方案 |
| 42 | Config | GET | /config/rate-limits/presets | - | api/admin/config.py | 获取所有限流预设 |
| 43 | Config | POST | /config/cache/clear | - | api/admin/config.py | 清空配置缓存 |
| **Events (5个)** |
| 44 | Events | GET | /events | - | api/admin/events.py | 获取用户事件 |
| 45 | Events | GET | /events/stats | - | api/admin/events.py | 获取事件统计 |
| 46 | Events | GET | /events/aggregated/{aggregation_type} | - | api/admin/events.py | 获取聚合统计 |
| 47 | Events | GET | /events/aggregated/{aggregation_type}/range | - | api/admin/events.py | 获取聚合统计范围 |
| 48 | Events | POST | /events/aggregation/run | - | api/admin/events.py | 手动触发聚合任务 |
| **Experiments (14个)** |
| 49 | Experiments | GET | /experiments | - | api/admin/experiments.py | 列出所有实验 |
| 50 | Experiments | POST | /experiments | - | api/admin/experiments.py | 创建实验 |
| 51 | Experiments | GET | /experiments/{experiment_key} | - | api/admin/experiments.py | 获取实验详情 |
| 52 | Experiments | PUT | /experiments/{experiment_key} | - | api/admin/experiments.py | 更新实验配置 |
| 53 | Experiments | PUT | /experiments/{experiment_key}/status | - | api/admin/experiments.py | 更新实验状态 |
| 54 | Experiments | DELETE | /experiments/{experiment_key} | - | api/admin/experiments.py | 删除实验 |
| 55 | Experiments | GET | /experiments/{experiment_key}/results | - | api/admin/experiments.py | 获取实验结果 |
| 56 | Experiments | POST | /experiments/{experiment_key}/aggregate | - | api/admin/experiments.py | 触发实验结果聚合 |
| 57 | Experiments | POST | /experiments/aggregate-all | - | api/admin/experiments.py | 触发所有实验聚合 |
| 58 | Experiments | POST | /experiments/cache/clear | - | api/admin/experiments.py | 清空实验缓存 |
| 59 | Experiments | POST | /experiments/{experiment_key}/ai-analysis | - | api/admin/experiments.py | 获取 AI 驱动的实验分析 |
| 60 | Experiments | GET | /experiments/{experiment_key}/quick-recommendation | - | api/admin/experiments.py | 获取快速决策建议 |
| 61 | Experiments | GET | /experiments/{experiment_key}/trend | - | api/admin/experiments.py | 获取每日趋势 |
| 62 | Experiments | GET | /experiments/{experiment_key}/hourly-trend | - | api/admin/experiments.py | 获取每小时趋势 |
| **Feature Flags (15个)** |
| 63 | Feature Flags | GET | /feature-flags | - | api/admin/feature_flags.py | 列出所有 Feature Flags |
| 64 | Feature Flags | POST | /feature-flags | - | api/admin/feature_flags.py | 创建新 Feature Flag |
| 65 | Feature Flags | GET | /feature-flags/{key} | - | api/admin/feature_flags.py | 获取 Feature Flag 详情 |
| 66 | Feature Flags | PATCH | /feature-flags/{key} | - | api/admin/feature_flags.py | 更新 Feature Flag |
| 67 | Feature Flags | POST | /feature-flags/{key}/toggle | - | api/admin/feature_flags.py | 快速切换启用状态 |
| 68 | Feature Flags | DELETE | /feature-flags/{key} | - | api/admin/feature_flags.py | 归档 Feature Flag |
| 69 | Feature Flags | POST | /feature-flags/test-evaluation | - | api/admin/feature_flags.py | 测试 Feature Flag 评估逻辑 |
| 70 | Feature Flags | GET | /feature-flags/{key}/audit | - | api/admin/feature_flags.py | 获取 Feature Flag 审计日志 |
| 71 | Feature Flags | GET | /feature-flags/client/flags | - | api/admin/feature_flags.py | 客户端 Feature Flags 评估 |
| 72 | Feature Flags | GET | /feature-flags/tree | - | api/admin/feature_flags.py | 获取 Flag 树状结构 (v1.1) |
| 73 | Feature Flags | GET | /feature-flags/{key}/children | - | api/admin/feature_flags.py | 获取子级 Flags (v1.1) |
| 74 | Feature Flags | GET | /feature-flags/{key}/parents | - | api/admin/feature_flags.py | 获取父级 Flags (v1.1) |
| 75 | Feature Flags | POST | /feature-flags/{key}/batch-toggle | - | api/admin/feature_flags.py | 批量开关 Flag 及子级 (v1.1) |
| 76 | Feature Flags | GET | /feature-flags/{key}/exposures | - | api/admin/feature_flags.py | 获取 Flag 曝光记录 (v1.1) |
| 77 | Feature Flags | GET | /feature-flags/{key}/exposures/stats | - | api/admin/feature_flags.py | 获取曝光统计 (v1.1) |
| **Logs (5个)** |
| 78 | Logs | GET | /logs/errors | - | api/admin/logs.py | 获取错误日志 |
| 79 | Logs | GET | /logs/errors/stats | - | api/admin/logs.py | 获取错误统计 |
| 80 | Logs | GET | /logs/operations | - | api/admin/logs.py | 获取操作日志 |
| 81 | Logs | GET | /logs/operations/export | - | api/admin/logs.py | 导出操作日志 |
| 82 | Logs | GET | /logs/audit | - | api/admin/logs.py | 统一审计日志查询 |
| **Metrics (7个)** |
| 83 | Metrics | GET | /metrics/daily | - | api/admin/metrics.py | 获取每日指标 |
| 84 | Metrics | GET | /metrics/monthly | - | api/admin/metrics.py | 获取每月指标 |
| 85 | Metrics | GET | /metrics/retention | - | api/admin/metrics.py | 获取留存指标 |
| 86 | Metrics | GET | /metrics/funnel | - | api/admin/metrics.py | 获取转化漏斗 |
| 87 | Metrics | GET | /metrics/errors | - | api/admin/metrics.py | 获取错误指标 |
| 88 | Metrics | GET | /metrics/dau-trend | - | api/admin/metrics.py | 获取 DAU 趋势 |
| 89 | Metrics | POST | /metrics/refresh | - | api/admin/metrics.py | 刷新指标缓存 |
| **Moderation (10个)** |
| 90 | Moderation | GET | /moderation/marketplace/moderation/list | - | api/admin/moderation.py | 获取待审核商品列表 |
| 91 | Moderation | GET | /moderation/marketplace/moderation/{listing_id} | - | api/admin/moderation.py | 获取商品审核详情 |
| 92 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/approve | - | api/admin/moderation.py | 批准商品上架 |
| 93 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/reject | - | api/admin/moderation.py | 拒绝商品上架 |
| 94 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/delete | - | api/admin/moderation.py | 软删除商品 |
| 95 | Moderation | POST | /moderation/marketplace/moderation/{listing_id}/unpublish | - | api/admin/moderation.py | 强制下架商品 |
| 96 | Moderation | GET | /moderation/reports | - | api/admin/moderation.py | 获取所有内容举报 |
| 97 | Moderation | GET | /moderation/reports/stats | - | api/admin/moderation.py | 获取举报统计 |
| 98 | Moderation | GET | /moderation/reports/{report_id} | - | api/admin/moderation.py | 获取举报详情 |
| 99 | Moderation | POST | /moderation/reports/{report_id}/respond | - | api/admin/moderation.py | 处理举报 |
| **Notifications (5个)** |
| 100 | Notifications | POST | /notifications/broadcast | - | api/admin/notifications.py | 发送系统广播通知 |
| 101 | Notifications | POST | /notifications/notification/send | - | api/admin/notifications.py | 发送通知给单个用户 |
| 102 | Notifications | POST | /notifications/notification/batch | - | api/admin/notifications.py | 批量发送通知 |
| 103 | Notifications | GET | /notifications/notification/stats | - | api/admin/notifications.py | 获取通知统计 |
| 104 | Notifications | GET | /notifications/notification/history | - | api/admin/notifications.py | 获取通知发送历史 |
| **Stats (18个)** |
| 105 | Stats | GET | /stats/dashboard | - | api/admin/stats.py | 获取仪表板 KPI |
| 106 | Stats | GET | /stats/user-growth | - | api/admin/stats.py | 获取用户增长统计 |
| 107 | Stats | GET | /stats/revenue | - | api/admin/stats.py | 获取收入统计 |
| 108 | Stats | GET | /stats/projects | - | api/admin/stats.py | 获取项目统计 |
| 109 | Stats | GET | /stats/credits | - | api/admin/stats.py | 获取积分使用统计 |
| 110 | Stats | GET | /stats/tier-distribution | - | api/admin/stats.py | 获取 Tier 分布 |
| 111 | Stats | GET | /stats/conversion-funnel | - | api/admin/stats.py | 获取转化漏斗 |
| 112 | Stats | GET | /stats/exports | - | api/admin/stats.py | 获取导出统计 |
| 113 | Stats | GET | /stats/assets | - | api/admin/stats.py | 获取素材统计 |
| 114 | Stats | GET | /stats/tier-activity | - | api/admin/stats.py | 获取 Tier 活跃度 |
| 115 | Stats | GET | /stats/subscription-events | - | api/admin/stats.py | 获取订阅事件统计 |
| 116 | Stats | GET | /stats/page-views | - | api/admin/stats.py | 获取页面浏览统计 |
| 117 | Stats | GET | /stats/project-details | - | api/admin/stats.py | 获取项目详细统计 |
| 118 | Stats | GET | /stats/returning-users | - | api/admin/stats.py | 获取回访用户统计 |
| 119 | Stats | GET | /stats/tier-trend | - | api/admin/stats.py | 获取 Tier 趋势 |
| 120 | Stats | GET | /stats/tier-conversion | - | api/admin/stats.py | 获取 Tier 转化统计 |
| 121 | Stats | GET | /stats/performance | - | api/admin/stats.py | 获取 Core Web Vitals 性能指标 |
| 122 | Stats | GET | /stats/user-distribution | - | api/admin/stats.py | 获取用户分布统计 |
| **Subscriptions (3个)** |
| 123 | Subscriptions | POST | /subscriptions/refund | - | api/admin/subscriptions.py | 处理退款 |
| 124 | Subscriptions | POST | /subscriptions/subscription/cancel | - | api/admin/subscriptions.py | 取消订阅 |
| 125 | Subscriptions | POST | /subscriptions/subscription/downgrade | - | api/admin/subscriptions.py | 降级订阅 |
| **System (12个)** |
| 126 | System | GET | /system/configs | get_configs_endpoint | api/admin/system.py | 获取系统配置列表 |
| 127 | System | GET | /system/configs/groups | get_config_groups_endpoint | api/admin/system.py | 获取配置组列表 |
| 128 | System | POST | /system/configs | create_config_endpoint | api/admin/system.py | 创建系统配置 |
| 129 | System | PUT | /system/configs/{key:path} | update_config_endpoint | api/admin/system.py | 更新系统配置 |
| 130 | System | DELETE | /system/configs/{key:path} | delete_config_endpoint | api/admin/system.py | 软删除配置 |
| 131 | System | GET | /system/configs/audit | get_config_audit_endpoint | api/admin/system.py | 获取配置变更审计日志 |
| 132 | System | POST | /system/configs/cache/invalidate | invalidate_cache_endpoint | api/admin/system.py | 清空配置缓存 |
| 133 | System | GET | /system/system/cache/status | get_cache_status_endpoint | api/admin/system.py | 获取 Redis 缓存状态 |
| 134 | System | GET | /system/system/cache/keys | list_cache_keys_endpoint | api/admin/system.py | 列出缓存键 |
| 135 | System | DELETE | /system/system/cache/key/{key:path} | delete_cache_key_endpoint | api/admin/system.py | 删除单个缓存键 |
| 136 | System | POST | /system/system/cache/clear-all/confirm | request_clear_all_confirmation | api/admin/system.py | 请求清空所有缓存的确认 Token |
| 137 | System | POST | /system/system/cache/clear-all | clear_all_cache_endpoint | api/admin/system.py | 清空所有缓存 |
| **Tasks (4个)** |
| 138 | Tasks | GET | /tasks/management/status | - | api/admin/tasks_mgmt.py | 获取任务状态 |
| 139 | Tasks | GET | /tasks/management/logs | - | api/admin/tasks_mgmt.py | 获取任务日志 |
| 140 | Tasks | GET | /tasks/management/health | - | api/admin/tasks_mgmt.py | 获取任务健康状态 |
| 141 | Tasks | POST | /tasks/management/{task_name}/run | - | api/admin/tasks_mgmt.py | 手动触发任务 |
| **Themes (13个)** |
| 142 | Themes | GET | /themes | list_themes | api/admin/themes.py | 列出所有主题 |
| 143 | Themes | GET | /themes/generation-status | get_generation_status | api/admin/themes.py | 获取主题生成状态 |
| 144 | Themes | GET | /themes/calendar | get_calendar_view | api/admin/themes.py | 获取主题日历视图 |
| 145 | Themes | GET | /themes/review/pending | get_pending_reviews | api/admin/themes.py | 获取待审核主题 |
| 146 | Themes | GET | /themes/{theme_id} | get_theme | api/admin/themes.py | 获取主题详情 |
| 147 | Themes | GET | /themes/{theme_id}/history | get_theme_history | api/admin/themes.py | 获取主题生成历史 |
| 148 | Themes | POST | /themes | create_theme | api/admin/themes.py | 创建新主题 |
| 149 | Themes | PUT | /themes/{theme_id} | update_theme | api/admin/themes.py | 更新主题 |
| 150 | Themes | DELETE | /themes/{theme_id} | delete_theme | api/admin/themes.py | 删除主题 |
| 151 | Themes | POST | /themes/batch-generate | batch_generate_themes | api/admin/themes.py | 批量生成主题 |
| 152 | Themes | POST | /themes/{theme_id}/review | review_theme | api/admin/themes.py | 审核主题 |
| 153 | Themes | POST | /themes/{theme_id}/regenerate | regenerate_theme | api/admin/themes.py | 重新生成主题 |
| 154 | Themes | POST | /themes/review/batch-approve | batch_approve_themes | api/admin/themes.py | 批量审核通过 |
| **Tiers (3个)** **NEW** |
| 155 | Tiers | GET | /tiers | get_all_tiers | api/admin/tiers.py | 获取所有 Tier 配置 |
| 156 | Tiers | GET | /tiers/{tier_code} | get_tier | api/admin/tiers.py | 获取单个 Tier 配置 |
| 157 | Tiers | PUT | /tiers/{tier_code} | update_tier | api/admin/tiers.py | 更新 Tier 配置 |
| **Users (13个)** |
| 158 | Users | GET | /users | - | api/admin/users.py | 搜索用户 |
| 159 | Users | GET | /users/by-tier/{tier} | - | api/admin/users.py | 按 Tier 获取用户 |
| 160 | Users | GET | /users/{user_id} | - | api/admin/users.py | 获取用户完整审计信息 |
| 161 | Users | POST | /users/{user_id}/credits | - | api/admin/users.py | 调整用户积分 |
| 162 | Users | PATCH | /users/{user_id} | - | api/admin/users.py | 更新用户信息 |
| 163 | Users | POST | /users/{user_id}/discount | - | api/admin/users.py | 创建用户折扣 |
| 164 | Users | GET | /users/{user_id}/payments | - | api/admin/users.py | 获取用户支付记录 |
| 165 | Users | GET | /users/{user_id}/projects | - | api/admin/users.py | 获取用户项目列表 |
| 166 | Users | GET | /users/{user_id}/asset-usage | - | api/admin/users.py | 获取用户素材使用情况 |
| 167 | Users | GET | /users/{user_id}/env-stats | - | api/admin/users.py | 获取用户环境统计 |
| 168 | Users | POST | /users/projects/{project_id}/restore | - | api/admin/users.py | 恢复用户项目 |
| 169 | Users | GET | /users/projects/feed | - | api/admin/users.py | 获取项目动态流 |
| **Webhooks (2个)** |
| 170 | Webhooks | POST | /webhooks/retry | - | api/admin/webhooks_retry.py | 重试失败的 Webhooks |
| 171 | Webhooks | GET | /webhooks/failed | - | api/admin/webhooks_retry.py | 获取失败的 Webhooks |
| **Static Pages (7个)** |
| 172 | Static Pages | GET | /static-pages | list_static_pages | api/admin/static_pages.py | 列出所有静态页面 |
| 173 | Static Pages | GET | /static-pages/{page_id} | get_static_page | api/admin/static_pages.py | 获取静态页面详情 |
| 174 | Static Pages | POST | /static-pages | create_static_page | api/admin/static_pages.py | 创建静态页面 |
| 175 | Static Pages | PUT | /static-pages/{page_id} | update_static_page | api/admin/static_pages.py | 更新静态页面 |
| 176 | Static Pages | DELETE | /static-pages/{page_id} | delete_static_page | api/admin/static_pages.py | 删除静态页面 |
| 177 | Static Pages | POST | /static-pages/{page_id}/publish | publish_static_page | api/admin/static_pages.py | 发布静态页面 |
| 178 | Static Pages | POST | /static-pages/{page_id}/unpublish | unpublish_static_page | api/admin/static_pages.py | 取消发布静态页面 |
| **User Creation Monitoring (5个)** |
| 179 | Monitoring | GET | /monitoring/user-creation/stats | get_user_creation_stats | api/admin/user_creation_monitoring.py | 用户创建仪表板统计 |
| 180 | Monitoring | GET | /monitoring/user-creation/health | get_user_creation_health | api/admin/user_creation_monitoring.py | 用户创建健康状态 |
| 181 | Monitoring | GET | /monitoring/user-creation/events | get_recent_creation_events | api/admin/user_creation_monitoring.py | 最近创建事件 |
| 182 | Monitoring | GET | /monitoring/user-creation/recent | get_recent_users | api/admin/user_creation_monitoring.py | 最近注册用户列表 ⭐NEW |
| 183 | Monitoring | GET | /monitoring/user-creation/trends | get_user_creation_trends | api/admin/user_creation_monitoring.py | 用户创建趋势 ⭐NEW |

**注**: 文档共记录 183 个接口。v3.42 新增 Monitoring /recent 和 /trends (2个)。v3.41 新增 Tiers (3个)。v3.40 新增 Static Pages (7个) 和 User Creation Monitoring (3个)。

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

## 2. AI Models 管理

**版本**: v3.30 (DDD Migration)
**文件**: [api/admin/ai_models.py](../../api/admin/ai_models.py)
**路由前缀**: `/ai/models`

**架构变更** (v3.30):
- API → Domain Service → ConfigService/Shared
- 所有函数改为 async（修复同步/异步混用问题）
- 移除直接访问数据库（supabase）
- 常量移至 `domains/platform/ai/constants.py`
- 灰度发布端点移至服务层

### GET `/ai/models/config`

获取所有 AI 模型配置

**限流**: 30 req/min

**参数**: 无

**响应**:
```json
{
  "configs": {
    "text": {
      "model": "gpt-4o-mini",
      "provider": "openai",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "image": {
      "model": "flux-1.1-pro",
      "provider": "fal"
    },
    "canary": {
      "enabled": false,
      "percentage": 10,
      "target_model": null
    }
  }
}
```

**错误处理**: 失败时返回空配置 + error 字段

---

### PUT `/ai/models/config/text`

更新文本生成模型配置

**限流**: 20 req/min

**请求体**:
```json
{
  "model": "gpt-4o-mini",
  "provider": "openai",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**参数验证**:
| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `model` | string | max 100 | 模型名称（可选） |
| `provider` | string | max 50 | 提供商（可选） |
| `temperature` | float | 0.0-2.0 | 温度参数（可选） |
| `max_tokens` | int | 1-32000 | 最大 token 数（可选） |

**响应**:
```json
{
  "status": "updated",
  "config": {
    "model": "gpt-4o-mini",
    "provider": "openai",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**DDD 调用链**: API → `update_text_model_config()` (Domain) → ConfigService

---

### PUT `/ai/models/config/image`

更新图像生成模型配置

**限流**: 20 req/min

**请求体**:
```json
{
  "model": "flux-1.1-pro",
  "provider": "fal"
}
```

**参数验证**:
| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `model` | string | max 100 | 模型名称（可选） |
| `provider` | string | max 50 | 提供商（可选） |

**响应**:
```json
{
  "status": "updated",
  "config": {
    "model": "flux-1.1-pro",
    "provider": "fal"
  }
}
```

**DDD 调用链**: API → `update_image_model_config()` (Domain) → ConfigService

---

### PUT `/ai/models/config/admin`

更新管理员专用 AI 配置（占位符）

**限流**: 20 req/min

**状态**: ⚠️ TODO - 功能待实现

**响应**:
```json
{
  "status": "ok",
  "message": "Admin config updated"
}
```

---

### PUT `/ai/models/config/canary`

更新灰度发布（Canary Release）配置

**限流**: 10 req/min

**请求体**:
```json
{
  "enabled": true,
  "percentage": 10,
  "target_model": "gpt-4o"
}
```

**参数验证**:
| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `enabled` | bool | - | 是否启用灰度发布 |
| `percentage` | int | 0-100 | 灰度流量百分比 |
| `target_model` | string | max 100 | 灰度目标模型（可选） |

**响应**:
```json
{
  "status": "updated",
  "canary": {
    "enabled": true,
    "percentage": 10,
    "target_model": "gpt-4o"
  }
}
```

**DDD 调用链**: API → `update_canary_config()` (Domain) → ConfigService

---

### PUT `/ai/models/providers/toggle`

启用/禁用 AI 提供商

**限流**: 10 req/min

**请求体**:
```json
{
  "provider": "openai",
  "enabled": true
}
```

**参数验证**:
| 参数 | 类型 | 验证 | 说明 |
|------|------|------|------|
| `provider` | string | 必须在 VALID_PROVIDERS 中 | 提供商名称 |
| `enabled` | bool | - | 是否启用 |

**有效提供商**: `openai`, `fal`, `anthropic` 等（见 `domains/platform/ai/constants.py`）

**响应**:
```json
{
  "status": "updated",
  "provider": "openai",
  "enabled": true
}
```

**DDD 调用链**: API → `toggle_ai_provider()` (Domain) → ConfigService

---

### GET `/ai/models/usage`

获取 AI 使用统计

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `days` | int | 30 | 1-365 | 统计天数 |

**响应**:
```json
{
  "usage": {
    "total_requests": 1250,
    "text_requests": 850,
    "image_requests": 400,
    "by_model": {
      "gpt-4o-mini": 850,
      "flux-1.1-pro": 400
    },
    "by_provider": {
      "openai": 850,
      "fal": 400
    }
  },
  "days": 30
}
```

**错误处理**: 失败时返回空统计 + error 字段

**DDD 调用链**: API → `get_ai_usage_stats(days)` (Domain) → 数据聚合

---

### POST `/ai/models/cache/clear`

清除 AI 相关缓存

**限流**: 5 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `cache_type` | string | all | 缓存类型: text/image/all |

**cache_type 验证**:
- 必须是以下之一: `text`, `image`, `all`
- 无效值返回 400 错误

**响应**:
```json
{
  "status": "cleared",
  "cache_type": "all"
}
```

**DDD 调用链**: API → `clear_ai_cache(cache_type)` (Domain) → Redis/内存缓存

---

## 3. Articles 文章管理 **NEW**

文章 CMS 管理 API，用于管理帮助文档 (Manual)、新闻公告 (News) 和更新日志 (Changelog)。

### GET `/articles`

获取所有文章列表（含草稿）

**限流**: 10 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `category` | string | - | 分类筛选: `manual`, `news`, `changelog` |
| `include_drafts` | bool | true | 是否包含草稿 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**响应**:
```json
{
  "articles": [
    {
      "id": "uuid-xxx",
      "slug": "how-to-add-images",
      "title": "How to Add Images",
      "summary": "Learn how to upload and manage images...",
      "category": "manual",
      "tags": ["editor", "images"],
      "cover_image": "https://...",
      "is_published": true,
      "published_at": "2026-01-10T10:00:00Z",
      "view_count": 120,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-10T10:00:00Z"
    }
  ],
  "total": 45,
  "offset": 0,
  "limit": 20
}
```

---

### GET `/articles/{id}`

获取单篇文章详情（by ID）

**限流**: 10 req/min

**响应**: 完整文章对象（含 `content` 字段）

---

### POST `/articles`

创建新文章

**限流**: 10 req/min

**请求体**:
```json
{
  "title": "How to Add Images",
  "slug": "how-to-add-images",
  "content": "# How to Add Images\n\nYou can add images...",
  "summary": "Learn how to upload and manage images",
  "category": "manual",
  "tags": ["editor", "images"],
  "cover_image": "https://...",
  "sort_order": 0
}
```

**验证规则**:
- `title`: 必填，1-500 字符
- `slug`: 可选，自动从 title 生成，必须唯一
- `content`: 必填，Markdown 内容
- `category`: 必填，枚举值 `manual`, `news`, `changelog`

**响应**:
```json
{
  "success": true,
  "article": { ... }
}
```

---

### PUT `/articles/{id}`

更新文章

**限流**: 10 req/min

**请求体**: 同 POST，所有字段可选

**响应**:
```json
{
  "success": true,
  "article": { ... }
}
```

---

### DELETE `/articles/{id}`

删除文章

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "deleted": true
}
```

---

### POST `/articles/{id}/publish`

发布文章

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "published_at": "2026-01-11T10:00:00Z"
}
```

---

### POST `/articles/{id}/unpublish`

取消发布文章

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "is_published": false
}
```

**DDD 调用链**: API → `ArticleService` (Domain) → `SupabaseArticleRepository` (Infrastructure)

---

## 4. Asset Categories 分类管理

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
- `min_tier`: 必须是 `t1`/`t2`/`t3`/`t4`
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

## 5. Campaigns 营销活动

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

## 6. Config 系统配置

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

## 7. Events 事件管理

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

## 8. Experiments 实验管理

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

## 9. Feature Flags 功能开关

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

### GET `/feature-flags/tree` (v1.1 新增)

获取 Flag 树状结构

**限流**: 无限流

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `root_prefix` | string | - | 可选，只获取指定前缀的树 (如 "editor") |

**响应**:
```json
{
  "editor": {
    "key": "editor",
    "enabled": true,
    "children": {
      "toolbar": {
        "key": "editor_toolbar",
        "enabled": true,
        "children": {
          "drawing": {
            "key": "editor_toolbar_drawing",
            "enabled": true,
            "children": {}
          }
        }
      }
    }
  },
  "dashboard": {
    "key": "dashboard",
    "enabled": true,
    "children": {}
  }
}
```

---

### GET `/feature-flags/{key}/children` (v1.1 新增)

获取 Flag 的所有子级

**限流**: 无限流

**响应**:
```json
{
  "flag_key": "editor_toolbar",
  "children": [
    {
      "key": "editor_toolbar_drawing",
      "name": "Drawing Tools",
      "enabled": true,
      "parent_flags": ["editor", "editor_toolbar"]
    },
    {
      "key": "editor_toolbar_shapes",
      "name": "Shape Tools",
      "enabled": true,
      "parent_flags": ["editor", "editor_toolbar"]
    }
  ],
  "total": 2
}
```

---

### GET `/feature-flags/{key}/parents` (v1.1 新增)

获取 Flag 的所有父级

**限流**: 无限流

**响应**:
```json
{
  "flag_key": "editor_toolbar_drawing",
  "parents": [
    {
      "key": "editor",
      "name": "Editor",
      "enabled": true
    },
    {
      "key": "editor_toolbar",
      "name": "Editor Toolbar",
      "enabled": true
    }
  ],
  "total": 2
}
```

---

### POST `/feature-flags/{key}/batch-toggle` (v1.1 新增)

批量开关 Flag 及其子级

**限流**: 无限流

**请求体**:
```json
{
  "enabled": false,
  "include_children": true,
  "reason": "暂时关闭 toolbar 及所有子功能"
}
```

**响应**:
```json
{
  "success": true,
  "toggled_flags": [
    {"key": "editor_toolbar", "enabled": false},
    {"key": "editor_toolbar_drawing", "enabled": false},
    {"key": "editor_toolbar_shapes", "enabled": false}
  ],
  "total_toggled": 3
}
```

**审计日志**: 自动记录到 `flag_audit_logs` 表

---

### GET `/feature-flags/{key}/exposures` (v1.1 新增)

获取 Flag 曝光记录

**限流**: 无限流

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `start_date` | string | - | 开始日期 (ISO 8601) |
| `end_date` | string | - | 结束日期 (ISO 8601) |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 (最大 100) |

**响应**:
```json
{
  "flag_key": "editor_toolbar_drawing",
  "exposures": [
    {
      "id": "uuid-xxx",
      "user_id": "user_123",
      "variant": "treatment",
      "enabled": true,
      "reason": "percentage",
      "timestamp": "2026-01-12T10:30:00Z"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 50,
    "total": 1250
  }
}
```

---

### GET `/feature-flags/{key}/exposures/stats` (v1.1 新增)

获取 Flag 曝光统计

**限流**: 无限流

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `start_date` | string | - | 开始日期 |
| `end_date` | string | - | 结束日期 |

**响应**:
```json
{
  "flag_key": "editor_toolbar_drawing",
  "total_exposures": 12345,
  "unique_users": 5678,
  "variant_distribution": {
    "control": {"count": 6000, "percentage": 48.6},
    "treatment": {"count": 6345, "percentage": 51.4}
  },
  "reason_distribution": {
    "percentage": 11000,
    "whitelist": 500,
    "rule": 845,
    "parent_disabled": 0
  },
  "daily_trend": [
    {"date": "2026-01-12", "exposures": 1234, "unique_users": 567},
    {"date": "2026-01-11", "exposures": 1180, "unique_users": 532}
  ]
}
```

---

## 10. Logs 日志审计

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

## 11. Metrics 系统指标

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

## 12. Moderation 内容审核

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

## 13. Notifications 通知管理

> v3.33 更新: 新增 Admin Notification Templates CRUD 端点
> 文件: [api/admin/notifications.py](../../api/admin/notifications.py)
> 版本: v3.33 (Admin Template CRUD Support)

**架构**: API → Domain Service → Repository

### 13.1 Template CRUD Endpoints (v3.33 新增)

#### GET `/notifications`

列出通知模板列表

**限流**: 60 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `status` | string | - | 状态筛选: draft, scheduled, sent, failed |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 20 | 每页数量 (1-100) |

**响应**:
```json
{
  "notifications": [
    {
      "id": "uuid-xxx",
      "title": "系统维护通知",
      "message": "我们将在周日凌晨进行系统维护",
      "type": "announcement",
      "channel": "in_app",
      "status": "draft",
      "target_users": null,
      "target_tiers": ["t2", "t3"],
      "scheduled_at": null,
      "sent_at": null,
      "created_by": "admin_xxx",
      "created_at": "2026-01-20T10:00:00Z",
      "updated_at": "2026-01-20T10:00:00Z",
      "stats": null
    }
  ],
  "total": 15
}
```

---

#### GET `/notifications/{id}`

获取单个通知模板

**限流**: 60 req/min

**响应**:
```json
{
  "id": "uuid-xxx",
  "title": "系统维护通知",
  "message": "我们将在周日凌晨进行系统维护",
  "type": "announcement",
  "channel": "in_app",
  "status": "draft",
  "target_users": null,
  "target_tiers": ["t2", "t3"],
  "scheduled_at": null,
  "sent_at": null,
  "created_by": "admin_xxx",
  "created_at": "2026-01-20T10:00:00Z",
  "updated_at": "2026-01-20T10:00:00Z",
  "stats": null
}
```

**错误**:
- 404: 通知模板不存在

---

#### POST `/notifications`

创建通知模板（草稿）

**限流**: 30 req/min

**请求体**:
```json
{
  "title": "系统维护通知",
  "message": "我们将在周日凌晨 2:00-4:00 进行系统维护",
  "type": "announcement",
  "channel": "in_app",
  "target_users": null,
  "target_tiers": ["t2", "t3"],
  "scheduled_at": "2026-01-21T02:00:00Z"
}
```

**type 可选值**: `info`, `warning`, `error`, `success`, `announcement`, `system`, `alert`, `promo`

**channel 可选值**: `in_app`, `email`, `push`, `all`

**响应**: 创建的通知模板对象

---

#### PUT `/notifications/{id}`

更新通知模板

**限流**: 30 req/min

**请求体**: 与 POST 相同，所有字段可选

**限制**: 只能更新 `draft` 或 `scheduled` 状态的通知

**错误**:
- 404: 通知模板不存在
- 400: 无法编辑已发送的通知

---

#### DELETE `/notifications/{id}`

删除通知模板

**限流**: 30 req/min

**限制**: 只能删除 `draft` 或 `scheduled` 状态的通知

**响应**:
```json
{
  "success": true,
  "message": "Notification deleted"
}
```

**错误**:
- 404: 通知模板不存在
- 400: 无法删除已发送的通知

---

#### POST `/notifications/{id}/send`

发送通知模板

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "template_id": "uuid-xxx",
  "total_recipients": 1542,
  "delivered": 1538,
  "failed": 4
}
```

**错误**:
- 404: 通知模板不存在
- 400: 无法发送已发送的通知

---

### 13.2 Legacy Sending Endpoints (保持向后兼容)

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

## 14. Static Pages 静态页面管理

> v3.40 更新：使用新的 Static Pages CMS 系统，完整 CRUD 支持。
> 设计文档：[static-pages-cms-design.md](static-pages-cms-design.md)
> 文件：[api/admin/static_pages.py](../../api/admin/static_pages.py)
> 版本：v1.1.0 (Container DI Migration)

**架构**: API → Container → StaticPageService → Repository

### GET `/static-pages`

列出所有静态页面（包含草稿）

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page_type` | string | - | 页面类型筛选: legal, company, guide, other |
| `include_drafts` | bool | true | 是否包含未发布页面 |
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 (1-100) |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "slug": "privacy-policy",
      "title": "Privacy Policy",
      "subtitle": "Your privacy matters",
      "page_type": "legal",
      "icon": "Shield",
      "is_published": true,
      "last_updated_display": "January 2026",
      "sort_order": 0,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 8,
  "offset": 0,
  "limit": 50
}
```

---

### GET `/static-pages/{page_id}`

获取静态页面详情（by UUID）

**限流**: 30 req/min

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `page_id` | string | 页面 UUID |

**响应**:
```json
{
  "id": "uuid-xxx",
  "slug": "privacy-policy",
  "title": "Privacy Policy",
  "subtitle": "Your privacy matters",
  "content": "# Privacy Policy\n\nMarkdown content...",
  "page_type": "legal",
  "icon": "Shield",
  "hero_gradient": "from-blue-600 to-indigo-600",
  "meta_title": "Privacy Policy | Make Decodables",
  "meta_description": "Learn about how we protect your data",
  "schema_data": { "@type": "WebPage" },
  "extra_data": {},
  "is_published": true,
  "published_at": "2026-01-01T00:00:00Z",
  "last_updated_display": "January 2026",
  "sort_order": 0,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-15T10:00:00Z"
}
```

---

### POST `/static-pages`

创建新静态页面

**限流**: 10 req/min

**请求体**:
```json
{
  "slug": "terms-of-service",
  "title": "Terms of Service",
  "content": "# Terms of Service\n\nMarkdown content...",
  "page_type": "legal",
  "subtitle": "Please read carefully",
  "icon": "FileText",
  "hero_gradient": "from-purple-600 to-pink-600",
  "meta_title": "Terms of Service | Make Decodables",
  "meta_description": "Read our terms of service",
  "schema_data": {},
  "extra_data": {},
  "last_updated_display": "January 2026",
  "sort_order": 1
}
```

**字段验证**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `slug` | string | ✅ | URL 友好标识符 (1-100 字符) |
| `title` | string | ✅ | 页面标题 (1-200 字符) |
| `content` | string | ✅ | Markdown 内容 |
| `page_type` | string | ✅ | 页面类型: legal, company, guide, other |
| `subtitle` | string | ❌ | 副标题 (最多 500 字符) |
| `icon` | string | ❌ | Lucide 图标名称 |
| `hero_gradient` | string | ❌ | CSS 渐变类名 |
| `meta_title` | string | ❌ | SEO 标题 |
| `meta_description` | string | ❌ | SEO 描述 |
| `schema_data` | object | ❌ | JSON-LD Schema |
| `extra_data` | object | ❌ | 额外数据 |
| `last_updated_display` | string | ❌ | 显示日期 |
| `sort_order` | int | ❌ | 排序权重 (默认 0) |

**响应**:
```json
{
  "success": true,
  "message": "Static page 'Terms of Service' created successfully",
  "page": { ... }
}
```

---

### PUT `/static-pages/{page_id}`

更新静态页面

**限流**: 30 req/min

**请求体**: 所有字段可选（同 POST 请求体）

**响应**:
```json
{
  "success": true,
  "message": "Static page updated successfully",
  "page": { ... }
}
```

---

### DELETE `/static-pages/{page_id}`

删除静态页面

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "message": "Static page deleted successfully"
}
```

---

### POST `/static-pages/{page_id}/publish`

发布静态页面

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "message": "Static page published successfully",
  "page": { ... }
}
```

---

### POST `/static-pages/{page_id}/unpublish`

取消发布静态页面（设为草稿）

**限流**: 10 req/min

**响应**:
```json
{
  "success": true,
  "message": "Static page unpublished successfully",
  "page": { ... }
}
```

---

## 15. Stats 统计仪表板

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

## 16. Subscriptions 订阅管理

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

## 17. System 系统管理

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
- `text` - 短文本
- `number` - 浮点数字
- `integer` - 整数
- `boolean` - 布尔值
- `json` - JSON 对象
- `array` - JSON 数组 (CMS-Lite: 用于 Landing 页面内容、定价功能列表等)
- `richtext` - Markdown/HTML 富文本 (CMS-Lite: 用于长文本内容)

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

## 18. Tasks 任务管理

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

## 19. Themes 主题管理

Theme System v2.1 - 支持 AI 批量预生成、审核工作流和主题历史追踪。

### GET `/themes`

列出所有主题（支持分页和筛选）

**限流**: 60 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 (max: 200) |
| `category` | string | - | 分类: holiday, memorial, historical, notable, campaign, special |
| `status` | string | - | 状态: draft, active, archived |
| `review_status` | string | - | 审核状态: pending, auto_approved, reviewed, rejected |
| `date_from` | string | - | 日期范围开始 (YYYY-MM-DD) |
| `date_to` | string | - | 日期范围结束 (YYYY-MM-DD) |
| `ai_generated` | bool | - | 是否 AI 生成 |

**响应**:
```json
{
  "themes": [
    {
      "id": "theme_xxx",
      "name": "World Book Day",
      "date": "2026-04-23",
      "category": "notable",
      "priority": 75,
      "review_status": "auto_approved",
      "ai_generated": true
    }
  ],
  "total": 365,
  "offset": 0,
  "limit": 50
}
```

---

### GET `/themes/generation-status`

获取主题生成状态概览

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 300 | 检查天数 (1-365) |

**响应**:
```json
{
  "total_days": 300,
  "generated": 250,
  "missing": 50,
  "review_status": {
    "pending": 10,
    "auto_approved": 200,
    "reviewed": 40,
    "rejected": 0
  },
  "missing_dates": ["2026-11-01", "2026-11-02"],
  "recommendation": "partial"
}
```

---

### GET `/themes/calendar`

获取主题日历视图

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_date` | string | ✅ | 开始日期 (YYYY-MM-DD) |
| `end_date` | string | ✅ | 结束日期 (YYYY-MM-DD) |

**响应**:
```json
{
  "start_date": "2026-04-01",
  "end_date": "2026-04-30",
  "themes": {
    "2026-04-23": {
      "id": "theme_xxx",
      "name": "World Book Day",
      "category": "notable"
    }
  },
  "total": 15
}
```

---

### GET `/themes/review/pending`

获取待审核主题

**限流**: 30 req/min

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `offset` | int | 0 | 分页偏移量 |
| `limit` | int | 50 | 每页数量 |
| `review_status` | string | - | 审核状态筛选 |

**响应**: 同 GET `/themes`

---

### GET `/themes/{theme_id}`

获取主题详情

**限流**: 60 req/min

**响应**:
```json
{
  "id": "theme_xxx",
  "name": "World Book Day",
  "name_i18n": {"en": "World Book Day", "zh": "世界读书日"},
  "date": "2026-04-23",
  "category": "notable",
  "priority": 75,
  "slogan": "Read, Dream, Grow",
  "description": "Celebrating reading",
  "theme_config": {
    "colors": {"primary": "#3B82F6"},
    "badge": {"icon": "book", "text": "Book Day"}
  },
  "ai_generated": true,
  "ai_alternatives": [
    {"id": "A", "name": "World Book Day"},
    {"id": "B", "name": "Reading Festival"}
  ],
  "selected_alternative_id": "A",
  "review_status": "reviewed",
  "reviewed_by": "admin_xxx",
  "reviewed_at": "2026-01-12T10:00:00Z"
}
```

---

### GET `/themes/{theme_id}/history`

获取主题生成历史

**限流**: 30 req/min

**响应**:
```json
{
  "theme_id": "theme_xxx",
  "current": {
    "alternatives": [...],
    "selected_id": "A",
    "recommended_id": "A"
  },
  "history": [
    {
      "generated_at": "2026-01-10T10:00:00Z",
      "alternatives": [...],
      "selected_id": "B",
      "reason": "manual_regenerate",
      "regenerated_by": "admin_xxx"
    }
  ],
  "regenerate_count": 1
}
```

---

### POST `/themes`

创建新主题

**限流**: 30 req/min

**请求体**:
```json
{
  "name": "Custom Theme",
  "date": "2026-05-01",
  "category": "special",
  "priority": 60,
  "description": "A custom theme",
  "slogan": "Your slogan",
  "theme_config": {...}
}
```

**响应**: 返回创建的主题对象

---

### PUT `/themes/{theme_id}`

更新主题

**限流**: 30 req/min

**请求体**:
```json
{
  "name": "Updated Theme Name",
  "priority": 80
}
```

**响应**: 返回更新后的主题对象

---

### DELETE `/themes/{theme_id}`

删除主题（软删除）

**限流**: 20 req/min

**响应**:
```json
{
  "status": "deleted",
  "theme_id": "theme_xxx"
}
```

---

### POST `/themes/batch-generate`

批量生成主题（AI 自动选择最佳方案）

**限流**: 5 req/min

**请求体**:
```json
{
  "start_date": "2026-01-01",
  "days": 30,
  "overwrite": false
}
```

**响应**:
```json
{
  "generated": 25,
  "skipped": 5,
  "failed": 0,
  "details": [
    {
      "date": "2026-01-01",
      "theme_id": "theme_xxx",
      "name": "New Year",
      "status": "success"
    }
  ]
}
```

---

### POST `/themes/{theme_id}/review`

审核主题

**限流**: 30 req/min

**请求体**:
```json
{
  "action": "approve",
  "notes": "Looks good"
}
```

**Action 类型**:
- `approve` - 批准当前选择
- `reject` - 拒绝主题
- `switch` - 切换到其他备选方案（需要 `alternative_id`）

**响应**:
```json
{
  "theme": {...},
  "message": "Theme approved successfully"
}
```

---

### POST `/themes/{theme_id}/regenerate`

重新生成主题（保留历史）

**限流**: 10 req/min

**请求体**:
```json
{
  "reason": "Need better alternatives"
}
```

**响应**:
```json
{
  "theme": {...},
  "message": "Theme regenerated successfully",
  "history_count": 2
}
```

---

### POST `/themes/review/batch-approve`

批量审核通过

**限流**: 10 req/min

**请求体**:
```json
{
  "theme_ids": ["theme_1", "theme_2", "theme_3"]
}
```

**响应**:
```json
{
  "approved": 3,
  "failed": 0
}
```

---

## 20. Tiers 配置管理

> **NEW** v3.41 (2026-01-20)

### GET `/tiers`

获取所有 Tier 配置

**限流**: 30 req/min

**响应**:
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
      "features": {
        "pdf_export": true,
        "zip_export": "trial",
        "basic_editor": true,
        "vector_tools": false,
        "freehand_tools": false,
        "clipboard_paste": false,
        "platform_assets": true,
        "upload_image": true,
        "upload_advanced": false,
        "save_assets": false,
        "history_assets": false,
        "browse_marketplace": true,
        "purchase_marketplace": false,
        "publish_marketplace": false,
        "ai_features": true
      }
    }
  ]
}
```

---

### GET `/tiers/{tier_code}`

获取单个 Tier 配置

**限流**: 30 req/min

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `tier_code` | string | Tier 代码: t1, t2, t3, t4 |

**响应**: 同上单个 tier 对象

**错误码**:
| 状态码 | 说明 |
|--------|------|
| 400 | 无效的 tier_code |

---

### PUT `/tiers/{tier_code}`

更新 Tier 配置

**限流**: 10 req/min

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `tier_code` | string | Tier 代码: t1, t2, t3, t4 |

**请求体**:
```json
{
  "display_name": "Starter Plan",
  "enabled": true,
  "monthly_credits": 100,
  "max_projects": 3,
  "price_original": 9.9,
  "price_current": 6.9,
  "ai_queue_priority": "normal",
  "topup_discount": 0.9,
  "features": {
    "pdf_export": true,
    "zip_export": true,
    "vector_tools": true
  }
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `display_name` | string | 用户看到的显示名称 |
| `enabled` | boolean | 是否启用 (t1 不可禁用) |
| `monthly_credits` | integer | 月度积分配额 |
| `max_projects` | integer | 最大项目数 |
| `price_original` | number | 原价 (用于划线) |
| `price_current` | number | 现价 |
| `ai_queue_priority` | string | AI 队列优先级: low/normal/high |
| `topup_discount` | number | 充值折扣 (0-1) |
| `features` | object | 功能权限配置 |

**响应**: 返回更新后的完整 Tier 配置

**审计日志**: 记录到 `admin_operations` 表

---

## 21. Users 用户管理

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
      "credits_monthly": 100,
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
    "credits_monthly": 100,
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
    "monthly": 100,
    "permanent": 250,
    "total": 350
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

## 22. User Creation Monitoring 用户创建监控

> v3.42 更新：新增 /recent 和 /trends 端点，重构 /stats 端点格式。
> 文件：[api/admin/user_creation_monitoring.py](../../api/admin/user_creation_monitoring.py)
> 版本：v1.1.0

**用途**: 监控用户创建情况、展示仪表板统计、追踪创建趋势

### GET `/monitoring/user-creation/stats`

获取用户创建仪表板统计数据（用于前端 User Monitoring 面板）

**限流**: 无

**参数**: 无

**响应**:
```json
{
  "today": 15,
  "yesterday": 12,
  "this_week": 85,
  "this_month": 320,
  "change_percent": 25.0,
  "hourly_breakdown": [
    {"hour": 0, "count": 2},
    {"hour": 1, "count": 1},
    {"hour": 2, "count": 0},
    ...
    {"hour": 23, "count": 3}
  ]
}
```

**关键指标**:
- `today`: 今日创建用户数
- `yesterday`: 昨日创建用户数
- `this_week`: 本周创建用户数
- `this_month`: 本月创建用户数
- `change_percent`: 与昨日相比的变化百分比
- `hourly_breakdown`: 今日每小时创建数（24 小时）

---

### GET `/monitoring/user-creation/health`

获取用户创建系统的健康状态（用于 Webhook 健康监控）

**限流**: 无

**参数**:
| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `days` | int | 7 | 1-90 | 统计周期（天数） |

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "degraded",
    "stats": { ... },
    "alerts": [
      {
        "severity": "warning",
        "metric": "webhook_success_rate",
        "value": 93.5,
        "threshold": 95,
        "message": "Webhook success rate is below target: 93.5%"
      }
    ],
    "recommendations": [
      "Monitor Clerk webhook delivery delays"
    ],
    "evaluated_at": "2026-01-17T10:30:00Z"
  }
}
```

**健康状态**:
- `healthy`: 所有指标正常
- `degraded`: 部分指标低于预期
- `unhealthy`: 关键指标异常

**告警级别**:
- `critical`: 需要立即处理
- `warning`: 需要关注

---

### GET `/monitoring/user-creation/events`

获取最近的用户创建事件（包含 Webhook/JIT 来源信息）

**限流**: 无

**参数**:
| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `limit` | int | 50 | 1-100 | 返回的最大事件数 |

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "user_id": "user_123",
      "email": "user@example.com",
      "created_by_source": "webhook",
      "user_created_at": "2026-01-17T10:30:00Z",
      "log_action": "created",
      "delay_seconds": 0.5
    },
    {
      "user_id": "user_124",
      "email": "another@example.com",
      "created_by_source": "jit",
      "user_created_at": "2026-01-17T10:31:00Z",
      "log_action": "created",
      "delay_seconds": null
    }
  ],
  "count": 2
}
```

**用途**:
- 查看最近的用户创建情况
- 分析 Webhook vs JIT 创建分布
- 调试 race condition 问题

---

### GET `/monitoring/user-creation/recent` ⭐ NEW

获取最近注册的用户列表（用于前端 Recent Registrations 展示）

**限流**: 无

**参数**:
| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `offset` | int | 0 | ≥0 | 偏移量 |
| `limit` | int | 20 | 1-100 | 返回的最大用户数 |

**响应**:
```json
{
  "users": [
    {
      "id": "uuid-123-456",
      "user_id": "user_2abc3def...",
      "email": "user@example.com",
      "tier": "t1",
      "source": "webhook",
      "created_at": "2026-01-20T10:30:00Z"
    },
    {
      "id": "uuid-789-012",
      "user_id": "user_4ghi5jkl...",
      "email": "another@example.com",
      "tier": "t2",
      "source": "jit",
      "created_at": "2026-01-20T09:15:00Z"
    }
  ],
  "total": 1250
}
```

**用途**:
- 前端 User Monitoring 面板的 "Recent Registrations" 展示
- 支持分页浏览所有用户

---

### GET `/monitoring/user-creation/trends` ⭐ NEW

获取用户创建趋势数据（用于前端趋势图表展示）

**限流**: 无

**参数**:
| 参数 | 类型 | 默认 | 可选值 | 说明 |
|------|------|------|--------|------|
| `period` | string | week | day, week, month | 统计周期 |

**响应**:
```json
{
  "trends": [
    {
      "date": "2026-01-14",
      "count": 15,
      "tier_breakdown": {
        "t1": 10,
        "t2": 3,
        "t3": 2
      }
    },
    {
      "date": "2026-01-15",
      "count": 18,
      "tier_breakdown": {
        "t1": 12,
        "t2": 4,
        "t3": 2
      }
    },
    ...
  ],
  "period": "week"
}
```

**用途**:
- 展示用户创建趋势图表
- 按 tier 分类显示创建数量（Free/Starter/Pro）
- 支持 day（1天）、week（7天）、month（30天）周期

---

## 23. Webhooks 重试管理

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

*文档版本: v3.42*
*最后更新: 2026-01-20*

**更新内容** (v3.42):
- ✅ User Creation Monitoring 模块扩展 (3→5个接口)
  - ⭐ NEW: GET /monitoring/user-creation/recent - 最近注册用户列表
  - ⭐ NEW: GET /monitoring/user-creation/trends - 用户创建趋势图表
  - 🔄 重构 GET /monitoring/user-creation/stats - 新增仪表板格式 (today/yesterday/this_week/this_month/hourly_breakdown)
- ✅ 总接口数: 183 个

**更新内容** (v3.41):
- ✅ 新增 "Tiers 管理" 模块 (3个接口)
- ✅ 总接口数: 181 个

**更新内容** (v3.40):
- ✅ 新增 "User Creation Monitoring 用户创建监控" 模块 (3个接口)
  - GET /monitoring/user-creation/stats - 用户创建统计
  - GET /monitoring/user-creation/health - 健康状态检查
  - GET /monitoring/user-creation/events - 最近创建事件
- 🔄 重写 Section 14 "Static Pages 静态页面管理" 模块 (7个接口)
  - 使用新的 `/static-pages` 路由替代旧的 `/pages`
  - 完整 CRUD + 发布/取消发布功能
  - Container-based DI 架构
- ✅ 修正 Themes 模块接口数量 (12→13个)
- ✅ 总模块数: 22 个
- ✅ 总接口数: 178 个

**更新内容** (v3.39):
- ✅ 新增 "Themes 主题管理" 模块 (13个接口)，Theme System v2.1
  - 完整 CRUD 操作 (list/get/create/update/delete)
  - AI 批量预生成 (batch-generate)
  - 审核工作流 (review/batch-approve)
  - 主题历史追踪 (regenerate/history)
  - 日历视图和生成状态
- ✅ 总模块数: 21 个
- ✅ 总接口数: 171 个

**更新内容** (v3.37):
- ✅ 新增 "Pages 静态页面管理" 模块 (已在 v3.40 重写)
- ✅ 总模块数: 20 个

**更新内容** (v3.36):
- ✅ 新增 Feature Flags 相关端点

**更新内容** (v3.33):
- 🚨 删除虚构的 "AI Models 管理" 模块 (8个不存在的接口)
- ✅ 新增 "Asset Categories 分类管理" 模块 (7个接口)
- ✅ 修正 "System 系统管理" 接口数量 (11→12个)
- ✅ 添加完整的接口总览表格 (135个接口)
- ✅ 更新 "AI Insights" 模块接口细节 (基于实际代码 v3.27)
- ✅ 所有接口信息从实际代码中提取，确保准确性
- ✅ 包含所有请求参数、响应格式、验证规则和限流配置
