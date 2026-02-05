# 移动端 Profile 页面设计方案

**状态**: needs-review  
**版本**: 1.1.0  
**版本日期**: 2026-01-22  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 个人中心需要移动端优先的统一体验
- 目标与非目标: 目标是明确移动端信息结构与交互；非目标是覆盖桌面端改造

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 移动端 Profile 的信息架构与交互方案
- 与现有移动端规范的对齐策略

## 影响范围

- 相关模块: Profile 页面与移动端体验
- 相关文档: `docs/v2/02-standards/responsive-design-guide.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/`、`decodables-fe/@business/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.1.0 | 结构对齐与信息补齐 | Docs Working Group |

## ⚠️ 与现有移动端规范对比

在设计此方案前，已详细审查现有移动端组件规范。以下是关键对比：

| 设计元素 | 现有规范 | 本方案 | 状态 |
|---------|---------|-------|------|
| **页面背景** | `bg-slate-50` (Dashboard/Marketplace) | `bg-slate-50` | ✅ 一致 |
| **卡片圆角** | `rounded-xl` (14px) - 移动端常用 | ~~`rounded-2xl`~~ → `rounded-xl` | ⚠️ 已调整 |
| **卡片边框** | `border border-slate-200` | `border border-slate-200` | ✅ 一致 |
| **页面内边距** | `px-4 sm:px-6` | `px-4` (移动端只用 `px-4`) | ✅ 一致 |
| **底部间距** | `pb-24 md:pb-8` (为 BottomNavbar 预留) | `pb-24` | ✅ 一致 |
| **顶部导航** | Dashboard/Marketplace 使用全局 Navbar | 全局 Navbar（与其他页面一致） | ✅ 已确认 |
| **Tier 颜色** | Free=emerald, Starter=blue, Pro=violet | 一致 | ✅ 一致 |
| **主 CTA 按钮** | `bg-indigo-600 hover:bg-indigo-700 rounded-xl h-11` | 一致 | ✅ 一致 |
| **触控反馈** | `active:scale-95`, `active:bg-slate-100`, haptic | 需添加 | ⚠️ 已补充 |
| **Footer** | 移动端隐藏 `hidden md:block` | 不显示 | ✅ 一致 |

### 已确认的设计决策

1. **顶部导航**：使用全局 Navbar（与 Landing、Dashboard、Marketplace 一致）✅

2. **卡片圆角**：使用 `rounded-xl` 以保持一致性 ✅

3. **头像 Tier 颜色环**：不使用（与 PC 端保持一致）✅

4. **Copy User ID**：直接显示 User ID + 复制按钮 ✅

5. **额外设置入口**：添加通知、语言/主题设置 ✅

---

## 目录

1. [设计目标与原则](#1-设计目标与原则)
2. [信息架构](#2-信息架构)
3. [视觉设计方案](#3-视觉设计方案)
4. [交互规范](#4-交互规范)
5. [技术实现方案](#5-技术实现方案)
6. [业界参考](#6-业界参考)
7. [待确认事项](#7-待确认事项)

---

## 1. 设计目标与原则

### 1.1 设计目标

1. **信息完整性**：移动端用户能够访问与 PC 端相同的 Profile 功能
2. **操作便捷性**：单手操作友好，重要操作触手可及
3. **视觉一致性**：与现有移动端 UI（Dashboard、Marketplace）保持统一风格
4. **性能优先**：轻量加载，关键信息优先展示

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **移动优先** | 专为触屏设计，最小触控区域 44x44px |
| **渐进披露** | 核心信息直接展示，次要信息折叠或跳转 |
| **视觉层次** | 重要信息（Plan、Credits）视觉突出 |
| **反馈及时** | 所有操作有明确的视觉/触觉反馈 |

---

## 2. 信息架构

### 2.1 页面结构

```
┌─────────────────────────────────────────┐
│            Mobile Profile Page           │
├─────────────────────────────────────────┤
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     👤 User Header Section        │   │ ← 固定高度 Header
│  │     Avatar + Name + Email         │   │
│  │     Tier Badge                    │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     💎 Credits Card (Hero)        │   │ ← 主要焦点区域
│  │     Total | Monthly | Permanent   │   │
│  │     [Buy Credits] Button          │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     📋 Subscription Card          │   │ ← 订阅管理
│  │     Current Plan + Price          │   │
│  │     [Manage] / [Upgrade]          │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     🆔 User ID Card               │   │ ← User ID 展示 + 复制
│  │     ID: abc123...  [📋 Copy]      │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     📜 Quick Actions              │   │ ← 快捷操作列表
│  │     - Transaction History →       │   │
│  │     - Account Settings →          │   │
│  │     - Security →                  │   │
│  │     - Notifications →             │   │ ← 新增
│  │     - Language & Theme →          │   │ ← 新增
│  │     - Help & Support →            │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     🚪 Sign Out Button            │   │ ← 底部登出
│  └──────────────────────────────────┘   │
│                                          │
│            App Version v1.0.0            │ ← Footer 信息
│                                          │
├─────────────────────────────────────────┤
│     [🏠] [📊] [➕] [🛒] [👤]            │ ← BottomNavbar (Profile 高亮)
└─────────────────────────────────────────┘
```

### 2.2 功能模块映射

| PC 端功能 | 移动端对应 | 展示方式 |
|----------|-----------|---------|
| Clerk UserButton 头像 | User Header Section | 直接展示 |
| Clerk Account 页面 | Account Settings → 跳转 Clerk 页面 | 外链跳转 |
| Clerk Security 页面 | Security → 跳转 Clerk 页面 | 外链跳转 |
| ClerkBillingPage (Billing) | Credits Card + Subscription Card | 内联卡片 |
| ClerkTransactionHistory | Transaction History → 单独页面/底部弹窗 | 页面跳转或 BottomSheet |

---

## 3. 视觉设计方案

### 3.1 整体布局

```
┌────────────────────────────────────┐
│  [☰] [Logo]  ...  [💎] [🔔]        │  ← 全局 Navbar (与 Dashboard 一致)
├────────────────────────────────────┤
│                                     │
│         ┌─────────┐                │
│         │ 🖼️      │                │
│         │ Avatar  │  w-20 h-20     │
│         │  80px   │  rounded-full  │
│         └─────────┘                │  ← 无 Tier 颜色环 (与 PC 一致)
│                                     │
│       Zhang Yi                      │  ← text-xl font-bold
│    zhang@example.com               │  ← text-sm text-slate-500
│                                     │
│    ┌───────────────┐               │
│    │ 👑 Pro Member │               │  ← Tier Badge (violet)
│    └───────────────┘               │
│                                     │
├────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Credits Balance              │  │  ← Credits Card
│  │                              │  │
│  │     💎 1,250                 │  │  ← Total (大字)
│  │                              │  │
│  │  ┌────────┐  ┌────────┐     │  │
│  │  │ ✨ 200 │  │ ♾️ 1050│     │  │  ← Monthly | Permanent
│  │  │Monthly │  │Permanent│     │  │
│  │  └────────┘  └────────┘     │  │
│  │                              │  │
│  │  [💳 Buy 100 Credits - $4.9] │  │  ← CTA Button
│  │  Pro: 20% OFF               │  │  ← Discount Badge
│  │                              │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Current Plan                 │  │  ← Subscription Card
│  │                              │  │
│  │  👑 Pro Plan     $9.9/mo    │  │
│  │                              │  │
│  │  ✓ 200 credits/month        │  │
│  │  ✓ Commercial license       │  │
│  │  ✓ Priority support         │  │
│  │                              │  │
│  │  [Manage Subscription]      │  │  ← 跳转 Stripe Portal
│  │                              │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ User ID                     │  │  ← User ID Card
│  │ user_2abc...xyz  [📋 Copy]  │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ 📜 Transaction History    → │  │  ← 快捷入口
│  ├──────────────────────────────┤  │
│  │ 👤 Account Settings       → │  │
│  ├──────────────────────────────┤  │
│  │ 🔒 Security               → │  │
│  ├──────────────────────────────┤  │
│  │ 🔔 Notifications          → │  │  ← 新增
│  ├──────────────────────────────┤  │
│  │ 🌐 Language & Theme       → │  │  ← 新增
│  ├──────────────────────────────┤  │
│  │ ❓ Help & Support         → │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │      🚪 Sign Out             │  │  ← Destructive style
│  └──────────────────────────────┘  │
│                                     │
│         v1.0.0 • Made with ❤️       │  ← App version
│                                     │
└────────────────────────────────────┘
```

### 3.2 配色方案

遵循现有设计系统（与 Dashboard、Marketplace 保持一致）：

| 元素 | 颜色 | Tailwind 类 |
|------|------|-------------|
| **背景** | 浅灰 | `bg-slate-50` |
| **卡片背景** | 白色 | `bg-white` |
| **卡片边框** | 浅灰 | `border border-slate-200` |
| **卡片圆角** | 14px | `rounded-xl` (与 PlanCard, ListingCard 一致) |
| **卡片阴影** | 柔和 | `shadow-sm hover:shadow-md` |
| **主文本** | 深灰 | `text-slate-900` |
| **次要文本** | 中灰 | `text-slate-500` |
| **Tier Free** | 翠绿 | `bg-emerald-100 text-emerald-700` |
| **Tier Starter** | 蓝色 | `bg-blue-100 text-blue-700` (badge) / `bg-blue-500 text-white` (button) |
| **Tier Pro** | 紫罗兰 | `bg-violet-100 text-violet-700` (badge) / `bg-violet-600 text-white` (button) |
| **Credits** | 琥珀色 | `text-amber-500` (图标) / `bg-amber-50` (背景) |
| **CTA 按钮** | 靛蓝 | `bg-indigo-600 hover:bg-indigo-700 h-11 rounded-xl` |
| **危险按钮** | 红色 | `text-red-600 border-red-200 hover:bg-red-50` |

### 3.3 组件样式详解

#### User Header Section

```jsx
// 设计规格 - 与 PC 端保持一致（无 Tier 颜色环）
<div className="flex flex-col items-center py-6 bg-white">
  {/* Avatar - 无颜色环，与 PC 端一致 */}
  <div className="relative w-20 h-20 rounded-full overflow-hidden bg-slate-100">
    <img src={avatarUrl} className="w-full h-full rounded-full object-cover" />
  </div>
  
  {/* Name */}
  <h1 className="mt-4 text-xl font-bold text-slate-900">{displayName}</h1>
  
  {/* Email */}
  <p className="text-sm text-slate-500">{email}</p>
  
  {/* Tier Badge */}
  <div className={cn(
    "mt-3 px-4 py-1.5 rounded-full text-sm font-semibold",
    "flex items-center gap-2",
    tier === 'pro' && "bg-violet-100 text-violet-700",
    tier === 'starter' && "bg-blue-100 text-blue-700",
    tier === 'free' && "bg-emerald-100 text-emerald-700",
  )}>
    <TierIcon className="w-4 h-4" />
    <span>{tierLabel} Member</span>
  </div>
