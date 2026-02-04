# 用户权限 UI 交互规范

> **版本**: v1.4
> **日期**: 2026-02-04
> **状态**: 设计完成
> **适用范围**: 功能权限、配额限制的前端 UI 交互

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [03-system-design.md](./03-system-design.md) | 系统架构总览 |
| [01-permission-matrix.md](./01-permission-matrix.md) | 功能权限矩阵 (**唯一数据源**) |
| [04-feature-flag-engine.md](./04-feature-flag-engine.md) | Feature Flag 评估引擎 |

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
| **平台素材** | `AssetPanel` | - | 能进入编辑页面即可用 |
| **矢量图工具** | `DrawingCanvas` | - | 能进入编辑页面即可用 |
| **画笔工具** | `DrawingCanvas` | - | 能进入编辑页面即可用 |
| **剪贴板粘贴** | Canvas 右键菜单 + 快捷键 | 菜单项可见但禁用 + 🔒 | 快捷键不生效；菜单 Tooltip → UpgradeModal |
| **AI 生成素材** | `CustomAssets` | 按钮 + 🔒 | Trial 时显示 Badge; 锁定时弹 UpgradeModal |
| **AI 生成 Page** | `AIPageGenerator` | 按钮 + 🔒 | Trial 时显示 Badge; 锁定时弹 UpgradeModal |
| **Smart Scan (OCR)** | `CustomAssets` | 按钮 + 🔒 | Tooltip: "Smart Scan requires Pro" → UpgradeModal |
| **Upload Custom Asset** | `CustomAssets` | 上传按钮 + 🔒 | Tooltip: "Custom uploads require Pro" → UpgradeModal |
| **PDF 打印** | `TopBarExport` | 游客: 🔒; 登录用户: 可用 | 游客需登录; t1 超出试用期后仍可用 |
| **PDF 下载** | `TopBarExport` | 游客: 🔒; 登录用户: 可用 | 游客需登录; t1 超出试用期后仍可用 |
| **ZIP Export** | `TopBarExport` | 菜单项 + 🔒 | Tooltip: "ZIP export requires Pro" → UpgradeModal |

> **剪贴板粘贴控制细节**: Canvas 右键菜单中显示"复制/粘贴"选项，当权限不足时：
> - 菜单项可见但 `disabled` + 🔒 图标
> - Ctrl+V / Cmd+V 快捷键不生效
> - 点击菜单项弹出 UpgradeModal

> **第 7-9 行说明**: 平台素材、矢量图、画笔当前配置为所有用户可用，能进入编辑页面即可使用。

### 4.3 Export 菜单

```tsx
<DropdownMenuContent>
  {/* PDF 打印 - 游客 NO，t1 trial YES，t1 过期后 YES，t2/t3 YES */}
  <DropdownMenuItem
    onClick={() => printAccess.checkAndTrigger(handlePrint)}
    className={cn(printAccess.isLocked && "opacity-70")}
  >
    <Printer className="w-4 h-4 mr-2" />
    Print PDF
    {printAccess.isLocked && <Lock className="w-3.5 h-3.5 text-amber-500 ml-auto" />}
  </DropdownMenuItem>

  {/* PDF 下载 - 游客 NO，t1 trial YES，t1 过期后 YES，t2/t3 YES */}
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
| Custom Assets | 10 (试用期) / 0 (过期后) | 50/Account | unlimited (-1) | t1 试用期内可上传 10 个 |

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

## 十一、试用期过期 UI 组件

> 本章节定义 t1 用户试用期过期后的 UI 交互规范。

### 11.1 试用期状态提醒

#### 11.1.1 TrialStatusBanner 组件

**展示时机 (基于百分比)**:

> 使用百分比而非固定天数，以便 `trial.default_days` 配置变更时自动适配。

| 剩余比例 | Banner 样式 | 可关闭 | 展示位置 | 示例 (7天试用期) |
|:-------:|------------|:-----:|---------|:---------------:|
| > 50% | `info` (蓝色) | ✅ | 页面顶部，Dashboard/Editor | 7-4 天 |
| 15% ~ 50% | `warning` (橙色) | ❌ | 页面顶部，Dashboard/Editor | 3-1 天 |
| 0% ~ 15% | `urgent` (红色) | ❌ | 页面顶部 + Modal 弹窗 | 当天 |
| 已过期 | `expired` (灰色) | ❌ | 持续显示 | - |

**配置 Key**:

```sql
-- system_configs 配置项 (可在 Admin 调整)
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('trial.default_days', '7', 'integer', 'trial', '默认试用天数'),
('trial.warning_threshold', '0.5', 'float', 'trial', 'warning 样式阈值 (剩余比例)'),
('trial.urgent_threshold', '0.15', 'float', 'trial', 'urgent 样式阈值 (剩余比例)'),
('trial.show_modal_on_last_day', 'true', 'boolean', 'trial', '最后一天是否弹窗');
```

**组件实现**:

```tsx
// components/trial/TrialStatusBanner.tsx

