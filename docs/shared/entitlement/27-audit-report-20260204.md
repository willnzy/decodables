# Entitlement 系统全面审计报告

> **审计日期**: 2026-02-04
> **审计范围**: 数据库层 + 后端逻辑层 + 前端展示层 + 用户场景
> **审计标准**: 26-audit-checklist.md v1.3
> **审计状态**: 完成

---

## 执行摘要

本次审计按照 `26-audit-checklist.md` 定义的 **200+ 检查项** 对 Entitlement 系统进行了全面审计，覆盖 5 个阶段：

| Phase | 审计层级 | 检查项 | 通过率 | 状态 |
|-------|---------|--------|--------|------|
| 1 | 数据库层 | 18 | **22%** | 🔴 严重缺陷 |
| 2 | 后端逻辑层 | 29 | **84%** | ✅ 良好 |
| 3 | 前端展示层 | 47 | **45%** | 🔴 严重缺陷 |
| 4 | 用户场景 (S1-S13) | 130+ | **58%** | 🟡 需要改进 |
| 5 | 交叉验证 | 15+ | **55%** | 🟡 需要改进 |

### 整体评分

```
┌──────────────────────────────────────────┐
│     Entitlement 系统审计评分             │
├──────────────────────────────────────────┤
│ 数据库层:     35/100 (35%)   🔴 严重缺陷 │
│ 后端逻辑层:   84/100 (84%)   ✅ 良好     │
│ 前端展示层:   45/100 (45%)   🔴 严重缺陷 │
│ 用户场景:     58/100 (58%)   🟡 需要改进 │
├──────────────────────────────────────────┤
│ 总体完成度:   55/100 (55%)   🟡 需要加速 │
└──────────────────────────────────────────┘
```

---

## 一、关键发现汇总

### 🔴 P0 级别问题 (必须立即修复)

| # | 问题 | 影响范围 | 根因 |
|---|------|---------|------|
| 1 | **Entitlement 核心表体系缺失** | 整个权限系统 | DB 未按文档创建 8 张表 |
| 2 | **credit_pools 表缺失** | 积分二维模型 | 仍使用旧二桶模型 |
| 3 | **user_feature_overrides 表缺失** | Admin 授权 | 权限覆盖无法实现 |
| 4 | **RLS 策略完全缺失** | 安全控制 | entitlement 表无 RLS |
| 5 | **前端核心组件完全缺失** | 用户体验 | 5 个必需组件未实现 |
| 6 | **OCR/PDF API 缺少 Tier 校验** | 安全 | t1 可免费使用付费功能 |

### 🟡 P1 级别问题 (应该修复)

| # | 问题 | 影响范围 |
|---|------|---------|
| 1 | 试用期天数 3 个来源矛盾 | 试用逻辑不可信 |
| 2 | 宽限期机制完全缺失 | 支付失败处理不完整 |
| 3 | Feature Flag 7级优先级缺失 | Flag 系统无法工作 |
| 4 | 资源只读标记缺失 | 降级用户体验问题 |
| 5 | 退款冷却期缺失 | 退款滥用风险 |
| 6 | 邮件提醒系统缺失 | 用户通知不完整 |

---

## 二、数据库层审计结果

### 2.1 表结构完整性: 35/100

**缺失的核心表** (8 张):

| # | 表名 | 用途 | 文档位置 | 优先级 |
|---|------|------|---------|--------|
| 1 | `credit_pools` | 积分池（二维模型核心） | 15-credits-lifecycle.md | 🔴 P0 |
| 2 | `user_feature_overrides` | 用户级权限覆盖 | 02-tier-config.md | 🔴 P0 |
| 3 | `group_feature_overrides` | 用户组权限覆盖 | 08-user-groups.md | 🟡 P1 |
| 4 | `workspace_feature_overrides` | 工作区权限覆盖 | 10-workspace-override.md | 🟡 P1 |
| 5 | `user_feature_override_logs` | 权限覆盖审计日志 | 02-tier-config.md | 🟡 P1 |
| 6 | `subscriptions` | 订阅信息表 | 03-system-design.md | 🔴 P0 |
| 7 | `refunds` | 退款记录表 | 18-refund-processing.md | 🔴 P0 |
| 8 | `user_groups` | 用户组表 | 08-user-groups.md | 🟡 P1 |

**已有但不完整的表**:

| 表名 | 缺失字段 | 影响 |
|------|---------|------|
| `profiles` | `credits_reset_at`, `grace_period_start/end` | 月度积分周期、宽限期 |
| `credit_transactions` | `source_type` CHECK (7种) | 无法区分积分来源 |
| `payment_records` | `grace_period_start/end` | 宽限期追踪 |

