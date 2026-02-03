# 用户权限 UI 交互规范

> **版本**: v1.1
> **日期**: 2026-02-03
> **状态**: 设计完成
> **适用范围**: 功能权限、配额限制的前端 UI 交互

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [entitlement-system-design.md](./entitlement-system-design.md) | 系统架构总览 |
| [entitlement-permission-matrix.md](./entitlement-permission-matrix.md) | 功能权限矩阵 (**唯一数据源**) |
| [feature-flag-engine.md](./feature-flag-engine.md) | Feature Flag 评估引擎 |

---

## 一、核心原则

### 1.1 主动锁定模式 (Proactive Lock)

| 模式 | 代表产品 | 用户体验 | 服务器负载 |
|------|----------|----------|------------|
| **主动锁定** ✓ | Figma, Notion, Canva | 最佳 | 零额外请求 |
| 被动拦截 | 传统应用 | 一般 | 浪费请求 |

**原则**:
- 在用户点击前就显示限制状态
- 按钮显示 Lock 图标 + Tooltip 提示原因
- 点击后直接打开 UpgradeModal，不发起 API 请求

### 1.2 UI 状态映射

```
功能权限状态:
├── full (完全可用)     → 正常按钮，无特殊标记
├── trial (试用期内)    → 正常按钮 + Trial Badge
├── locked (无权限)     → 按钮可见 + Lock 图标 + Tooltip + 点击弹 UpgradeModal
└── disabled (功能下线) → 按钮完全隐藏
```

### 1.3 视觉规范

| 状态 | 按钮外观 | 图标 | Tooltip | 点击行为 |
|------|---------|------|---------|---------|
| `full` | 正常 | 无 | 无 | 执行功能 |
| `trial` | 正常 | Badge "Trial" | "X days remaining" | 执行功能 |
| `locked` | `opacity-70` | 🔒 `Lock` `w-3.5 h-3.5 text-amber-500` | "Upgrade to unlock" | 弹 UpgradeModal |
| `disabled` | 不渲染 | - | - | - |

---

## 二、配额类交互 (Quota)

### 2.1 useQuotaGuard Hook

```tsx
const { isAtLimit, checkAndTrigger } = useQuotaGuard({
  type: 'project',
  currentCount: projectsTotal,
});

<Button onClick={() => checkAndTrigger(() => openModal())}>
  New Project
  {isAtLimit && <Lock className="w-3.5 h-3.5 text-amber-500" />}
</Button>
```

### 2.2 QuotaBar 组件 (侧边栏)

```
┌──────────────────────────────┐
│  Projects              0/3   │  ← 标签 + 当前/最大
│  ████░░░░░░░░░░░░░░░░░░░░░░  │  ← 进度条 (颜色随状态变化)
├──────────────────────────────┤
│  ✨ Upgrade for more         │  ← 升级入口 (达到限制时显示)
└──────────────────────────────┘
```

**颜色状态映射**:

| 使用百分比 | 进度条颜色 | 数字颜色 | 状态 |
|-----------|-----------|---------|------|
| 0%-79% | `bg-indigo-500` | `text-slate-700` | 正常 |
| 80%-99% | `bg-amber-500` | `text-amber-600` | 警告 |
| 100% | `bg-red-500` | `text-red-600` | 达到限制 |

**Unlimited 状态**:

```
┌──────────────────────────────┐
│  Projects            5 / ∞   │  ← 数字 + 无限符号
│  (无进度条)                    │  ← 不显示进度条
└──────────────────────────────┘
```

### 2.3 配额警告条

**显示规则**: 仅在 ≥80% 时显示于 Dashboard 主区域顶部

| 阈值 | 背景色 | 图标 | 提示内容 |
|------|-------|------|---------|
| 80%-99% | `bg-amber-50 border-amber-200` | ⚡ Zap (amber) | "2 projects remaining. Upgrade for more" |
| 100% | `bg-red-50 border-red-200` | ⚠️ AlertTriangle (red) | "Project limit reached. Upgrade your plan" |

---

## 三、功能开关类交互 (Feature)

### 3.1 useFeatureAccess Hook

