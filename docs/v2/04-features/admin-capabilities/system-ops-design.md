# 系统运维能力设计

> 系统配置、日志、任务与通知等运维能力的系统设计与边界说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/operations/`, `decodables/api/admin/system.py`, `decodables/api/admin/logs.py`, `decodables/api/admin/tasks_mgmt.py`, `decodables/api/admin/webhooks_retry.py`, `decodables/api/admin/notifications.py`, `decodables/api/admin/user_creation_monitoring.py`

---

## 背景

- 需要统一系统配置、日志与任务监控入口
- 需要集中处理通知与 Webhooks 重试
- 需要对高风险操作提供双重确认与审计

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一运维入口（配置、缓存、日志、任务、通知、Webhooks、监控）
- 提供可追溯的审计与安全护栏
- 支持高风险操作的确认与限流

## 能力清单

- 系统配置管理与审计
- 缓存状态查看与安全清理
- 错误/操作/审计日志检索与导出
- 任务运行状态、健康度与手动触发
- Webhooks 失败重试与列表
- 通知模板 CRUD 与发送
- 用户创建监控与趋势分析

## 关键流程

- 配置管理 → 审计记录 → 缓存失效
- 缓存清理 → 二次确认 → 审计记录
- 日志查询 → 过滤分页 → 导出
- 任务状态 → 健康检查 → 手动触发
- Webhook 失败 → 复查 → 重试
- 通知模板 → 发送 → 统计回传
- 用户创建监控 → 趋势/事件 → 健康告警

## 规则与护栏

- 配置值类型与分组校验（value_type / config_group）
- 缓存 key 与 pattern 正则校验
- 清空缓存两步确认（/confirm → /clear-all）
- 管理员权限与全接口限流
- 任务名白名单校验（hourly/daily/all/cleanup/retention）
- 日志日期格式校验（YYYY-MM-DD 或 ISO）
- Webhook 重试为高成本操作（10/hour）

## 状态与类型

- 配置分组：`tier_pricing` / `credits` / `features` / `limits` / `ai` / `notifications` / `maintenance`
- 通知类型：`info` / `warning` / `error` / `success` / `announcement`
- 通知渠道：`in_app` / `email` / `push` / `all`
- 通知状态：`draft` / `scheduled` / `sent` / `failed`
- Webhook 来源：`stripe` / `clerk` / `fal` / `other`
- Webhook 状态：`pending` / `processing` / `completed` / `failed` / `retrying`
- 缓存类型：`redis` / `memory` / `cdn`

## 数据结构

- SystemConfig：`key` / `value` / `value_type` / `config_group` / `description` / `is_active`
- ConfigHistory：`old_value` / `new_value` / `changed_by` / `changed_at`
- CacheStats：`total_keys` / `memory_used` / `hit_rate` / `miss_rate`
- Notification：`title` / `message` / `type` / `channel` / `status` / `target_users` / `target_tiers`
- FailedWebhook：`event_type` / `retry_count` / `error_message` / `next_retry_at`
- UserCreationStats：`today` / `this_week` / `change_percent` / `hourly_breakdown`

## 前端交互要点

- 面板 Tab 驱动：`configs` / `cache` / `notifications` / `webhooks` / `monitoring`
- 高危操作（清空缓存、重试 Webhook）需二次确认
- 通知模板 CRUD 与发送同屏操作
- 用户创建监控含趋势、事件与健康态提示

## 实现边界（现状）

- 前端支持配置批量更新、重置、导出接口，后端尚未实现
- 前端支持读取单个配置与历史记录，后端仅提供列表与审计汇总
- 前端缓存支持读取缓存值与按 key 删除，后端仅提供删除与列表
- 前端支持 webhook 单条重试与 retry-all，后端仅支持全量 retry
- 后端存在通知 legacy 接口（broadcast/send/batch/stats/history），前端未接入

## 接口清单（Admin）

- `GET /api/v2/admin/system/configs`
- `GET /api/v2/admin/system/configs/groups`
- `POST /api/v2/admin/system/configs`
- `PUT /api/v2/admin/system/configs/{key}`
- `DELETE /api/v2/admin/system/configs/{key}`
- `GET /api/v2/admin/system/configs/audit`
- `POST /api/v2/admin/system/configs/cache/invalidate`
- `GET /api/v2/admin/system/cache/status`
- `GET /api/v2/admin/system/cache/keys`
- `DELETE /api/v2/admin/system/cache/key/{key}`
- `POST /api/v2/admin/system/cache/clear-all/confirm`
- `POST /api/v2/admin/system/cache/clear-all`

- `GET /api/v2/admin/logs/errors`
- `GET /api/v2/admin/logs/errors/stats`
- `GET /api/v2/admin/logs/operations`
- `GET /api/v2/admin/logs/operations/export`
- `GET /api/v2/admin/logs/audit`

- `GET /api/v2/admin/tasks/management/status`
- `GET /api/v2/admin/tasks/management/logs`
- `GET /api/v2/admin/tasks/management/health`
- `POST /api/v2/admin/tasks/management/{task_name}/run`

- `POST /api/v2/admin/webhooks/retry`
- `GET /api/v2/admin/webhooks/failed`

- `GET /api/v2/admin/notifications`
- `GET /api/v2/admin/notifications/{id}`
- `POST /api/v2/admin/notifications`
- `PUT /api/v2/admin/notifications/{id}`
- `DELETE /api/v2/admin/notifications/{id}`
- `POST /api/v2/admin/notifications/{id}/send`

- `GET /api/v2/admin/monitoring/user-creation/stats`
- `GET /api/v2/admin/monitoring/user-creation/health`
- `GET /api/v2/admin/monitoring/user-creation/events`
- `GET /api/v2/admin/monitoring/user-creation/recent`
- `GET /api/v2/admin/monitoring/user-creation/trends`

## 影响范围

- 相关模块：系统运维
- 相关文档：`docs/v2/10-product/admin/admin-dashboard/operations.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/operations/`、`decodables/api/admin/system.py`、`decodables/api/admin/logs.py`、`decodables/api/admin/tasks_mgmt.py`、`decodables/api/admin/webhooks_retry.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充系统运维设计细节 | Docs Working Group |
