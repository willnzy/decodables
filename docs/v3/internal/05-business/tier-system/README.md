# 会员等级体系

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟢 已验证
> **同步范围**: [fullstack]
> **数据来源**: `CLAUDE.md`, `domains/identity/`

---

## 概述

系统使用四级会员体系（t1/t2/t3/t4）。

## Tier 定义

| 系统代码 | 简称 | 显示名称 | 原价 | 现价 | 月度积分 | 主题色 |
|----------|------|----------|------|------|----------|--------|
| `t1` | First Tier | Free Plan | $0 | $0 | 0 | 🟢 Emerald |
| `t2` | Second Tier | Starter Plan | $9.9 | $6.9 | 100 | 🔵 Blue |
| `t3` | Third Tier | Pro Plan | $15.9 | $9.9 | 200 | 🟣 Violet |
| `t4` | Fourth Tier | (预留) | 待定 | 待定 | 待定 | 预留 |

## 重要说明

- **系统代码** (`t1`/`t2`/`t3`/`t4`) - 数据库字段、代码逻辑使用，**永不改变**
- **显示名称** - 用户看到的，**可通过 Admin 配置**
- **t4 预留** - 数据库和后端已支持，前端暂不展示

## 代码使用

```python
# ✅ 正确: 使用系统代码
from domains.identity.constants import TIER_T1, TIER_T2, TIER_T3

if user.tier == TIER_T2:  # "t2"
    credits = TIER_MONTHLY_CREDITS[TIER_T2]  # 100

# ❌ 错误: 硬编码显示名称
plan_name = "Starter Plan"  # 将来可能改名
```

## 计划文档

| 文档 | 用途 | 状态 |
|------|------|------|
| `tier-benefits.md` | 各等级权益详情 | 📋 待创建 |
| `tier-upgrade.md` | 升级/降级规则 | 📋 待创建 |

## 参考

- 完整权益表：`CLAUDE.md` Tier 命名系统章节