```tsx
const { isLocked, isTrial, checkAndTrigger, trialDaysRemaining } =
  useFeatureAccess('ai_features');

<Button onClick={() => checkAndTrigger(() => doAction())}>
  AI 生成
  {isTrial && <Badge variant="outline">Trial · {trialDaysRemaining}d left</Badge>}
  {isLocked && <Lock className="w-3.5 h-3.5 text-amber-500" />}
</Button>
```

### 3.2 锁定按钮示例

```tsx
<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => checkAndTrigger(() => selectTool('vector'))}
        className={cn(isLocked && "opacity-50 cursor-not-allowed")}
      >
        <Pen className="w-4 h-4" />
        {isLocked && (
          <Lock className="w-3 h-3 text-amber-500 absolute -top-1 -right-1" />
        )}
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      {isLocked ? "Vector tools require Starter plan" : "Vector Tool"}
    </TooltipContent>
  </Tooltip>
</TooltipProvider>
```

---

## 四、页面级交互详表

### 4.1 Dashboard 页面

| 功能 | 组件位置 | 无权限时展示 | 交互行为 |
|------|---------|-------------|---------|
| **New Project** | `DashboardHeader` | 按钮 + 🔒 + `opacity-70` | Tooltip: "Project limit reached (1/1)" → UpgradeModal |
| **New Folder** | `DashboardHeader` | 按钮 + 🔒 + `opacity-70` | Tooltip: "Folder limit reached" → UpgradeModal |
| **Create Workspace** | `WorkspaceSwitcher` | 选项 + 🔒 + `text-slate-400` | Tooltip: "Pro plan required" → UpgradeModal |
| **Invite Members** | `MembersSection` | 按钮 + 🔒 | Tooltip: "Pro plan required" → UpgradeModal |
| **Restore from Trash** | `TrashSection` | 按钮 + 🔒 | Tooltip: "30-day recovery requires Pro" → UpgradeModal |

### 4.2 Editor 页面

| 功能 | 组件位置 | 无权限时展示 | 交互行为 |
|------|---------|-------------|---------|
| **AI 生成素材** | `CustomAssets` | 按钮 + 🔒 | Trial 时显示 Badge; 锁定时弹 UpgradeModal |
| **Smart Scan (OCR)** | `CustomAssets` | 按钮 + 🔒 | Tooltip: "Smart Scan requires Pro" → UpgradeModal |
| **Upload Custom Asset** | `CustomAssets` | 上传按钮 + 🔒 | Tooltip: "Custom uploads require Pro" → UpgradeModal |
| **ZIP Export** | `TopBarExport` | 菜单项 + 🔒 | Tooltip: "ZIP export requires Pro" → UpgradeModal |
| **矢量图工具** | `DrawingCanvas` | 工具图标 + 🔒 覆盖 | Tooltip: "Vector tools require Starter" → UpgradeModal |
| **画笔工具** | `DrawingCanvas` | 工具图标 + 🔒 覆盖 | Tooltip: "Brush tools require Starter" → UpgradeModal |
| **剪贴板粘贴** | 全局快捷键 | Toast 提示 | Toast: "Clipboard paste requires Pro" + Upgrade 按钮 |

### 4.3 Export 菜单

```tsx
<DropdownMenuContent>
  {/* PDF 打印 - 所有人可用 */}
  <DropdownMenuItem onClick={handlePrint}>
    <Printer className="w-4 h-4 mr-2" />
    Print PDF
  </DropdownMenuItem>

  {/* PDF 下载 - Trial 超出锁定 */}
  <DropdownMenuItem
    onClick={() => pdfAccess.checkAndTrigger(handleDownloadPdf)}
    className={cn(pdfAccess.isLocked && "opacity-70")}
  >
    <FileDown className="w-4 h-4 mr-2" />
    Download PDF
    {pdfAccess.isLocked && <Lock className="w-3.5 h-3.5 text-amber-500 ml-auto" />}
  </DropdownMenuItem>

  {/* ZIP 导出 - Pro only */}
  <DropdownMenuItem
    onClick={() => zipAccess.checkAndTrigger(handleZipExport)}
    className={cn(zipAccess.isLocked && "opacity-70")}
  >
    <Archive className="w-4 h-4 mr-2" />
    Export ZIP (PDF + Images)
    {zipAccess.isLocked && <Lock className="w-3.5 h-3.5 text-amber-500 ml-auto" />}
  </DropdownMenuItem>
</DropdownMenuContent>
```