### 2.2 索引设计: 40/100

**缺失的关键索引**:

```sql
-- FEFO 扣费查询索引 (credit_pools 表不存在)
CREATE INDEX idx_credit_pools_user_expiry
ON credit_pools(user_id, COALESCE(expires_at, '9999-12-31'), source_type);

-- 过期积分清理索引
CREATE INDEX idx_credit_pools_expires
ON credit_pools(expires_at) WHERE expires_at IS NOT NULL AND balance > 0;

-- 用户权限覆盖查询
CREATE INDEX idx_user_feature_overrides_expires
ON user_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;
```

### 2.3 RPC 函数: 12.5/100

**必需的 RPC 函数 (8个)**:

| # | 函数名 | 状态 |
|---|--------|------|
| 1 | `process_subscription_upgrade` | ❌ 缺失 |
| 2 | `process_subscription_downgrade` | ❌ 缺失 |
| 3 | `process_subscription_cancel` | ❌ 缺失 |
| 4 | `add_credits_atomic` | ❌ 缺失 |
| 5 | `deduct_credits_atomic` | ✅ 存在 (但基于旧架构) |
| 6 | `process_refund` | ❌ 缺失 |
| 7 | `pause_subscription` | ❌ 缺失 |
| 8 | `resume_subscription` | ❌ 缺失 |

### 2.4 RLS 策略: 0/100

**问题**: Entitlement 相关表完全没有 RLS 策略

**需要添加 RLS 的表**:
- user_feature_overrides
- workspace_feature_overrides
- group_feature_overrides
- credit_pools

---

## 三、后端逻辑层审计结果

### 3.1 架构合规性: 90/100 ✅

| 检查项 | 状态 |
|--------|------|
| DDD 分层 (API → Service → Repository) | ✅ 正确 |
| DI 注入 (Container) | ✅ 正确 |
| 职责单一 | ✅ 正确 |
| 配置集中 | ⚠️ 部分硬编码 |

### 3.2 业务逻辑: 75/100

**订阅管理** ✅:
- 升级流程完整
- 降级流程完整
- 多路径基本一致

**积分管理** ⚠️:
- 扣费优先级: 基于旧二桶模型，不支持 7 种来源
- 余额检查: ✅ 正确
- 原子扣费: ✅ RPC 保证

**权限评估** ❌:
- 当前实现: 仅基本 Tier 权限检查
- 文档要求: 7 级优先级 (Kill Switch > Feature Flag > User Override > ...)

### 3.3 API 接口: 85/100

**缺失的 Tier 校验** 🔴 P0:

| API | 缺失校验 |
|-----|---------|
| `POST /tools/ocr` | smart_scan tier |
| `POST /tools/pdf_preview` | smart_scan tier |

### 3.4 Webhook 处理: 95/100 ✅

- ✅ 签名验证
- ✅ 幂等处理
- ✅ Stripe 事件覆盖
- ⚠️ invoice.payment_failed 处理不完整 (无宽限期逻辑)

---

## 四、前端展示层审计结果

### 4.1 UI 设计: 50/100

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 锁定图标 🔒 | ⚠️ 不一致 | 未系统性应用 |
| Tier 主题色 | ✅ 完整 | Emerald/Blue/Violet |
| 状态颜色 | ✅ 一致 | Green/Yellow/Red |
| cursor: not-allowed | ⚠️ 不一致 | 部分按钮缺失 |

### 4.2 信息提示: 28/100

**缺失的关键提示**:

| 类型 | 组件 | 状态 |
|------|------|------|
| Tooltip | 锁定原因说明 | ❌ 缺失 |
| Toast | 积分变动通知 | ❌ 缺失 |
| Modal | TrialExpiredModal | ❌ 缺失 |
| Modal | DowngradeConfirmModal | ❌ 缺失 |
| Banner | GracePeriodBanner | ❌ 缺失 |
| Banner | PausedSubscriptionBanner | ❌ 缺失 |

### 4.3 核心组件: 25/100

**文档要求 8 个组件，实际完成 2 个**:

| # | 组件名 | 状态 |
|---|--------|------|
| 1 | TrialStatusBanner | ❌ 缺失 |
| 2 | EditorReadOnlyOverlay | ⚠️ 逻辑存在，无专用组件 |
| 3 | GracePeriodBanner | ❌ 缺失 |
| 4 | LockedProjectCard | ❌ 缺失 |
| 5 | UpgradeModal | ✅ 完整 |
| 6 | CreditsDisplay | ⚠️ 不完整 (缺少 7 种来源显示) |
| 7 | PausedSubscriptionBanner | ❌ 缺失 |
| 8 | DowngradeConfirmModal | ❌ 缺失 |

