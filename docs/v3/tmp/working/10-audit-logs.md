# 10 - Logs & Audit 审计

> 审计时间: 2026-02-12 | 审计维度: 后端API ↔ 前端页面 ↔ 文档覆盖

---

## A. Logs (logs.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /logs/errors | 错误日志 (含过滤分页) | ✅ adminGetErrorLogs | ❌ | ❌ |
| 2 | GET | /logs/errors/stats | 错误统计 | ✅ adminGetErrorStats | ❌ | ❌ |
| 3 | GET | /logs/operations | 管理员操作日志 | ✅ adminGetOperationLogs | ❌ | ❌ |
| 4 | GET | /logs/operations/export | 导出操作日志 CSV | ✅ adminExportOperationLogs | ❌ | ❌ |
| 5 | GET | /logs/audit | 综合审计日志 | ❌ (后端有但前端未调用) | ❌ | ❌ |

### 关键发现

- 🟡 **前端覆盖率 80% (4/5)**: /logs/audit 端点孤立
- 🔴 **文档完全缺失**: 零文档覆盖
- 🟢 **DDD 合规**: v3.29 Container-based DI (AdminLogsService)
- 🟢 **安全**: 查询30/min, 导出10/min
- 🔴 **API 参数不一致**: 后端用 offset/limit, 前端发送 page/limit — 映射可能失败
- 🟡 **审计端点闲置**: GET /logs/audit 含6个过滤字段, 后端完整实现但前端无对应

---

## B. 总评

| 指标 | 数值 | 评级 |
|------|------|------|
| 总端点数 | 5 | - |
| API→Frontend 对齐率 | 80% (4/5) | 🟡 |
| 文档覆盖率 | 0% (0/5) | 🔴 |
| DDD 架构合规 | 100% | 🟢 |

### 严重问题

| 优先级 | 问题 | 影响 |
|--------|------|------|
| 🔴 P0 | 前端 page/limit vs 后端 offset/limit 参数不匹配 | 分页可能失败 |
| 🔴 P1 | 文档完全缺失 (5端点) | 无法维护/交接 |
| 🟡 P2 | /logs/audit 端点后端已实现但前端未集成 | 功能浪费 |

---

## v2.0 审计补充 (2026-02-13)

### 发现升级与新增

| 编号 | 优先级 | 变化 | 详情 |
|------|--------|------|------|
| C8 | 🔴 P0 升级 | v1.0 已发现但严重度低估 | 前端 page/limit 参数映射到后端 offset/limit 会导致运行时分页失败。此问题在 logs 模块尤为明显: `ErrorLogsResponse`/`OperationLogsResponse`/`AuditLogsResponse` 后端返回 offset/limit/has_more，前端类型定义期望 page/page_size | D17 |
| H12 | 🟡 P1 新增 | 日志格式部分不统一 | logs.py 整体合规 (使用 `logger.info()` + `extra` 字典)，但前端 `adminApiClient.ts` 直接使用 `console.log()` 违反前端日志规范 (应使用 Logger 类) | D23 + CL-4.2 |

### 修复建议

1. **C8**: 前端 `admin/_lib/types.ts` 中 `ErrorLogsResponse`/`OperationLogsResponse` 类型改为 `offset/limit/has_more`，`admin/_lib/api.ts` 中参数从 `page/page_size` 改为 `offset/limit`
2. **H12**: 前端 `adminApiClient.ts` 中 `console.log()` 替换为 Logger 类调用
