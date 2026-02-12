# Admin 功能全面审计报告

> **审计日期**: 2026-02-12
> **审计范围**: 全部 21 个 Admin API Router 文件 × 3 维度 (后端API ↔ 前端页面 ↔ 文档覆盖)
> **目标**: 确保 Admin 页面功能完善并正常工作

---

## 一、总览

### 1.1 审计覆盖

| 批次 | 模块 | Router 文件 | 审计文件 |
|------|------|------------|----------|
| Batch 1 | 用户管理 + 配置/Tier/Flags/System | users, subscriptions, config, tiers, feature_flags, system | 01, 02 |
| Batch 2 | 主题 + 文章 + 静态页面 + 资产分类 + 审核 | themes, articles, static_pages, asset_categories, moderation | 03, 04, 05 |
| Batch 3 | 营销 + 实验 + 通知 + Analytics | campaigns, experiments, notifications, stats, metrics, events | 06, 07 |
| Batch 4 | AI + Overrides + 任务/Webhook/监控 + 日志 | ai, ai_models, overrides, tasks_mgmt, webhooks_retry, user_creation_monitoring, logs | 08, 09, 10 |

### 1.2 端点统计

| 模块 | 端点数 | 前端调用 | 对齐率 | 文档覆盖 |
|------|:---:|:---:|:---:|:---:|
| 用户管理 (users+subscriptions) | 16 | 12 | 75% | 🟡 部分 |
| 配置 (config) | 8 | 8 | 100% | ✅ v2完整 |
| Tier (tiers) | 3 | 3 | 100% | ✅ |
| Feature Flags | 9 | 8 | 89% | ✅ |
| 系统运维 (system) | 12 | 12 | 100% | ✅ |
| 主题 (themes) | 13 | 13 | 100% | 🟡 |
| 文章 (articles) | ~10 | ~8 | 80% | 🟡 |
| 静态页面 (static_pages) | 7 | 7 | 100% | 🟡 |
| 资产分类 (asset_categories) | 7 | 5 | 71% | 🔴 |
| 内容审核 (moderation) | 10 | 10 | 100% | ✅ |
| 营销活动 (campaigns) | 8 | 8 | 100% | 🔴 无文档 |
| 实验 (experiments) | 14 | 14 | 100% | 🔴 无文档 |
| 通知 (notifications) | 11 | 1 | 9% | 🔴 无文档 |
| 统计 (stats) | 18 | 8 | 44% | 🔴 无文档 |
| 指标 (metrics) | 7 | 0 | 0% | 🔴 无文档 |
| 事件 (events) | 5 | 0 | 0% | 🔴 无文档 |
| AI Insights (ai) | 5 | 5 | 100% | ✅ |
| AI Models (ai_models) | 8 | 7 | 88% | 🔴 |
| Overrides (overrides) | 3 | 0 | 0% | 🟡 v2有 |
| 任务管理 (tasks_mgmt) | 4 | 4 | 100% | 🔴 无文档 |
| Webhook重试 (webhooks_retry) | 2 | 2 | 100% | 🔴 无文档 |
| 用户监控 (user_creation_monitoring) | 5 | 3 | 60% | 🔴 无文档 |
| 日志 (logs) | 5 | 4 | 80% | 🔴 无文档 |
| **合计** | **~195** | **~142** | **~73%** | **~35%** |

---

## 二、🔴 Critical 问题 (P0 — 功能不可用)

### C1: 资产分类模块完全不可用
- **文件**: asset_categories.py ↔ 前端 admin/content
- **问题**: 后端用 `slug` 标识资源，前端用 `id`；PUT vs PATCH 不匹配；字段名全错
- **影响**: 所有 CRUD 操作都会失败
- **修复**: 统一标识符 + HTTP 方法 + 字段映射

### C2: 用户 Tier 变更调用已废弃 API
- **文件**: users.py → POST /users/{user_id}/tier 返回 410
- **问题**: 前端仍调用已废弃端点
- **影响**: Tier 变更功能完全失败
- **修复**: 前端切换到新 Tier 管理流程 (通过 Stripe)

### C3: 通知模板 CRUD (v3.33) 无前端 UI
- **文件**: notifications.py — 6 个模板端点 (GET/POST/PUT/DELETE/send)
- **问题**: 后端已实现完整的草稿→发送工作流，但前端只有 broadcast 按钮
- **影响**: 新增的通知管理功能无法使用
- **修复**: 创建 NotificationTemplatePanel 前端组件

### C4: AI Models update_admin_config 占位符
- **文件**: ai_models.py → PUT /ai/models/config/admin
- **问题**: 端点路由已注册，但实现为 TODO 占位符
- **影响**: 调用返回错误或空响应
- **修复**: 实现或删除该端点