### 4.5 代码架构: 100/100 ✅

- ✅ Hook 职责单一
- ✅ Store 设计合理
- ✅ 组件拆分合理
- ✅ 类型安全

---

## 五、用户场景审计结果

### 5.1 场景完成度汇总

| 场景 | 名称 | 完成度 | 状态 | 主要缺失 |
|------|------|--------|------|---------|
| S1 | 用户升级 | 72% | ⚠️ | 权限缓存刷新、资源解锁 |
| S2 | 用户降级 | 65% | ⚠️ | 宽限期、资源只读标记 |
| S3 | 账户删除 | 55% | ⚠️ | 自动删除任务、数据导出 |
| S4 | Admin授权 | 50% | ❌ | Override 系统完全缺失 |
| S5 | 积分规则 | 62% | ⚠️ | FEFO 验证、过期提醒 |
| S6 | 试用期 | 68% | ⚠️ | 前端 Banner/Modal |
| S7 | 订阅暂停 | 48% | ❌ | 功能完全缺失 |
| S8 | 支付失败 | 58% | ⚠️ | 宽限期逻辑 |
| S9 | 退款处理 | 72% | ⚠️ | 冷却期、积分回收 |
| S10 | Feature Flag | 45% | ❌ | 前端集成 |
| S11 | 周期切换 | 55% | ⚠️ | Stripe Schedule |
| S12 | 续期提醒 | 40% | ❌ | 邮件任务 |
| S13 | 发票管理 | 50% | ⚠️ | PDF 下载 |

### 5.2 关键缺失项

**🔴 P0 级别**:

1. **资源只读/锁定机制缺失** (S1, S2, S6)
   - DB: 缺少 `projects.is_readonly` 字段
   - 后端: 无资源状态更新逻辑
   - 前端: 无 LockedProjectCard 组件

2. **宽限期机制缺失** (S2, S8)
   - DB: 缺少 `grace_period_start/end` 字段
   - 后端: 无自动降级定时任务
   - 前端: 无 GracePeriodBanner

3. **权限缓存刷新机制缺失** (全局)
   - 无 WebSocket/事件驱动
   - 升级/降级后用户需刷新页面

---

## 六、交叉验证结果

### 6.1 API 契约一致性: 65/100

- ⚠️ 权限检查 API 缺失
- ⚠️ 积分查询 API 不完整
- ✅ 响应格式定义完整

### 6.2 多路径副作用一致性: 60/100

**降级场景 4 条路径**:

| 路径 | 触发方式 | 状态 |
|------|---------|------|
| A | 用户主动取消 | ✅ 一致 |
| B | 支付失败 → 宽限期 → 降级 | ❌ 宽限期缺失 |
| C | Admin 手动降级 | ✅ 一致 |
| D | 退款 → 立即降级 | ⚠️ 需验证 |

### 6.3 状态同步机制: 40/100

**缺失的同步点**:
1. 权限变更 → 前端缓存失效
2. 积分变动 → 实时通知
3. 订阅状态变更 → UI 更新

---

## 七、修复优先级路线图

### Phase 1: 危急修复 (1-2 周)

| 任务 | 工作量 | 负责 |
|------|--------|------|
| 创建 8 张缺失的核心表 | 2d | DB |
| 添加 profiles 缺失字段 | 0.5d | DB |
| 创建缺失的 RPC 函数 (6个) | 2d | DB |
| 添加 RLS 策略 | 1d | DB |
| 修复 OCR/PDF API Tier 校验 | 0.5d | 后端 |
| 实现宽限期逻辑 | 2d | 后端 |
| 创建 5 个核心前端组件 | 3d | 前端 |

### Phase 2: 核心功能完善 (2-3 周)

| 任务 | 工作量 |
|------|--------|
| 实现积分二维模型 (credit_pools) | 3d |
| FEFO 算法实现与测试 | 2d |
| 权限评估 7 级优先级 | 3d |
| 邮件系统 + 定时任务 | 3d |
| 前端 Hook 库 | 2d |

### Phase 3: 高级功能 (3-4 周)

| 任务 | 工作量 |
|------|--------|
| Admin Override 系统 | 5d |
| 订阅暂停/恢复 | 3d |
| 数据导出 (GDPR) | 2d |
| 发票 PDF | 2d |

---

## 八、测试覆盖率建议

### 当前状态

| 层级 | 覆盖率 |
|------|--------|
| 后端单元测试 | ~50% |
| 后端集成测试 | ~30% |
| 前端测试 | <10% |