interface TrialStatusBannerProps {
  daysRemaining: number;
  totalTrialDays: number;  // 从配置获取
  warningThreshold?: number;  // 默认 0.5 (50%)
  urgentThreshold?: number;   // 默认 0.15 (15%)
  onUpgrade: () => void;
  onDismiss?: () => void;
}

export function TrialStatusBanner({
  daysRemaining,
  totalTrialDays,
  warningThreshold = 0.5,
  urgentThreshold = 0.15,
  onUpgrade,
  onDismiss
}: TrialStatusBannerProps) {
  const remainingRatio = daysRemaining / totalTrialDays;

  const variant = useMemo(() => {
    if (daysRemaining <= 0) return 'expired';
    if (remainingRatio <= urgentThreshold) return 'urgent';
    if (remainingRatio <= warningThreshold) return 'warning';
    return 'info';
  }, [daysRemaining, remainingRatio, warningThreshold, urgentThreshold]);

  const canDismiss = remainingRatio > warningThreshold;

  const variantStyles = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
    urgent: 'bg-red-50 border-red-200 text-red-800',
    expired: 'bg-slate-100 border-slate-300 text-slate-700',
  };

  const messages = {
    info: `🎉 试用期还剩 ${daysRemaining} 天，探索所有 Pro 功能`,
    warning: `⚠️ 试用期还剩 ${daysRemaining} 天，升级后继续使用`,
    urgent: `🔔 试用期今天结束！立即升级保留所有功能`,
    expired: `⏰ 试用期已结束，项目已变为只读模式`,
  };

  const ctaText = {
    info: '查看套餐',
    warning: '立即升级',
    urgent: '立即升级',
    expired: '升级解锁',
  };

  return (
    <div className={cn(
      'flex items-center justify-between px-4 py-2.5 border-b',
      variantStyles[variant]
    )}>
      <span className="text-sm font-medium">{messages[variant]}</span>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant={variant === 'urgent' || variant === 'expired' ? 'default' : 'outline'}
          onClick={onUpgrade}
        >
          {ctaText[variant]}
        </Button>
        {canDismiss && onDismiss && (
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
```

**Banner 视觉示例**:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🎉 试用期还剩 5 天，探索所有 Pro 功能          [查看套餐] [✕]        │  ← info (可关闭)
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ ⚠️ 试用期还剩 2 天，升级后继续使用              [立即升级]           │  ← warning (不可关闭)
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 🔔 试用期今天结束！立即升级保留所有功能          [立即升级]           │  ← urgent (不可关闭)
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ ⏰ 试用期已结束，项目已变为只读模式              [升级解锁]           │  ← expired (不可关闭)
└─────────────────────────────────────────────────────────────────────┘
```

#### 11.1.2 TrialExpiredModal 组件

**触发时机**: 试用期结束当天首次登录 / 首次进入 Dashboard

```tsx
// components/trial/TrialExpiredModal.tsx

interface TrialExpiredModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade: () => void;
}

export function TrialExpiredModal({ isOpen, onClose, onUpgrade }: TrialExpiredModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-amber-500" />
            <DialogTitle>试用期已结束</DialogTitle>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <p className="text-slate-600">
            您的 {trialDays} 天免费试用已结束。感谢您的体验！
          </p>

          <div className="bg-slate-50 rounded-lg p-4 space-y-2">
            <p className="font-medium text-slate-900">升级后可以：</p>
            <ul className="text-sm text-slate-600 space-y-1.5">
              <li className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-500" />
                继续编辑您的项目
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-500" />
                创建更多项目和文件夹
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-500" />
                使用 AI 生成功能
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-500" />
                导出 ZIP 文件
              </li>
            </ul>
          </div>

          <p className="text-sm text-slate-500">
            您的项目数据已安全保存，升级后可立即恢复编辑。
          </p>
        </div>

        <DialogFooter className="flex gap-2">
          <Button variant="ghost" onClick={onClose}>
            以后再说
          </Button>
          <Button onClick={onUpgrade}>
            查看套餐
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Modal 视觉示例**:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⏰ 试用期已结束                                          [✕]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  您的 {trialDays} 天免费试用已结束。感谢您的体验！                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 升级后可以：                                              │   │
│  │ ✓ 继续编辑您的项目                                        │   │
│  │ ✓ 创建更多项目和文件夹                                    │   │
│  │ ✓ 使用 AI 生成功能                                        │   │
│  │ ✓ 导出 ZIP 文件                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  您的项目数据已安全保存，升级后可立即恢复编辑。                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [以后再说]  [查看套餐]              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 十二、编辑器只读模式 UI

> t1 用户试用期过期后，已有项目进入只读模式。

### 12.1 只读模式检测

```tsx
// hooks/useEditorReadOnly.ts

export function useEditorReadOnly(projectId: string) {
  const { tier, isWithinTrialPeriod } = useEntitlement();
  const [isReadOnly, setIsReadOnly] = useState(false);
  const [readOnlyReason, setReadOnlyReason] = useState<string | null>(null);

  useEffect(() => {
    // t1 试用期过期 → 只读
    if (tier === 't1' && !isWithinTrialPeriod) {
      setIsReadOnly(true);
      setReadOnlyReason('trial_expired');
      return;
    }

    // 检查项目是否因降级被锁定
    checkProjectLockStatus(projectId).then((lockStatus) => {
      if (lockStatus?.is_read_only) {
        setIsReadOnly(true);
        setReadOnlyReason(lockStatus.read_only_reason);
      }
    });
  }, [tier, isWithinTrialPeriod, projectId]);

  return { isReadOnly, readOnlyReason };
}
```

### 12.2 EditorReadOnlyOverlay 组件

**只读时编辑器的 UI 表现**:

| 元素 | 正常模式 | 只读模式 |
|------|---------|---------|
| Canvas | 可交互 | 禁用所有交互，显示半透明遮罩 |
| 工具栏 | 可用 | 全部禁用 + `opacity-50` |
| 右侧属性面板 | 可用 | 全部禁用 + `opacity-50` |
| 顶部 Banner | 无 | 显示只读提示 Banner |
| 保存按钮 | 可用 | 隐藏 |
| 导出 PDF | 可用 | 可用 (保留) |
| 导出 ZIP | 可用 | 禁用 + 🔒 |

```tsx
// components/editor/EditorReadOnlyOverlay.tsx

interface EditorReadOnlyOverlayProps {
  reason: 'trial_expired' | 'tier_downgrade' | 'grace_period';
  onUpgrade: () => void;
}

export function EditorReadOnlyOverlay({ reason, onUpgrade }: EditorReadOnlyOverlayProps) {
  const messages = {
    trial_expired: {
      title: '试用期已结束',
      description: '项目为只读模式，升级后可继续编辑',
      cta: '升级解锁编辑',
    },
    tier_downgrade: {
      title: '订阅已降级',
      description: '此项目超出当前套餐配额，升级后可恢复编辑',
      cta: '升级恢复编辑',
    },
    grace_period: {
      title: '即将锁定',
      description: '宽限期结束后此项目将变为只读',
      cta: '续订保留',
    },
  };

  const { title, description, cta } = messages[reason];

  return (
    <>
      {/* 顶部 Banner */}
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lock className="w-4 h-4 text-amber-600" />
          <span className="text-sm font-medium text-amber-800">{title}</span>
          <span className="text-sm text-amber-600">· {description}</span>
        </div>
        <Button size="sm" onClick={onUpgrade}>
          {cta}
        </Button>
      </div>

      {/* Canvas 遮罩 (仅视觉提示，实际禁用由 Editor 组件处理) */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-slate-900/80 text-white px-4 py-2 rounded-lg flex items-center gap-2">
          <Eye className="w-4 h-4" />
          <span className="text-sm">只读模式 · 可查看和导出 PDF</span>
        </div>
      </div>
    </>
  );
}
```

**编辑器只读模式视觉示例**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔒 试用期已结束 · 项目为只读模式，升级后可继续编辑        [升级解锁编辑]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │  [工具栏 - 全部禁用 opacity-50]                                        │   │
│ ├───────────────────────────────────────────────────────────────────────┤   │
│ │                                                                       │   │
│ │                                                                       │   │
│ │                         Canvas 内容                                   │   │
│ │                       (可查看，不可编辑)                               │   │
│ │                                                                       │   │
│ │                                                                       │   │
│ │         ┌───────────────────────────────────────┐                     │   │
│ │         │  👁 只读模式 · 可查看和导出 PDF        │                     │   │
│ │         └───────────────────────────────────────┘                     │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.3 只读模式下的操作限制

| 操作 | 是否允许 | UI 表现 |
|------|:-------:|---------|
| 查看 Canvas | ✅ | 正常显示 |
| 缩放/平移 | ✅ | 正常交互 |
| 选择元素 | ❌ | 点击无反应 |
| 移动/调整元素 | ❌ | 禁用 |
| 添加/删除元素 | ❌ | 工具栏禁用 |
| 修改属性 | ❌ | 属性面板禁用 |
| 撤销/重做 | ❌ | 快捷键不响应 |
| 复制/粘贴 | ❌ | 快捷键不响应 |
| 导出 PDF | ✅ | 正常可用 |
| 导出 ZIP | ❌ | 按钮禁用 + 🔒 |
| 打印 | ✅ | 正常可用 |

---

## 十三、Tier 降级资源锁定 UI

> 用户降级后，超出配额的资源显示锁定状态。

### 13.1 Dashboard 资源卡片锁定状态

#### 13.1.1 LockedProjectCard 组件

```tsx
// components/dashboard/LockedProjectCard.tsx

interface LockedProjectCardProps {
  project: Project;
  lockReason: 'tier_downgrade' | 'grace_period';
  gracePeriodEnd?: Date;
  onUpgrade: () => void;
}

export function LockedProjectCard({
  project,
  lockReason,
  gracePeriodEnd,
  onUpgrade
}: LockedProjectCardProps) {
  const isGracePeriod = lockReason === 'grace_period';

  return (
    <Card className={cn(
      'relative overflow-hidden',
      isGracePeriod ? 'border-amber-300' : 'border-slate-300 opacity-75'
    )}>
      {/* 锁定标识 */}
      <div className={cn(
        'absolute top-2 right-2 px-2 py-1 rounded text-xs font-medium flex items-center gap-1',
        isGracePeriod
          ? 'bg-amber-100 text-amber-700'
          : 'bg-slate-100 text-slate-600'
      )}>
        <Lock className="w-3 h-3" />
        {isGracePeriod ? '即将锁定' : '只读'}
      </div>

      {/* 项目缩略图 */}
      <div className="aspect-video bg-slate-100 relative">
        <img src={project.thumbnail} alt={project.name} className="w-full h-full object-cover" />
        {!isGracePeriod && (
          <div className="absolute inset-0 bg-slate-900/20 flex items-center justify-center">
            <Lock className="w-8 h-8 text-white/80" />
          </div>
        )}
      </div>

      {/* 项目信息 */}
      <CardContent className="p-3">
        <h3 className="font-medium truncate">{project.name}</h3>
        <p className="text-xs text-slate-500 mt-1">
          {isGracePeriod
            ? `将于 ${formatDate(gracePeriodEnd)} 锁定`
            : '升级后可恢复编辑'}
        </p>
      </CardContent>

      {/* 操作按钮 */}
      <CardFooter className="p-3 pt-0 flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1"
          onClick={() => window.open(`/create/${project.id}?readonly=true`)}
        >
          <Eye className="w-4 h-4 mr-1" />
          查看
        </Button>
        <Button
          size="sm"
          className="flex-1"
          onClick={onUpgrade}
        >
          <Unlock className="w-4 h-4 mr-1" />
          解锁
        </Button>
      </CardFooter>
    </Card>
  );
}
```

**锁定项目卡片视觉示例**:

```
正常项目卡片:                          锁定项目卡片 (降级):
┌─────────────────────┐              ┌─────────────────────┐
│ ┌─────────────────┐ │              │ ┌─────────────────┐ │ [🔒 只读]
│ │                 │ │              │ │    🔒            │ │
│ │    缩略图       │ │              │ │   (半透明遮罩)   │ │
│ │                 │ │              │ │                 │ │
│ └─────────────────┘ │              │ └─────────────────┘ │
│ 项目名称            │              │ 项目名称            │
│ 上次编辑: 2小时前    │              │ 升级后可恢复编辑     │
│                     │              │ [查看] [解锁]        │
└─────────────────────┘              └─────────────────────┘

宽限期项目卡片:
┌─────────────────────┐
│ ┌─────────────────┐ │ [⚠️ 即将锁定]
│ │                 │ │
│ │    缩略图       │ │
│ │   (无遮罩)      │ │
│ └─────────────────┘ │
│ 项目名称            │
│ 将于 2月11日 锁定    │
│ [编辑] [续订保留]    │
└─────────────────────┘
```

### 13.2 GracePeriodBanner 组件

**宽限期内 Dashboard 顶部显示**:

```tsx
// components/dashboard/GracePeriodBanner.tsx

interface GracePeriodBannerProps {
  daysRemaining: number;
  exceededResources: {
    workspaces: number;
    projects: number;
    folders: number;
  };
  onUpgrade: () => void;
}

export function GracePeriodBanner({
  daysRemaining,
  exceededResources,
  onUpgrade
}: GracePeriodBannerProps) {
  const totalExceeded =
    exceededResources.workspaces +
    exceededResources.projects +
    exceededResources.folders;

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-3">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
          <div>
            <p className="font-medium text-amber-800">
              订阅已降级 · 宽限期还剩 {daysRemaining} 天
            </p>
            <p className="text-sm text-amber-600 mt-1">
              {totalExceeded} 个资源将在宽限期结束后变为只读：
              {exceededResources.projects > 0 && ` ${exceededResources.projects} 个项目`}
              {exceededResources.folders > 0 && ` ${exceededResources.folders} 个文件夹`}
              {exceededResources.workspaces > 0 && ` ${exceededResources.workspaces} 个 Workspace`}
            </p>
          </div>
        </div>
        <Button onClick={onUpgrade}>
          续订保留
        </Button>
      </div>
    </div>
  );
}
```

**宽限期 Banner 视觉示例**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⚠️ 订阅已降级 · 宽限期还剩 5 天                                [续订保留]   │
│    8 个资源将在宽限期结束后变为只读：5 个项目 3 个文件夹                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.3 资源操作限制

| 资源状态 | 查看 | 编辑 | 删除 | 导出 |
|---------|:----:|:----:|:----:|:----:|
| 正常 | ✅ | ✅ | ✅ | ✅ |
| 宽限期内 | ✅ | ✅ | ✅ | ✅ |
| 已锁定 (降级) | ✅ | ❌ | ✅ | PDF ✅ / ZIP ❌ |
| 已锁定 (试用期过期) | ✅ | ❌ | ✅ | PDF ✅ / ZIP ❌ |

---

## 十四、修订历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-02-03 | 初始版本 |
| v1.1 | 2026-02-03 | 补充遗漏：useQuotaGuard 实现、QuotaBar 组件、ProjectLimitWarning、配额映射表 |
| v1.2 | 2026-02-04 | 基于 CSV 表格校准：Editor 页面功能控制方式、第 7-9 行说明 |
| v1.3 | 2026-02-04 | 全面审计修复：PDF 打印/下载注释错误修正；t2 maxCustomAssets 改为 50/Account |
| v1.4 | 2026-02-04 | **边界场景 UI 规范**：(1) 试用期状态提醒 (TrialStatusBanner + TrialExpiredModal)；(2) 编辑器只读模式 (EditorReadOnlyOverlay + 操作限制表)；(3) Tier 降级资源锁定 (LockedProjectCard + GracePeriodBanner) |

---

**END OF DOCUMENT**
