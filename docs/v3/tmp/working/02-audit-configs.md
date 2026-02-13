# 02 - 系统配置 / Tier / Feature Flags / 系统运维 审计报告

> 审计时间: 2026-02-12 ~ 2026-02-13 | 后端: config.py, tiers.py, feature_flags.py, system.py | 前端: /admin/configs, /admin/operations

---

## 1. 文档一致性

| 文档 | 版本 | 完整性 | 评价 |
|------|------|--------|------|
| v2/10-product/configs.md | 0.1.0 | 低(仅UI结构) | 浅层次 |
| v2/04-features/config-ops-design.md | 0.2.0 | 中(含接口清单) | 与config.py基本对应 |
| v2/04-features/system-ops-design.md | 0.2.0 | 高(含实现边界) | 与system.py有部分偏差 |
| v3/internal/configs.md | 1.0.0 | 低(🟡待补充) | 骨架文档 |
| v3/internal/operations.md | 1.0.0 | 低(🟡待补充) | 骨架文档 |

## 2. 文档 → API 覆盖度

| 模块 | 端点数 | 文档覆盖 | 状态 |
|------|:---:|:---:|------|
| config.py | 8 | 8/8 | ✅ 100% |
| tiers.py | 3 | 3/3 | ✅ 100% |
| feature_flags.py | 9 | 8/9 | ⚠️ GET /client/flags 未文档化 |
| system.py | 12 | 12/12 | ✅ 100% |

## 3. API → 前端覆盖度

### /admin/configs 页面 — ✅ 基本完整

| 问题 | 详情 |
|------|------|
| ⚠️ | createConfig() 和 deleteConfig() 在 v2 文档未提及 |
| ⚠️ | updateRateLimit() 端点后端不存在 — 前端调用会失败 |

### /admin/operations 页面 — 🔴 严重缺口

| 功能分类 | 期望端点 | 已实现 | 缺口 |
|---------|---------|--------|------|
| 系统配置 | 7 | 3 | bulkUpdateConfigs, getConfigHistory, resetConfig, exportConfigs |
| 缓存管理 | 5 | 4 | getCacheValue |
| 通知管理 | 6 | 6 | ✅ (→ 见 07-audit-notifications-analytics.md) |
| Webhook重试 | 3 | 2 | retryAllWebhooks |
| 用户创建监控 | 3 | 3 | ✅ (→ 见 09-audit-tasks-webhooks-monitoring.md) |

## 4. 问题清单

| 编号 | 优先级 | 问题 | 审计维度 |
|------|--------|------|---------|
| C5 | 🔴 P0 | **tiers.py DDD 违规** — 直接实例化 `TierConfigRepository()` 而非通过 Container DI 注入，违反架构规范，无法统一管理生命周期和测试 mock | D5 + CL-3.3 |
| H3 | 🟡 P1 | **feature_flags.py 全局 Service 导入** — 在模块级导入 `feature_service` 全局实例而非通过 Container DI，测试时无法 mock，生命周期管理不一致 | D5 + CL-3.3 |
| M7 | 🟢 P2 | **config.py batch_update_configs 无事务保护** — 批量更新多个配置项非原子操作，部分失败时状态不一致 | D19 |
| - | ⚠️ | updateRateLimit() 前端调用后端不存在的端点 | D9 |
| - | ⚠️ | v3 文档骨架待补充 | D2 |

### DDD 合规状态

| 模块 | Container DI | Service 层 | 状态 |
|------|:---:|:---:|------|
| config.py | ✅ | ✅ | 合规 |
| tiers.py | ❌ 直接创建 Repository | ✅ | ⚠️ C5 |
| feature_flags.py | ❌ 全局导入 Service | ✅ | ⚠️ H3 |
| system.py | ✅ | ✅ | 合规 |

### 修复建议

1. **C5**: tiers.py 迁移到 `container.tier_config_service` 注入模式 (参考 config.py 实现)
2. **H3**: feature_flags.py 改为 `Depends(get_feature_service)` 依赖注入
3. **M7**: batch_update_configs 包裹在数据库事务中，或改用 RPC 原子操作

## 5. 总评

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档一致性 | ⚠️ | v2 详细，v3 骨架待补充 |
| 文档→API | ✅ | 31/32 端点有文档对应 |
| API→前端 | ⚠️ | updateRateLimit 端点后端不存在 |
| DDD 合规 | ⚠️ | tiers.py (C5) + feature_flags.py (H3) 违规 |
| 安全加固 | ✅ | 速率限制已配置 |
| 职责边界 | ✅ | config.py vs system.py 清晰 |

**总体评分**: 🟡 中 — v2 API 实现完整，核心问题在 DDD 违规 + v3 文档缺失 + operations 前端对齐

## 6. 跨层审计 (D17-D25) 复核

- D5 (DDD 合规): 🔴 C5 — tiers.py 直接创建 Repository; H3 — feature_flags.py 全局导入
- D17 (参数一致性): ✅ 无显著问题
- D19 (批量原子性): 🟡 M7 — batch_update_configs 非原子
- D25 (性能): ✅ 无 N+1 风险