</div>
```

#### User ID Card (新增)

```jsx
// 设计规格 - 直接显示 User ID + 复制按钮
<div className="mx-4 mt-3 rounded-xl bg-white shadow-sm border border-slate-200 p-4">
  <div className="flex items-center justify-between">
    <div className="flex-1 min-w-0">
      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
        User ID
      </span>
      <p className="mt-1 text-sm font-mono text-slate-700 truncate">
        {userId}
      </p>
    </div>
    
    {/* Copy Button */}
    <Button
      variant="outline"
      size="sm"
      className={cn(
        "h-9 px-3 rounded-lg shrink-0 ml-3",
        "active:scale-95 transition-all",
        copied && "bg-emerald-50 border-emerald-200 text-emerald-600"
      )}
      onClick={() => {
        navigator.clipboard.writeText(userId);
        setCopied(true);
        haptic.success();
        message.success("User ID copied!");
        setTimeout(() => setCopied(false), 2000);
      }}
    >
      {copied ? (
        <>
          <Check className="w-4 h-4 mr-1.5" />
          Copied
        </>
      ) : (
        <>
          <Copy className="w-4 h-4 mr-1.5" />
          Copy
        </>
      )}
    </Button>
  </div>
</div>
```

#### Credits Card (Hero)

```jsx
// 设计规格 - 与 ClerkBillingPage 保持一致
<div className="mx-4 rounded-xl bg-white shadow-sm border border-slate-200 p-4">
  {/* Header */}
  <div className="flex items-center justify-between mb-3">
    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
      Credits Balance
    </span>
    {/* Total Credits - Hero 展示 */}
    <div className="flex items-center gap-1.5">
      <Gem className="w-5 h-5 text-amber-500" />
      <span className="text-2xl font-bold text-slate-900">
        {totalCredits.toLocaleString()}
      </span>
    </div>
  </div>
  
  {/* Monthly / Permanent 分解 */}
  <div className="grid grid-cols-2 gap-3 mb-4">
    <div className={cn(
      "p-3 rounded-lg text-center",
      tier === 'pro' && "bg-violet-50",
      tier === 'starter' && "bg-blue-50",
      tier === 'free' && "bg-slate-100",
    )}>
      <div className="flex items-center justify-center gap-1.5 mb-1">
        <Sparkles className={cn(
          "w-4 h-4",
          tier === 'pro' && "text-violet-600",
          tier === 'starter' && "text-blue-600",
          tier === 'free' && "text-slate-500",
        )} />
        <span className="text-xs text-slate-500">Monthly</span>
      </div>
      <p className="text-xl font-bold text-slate-900">{creditsMonthly}</p>
    </div>
    
    <div className="p-3 rounded-lg text-center bg-amber-50">
      <div className="flex items-center justify-center gap-1.5 mb-1">
        <Infinity className="w-4 h-4 text-amber-600" />
        <span className="text-xs text-slate-500">Permanent</span>
      </div>
      <p className="text-xl font-bold text-slate-900">{creditsPermanent}</p>
    </div>
  </div>
  
  {/* Buy Credits CTA - 与 ClerkBillingPage 按钮样式一致 */}
  <Button 
    className={cn(
      "w-full h-11 rounded-xl font-semibold",
      "bg-amber-500 hover:bg-amber-600 text-white",
      "active:scale-[0.98] transition-all duration-150"
    )}
    onClick={handleBuyCredits}
  >
    <ShoppingCart className="w-4 h-4 mr-2" />
    Buy 100 Credits - $4.9
    {isPro && (
      <span className="ml-2 px-2 py-0.5 text-[10px] bg-white/20 rounded-full">
        20% OFF
      </span>
    )}
  </Button>
