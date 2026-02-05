# Entitlement 系统补充审计 - 遗漏问题汇总

> **审计日期**: 2026-02-04
> **审计范围**: 全部 25 个设计文档 (01-25) 的交叉验证
> **审计目的**: 发现文档之间的不一致、遗漏场景、未覆盖的边界条件
> **基于**: 26-audit-checklist.md v1.3 + 27-audit-report-20260204.md

---

## 一、新发现的遗漏问题

### 1.1 Critical 级别 (🔴 必须立即修复)

| # | 问题 | 影响范围 | 发现位置 | 修复建议 |
|---|------|---------|---------|---------|
| C1 | **t2 maxCustomAssets 配置矛盾** | 权限控制失效 | 01:64 vs 02:564 | 统一为 50 (01 定义为权威) |
| C2 | **t1 试用期 maxCustomAssets 差分不明确** | 用户体验不一致 | 01:64 说 10，但 fallback 代码不区分 | 在 EMERGENCY_TIER_CONFIGS 增加 trial 区分 |
| C3 | **credit_pools 表未创建** | 积分二维模型无法工作 | 15 设计完整，但 DB 无此表 | 立即创建表和索引 |
| C4 | **user_feature_overrides 表未创建** | Admin 授权功能不可用 | 02/03 设计完整，但 DB 无此表 | 立即创建表 |
| C5 | **7 级优先级评估引擎未实现** | 权限评估逻辑不完整 | 04/06/24 设计完整 | 实现 evaluate_permission() |
| C6 | **subscriptions 表缺失** | 订阅信息无法持久化 | 03/13/14 引用此表 | 创建订阅表 |

### 1.2 High 级别 (🟡 应该尽快修复)

| # | 问题 | 影响范围 | 发现位置 | 修复建议 |
|---|------|---------|---------|---------|
| H1 | **feature_flags 表 parent_flags 功能未实现** | AI 功能家族依赖无法工作 | 04:176 设计了但未使用 | 实现 prerequisite 检查 |
| H2 | **Override 过期自动清理机制缺失** | 数据库膨胀 | 02:206 定义了索引但无清理任务 | 添加定时任务 |
| H3 | **UpgradeModal 触发逻辑与功能控制未关联** | UX 流程断裂 | 05:267 定义了但未说明哪个功能触发哪个 | 完善 getRecommendedPlan 映射 |
| H4 | **宽限期机制完全缺失** | 支付失败体验差 | 12/13 设计了但无实现 | 实现宽限期逻辑 |
| H5 | **试用期天数 3 个来源矛盾** | 试用逻辑不可信 | seed=7, constants.py=30, 文档=7 | 统一为 system_configs 读取 |
| H6 | **资源只读标记机制缺失** | 降级用户体验问题 | 12:没有 is_readonly 字段 | 添加 projects.is_readonly |
| H7 | **邮件提醒系统缺失** | 用户通知不完整 | 11/12/16 都依赖邮件 | 实现邮件任务调度 |

### 1.3 Medium 级别 (🟢 改进建议)

| # | 问题 | 影响范围 | 发现位置 | 修复建议 |
|---|------|---------|---------|---------|
| M1 | 01 第 7-9 行说"不需要控制"但仍有配置定义 | 文档自相矛盾 | 01:70-72 | 明确这些功能的实际控制方式 |
| M2 | 试用期定义在 01/02/03/11 重复 | 维护困难 | 多处定义 | 统一指向 01 作为唯一源 |
| M3 | 配额警告条只有 ≥80% 规则 | UX 不完整 | 05:102 | 添加 50%-80% 的提示 |
| M4 | 权限评估结果无缓存表 | 性能问题 | 无设计 | 考虑添加缓存表或 Redis |
| M5 | 权限变更时间线表缺失 | 无法追踪历史 | 无设计 | 添加 permission_history 表 |
| M6 | 冲突解决策略配置未入库 | 无法动态调整 | 24:167 硬编码 | 移到 system_configs |
| M7 | A/B 实验统计模块未关联 CreditsDisplay | 实验分析不完整 | 04 vs 15 | 添加实验指标追踪 |

---

## 二、文档间不一致问题

### 2.1 数值不一致

