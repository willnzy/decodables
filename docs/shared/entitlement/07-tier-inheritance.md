# 权限继承链

> 本文档定义了 Tier 权限的继承规则和验证工具。

**版本**: v1.0
**创建日期**: 2026-02-04
**来源**: 基于 01-permission-matrix.md 的 Tier 继承规则

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [01-permission-matrix.md](./01-permission-matrix.md) | 功能权限矩阵 (**唯一数据源**) |
| [02-tier-config.md](./02-tier-config.md) | Tier JSON 配置 |
| [06-priority-rules.md](./06-priority-rules.md) | 7 层优先级规则 |
| [24-conflict-resolution.md](./24-conflict-resolution.md) | 权限冲突解决 |

---

## 目录

- [1. 继承规则定义](#1-继承规则定义)
  - [1.1 Tier 继承链](#11-tier-继承链)
  - [1.2 Tier 增量配置](#12-tier-增量配置)
  - [1.3 获取完整权限配置](#13-获取完整权限配置)
- [2. 继承链验证工具](#2-继承链验证工具)

---

## 1. 继承规则定义

### 1.1 Tier 继承链

```typescript
// lib/entitlement/inheritance.ts

/**
 * Tier 继承链定义
 * - t1: 基础层级，无继承
 * - t2: 继承 t1 所有权限
 * - t3: 继承 t2 所有权限 (间接继承 t1)
 * - t4: 继承 t3 所有权限 (间接继承 t1, t2)
 */
export const TIER_INHERITANCE: Record<string, string[]> = {
  t1: [],
  t2: ['t1'],
  t3: ['t2'],
  t4: ['t3'],
};
```

### 1.2 Tier 增量配置

```typescript
/**
 * Tier 增量配置
 * 只配置该层级新增/修改的权限，其余从父级继承
 */
export const TIER_FEATURES_DELTA: Record<string, Record<string, boolean | string>> = {
  t1: {
    // 基础权限
    platform_assets: true,
    vector_tools: true,
    freehand_tools: true,
    pdf_export: true,
    pdf_print: true,
    can_subscribe: true,
    // 试用权限
    clipboard_paste: 'trial',
    ai_features: 'trial',
    smart_scan: 'trial',
    zip_export: 'trial',
    publish_paid: 'trial',
    publish_free: 'trial',
    browse_marketplace: 'trial',
    purchase_marketplace: 'trial',
    can_upload_custom_assets: 'trial',
    // 禁用权限
    recover_deleted: false,
    can_invite_members: false,
    can_purchase_credits: false,
  },
  t2: {
    // t2 新增/覆盖的权限 (继承 t1 的基础)
    ai_features: true,              // 覆盖 t1 的 trial
    publish_free: true,             // 覆盖 t1 的 trial
    browse_marketplace: true,       // 覆盖 t1 的 trial
    purchase_marketplace: true,     // 覆盖 t1 的 trial
    can_purchase_credits: true,     // 覆盖 t1 的 false
    // 其余从 t1 继承
  },
  t3: {
    // t3 新增/覆盖的权限 (继承 t2 的基础)
    clipboard_paste: true,          // 覆盖 t1 的 trial
    smart_scan: true,               // 覆盖 t1 的 trial
    zip_export: true,               // 覆盖 t1 的 trial
    publish_paid: true,             // 覆盖 t1 的 trial
    recover_deleted: true,          // 覆盖 t1 的 false
    can_invite_members: true,       // 覆盖 t1 的 false
    can_upload_custom_assets: true, // 覆盖 t1 的 trial
    // 其余从 t2 继承
  },
  t4: {
    // t4 完全继承 t3，可添加额外企业功能
    // 其余从 t3 继承
  },
};
```

### 1.3 获取完整权限配置

```typescript
/**
 * 获取 Tier 的完整权限配置 (含继承)
 */
export function getTierFeaturesWithInheritance(tier: string): Record<string, boolean | string> {
  const result: Record<string, boolean | string> = {};

  // 递归获取父级权限
  const parents = TIER_INHERITANCE[tier] || [];
  for (const parent of parents) {
    Object.assign(result, getTierFeaturesWithInheritance(parent));
  }

  // 覆盖当前层级的权限
  Object.assign(result, TIER_FEATURES_DELTA[tier] || {});

  return result;
}

/**
 * 获取完整的 TIER_FEATURES (展开所有继承)
 * 用于生成 TIER_FEATURES_FALLBACK 和 system_configs
 */
export function generateFullTierFeatures(): Record<string, Record<string, boolean | string>> {
  return {
    t1: getTierFeaturesWithInheritance('t1'),
    t2: getTierFeaturesWithInheritance('t2'),
    t3: getTierFeaturesWithInheritance('t3'),
    t4: getTierFeaturesWithInheritance('t4'),
  };
}
```

---

## 2. 继承链验证工具

```typescript
// scripts/tools/verify-tier-inheritance.ts

import { generateFullTierFeatures, TIER_FEATURES_DELTA } from '@/lib/entitlement/inheritance';

/**
 * 验证继承链的正确性
 */
function verifyTierInheritance() {
  const fullFeatures = generateFullTierFeatures();

  console.log('=== Tier 继承验证 ===\n');

  // 验证规则: 高层级必须包含低层级的所有 true 权限
  const tiers = ['t1', 't2', 't3', 't4'];

  for (let i = 1; i < tiers.length; i++) {
    const currentTier = tiers[i];
    const parentTier = tiers[i - 1];

    const current = fullFeatures[currentTier];
    const parent = fullFeatures[parentTier];

    console.log(`${currentTier} vs ${parentTier}:`);

    for (const [key, value] of Object.entries(parent)) {
      if (value === true && current[key] !== true) {
        console.error(`  ❌ ${key}: ${parentTier}=${value}, ${currentTier}=${current[key]}`);
      }
    }

    // 显示增量
    const delta = TIER_FEATURES_DELTA[currentTier];
    console.log(`  增量配置: ${Object.keys(delta).length} 项`);
    for (const [key, value] of Object.entries(delta)) {
      console.log(`    ${key}: ${parent[key]} → ${value}`);
    }
    console.log('');
  }
}

verifyTierInheritance();
```

---

## 相关文档

- [README.md](./README.md) - 文档导航索引
- [01-permission-matrix.md](./01-permission-matrix.md) - 功能权限矩阵 (**唯一数据源**)
- [02-tier-config.md](./02-tier-config.md) - Tier JSON 配置
- [11-trial-expiration.md](./11-trial-expiration.md) - 试用期过期处理
- [../tier-permissions.md](../tier-permissions.md) - 完整权益汇总表