</div>
```

#### Subscription Card

```jsx
// 设计规格 - 与 PlanCard 组件风格一致
<div className="mx-4 mt-3 rounded-xl bg-white shadow-sm border border-slate-200 p-4">
  {/* Header */}
  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
    Current Plan
  </span>
  
  {/* Plan Info */}
  <div className="flex items-center justify-between mt-3">
    <div className="flex items-center gap-3">
      <div className={cn(
        "w-10 h-10 rounded-xl flex items-center justify-center",
        tier === 'pro' && "bg-violet-100",
        tier === 'starter' && "bg-blue-100",
        tier === 'free' && "bg-emerald-100",
      )}>
        <TierIcon className={cn(
          "w-5 h-5",
          tier === 'pro' && "text-violet-600",
          tier === 'starter' && "text-blue-600",
          tier === 'free' && "text-emerald-600",
        )} />
      </div>
      <div>
        <p className="font-bold text-slate-900">{tierName} Plan</p>
        <p className="text-sm text-slate-500">
          {hasPaidPlan ? `$${price}/month` : 'Free forever'}
        </p>
      </div>
    </div>
    
    {/* Trial Badge (if applicable) */}
    {isFree && trialDaysRemaining > 0 && (
      <div className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
        {trialDaysRemaining} days left
      </div>
    )}
  </div>
  
  {/* Plan Features (简化) - 与 ClerkBillingPage 一致 */}
  <div className="space-y-1.5 text-sm text-slate-600 mt-3">
    <div className="flex items-center gap-2">
      <Check className="w-4 h-4 text-emerald-500 shrink-0" />
      <span>{monthlyCredits} credits/month</span>
    </div>
    {isPro && (
      <>
        <div className="flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-500 shrink-0" />
          <span>Commercial license</span>
        </div>
        <div className="flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-500 shrink-0" />
          <span>20% off credit purchases</span>
        </div>
      </>
    )}
  </div>
  
  {/* Action Button */}
  {hasPaidPlan ? (
    <Button 
      variant="outline"
      className="w-full h-10 rounded-xl mt-4 active:scale-[0.98] transition-all"
      onClick={handleManageSubscription}
    >
      <Settings className="w-4 h-4 mr-2" />
      Manage Subscription
    </Button>
  ) : (
    <Button 
      className={cn(
        "w-full h-10 rounded-xl mt-4 font-semibold",
        "bg-linear-to-r from-indigo-600 to-violet-600 text-white",
        "hover:from-indigo-700 hover:to-violet-700",
        "active:scale-[0.98] transition-all"
      )}
      onClick={handleUpgrade}
    >
      <Sparkles className="w-4 h-4 mr-2" />
      Upgrade to Pro
    </Button>
  )}
