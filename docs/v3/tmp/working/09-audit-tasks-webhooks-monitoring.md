# 09 - 任务管理 + Webhook 重试 + 用户创建监控 审计报告

> 审计时间: 2026-02-12 ~ 2026-02-13 | 后端: tasks_mgmt.py, webhooks_retry.py, user_creation_monitoring.py | 前端: /admin, /admin/operations

---

## A. Task Management (tasks_mgmt.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | 文档 |
|---|--------|------|------|----------|------|
| 1 | GET | /tasks/management/status | 获取所有计划任务状态 | ✅ useTaskStatus | ❌ |
| 2 | GET | /tasks/management/logs | 获取任务执行日志 | ✅ AdminService | ❌ |
| 3 | GET | /tasks/management/health | 任务系统健康状态 | ✅ AdminService | ❌ |
| 4 | POST | /tasks/management/{task_name}/run | 手动触发任务 | ✅ AdminService | ❌ |

**前端覆盖**: 4/4 (100%) ✅ | **DDD 合规**: ✅ v3.29 Container DI | **安全**: ✅ 差异化限流

**注意**: 前端 cancelTask()/retryTask() 已声明但后端无对应端点 (stub)

---

## B. Webhook Retry (webhooks_retry.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | 文档 |
|---|--------|------|------|----------|------|
| 1 | POST | /webhooks/retry | 手动触发 webhook 重试 | ✅ WebhookRetryPanel | ❌ |
| 2 | GET | /webhooks/failed | 查看失败 webhook 列表 | ✅ WebhookRetryPanel | ❌ |

**前端覆盖**: 2/2 (100%) ✅ | **DDD 合规**: ✅ v1.1.0 Container DI | **安全**: ✅ 重试 10/hour

---

## C. User Creation Monitoring (user_creation_monitoring.py) — 🔴 复合 P0

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | 文档 |
|---|--------|------|------|----------|------|
| 1 | GET | /monitoring/user-creation/stats | 用户创建仪表板统计 | ✅ UserMonitoringPanel | ❌ |
| 2 | GET | /monitoring/user-creation/health | 创建系统健康状态 | ❌ | ❌ |
| 3 | GET | /monitoring/user-creation/events | 最近创建事件 | ❌ | ❌ |
| 4 | GET | /monitoring/user-creation/recent | 最近注册用户列表 | ✅ UserMonitoringPanel | ❌ |
| 5 | GET | /monitoring/user-creation/trends | 用户创建趋势 | ✅ UserMonitoringPanel | ❌ |

**前端覆盖**: 3/5 (60%) 🟡 | **DDD 合规**: ❌ 全面违规 | **安全**: ❌ 无速率限制

---

## D. 问题清单

| 编号 | 优先级 | 问题 | 模块 | 审计维度 |
|------|--------|------|------|---------|
| C6 | 🔴 P0 | **tasks_mgmt.py 第 165 行缺少 await** — 异步函数调用缺少 `await`，协程对象被创建但从未执行，相关任务操作静默失败，无错误日志 | tasks_mgmt | D3 + CL-4.1 |
| C10 | 🔴 P0 | **user_creation_monitoring 全面违规** — 复合问题 (见下表) | monitoring | D5+D6+CL-3.10 |
| H11 | 🟡 P1 | **日志格式不统一** — tasks_mgmt.py 使用格式字符串而非 `event: "module.action"` 结构化格式；前端 `adminApiClient.ts` 直接使用 `console.log()` 违反前端日志规范 (→ 也影响 10-audit-logs.md 中 logs 模块) | D23 + CL-4.2 |
| - | 🟡 P2 | 前端 cancelTask/retryTask stub 函数无后端实现 | tasks_mgmt | D9 |
| - | 🟡 P1 | health + events 端点无前端集成 | monitoring | D9 |

### C10 详细分解

| # | 问题类型 | 详情 |
|---|---------|------|
| 1 | Container DI 缺失 | 未使用 Container-based DI，直接调用 `UserCreationMonitoringService` 单例 |
| 2 | 速率限制缺失 | 所有 5 个端点无 @limiter 装饰器，监控端点可被滥用 |
| 3 | PII 泄露 | `/events` 端点返回未脱敏用户邮箱 |

### 修复建议

1. **C6** (5min): tasks_mgmt.py 第 165 行添加 `await` 关键字
2. **C10** (3h):
   - 迁移到 Container DI: `container = get_container()` → `service = container.user_creation_monitoring_service`
   - 添加 `@limiter.limit("30/minute")` 到所有端点
   - `/events` 响应中邮箱使用 `mask_email()` 脱敏
3. **H11** (30min): 将 `logger.info(f"...")` 改为 `logger.info("admin.task.xxx", extra={...})`；前端 `adminApiClient.ts` 中 `console.log()` 替换为 Logger 类调用

## E. 总评

| 指标 | Tasks | Webhooks | Monitoring | **合计** |
|------|:---:|:---:|:---:|:---:|
| 端点数 | 4 | 2 | 5 | **11** |
| 前端覆盖 | 4 (100%) | 2 (100%) | 3 (60%) | **9 (82%)** |
| 文档覆盖 | 0 | 0 | 0 | **0 (0%)** |
| DDD 合规 | ✅ | ✅ | ❌ | **67%** |

**总体评分**: 🔴 — tasks/webhooks 合规，monitoring 全面违规 + 缺少 await 为致命缺陷
