# 审计报告：系统配置 / Tier / Feature Flags / 系统运维

## 1. 文档一致性

| 文档 | 版本 | 完整性 | 评价 |
|------|------|--------|------|
| v2/10-product/configs.md | 0.1.0 | 低(仅UI结构) | 浅层次 |
| v2/04-features/config-ops-design.md | 0.2.0 | 中(含接口清单) | 与config.py基本对应 |
| v2/04-features/system-ops-design.md | 0.2.0 | 高(含实现边界) | 与system.py有部分偏差 |
| v3/internal/configs.md | 1.0.0 | 低(🟡待补充) | 骨架文档 |
| v3/internal/operations.md | 1.0.0 | 低(🟡待补充) | 骨架文档 |

## 2. 文档 → API 覆盖度

### config.py (8/8 ✅ 100%)
所有端点完全对应文档，无遗漏。

### tiers.py (3/3 ✅ 100%)
所有端点完全对应文档，无遗漏。

### feature_flags.py (8/9 ⚠️)
- 8/8 文档记录的端点全部实现
- +1 额外端点未文档化: GET /client/flags (get_client_flags)

### system.py (12/12 ✅ 100%)
所有端点完全对应文档，无遗漏。

## 3. API → 前端覆盖度

### /admin/configs 页面 ✅ 基本完整
| 问题 | 详情 |
|------|------|
| ⚠️ | createConfig() 和 deleteConfig() 在 v2 文档未提及 |
| ⚠️ | updateRateLimit() 端点后端不存在 — 前端调用会失败 |

### /admin/operations 页面 🔴 严重缺口
| 功能分类 | 期望端点 | 已实现 | 缺口 |
|---------|---------|--------|------|
| 系统配置 | 7 | 3 | bulkUpdateConfigs, getConfigHistory, resetConfig, exportConfigs |
| 缓存管理 | 5 | 4 | getCacheValue |
| 通知管理 | 6 | 6 | ✅ (notifications.py 已实现) |
| Webhook重试 | 3 | 2 | retryAllWebhooks |
| 用户创建监控 | 3 | 3 | ✅ (user_creation_monitoring.py 已实现) |

**注意**: Agent 报告中标记 operations 页面"19个端点缺失"需进一步核实。
notifications.py 和 user_creation_monitoring.py 实际存在，但前端调用路径可能不匹配。

## 4. 职责边界: config.py vs system.py ✅ 清晰
- config.py: 系统配置、Feature Flags、速率限制 → /admin/configs
- system.py: 缓存管理、配置审计 → /admin/operations

## 5. 总结

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 文档版本一致性 | ⚠️ | v2详细，v3骨架待补充 |
| 文档→API (config-ops) | ✅ | 8/8 完全对应 |
| 文档→API (system-ops) | ✅ | 12/12 完全对应 |
| API→前端 (configs) | ⚠️ | updateRateLimit()端点后端不存在 |
| API→前端 (operations) | 🔴 | 多个前端调用路径与后端不匹配，需核实 |
| 职责边界 | ✅ | 清晰 |

**总体评分**: 🟡 中 — v2 API 实现完整，核心问题在 v3 文档缺失 + operations 前端对齐

---

## v2.0 审计补充 (2026-02-13)

### 新增发现

| 编号 | 优先级 | 问题 | 审计维度 |
|------|--------|------|---------|
| C5 | 🔴 P0 | **tiers.py DDD 违规** — 直接实例化 `TierConfigRepository()` 而非通过 Container DI 注入，违反架构规范，无法统一管理生命周期和测试 mock | D5 (DDD) + CL-3.3 |
| H3 | 🟡 P1 | **feature_flags.py 全局 Service 导入** — 在模块级导入 `feature_service` 全局实例而非通过 Container DI，测试时无法 mock，生命周期管理不一致 | D5 (DDD) + CL-3.3 |
| M7 | 🟢 P2 | **config.py batch_update_configs 无事务保护** — 批量更新多个配置项非原子操作，部分失败时状态不一致 | D19 (批量操作原子性) |

### DDD 合规状态更新

| 模块 | v1.0 评估 | v2.0 评估 | 变化 |
|------|:---:|:---:|------|
| config.py | ✅ | ✅ | 无变化 |
| tiers.py | ✅ | ⚠️ **降级** | 发现直接创建 Repository，未通过 Container DI |
| feature_flags.py | ✅ | ⚠️ **降级** | 发现全局导入 Service 实例 |
| system.py | ✅ | ✅ | 无变化 |

### 修复建议

1. **C5**: tiers.py 迁移到 `container.tier_config_service` 注入模式 (参考 config.py 实现)
2. **H3**: feature_flags.py 改为 `Depends(get_feature_service)` 依赖注入
3. **M7**: batch_update_configs 包裹在数据库事务中，或改用 RPC 原子操作