</div>
```

#### Quick Actions List

```jsx
// 设计规格 - 与 MobileMenu 中的导航列表风格一致
<div className="mx-4 mt-3 rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
  {QUICK_ACTIONS.map((action, index) => (
    <button
      key={action.id}
      onClick={() => {
        haptic.light(); // 触觉反馈
        action.onClick();
      }}
      className={cn(
        "w-full flex items-center justify-between px-4 py-3.5",
        "active:bg-slate-100 transition-colors",
        index !== QUICK_ACTIONS.length - 1 && "border-b border-slate-100"
      )}
    >
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center">
          <action.icon className="w-5 h-5 text-slate-600" />
        </div>
        <span className="font-medium text-slate-900">{action.label}</span>
      </div>
      <ChevronRight className="w-5 h-5 text-slate-400" />
    </button>
  ))}
</div>

// Quick Actions 数据 - 完整列表
const QUICK_ACTIONS = [
  { 
    id: 'transactions', 
    label: 'Transaction History', 
    icon: History, 
    onClick: () => openTransactionsSheet() 
  },
  { 
    id: 'account', 
    label: 'Account Settings', 
    icon: User, 
    onClick: () => openClerkAccountManage() 
  },
  { 
    id: 'security', 
    label: 'Security', 
    icon: Shield, 
    onClick: () => openClerkSecurityManage() 
  },
  { 
    id: 'notifications', 
    label: 'Notifications', 
    icon: Bell, 
    onClick: () => openNotificationsSheet() // 新增
  },
  { 
    id: 'preferences', 
    label: 'Language & Theme', 
    icon: Globe, // 或 Palette
    onClick: () => openPreferencesSheet() // 新增
  },
  { 
    id: 'help', 
    label: 'Help & Support', 
    icon: HelpCircle, 
    onClick: () => router.push('/manual') 
  },
];
```

#### Sign Out Button

```jsx
// 设计规格 - 与 MobileMenu 中的登出按钮风格一致
<div className="mx-4 mt-4 pb-24"> {/* pb-24 为 BottomNavbar 预留空间 */}
  <Button
    variant="outline"
    className={cn(
      "w-full h-11 rounded-xl",
      "border-red-200 text-red-600",
      "hover:bg-red-50 hover:border-red-300",
      "active:bg-red-100 active:scale-[0.98]",
      "transition-all duration-150"
    )}
    onClick={() => {
      haptic.light(); // 触觉反馈
      handleSignOut();
    }}
  >
    <LogOut className="w-4 h-4 mr-2" />
    Sign Out
  </Button>
  
  {/* App Version */}
  <p className="mt-8 text-center text-xs text-slate-400">
    Version 1.0.0 • Made with ❤️
  </p>
