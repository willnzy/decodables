# Admin 功能全面审计框架

## 审计目标
确保 Admin 页面功能完善且正常工作。通过三方交叉对照发现遗漏和不一致。

## 三个信息源

| 维度 | 来源 | 数量 |
|------|------|------|
| A. 文档 | v2/10-product/admin + v2/04-features/admin-capabilities + v3/internal/02-product/pages/admin | ~20个文档 |
| B. 后端 API | api/routers/admin/ 下 21 个 router 文件 | 206 个端点 |
| C. 前端页面 | app/admin/ 下 9 个页面 | 110+ API 调用 |

## 审计模块 (去除订阅管理独立模块，合并到用户管理)

| 批次 | 模块 | 文档 | API 文件 | 前端页面 |
|------|------|------|---------|---------|
| 1 | 用户管理 (含订阅) | users.md, user-ops-design.md | users.py, subscriptions.py | /admin/users |
| 1 | 系统配置/Tier/Flags | configs.md, config-ops-design.md | config.py, tiers.py, feature_flags.py, system.py | /admin/configs, /admin/operations |
| 2 | 主题管理 | themes.md | themes.py | /admin/themes |
| 2 | 文章管理 | articles.md, articles-system-design.md | articles.py | /admin/articles |
| 2 | 静态页面 CMS | content.md, static-pages-cms-design.md | static_pages.py | /admin/content |
| 2 | 资产分类 | asset-category-design.md | asset_categories.py | /admin/content |
| 2 | 内容审核 | moderation.md, moderation-system-design.md | moderation.py | /admin/moderation |
| 3 | 营销活动 | marketing.md, marketing-ops-design.md | campaigns.py | /admin/marketing |
| 3 | 实验 (A/B Test) | marketing.md, marketing-ops-design.md | experiments.py | /admin/marketing |
| 3 | 通知/广播 | operations.md | notifications.py | /admin/operations |
| 3 | Analytics/统计 | analytics.md, analytics-system-design.md | stats.py, metrics.py, events.py | /admin/analytics |
| 4 | AI 洞察 | analytics.md | ai.py | /admin/analytics |
| 4 | 缓存管理 | operations.md, system-ops-design.md | system.py | /admin/operations |
| 4 | 任务管理 | system-ops-design.md | tasks_mgmt.py | /admin (主面板) |
| 4 | Webhook 重试 | system-ops-design.md | webhooks_retry.py | /admin/operations |
| 4 | 日志/审计 | operations.md, system-ops-design.md | logs.py | /admin (主面板) |
| 4 | 用户创建监控 | ? | user_creation_monitoring.py | /admin/operations |
| 4 | Feature Overrides | ? | overrides.py | ? |
| 4 | AI 模型配置 | ? | ai_models.py | /admin/configs |

## 每个模块的审计检查项

### 检查 1: 文档完整性
- v2/10-product (产品文档) 中是否有该模块描述
- v2/04-features (功能设计) 中是否有该模块设计
- v3/internal (页面规范) 中是否有该模块规范
- 三份文档描述是否一致

### 检查 2: 文档 → API 覆盖度
- 文档描述的功能，后端 API 是否都有对应端点
- API 有但文档未提到的端点 (undocumented)

### 检查 3: API → 前端覆盖度
- API 端点是否都有前端页面/组件调用
- 前端调用的 API 路径是否与后端一致

### 检查 4: 端到端可用性 (抽查)
- 关键业务链路 前端 → API → Service → DB 是否通畅
- Service 层是否有对应实现

## 输出格式

每个模块输出：
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档: v2-product | ✅/⚠️/❌ | ... |
| 文档: v2-features | ✅/⚠️/❌ | ... |
| 文档: v3-pages | ✅/⚠️/❌ | ... |
| API 覆盖 | ✅/⚠️/❌ | ... |
| 前端覆盖 | ✅/⚠️/❌ | ... |
| 端到端 | ✅/⚠️/❌ | ... |

状态：✅ 完全对齐 | ⚠️ 存在差异 | ❌ 明显缺失

---

## v2.0 审计扩展 (2026-02-13)

> 基于 `audit-standard.md` v1.2 (25 维度 × 36 检查清单 × 287 检查项)

### 新增审计维度: 跨层一致性 (D17-D25)

v1.0 审计仅覆盖 D1-D8 (后端 API) + D9-D16 (前端页面)。v2.0 新增跨层审计:

| 维度 | 检查内容 | v2.0 发现 |
|------|---------|-----------|
| D17 | API-前端参数一致性 | 🔴 P0 — page/page_size vs offset/limit 系统性不一致 |
| D18 | 错误处理链路 (后端错误码→前端展示) | 🔴 P0 — 缺统一错误码 + 前端无 getUserFriendlyMessage |
| D19 | 批量操作原子性 + 前端回滚 | 🟡 P1 — 后端有 batch API, 前端无回滚机制 |
| D20 | 并发安全 (乐观锁/版本号) | 🟢 P2 — 无 version/etag, 多管理员并发无冲突检测 |
| D21 | 缓存一致性 | ✅ 无显著问题 |
| D22 | 认证/鉴权一致性 | 🔴 P0 — 认证 100% 但无细粒度 RBAC |
| D23 | 日志链路 (结构化日志 event 格式) | 🟡 P1 — 格式不统一, 前端有裸 console.log |
| D24 | 用户流程完整性 (CRUD) | 🔴 确认 overrides CRUD 不完整 (仅 GET/DELETE) |
| D25 | 性能 (N+1, 大数据量分页) | 🟡 P1 — overrides 循环构造有 N+1 风险 |

### 新增审计方法: DDD 合规深度检查

v2.0 将 DDD 检查从"是否分层"扩展到:
1. **Container DI 注入** — 是否通过 Container 获取 Service/Repository (而非直接实例化或全局导入)
2. **异步安全** — 是否所有异步调用都有 await
3. **参数验证** — 是否有 feature_key 白名单等输入校验
4. **PII 脱敏** — 响应数据是否脱敏处理

### 问题统计对比

| 严重度 | v1.0 | v2.0 | 增量 |
|--------|:---:|:---:|------|
| P0 | 4 | 10 | +6 (C5-C10) |
| P1 | 9 | 14 | +5 (H1-H3, H10-H14) |
| P2 | 未统计 | 8 | 新增 |
| P3 | 未统计 | 2 | 新增 |
| **总计** | 13 | **34** | +21 |

> 详见: FINAL-AUDIT-REPORT.md v2.0