| 配置项 | 01 定义 | 02 定义 | 代码实际 | 应以哪个为准 |
|--------|---------|---------|---------|-------------|
| t1 maxCustomAssets (试用期内) | 10 | 10 | 10 | ✅ 一致 |
| t1 maxCustomAssets (试用期后) | 0 | 0 | 0 | ✅ 一致 |
| t2 maxCustomAssets | 50/Account | 0 (fallback) | 需检查 | **以 01 为准: 50** |
| 试用期天数 | 7 | 7 | 30 (constants.py) | **以 01 为准: 7** |
| OCR 成本 | 5 | 5 | 10 (value_objects.py) | **以 01 为准: 5** |

### 2.2 术语不一致

| 位置 | 使用术语 | 应该使用 | 修复建议 |
|------|---------|---------|---------|
| 18:旧版 | 月度/永久积分 | 7 种 source_type | ✅ 已修复 (v2.1) |
| 20:旧版 | gift | bonus_referral | ✅ 已修复 (v2.2) |
| 部分文档 | `enabled` | `override_value` | 统一用 override_value |

### 2.3 表结构不一致

| 表名 | 文档 A | 文档 B | 差异 | 应以哪个为准 |
|------|--------|--------|------|-------------|
| user_feature_overrides | 02:190 | 03:252 | 字段名一致 | ✅ 一致 |
| feature_flags | 04:126 | 09:字段名不同 | flag_key vs key | 以 04 为准 |

---

## 三、遗漏的场景

### 3.1 边界条件

| # | 场景 | 当前覆盖 | 建议补充 |
|---|------|---------|---------|
| 1 | 用户在 API 调用中途被降级 | ❌ | 添加竞态条件处理 |
| 2 | 多个 Override 同时生效的冲突 | ⚠️ | 24 有设计，需实现 |
| 3 | 权限变更后的缓存主动失效 | ❌ | 添加 WebSocket/Event 通知 |
| 4 | 离线模式下的权限评估 | ❌ | 添加本地缓存策略 |
| 5 | 跨 Workspace 权限继承 | ❌ | 添加到 10 文档 |
| 6 | 积分池合并/拆分 | ❌ | 添加到 15 文档 |
| 7 | 批量用户权限变更 | ⚠️ | 08 有设计，需完善回滚 |

### 3.2 错误处理场景

| # | 场景 | 当前覆盖 | 建议补充 |
|---|------|---------|---------|
| 1 | Stripe Webhook 重试失败 | ⚠️ | 添加死信队列处理 |
| 2 | 积分扣费部分成功 | ❌ | 添加补偿事务 |
| 3 | Override 过期但缓存未失效 | ❌ | 添加缓存一致性检查 |
| 4 | 配置版本回滚失败 | ❌ | 09 需添加回滚策略 |

### 3.3 安全场景

| # | 场景 | 当前覆盖 | 建议补充 |
|---|------|---------|---------|
| 1 | 权限提升攻击 (绕过 Tier 检查) | ⚠️ | 添加 API 层 Tier 校验 |
| 2 | Override 滥用 (Admin 误操作) | ⚠️ | 添加二次确认 + 限制 |
| 3 | 积分刷取 (邀请奖励滥用) | ✅ | 20 已有防作弊规则 |
| 4 | 退款滥用 | ⚠️ | 18 需完善冷却期实现 |

---

## 四、数据库 Schema 完整性检查

### 4.1 已定义但未创建的表

| 表名 | 定义文档 | 用途 | 优先级 |
|------|---------|------|--------|
| `credit_pools` | 15:75 | 积分二维模型 | 🔴 P0 |
| `user_feature_overrides` | 02:190 | 用户级权限覆盖 | 🔴 P0 |
| `group_feature_overrides` | 08 | 用户组权限覆盖 | 🟡 P1 |
| `workspace_feature_overrides` | 10 | 工作区权限覆盖 | 🟡 P1 |
| `user_feature_override_logs` | 02:213 | 权限覆盖审计 | 🟡 P1 |
| `subscriptions` | 03/13/14 | 订阅信息 | 🔴 P0 |
| `refunds` | 18 | 退款记录 | 🔴 P0 |
| `user_groups` | 08 | 用户组 | 🟡 P1 |
| `config_snapshots` | 09 | 配置快照 | 🟢 P2 |

