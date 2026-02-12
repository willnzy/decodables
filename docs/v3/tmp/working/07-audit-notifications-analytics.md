# 07 - Notifications + Analytics 审计

> 审计时间: 2026-02-12 | 审计维度: 后端API ↔ 前端页面 ↔ 文档覆盖

---

## A. Notifications (notifications.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | POST | /notifications/broadcast | 广播通知到目标用户组 | ✅ adminBroadcast | ❌ | ❌ |
| 2 | POST | /notifications/notification/send | 发送通知给单个用户 | ❌ | ❌ | ❌ |
| 3 | POST | /notifications/notification/batch | 批量发送 (最多100人) | ❌ | ❌ | ❌ |
| 4 | GET | /notifications/notification/stats | 通知统计数据 | ❌ | ❌ | ❌ |
| 5 | GET | /notifications/notification/history | 通知历史 (分页) | ❌ | ❌ | ❌ |
| 6 | GET | /notifications | 列出通知模板 (v3.33 CRUD) | ❌ | ❌ | ❌ |
| 7 | GET | /notifications/{id} | 获取单个通知模板 | ❌ | ❌ | ❌ |
| 8 | POST | /notifications | 创建通知模板 (草稿) | ❌ | ❌ | ❌ |
| 9 | PUT | /notifications/{id} | 更新通知模板 | ❌ | ❌ | ❌ |
| 10 | DELETE | /notifications/{id} | 删除通知模板 | ❌ | ❌ | ❌ |
| 11 | POST | /notifications/{id}/send | 发送通知模板 | ❌ | ❌ | ❌ |

### 关键发现

- 🔴 **前端覆盖率极低**: 仅 1/11 (9%) — 只有 broadcast 被调用
- 🔴 **v3.33 模板 CRUD (6端点) 无前端 UI**: 草稿→发送工作流后端已实现，前端未跟进
- 🔴 **文档完全缺失**: 零文档覆盖
- 🟢 **DDD 迁移完成 (v3.30)**: API → Domain Service，已从 Repository 分离
- 🟢 **安全**: rate limiting (广播5/min, 发送30/min, 批量10/min, 模板30/min)

---

## B. Analytics Stats (stats.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /stats/dashboard | 仪表板 KPI | ✅ adminGetDashboardStats | ❌ | ❌ |
| 2 | GET | /stats/user-growth | 用户增长 (日/周/月) | ✅ adminGetUserGrowthStats | ❌ | ❌ |
| 3 | GET | /stats/revenue | 收入统计 (日/周/月) | ✅ adminGetRevenueStats | ❌ | ❌ |
| 4 | GET | /stats/projects | 项目创建统计 | ✅ adminGetProjectStats | ❌ | ❌ |
| 5 | GET | /stats/credits | 积分使用统计 | ✅ adminGetCreditUsageStats | ❌ | ❌ |
| 6 | GET | /stats/tier-distribution | Tier 分布 | ❌ | ❌ | ❌ |
| 7 | GET | /stats/conversion-funnel | 转化漏斗 | ✅ adminGetConversionFunnel | ❌ | ❌ |
| 8 | GET | /stats/exports | 导出统计 | ✅ adminGetExportStats | ❌ | ❌ |
| 9 | GET | /stats/assets | 资产使用排名 | ✅ adminGetAssetUsageStats | ❌ | ❌ |
| 10 | GET | /stats/tier-activity | 按 Tier 活跃度 | ❌ | ❌ | ❌ |
| 11 | GET | /stats/subscription-events | 订阅事件 | ❌ | ❌ | ❌ |
| 12 | GET | /stats/page-views | 页面浏览统计 | ❌ | ❌ | ❌ |
| 13 | GET | /stats/project-details | 项目详情统计 | ❌ | ❌ | ❌ |
| 14 | GET | /stats/returning-users | 留存用户统计 | ❌ | ❌ | ❌ |
| 15 | GET | /stats/tier-trend | Tier 趋势 | ❌ | ❌ | ❌ |
| 16 | GET | /stats/tier-conversion | Tier 转化矩阵 | ❌ | ❌ | ❌ |
| 17 | GET | /stats/performance | Core Web Vitals | ❌ | ❌ | ❌ |
| 18 | GET | /stats/user-distribution | 用户分布 (国家/浏览器/OS) | ❌ | ❌ | ❌ |

