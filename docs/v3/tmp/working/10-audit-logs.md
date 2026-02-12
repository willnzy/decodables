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
