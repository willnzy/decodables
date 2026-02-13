# 10 - 日志/审计 审计报告

> 审计时间: 2026-02-12 ~ 2026-02-13 | 后端: logs.py | 前端: /admin (主面板)

---

## A. API 端点清单

| # | Method | Path | 功能 | 前端调用 | 文档 |
|---|--------|------|------|----------|------|
| 1 | GET | /logs/errors | 错误日志 (含过滤分页) | ✅ adminGetErrorLogs | ❌ |
| 2 | GET | /logs/errors/stats | 错误统计 | ✅ adminGetErrorStats | ❌ |
| 3 | GET | /logs/operations | 管理员操作日志 | ✅ adminGetOperationLogs | ❌ |
| 4 | GET | /logs/operations/export | 导出操作日志 CSV | ✅ adminExportOperationLogs | ❌ |
| 5 | GET | /logs/audit | 综合审计日志 | ❌ (后端有但前端未调用) | ❌ |

**前端覆盖**: 4/5 (80%) 🟡 | **DDD 合规**: ✅ v3.29 Container DI | **安全**: ✅ 查询 30/min, 导出 10/min

## B. 问题清单

| 编号 | 优先级 | 问题 | 审计维度 |
|------|--------|------|---------|
| → C8 | 🔴 P0 | **跨层参数不匹配** — 后端返回 offset/limit/has_more，前端类型定义期望 page/page_size。此为系统性问题，logs 模块尤为明显 (`ErrorLogsResponse`/`OperationLogsResponse`/`AuditLogsResponse`)。详见 01-audit-users.md C8 | D17 |
| → H12 | 🟡 P1 | **日志格式不统一** — 前端 `adminApiClient.ts` 直接使用 `console.log()` 违反前端日志规范。此为跨模块问题，详见 09-audit-tasks-webhooks-monitoring.md H12 | D23 + CL-4.2 |
| - | 🟡 P2 | /logs/audit 端点后端完整实现 (含 6 个过滤字段) 但前端无对应 UI | D9 |
| - | 🔴 P0 | 文档完全缺失 (5 端点零文档覆盖) | D2 |

> **编号说明**: `→ C8` 和 `→ H12` 表示该问题的主条目在其他文件中定义，本文件为交叉引用。C8 首次发现于 01-audit-users.md (系统级问题)，H12 首次定义于 09-audit-tasks-webhooks-monitoring.md (跨模块日志问题)。

### 修复建议

1. **C8**: 前端 `admin/_lib/types.ts` 中 `ErrorLogsResponse`/`OperationLogsResponse` 类型改为 `offset/limit/has_more`，`admin/_lib/api.ts` 中参数从 `page/page_size` 改为 `offset/limit`
2. **H12**: 前端 `adminApiClient.ts` 中 `console.log()` 替换为 Logger 类调用

## C. 总评

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档覆盖 | 🔴 | 5 端点零文档 |
| API→前端 | 🟡 | 4/5 端点有前端调用，/logs/audit 闲置 |
| DDD 合规 | ✅ | v3.29 Container-based DI |
| 安全加固 | ✅ | 查询 30/min, 导出 10/min |
| 跨层参数 | 🔴 | → C8 page/limit vs offset/limit 系统性问题 |

**总体评分**: 🟡 中 — DDD 和安全合规，但 C8 参数不匹配影响运行时分页