### 4.2 已存在但需扩展的表

| 表名 | 缺失字段 | 来源 | 优先级 |
|------|---------|------|--------|
| `profiles` | `credits_reset_at` | 15 | 🟡 P1 |
| `profiles` | `grace_period_start/end` | 12/13 | 🟡 P1 |
| `projects` | `is_readonly` | 12 | 🟡 P1 |
| `credit_transactions` | `pool_id` | 15:122 | 🔴 P0 |
| `payment_records` | `grace_period_start/end` | 12 | 🟡 P1 |

### 4.3 缺失的索引

| 索引 | 表 | 用途 | 优先级 |
|------|-----|------|--------|
| `idx_credit_pools_user_expiry` | credit_pools | FEFO 查询 | 🔴 P0 |
| `idx_credit_pools_expires` | credit_pools | 过期清理 | 🟡 P1 |
| `idx_user_feature_overrides_expires` | user_feature_overrides | 过期清理 | 🟡 P1 |

### 4.4 缺失的 RPC 函数

| 函数名 | 用途 | 定义文档 | 优先级 |
|--------|------|---------|--------|
| `process_subscription_upgrade` | 升级处理 | 03 | 🔴 P0 |
| `process_subscription_downgrade` | 降级处理 | 12 | 🔴 P0 |
| `add_credits_atomic` | 发放积分 | 15 | 🔴 P0 |
| `deduct_credits_fefo` | FEFO 扣费 | 15 | 🔴 P0 |
| `pause_subscription` | 暂停订阅 | 13 | 🟡 P1 |
| `resume_subscription` | 恢复订阅 | 13 | 🟡 P1 |
| `process_refund` | 退款处理 | 18 | 🔴 P0 |

---

## 五、API 设计完整性检查

### 5.1 已设计但未实现的 API

| API | 定义文档 | 用途 | 优先级 |
|-----|---------|------|--------|
| `GET /api/v2/user/features` | 03:276 | 核心权限查询 | 🔴 P0 |
| `GET /api/v1/credits/balance` | 15:565 | 积分余额查询 | 🔴 P0 |
| `GET /api/v1/credits/pools` | 15:623 | 积分池明细 | 🟡 P1 |
| `POST /api/admin/users/{id}/overrides` | 02 | Admin 授权 | 🟡 P1 |
| `GET /api/v1/debug/permissions/{feature}` | 24:219 | 权限调试 | 🟢 P2 |

### 5.2 需要添加 Tier 校验的现有 API

| API | 应校验的功能 | 当前状态 |
|-----|-------------|---------|
| `POST /tools/ocr` | smart_scan | ❌ 缺失 |
| `POST /tools/pdf_preview` | smart_scan | ❌ 缺失 |
| `POST /export/zip` | zip_export | ⚠️ 需验证 |
| `GET /assets?scope=all` | history_assets | ❌ 缺失 |

---

## 六、前端实现完整性检查

### 6.1 缺失的核心组件

| 组件 | 定义文档 | 用途 | 优先级 |
|------|---------|------|--------|
| `TrialStatusBanner` | 05:296 | 试用期状态 | 🔴 P0 |
| `EditorReadOnlyOverlay` | 05:297 | 只读遮罩 | 🔴 P0 |
| `GracePeriodBanner` | 05:298 | 宽限期警告 | 🔴 P0 |
| `LockedProjectCard` | 05:299 | 锁定项目卡片 | 🔴 P0 |
| `PausedSubscriptionBanner` | 05:302 | 暂停状态 | 🟡 P1 |
| `DowngradeConfirmModal` | 05:303 | 降级确认 | 🟡 P1 |
| `ExpiringCreditsBanner` | 15:715 | 积分过期提醒 | 🟡 P1 |

### 6.2 缺失的 Hooks

| Hook | 定义文档 | 用途 | 优先级 |
|------|---------|------|--------|
| `useTrialStatus` | 05 | 试用期状态 | 🔴 P0 |
| `useGracePeriod` | 05 | 宽限期状态 | 🟡 P1 |
| `useEditorReadOnly` | 05 | 编辑器只读 | 🟡 P1 |
| `useCreditBalance` | 15 | 积分余额 | 🔴 P0 |

