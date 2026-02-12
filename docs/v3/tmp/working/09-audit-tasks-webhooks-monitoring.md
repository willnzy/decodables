# 09 - Task Management + Webhook Retry + User Creation Monitoring 审计

> 审计时间: 2026-02-12 | 审计维度: 后端API ↔ 前端页面 ↔ 文档覆盖

---

## A. Task Management (tasks_mgmt.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /tasks/management/status | 获取所有计划任务状态 | ✅ useTaskStatus | ❌ | ❌ |
| 2 | GET | /tasks/management/logs | 获取任务执行日志 | ✅ AdminService | ❌ | ❌ |
| 3 | GET | /tasks/management/health | 任务系统健康状态 | ✅ AdminService | ❌ | ❌ |
| 4 | POST | /tasks/management/{task_name}/run | 手动触发任务 | ✅ AdminService | ❌ | ❌ |

### 关键发现

- 🟢 **API→Frontend 100% 对齐**: 4/4 端点均有前端调用
- 🔴 **文档完全缺失**: 零文档覆盖
- 🟢 **DDD 合规**: v3.29 Container-based DI
- 🟢 **安全**: @limiter (查询30/min, 触发10/min)
- 🟡 **前端 stub**: cancelTask()/retryTask() 声明但后端无对应端点

---

## B. Webhook Retry (webhooks_retry.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | POST | /webhooks/retry | 手动触发 webhook 重试 | ✅ WebhookRetryPanel | ❌ | ❌ |
| 2 | GET | /webhooks/failed | 查看失败 webhook 列表 | ✅ WebhookRetryPanel | ❌ | ❌ |

### 关键发现

- 🟢 **API→Frontend 100% 对齐**: 2/2 端点均有前端调用
- 🔴 **文档完全缺失**: 零文档覆盖
- 🟢 **DDD 合规**: v1.1.0 Container-based DI
- 🟢 **安全**: 重试10/hour (严格限制), 查询30/min
- 🟢 **前端完整**: WebhookRetryPanel 含过滤/批量重试/Payload查看/分页

---

## C. User Creation Monitoring (user_creation_monitoring.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /monitoring/user-creation/stats | 用户创建仪表板统计 | ✅ UserMonitoringPanel | ❌ | ❌ |
| 2 | GET | /monitoring/user-creation/health | 创建系统健康状态 | ❌ | ❌ | ❌ |
| 3 | GET | /monitoring/user-creation/events | 最近创建事件 | ❌ | ❌ | ❌ |
| 4 | GET | /monitoring/user-creation/recent | 最近注册用户列表 | ✅ UserMonitoringPanel | ❌ | ❌ |
| 5 | GET | /monitoring/user-creation/trends | 用户创建趋势 | ✅ UserMonitoringPanel | ❌ | ❌ |

### 关键发现

- 🟡 **前端覆盖率 60% (3/5)**: health + events 后端有但前端未使用
- 🔴 **文档完全缺失**: 零文档覆盖
- 🔴 **DDD 违规**: 未使用 Container-based DI，直接调用 Service
- 🔴 **缺少速率限制**: 所有端点无 @limiter
- 🟡 **PII 风险**: /events 端点返回未脱敏用户邮箱

---

## D. 总评

| 指标 | Tasks | Webhooks | Monitoring | **合计** |
|------|:---:|:---:|:---:|:---:|
| 端点数 | 4 | 2 | 5 | **11** |
| 前端调用 | 4 | 2 | 3 | **9 (82%)** |
| 文档覆盖 | 0 | 0 | 0 | **0 (0%)** |

### 严重问题

| 优先级 | 问题 | 模块 |
|--------|------|------|
| 🔴 P0 | 全部 11 端点零文档 | 全部 |
| 🔴 P0 | user_creation_monitoring 违反 DDD/Container 标准 | monitoring |
| 🔴 P0 | user_creation_monitoring 缺少速率限制 | monitoring |
| 🟡 P1 | /events 端点返回未脱敏 PII | monitoring |
| 🟡 P1 | health + events 端点无前端集成 | monitoring |
| 🟡 P2 | cancelTask/retryTask stub 函数无后端实现 | tasks |