### 4.4 Marketplace 页面

| 功能 | 组件位置 | 无权限时展示 | 交互行为 |
|------|---------|-------------|---------|
| **浏览商城** | `marketplace/page` | 商品卡片 + 🔒 覆盖层 | Toast + UpgradeModal |
| **购买商品** | `QuickViewModal` | Buy 按钮 + 🔒 | Tooltip: "Purchasing requires Starter" → UpgradeModal |
| **发布免费项目** | `PublishAssetDialog` | 发布选项 + 🔒 | Tooltip: "Free publishing requires Starter" → UpgradeModal |
| **发布付费项目** | `PublishAssetDialog` | 发布选项 + 🔒 | Tooltip: "Paid publishing requires Pro" → UpgradeModal |

---

## 五、UpgradeModal 规范

### 5.1 布局结构

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🟢 Free Plan        💎 Monthly 0  ∞ Permanent 100  🔶 100 │   │ ← Header
│  │    Free trial active                         Total Credits│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌───────────────────┐    ┌─────────────────────────┐          │
│  │   ⚡ Starter       │    │   👑 Pro   BEST VALUE   │          │
│  │   $6.9 /mo         │    │   $9.9 /mo              │          │
│  │                    │    │                         │          │
│  │ 💎 100 Credits/Mo  │    │ 💎 200 Credits/Mo       │          │
│  │ ✓ AI Image Gen     │    │ ✓ Everything in Starter │          │
│  │ ✓ PDF Export       │    │ ✓ Smart Scan OCR        │          │
│  │ ✗ Smart Scan/ZIP   │    │ ✓ ZIP Export            │          │
│  │                    │    │                         │          │
│  │ [Subscribe Starter]│    │ [Subscribe to Pro]      │          │
│  └───────────────────┘    └─────────────────────────┘          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔶 Buy Credits    One-time purchase, never expires       │   │
│  │ ┌─────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│  │ │ 💎 100  │  │ 💎 500 Pop  │  │ 💎 2000 -20%│           │   │
│  │ │ $2.99   │  │ $13.49      │  │ $48.00      │           │   │
│  │ └─────────┘  └─────────────┘  └─────────────┘           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 根据触发功能动态高亮

```tsx
const getRecommendedPlan = (feature: FeatureKey): 't2' | 't3' => {
  const proOnlyFeatures = [
    'smart_scan', 'zip_export', 'clipboard_paste',
    'commercial_license', 'history_assets', 'custom_upload'
  ];

  if (proOnlyFeatures.includes(feature)) return 't3';
  return 't2';
};

// 高亮效果
<div className={cn(
  "border rounded-xl p-4",
  isRecommended && "ring-2 ring-violet-500 border-violet-300",
)}>
  {isRecommended && (
    <Badge className="absolute -top-3 bg-violet-500">RECOMMENDED</Badge>
  )}
</div>
```

### 5.3 响应式设计

| 断点 | Plan 卡片布局 | Credits 卡片布局 |
|------|-------------|-----------------|
| Desktop (≥768px) | 2列横排 | 3列横排 |
| Mobile (<768px) | 1列竖排 | 1列竖排 |

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  <StarterPlanCard />
  <ProPlanCard />
</div>
```

---

## 六、Toast 提示规范

对于无法显示 Lock 图标的场景 (如快捷键操作):

```tsx
toast({
  title: "Feature Locked",
  description: "Clipboard paste requires Pro plan.",
  action: (
    <Button
      variant="outline"
      size="sm"
      onClick={() => openUpgradeModal('clipboard_paste')}
    >
      Upgrade
    </Button>
  ),
});
```

---

## 七、API 错误 Fallback

即使前端做了主动锁定，仍需保留 API 错误处理作为纵深防御：

```tsx
} catch (err) {
  const errorMessage = err instanceof Error ? err.message : "";

  // 检测配额/权限限制错误 → 打开 UpgradeModal
  if (errorMessage.includes("project limit") ||
      errorMessage.includes("quota exceeded") ||
      errorMessage.includes("requires tier")) {
    openUpgradeModal(featureKey);
    return;
  }

  // 其他错误显示友好提示
  setError("Failed to complete action. Please try again.");
}
```

---

## 八、Trial 状态特殊处理

Trial 期间的功能显示 Badge 而非 Lock：

```tsx
<Button onClick={() => checkAndTrigger(doAction)}>
  <Sparkles className="w-4 h-4 mr-2" />
  AI Generate
  {isTrial && (
    <Badge variant="outline" className="ml-2 text-xs">
      Trial · {daysRemaining}d left
    </Badge>
  )}
  {isLocked && <Lock className="w-3.5 h-3.5 text-amber-500 ml-2" />}
