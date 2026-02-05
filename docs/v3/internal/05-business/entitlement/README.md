# 权益系统

> Entitlement System - 用户权限、配额、功能控制

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]

---

## 一、概述

权益系统管理用户对功能的访问权限、配额限制和特殊优惠，是平台商业模式的核心组件。

---

## 二、文档清单

| 文档 | 状态 | 描述 |
|------|------|------|
| [系统设计](./system-design.md) | 🟢 Active | 权益系统整体架构 |
| [权限矩阵](./permission-matrix.md) | 🟢 Active | Tier 权限对照表 |
| [策略规则](./policy-rules.md) | 🟢 Active | 权限判断优先级和规则 |
| [促销规则](./promotions.md) | 🟡 Draft | 折扣码、限时优惠 |
| [试用与到期](./trial-expiration.md) | 🟡 Draft | 试用期、订阅到期处理 |
| [推荐奖励](./referral-rewards.md) | 🟢 Active | 推荐返利机制 |
| [教育优惠](./education-discount.md) | 🟡 Draft | 教育用户优惠政策 |
| [实现指南](./implementation-guide.md) | 🟢 Active | 开发实现参考 |

---

## 三、核心概念

### 3.1 权限层级

```
┌─────────────────────────────────────────────────────────────────┐
│                    权限判断优先级                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Kill Switch (全局禁用)                                      │
│     │  ↓ 最高优先级                                             │
│                                                                 │
│  2. User Override (用户级覆盖)                                  │
│     │  ↓ 管理员设置                                             │
│                                                                 │
│  3. Tier Permission (层级权限)                                  │
│     │  ↓ t1/t2/t3 基础权限                                      │
│                                                                 │
│  4. Feature Flag (功能标记)                                     │
│     │  ↓ A/B 测试、灰度发布                                     │
│                                                                 │
│  5. Default Value (默认值)                                      │
│        ↓ 兜底策略                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Tier 体系

| Tier | 代码 | 显示名 | 价格 |
|------|------|--------|------|
| t1 | `t1` | Free Plan | $0 |
| t2 | `t2` | Starter Plan | $6.9/月 |
| t3 | `t3` | Pro Plan | $9.9/月 |

### 3.3 配额类型

| 类型 | 描述 | 限制方式 |
|------|------|----------|
| 积分 | AI 生成消耗 | 月度 + 永久 |
| 存储 | 文件存储空间 | 按 Tier |
| 项目 | 最大项目数 | 按 Tier |
| 速率 | API 调用频率 | 分钟/天 |

---

## 四、实现状态

| 功能 | 状态 | 说明 |
|------|------|------|
| Tier 权限 | 🟢 已实现 | t1/t2/t3 基础权限 |
| Feature Flag | 🟢 已实现 | 布尔/百分比/分群 |
| Kill Switch | 🟢 已实现 | 紧急禁用开关 |
| User Override | 🟢 已实现 | 管理员覆盖 |
| 积分配额 | 🟢 已实现 | 双桶模型 |
| 存储配额 | 🟡 部分实现 | 按 Tier 限制 |
| 速率限制 | 🟢 已实现 | Redis 计数 |
| 促销系统 | 🟡 规划中 | Stripe 集成 |
| 教育优惠 | 🟡 规划中 | 验证流程 |

---

## 五、快速使用

### 5.1 后端检查权限

```python
# 依赖注入方式
@router.post("/generate")
async def generate(
    _: FeatureAccess = Depends(require_feature("ai_generation")),
    user: User = Depends(get_current_user)
):
    ...

# 编程方式
access = await entitlement_checker.check_feature(user, "export_pdf")
if not access.allowed:
    raise FeatureNotAllowedError(access.feature)
```

### 5.2 前端检查权限

```typescript
// Hook 方式
const { allowed, loading } = useFeatureAccess('ai_generation');

// 组件方式
<FeatureGate feature="custom_fonts" fallback={<UpgradePrompt />}>
  <CustomFontPicker />
</FeatureGate>
```

---

## 六、相关文档

- [Billing 架构](../../04-engineering/modules/billing/architecture.md)
- [Feature Flag 引擎](../../02-standards/feature-flag-engine.md)
- [Tier 命名系统](../../03-business/tier-system.md)