</div>
```

---

## 4. 交互规范

### 4.1 触控反馈

与现有移动端组件（BottomNavbar、MobileBottomSheet 等）保持一致：

| 元素类型 | 触控反馈 | 代码示例 |
|----------|---------|---------|
| **主按钮 (CTA)** | `active:scale-[0.98]` + `haptic.light()` | `className="active:scale-[0.98] transition-all"` |
| **次要按钮** | `active:scale-[0.98]` + `haptic.light()` | 同上 |
| **列表项** | `active:bg-slate-100` + `haptic.light()` | `className="active:bg-slate-100 transition-colors"` |
| **危险操作** | `active:bg-red-100` + `haptic.warning()` + 确认弹窗 | - |
| **Tab 切换** | `active:scale-95` + `haptic.light()` | 参考 BottomNavbar |

**触觉反馈 API（使用现有 haptic 模块）**：

```typescript
import { haptic } from '@/app/create/_lib/haptic';

// 轻触反馈 - 用于普通操作
haptic.light();

// 成功反馈 - 用于操作成功
haptic.success();

// 警告反馈 - 用于危险操作确认
haptic.warning();
```

### 4.2 加载状态

```jsx
// 页面初始加载
<div className="flex flex-col items-center justify-center min-h-screen">
  <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
  <p className="mt-2 text-sm text-slate-500">Loading your profile...</p>
</div>

// 按钮加载
<Button disabled={isLoading}>
  {isLoading ? (
    <>
      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      Processing...
    </>
  ) : (
    'Submit'
  )}
</Button>
```

### 4.3 空状态

```jsx
// 未登录状态
<div className="flex flex-col items-center justify-center min-h-screen px-6">
  <User className="w-16 h-16 text-slate-300" />
  <h2 className="mt-4 text-xl font-bold text-slate-900">Sign in to continue</h2>
  <p className="mt-2 text-sm text-slate-500 text-center">
    Access your profile, manage subscriptions, and track your credits.
  </p>
  <SignInButton mode="modal">
    <Button className="mt-6 w-full max-w-xs h-12 rounded-xl">
      Sign In
    </Button>
  </SignInButton>
</div>
```

### 4.4 错误处理

```jsx
// 网络错误
<div className="mx-4 p-4 rounded-xl bg-red-50 border border-red-200">
  <div className="flex items-center gap-3">
    <AlertTriangle className="w-5 h-5 text-red-500" />
    <div>
      <p className="font-medium text-red-700">Failed to load profile</p>
      <p className="text-sm text-red-600">Please check your connection and try again.</p>
    </div>
  </div>
  <Button 
    variant="outline" 
    size="sm" 
    className="mt-3"
    onClick={handleRetry}
  >
    <RefreshCw className="w-4 h-4 mr-2" />
    Retry
  </Button>
</div>
```

### 4.5 Transaction History 展示方式

**方案 A：BottomSheet（推荐）**

```jsx
// 使用现有的 MobileBottomSheet 组件
<MobileBottomSheet
  open={showTransactions}
  onOpenChange={setShowTransactions}
  title="Transaction History"
  height="85vh"
>
  <ClerkTransactionHistory />
</MobileBottomSheet>
```

**方案 B：单独页面**

```jsx
// /profile/transactions 页面
// 完整页面，支持分页和筛选
```

建议使用 **方案 A（BottomSheet）**，原因：
1. 保持用户在 Profile 页面的上下文
2. 交互更流畅，无需页面跳转
3. 与移动端编辑器的 BottomSheet 交互一致

### 4.6 Notifications 设置 (新增)

```tsx
// components/profile/NotificationsSheet.tsx
import { MobileBottomSheet } from "@/components/common/MobileBottomSheet";
import { Switch } from "@/components/ui/switch";
import { Mail, Bell, Megaphone } from "lucide-react";

interface NotificationsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NotificationsSheet({ open, onOpenChange }: NotificationsSheetProps) {
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [pushEnabled, setPushEnabled] = useState(true);
  const [marketingEnabled, setMarketingEnabled] = useState(false);

  return (
    <MobileBottomSheet
      open={open}
      onOpenChange={onOpenChange}
      title="Notifications"
      height="50vh"
    >
      <div className="px-4 py-2">
        <div className="rounded-xl bg-white border border-slate-200 divide-y divide-slate-100">
          {/* Email Notifications */}
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
                <Mail className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="font-medium text-slate-900">Email Notifications</p>
                <p className="text-xs text-slate-500">Updates, promotions & tips</p>
              </div>
            </div>
            <Switch checked={emailEnabled} onCheckedChange={setEmailEnabled} />
          </div>
          
          {/* Push Notifications */}
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-violet-50 flex items-center justify-center">
                <Bell className="w-5 h-5 text-violet-600" />
              </div>
              <div>
                <p className="font-medium text-slate-900">Push Notifications</p>
                <p className="text-xs text-slate-500">Real-time alerts</p>
              </div>
            </div>
            <Switch checked={pushEnabled} onCheckedChange={setPushEnabled} />
          </div>
          
          {/* Marketing */}
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center">
                <Megaphone className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="font-medium text-slate-900">Marketing</p>
                <p className="text-xs text-slate-500">Special offers & deals</p>
              </div>
            </div>
            <Switch checked={marketingEnabled} onCheckedChange={setMarketingEnabled} />
          </div>
        </div>
      </div>
    </MobileBottomSheet>
  );
}
```

### 4.7 Language & Theme 设置 (新增)

```tsx
// components/profile/PreferencesSheet.tsx
import { MobileBottomSheet } from "@/components/common/MobileBottomSheet";
import { Check, Monitor, Sun, Moon } from "lucide-react";