</Button>
```

---

## 九、配额刷新时机

| 触发事件 | 刷新配额 |
|---------|---------|
| 页面加载 | ✅ 从 `/user/features` 获取 |
| 创建项目成功 | ✅ 本地 +1 |
| 删除项目成功 | ✅ 本地 -1 |
| Tier 升级 | ✅ 重新获取 `/user/features` |
| 5 分钟定时器 | ⚠️ 可选，用于多端同步 |

**重要**: 移动到回收站 ≠ 释放配额。只有永久删除才释放。

---

## 十、配额类 Hook 与组件实现

### 10.1 useQuotaGuard Hook

```tsx
// hooks/useQuotaGuard.ts
import { useCallback, useMemo } from 'react';
import { useUserStore } from '@/lib/useUserStore';
import { useModalStore } from '@/lib/useModalStore';
import { useAllTiers } from '@/lib/config';

export type QuotaType = 'project' | 'folder' | 'workspace' | 'custom_asset';

export interface UseQuotaGuardOptions {
  type: QuotaType;
  currentCount: number;
}

export interface UseQuotaGuardReturn {
  canCreate: boolean;
  isAtLimit: boolean;
  currentCount: number;
  maxCount: number;
  isUnlimited: boolean;
  checkAndTrigger: (callback?: () => void) => void;
}

export function useQuotaGuard({ type, currentCount }: UseQuotaGuardOptions): UseQuotaGuardReturn {
  const { tier } = useUserStore();
  const { openUpgradeModal } = useModalStore();
  const allTiers = useAllTiers();

  const maxCount = useMemo(() => {
    const tierConfig = allTiers.find(t => t.key === tier);
    switch (type) {
      case 'project': return tierConfig?.maxProjects ?? 1;
      case 'folder': return tierConfig?.maxFolders ?? 1;
      case 'workspace': return tierConfig?.maxWorkspaces ?? 1;
      case 'custom_asset': return tierConfig?.maxCustomAssets ?? 0;
      default: return 1;
    }
  }, [tier, type, allTiers]);

  const isUnlimited = maxCount === -1;
  const isAtLimit = !isUnlimited && currentCount >= maxCount;
  const canCreate = isUnlimited || currentCount < maxCount;

  const checkAndTrigger = useCallback((callback?: () => void) => {
    if (canCreate) {
      callback?.();
    } else {
      openUpgradeModal(`quota.${type}`);
    }
  }, [canCreate, openUpgradeModal, type]);

  return {
    canCreate,
    isAtLimit,
    currentCount,
    maxCount,
    isUnlimited,
    checkAndTrigger,
  };
}
```

### 10.2 QuotaBar 组件 (侧边栏)

```tsx
// components/dashboard/QuotaBar.tsx
import { cn } from '@/lib/utils';

interface QuotaItemProps {
  label: string;       // "Projects" | "Folders"
  current: number;     // 当前数量
  max: number;         // 最大数量 (unlimited = -1)
  compact?: boolean;   // 紧凑模式 (Mobile)
}

