# 权限与功能控制系统文档

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 文档导航

本文件夹包含 Make Decodables 权限与功能控制系统的完整设计文档。

### 核心文档

| # | 文档 | 说明 | 行数 |
|---|------|------|:----:|
| 01 | [permission-matrix.md](./01-permission-matrix.md) | **权限矩阵 (唯一数据源)** - 35 个功能权限定义 | ~250 |
| 02 | [tier-config.md](./02-tier-config.md) | Tier JSON 配置 - t1/t2/t3/t4 完整配置 | ~400 |
| 03 | [system-design.md](./03-system-design.md) | 系统架构 - EntitlementService + FeatureFlagService | ~800 |
| 04 | [feature-flag-engine.md](./04-feature-flag-engine.md) | Feature Flag 引擎 - 9 步评估流程 | ~850 |
| 05 | [ui-spec.md](./05-ui-spec.md) | UI 交互规范 - 10 个核心组件 | ~600 |

### 扩展场景

| # | 文档 | 说明 | 行数 |
|---|------|------|:----:|
| 06 | [priority-rules.md](./06-priority-rules.md) | 7 层权限优先级规则 | ~300 |
| 07 | [tier-inheritance.md](./07-tier-inheritance.md) | 权限继承链 (TIER_INHERITANCE) | ~200 |
| 08 | [user-groups.md](./08-user-groups.md) | 用户组批量授权 | ~300 |
| 09 | [config-versioning.md](./09-config-versioning.md) | 配置版本控制与回滚 | ~200 |
| 10 | [workspace-override.md](./10-workspace-override.md) | 多租户 / Workspace 权限 | ~200 |

### 边界处理

| # | 文档 | 说明 | 行数 |
|---|------|------|:----:|
| 11 | [trial-expiration.md](./11-trial-expiration.md) | t1 试用期过期处理 | ~350 |
| 12 | [tier-downgrade.md](./12-tier-downgrade.md) | Tier 降级处理 (Graceful Degradation) | ~450 |

### 计费生命周期

| # | 文档 | 说明 | 行数 |
|---|------|------|:----:|
| 13 | [subscription-pause.md](./13-subscription-pause.md) | 订阅暂停 (Spotify/Netflix 模式) | ~300 |
| 14 | [billing-cycle-switch.md](./14-billing-cycle-switch.md) | 年付/月付切换 (Proration) | ~300 |
| 15 | [credits-lifecycle.md](./15-credits-lifecycle.md) | 积分完整生命周期 | ~400 |
| 16 | [renewal-reminders.md](./16-renewal-reminders.md) | 订阅续期提醒 | ~200 |
| 17 | [invoice-management.md](./17-invoice-management.md) | 发票与收据管理 | ~250 |
| 18 | [refund-processing.md](./18-refund-processing.md) | 退款完整处理流程 | ~350 |

### 促销与增长

| # | 文档 | 说明 | 行数 |
|---|------|------|:----:|
| 19 | [promotions.md](./19-promotions.md) | 限时优惠与倒计时 | ~300 |
| 20 | [referral-rewards.md](./20-referral-rewards.md) | 邀请奖励完整规则 | ~350 |
| 21 | [education-discount.md](./21-education-discount.md) | 学生/教育优惠 | ~200 |
| 22 | [free-quota.md](./22-free-quota.md) | 免费额度/体验次数 | ~200 |

### 高级场景

| # | 文档 | 说明 | 行数 |
|---|------|------|:----:|
| 23 | [feature-sunset.md](./23-feature-sunset.md) | 功能下线迁移 | ~150 |
| 24 | [conflict-resolution.md](./24-conflict-resolution.md) | 权限继承冲突解决 | ~200 |
| 25 | [future-scenarios.md](./25-future-scenarios.md) | P2 场景索引 (待实现) | ~100 |

---

## 快速查找

### 按角色

| 角色 | 推荐阅读 |
|------|---------|
| **产品经理** | 01 权限矩阵 → 05 UI 规范 |
| **后端开发** | 03 系统架构 → 04 Flag 引擎 → 02 Tier 配置 |
| **前端开发** | 05 UI 规范 → 01 权限矩阵 |
| **运营人员** | 19-22 促销与增长 |

### 按场景

| 场景 | 文档 |
|------|------|
| 新增功能权限 | 01 → 02 |
| 实现灰度发布 | 04 → 06 |
| 处理用户投诉 (降级) | 12 → 18 |
| 配置促销活动 | 19 |
| 排查权限问题 | 01 → 06 → 03 |

---

## 数据流概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        权限评估流程                               │
└─────────────────────────────────────────────────────────────────┘

用户请求
    │
    ▼
┌─────────────────┐
│ L0: Kill Switch │ ── 关闭 ──▶ 返回 disabled
└────────┬────────┘
         │ 开启
         ▼
┌─────────────────┐
│ L1: Feature Flag│ ── 关闭 ──▶ 返回 disabled
└────────┬────────┘
         │ 开启
         ▼
┌─────────────────┐
│ L2: User Override│ ── 有 ──▶ 返回 Override 值
└────────┬────────┘
         │ 无
         ▼
┌─────────────────┐
│ L3: Group Override│ ── 有 ──▶ 返回 Override 值
└────────┬────────┘
         │ 无
         ▼
┌─────────────────┐
│ L4: Workspace   │ ── 有 ──▶ 返回 Override 值
└────────┬────────┘
         │ 无
         ▼
┌─────────────────┐
│ L5: Tier Config │ ── 返回 Tier 基础权限
│   (含继承链)    │
└────────┬────────┘
         │ 无配置
         ▼
┌─────────────────┐
│ L6: Fallback    │ ── 返回兜底默认值
└─────────────────┘
```

---

## 参考产品

本系统设计参考了以下业界产品的最佳实践：

- **权限系统**: LaunchDarkly, Split.io, Unleash
- **订阅计费**: Stripe, Chargebee
- **用户体验**: Notion, Figma, Canva, Slack, Dropbox
- **流媒体订阅**: Spotify, Netflix
- **教育优惠**: Adobe, GitHub

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-02-04 | v2.0 | 从单文件拆分为 25 个独立文档，创建 entitlement 文件夹 |

---

**维护者**: Make Decodables Team