interface PreferencesSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const LANGUAGES = [
  { code: 'en', label: 'English', flag: '🇺🇸' },
  { code: 'zh', label: '简体中文', flag: '🇨🇳' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
];

const THEMES = [
  { id: 'system', label: 'System', icon: Monitor },
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'dark', label: 'Dark', icon: Moon },
];

export function PreferencesSheet({ open, onOpenChange }: PreferencesSheetProps) {
  const [currentLanguage, setCurrentLanguage] = useState('en');
  const [currentTheme, setCurrentTheme] = useState('system');

  return (
    <MobileBottomSheet
      open={open}
      onOpenChange={onOpenChange}
      title="Language & Theme"
      height="70vh"
    >
      <div className="px-4 py-2 space-y-6">
        {/* Language Section */}
        <div>
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3 px-1">
            Language
          </h3>
          <div className="rounded-xl bg-white border border-slate-200 overflow-hidden">
            {LANGUAGES.map((lang, index) => (
              <button
                key={lang.code}
                onClick={() => {
                  setCurrentLanguage(lang.code);
                  haptic.light();
                }}
                className={cn(
                  "w-full flex items-center justify-between px-4 py-3.5",
                  "active:bg-slate-100 transition-colors",
                  index !== LANGUAGES.length - 1 && "border-b border-slate-100"
                )}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{lang.flag}</span>
                  <span className="font-medium text-slate-900">{lang.label}</span>
                </div>
                {currentLanguage === lang.code && (
                  <Check className="w-5 h-5 text-violet-600" />
                )}
              </button>
            ))}
          </div>
        </div>
        
        {/* Theme Section */}
        <div>
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3 px-1">
            Theme
          </h3>
          <div className="rounded-xl bg-white border border-slate-200 overflow-hidden">
            {THEMES.map((theme, index) => (
              <button
                key={theme.id}
                onClick={() => {
                  setCurrentTheme(theme.id);
                  haptic.light();
                }}
                className={cn(
                  "w-full flex items-center justify-between px-4 py-3.5",
                  "active:bg-slate-100 transition-colors",
                  index !== THEMES.length - 1 && "border-b border-slate-100"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center">
                    <theme.icon className="w-5 h-5 text-slate-600" />
                  </div>
                  <span className="font-medium text-slate-900">{theme.label}</span>
                </div>
                {currentTheme === theme.id && (
                  <Check className="w-5 h-5 text-violet-600" />
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    </MobileBottomSheet>
  );
}
```

---

## 5. 技术实现方案

### 5.1 文件结构

```
decodables-fe/
├── app/
│   └── profile/
│       └── page.tsx                # Profile 页面主入口
│
├── components/
│   └── profile/
│       ├── index.ts                # 导出所有组件
│       ├── ProfileHeader.tsx       # 用户头像/名字区域
│       ├── UserIdCard.tsx          # User ID 展示 + 复制 (新增)
│       ├── CreditsCard.tsx         # 积分卡片
│       ├── SubscriptionCard.tsx    # 订阅卡片
│       ├── QuickActionsList.tsx    # 快捷操作列表
│       ├── TransactionSheet.tsx    # 交易历史 BottomSheet
│       ├── NotificationsSheet.tsx  # 通知设置 BottomSheet (新增)
│       └── PreferencesSheet.tsx    # 语言/主题设置 BottomSheet (新增)
```

### 5.2 核心组件实现

```typescript
// app/profile/page.tsx
"use client";

import { useState, useEffect } from "react";
import { useUser, useAuth, useClerk, SignIn } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useUserStore, TIERS } from "@/lib/useUserStore";
import { cn } from "@/lib/utils";
import { haptic } from "@/app/create/_lib/haptic";

// Components
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { CreditsCard } from "@/components/profile/CreditsCard";
import { SubscriptionCard } from "@/components/profile/SubscriptionCard";
import { QuickActionsList } from "@/components/profile/QuickActionsList";
import { TransactionSheet } from "@/components/profile/TransactionSheet";

export default function ProfilePage() {
  const { user, isLoaded: isUserLoaded } = useUser();
  const { isSignedIn, getToken } = useAuth();
  const { signOut, openUserProfile } = useClerk();
  const router = useRouter();
  
  const { 
    tier, 
    creditsMonthly, 
    creditsPermanent, 
    isInitialized,
    isWithinTrialPeriod,
    createdAt,
  } = useUserStore();
  
  const [showTransactions, setShowTransactions] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Hydration fix (与 Dashboard 保持一致)
  useEffect(() => {
    setMounted(true);
  }, []);

  // Handle sign out
  const handleSignOut = async () => {
    try {
      setIsSigningOut(true);
      haptic.light();
      await signOut();
      router.push("/");
    } catch (error) {
      console.error("Sign out failed:", error);
    } finally {
      setIsSigningOut(false);
    }
  };

  // Handle Clerk account/security management
  const handleOpenAccount = () => {
    haptic.light();
    openUserProfile();
  };

  // Loading state (与 Dashboard 保持一致)
  if (!mounted || !isUserLoaded || !isInitialized) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
          <p className="text-slate-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  // Not signed in (与 Dashboard 保持一致)
  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <SignIn
          routing="hash"
          forceRedirectUrl="/profile"
          appearance={{
            elements: {
              rootBox: 'mx-auto',
              card: 'shadow-xl',
            },
          }}
        />
      </div>
    );
  }

  // BottomSheet states
  const [showTransactions, setShowTransactions] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* 全局 Navbar (与 Landing、Dashboard、Marketplace 一致) */}
      <Navbar />

      {/* Content - pb-24 为 BottomNavbar 预留空间 */}
      <div className="py-4 pb-24">
        {/* User Header */}
        <ProfileHeader user={user} tier={tier} />
        
        {/* User ID Card (新增) */}
        <UserIdCard userId={user.id} />
        
        {/* Credits Card */}
        <CreditsCard
          tier={tier}
          creditsMonthly={creditsMonthly}
          creditsPermanent={creditsPermanent}
          onBuyCredits={handleBuyCredits}
        />
        
        {/* Subscription Card */}
        <SubscriptionCard
          tier={tier}
          isWithinTrialPeriod={isWithinTrialPeriod}
          createdAt={createdAt}
          onManage={handleManageSubscription}
          onUpgrade={handleUpgrade}
        />
        
        {/* Quick Actions */}
        <QuickActionsList
          onOpenTransactions={() => {
            haptic.light();
            setShowTransactions(true);
          }}
          onOpenAccount={handleOpenAccount}
          onOpenNotifications={() => {
            haptic.light();
            setShowNotifications(true);
          }}
          onOpenPreferences={() => {
            haptic.light();
            setShowPreferences(true);
          }}
          onOpenHelp={() => {
            haptic.light();
            router.push("/manual");
          }}
        />
        
        {/* Sign Out */}
        <SignOutButton 
          isLoading={isSigningOut} 
          onClick={handleSignOut} 
        />
        
        {/* Version */}
        <p className="mt-8 text-center text-xs text-slate-400">
          Version 1.0.0 • Made with ❤️
        </p>
      </div>

      {/* Transaction History BottomSheet */}
      <TransactionSheet
        open={showTransactions}
        onOpenChange={setShowTransactions}
      />
      
      {/* Notifications BottomSheet (新增) */}
      <NotificationsSheet
        open={showNotifications}
        onOpenChange={setShowNotifications}
      />
      
      {/* Language & Theme BottomSheet (新增) */}
      <PreferencesSheet
        open={showPreferences}
        onOpenChange={setShowPreferences}
      />
    </div>
  );
}
```

### 5.3 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                      Profile Page                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌─────────────────┐                   │
│  │ useUser()    │────►│ ProfileHeader   │                   │
│  │ (Clerk)      │     │ - avatar        │                   │
│  │              │     │ - name          │                   │
│  │              │     │ - email         │                   │
│  └──────────────┘     └─────────────────┘                   │
│                                                              │
│  ┌──────────────┐     ┌─────────────────┐                   │
│  │ useUserStore │────►│ CreditsCard     │                   │
│  │ (Zustand)    │     │ - tier          │                   │
│  │              │     │ - monthly       │                   │
│  │              │     │ - permanent     │                   │
│  └──────────────┘     └─────────────────┘                   │
│         │                                                    │
│         │             ┌─────────────────┐                   │
│         └────────────►│ SubscriptionCard│                   │
│                       │ - tier          │                   │
│                       │ - trial status  │                   │
│                       └─────────────────┘                   │
│                                                              │
│  ┌──────────────┐     ┌─────────────────┐                   │
│  │ useAuth()    │────►│ API Calls       │                   │
│  │ (Clerk)      │     │ - getCheckoutUrl│                   │
│  │              │     │ - getPortalUrl  │                   │
│  │              │     │ - getCreditHist │                   │
│  └──────────────┘     └─────────────────┘                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 动画规范

```jsx
// 页面进入动画
<div className="animate-in fade-in-0 slide-in-from-bottom-4 duration-300">
  {/* Content */}
</div>

// 卡片交错进入
{cards.map((card, index) => (
  <div
    key={card.id}
    className="animate-in fade-in-0 slide-in-from-bottom-2"
    style={{ animationDelay: `${index * 50}ms` }}
  >
    {/* Card content */}
  </div>
))}

// BottomSheet 动画 (使用现有组件)
// MobileBottomSheet 已内置 slide-in-from-bottom 动画
```

---

## 6. 业界参考

### 6.1 Spotify Mobile

**优点**：
- 顶部大头像 + 用户名，视觉突出
- 设置项分组清晰
- 底部登出按钮位置合理

**借鉴**：
- 头像尺寸 80px，带边框
- 设置列表使用卡片分组

### 6.2 Notion Mobile

**优点**：
- Plan/Subscription 信息直接展示
- 设置项有图标 + 文字 + 箭头
- 浅色背景 + 白色卡片的对比

**借鉴**：
- 订阅卡片的信息展示方式
- 列表项的 icon + label + chevron 布局

### 6.3 Linear Mobile

**优点**：
- 紧凑的个人信息区
- Workspace 切换区域清晰
- 版本信息在底部

**借鉴**：
- 底部版本号展示
- 整体紧凑的间距设计

### 6.4 Figma Mobile

**优点**：
- Plan badge 视觉突出
- 操作按钮直接展示
- 无需滚动查看核心信息

**借鉴**：
- Tier badge 的设计风格
- 按钮直接展示而非隐藏在菜单中

---

## 7. 已确认事项

### 7.1 功能范围 ✅

- [x] **Transaction History 展示方式**：使用 BottomSheet ✅
  - 理由：保持上下文，与编辑器 BottomSheet 交互一致
- [x] **Account/Security 跳转**：使用 Clerk `openUserProfile()` ✅
  - 理由：复用现有安全功能，无需重新实现
- [x] **Copy User ID**：直接显示 User ID + 复制按钮 ✅ (2026-01-22 确认)
  - 理由：与 PC 端功能保持一致
- [x] **通知设置入口**：添加 Notifications 设置 ✅ (2026-01-22 确认)
- [x] **语言/主题切换入口**：添加 Language & Theme 设置 ✅ (2026-01-22 确认)
- [x] **Security 和 Help & Support**：保留 ✅ (2026-01-22 确认)

### 7.2 视觉细节 ✅

- [x] **顶部导航**：使用全局 Navbar（与 Landing、Dashboard、Marketplace 一致）✅ (2026-01-22 确认)
- [x] **页面背景**：`bg-slate-50`（与 Dashboard 一致）✅
- [x] **卡片圆角**：`rounded-xl`（与 PlanCard、ListingCard 一致）✅
- [x] **头像边框**：不使用 Tier 颜色环（与 PC 端保持一致）✅ (2026-01-22 确认)
- [x] **Credits Card**：与 ClerkBillingPage 风格一致，无需额外渐变 ✅
- [x] **Sign Out 按钮**：红色描边样式（与 MobileMenu 一致）✅

### 7.3 技术细节

- [x] **Clerk UserProfile 弹窗**：使用默认 Modal，Clerk 已做移动端响应式适配 ✅
  - 业界最佳实践：保持默认 Modal，通过 `appearance` API 微调样式
  - 如果体验不佳，可改为 `<UserProfile />` 组件嵌入全屏页面
  
- [x] **Stripe Portal**：使用同窗口跳转 (`window.location.href`) ✅
  - 业界最佳实践：同窗口跳转兼容性最好，配合 `return_url` 实现返回
  - 不推荐 In-App Browser（支付安全问题）或新标签页（可能被阻止）
  - 跳转前显示加载状态和外部链接图标，提示用户即将离开
  
- [x] **Hydration 处理**：使用与 Dashboard 相同的 `mounted` state 模式 ✅
- [x] **底部安全区域**：使用 `pb-24` 为 BottomNavbar 预留空间 ✅

### 7.4 关键决策点

| 决策项 | 选项 A | 选项 B | 最终决策 |
|-------|--------|--------|---------|
| **顶部导航** | 全局 Navbar（有 Logo） | 简洁 Header（仅标题） | **选项 A** ✅ - 与其他页面保持一致 |
| **头像 Tier 颜色环** | 使用 Tier 颜色环 | 无颜色环 | **选项 B** ✅ - 与 PC 端保持一致 |
| **Transaction History** | 单独页面 | BottomSheet | **选项 B** ✅ - 保持交互一致性 |
| **Clerk 集成** | 完全自定义 | 调用 openUserProfile() | **选项 B** ✅ - 复用现有功能 |
| **Copy User ID** | 隐藏在菜单中 | 直接显示 + 复制按钮 | **选项 B** ✅ - 更便捷 |
| **额外设置** | 无 | 通知 + 语言/主题 | **选项 B** ✅ - 增强功能 |

---

## 附录：组件清单

| 组件名 | 类型 | 状态 | 说明 |
|--------|------|------|------|
| `ProfilePage` | Page | 新建 | 主页面 |
| `ProfileHeader` | Component | 新建 | 用户头像/信息区（无 Tier 颜色环） |
| `UserIdCard` | Component | 新建 | User ID 展示 + 复制按钮 |
| `CreditsCard` | Component | 新建 | 积分卡片 |
| `SubscriptionCard` | Component | 新建 | 订阅管理卡片 |
| `QuickActionsList` | Component | 新建 | 快捷操作列表（含 6 个入口） |
| `TransactionSheet` | Component | 新建 | 交易历史 BottomSheet |
| `NotificationsSheet` | Component | 新建 | 通知设置 BottomSheet |
| `PreferencesSheet` | Component | 新建 | 语言/主题设置 BottomSheet |
| `SignOutButton` | Component | 新建 | 登出按钮 |
| `ProfileSkeleton` | Component | 新建 | 加载骨架屏 |
| `SignInPrompt` | Component | 新建 | 未登录提示 |

---

> **文档结束**  
> 请确认上述设计方案后，我们将开始实施。
