# 权限优先级规则

> 基于业界最佳实践 (LaunchDarkly, Split.io, Unleash, Statsig) 设计的扩展场景完整实现方案。

**版本**: v1.0
**创建日期**: 2026-02-04
**来源**: 基于 01-permission-matrix.md + 03-system-design.md 定义

---

## 相关文档

- [01-permission-matrix.md](./01-permission-matrix.md) - 功能权限矩阵 (**唯一数据源**)
- [02-tier-config.md](./02-tier-config.md) - Tier JSON 配置
- [03-system-design.md](./03-system-design.md) - 系统架构总览
- [04-feature-flag-engine.md](./04-feature-flag-engine.md) - Feature Flag 评估引擎
- [05-ui-spec.md](./05-ui-spec.md) - UI 交互规范

---

## 1. 场景支持矩阵

| 场景 | 支持情况 | 说明 |
|------|:--------:|------|
| **灰度发布 + Tier 组合** | ✅ 支持 | 完整优先级规则 + 评估引擎 |
| **权限继承链** | ✅ 支持 | Tier 自动继承父级权限 |
| **权限批量管理** | ✅ 支持 | 用户组 + 组级权限覆盖 |
| **配置版本控制** | ✅ 支持 | 快照 + 回滚机制 |
| **多租户 (Team/Org 级权限)** | ✅ 支持 | Workspace 级权限继承 |
| **审计 + 回溯** | ✅ 已实现 | v1.6 已补充 logs 表 |

---

## 2. 灰度发布 + Tier 组合

### 2.1 完整优先级规则

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    权限评估完整优先级 (从高到低)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Level 1: 全局开关 (Kill Switch)                                            │
│  ├── 配置: feature.{key}.enabled = false                                   │
│  ├── 效果: 功能完全下线，任何其他配置无效                                      │
│  └── 场景: 紧急下线、功能维护、严重 Bug                                       │
│                                                                             │
│  Level 2: Feature Flag (技术开关)                                           │
│  ├── 配置: feature_flags 表                                                │
│  ├── 效果: 控制功能是否对特定用户群可见                                        │
│  ├── 场景: 灰度发布、AB 实验、Beta 测试                                       │
│  └── ⚠️ 即使用户有 Entitlement 权限，Flag 关闭也无法访问                       │
│                                                                             │
│  Level 3: 用户级覆盖 (User Override)                                        │
│  ├── 配置: user_feature_overrides 表                                        │
│  ├── 效果: 为特定用户开通/关闭功能，跨 Tier 生效                               │
│  └── 场景: VIP 用户、客服补偿、Bug 隔离                                       │
│                                                                             │
│  Level 4: 用户组覆盖 (Group Override)                                       │
│  ├── 配置: group_feature_overrides 表                                       │
│  ├── 效果: 为用户组批量授权                                                   │
│  └── 场景: KOL 用户组、Beta 测试组、Enterprise 试用组                          │
│                                                                             │
│  Level 5: Workspace 覆盖 (Workspace Override)                               │
│  ├── 配置: workspace_feature_overrides 表                                   │
│  ├── 效果: Workspace 成员继承权限                                            │
│  └── 场景: Team Plan、企业授权                                               │
│                                                                             │
│  Level 6: Tier 配置 (Plan-based) + 继承链                                   │
│  ├── 配置: tier.{tier}.features + TIER_INHERITANCE                         │
│  ├── 效果: 按用户订阅等级决定权限，自动继承父级                                 │
│  └── 场景: 常规付费功能控制                                                   │
│                                                                             │
│  Level 7: 默认值 (Fallback)                                                 │
│  ├── 配置: EMERGENCY_TIER_CONFIGS 常量                                      │
│  └── 场景: 数据库不可用时的兜底                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 完整评估引擎