---

## 三、🟡 High 问题 (P1 — 功能降级)

### H1: 前后端参数不一致 (多模块)
- **用户搜索**: 前端 `q/page/page_size` vs 后端 `search/offset/limit`
- **积分字段**: 前端 `credit_type` vs 后端 `bucket`
- **日志分页**: 前端 `page/limit` vs 后端 `offset/limit`
- **影响**: 分页/搜索/过滤功能可能返回错误结果

### H2: Feature Overrides 完全未集成
- **文件**: overrides.py — 3 个端点
- **问题**: 前端无任何调用 + 违反 DDD 架构 + 无速率限制/参数验证
- **决策**: 确认是否需要此功能 — 保留则需全面重构，否则删除

### H3: Metrics 全部 7 端点无前端 (空中楼阁)
- **文件**: metrics.py — daily/monthly/retention/funnel/errors/dau-trend/refresh
- **问题**: 完整后端实现 + Pydantic 模型，但零前端集成
- **决策**: 创建 Metrics Dashboard 或评估与 Stats 合并

### H4: Events 全部 5 端点无前端
- **文件**: events.py — 事件浏览/统计/聚合/触发
- **问题**: 同 Metrics，后端完整但前端为空
- **决策**: 创建 Events Browser UI 或评估需求

### H5: Stats 10 个高级端点无前端
- **文件**: stats.py — tier-distribution, tier-activity, subscription-events, page-views, project-details, returning-users, tier-trend, tier-conversion, performance, user-distribution
- **影响**: 大量数据洞察能力未暴露

### H6: user_creation_monitoring DDD 违规
- **文件**: user_creation_monitoring.py
- **问题**: 未使用 Container-based DI + 无速率限制
- **影响**: 安全风险 + 与其他模块架构不一致

### H7: Themes 批量生成端点缺失
- **文件**: themes.py
- **问题**: 前端调用 batch-generate/preview 和 status 端点，但后端未实现
- **影响**: 批量主题生成功能不可用

### H8: Articles 辅助端点缺失
- **文件**: articles.py
- **问题**: check-slug (slug 唯一性) 和 stats (文章统计) 端点前端需要但后端未实现
- **影响**: 创建文章无法检查 slug 冲突

### H9: 用户监控 PII 泄露风险
- **文件**: user_creation_monitoring.py → /events 端点
- **问题**: 返回未脱敏用户邮箱
- **修复**: 实现邮箱掩码

---

## 四、🟢 表现良好的模块

| 模块 | 三维度评分 | 亮点 |
|------|:---:|------|
| 配置管理 (config) | 9/10 | API→前端→文档 100% 对齐 |
| Tier 管理 (tiers) | 9/10 | 3 端点全部对齐 |
| 系统运维 (system) | 9/10 | 12 端点全部对齐 |
| 内容审核 (moderation) | 8.8/10 | 10 端点 100% 前端调用 |
| 营销活动 (campaigns) | 8/10 | 8 端点 100% 前端调用 (缺文档) |
| 实验 (experiments) | 8/10 | 14 端点 100% 前端调用 (缺文档) |
| AI Insights (ai) | 9.5/10 | 三维度完整对齐 |
| Webhook 重试 | 9/10 | 2 端点完整 (缺文档) |
| 任务管理 | 8.5/10 | 4 端点对齐 (缺文档) |

---

## 五、文档覆盖分析

### 5.1 文档状态矩阵

| 模块 | v2 文档 | v3 文档 | 需补充 |
|------|:---:|:---:|:---:|
| 用户管理 | ✅ 详细 | 🟡 骨架 | v3 扩展 |
| 配置/Tier/Flags | ✅ 详细 | 🟡 骨架 | v3 扩展 |
| 系统运维 | ✅ 详细 | 🟡 骨架 | v3 扩展 |
| 主题 | ✅ 详细 | 🟡 简化 | v3 扩展 |
| 文章 | ✅ 详细 | 🟡 简化 | v3 扩展 |
| 静态页面 | ✅ 详细 | 🟡 简化 | v3 扩展 |
| 资产分类 | ❌ 严重不一致 | ❌ 不一致 | 重写 |
| 内容审核 | ✅ 详细 | 🟡 骨架 | v3 扩展 |
| 营销活动 | ❌ 无 | ❌ 无 | 新建 |
| 实验 | ❌ 无 | ❌ 无 | 新建 |
| 通知 | ❌ 无 | ❌ 无 | 新建 |
| Stats/Metrics/Events | ❌ 无 | ❌ 无 | 新建 |
| AI Models | 🟡 部分 | ❌ 无 | 新建 |
| Overrides | 🟡 v2有 | ❌ 无 | 视需要 |
| 任务管理 | ❌ 无 | ❌ 无 | 新建 |
| Webhook | ❌ 无 | ❌ 无 | 新建 |
| 用户监控 | ❌ 无 | ❌ 无 | 新建 |
| 日志 | ❌ 无 | ❌ 无 | 新建 |

