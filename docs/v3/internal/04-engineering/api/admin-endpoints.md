# Admin API 端点清单

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: v2 文档 + 代码分析)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/` 目录

---

## 一、概述

### 1.1 端点基础路径

```
/api/v2/admin/*
/api/admin/*
```

### 1.2 认证要求

所有 Admin API 需要 Admin 角色权限。

### 1.3 Rate Limit 说明

| 类型 | 限制 |
|------|------|
| 查询操作 | 30/min |
| 修改操作 | 10/min |
| 敏感操作 | 5/min |
| 高危操作 | 1/10min |

---

## 二、Users (用户管理)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/admin/users` | GET | 30/min | 用户列表 |
| `/api/admin/users/by-tier/{tier}` | GET | 30/min | 按 Tier 筛选 |
| `/api/admin/users/{user_id}` | GET | 30/min | 用户详情 |
| `/api/admin/users/{user_id}` | PATCH | 10/min | 更新用户 |
| `/api/admin/users/{user_id}/credits` | POST | 10/min | 调整积分 |
| `/api/admin/users/{user_id}/discount` | POST | 10/min | 设置折扣 |
| `/api/admin/users/{user_id}/payments` | GET | 30/min | 支付记录 |
| `/api/admin/users/{user_id}/projects` | GET | 30/min | 项目列表 |
| `/api/admin/users/{user_id}/asset-usage` | GET | 30/min | 素材使用 |
| `/api/admin/users/{user_id}/env-stats` | GET | 30/min | 环境统计 |
| `/api/admin/projects/{project_id}/restore` | POST | 10/min | 恢复项目 |
| `/api/admin/projects/feed` | GET | 30/min | 项目动态 |

---

## 三、Subscriptions (订阅管理)

| 端点 | 方法 | Rate Limit | 风险 | 说明 |
|------|------|------------|:----:|------|
| `/api/admin/subscriptions/refund` | POST | 10/min | 🔴 | 退款 |
| `/api/admin/subscriptions/subscription/cancel` | POST | 10/min | 🔴 | 取消订阅 |
| `/api/admin/subscriptions/subscription/downgrade` | POST | 10/min | 🟠 | 降级 |

---

## 四、Config (系统配置)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/config` | GET | 30/min | 获取所有配置 |
| `/api/v2/admin/config/{config_key}` | GET | 30/min | 获取单个配置 |
| `/api/v2/admin/config` | PUT | 10/min | 更新配置 |
| `/api/v2/admin/config/batch` | PUT | 10/min | 批量更新 |
| `/api/v2/admin/config/rate-limits` | GET | 30/min | 限流配置 |
| `/api/v2/admin/config/rate-limits/preset` | POST | 10/min | 应用预设 |
| `/api/v2/admin/config/rate-limits/presets` | GET | 30/min | 获取预设 |
| `/api/v2/admin/config/cache/clear` | POST | 10/min | 清除缓存 |

---

## 五、Tiers (Tier 管理)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/tiers` | GET | 30/min | Tier 列表 |
| `/api/v2/admin/tiers/{tier_code}` | GET | 30/min | Tier 详情 |
| `/api/v2/admin/tiers/{tier_code}` | PUT | 10/min | 更新 Tier |

---

## 六、Feature Flags (功能开关)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/feature-flags` | GET | Flag 列表 |
| `/api/v2/admin/feature-flags` | POST | 创建 Flag |
| `/api/v2/admin/feature-flags/{key}` | GET | Flag 详情 |
| `/api/v2/admin/feature-flags/{key}` | PATCH | 更新 Flag |
| `/api/v2/admin/feature-flags/{key}/toggle` | POST | 切换状态 |
| `/api/v2/admin/feature-flags/{key}` | DELETE | 删除 Flag |
| `/api/v2/admin/feature-flags/test-evaluation` | POST | 测试评估 |
| `/api/v2/admin/feature-flags/{key}/audit` | GET | 审计日志 |
| `/api/v2/admin/feature-flags/client/flags` | GET | 客户端 Flags |

---

## 七、Experiments (A/B 实验)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/experiments` | GET | 30/min | 实验列表 |
| `/api/v2/admin/experiments` | POST | 20/min | 创建实验 |
| `/api/v2/admin/experiments/{key}` | GET | 30/min | 实验详情 |
| `/api/v2/admin/experiments/{key}` | PUT | 20/min | 更新实验 |
| `/api/v2/admin/experiments/{key}` | DELETE | 10/min | 删除实验 |
| `/api/v2/admin/experiments/{key}/status` | PUT | 20/min | 更新状态 |
| `/api/v2/admin/experiments/{key}/results` | GET | 30/min | 实验结果 |
| `/api/v2/admin/experiments/{key}/aggregate` | POST | 10/min | 聚合数据 |
| `/api/v2/admin/experiments/aggregate-all` | POST | 5/min | 全量聚合 |
| `/api/v2/admin/experiments/cache/clear` | POST | 10/min | 清除缓存 |
| `/api/v2/admin/experiments/{key}/ai-analysis` | POST | 10/min | AI 分析 |
| `/api/v2/admin/experiments/{key}/quick-recommendation` | GET | 30/min | 快速建议 |
| `/api/v2/admin/experiments/{key}/trend` | GET | 20/min | 趋势数据 |
| `/api/v2/admin/experiments/{key}/hourly-trend` | GET | 20/min | 小时趋势 |

---

## 八、Stats (数据统计)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/admin/stats/dashboard` | GET | 30/min | 仪表盘 |
| `/api/admin/stats/user-growth` | GET | 30/min | 用户增长 |
| `/api/admin/stats/revenue` | GET | 30/min | 收入统计 |
| `/api/admin/stats/projects` | GET | 30/min | 项目统计 |
| `/api/admin/stats/credits` | GET | 30/min | 积分统计 |
| `/api/admin/stats/tier-distribution` | GET | 30/min | Tier 分布 |
| `/api/admin/stats/conversion-funnel` | GET | 30/min | 转化漏斗 |
| `/api/admin/stats/exports` | GET | 30/min | 导出统计 |
| `/api/admin/stats/assets` | GET | 30/min | 素材统计 |
| `/api/admin/stats/tier-activity` | GET | 30/min | Tier 活跃度 |
| `/api/admin/stats/subscription-events` | GET | 30/min | 订阅事件 |
| `/api/admin/stats/page-views` | GET | 30/min | 页面浏览 |
| `/api/admin/stats/project-details` | GET | 30/min | 项目详情 |
| `/api/admin/stats/returning-users` | GET | 30/min | 回访用户 |
| `/api/admin/stats/tier-trend` | GET | 30/min | Tier 趋势 |
| `/api/admin/stats/tier-conversion` | GET | 30/min | Tier 转化 |
| `/api/admin/stats/performance` | GET | 30/min | 性能指标 |
| `/api/admin/stats/user-distribution` | GET | 30/min | 用户分布 |

---

## 九、Metrics (系统指标)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/metrics/daily` | GET | 30/min | 日指标 |
| `/api/v2/admin/metrics/monthly` | GET | 30/min | 月指标 |
| `/api/v2/admin/metrics/retention` | GET | 30/min | 留存率 |
| `/api/v2/admin/metrics/funnel` | GET | 30/min | 漏斗数据 |
| `/api/v2/admin/metrics/errors` | GET | 30/min | 错误指标 |
| `/api/v2/admin/metrics/dau-trend` | GET | 30/min | DAU 趋势 |
| `/api/v2/admin/metrics/refresh` | POST | 5/min | 刷新指标 |

---

## 十、内容管理

### 10.1 Themes (主题管理)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/themes` | GET | 60/min | 主题列表 |
| `/api/v2/admin/themes/{id}` | GET | 60/min | 主题详情 |
| `/api/v2/admin/themes` | POST | 30/min | 创建主题 |
| `/api/v2/admin/themes/{id}` | PUT | 30/min | 更新主题 |
| `/api/v2/admin/themes/{id}` | DELETE | 20/min | 删除主题 |
| `/api/v2/admin/themes/batch-generate` | POST | 5/min | 批量生成 |
| `/api/v2/admin/themes/generation-status` | GET | 30/min | 生成状态 |
| `/api/v2/admin/themes/calendar` | GET | 30/min | 日历视图 |
| `/api/v2/admin/themes/review/pending` | GET | 30/min | 待审核 |
| `/api/v2/admin/themes/{id}/review` | POST | 30/min | 审核主题 |
| `/api/v2/admin/themes/{id}/regenerate` | POST | 10/min | 重新生成 |
| `/api/v2/admin/themes/{id}/history` | GET | 30/min | 历史版本 |
| `/api/v2/admin/themes/review/batch-approve` | POST | 10/min | 批量审核 |

### 10.2 Asset Categories (素材分类)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/asset-categories` | GET | 分类列表 |
| `/api/v2/admin/asset-categories/tree` | GET | 分类树 |
| `/api/v2/admin/asset-categories` | POST | 创建分类 |
| `/api/v2/admin/asset-categories/{slug}` | PATCH | 更新分类 |
| `/api/v2/admin/asset-categories/{slug}/move` | PUT | 移动分类 |
| `/api/v2/admin/asset-categories/{slug}` | DELETE | 删除分类 |
| `/api/v2/admin/asset-categories/{slug}/resources` | GET | 分类资源 |

### 10.3 Static Pages (静态页面)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/static-pages` | GET | 页面列表 |
| `/api/v2/admin/static-pages/{id}` | GET | 页面详情 |
| `/api/v2/admin/static-pages` | POST | 创建页面 |
| `/api/v2/admin/static-pages/{id}` | PUT | 更新页面 |
| `/api/v2/admin/static-pages/{id}` | DELETE | 删除页面 |
| `/api/v2/admin/static-pages/{id}/publish` | POST | 发布页面 |
| `/api/v2/admin/static-pages/{id}/unpublish` | POST | 取消发布 |

### 10.4 Articles (文章管理)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/articles` | GET | 文章列表 |
| `/api/v2/admin/articles/{id}` | GET | 文章详情 |
| `/api/v2/admin/articles` | POST | 创建文章 |
| `/api/v2/admin/articles/{id}` | PUT | 更新文章 |
| `/api/v2/admin/articles/{id}` | DELETE | 删除文章 |
| `/api/v2/admin/articles/{id}/publish` | POST | 发布文章 |
| `/api/v2/admin/articles/{id}/unpublish` | POST | 取消发布 |

---

## 十一、运营管理

### 11.1 Campaigns (营销活动)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/campaigns` | GET | 30/min | 活动列表 |
| `/api/v2/admin/campaigns/{id}` | GET | 30/min | 活动详情 |
| `/api/v2/admin/campaigns` | POST | 20/min | 创建活动 |
| `/api/v2/admin/campaigns/{id}` | PUT | 20/min | 更新活动 |
| `/api/v2/admin/campaigns/{id}` | DELETE | 10/min | 删除活动 |
| `/api/v2/admin/campaigns/{id}/activate` | POST | 10/min | 激活活动 |
| `/api/v2/admin/campaigns/{id}/pause` | POST | 10/min | 暂停活动 |
| `/api/v2/admin/campaigns/{id}/stats` | GET | 30/min | 活动统计 |

### 11.2 Notifications (通知管理)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/notifications/broadcast` | POST | 广播通知 |
| `/api/admin/notifications/notification/send` | POST | 发送通知 |
| `/api/admin/notifications/notification/batch` | POST | 批量发送 |
| `/api/admin/notifications/notification/stats` | GET | 通知统计 |
| `/api/admin/notifications/notification/history` | GET | 发送历史 |

### 11.3 Moderation (内容审核)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/moderation/marketplace/moderation/list` | GET | 待审核列表 |
| `/api/admin/moderation/marketplace/moderation/{id}` | GET | 审核详情 |
| `/api/admin/moderation/marketplace/moderation/{id}/approve` | POST | 通过审核 |
| `/api/admin/moderation/marketplace/moderation/{id}/reject` | POST | 拒绝审核 |
| `/api/admin/moderation/marketplace/moderation/{id}/delete` | POST | 删除内容 |
| `/api/admin/moderation/marketplace/moderation/{id}/unpublish` | POST | 下架内容 |
| `/api/admin/moderation/reports` | GET | 举报列表 |
| `/api/admin/moderation/reports/stats` | GET | 举报统计 |
| `/api/admin/moderation/reports/{id}` | GET | 举报详情 |
| `/api/admin/moderation/reports/{id}/respond` | POST | 处理举报 |

---

## 十二、系统运维

### 12.1 System (系统管理)

| 端点 | 方法 | Rate Limit | 风险 | 说明 |
|------|------|------------|:----:|------|
| `/api/v2/admin/system/configs` | GET | 30/min | - | 系统配置 |
| `/api/v2/admin/system/configs/groups` | GET | 30/min | - | 配置分组 |
| `/api/v2/admin/system/configs` | POST | 10/min | - | 创建配置 |
| `/api/v2/admin/system/configs/{key}` | PUT | 10/min | - | 更新配置 |
| `/api/v2/admin/system/configs/{key}` | DELETE | 10/min | 🟠 | 删除配置 |
| `/api/v2/admin/system/configs/audit` | GET | 30/min | - | 审计日志 |
| `/api/v2/admin/system/configs/cache/invalidate` | POST | 5/min | - | 失效缓存 |
| `/api/v2/admin/system/system/cache/status` | GET | 30/min | - | 缓存状态 |
| `/api/v2/admin/system/system/cache/keys` | GET | 30/min | - | 缓存键 |
| `/api/v2/admin/system/system/cache/key/{key}` | DELETE | 10/min | - | 删除缓存键 |
| `/api/v2/admin/system/system/cache/clear-all/confirm` | POST | 1/10min | 🔴 | 确认清空 |
| `/api/v2/admin/system/system/cache/clear-all` | POST | 1/10min | 🔴 | 清空缓存 |

### 12.2 Logs (日志管理)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/logs/errors` | GET | 30/min | 错误日志 |
| `/api/v2/admin/logs/errors/stats` | GET | 30/min | 错误统计 |
| `/api/v2/admin/logs/operations` | GET | 30/min | 操作日志 |
| `/api/v2/admin/logs/operations/export` | GET | 10/min | 导出日志 |
| `/api/v2/admin/logs/audit` | GET | 30/min | 审计日志 |

### 12.3 Events (事件分析)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/admin/events/events` | GET | 30/min | 事件列表 |
| `/api/admin/events/events/stats` | GET | 30/min | 事件统计 |
| `/api/admin/events/aggregated/{stat_type}` | GET | 30/min | 聚合数据 |
| `/api/admin/events/aggregated/{stat_type}/range` | GET | 30/min | 范围聚合 |
| `/api/admin/events/aggregation/run` | POST | 5/min | 执行聚合 |

### 12.4 Tasks (任务管理)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/tasks/management/status` | GET | 任务状态 |
| `/api/admin/tasks/management/logs` | GET | 任务日志 |
| `/api/admin/tasks/management/health` | GET | 健康检查 |
| `/api/admin/tasks/management/{task_name}/run` | POST | 运行任务 |

### 12.5 Webhooks (Webhook 管理)

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/webhooks/retry` | POST | 10/hour | 重试 Webhook |
| `/api/v2/admin/webhooks/failed` | GET | 30/min | 失败记录 |

### 12.6 Monitoring (监控)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/monitoring/user-creation/stats` | GET | 用户创建统计 |
| `/api/admin/monitoring/user-creation/health` | GET | 健康状态 |
| `/api/admin/monitoring/user-creation/events` | GET | 创建事件 |

---

## 十三、AI 洞察

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/ai/insights` | GET | AI 洞察 |
| `/api/admin/ai/recommendations` | GET | 推荐建议 |
| `/api/admin/ai/behavior-analysis` | GET | 行为分析 |
| `/api/admin/ai/generate-report` | POST | 生成报告 |
| `/api/admin/ai/quick-insights` | GET | 快速洞察 |

---

## 十四、端点统计

| 分类 | 模块数 | 端点数 |
|------|:------:|:------:|
| 核心管理 | 5 | 35 |
| 数据分析 | 4 | 44 |
| 内容管理 | 4 | 34 |
| 运营功能 | 3 | 23 |
| 系统运维 | 6 | 31 |
| **总计** | **22** | **~170** |

---

## 十五、敏感操作清单

| 端点 | 风险级别 | 说明 |
|------|:--------:|------|
| `POST /subscriptions/refund` | 🔴 极高 | 退款操作 |
| `POST /subscriptions/subscription/cancel` | 🔴 极高 | 取消订阅 |
| `POST /users/{id}/credits` | 🔴 极高 | 积分调整 |
| `POST /system/cache/clear-all` | 🔴 极高 | 清空缓存 |
| `DELETE /experiments/{key}` | 🟠 高 | 删除实验 |
| `DELETE /campaigns/{id}` | 🟠 高 | 删除活动 |

---

## 十六、相关文档

- [API 参考文档](./api-reference.md)
- [User API 端点](./user-endpoints.md)
- [权限系统设计](../../05-business/entitlement/system-design.md)

---

**END OF DOCUMENT**