```typescript
// lib/entitlement/evaluator.ts

interface EvaluationContext {
  userId: string;
  tier: string;
  isWithinTrialPeriod: boolean;
  userGroups: string[];      // 用户所属组
  workspaceId?: string;      // 当前 Workspace
}

interface EvaluationResult {
  allowed: boolean;
  reason: string;
  source: 'kill_switch' | 'feature_flag' | 'user_override' | 'group_override' | 'workspace_override' | 'tier_config' | 'fallback';
  trialDaysRemaining?: number;
}

async function evaluateFeatureAccess(
  featureKey: string,
  context: EvaluationContext
): Promise<EvaluationResult> {

  // Level 1: Kill Switch
  const killSwitch = await getConfig(`feature.${featureKey}.enabled`);
  if (killSwitch === 'false') {
    return {
      allowed: false,
      reason: 'Feature is globally disabled',
      source: 'kill_switch'
    };
  }

  // Level 2: Feature Flag
  const flagResult = await evaluateFeatureFlag(featureKey, context);
  if (flagResult !== null) {
    return {
      allowed: flagResult.enabled,
      reason: flagResult.enabled ? 'Feature flag enabled' : 'Feature flag disabled or not in rollout',
      source: 'feature_flag'
    };
  }

  // Level 3: User Override
  const userOverride = await getUserOverride(context.userId, featureKey);
  if (userOverride) {
    return {
      allowed: userOverride.override_value === 'true',
      reason: `User override: ${userOverride.reason}`,
      source: 'user_override'
    };
  }

  // Level 4: Group Override
  if (context.userGroups.length > 0) {
    const groupOverride = await getGroupOverride(context.userGroups, featureKey);
    if (groupOverride) {
      return {
        allowed: groupOverride.override_value === 'true',
        reason: `Group override: ${groupOverride.reason}`,
        source: 'group_override'
      };
    }
  }

  // Level 5: Workspace Override
  if (context.workspaceId) {
    const workspaceOverride = await getWorkspaceOverride(context.workspaceId, featureKey);
    if (workspaceOverride) {
      return {
        allowed: workspaceOverride.override_value === 'true',
        reason: `Workspace override: ${workspaceOverride.reason}`,
        source: 'workspace_override'
      };
    }
  }

  // Level 6: Tier Config (with inheritance)
  const tierFeatures = getTierFeaturesWithInheritance(context.tier);
  const featureValue = tierFeatures[featureKey];

  if (featureValue === true) {
    return { allowed: true, reason: 'Tier permission', source: 'tier_config' };
  }

  if (featureValue === 'trial') {
    if (context.isWithinTrialPeriod) {
      const daysRemaining = await getTrialDaysRemaining(context.userId);
      return {
        allowed: true,
        reason: 'Trial period active',
        source: 'tier_config',
        trialDaysRemaining: daysRemaining
      };
    }
    return { allowed: false, reason: 'Trial period expired', source: 'tier_config' };
  }

  if (featureValue === false) {
    return { allowed: false, reason: 'Not included in tier', source: 'tier_config' };
  }

  // Level 7: Fallback
  const fallback = EMERGENCY_TIER_CONFIGS[context.tier]?.features[featureKey] ?? false;
  return {
    allowed: fallback === true,
    reason: 'Fallback default',
    source: 'fallback'
  };
}

// Feature Flag 评估 (灰度 + Tier 组合)
async function evaluateFeatureFlag(
  featureKey: string,
  context: EvaluationContext
): Promise<{ enabled: boolean } | null> {
  const flag = await db.fetch(`
    SELECT * FROM feature_flags
    WHERE flag_key = $1 AND is_enabled = true
  `, featureKey);

  if (!flag) return null;  // 无 Flag，继续下一级

  // 检查 Tier 限制
  if (flag.allowed_tiers && flag.allowed_tiers.length > 0) {
    if (!flag.allowed_tiers.includes(context.tier)) {
      return { enabled: false };  // Tier 不在允许列表
    }
  }

  // 检查灰度百分比
  if (flag.rollout_percentage < 100) {
    const hash = hashUserForRollout(context.userId, featureKey);
    if (hash > flag.rollout_percentage) {
      return { enabled: false };  // 未命中灰度
    }
  }

  return { enabled: true };
}
```

### 2.3 灰度 + Tier 组合示例

```typescript
// 场景: 新 AI 模型只对 t3 用户的 30% 灰度发布

// 1. 创建 Feature Flag
await db.insert('feature_flags', {
  flag_key: 'new_ai_model_v2',
  flag_name: '新 AI 模型 v2',
  is_enabled: true,
  allowed_tiers: ['t3'],           // 只对 t3 用户
  rollout_percentage: 30,          // 30% 灰度
  description: '新 AI 模型灰度测试'
});

// 2. 评估结果
// t1 用户 → allowed: false (Tier 不在 allowed_tiers)
// t2 用户 → allowed: false (Tier 不在 allowed_tiers)
// t3 用户 (命中 30%) → allowed: true
// t3 用户 (未命中) → allowed: false (未命中灰度)

// 3. 灰度结束后，删除 Flag，回归 Tier 配置
await db.delete('feature_flags', { flag_key: 'new_ai_model_v2' });
```

---

## 3. 优先级规则总结

| Level | 名称 | 配置位置 | 优先级 | 典型场景 |
|:-----:|------|----------|:------:|----------|
| 1 | Kill Switch | system_configs | 最高 | 紧急下线 |
| 2 | Feature Flag | feature_flags 表 | 高 | 灰度发布 |
| 3 | User Override | user_feature_overrides | 高 | VIP 特权 |
| 4 | Group Override | group_feature_overrides | 中 | Beta 测试组 |
| 5 | Workspace Override | workspace_feature_overrides | 中 | Team Plan |
| 6 | Tier Config | tier.{tier}.features | 低 | 常规付费 |
| 7 | Fallback | 代码常量 | 最低 | 兜底默认 |

**关键原则**:
- 高优先级可以覆盖低优先级
- Kill Switch 可以立即下线任何功能
- Feature Flag 可以控制灰度范围
- Override 可以为特定用户/组开通特权
- Tier Config 是常规的付费权限控制
- Fallback 确保系统在异常情况下仍可运行
