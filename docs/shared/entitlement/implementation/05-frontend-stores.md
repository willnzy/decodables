# 前端 Store 实现

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 🔴 待实现
> **代码位置**: `decodables-fe/@business/stores/entitlement/`

---

## 相关设计文档

| 设计文档 | 本文档章节 |
|----------|-----------|
| 01-permission-matrix.md | §2.1 |
| 02-tier-config.md | §2.2 |
| 04-feature-flag-engine.md | §2.3 |
| 06-priority-rules.md | §2.4 |
| 08-user-groups.md | §2.5 |
| 10-workspace-override.md | §2.6 |
| 11-trial-expiration.md | §3.1 |
| 12-tier-downgrade.md | §3.2 |
| 13-subscription-pause.md | §3.3 |
| 15-credits-lifecycle.md | §3.4 |
| 19-promotions.md | §4.1 |
| 20-referral-rewards.md | §4.2 |
| 22-free-quota.md | §4.3 |
| 23-feature-sunset.md | §4.4 |

---

## 目录

- [§1. 架构概述](#1-架构概述)
- [§2. 核心配置 Store](#2-核心配置-store)
  - [§2.1 usePermissionStore](#21-usepermissionstore)
  - [§2.2 useTierStore](#22-usetierstore)
  - [§2.3 useFeatureFlagStore](#23-usefeatureflagstore)
  - [§2.4 usePriorityStore](#24-useprioritystore)
  - [§2.5 useUserGroupStore](#25-useusergroupstore)
  - [§2.6 useWorkspaceOverrideStore](#26-useworkspaceoverridestore)
- [§3. 生命周期 Store](#3-生命周期-store)
  - [§3.1 useTrialStore](#31-usetrialstore)
  - [§3.2 useTierDowngradeStore](#32-usetierdowngradestore)
  - [§3.3 useSubscriptionStore](#33-usesubscriptionstore)
  - [§3.4 useCreditStore](#34-usecreditstore)
- [§4. 营销扩展 Store](#4-营销扩展-store)
  - [§4.1 usePromotionStore](#41-usepromotionstore)
  - [§4.2 useReferralStore](#42-usereferralstore)
  - [§4.3 useFreeQuotaStore](#43-usefreequotastore)
  - [§4.4 useFeatureSunsetStore](#44-usefeaturesunsetstore)

---

## §1. 架构概述

### 1.1 目录结构

```
decodables-fe/@business/stores/entitlement/
├── index.ts                    # 导出入口
├── usePermissionStore.ts       # 权限检查
├── useTierStore.ts             # Tier 配置
├── useFeatureFlagStore.ts      # Feature Flag
├── useCreditStore.ts           # 积分
├── useTrialStore.ts            # 试用期
├── useSubscriptionStore.ts     # 订阅状态
├── usePromotionStore.ts        # 促销
├── useReferralStore.ts         # 邀请
└── types.ts                    # 类型定义
```

### 1.2 Store 设计原则

1. **单一职责**: 每个 Store 负责一个领域
2. **拆分式 Store**: 使用 Zustand slice 模式
3. **选择器优化**: 使用 shallow 比较防止不必要渲染
4. **持久化**: 关键状态使用 persist 中间件

### 1.3 基础类型定义

```typescript
// @business/stores/entitlement/types.ts

export type TierType = 't1' | 't2' | 't3' | 't4';

export type PermissionValue = boolean | 'trial';

export interface PermissionResult {
  enabled: PermissionValue;
  source: string;
  quota?: number;
  expiresAt?: string;
}

export interface TierConfig {
  tier: TierType;
  displayName: string;
  features: Record<string, PermissionValue>;
  quotas: Record<string, number>;
}

export interface QuotaUsage {
  used: number;
  limit: number; // -1 = 无限
}

export interface CreditBalance {
  total: number;
  bySource: {
    subscription: number;
    purchase: number;
    bonus_signup: number;
    bonus_referral: number;
    bonus_campaign: number;
    compensation: number;
    earning: number;
  };
  expiringSoon: number;
  expiringAt?: string;
}

export interface CreditTransaction {
  id: string;
  type: 'grant' | 'consume' | 'expire' | 'refund';
  amount: number;
  balanceAfter: number;
  description?: string;
  createdAt: string;
}

export interface TrialStatus {
  status: 'not_started' | 'active' | 'expired' | 'converted';
  startedAt?: string;
  expiresAt?: string;
  remainingDays?: number;
}
```

---

## §2. 核心配置 Store

### §2.1 usePermissionStore

> 设计文档: [01-permission-matrix.md](../01-permission-matrix.md)

**文件**: `@business/stores/entitlement/usePermissionStore.ts`

**职责**: 权限检查的统一入口

```typescript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { shallow } from 'zustand/shallow';
import type { PermissionResult, PermissionValue } from './types';
import { entitlementApi } from '@business/services/entitlement';

interface PermissionState {
  // 缓存的权限结果
  permissions: Record<string, PermissionResult>;
  // 加载状态
  loading: Record<string, boolean>;
  // 错误状态
  errors: Record<string, string | null>;
}

interface PermissionActions {
  // 检查权限 (会缓存结果)
  checkPermission: (featureKey: string, workspaceId?: string) => Promise<PermissionResult>;
  // 批量检查权限
  checkPermissions: (featureKeys: string[]) => Promise<Record<string, PermissionResult>>;
  // 快速检查 (使用缓存，不发请求)
  canUse: (featureKey: string) => boolean;
  // 是否在试用期
  isTrialing: (featureKey: string) => boolean;
  // 清除缓存
  clearCache: () => void;
  // 刷新权限
  refreshPermission: (featureKey: string) => Promise<void>;
}

export const usePermissionStore = create<PermissionState & PermissionActions>()(
  devtools(
    (set, get) => ({
      permissions: {},
      loading: {},
      errors: {},

      checkPermission: async (featureKey, workspaceId) => {
        const cacheKey = workspaceId ? `${featureKey}:${workspaceId}` : featureKey;

        // 如果已有缓存，直接返回
        const cached = get().permissions[cacheKey];
        if (cached) return cached;

        // 设置加载状态
        set(state => ({
          loading: { ...state.loading, [cacheKey]: true },
        }));

        try {
          const result = await entitlementApi.checkPermission(featureKey, workspaceId);

          set(state => ({
            permissions: { ...state.permissions, [cacheKey]: result },
            loading: { ...state.loading, [cacheKey]: false },
            errors: { ...state.errors, [cacheKey]: null },
          }));

          return result;
        } catch (error) {
          set(state => ({
            loading: { ...state.loading, [cacheKey]: false },
            errors: { ...state.errors, [cacheKey]: (error as Error).message },
          }));
          throw error;
        }
      },

      checkPermissions: async (featureKeys) => {
        const results: Record<string, PermissionResult> = {};
        const uncachedKeys = featureKeys.filter(key => !get().permissions[key]);

        // 返回已缓存的
        featureKeys.forEach(key => {
          if (get().permissions[key]) {
            results[key] = get().permissions[key];
          }
        });

        // 批量请求未缓存的
        if (uncachedKeys.length > 0) {
          const response = await entitlementApi.checkPermissionsBatch(uncachedKeys);
          set(state => ({
            permissions: { ...state.permissions, ...response },
          }));
          Object.assign(results, response);
        }

        return results;
      },

      canUse: (featureKey) => {
        const permission = get().permissions[featureKey];
        if (!permission) return false;
        return permission.enabled === true || permission.enabled === 'trial';
      },

      isTrialing: (featureKey) => {
        const permission = get().permissions[featureKey];
        return permission?.enabled === 'trial';
      },

      clearCache: () => {
        set({ permissions: {}, loading: {}, errors: {} });
      },

      refreshPermission: async (featureKey) => {
        // 清除缓存后重新请求
        set(state => {
          const { [featureKey]: _, ...rest } = state.permissions;
          return { permissions: rest };
        });
        await get().checkPermission(featureKey);
      },
    }),
    { name: 'permission-store' }
  )
);

// 选择器
export const usePermission = (featureKey: string) =>
  usePermissionStore(state => state.permissions[featureKey], shallow);

export const useCanUse = (featureKey: string) =>
  usePermissionStore(state => state.canUse(featureKey));

export const useIsTrialing = (featureKey: string) =>
  usePermissionStore(state => state.isTrialing(featureKey));
```

### §2.2 useTierStore

> 设计文档: [02-tier-config.md](../02-tier-config.md), [07-tier-inheritance.md](../07-tier-inheritance.md)

**文件**: `@business/stores/entitlement/useTierStore.ts`

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { TierType, TierConfig, QuotaUsage } from './types';
import { entitlementApi } from '@business/services/entitlement';

interface TierState {
  // 当前用户 Tier
  currentTier: TierType | null;
  // Tier 显示名称
  displayName: string | null;
  // 功能权限
  features: Record<string, boolean | 'trial'>;
  // 配额限制
  quotas: Record<string, number>;
  // 配额使用情况
  quotaUsage: Record<string, QuotaUsage>;
  // 加载状态
  loading: boolean;
}

interface TierActions {
  // 加载用户 Tier 信息
  loadTierInfo: () => Promise<void>;
  // 获取功能是否启用
  hasFeature: (featureKey: string) => boolean | 'trial';
  // 获取配额
  getQuota: (quotaKey: string) => number;
  // 检查配额是否足够
  hasQuota: (quotaKey: string) => boolean;
  // 刷新配额使用情况
  refreshQuotaUsage: () => Promise<void>;
}

export const useTierStore = create<TierState & TierActions>()(
  devtools(
    persist(
      (set, get) => ({
        currentTier: null,
        displayName: null,
        features: {},
        quotas: {},
        quotaUsage: {},
        loading: false,

        loadTierInfo: async () => {
          set({ loading: true });
          try {
            const [tierInfo, quotaUsage] = await Promise.all([
              entitlementApi.getMyTier(),
              entitlementApi.getMyQuotas(),
            ]);

            set({
              currentTier: tierInfo.tier,
              displayName: tierInfo.displayName,
              features: tierInfo.features,
              quotas: tierInfo.quotas,
              quotaUsage,
              loading: false,
            });
          } catch (error) {
            set({ loading: false });
            throw error;
          }
        },

        hasFeature: (featureKey) => {
          return get().features[featureKey] ?? false;
        },

        getQuota: (quotaKey) => {
          return get().quotas[quotaKey] ?? 0;
        },

        hasQuota: (quotaKey) => {
          const quota = get().quotas[quotaKey];
          const usage = get().quotaUsage[quotaKey];

          if (quota === -1) return true; // 无限
          if (!usage) return true;
          return usage.used < usage.limit;
        },

        refreshQuotaUsage: async () => {
          const quotaUsage = await entitlementApi.getMyQuotas();
          set({ quotaUsage });
        },
      }),
      {
        name: 'tier-store',
        partialize: (state) => ({
          currentTier: state.currentTier,
          displayName: state.displayName,
          features: state.features,
          quotas: state.quotas,
        }),
      }
    ),
    { name: 'tier-store' }
  )
);

// 选择器
export const useCurrentTier = () => useTierStore(state => state.currentTier);
export const useTierDisplayName = () => useTierStore(state => state.displayName);
export const useHasFeature = (featureKey: string) =>
  useTierStore(state => state.hasFeature(featureKey));
export const useHasQuota = (quotaKey: string) =>
  useTierStore(state => state.hasQuota(quotaKey));
```

### §2.3 useFeatureFlagStore

> 设计文档: [04-feature-flag-engine.md](../04-feature-flag-engine.md)

**文件**: `@business/stores/entitlement/useFeatureFlagStore.ts`

```typescript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { entitlementApi } from '@business/services/entitlement';

interface FlagResult {
  enabled: boolean;
  source: string;
  variant?: string;
}

interface FeatureFlagState {
  flags: Record<string, FlagResult>;
  loading: boolean;
}

interface FeatureFlagActions {
  evaluateFlag: (flagKey: string, context?: Record<string, any>) => Promise<FlagResult>;
  evaluateFlags: (flagKeys: string[]) => Promise<Record<string, FlagResult>>;
  isEnabled: (flagKey: string) => boolean;
  getVariant: (flagKey: string) => string | undefined;
}

export const useFeatureFlagStore = create<FeatureFlagState & FeatureFlagActions>()(
  devtools(
    (set, get) => ({
      flags: {},
      loading: false,

      evaluateFlag: async (flagKey, context) => {
        // 使用缓存
        if (get().flags[flagKey]) {
          return get().flags[flagKey];
        }

        const result = await entitlementApi.evaluateFlag(flagKey, context);
        set(state => ({
          flags: { ...state.flags, [flagKey]: result },
        }));
        return result;
      },

      evaluateFlags: async (flagKeys) => {
        const results = await entitlementApi.evaluateFlagsBatch(flagKeys);
        set(state => ({
          flags: { ...state.flags, ...results },
        }));
        return results;
      },

      isEnabled: (flagKey) => {
        return get().flags[flagKey]?.enabled ?? false;
      },

      getVariant: (flagKey) => {
        return get().flags[flagKey]?.variant;
      },
    }),
    { name: 'feature-flag-store' }
  )
);

// 选择器
export const useFlag = (flagKey: string) =>
  useFeatureFlagStore(state => state.flags[flagKey]);
export const useFlagEnabled = (flagKey: string) =>
  useFeatureFlagStore(state => state.isEnabled(flagKey));
export const useFlagVariant = (flagKey: string) =>
  useFeatureFlagStore(state => state.getVariant(flagKey));
```

### §2.4 usePriorityStore

> 设计文档: [06-priority-rules.md](../06-priority-rules.md)

**说明**: 7 层优先级计算主要在后端进行，前端只需调用 checkPermission API。此 Store 用于调试和可视化。

```typescript
// 仅用于调试，显示权限来源
export const usePermissionSource = (featureKey: string) =>
  usePermissionStore(state => state.permissions[featureKey]?.source);
```

### §2.5 useUserGroupStore

> 设计文档: [08-user-groups.md](../08-user-groups.md)

**文件**: `@business/stores/entitlement/useUserGroupStore.ts`

```typescript
import { create } from 'zustand';

interface UserGroup {
  id: string;
  name: string;
  priority: number;
}

interface UserGroupState {
  groups: UserGroup[];
  loading: boolean;
}

interface UserGroupActions {
  loadGroups: () => Promise<void>;
}

export const useUserGroupStore = create<UserGroupState & UserGroupActions>()(
  (set) => ({
    groups: [],
    loading: false,

    loadGroups: async () => {
      set({ loading: true });
      const groups = await entitlementApi.getMyGroups();
      set({ groups, loading: false });
    },
  })
);
```

### §2.6 useWorkspaceOverrideStore

> 设计文档: [10-workspace-override.md](../10-workspace-override.md)

**文件**: `@business/stores/entitlement/useWorkspaceOverrideStore.ts`

```typescript
import { create } from 'zustand';

interface WorkspaceOverride {
  featureKey: string;
  value: any;
  expiresAt?: string;
}

interface WorkspaceOverrideState {
  overrides: Record<string, Record<string, WorkspaceOverride>>; // workspaceId -> featureKey -> override
}

interface WorkspaceOverrideActions {
  loadOverrides: (workspaceId: string) => Promise<void>;
  getOverride: (workspaceId: string, featureKey: string) => WorkspaceOverride | undefined;
}

export const useWorkspaceOverrideStore = create<WorkspaceOverrideState & WorkspaceOverrideActions>()(
  (set, get) => ({
    overrides: {},

    loadOverrides: async (workspaceId) => {
      const overrides = await entitlementApi.getWorkspaceOverrides(workspaceId);
      set(state => ({
        overrides: { ...state.overrides, [workspaceId]: overrides },
      }));
    },

    getOverride: (workspaceId, featureKey) => {
      return get().overrides[workspaceId]?.[featureKey];
    },
  })
);
```

---

## §3. 生命周期 Store

### §3.1 useTrialStore

> 设计文档: [11-trial-expiration.md](../11-trial-expiration.md)

**文件**: `@business/stores/entitlement/useTrialStore.ts`

```typescript
import { create } from 'zustand';
import type { TrialStatus } from './types';
import { entitlementApi } from '@business/services/entitlement';

interface TrialState {
  trials: Record<string, TrialStatus>;
  loading: Record<string, boolean>;
}

interface TrialActions {
  getTrialStatus: (featureKey: string) => Promise<TrialStatus>;
  startTrial: (featureKey: string) => Promise<TrialStatus>;
  isTrialActive: (featureKey: string) => boolean;
  getTrialRemainingDays: (featureKey: string) => number | null;
}

export const useTrialStore = create<TrialState & TrialActions>()(
  (set, get) => ({
    trials: {},
    loading: {},

    getTrialStatus: async (featureKey) => {
      set(state => ({
        loading: { ...state.loading, [featureKey]: true },
      }));

      const status = await entitlementApi.getTrialStatus(featureKey);

      set(state => ({
        trials: { ...state.trials, [featureKey]: status },
        loading: { ...state.loading, [featureKey]: false },
      }));

      return status;
    },

    startTrial: async (featureKey) => {
      const status = await entitlementApi.startTrial(featureKey);
      set(state => ({
        trials: { ...state.trials, [featureKey]: status },
      }));
      return status;
    },

    isTrialActive: (featureKey) => {
      const trial = get().trials[featureKey];
      return trial?.status === 'active';
    },

    getTrialRemainingDays: (featureKey) => {
      const trial = get().trials[featureKey];
      return trial?.remainingDays ?? null;
    },
  })
);

// 选择器
export const useTrialStatus = (featureKey: string) =>
  useTrialStore(state => state.trials[featureKey]);
export const useIsTrialActive = (featureKey: string) =>
  useTrialStore(state => state.isTrialActive(featureKey));
```

### §3.2 useTierDowngradeStore

> 设计文档: [12-tier-downgrade.md](../12-tier-downgrade.md)

**文件**: `@business/stores/entitlement/useTierDowngradeStore.ts`

```typescript
import { create } from 'zustand';

interface AffectedResources {
  projectsOverLimit: number;
  pagesOverLimit: number;
  customAssetsAffected: number;
}

interface DowngradePreview {
  fromTier: string;
  toTier: string;
  affectedResources: AffectedResources;
  featuresLost: string[];
}

interface TierDowngradeState {
  preview: DowngradePreview | null;
  loading: boolean;
}

interface TierDowngradeActions {
  previewDowngrade: (toTier: string) => Promise<DowngradePreview>;
  clearPreview: () => void;
}

export const useTierDowngradeStore = create<TierDowngradeState & TierDowngradeActions>()(
  (set) => ({
    preview: null,
    loading: false,

    previewDowngrade: async (toTier) => {
      set({ loading: true });
      const preview = await entitlementApi.previewDowngrade(toTier);
      set({ preview, loading: false });
      return preview;
    },

    clearPreview: () => {
      set({ preview: null });
    },
  })
);
```

### §3.3 useSubscriptionStore

> 设计文档: [13-subscription-pause.md](../13-subscription-pause.md)

**文件**: `@business/stores/entitlement/useSubscriptionStore.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SubscriptionStatus {
  status: 'active' | 'paused' | 'cancelled' | 'past_due';
  currentPeriodEnd?: string;
  pausedUntil?: string;
  cancelAtPeriodEnd: boolean;
}

interface SubscriptionState {
  subscription: SubscriptionStatus | null;
  loading: boolean;
}

interface SubscriptionActions {
  loadSubscription: () => Promise<void>;
  pauseSubscription: (pauseDays: number, reason?: string) => Promise<void>;
  resumeSubscription: () => Promise<void>;
  isPaused: () => boolean;
}

export const useSubscriptionStore = create<SubscriptionState & SubscriptionActions>()(
  persist(
    (set, get) => ({
      subscription: null,
      loading: false,

      loadSubscription: async () => {
        set({ loading: true });
        const subscription = await entitlementApi.getSubscriptionStatus();
        set({ subscription, loading: false });
      },

      pauseSubscription: async (pauseDays, reason) => {
        await entitlementApi.pauseSubscription(pauseDays, reason);
        await get().loadSubscription();
      },

      resumeSubscription: async () => {
        await entitlementApi.resumeSubscription();
        await get().loadSubscription();
      },

      isPaused: () => {
        return get().subscription?.status === 'paused';
      },
    }),
    {
      name: 'subscription-store',
      partialize: (state) => ({ subscription: state.subscription }),
    }
  )
);

// 选择器
export const useSubscriptionStatus = () =>
  useSubscriptionStore(state => state.subscription?.status);
export const useIsPaused = () =>
  useSubscriptionStore(state => state.isPaused());
```

### §3.4 useCreditStore

> 设计文档: [15-credits-lifecycle.md](../15-credits-lifecycle.md)

**文件**: `@business/stores/entitlement/useCreditStore.ts`

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { CreditBalance, CreditTransaction } from './types';
import { entitlementApi } from '@business/services/entitlement';

interface CreditState {
  // 余额信息
  balance: CreditBalance | null;
  // 交易历史
  transactions: CreditTransaction[];
  // 分页信息
  hasMore: boolean;
  // 加载状态
  loading: boolean;
  loadingMore: boolean;
}

interface CreditActions {
  // 加载余额
  loadBalance: () => Promise<void>;
  // 加载交易历史
  loadTransactions: (reset?: boolean) => Promise<void>;
  // 加载更多交易
  loadMoreTransactions: () => Promise<void>;
  // 检查余额是否足够
  hasEnough: (amount: number) => boolean;
  // 消耗积分 (内部使用)
  consume: (amount: number, description: string) => Promise<boolean>;
  // 刷新余额
  refreshBalance: () => Promise<void>;
}

export const useCreditStore = create<CreditState & CreditActions>()(
  devtools(
    persist(
      (set, get) => ({
        balance: null,
        transactions: [],
        hasMore: true,
        loading: false,
        loadingMore: false,

        loadBalance: async () => {
          set({ loading: true });
          const balance = await entitlementApi.getCreditBalance();
          set({ balance, loading: false });
        },

        loadTransactions: async (reset = true) => {
          set({ loading: true });
          const offset = reset ? 0 : get().transactions.length;
          const response = await entitlementApi.getCreditTransactions(50, offset);

          set({
            transactions: reset ? response.items : [...get().transactions, ...response.items],
            hasMore: response.hasMore,
            loading: false,
          });
        },

        loadMoreTransactions: async () => {
          if (!get().hasMore || get().loadingMore) return;

          set({ loadingMore: true });
          const offset = get().transactions.length;
          const response = await entitlementApi.getCreditTransactions(50, offset);

          set({
            transactions: [...get().transactions, ...response.items],
            hasMore: response.hasMore,
            loadingMore: false,
          });
        },

        hasEnough: (amount) => {
          const balance = get().balance;
          if (!balance) return false;
          return balance.total >= amount;
        },

        consume: async (amount, description) => {
          const result = await entitlementApi.consumeCredits(amount, description);
          if (result.success) {
            // 更新本地余额
            await get().loadBalance();
          }
          return result.success;
        },

        refreshBalance: async () => {
          await get().loadBalance();
        },
      }),
      {
        name: 'credit-store',
        partialize: (state) => ({ balance: state.balance }),
      }
    ),
    { name: 'credit-store' }
  )
);

// 选择器
export const useCreditBalance = () => useCreditStore(state => state.balance?.total ?? 0);
export const useCreditBalanceBySource = () => useCreditStore(state => state.balance?.bySource);
export const useHasEnoughCredits = (amount: number) =>
  useCreditStore(state => state.hasEnough(amount));
export const useCreditTransactions = () => useCreditStore(state => state.transactions);
export const useExpiringSoon = () => useCreditStore(state => state.balance?.expiringSoon ?? 0);
```

---

## §4. 营销扩展 Store

### §4.1 usePromotionStore

> 设计文档: [19-promotions.md](../19-promotions.md)

**文件**: `@business/stores/entitlement/usePromotionStore.ts`

```typescript
import { create } from 'zustand';

interface PromotionValidation {
  valid: boolean;
  promotion?: {
    code: string;
    name: string;
    discountType: 'percentage' | 'fixed';
    discountValue: number;
  };
  error?: string;
}

interface PromotionState {
  currentCode: string;
  validation: PromotionValidation | null;
  loading: boolean;
}

interface PromotionActions {
  setCode: (code: string) => void;
  validateCode: (planType?: string) => Promise<PromotionValidation>;
  applyCode: (subscriptionId?: string) => Promise<void>;
  clearCode: () => void;
}

export const usePromotionStore = create<PromotionState & PromotionActions>()(
  (set, get) => ({
    currentCode: '',
    validation: null,
    loading: false,

    setCode: (code) => {
      set({ currentCode: code, validation: null });
    },

    validateCode: async (planType) => {
      const code = get().currentCode;
      if (!code) return { valid: false, error: 'No code entered' };

      set({ loading: true });
      const validation = await entitlementApi.validatePromotionCode(code, planType);
      set({ validation, loading: false });
      return validation;
    },

    applyCode: async (subscriptionId) => {
      const code = get().currentCode;
      await entitlementApi.applyPromotion(code, subscriptionId);
    },

    clearCode: () => {
      set({ currentCode: '', validation: null });
    },
  })
);
```

### §4.2 useReferralStore

> 设计文档: [20-referral-rewards.md](../20-referral-rewards.md)

**文件**: `@business/stores/entitlement/useReferralStore.ts`

```typescript
import { create } from 'zustand';

interface ReferralStats {
  totalReferrals: number;
  qualifiedReferrals: number;
  totalRewardsEarned: number;
  pendingRewards: number;
}

interface ReferralState {
  code: string | null;
  shareUrl: string | null;
  stats: ReferralStats | null;
  loading: boolean;
}

interface ReferralActions {
  loadReferralCode: () => Promise<void>;
  loadStats: () => Promise<void>;
  useCode: (code: string) => Promise<void>;
}

export const useReferralStore = create<ReferralState & ReferralActions>()(
  (set) => ({
    code: null,
    shareUrl: null,
    stats: null,
    loading: false,

    loadReferralCode: async () => {
      set({ loading: true });
      const { code, shareUrl } = await entitlementApi.getMyReferralCode();
      set({ code, shareUrl, loading: false });
    },

    loadStats: async () => {
      const stats = await entitlementApi.getReferralStats();
      set({ stats });
    },

    useCode: async (code) => {
      await entitlementApi.useReferralCode(code);
    },
  })
);

// 选择器
export const useReferralCode = () => useReferralStore(state => state.code);
export const useReferralShareUrl = () => useReferralStore(state => state.shareUrl);
export const useReferralStats = () => useReferralStore(state => state.stats);
```

### §4.3 useFreeQuotaStore

> 设计文档: [22-free-quota.md](../22-free-quota.md)

**文件**: `@business/stores/entitlement/useFreeQuotaStore.ts`

```typescript
import { create } from 'zustand';

interface FreeQuotaState {
  quotas: Record<string, { used: number; limit: number }>;
}

interface FreeQuotaActions {
  checkQuota: (featureKey: string) => Promise<{ used: number; limit: number }>;
  hasQuota: (featureKey: string) => boolean;
}

export const useFreeQuotaStore = create<FreeQuotaState & FreeQuotaActions>()(
  (set, get) => ({
    quotas: {},

    checkQuota: async (featureKey) => {
      const quota = await entitlementApi.checkFreeQuota(featureKey);
      set(state => ({
        quotas: { ...state.quotas, [featureKey]: quota },
      }));
      return quota;
    },

    hasQuota: (featureKey) => {
      const quota = get().quotas[featureKey];
      if (!quota) return true; // 未加载时默认允许
      return quota.used < quota.limit;
    },
  })
);
```

### §4.4 useFeatureSunsetStore

> 设计文档: [23-feature-sunset.md](../23-feature-sunset.md)

**文件**: `@business/stores/entitlement/useFeatureSunsetStore.ts`

```typescript
import { create } from 'zustand';

interface SunsetInfo {
  featureKey: string;
  sunsetDate: string;
  migrationGuide: string;
  daysRemaining: number;
}

interface FeatureSunsetState {
  sunsets: SunsetInfo[];
  dismissed: Set<string>;
}

interface FeatureSunsetActions {
  loadSunsets: () => Promise<void>;
  dismissSunset: (featureKey: string) => void;
  getActiveSunsets: () => SunsetInfo[];
}

export const useFeatureSunsetStore = create<FeatureSunsetState & FeatureSunsetActions>()(
  (set, get) => ({
    sunsets: [],
    dismissed: new Set(),

    loadSunsets: async () => {
      const sunsets = await entitlementApi.getUpcomingSunsets();
      set({ sunsets });
    },

    dismissSunset: (featureKey) => {
      set(state => ({
        dismissed: new Set([...state.dismissed, featureKey]),
      }));
    },

    getActiveSunsets: () => {
      return get().sunsets.filter(s => !get().dismissed.has(s.featureKey));
    },
  })
);
```

---

## 附录: Store 使用示例

### 权限检查示例

```tsx
import { usePermissionStore, useCanUse } from '@business/stores/entitlement';

function AIFeatureButton() {
  const canUseAI = useCanUse('ai_features');
  const { checkPermission } = usePermissionStore();

  useEffect(() => {
    checkPermission('ai_features');
  }, []);

  if (!canUseAI) {
    return <UpgradePrompt feature="ai_features" />;
  }

  return <Button onClick={handleAIAction}>Use AI</Button>;
}
```

### 积分消耗示例

```tsx
import { useCreditStore, useHasEnoughCredits } from '@business/stores/entitlement';

function GenerateImageButton() {
  const hasEnough = useHasEnoughCredits(5); // AI 生图需要 5 积分
  const { consume } = useCreditStore();

  const handleGenerate = async () => {
    const success = await consume(5, 'AI 生图');
    if (success) {
      // 执行生图逻辑
    }
  };

  return (
    <Button onClick={handleGenerate} disabled={!hasEnough}>
      Generate (5 credits)
    </Button>
  );
}
```

---

**END OF DOCUMENT**
