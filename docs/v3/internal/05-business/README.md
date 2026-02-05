# 业务规则

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟢 已验证
> **同步范围**: [fullstack]
> **数据来源**: `CLAUDE.md`

**说明**: 定义核心业务约束，前后端必须遵循

---

## 目录结构

```
05-business/
├── README.md              # 本文件
├── user-system.md         # 用户体系（双 ID）
├── tier-system.md         # Tier 体系（t1/t2/t3/t4）
├── credits-system.md      # 积分体系
├── pricing.md             # 定价规则
│
└── entitlement/           # 权益系统
    ├── permission-matrix.md   # 权限矩阵
    ├── billing-lifecycle.md   # 订阅生命周期
    └── promotions.md          # 促销规则
```

---

## 核心业务规则速查

### 用户 ID 系统

| 标识符 | 格式 | 用途 |
|--------|------|------|
| `user_id` | UUID v4 | 数据库主键，API 调用 |
| `user_code` | 26位数字 | 用户反馈，管理员搜索 |

### Tier 体系

| 代码 | 显示名称 | 月度积分 | 主题色 |
|------|----------|----------|--------|
| `t1` | Free Plan | 0 | 🟢 Emerald |
| `t2` | Starter Plan | 100 | 🔵 Blue |
| `t3` | Pro Plan | 200 | 🟣 Violet |
| `t4` | (预留) | 待定 | - |

### 积分规则

| 类型 | 来源 | 有效期 |
|------|------|--------|
| 月度积分 | 订阅发放 | 每月重置 |
| 永久积分 | 充值/活动 | 永久有效 |

**扣费顺序**: 月度积分 → 永久积分

---

## 文档说明

| 文档 | 说明 | 来源 |
|------|------|------|
| `user-system.md` | 用户体系：双 ID、注册流程、用户状态 | v2/03-business/user-id-system.md |
| `tier-system.md` | Tier 体系：套餐定义、权益差异 | v2/03-business/tier-naming-system.md |
| `credits-system.md` | 积分体系：类型、获取、消耗、过期 | v2/03-business/entitlement/credits-lifecycle.md |
| `pricing.md` | 定价规则：套餐价格、积分包价格 | v2/03-business/pricing-system.md |

---

## entitlement/ 权益系统

| 文档 | 说明 | 来源 |
|------|------|------|
| `permission-matrix.md` | 权限矩阵：各 Tier 的功能权限 | v2/03-business/entitlement/permission-matrix.md |
| `billing-lifecycle.md` | 订阅生命周期：升级、降级、取消、续费 | v2/03-business/entitlement/billing-lifecycle.md |
| `promotions.md` | 促销规则：折扣、优惠码、活动 | v2/03-business/entitlement/promotions.md |

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `02-product/features/billing.md` | 业务规则的产品表达 |
| `04-engineering/modules/billing/` | 业务规则的技术实现 |
| `public/faq/billing.md` | 业务规则转化为用户 FAQ |
| `public/manual/billing/` | 业务规则转化为用户手册 |