### 5.2 文档缺口总计
- **完全无文档的端点**: ~95 个 (占总量 49%)
- **需要新建的 v3 文档**: 约 8 份
- **需要从骨架扩展的 v3 文档**: 约 6 份

---

## 六、架构合规分析

### 6.1 DDD / Container DI 迁移状态

| 模块 | DDD 合规 | Container DI | 版本 |
|------|:---:|:---:|------|
| users | ✅ | ✅ | v3.29+ |
| config/tiers/flags | ✅ | ✅ | v3.29+ |
| system | ✅ | ✅ | v3.29+ |
| themes | ✅ | ✅ | v3.31 |
| articles | ✅ | ✅ | v3.30 |
| static_pages | ✅ | ✅ | v3.30 |
| asset_categories | ✅ | ✅ | v3.30 |
| moderation | ✅ | ✅ | v3.30 |
| campaigns | ✅ | ✅ | v3.31 |
| experiments | ✅ | ✅ | v3.32 |
| notifications | ✅ | ✅ | v3.30 |
| stats | ✅ | ✅ | v3.30 |
| metrics | ✅ | ✅ | v3.29 |
| events | ✅ | ✅ | v3.27-29 |
| ai | ✅ | ✅ | v3.27 |
| ai_models | ✅ | ✅ | v3.30 |
| **overrides** | **🔴 违规** | **❌ 直接 Supabase** | v1.0 |
| tasks_mgmt | ✅ | ✅ | v3.29 |
| webhooks_retry | ✅ | ✅ | v1.1 |
| **user_creation_monitoring** | **🔴 违规** | **❌ 直接 Service** | 未迁移 |
| logs | ✅ | ✅ | v3.29 |

**DDD 合规率**: 19/21 (90%) — 2 个模块需要迁移

### 6.2 安全配置 (Rate Limiting)

| 模块 | Rate Limiting | 状态 |
|------|:---:|:---:|
| 大部分模块 | ✅ 有 | 差异化限流 |
| **user_creation_monitoring** | **❌ 无** | 🔴 安全风险 |
| **overrides** | **❌ 无** | 🔴 安全风险 |

---

## 七、修复优先级路线图

### Phase 1: 紧急修复 (P0 — 功能不可用)
1. ~~资产分类~~: 统一 slug/id + PUT/PATCH + 字段名 (C1)
2. 用户 Tier 变更: 前端切到新流程或后端恢复端点 (C2)
3. 通知模板 CRUD: 创建前端组件 (C3)
4. AI Models 占位符: 实现或删除 (C4)

### Phase 2: 功能修复 (P1 — 功能降级)
5. 参数不一致统一 (H1): page→offset 映射层
6. Feature Overrides 决策 (H2): 保留重构 or 删除
7. Themes batch-generate 端点实现 (H7)
8. Articles check-slug + stats 端点实现 (H8)
9. user_creation_monitoring DDD 迁移 + 限流 (H6)
10. PII 脱敏 (H9)

### Phase 3: 功能完善 (P1-P2)
11. Metrics Dashboard 前端 (H3)
12. Events Browser 前端 (H4)
13. Stats 高级聚合前端 (H5)

### Phase 4: 文档补全
14. 新建 8 份 v3 文档 (campaigns, experiments, notifications, analytics, ai_models, tasks, webhooks, logs)
15. 扩展 6 份骨架 v3 文档

---

## 八、详细审计文件索引

| 文件 | 覆盖模块 |
|------|----------|
| 01-audit-users.md | 用户管理 + 订阅 |
| 02-audit-configs.md | 配置 / Tier / Feature Flags / 系统运维 |
| 03-audit-themes-articles.md | 主题 + 文章 |
| 04-audit-staticpages-categories.md | 静态页面 + 资产分类 |
| 05-audit-moderation.md | 内容审核 |
| 06-audit-marketing-experiments.md | 营销活动 + 实验 |
| 07-audit-notifications-analytics.md | 通知 + Analytics (Stats/Metrics/Events) |
| 08-audit-ai-overrides.md | AI Insights + AI Models + Feature Overrides |
| 09-audit-tasks-webhooks-monitoring.md | 任务管理 + Webhook重试 + 用户创建监控 |
| 10-audit-logs.md | 日志 & 审计 |

---

**审计完成**。共发现 **4 个 P0 (功能不可用)**、**9 个 P1 (功能降级)**、**多个 P2 (文档/优化)** 问题。