---

## 七、文档依赖关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Entitlement 文档依赖关系                              │
└─────────────────────────────────────────────────────────────────────────────┘

                              01-permission-matrix
                           (权限矩阵 - 唯一数据源 ⭐)
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            ▼                         ▼                         ▼
      02-tier-config            03-system-design          04-feature-flag
       (Tier JSON)               (架构总览)                (Flag 引擎)
            │                         │                         │
            │    ┌────────────────────┼────────────────────┐   │
            │    │                    │                    │   │
            ▼    ▼                    ▼                    ▼   ▼
      06-priority-rules         05-ui-spec            07-tier-inheritance
       (7 层优先级)            (UI 交互规范)           (继承链)
            │                         │                    │
            │                         │                    │
            └─────────────────────────┼────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
  08-user-groups               15-credits-lifecycle         24-conflict-resolution
   (用户组)                      (积分生命周期)                (冲突解决)
        │                             │
        │                             │
        ▼                             ▼
  09-config-versioning         18-refund-processing
   (配置版本)                    (退款处理)
        │                             │
        │                             │
        ▼                             ▼
  10-workspace-override        19-promotions
   (工作区覆盖)                  (促销活动)
        │                             │
        │                             │
        ▼                             ▼
  11-trial-expiration          20-referral-rewards
   (试用期过期)                  (邀请奖励)

                    (其他文档: 12-14, 16-17, 21-23, 25)
```

---

## 八、修复优先级建议

### Phase 0: 危急修复 (本周)

```
1. 创建 credit_pools 表 + 索引
2. 创建 user_feature_overrides 表
3. 创建 subscriptions 表
4. 统一试用期天数配置 (改为从 system_configs 读取)
5. 修复 t2 maxCustomAssets 配置 (改为 50)
```

### Phase 1: 核心功能 (下周)

```
6. 实现 7 级优先级评估引擎
7. 实现 FEFO 扣费算法
8. 添加 API 层 Tier 校验 (OCR/PDF)
9. 创建 5 个核心前端组件
10. 创建 4 个核心 Hooks
```

### Phase 2: 扩展功能 (第 3 周)

```
11. 实现 Override 过期清理任务
12. 实现宽限期机制
13. 实现邮件提醒系统
14. 创建 group_feature_overrides 表
15. 创建 workspace_feature_overrides 表
```

### Phase 3: 高级功能 (第 4 周)

```
16. 实现权限调试 API
17. 实现配置版本控制
18. 添加权限变更实时通知
19. 完善退款积分回收
20. 添加冲突解决策略配置化
```

---

## 九、总结

### 9.1 整体评估

| 维度 | 评分 | 说明 |
|------|:----:|------|
| **文档设计完整性** | ⭐⭐⭐⭐⭐ | 25 个文档覆盖了所有核心场景 |
| **文档内部一致性** | ⭐⭐⭐⭐☆ | 少量数值不一致，已识别 |
| **文档间一致性** | ⭐⭐⭐⭐☆ | 术语和引用基本一致 |
| **代码实现覆盖率** | ⭐⭐☆☆☆ | 核心表和函数缺失 |
| **前端实现覆盖率** | ⭐⭐☆☆☆ | 核心组件缺失 |

### 9.2 关键发现

1. **设计完善，实现滞后**: 文档设计非常完整 (~9000 行)，但 DB/后端/前端实现严重滞后
2. **数据库层是瓶颈**: 8 张核心表未创建，阻塞了后续所有工作
3. **配置不一致**: 试用期天数、OCR 成本等数值在代码中硬编码，与文档不一致
4. **前端组件缺失**: 5 个核心 Banner/Modal 组件完全缺失

### 9.3 建议

1. **立即执行 Phase 0**: 创建核心表是解除阻塞的关键
2. **统一配置源**: 所有可配置数值改为从 system_configs 读取
3. **定期审计**: 每次大改动后对照 26-audit-checklist 进行审计

---

**审计完成日期**: 2026-02-04
**审计人**: Claude Code
**下次审计**: Phase 0 完成后复审