export function QuotaItem({ label, current, max, compact }: QuotaItemProps) {
  // Unlimited 情况特殊处理
  if (max === -1) {
    return (
      <div className="flex items-center justify-between">
        <span className="text-slate-600 text-xs">{label}</span>
        <span className="text-slate-700 font-medium text-xs">
          {current} <span className="text-slate-400">/ ∞</span>
        </span>
      </div>
    );
  }

  const percentage = Math.min((current / max) * 100, 100);
  const isNearLimit = percentage >= 80;
  const isAtLimit = current >= max;

  return (
    <div className={cn("space-y-1", compact ? "" : "space-y-1.5")}>
      {/* 标签行 */}
      <div className="flex items-center justify-between">
        <span className={cn("text-slate-600", compact ? "text-[11px]" : "text-xs")}>
          {label}
        </span>
        <span className={cn(
          "font-medium",
          compact ? "text-[11px]" : "text-xs",
          isAtLimit ? "text-red-600" :
          isNearLimit ? "text-amber-600" : "text-slate-700"
        )}>
          {current}/{max}
        </span>
      </div>

      {/* 进度条 */}
      <div className={cn(
        "w-full rounded-full bg-slate-200",
        compact ? "h-1" : "h-1.5"
      )}>
        <div
          className={cn(
            "rounded-full transition-all duration-300",
            compact ? "h-1" : "h-1.5",
            isAtLimit ? "bg-red-500" :
            isNearLimit ? "bg-amber-500" : "bg-indigo-500"
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
```

### 10.3 ProjectLimitWarning 组件

```tsx
// components/dashboard/ProjectLimitWarning.tsx
import { AlertTriangle, Zap } from 'lucide-react';
import Link from 'next/link';

interface ProjectLimitWarningProps {
  currentCount: number;
  maxProjects: number;
}

export function ProjectLimitWarning({ currentCount, maxProjects }: ProjectLimitWarningProps) {
  const percentage = (currentCount / maxProjects) * 100;
  const remaining = maxProjects - currentCount;

  // 低于 80% 不显示
  if (percentage < 80) return null;

  const isAtLimit = remaining <= 0;

  if (isAtLimit) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm">
        <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
        <span className="text-red-700">
          Project limit reached ({currentCount}/{maxProjects}).{' '}
          <Link href="/#pricing" className="font-medium underline hover:text-red-800">
            Upgrade your plan
          </Link>{' '}
          to create more.
        </span>
      </div>
    );
  }

  // 80%-99%
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm">
      <Zap className="w-4 h-4 text-amber-500 shrink-0" />
      <span className="text-amber-700">
        {remaining} project{remaining > 1 ? 's' : ''} remaining ({currentCount}/{maxProjects}).{' '}
        <Link href="/#pricing" className="font-medium underline hover:text-amber-800">
          Upgrade for more
        </Link>
      </span>
    </div>
  );
}
```

### 10.4 配额类型与 Tier 限制映射

| 配额类型 | T1 (Free) | T2 (Starter) | T3 (Pro) | 数据来源 |
|---------|-----------|--------------|----------|---------|
| Projects | 1 | 10 | unlimited (-1) | `system_configs.tier.{tier}.max_projects` |
| Folders | 1 | 20 | 200 | `system_configs.tier.{tier}.max_folders` |
| Workspaces | 1* | 1* | unlimited (-1) | *只能加入，不能创建 |
| Custom Assets | 10 | 0 | 50 → unlimited | T2 为 0 是特殊设计 |

### 10.5 配额恢复交互

| 操作 | 预期行为 | 实现方式 |
|------|---------|---------|
| 删除项目 | 配额立即 -1，进度条更新 | `useUserStore.decrementProjectCount()` |
| 移动到回收站 | 配额 **不变**（仍占用） | 项目仍计入 count |
| 从回收站恢复 | 配额 **不变** | 项目已计入 count |
| 永久删除 | 配额 -1 | 需后端同步 |

**重要**: 移动到回收站 ≠ 释放配额。只有永久删除才释放。

### 10.6 Unlimited 状态展示

T3 用户的 Projects 为 unlimited，显示方式：

```
┌──────────────────────────────┐
│  Projects            5 / ∞   │  ← 数字 + 无限符号
│  (无进度条)                    │  ← 不显示进度条
└──────────────────────────────┘
```

---

## 十一、修订历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-02-03 | 初始版本 |
| v1.1 | 2026-02-03 | 补充遗漏：useQuotaGuard 实现、QuotaBar 组件、ProjectLimitWarning、配额映射表 |

---

**END OF DOCUMENT**