### 建议增加的测试

1. **FEFO 算法边界测试** (100+ 用例)
2. **多路径一致性测试** (降级 4 条路径)
3. **Webhook 重放测试**
4. **权限组件测试**

---

## 九、文档同步检查

### 已修复的文档问题 (初审)

| 文档 | 修复内容 |
|------|---------|
| 02-tier-config.md | 更新来源注释 |
| 03-system-design.md | 更新相关文档引用 |
| 04-feature-flag-engine.md | 更新相关文档引用 |
| 05-ui-spec.md | 更新相关文档引用 |
| 06-priority-rules.md | 更新来源注释和相关文档 |
| 07-tier-inheritance.md | 更新来源注释和相关文档 |
| 08-user-groups.md | 更新来源注释 |
| 09-config-versioning.md | 更新来源注释 |
| 10-workspace-override.md | 更新来源注释 |
| 11-trial-expiration.md | 更新来源注释 |

### 本次文档审计修复 (2026-02-04 复审)

#### P0 级别修复 (积分一致性)

| 文档 | 版本变更 | 修复内容 |
|------|----------|---------|
| **18-refund-processing.md** | v2.0 → v2.1 | 1. 修正 FEFO 逆序扣回算法（7 种 source_type）<br>2. 将过时的「永久/月度」术语改为二维模型 |

#### P1 级别修复 (文档内部缺陷)

| 文档 | 版本变更 | 修复内容 |
|------|----------|---------|
| **20-referral-rewards.md** | v2.0 → v2.2 | 1. `gift` → `bonus_referral` (source_type 一致性)<br>2. referrer_id 类型 TEXT → UUID<br>3. **移除所有硬编码数值**，改用 system_configs 配置 key 引用 |
| **08-user-groups.md** | v1.0 → v1.1 | 补全 7 层优先级描述（从错误的 4 层修正为 L0-L6） |
| **16-renewal-reminders.md** | v1.0 → v1.1 | 添加年度订阅 30 天提醒逻辑，与 S12 场景一致 |
| **17-invoice-management.md** | v2.0 → v2.1 | `transaction_id` → `payment_record_id` (引用正确的表) |
| **09-config-versioning.md** | v1.0 → v1.1 | feature_flags 字段名与 04 文档一致 (flag_key→key, is_enabled→enabled) |
| **22-free-quota.md** | v2.0 → v2.1 | 完善「与积分关系」逻辑，添加试用期状态检查 |

#### 配置化改进 (20-referral-rewards.md)

新增 system_configs 配置示例：

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('referral.referrer_reward', '50', 'integer', 'referral', '邀请人奖励积分'),
('referral.referee_reward', '50', 'integer', 'referral', '被邀请人奖励积分'),
('referral.daily_reward_limit', '500', 'integer', 'referral', '单日奖励上限'),
('referral.total_reward_limit', '5000', 'integer', 'referral', '总奖励上限'),
('referral.same_ip_limit_24h', '3', 'integer', 'referral', '同IP 24小时内限制'),
('referral.risk_delay_days', '7', 'integer', 'referral', '风控延迟发放天数');
```

### 待更新的文档

| 文档 | 需要更新内容 |
|------|-------------|
| 26-audit-checklist.md 第九章 | 添加本次审计发现的新问题 |
| 01-permission-matrix.md | 同步积分二维模型定义 |

---

## 十、做得好的地方

| 方面 | 评价 |
|------|------|
| **后端 DDD 架构** | ⭐⭐⭐⭐⭐ 分层清晰，职责单一 |
| **Webhook 处理** | ⭐⭐⭐⭐⭐ 签名验证、幂等设计完善 |
| **Tier 颜色系统** | ⭐⭐⭐⭐⭐ 前端一致性好 |
| **UpgradeModal** | ⭐⭐⭐⭐⭐ 用户体验好 |
| **代码类型安全** | ⭐⭐⭐⭐⭐ TypeScript 类型完善 |
| **审计日志设计** | ⭐⭐⭐⭐ admin_operations 完整 |

---

## 结论

Make Decodables Entitlement 系统当前整体完成度为 **55%**，存在以下核心问题：

1. **数据库层严重缺陷** (35%): 8 张核心表缺失，积分二维模型未实现
2. **前端展示层严重缺陷** (45%): 5 个必需组件缺失
3. **用户场景不完整** (58%): 宽限期、资源锁定等关键机制缺失

**建议**: 优先完成 Phase 1 (危急修复)，使系统达到可用状态 (≥75% 完成度)。

---

**审计完成日期**: 2026-02-04
**审计人**: Claude Code
**下次审计**: 修复 P0 项目后复审