### 关键发现

- 🟡 **前端覆盖率 44% (8/18)**: 核心 KPI 端点已实现，10个高级聚合端点无前端
- 🔴 **文档完全缺失**: 零文档覆盖
- 🟢 **Pydantic 类型安全**: v3.30 迁移完成，所有端点有响应模型
- 🟢 **rate limiting**: 统一 30/min

---

## C. Analytics Metrics (metrics.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /metrics/daily | 日度指标 (DAU/MAU/新用户/收入) | ❌ | ❌ | ❌ |
| 2 | GET | /metrics/monthly | 月度汇总 (6-24月) | ❌ | ❌ | ❌ |
| 3 | GET | /metrics/retention | 留存指标 (D1/D7/D30) | ❌ | ❌ | ❌ |
| 4 | GET | /metrics/funnel | 转化漏斗 (7-90d) | ❌ | ❌ | ❌ |
| 5 | GET | /metrics/errors | 错误指标 (24-168h) | ❌ | ❌ | ❌ |
| 6 | GET | /metrics/dau-trend | DAU 趋势 (1-365d) | ❌ | ❌ | ❌ |
| 7 | POST | /metrics/refresh | 手动刷新指标聚合 | ❌ | ❌ | ❌ |

### 关键发现

- 🔴 **前端覆盖率 0% (0/7)**: 完全无前端集成，"空中楼阁"状态
- 🔴 **文档完全缺失**: 零文档覆盖
- 🟢 **Container-based DI (v3.29)**: 架构合规
- 🟡 **与 Stats 功能重叠**: retention/funnel 在 stats.py 也有类似端点

---

## D. Analytics Events (events.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /events/events | 获取用户事件 (分页/过滤) | ❌ | ❌ | ❌ |
| 2 | GET | /events/events/stats | 事件统计 | ❌ | ❌ | ❌ |
| 3 | GET | /events/aggregated/{stat_type} | 聚合统计 (缓存) | ❌ | ❌ | ❌ |
| 4 | GET | /events/aggregated/{stat_type}/range | 时间范围聚合 (1-90d) | ❌ | ❌ | ❌ |
| 5 | POST | /events/aggregation/run | 手动触发聚合 | ❌ | ❌ | ❌ |

### 关键发现

- 🔴 **前端覆盖率 0% (0/5)**: 完全无前端集成
- 🔴 **文档完全缺失**: 零文档覆盖
- 🟢 **DDD 架构完整 (v3.27-3.29)**: Container → Service → Repository

---

## E. 总评

| 指标 | Notifications | Stats | Metrics | Events | **合计** |
|------|:---:|:---:|:---:|:---:|:---:|
| 端点数 | 11 | 18 | 7 | 5 | **41** |
| 前端调用 | 1 | 8 | 0 | 0 | **9 (22%)** |
| 文档覆盖 | 0 | 0 | 0 | 0 | **0 (0%)** |

### 严重问题汇总

| 优先级 | 问题 | 影响 |
|--------|------|------|
| 🔴 P0 | 文档完全缺失 (41端点) | 无法维护/交接 |
| 🔴 P0 | v3.33 通知模板 CRUD (6端点) 无前端 UI | 功能不可用 |
| 🔴 P1 | Metrics 全部7端点无前端 | 后端投入浪费 |
| 🔴 P1 | Events 全部5端点无前端 | 后端投入浪费 |
| 🟡 P2 | Stats 10个高级聚合端点无前端 | 数据洞察缺失 |
| 🟡 P2 | Stats vs Metrics 功能重叠 | 维护成本增加 |
