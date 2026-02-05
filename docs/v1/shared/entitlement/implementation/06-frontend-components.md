# 前端组件实现

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 🔴 待实现
> **代码位置**: `decodables-fe/components/entitlement/`

---

## 相关设计文档

| 设计文档 | 本文档章节 |
|----------|-----------|
| 05-ui-spec.md | §2-§5 |
| 08-user-groups.md | §6 |
| 11-trial-expiration.md | §7 |
| 12-tier-downgrade.md | §8 |
| 13-subscription-pause.md | §9 |
| 15-credits-lifecycle.md | §10 |
| 16-renewal-reminders.md | §11 |
| 17-invoice-management.md | §12 |
| 19-promotions.md | §13 |
| 20-referral-rewards.md | §14 |
| 21-education-discount.md | §15 |
| 23-feature-sunset.md | §16 |

---

## 目录

- [§1. 架构概述](#1-架构概述)
- [§2. 权限控制组件](#2-权限控制组件)
- [§3. Tier 展示组件](#3-tier-展示组件)
- [§4. 配额展示组件](#4-配额展示组件)
- [§5. 升级引导组件](#5-升级引导组件)
- [§6. 用户组组件](#6-用户组组件)
- [§7. 试用期组件](#7-试用期组件)
- [§8. 降级警告组件](#8-降级警告组件)
- [§9. 订阅暂停组件](#9-订阅暂停组件)
- [§10. 积分组件](#10-积分组件)
- [§11. 续费提醒组件](#11-续费提醒组件)
- [§12. 发票组件](#12-发票组件)
- [§13. 促销组件](#13-促销组件)
- [§14. 邀请组件](#14-邀请组件)
- [§15. 教育优惠组件](#15-教育优惠组件)
- [§16. 功能下线组件](#16-功能下线组件)

---

## §1. 架构概述

### 1.1 目录结构

```
decodables-fe/components/entitlement/
├── index.ts                    # 导出入口
├── permission/                 # 权限控制
│   ├── FeatureGate.tsx
│   ├── PermissionRequired.tsx
│   └── QuotaGuard.tsx
├── tier/                       # Tier 展示
│   ├── TierBadge.tsx
│   ├── TierComparison.tsx
│   └── PlanCard.tsx
├── upgrade/                    # 升级引导
│   ├── UpgradePrompt.tsx
│   ├── UpgradeModal.tsx
│   └── PaywallOverlay.tsx
├── credits/                    # 积分
│   ├── CreditBalance.tsx
│   ├── CreditHistory.tsx
│   └── CreditPurchase.tsx
├── trial/                      # 试用期
│   ├── TrialBanner.tsx
│   ├── TrialCountdown.tsx
│   └── TrialExpiredModal.tsx
├── subscription/               # 订阅
│   ├── SubscriptionStatus.tsx
│   ├── PauseSubscription.tsx
│   └── RenewalReminder.tsx
├── invoice/                    # 发票
│   ├── InvoiceList.tsx
│   └── InvoiceDetail.tsx
├── promotion/                  # 促销
│   ├── PromoCodeInput.tsx
│   └── PromoBanner.tsx
├── referral/                   # 邀请
│   ├── ReferralCard.tsx
│   └── ReferralStats.tsx
└── hooks/                      # 组件 Hooks
    ├── useFeatureGate.ts
    ├── useUpgradeFlow.ts
    └── useCreditConsume.ts
```

### 1.2 设计原则

1. **声明式权限控制**: 使用 `<FeatureGate>` 包裹需要权限的 UI
2. **优雅降级**: 无权限时显示升级引导而非隐藏
3. **一致的 UI 语言**: 统一的 Badge、Toast、Modal 样式
4. **响应式设计**: 支持移动端和桌面端

---

## §2. 权限控制组件

### 2.1 FeatureGate

**文件**: `components/entitlement/permission/FeatureGate.tsx`

**用途**: 根据功能权限控制子组件渲染

```tsx
import { ReactNode, useEffect } from 'react';
import { usePermissionStore, useCanUse, useIsTrialing } from '@business/stores/entitlement';
import { UpgradePrompt } from '../upgrade/UpgradePrompt';
import { TrialBanner } from '../trial/TrialBanner';

interface FeatureGateProps {
  feature: string;
  children: ReactNode;
  // 无权限时的替代内容
  fallback?: ReactNode;
  // 是否显示升级引导
  showUpgrade?: boolean;
  // 自定义升级文案
  upgradeMessage?: string;
  // 工作区 ID (可选)
  workspaceId?: string;
}

export function FeatureGate({
  feature,
  children,
  fallback,
  showUpgrade = true,
  upgradeMessage,
  workspaceId,
}: FeatureGateProps) {
  const { checkPermission } = usePermissionStore();
  const canUse = useCanUse(feature);
  const isTrialing = useIsTrialing(feature);

  // 首次加载时检查权限
  useEffect(() => {
    checkPermission(feature, workspaceId);
  }, [feature, workspaceId]);

  // 正式权限 - 直接渲染
  if (canUse && !isTrialing) {
    return <>{children}</>;
  }

  // 试用中 - 显示试用 Banner + 内容
  if (isTrialing) {
    return (
      <>
        <TrialBanner feature={feature} />
        {children}
      </>
    );
  }

  // 无权限 - 显示升级引导或自定义 fallback
  if (showUpgrade) {
    return (
      <UpgradePrompt
        feature={feature}
        message={upgradeMessage}
      />
    );
  }

  return fallback ? <>{fallback}</> : null;
}
```

### 2.2 PermissionRequired

**文件**: `components/entitlement/permission/PermissionRequired.tsx`

**用途**: HOC 风格的权限控制

```tsx
import { ComponentType } from 'react';
import { FeatureGate } from './FeatureGate';

interface WithPermissionOptions {
  feature: string;
  fallback?: ReactNode;
}

export function withPermission<P extends object>(
  WrappedComponent: ComponentType<P>,
  options: WithPermissionOptions
) {
  return function PermissionWrapper(props: P) {
    return (
      <FeatureGate feature={options.feature} fallback={options.fallback}>
        <WrappedComponent {...props} />
      </FeatureGate>
    );
  };
}

// Hook 风格
export function useRequirePermission(feature: string): {
  hasPermission: boolean;
  isTrialing: boolean;
  checkPermission: () => Promise<void>;
} {
  const { checkPermission } = usePermissionStore();
  const canUse = useCanUse(feature);
  const isTrialing = useIsTrialing(feature);

  return {
    hasPermission: canUse,
    isTrialing,
    checkPermission: () => checkPermission(feature),
  };
}
```

### 2.3 QuotaGuard

**文件**: `components/entitlement/permission/QuotaGuard.tsx`

**用途**: 配额控制

```tsx
interface QuotaGuardProps {
  quota: string; // 如 "max_projects", "max_pages_per_project"
  children: ReactNode;
  onQuotaExceeded?: () => void;
}

export function QuotaGuard({
  quota,
  children,
  onQuotaExceeded,
}: QuotaGuardProps) {
  const hasQuota = useHasQuota(quota);

  if (!hasQuota) {
    onQuotaExceeded?.();
    return <QuotaExceededPrompt quota={quota} />;
  }

  return <>{children}</>;
}
```

---

## §3. Tier 展示组件

### 3.1 TierBadge

**文件**: `components/entitlement/tier/TierBadge.tsx`

**用途**: 显示 Tier 徽章

```tsx
import { cn } from '@/lib/utils';

interface TierBadgeProps {
  tier: 't1' | 't2' | 't3' | 't4';
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
}

const TIER_CONFIG = {
  t1: { name: 'Free', color: 'bg-emerald-100 text-emerald-800' },
  t2: { name: 'Starter', color: 'bg-blue-100 text-blue-800' },
  t3: { name: 'Pro', color: 'bg-violet-100 text-violet-800' },
  t4: { name: 'Enterprise', color: 'bg-amber-100 text-amber-800' },
};

export function TierBadge({ tier, size = 'md', showName = true }: TierBadgeProps) {
  const config = TIER_CONFIG[tier];

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium',
        config.color,
        sizeClasses[size]
      )}
    >
      {showName ? config.name : tier.toUpperCase()}
    </span>
  );
}
```

### 3.2 TierComparison

**文件**: `components/entitlement/tier/TierComparison.tsx`

**用途**: Tier 功能对比表

```tsx
interface TierComparisonProps {
  currentTier?: string;
  highlightTier?: string;
}

export function TierComparison({ currentTier, highlightTier }: TierComparisonProps) {
  const features = [
    { key: 'max_projects', label: '项目数量' },
    { key: 'max_pages_per_project', label: '每项目页面数' },
    { key: 'ai_features', label: 'AI 功能' },
    { key: 'smart_scan', label: '智能扫描' },
    // ... 更多功能
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr>
            <th>功能</th>
            {['t1', 't2', 't3'].map(tier => (
              <th
                key={tier}
                className={cn(
                  tier === highlightTier && 'bg-primary/10',
                  tier === currentTier && 'ring-2 ring-primary'
                )}
              >
                <TierBadge tier={tier as any} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {features.map(feature => (
            <FeatureRow key={feature.key} feature={feature} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### 3.3 PlanCard

**文件**: `components/entitlement/tier/PlanCard.tsx`

**用途**: 定价页面的套餐卡片

```tsx
interface PlanCardProps {
  tier: 't1' | 't2' | 't3';
  isCurrent?: boolean;
  isPopular?: boolean;
  onSelect?: () => void;
}

export function PlanCard({ tier, isCurrent, isPopular, onSelect }: PlanCardProps) {
  const { features, quotas, price } = useTierConfig(tier);

  return (
    <div
      className={cn(
        'relative rounded-2xl border p-6',
        isPopular && 'border-primary shadow-lg',
        isCurrent && 'ring-2 ring-primary'
      )}
    >
      {isPopular && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white px-3 py-1 rounded-full text-sm">
          Most Popular
        </span>
      )}

      <TierBadge tier={tier} size="lg" />

      <div className="mt-4">
        <span className="text-4xl font-bold">${price}</span>
        <span className="text-muted-foreground">/month</span>
      </div>

      <ul className="mt-6 space-y-3">
        {/* 配额 */}
        <li className="flex items-center gap-2">
          <CheckIcon className="text-green-500" />
          <span>{quotas.max_projects === -1 ? 'Unlimited' : quotas.max_projects} projects</span>
        </li>
        {/* ... 更多功能列表 */}
      </ul>

      <Button
        className="w-full mt-6"
        variant={isCurrent ? 'outline' : 'default'}
        onClick={onSelect}
        disabled={isCurrent}
      >
        {isCurrent ? 'Current Plan' : 'Select Plan'}
      </Button>
    </div>
  );
}
```

---

## §4. 配额展示组件

### 4.1 QuotaProgress

**文件**: `components/entitlement/quota/QuotaProgress.tsx`

```tsx
interface QuotaProgressProps {
  quota: string;
  label: string;
}

export function QuotaProgress({ quota, label }: QuotaProgressProps) {
  const { quotaUsage } = useTierStore();
  const usage = quotaUsage[quota];

  if (!usage) return null;

  const percentage = usage.limit === -1 ? 0 : (usage.used / usage.limit) * 100;
  const isNearLimit = percentage > 80;
  const isAtLimit = percentage >= 100;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className={cn(isAtLimit && 'text-red-500')}>
          {usage.used} / {usage.limit === -1 ? '∞' : usage.limit}
        </span>
      </div>
      <Progress
        value={Math.min(percentage, 100)}
        className={cn(
          isNearLimit && 'bg-yellow-100',
          isAtLimit && 'bg-red-100'
        )}
      />
      {isNearLimit && !isAtLimit && (
        <p className="text-xs text-yellow-600">
          接近配额上限，请考虑升级
        </p>
      )}
    </div>
  );
}
```

---

## §5. 升级引导组件

### 5.1 UpgradePrompt

**文件**: `components/entitlement/upgrade/UpgradePrompt.tsx`

```tsx
interface UpgradePromptProps {
  feature: string;
  message?: string;
  variant?: 'inline' | 'card' | 'banner';
}

export function UpgradePrompt({
  feature,
  message,
  variant = 'card',
}: UpgradePromptProps) {
  const { openUpgradeModal } = useUpgradeFlow();
  const featureInfo = getFeatureInfo(feature);

  if (variant === 'inline') {
    return (
      <span className="text-muted-foreground">
        {message || `升级以使用 ${featureInfo.name}`}
        <Button variant="link" onClick={() => openUpgradeModal(feature)}>
          升级
        </Button>
      </span>
    );
  }

  if (variant === 'banner') {
    return (
      <div className="bg-gradient-to-r from-primary/10 to-primary/5 p-4 rounded-lg flex items-center justify-between">
        <div>
          <h4 className="font-medium">{featureInfo.name}</h4>
          <p className="text-sm text-muted-foreground">
            {message || featureInfo.description}
          </p>
        </div>
        <Button onClick={() => openUpgradeModal(feature)}>
          升级解锁
        </Button>
      </div>
    );
  }

  // Card variant (default)
  return (
    <Card className="p-6 text-center">
      <LockIcon className="mx-auto h-12 w-12 text-muted-foreground" />
      <h3 className="mt-4 font-semibold">{featureInfo.name}</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        {message || `此功能需要 ${featureInfo.requiredTier} 及以上套餐`}
      </p>
      <Button className="mt-4" onClick={() => openUpgradeModal(feature)}>
        查看套餐
      </Button>
    </Card>
  );
}
```

### 5.2 UpgradeModal

**文件**: `components/entitlement/upgrade/UpgradeModal.tsx`

```tsx
interface UpgradeModalProps {
  open: boolean;
  onClose: () => void;
  feature?: string;
  recommendedTier?: string;
}

export function UpgradeModal({
  open,
  onClose,
  feature,
  recommendedTier,
}: UpgradeModalProps) {
  const { currentTier } = useTierStore();
  const [selectedTier, setSelectedTier] = useState(recommendedTier || 't2');

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>选择适合你的套餐</DialogTitle>
          {feature && (
            <DialogDescription>
              升级以解锁 {getFeatureInfo(feature).name} 等更多功能
            </DialogDescription>
          )}
        </DialogHeader>

        <div className="grid grid-cols-3 gap-4 py-6">
          {['t1', 't2', 't3'].map(tier => (
            <PlanCard
              key={tier}
              tier={tier as any}
              isCurrent={tier === currentTier}
              isPopular={tier === 't2'}
              onSelect={() => setSelectedTier(tier)}
            />
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            稍后再说
          </Button>
          <Button
            onClick={() => handleUpgrade(selectedTier)}
            disabled={selectedTier === currentTier}
          >
            升级到 {TIER_CONFIG[selectedTier].name}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### 5.3 PaywallOverlay

**文件**: `components/entitlement/upgrade/PaywallOverlay.tsx`

**用途**: 覆盖在需要付费的内容上

```tsx
interface PaywallOverlayProps {
  feature: string;
  children: ReactNode;
}

export function PaywallOverlay({ feature, children }: PaywallOverlayProps) {
  const canUse = useCanUse(feature);

  if (canUse) {
    return <>{children}</>;
  }

  return (
    <div className="relative">
      {/* 模糊的背景内容 */}
      <div className="blur-sm pointer-events-none">
        {children}
      </div>

      {/* 付费墙遮罩 */}
      <div className="absolute inset-0 flex items-center justify-center bg-background/80">
        <UpgradePrompt feature={feature} variant="card" />
      </div>
    </div>
  );
}
```

---

## §7. 试用期组件

### 7.1 TrialBanner

**文件**: `components/entitlement/trial/TrialBanner.tsx`

```tsx
interface TrialBannerProps {
  feature: string;
}

export function TrialBanner({ feature }: TrialBannerProps) {
  const trialStatus = useTrialStatus(feature);
  const remainingDays = trialStatus?.remainingDays;

  if (!trialStatus || trialStatus.status !== 'active') {
    return null;
  }

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <ClockIcon className="h-5 w-5 text-amber-600" />
        <span className="text-sm">
          试用期还剩 <strong>{remainingDays}</strong> 天
        </span>
      </div>
      <Button size="sm" variant="outline" onClick={handleUpgrade}>
        立即订阅
      </Button>
    </div>
  );
}
```

### 7.2 TrialCountdown

**文件**: `components/entitlement/trial/TrialCountdown.tsx`

```tsx
export function TrialCountdown({ feature }: { feature: string }) {
  const trialStatus = useTrialStatus(feature);

  if (!trialStatus?.expiresAt) return null;

  const expiresAt = new Date(trialStatus.expiresAt);

  return (
    <div className="text-center p-4 bg-gradient-to-r from-primary/5 to-primary/10 rounded-lg">
      <p className="text-sm text-muted-foreground mb-2">试用期倒计时</p>
      <Countdown
        date={expiresAt}
        renderer={({ days, hours, minutes, seconds }) => (
          <div className="flex gap-4 justify-center">
            <TimeUnit value={days} label="天" />
            <TimeUnit value={hours} label="时" />
            <TimeUnit value={minutes} label="分" />
            <TimeUnit value={seconds} label="秒" />
          </div>
        )}
      />
    </div>
  );
}
```

### 7.3 TrialExpiredModal

**文件**: `components/entitlement/trial/TrialExpiredModal.tsx`

```tsx
export function TrialExpiredModal({ feature }: { feature: string }) {
  const [open, setOpen] = useState(false);
  const trialStatus = useTrialStatus(feature);

  useEffect(() => {
    if (trialStatus?.status === 'expired') {
      setOpen(true);
    }
  }, [trialStatus?.status]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>试用期已结束</DialogTitle>
          <DialogDescription>
            {getFeatureInfo(feature).name} 的 7 天试用期已结束。
            订阅以继续使用此功能。
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <TierComparison highlightTier="t2" />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            稍后再说
          </Button>
          <Button onClick={handleUpgrade}>
            立即订阅
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

## §10. 积分组件

### 10.1 CreditBalance

**文件**: `components/entitlement/credits/CreditBalance.tsx`

```tsx
export function CreditBalance() {
  const balance = useCreditBalance();
  const expiringSoon = useExpiringSoon();

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <CoinIcon className="h-5 w-5 text-amber-500" />
        <span className="text-lg font-semibold">{balance}</span>
        <span className="text-muted-foreground">积分</span>
      </div>

      {expiringSoon > 0 && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="warning">
                {expiringSoon} 即将过期
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              7 天内将有 {expiringSoon} 积分过期
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}
```

### 10.2 CreditHistory

**文件**: `components/entitlement/credits/CreditHistory.tsx`

```tsx
export function CreditHistory() {
  const transactions = useCreditTransactions();
  const { loadMoreTransactions, hasMore, loadingMore } = useCreditStore();

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">积分记录</h3>

      <div className="divide-y">
        {transactions.map(tx => (
          <div key={tx.id} className="py-3 flex items-center justify-between">
            <div>
              <p className="font-medium">
                {tx.type === 'grant' ? '获得' : '消耗'}
              </p>
              <p className="text-sm text-muted-foreground">
                {tx.description}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatDate(tx.createdAt)}
              </p>
            </div>
            <span
              className={cn(
                'font-semibold',
                tx.amount > 0 ? 'text-green-600' : 'text-red-600'
              )}
            >
              {tx.amount > 0 ? '+' : ''}{tx.amount}
            </span>
          </div>
        ))}
      </div>

      {hasMore && (
        <Button
          variant="outline"
          className="w-full"
          onClick={loadMoreTransactions}
          disabled={loadingMore}
        >
          {loadingMore ? '加载中...' : '加载更多'}
        </Button>
      )}
    </div>
  );
}
```

### 10.3 CreditPurchase

**文件**: `components/entitlement/credits/CreditPurchase.tsx`

```tsx
const CREDIT_PACKAGES = [
  { id: 'credits_100', credits: 100, price: 2.99 },
  { id: 'credits_500', credits: 500, price: 13.46, originalPrice: 14.95 },
  { id: 'credits_2000', credits: 2000, price: 47.84, originalPrice: 59.80 },
];

export function CreditPurchase() {
  const [selected, setSelected] = useState('credits_500');
  const [loading, setLoading] = useState(false);

  const handlePurchase = async () => {
    setLoading(true);
    try {
      await purchaseCredits(selected);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="font-semibold">购买积分</h3>

      <div className="grid grid-cols-3 gap-4">
        {CREDIT_PACKAGES.map(pkg => (
          <div
            key={pkg.id}
            className={cn(
              'border rounded-lg p-4 cursor-pointer transition-all',
              selected === pkg.id && 'border-primary ring-2 ring-primary/20'
            )}
            onClick={() => setSelected(pkg.id)}
          >
            <div className="text-center">
              <p className="text-2xl font-bold">{pkg.credits}</p>
              <p className="text-sm text-muted-foreground">积分</p>

              <div className="mt-2">
                {pkg.originalPrice && (
                  <span className="text-sm line-through text-muted-foreground mr-2">
                    ${pkg.originalPrice}
                  </span>
                )}
                <span className="font-semibold">${pkg.price}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Button
        className="w-full"
        onClick={handlePurchase}
        disabled={loading}
      >
        {loading ? '处理中...' : '购买'}
      </Button>
    </div>
  );
}
```

---

## §13. 促销组件

### 13.1 PromoCodeInput

**文件**: `components/entitlement/promotion/PromoCodeInput.tsx`

```tsx
export function PromoCodeInput({ onApply }: { onApply?: () => void }) {
  const { currentCode, setCode, validateCode, validation, loading } = usePromotionStore();

  const handleValidate = async () => {
    const result = await validateCode();
    if (result.valid) {
      onApply?.();
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          placeholder="输入促销码"
          value={currentCode}
          onChange={e => setCode(e.target.value)}
        />
        <Button
          onClick={handleValidate}
          disabled={!currentCode || loading}
        >
          {loading ? '验证中...' : '应用'}
        </Button>
      </div>

      {validation && (
        <div className={cn(
          'text-sm',
          validation.valid ? 'text-green-600' : 'text-red-600'
        )}>
          {validation.valid
            ? `优惠码有效！${validation.promotion?.discountType === 'percentage'
                ? `${validation.promotion.discountValue}% 折扣`
                : `立减 $${validation.promotion?.discountValue}`}`
            : validation.error}
        </div>
      )}
    </div>
  );
}
```

---

## §14. 邀请组件

### 14.1 ReferralCard

**文件**: `components/entitlement/referral/ReferralCard.tsx`

```tsx
export function ReferralCard() {
  const code = useReferralCode();
  const shareUrl = useReferralShareUrl();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareUrl || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="p-6">
      <h3 className="font-semibold">邀请好友</h3>
      <p className="text-sm text-muted-foreground mt-1">
        邀请好友注册，你和好友各得 50 积分
      </p>

      <div className="mt-4 flex gap-2">
        <Input value={code || ''} readOnly className="font-mono" />
        <Button variant="outline" onClick={handleCopy}>
          {copied ? <CheckIcon /> : <CopyIcon />}
        </Button>
      </div>

      <div className="mt-4 flex gap-2">
        <Button variant="outline" className="flex-1" onClick={shareToTwitter}>
          <TwitterIcon className="mr-2 h-4 w-4" />
          Twitter
        </Button>
        <Button variant="outline" className="flex-1" onClick={shareToFacebook}>
          <FacebookIcon className="mr-2 h-4 w-4" />
          Facebook
        </Button>
      </div>
    </Card>
  );
}
```

### 14.2 ReferralStats

**文件**: `components/entitlement/referral/ReferralStats.tsx`

```tsx
export function ReferralStats() {
  const stats = useReferralStats();

  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 gap-4">
      <StatCard
        label="已邀请"
        value={stats.totalReferrals}
        icon={<UsersIcon />}
      />
      <StatCard
        label="已获奖励"
        value={`${stats.totalRewardsEarned} 积分`}
        icon={<GiftIcon />}
      />
    </div>
  );
}
```

---

## 附录: 组件使用示例

### 权限控制示例

```tsx
// 方式 1: 声明式
function AIImageGenerator() {
  return (
    <FeatureGate feature="ai_features">
      <ImageGeneratorUI />
    </FeatureGate>
  );
}

// 方式 2: HOC
const ProtectedImageGenerator = withPermission(ImageGeneratorUI, {
  feature: 'ai_features',
});

// 方式 3: Hook
function SmartScanButton() {
  const { hasPermission, isTrialing } = useRequirePermission('smart_scan');

  if (!hasPermission) {
    return <UpgradePrompt feature="smart_scan" variant="inline" />;
  }

  return (
    <Button>
      {isTrialing && <Badge className="mr-2">试用</Badge>}
      智能扫描
    </Button>
  );
}
```

---

**END OF DOCUMENT**
