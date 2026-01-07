# Onboarding 新手引导系统设计

> **版本**: v1.0  
> **日期**: 2026-01-06  
> **目标**: 提升新用户激活率和功能发现率

---

## 目录

1. [设计概览](#1-设计概览)
2. [引导类型详细设计](#2-引导类型详细设计)
3. [Welcome Tour 设计](#3-welcome-tour-设计)
4. [Editor Tour 设计](#4-editor-tour-设计)
5. [Getting Started Checklist](#5-getting-started-checklist)
6. [Feature Spotlights](#6-feature-spotlights)
7. [数据结构设计](#7-数据结构设计)
8. [后端实现](#8-后端实现)
9. [前端实现](#9-前端实现)
10. [实施计划](#10-实施计划)

---

## 1. 设计概览

### 1.1 设计目标

```
┌─────────────────────────────────────────────────────────────────┐
│                    Onboarding 设计目标                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 量化目标                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 新用户 7 天留存率: +15%                               │   │
│  │  • 首个项目创建率: +30%                                  │   │
│  │  • AI 生成功能使用率: +25%                               │   │
│  │  • 付费转化率: +10%                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🎯 体验目标                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 30 秒内理解产品核心价值                               │   │
│  │  • 2 分钟内完成第一个作品                                │   │
│  │  • 发现 80% 的核心功能                                   │   │
│  │  • 感受到 "Aha Moment"                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  💡 设计原则                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 渐进披露: 不要一次性展示所有功能                       │   │
│  │  • 即时价值: 让用户尽快体验到产品价值                     │   │
│  │  • 可跳过: 尊重用户选择，所有引导可跳过                   │   │
│  │  • 可重来: 用户可以随时重新查看引导                       │   │
│  │  • 上下文: 在合适的时机展示相关引导                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 引导体系架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    引导体系架构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户注册                                                        │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1️⃣ Welcome Tour (欢迎引导)                              │   │
│  │     触发: 新用户首次登录                                  │   │
│  │     目的: 产品价值认知 + 积分礼物                         │   │
│  │     时长: ~30 秒                                          │   │
│  │     步骤: 5 步                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  2️⃣ Getting Started Checklist (任务清单)                 │   │
│  │     触发: 完成 Welcome Tour 后                            │   │
│  │     目的: 引导完成关键动作 + 奖励驱动                     │   │
│  │     位置: Dashboard 侧边栏                                │   │
│  │     有效期: 注册后 7 天内                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼ (首次进入编辑器)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  3️⃣ Editor Tour (编辑器引导)                             │   │
│  │     触发: 首次进入 /create 页面                           │   │
│  │     目的: 熟悉编辑器核心功能                              │   │
│  │     时长: ~1 分钟                                         │   │
│  │     步骤: 8 步                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼ (发现新功能时)                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  4️⃣ Feature Spotlights (功能高亮)                        │   │
│  │     触发: 首次接触特定功能                                │   │
│  │     目的: 功能发现 + 升级提示                             │   │
│  │     类型: 小气泡提示 / 升级提示 / 新功能公告              │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼ (持续使用)                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  5️⃣ Contextual Help (上下文帮助)                         │   │
│  │     触发: 用户遇到困难 / 空状态                           │   │
│  │     目的: 减少困惑，提供即时帮助                          │   │
│  │     类型: 空状态引导 / 错误恢复 / 帮助提示                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 触发规则总览

| 引导类型 | 触发条件 | 优先级 | 可跳过 | 可重新触发 | 显示位置 |
|----------|----------|--------|--------|-----------|----------|
| Welcome Tour | 新用户首次登录 | 最高 | ✅ | 手动 (帮助菜单) | 全屏 Modal |
| Checklist | 新用户 7 天内 | 高 | ✅ (可收起) | 自动 (未完成) | Dashboard 侧边 |
| Editor Tour | 首次进入编辑器 | 中 | ✅ | 手动 (帮助菜单) | 步骤高亮 |
| Feature Spotlight | 首次接触功能 | 低 | ✅ | ❌ | 气泡/弹窗 |
| Contextual Help | 空状态/错误 | 低 | ✅ | 自动 | 内嵌提示 |

---

## 2. 引导类型详细设计

### 2.1 引导类型对比

```
┌─────────────────────────────────────────────────────────────────┐
│                    引导类型对比                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Modal Tour (全屏弹窗式)                                  │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │                                                    │  │   │
│  │  │          🎉 Welcome to Our App!                   │  │   │
│  │  │                                                    │  │   │
│  │  │              [   Image/Animation   ]              │  │   │
│  │  │                                                    │  │   │
│  │  │          Description text here...                 │  │   │
│  │  │                                                    │  │   │
│  │  │              [Skip]  [Next →]                     │  │   │
│  │  │                                                    │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │  适用: Welcome Tour, 重要公告                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Guided Tour (步骤高亮式 - Joyride)                      │   │
│  │                                                          │   │
│  │  ┌──────┐                                               │   │
│  │  │Target│ ← 高亮                                        │   │
│  │  └──────┘                                               │   │
│  │      ↑                                                   │   │
│  │  ┌──────────────────────────────┐                       │   │
│  │  │ 💡 Step Title                │                       │   │
│  │  │                              │                       │   │
│  │  │ Description of this feature │                       │   │
│  │  │                              │                       │   │
│  │  │ [Skip] [Back] [Next] (2/8)  │                       │   │
│  │  └──────────────────────────────┘                       │   │
│  │  适用: Editor Tour, 功能教学                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Spotlight (小气泡式)                                    │   │
│  │                                                          │   │
│  │  ┌──────────┐                                           │   │
│  │  │ Feature  │                                           │   │
│  │  └──────────┘                                           │   │
│  │       ↑                                                  │   │
│  │  ┌─────────────────┐                                    │   │
│  │  │ 💡 New!         │                                    │   │
│  │  │ Try this feature│                                    │   │
│  │  │        [Got it] │                                    │   │
│  │  └─────────────────┘                                    │   │
│  │  适用: 新功能提示, 小技巧                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Checklist (任务清单式)                                  │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  Getting Started          [████░░░░] 40%        │    │   │
│  │  ├─────────────────────────────────────────────────┤    │   │
│  │  │  ✅ Create your first project         +10 💎   │    │   │
│  │  │  ✅ Generate an AI image              +10 💎   │    │   │
│  │  │  ⬜ Add text to a page                +5 💎    │    │   │
│  │  │  ⬜ Export your book                  +10 💎   │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  适用: 新手任务, 激活引导                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Welcome Tour 设计

### 3.1 流程设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Welcome Tour 流程                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: 欢迎页面                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │              🎉 Welcome to Make Decodables!             │   │
│  │                                                          │   │
│  │     ┌────────────────────────────────────────────┐      │   │
│  │     │                                            │      │   │
│  │     │           [动画: 书本翻页效果]              │      │   │
│  │     │                                            │      │   │
│  │     └────────────────────────────────────────────┘      │   │
│  │                                                          │   │
│  │     Create beautiful 8-page mini-books                  │   │
│  │     in just 30 seconds with AI                          │   │
│  │                                                          │   │
│  │     ┌────────────────┐  ┌────────────────┐              │   │
│  │     │  Quick Start   │  │  Take a Tour   │              │   │
│  │     │  (跳过引导)     │  │  (开始引导)    │              │   │
│  │     └────────────────┘  └────────────────┘              │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 2: AI 功能介绍                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                    ✨ AI-Powered                         │   │
│  │                                                          │   │
│  │     ┌────────────────────────────────────────────┐      │   │
│  │     │                                            │      │   │
│  │     │     [动画: AI 生成图片过程]                 │      │   │
│  │     │                                            │      │   │
│  │     └────────────────────────────────────────────┘      │   │
│  │                                                          │   │
│  │     Generate stunning illustrations and stories         │   │
│  │     with just a few words                               │   │
│  │                                                          │   │
│  │                    ○ ● ○ ○ ○                            │   │
│  │                                                          │   │
│  │                [Back]  [Next →]                         │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 3: 可视化编辑器                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                    🎨 Visual Editor                      │   │
│  │                                                          │   │
│  │     ┌────────────────────────────────────────────┐      │   │
│  │     │                                            │      │   │
│  │     │     [动画: 拖拽编辑演示]                    │      │   │
│  │     │                                            │      │   │
│  │     └────────────────────────────────────────────┘      │   │
│  │                                                          │   │
│  │     Drag-and-drop editor for easy customization         │   │
│  │     No design skills needed                             │   │
│  │                                                          │   │
│  │                    ○ ○ ● ○ ○                            │   │
│  │                                                          │   │
│  │                [Back]  [Next →]                         │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 4: 导出功能                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                    📄 Print Ready                        │   │
│  │                                                          │   │
│  │     ┌────────────────────────────────────────────┐      │   │
│  │     │                                            │      │   │
│  │     │     [动画: PDF 导出 + 折叠演示]             │      │   │
│  │     │                                            │      │   │
│  │     └────────────────────────────────────────────┘      │   │
│  │                                                          │   │
│  │     Export as PDF for professional printing             │   │
│  │     Perfect foldable mini-books every time              │   │
│  │                                                          │   │
│  │                    ○ ○ ○ ● ○                            │   │
│  │                                                          │   │
│  │                [Back]  [Next →]                         │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 5: 赠送积分 (关键转化步骤)                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                    🎁 Welcome Gift!                      │   │
│  │                                                          │   │
│  │     ┌────────────────────────────────────────────┐      │   │
│  │     │                                            │      │   │
│  │     │          ✨ 50 ✨                          │      │   │
│  │     │         FREE CREDITS                       │      │   │
│  │     │                                            │      │   │
│  │     │     [动画: 积分飞入效果]                    │      │   │
│  │     │                                            │      │   │
│  │     └────────────────────────────────────────────┘      │   │
│  │                                                          │   │
│  │     Use them to generate AI images and stories          │   │
│  │                                                          │   │
│  │     ┌──────────────────────────────────────────┐        │   │
│  │     │      🚀 Create My First Book             │        │   │
│  │     └──────────────────────────────────────────┘        │   │
│  │                                                          │   │
│  │                    ○ ○ ○ ○ ●                            │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Welcome Tour 配置

```typescript
// @business/onboarding/tours/welcomeTour.ts

import { TourConfig } from '@core/onboarding/types';

export const welcomeTour: TourConfig = {
  key: 'welcome_tour',
  name: 'Welcome Tour',
  version: 1,
  
  // 触发条件
  trigger: {
    type: 'auto',
    conditions: {
      isNewUser: true,
      newUserDays: 7,
      hasNotCompletedTour: ['welcome_tour'],
    },
  },
  
  // 类型
  tourType: 'modal',
  
  // 步骤
  steps: [
    {
      key: 'welcome',
      title: '🎉 Welcome to Make Decodables!',
      content: 'Create beautiful 8-page mini-books in just 30 seconds with AI',
      image: '/onboarding/welcome-animation.json', // Lottie 动画
      actions: {
        primary: { label: 'Take a Tour', action: 'next' },
        secondary: { label: 'Quick Start', action: 'skip' },
      },
    },
    {
      key: 'ai_powered',
      title: '✨ AI-Powered',
      content: 'Generate stunning illustrations and stories with just a few words',
      image: '/onboarding/ai-demo.json',
      actions: {
        primary: { label: 'Next', action: 'next' },
        secondary: { label: 'Back', action: 'back' },
      },
    },
    {
      key: 'visual_editor',
      title: '🎨 Visual Editor',
      content: 'Drag-and-drop editor for easy customization. No design skills needed.',
      image: '/onboarding/editor-demo.json',
      actions: {
        primary: { label: 'Next', action: 'next' },
        secondary: { label: 'Back', action: 'back' },
      },
    },
    {
      key: 'print_ready',
      title: '📄 Print Ready',
      content: 'Export as PDF for professional printing. Perfect foldable mini-books every time.',
      image: '/onboarding/export-demo.json',
      actions: {
        primary: { label: 'Next', action: 'next' },
        secondary: { label: 'Back', action: 'back' },
      },
    },
    {
      key: 'welcome_gift',
      title: '🎁 Welcome Gift!',
      content: 'You received 50 free credits! Use them to generate AI images and stories.',
      image: '/onboarding/credits-animation.json',
      highlight: true,
      actions: {
        primary: { label: '🚀 Create My First Book', action: 'complete', redirect: '/create' },
      },
    },
  ],
  
  // 选项
  options: {
    showProgress: true,
    allowSkip: true,
    showStepNumbers: true,
    backdropClick: false, // 点击背景不关闭
  },
  
  // 完成回调
  onComplete: {
    markAsComplete: true,
    redirect: '/create',
    trackEvent: 'onboarding_welcome_completed',
  },
  
  // 跳过回调
  onSkip: {
    markAsComplete: true,
    redirect: '/dashboard',
    trackEvent: 'onboarding_welcome_skipped',
  },
};
```

---

## 4. Editor Tour 设计

### 4.1 步骤设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Editor Tour 步骤设计                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  使用 React Joyride 实现步骤高亮引导                              │
│                                                                 │
│  Step 1: 页面导航器                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  ┌──────┐                                               │   │
│  │  │Page 1│ ← 高亮 + 脉冲动画                              │   │
│  │  │Page 2│                                               │   │
│  │  │Page 3│   ┌────────────────────────────────────┐      │   │
│  │  │ ...  │   │ 📖 Page Navigator           (1/8) │      │   │
│  │  │Page 8│   │                                    │      │   │
│  │  └──────┘   │ Your mini-book has 8 pages.       │      │   │
│  │             │ Click any page to edit it.        │      │   │
│  │             │                                    │      │   │
│  │             │ 💡 Tip: The first page is the     │      │   │
│  │             │ cover of your book!               │      │   │
│  │             │                                    │      │   │
│  │             │ [Skip Tour]  [Next →]             │      │   │
│  │             └────────────────────────────────────┘      │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 2: 工具栏                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────┐ ← 高亮          │   │
│  │  │ [T] [🖼] [✨] [📁] | [↩] [↪] [💾]  │                  │   │
│  │  └────────────────────────────────────┘                  │   │
│  │          ↑                                               │   │
│  │  ┌────────────────────────────────────┐                  │   │
│  │  │ 🛠️ Toolbar                  (2/8) │                  │   │
│  │  │                                    │                  │   │
│  │  │ This is your creative toolbox:    │                  │   │
│  │  │ • T - Add text                    │                  │   │
│  │  │ • 🖼 - Add images                 │                  │   │
│  │  │ • ✨ - AI Generate (Magic!)       │                  │   │
│  │  │ • 📁 - Media library              │                  │   │
│  │  │                                    │                  │   │
│  │  │ [← Back]  [Next →]                │                  │   │
│  │  └────────────────────────────────────┘                  │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 3: AI 生成按钮 (重点 - 强调)                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │        ┌───────────────────┐ ← 高亮 + 特殊脉冲动画       │   │
│  │        │ ✨ AI Generate    │                             │   │
│  │        └───────────────────┘                             │   │
│  │                ↑                                         │   │
│  │        ┌────────────────────────────────────┐           │   │
│  │        │ ✨ AI Magic                 (3/8) │           │   │
│  │        │                                    │           │   │
│  │        │ This is where the magic happens!  │           │   │
│  │        │                                    │           │   │
│  │        │ 🖼 Generate Images                │           │   │
│  │        │ Describe what you want to see,    │           │   │
│  │        │ and AI will create it for you.    │           │   │
│  │        │                                    │           │   │
│  │        │ 📝 Generate Stories               │           │   │
│  │        │ Let AI help you write engaging    │           │   │
│  │        │ stories for your mini-books.      │           │   │
│  │        │                                    │           │   │
│  │        │ [← Back]  [Try it now! →]         │           │   │
│  │        └────────────────────────────────────┘           │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 4: 画布区域                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────┐ ←高亮  │   │
│  │  │                                               │       │   │
│  │  │                 Canvas Area                   │       │   │
│  │  │                                               │       │   │
│  │  └──────────────────────────────────────────────┘       │   │
│  │                          ↑                               │   │
│  │  ┌────────────────────────────────────┐                  │   │
│  │  │ 🎨 Canvas                   (4/8) │                  │   │
│  │  │                                    │                  │   │
│  │  │ This is your creative space!      │                  │   │
│  │  │                                    │                  │   │
│  │  │ • Drag elements to position them  │                  │   │
│  │  │ • Resize by dragging corners      │                  │   │
│  │  │ • Double-click to edit text       │                  │   │
│  │  │ • Right-click for more options    │                  │   │
│  │  │                                    │                  │   │
│  │  │ [← Back]  [Next →]                │                  │   │
│  │  └────────────────────────────────────┘                  │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 5: Media Library                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 📁 Media Library                         (5/8) │    │   │
│  │  │                                                 │    │   │
│  │  │ Browse thousands of assets:                    │    │   │
│  │  │                                                 │    │   │
│  │  │ 🎨 Stickers - Fun characters & objects        │    │   │
│  │  │ 🖼 Backgrounds - Beautiful scenes             │    │   │
│  │  │ 📝 Text Styles - Ready-to-use designs        │    │   │
│  │  │ 📁 Your Uploads - Your own images            │    │   │
│  │  │                                                 │    │   │
│  │  │ Click or drag any item to add it!             │    │   │
│  │  │                                                 │    │   │
│  │  │ [← Back]  [Next →]                            │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                          ↑ 高亮          │   │
│  │  ┌──────────┐                                           │   │
│  │  │ Media    │                                           │   │
│  │  │ Library  │                                           │   │
│  │  │ Panel    │                                           │   │
│  │  └──────────┘                                           │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 6: Properties Panel                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                                  ┌──────────┐           │   │
│  │                                  │Properties│ ← 高亮    │   │
│  │                                  │  Panel   │           │   │
│  │                                  └──────────┘           │   │
│  │                                        ↑                 │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ ⚙️ Properties Panel                      (6/8) │    │   │
│  │  │                                                 │    │   │
│  │  │ Select any element to edit its properties:     │    │   │
│  │  │                                                 │    │   │
│  │  │ 📏 Size & Position                             │    │   │
│  │  │ 🎨 Colors & Styles                             │    │   │
│  │  │ ✨ Effects & Filters                           │    │   │
│  │  │                                                 │    │   │
│  │  │ [← Back]  [Next →]                            │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 7: 保存按钮                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │             ┌─────────────┐ ← 高亮                       │   │
│  │             │ 💾 Auto-Save │                             │   │
│  │             └─────────────┘                              │   │
│  │                    ↑                                     │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 💾 Auto-Save                             (7/8) │    │   │
│  │  │                                                 │    │   │
│  │  │ Don't worry about losing your work!            │    │   │
│  │  │                                                 │    │   │
│  │  │ Your project saves automatically every         │    │   │
│  │  │ few seconds. You can also click here to        │    │   │
│  │  │ save manually.                                  │    │   │
│  │  │                                                 │    │   │
│  │  │ [← Back]  [Next →]                            │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 8: 导出按钮 (最终步骤)                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │             ┌─────────────────┐ ← 高亮                   │   │
│  │             │ 📤 Export PDF   │                          │   │
│  │             └─────────────────┘                          │   │
│  │                      ↑                                   │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 📤 Export                                (8/8) │    │   │
│  │  │                                                 │    │   │
│  │  │ When you're done, click here to download       │    │   │
│  │  │ your mini-book as a PDF!                       │    │   │
│  │  │                                                 │    │   │
│  │  │ 📄 PDF - Ready to print and fold              │    │   │
│  │  │ 📁 ZIP - Separate image files (Pro)           │    │   │
│  │  │                                                 │    │   │
│  │  │ That's it! You're ready to create! 🎉         │    │   │
│  │  │                                                 │    │   │
│  │  │ [← Back]  [🚀 Start Creating!]                │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Editor Tour 配置

```typescript
// @business/onboarding/tours/editorTour.ts

import { TourConfig } from '@core/onboarding/types';

export const editorTour: TourConfig = {
  key: 'editor_tour',
  name: 'Editor Tour',
  version: 1,
  
  trigger: {
    type: 'auto',
    conditions: {
      onPage: ['/create', '/create/*'],
      hasCompletedTour: ['welcome_tour'],
      hasNotCompletedTour: ['editor_tour'],
    },
  },
  
  tourType: 'guided', // 使用 Joyride
  
  steps: [
    {
      key: 'page_navigator',
      target: '[data-tour="page-navigator"]',
      placement: 'right',
      title: '📖 Page Navigator',
      content: 'Your mini-book has 8 pages. Click any page to edit it.',
      tip: '💡 The first page is the cover of your book!',
      highlight: { animation: 'pulse' },
    },
    {
      key: 'toolbar',
      target: '[data-tour="toolbar"]',
      placement: 'bottom',
      title: '🛠️ Toolbar',
      content: 'This is your creative toolbox:\n• T - Add text\n• 🖼 - Add images\n• ✨ - AI Generate (Magic!)\n• 📁 - Media library',
    },
    {
      key: 'ai_generate',
      target: '[data-tour="ai-generate"]',
      placement: 'bottom',
      title: '✨ AI Magic',
      content: 'This is where the magic happens!\n\n🖼 Generate Images - Describe what you want to see\n📝 Generate Stories - Let AI help you write',
      highlight: { animation: 'glow', color: '#FFD700' },
      actions: {
        primary: { label: 'Try it now!', action: 'next' },
      },
    },
    {
      key: 'canvas',
      target: '[data-tour="canvas"]',
      placement: 'center',
      title: '🎨 Canvas',
      content: 'This is your creative space!\n\n• Drag elements to position them\n• Resize by dragging corners\n• Double-click to edit text\n• Right-click for more options',
    },
    {
      key: 'media_library',
      target: '[data-tour="media-library"]',
      placement: 'left',
      title: '📁 Media Library',
      content: 'Browse thousands of assets:\n\n🎨 Stickers - Fun characters & objects\n🖼 Backgrounds - Beautiful scenes\n📝 Text Styles - Ready-to-use designs',
    },
    {
      key: 'properties',
      target: '[data-tour="properties-panel"]',
      placement: 'left',
      title: '⚙️ Properties Panel',
      content: 'Select any element to edit:\n\n📏 Size & Position\n🎨 Colors & Styles\n✨ Effects & Filters',
    },
    {
      key: 'save',
      target: '[data-tour="save-button"]',
      placement: 'bottom',
      title: '💾 Auto-Save',
      content: "Don't worry about losing your work! Your project saves automatically every few seconds.",
    },
    {
      key: 'export',
      target: '[data-tour="export-button"]',
      placement: 'bottom',
      title: '📤 Export',
      content: 'When you\'re done, download your mini-book as a PDF!\n\n📄 PDF - Ready to print and fold\n📁 ZIP - Separate image files (Pro)',
      actions: {
        primary: { label: '🚀 Start Creating!', action: 'complete' },
      },
    },
  ],
  
  options: {
    continuous: true,
    showProgress: true,
    showSkipButton: true,
    spotlightClicks: true, // 允许点击高亮区域
    disableOverlay: false,
    styles: {
      options: {
        primaryColor: '#4F46E5',
        zIndex: 10000,
      },
    },
  },
  
  onComplete: {
    markAsComplete: true,
    trackEvent: 'onboarding_editor_completed',
  },
};
```

---

## 5. Getting Started Checklist

### 5.1 视觉设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Checklist 视觉设计                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  展开状态 (默认):                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🚀 Getting Started               [━━━━━━━━░░░░] 60%    │   │
│  │                                                          │   │
│  │  Complete all tasks to earn bonus credits! 🎁           │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ✅ Create your first project                           │   │
│  │     └─ Earned: 10 💎                                    │   │
│  │                                                          │   │
│  │  ✅ Generate an AI image                                │   │
│  │     └─ Earned: 10 💎                                    │   │
│  │                                                          │   │
│  │  ✅ Add text to a page                                  │   │
│  │     └─ Earned: 5 💎                                     │   │
│  │                                                          │   │
│  │  ⬜ Use a sticker from the library            +5 💎     │   │
│  │     └─ [Browse Stickers →]                              │   │
│  │                                                          │   │
│  │  ⬜ Export your book as PDF                   +10 💎    │   │
│  │     └─ [Export Now →]                                   │   │
│  │                                                          │   │
│  │  ⬜ Share to Marketplace (Optional)           +20 💎    │   │
│  │     └─ Share your creation with the community           │   │
│  │                                                          │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  🏆 Complete All Tasks = +50 Bonus Credits!             │   │
│  │                                                          │   │
│  │  You've earned: 25 💎    Potential: +85 💎              │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│          [Collapse ▲]                                           │
│                                                                 │
│  收起状态:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🚀 Getting Started   [━━━━━━━━░░░░] 60%   [Expand ▼]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  完成状态:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🎉 All Done!         [━━━━━━━━━━━━] 100%               │   │
│  │                                                          │   │
│  │  You've earned 110 💎 in total!                         │   │
│  │                                                          │   │
│  │  [Dismiss] [Explore More Features →]                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 任务配置

```typescript
// @business/onboarding/checklists/gettingStarted.ts

import { ChecklistConfig, TaskConfig } from '@core/onboarding/types';

export const gettingStartedChecklist: ChecklistConfig = {
  key: 'getting_started',
  name: 'Getting Started',
  version: 1,
  
  // 显示条件
  display: {
    position: 'dashboard-sidebar', // 或 'floating', 'bottom-banner'
    showFor: {
      isNewUser: true,
      newUserDays: 7,
    },
    collapsible: true,
    dismissible: false, // 完成后可关闭
  },
  
  // 任务列表
  tasks: [
    {
      id: 'create_project',
      title: 'Create your first project',
      description: 'Start a new mini-book from scratch or template',
      icon: '📚',
      reward: {
        type: 'credits',
        amount: 10,
      },
      detection: {
        type: 'auto',
        condition: {
          metric: 'user.projects_count',
          operator: 'gte',
          value: 1,
        },
      },
      action: {
        label: 'Create Now',
        url: '/create',
      },
      order: 1,
    },
    {
      id: 'ai_generate',
      title: 'Generate an AI image',
      description: 'Use AI to create a unique illustration',
      icon: '✨',
      reward: {
        type: 'credits',
        amount: 10,
      },
      detection: {
        type: 'auto',
        condition: {
          metric: 'user.ai_generations_count',
          operator: 'gte',
          value: 1,
        },
      },
      action: {
        label: 'Try AI Generate',
        url: '/create?openAI=true',
      },
      order: 2,
    },
    {
      id: 'add_text',
      title: 'Add text to a page',
      description: 'Add a title or sentence to your book',
      icon: '📝',
      reward: {
        type: 'credits',
        amount: 5,
      },
      detection: {
        type: 'auto',
        condition: {
          metric: 'user.has_text_element',
          operator: 'eq',
          value: true,
        },
      },
      order: 3,
    },
    {
      id: 'use_sticker',
      title: 'Use a sticker from the library',
      description: 'Browse and add a fun sticker',
      icon: '🎨',
      reward: {
        type: 'credits',
        amount: 5,
      },
      detection: {
        type: 'auto',
        condition: {
          metric: 'user.has_sticker_element',
          operator: 'eq',
          value: true,
        },
      },
      action: {
        label: 'Browse Stickers',
        url: '/create?openMedia=stickers',
      },
      order: 4,
    },
    {
      id: 'export_pdf',
      title: 'Export your book as PDF',
      description: 'Download your finished mini-book',
      icon: '📄',
      reward: {
        type: 'credits',
        amount: 10,
      },
      detection: {
        type: 'auto',
        condition: {
          metric: 'user.exports_count',
          operator: 'gte',
          value: 1,
        },
      },
      action: {
        label: 'Export Now',
        url: '/create?action=export',
      },
      order: 5,
    },
    {
      id: 'marketplace_share',
      title: 'Share to Marketplace',
      description: 'Share your creation with the community',
      icon: '🌍',
      reward: {
        type: 'credits',
        amount: 20,
      },
      detection: {
        type: 'auto',
        condition: {
          metric: 'user.marketplace_listings_count',
          operator: 'gte',
          value: 1,
        },
      },
      optional: true,
      order: 6,
    },
  ],
  
  // 奖励
  bonus: {
    title: 'Complete All Tasks',
    description: 'Finish all tasks to earn a special bonus!',
    reward: {
      type: 'credits',
      amount: 50,
    },
    requireOptional: false, // 不需要完成可选任务
  },
  
  // 事件
  events: {
    onTaskComplete: 'checklist_task_completed',
    onAllComplete: 'checklist_all_completed',
    onBonusClaimed: 'checklist_bonus_claimed',
  },
};
```

### 5.3 任务检测逻辑

```typescript
// @core/onboarding/checklist/detector.ts

import { TaskConfig, DetectionCondition } from '../types';

export class TaskDetector {
  
  /**
   * 检测任务是否完成
   */
  async checkTask(task: TaskConfig, userId: string): Promise<boolean> {
    const { detection } = task;
    
    if (detection.type === 'manual') {
      return false; // 需要用户手动标记
    }
    
    const value = await this.getMetricValue(detection.condition.metric, userId);
    return this.evaluate(value, detection.condition);
  }
  
  /**
   * 获取指标值
   */
  private async getMetricValue(metric: string, userId: string): Promise<any> {
    const metricFetchers: Record<string, () => Promise<any>> = {
      'user.projects_count': () => this.getUserProjectsCount(userId),
      'user.ai_generations_count': () => this.getUserAIGenerationsCount(userId),
      'user.has_text_element': () => this.userHasTextElement(userId),
      'user.has_sticker_element': () => this.userHasStickerElement(userId),
      'user.exports_count': () => this.getUserExportsCount(userId),
      'user.marketplace_listings_count': () => this.getUserMarketplaceListingsCount(userId),
    };
    
    const fetcher = metricFetchers[metric];
    if (!fetcher) {
      throw new Error(`Unknown metric: ${metric}`);
    }
    
    return fetcher();
  }
  
  /**
   * 评估条件
   */
  private evaluate(value: any, condition: DetectionCondition): boolean {
    const { operator, value: expected } = condition;
    
    switch (operator) {
      case 'eq': return value === expected;
      case 'neq': return value !== expected;
      case 'gt': return value > expected;
      case 'gte': return value >= expected;
      case 'lt': return value < expected;
      case 'lte': return value <= expected;
      default: return false;
    }
  }
  
  // 具体指标获取实现...
  private async getUserProjectsCount(userId: string): Promise<number> {
    const result = await supabase
      .from('projects')
      .select('id', { count: 'exact' })
      .eq('user_id', userId)
      .eq('is_deleted', false);
    return result.count || 0;
  }
  
  // ... 其他指标
}
```

---

## 6. Feature Spotlights

### 6.1 Spotlight 类型

```
┌─────────────────────────────────────────────────────────────────┐
│                    Feature Spotlight 类型                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  类型 1: 新功能提示 (非侵入式)                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │        ┌──────────────┐                                 │   │
│  │        │ 📁 Media     │                                 │   │
│  │        └──────────────┘                                 │   │
│  │              ↑                                          │   │
│  │        ┌─────────────────────┐                          │   │
│  │        │ 💡 New!             │                          │   │
│  │        │                     │                          │   │
│  │        │ Browse 1000+ free   │                          │   │
│  │        │ stickers!           │                          │   │
│  │        │                     │                          │   │
│  │        │ [Got it]            │                          │   │
│  │        └─────────────────────┘                          │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  类型 2: 功能教育 (带图示)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │                                                    │  │   │
│  │  │  🖼 AI Image Generation                           │  │   │
│  │  │                                                    │  │   │
│  │  │  ┌────────────────────────────────────────────┐   │  │   │
│  │  │  │                                            │   │  │   │
│  │  │  │         [示意图/GIF]                        │   │  │   │
│  │  │  │                                            │   │  │   │
│  │  │  └────────────────────────────────────────────┘   │  │   │
│  │  │                                                    │  │   │
│  │  │  Simply describe what you want, and AI will       │  │   │
│  │  │  create a unique illustration for you!            │  │   │
│  │  │                                                    │  │   │
│  │  │  Example: "A happy dog playing in the park"       │  │   │
│  │  │                                                    │  │   │
│  │  │  [Try it] [Remind me later] [Don't show again]   │  │   │
│  │  │                                                    │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  类型 3: 升级提示 (触发条件: 使用受限功能)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │        ┌──────────────────┐                             │   │
│  │        │ 🔒 ZIP Export    │                             │   │
│  │        └──────────────────┘                             │   │
│  │                ↑                                         │   │
│  │        ┌───────────────────────────────┐                │   │
│  │        │ 🌟 Pro Feature                │                │   │
│  │        │                               │                │   │
│  │        │ Export as ZIP with separate   │                │   │
│  │        │ image files for each page.    │                │   │
│  │        │                               │                │   │
│  │        │ Perfect for custom printing   │                │   │
│  │        │ and advanced editing.         │                │   │
│  │        │                               │                │   │
│  │        │ [Upgrade to Pro] [Maybe later]│                │   │
│  │        └───────────────────────────────┘                │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  类型 4: 新功能发布公告                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │ 🎉 New Feature!                              [×]  │  │   │
│  │  │                                                    │  │   │
│  │  │ ┌────────────────────────────────────────────┐   │  │   │
│  │  │ │                                            │   │  │   │
│  │  │ │           [功能演示 GIF]                   │   │  │   │
│  │  │ │                                            │   │  │   │
│  │  │ └────────────────────────────────────────────┘   │  │   │
│  │  │                                                    │  │   │
│  │  │ Smart Scan is now available!                      │  │   │
│  │  │                                                    │  │   │
│  │  │ Scan handwritten text and convert it to           │  │   │
│  │  │ editable content with our new AI feature.         │  │   │
│  │  │                                                    │  │   │
│  │  │ [Try Now] [Learn More] [Dismiss]                  │  │   │
│  │  │                                                    │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Spotlight 配置

```typescript
// @business/onboarding/spotlights/index.ts

import { SpotlightConfig } from '@core/onboarding/types';

export const spotlights: SpotlightConfig[] = [
  // 媒体库介绍
  {
    key: 'media_library_intro',
    type: 'tooltip',
    target: '[data-tour="media-library"]',
    placement: 'left',
    title: '💡 New!',
    content: 'Browse 1000+ free stickers!',
    trigger: {
      event: 'media_library_opened',
      conditions: {
        showOnce: true,
      },
    },
  },
  
  // AI 图片生成介绍
  {
    key: 'ai_image_intro',
    type: 'modal',
    title: '🖼 AI Image Generation',
    content: 'Simply describe what you want, and AI will create a unique illustration for you!',
    image: '/spotlights/ai-image-demo.gif',
    example: 'Example: "A happy dog playing in the park"',
    trigger: {
      event: 'ai_generate_clicked',
      conditions: {
        showOnce: true,
        hasNotUsedFeature: ['ai_image_generation'],
      },
    },
    actions: [
      { label: 'Try it', action: 'continue' },
      { label: 'Remind me later', action: 'remind' },
      { label: "Don't show again", action: 'dismiss' },
    ],
  },
  
  // ZIP 导出 - 升级提示
  {
    key: 'zip_export_upgrade',
    type: 'upgrade',
    target: '[data-action="export-zip"]',
    placement: 'bottom',
    title: '🌟 Pro Feature',
    content: 'Export as ZIP with separate image files for each page. Perfect for custom printing and advanced editing.',
    trigger: {
      event: 'zip_export_clicked',
      conditions: {
        userTier: ['free', 'starter'],
        showEveryTime: true,
      },
    },
    actions: [
      { label: 'Upgrade to Pro', action: 'upgrade', variant: 'primary' },
      { label: 'Maybe later', action: 'dismiss' },
    ],
  },
  
  // 新功能发布
  {
    key: 'smart_scan_launch',
    type: 'announcement',
    title: '🎉 New Feature!',
    subtitle: 'Smart Scan is now available!',
    content: 'Scan handwritten text and convert it to editable content with our new AI feature.',
    image: '/spotlights/smart-scan-demo.gif',
    trigger: {
      conditions: {
        afterDate: '2026-02-01',
        showOnce: true,
        onPage: ['/dashboard', '/create'],
      },
    },
    actions: [
      { label: 'Try Now', action: 'navigate', url: '/create?feature=scan' },
      { label: 'Learn More', action: 'navigate', url: '/help/smart-scan' },
      { label: 'Dismiss', action: 'dismiss' },
    ],
  },
];
```

---

## 7. 数据结构设计

### 7.1 数据库表结构

```sql
-- ============================================================
-- 引导配置表 (存储引导定义)
-- ============================================================
CREATE TABLE onboarding_tours (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基础信息
    key VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 类型
    tour_type VARCHAR(50) NOT NULL,             -- modal, guided, spotlight, checklist
    
    -- 触发条件 (JSON)
    trigger_conditions JSONB NOT NULL,
    
    -- 步骤配置 (JSON)
    steps JSONB NOT NULL,
    
    -- 选项 (JSON)
    options JSONB DEFAULT '{}',
    
    -- 回调 (JSON)
    on_complete JSONB DEFAULT '{}',
    on_skip JSONB DEFAULT '{}',
    
    -- 状态
    enabled BOOLEAN DEFAULT true,
    
    -- 版本控制 (用于判断是否需要重新引导)
    version INTEGER DEFAULT 1,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 用户引导进度表
-- ============================================================
CREATE TABLE onboarding_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id VARCHAR(100) NOT NULL,
    tour_key VARCHAR(100) NOT NULL,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'not_started',   -- not_started, in_progress, completed, skipped
    
    -- 进度详情
    current_step INTEGER DEFAULT 0,
    completed_steps JSONB DEFAULT '[]',         -- 已完成的步骤 key 列表
    
    -- 时间戳
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    skipped_at TIMESTAMPTZ,
    
    -- 版本 (与 tour 的 version 对比)
    tour_version INTEGER DEFAULT 1,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, tour_key)
);

-- ============================================================
-- 任务清单进度表
-- ============================================================
CREATE TABLE checklist_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id VARCHAR(100) NOT NULL,
    checklist_key VARCHAR(100) NOT NULL,
    
    -- 任务状态 (JSON 数组)
    tasks JSONB DEFAULT '[]',
    -- 格式: [{taskId, completed, completedAt, rewardClaimed, claimedAt}]
    
    -- 汇总统计
    completed_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    total_credits_earned INTEGER DEFAULT 0,
    
    -- 奖励状态
    bonus_available BOOLEAN DEFAULT false,
    bonus_claimed BOOLEAN DEFAULT false,
    bonus_claimed_at TIMESTAMPTZ,
    
    -- 显示状态
    collapsed BOOLEAN DEFAULT false,
    dismissed BOOLEAN DEFAULT false,
    dismissed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, checklist_key)
);

-- ============================================================
-- Spotlight 展示记录
-- ============================================================
CREATE TABLE spotlight_impressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id VARCHAR(100) NOT NULL,
    spotlight_key VARCHAR(100) NOT NULL,
    
    -- 状态
    shown BOOLEAN DEFAULT true,
    dismissed BOOLEAN DEFAULT false,
    clicked BOOLEAN DEFAULT false,
    remind_later BOOLEAN DEFAULT false,
    remind_at TIMESTAMPTZ,
    
    -- 操作
    action_taken VARCHAR(50),                   -- continue, dismiss, upgrade, navigate, etc.
    
    -- 时间
    shown_at TIMESTAMPTZ DEFAULT NOW(),
    action_at TIMESTAMPTZ,
    
    UNIQUE(user_id, spotlight_key)
);

-- ============================================================
-- 引导分析表 (用于数据分析)
-- ============================================================
CREATE TABLE onboarding_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,            -- tour_started, tour_completed, task_completed, etc.
    
    -- 事件详情
    tour_key VARCHAR(100),
    task_id VARCHAR(100),
    spotlight_key VARCHAR(100),
    step_key VARCHAR(100),
    
    -- 额外数据
    metadata JSONB DEFAULT '{}',
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_progress_user ON onboarding_progress(user_id);
CREATE INDEX idx_progress_status ON onboarding_progress(status);
CREATE INDEX idx_checklist_user ON checklist_progress(user_id);
CREATE INDEX idx_spotlight_user ON spotlight_impressions(user_id);
CREATE INDEX idx_analytics_user ON onboarding_analytics(user_id);
CREATE INDEX idx_analytics_event ON onboarding_analytics(event_type);
CREATE INDEX idx_analytics_time ON onboarding_analytics(created_at);
```

### 7.2 TypeScript 类型定义

```typescript
// @core/onboarding/types.ts

// ==================== 通用类型 ====================

export type TourType = 'modal' | 'guided' | 'spotlight' | 'checklist';
export type TourStatus = 'not_started' | 'in_progress' | 'completed' | 'skipped';
export type SpotlightType = 'tooltip' | 'modal' | 'upgrade' | 'announcement';

// ==================== 触发条件 ====================

export interface TriggerConditions {
  // 用户条件
  isNewUser?: boolean;
  newUserDays?: number;
  userTier?: string[];
  
  // 引导条件
  hasCompletedTour?: string[];
  hasNotCompletedTour?: string[];
  
  // 功能条件
  hasUsedFeature?: string[];
  hasNotUsedFeature?: string[];
  
  // 页面条件
  onPage?: string[];
  
  // 时间条件
  afterDate?: string;
  beforeDate?: string;
  
  // 显示频率
  showOnce?: boolean;
  showEveryTime?: boolean;
}

export interface TourTrigger {
  type: 'auto' | 'manual' | 'event';
  event?: string;
  conditions: TriggerConditions;
}

// ==================== 步骤配置 ====================

export interface TourStep {
  key: string;
  
  // 目标 (guided tour)
  target?: string;
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'center';
  
  // 内容
  title: string;
  content: string;
  tip?: string;
  image?: string;
  
  // 高亮效果
  highlight?: {
    animation?: 'pulse' | 'glow' | 'none';
    color?: string;
    padding?: number;
  };
  
  // 操作按钮
  actions?: {
    primary?: { label: string; action: string };
    secondary?: { label: string; action: string };
  };
  
  // 条件显示
  condition?: {
    feature?: string;
    tier?: string[];
  };
}

// ==================== 引导配置 ====================

export interface TourConfig {
  key: string;
  name: string;
  version: number;
  
  trigger: TourTrigger;
  tourType: TourType;
  steps: TourStep[];
  
  options?: {
    continuous?: boolean;
    showProgress?: boolean;
    showSkipButton?: boolean;
    allowSkip?: boolean;
    spotlightClicks?: boolean;
    backdropClick?: boolean;
    styles?: any;
  };
  
  onComplete?: {
    markAsComplete?: boolean;
    redirect?: string;
    trackEvent?: string;
  };
  
  onSkip?: {
    markAsComplete?: boolean;
    redirect?: string;
    trackEvent?: string;
  };
}

// ==================== 任务清单 ====================

export interface TaskReward {
  type: 'credits' | 'badge' | 'feature';
  amount?: number;
  value?: string;
}

export interface TaskDetection {
  type: 'auto' | 'manual';
  condition?: {
    metric: string;
    operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte';
    value: any;
  };
}

export interface TaskConfig {
  id: string;
  title: string;
  description?: string;
  icon?: string;
  reward: TaskReward;
  detection: TaskDetection;
  action?: {
    label: string;
    url: string;
  };
  optional?: boolean;
  order: number;
}

export interface ChecklistConfig {
  key: string;
  name: string;
  version: number;
  
  display: {
    position: 'dashboard-sidebar' | 'floating' | 'bottom-banner';
    showFor: TriggerConditions;
    collapsible?: boolean;
    dismissible?: boolean;
  };
  
  tasks: TaskConfig[];
  
  bonus?: {
    title: string;
    description?: string;
    reward: TaskReward;
    requireOptional?: boolean;
  };
  
  events?: {
    onTaskComplete?: string;
    onAllComplete?: string;
    onBonusClaimed?: string;
  };
}

// ==================== 进度状态 ====================

export interface TourProgress {
  tourKey: string;
  status: TourStatus;
  currentStep: number;
  completedSteps: string[];
  startedAt?: Date;
  completedAt?: Date;
  tourVersion: number;
}

export interface TaskProgress {
  taskId: string;
  completed: boolean;
  completedAt?: Date;
  rewardClaimed: boolean;
  claimedAt?: Date;
}

export interface ChecklistProgress {
  checklistKey: string;
  tasks: TaskProgress[];
  completedCount: number;
  totalCount: number;
  percentage: number;
  totalCreditsEarned: number;
  bonusAvailable: boolean;
  bonusClaimed: boolean;
  collapsed: boolean;
  dismissed: boolean;
}
```

---

## 8. 后端实现

### 8.1 目录结构

```
domains/platform/onboarding/
├── __init__.py
├── entities.py                 # 实体定义 (<150 行)
├── value_objects.py            # 值对象 (<100 行)
├── repository.py               # 仓储接口 (<100 行)
├── service.py                  # 领域服务 (<250 行)
└── exceptions.py               # 异常 (<50 行)

application/commands/onboarding/
├── __init__.py
├── start_tour.py               # 开始引导 (<80 行)
├── complete_tour.py            # 完成引导 (<80 行)
├── complete_task.py            # 完成任务 (<100 行)
└── claim_reward.py             # 领取奖励 (<100 行)

application/queries/onboarding/
├── __init__.py
├── get_available_tours.py      # 获取可用引导 (<80 行)
├── get_tour_progress.py        # 获取引导进度 (<60 行)
└── get_checklist_progress.py   # 获取清单进度 (<80 行)

api/routers/
└── onboarding.py               # API 路由 (<200 行)
```

### 8.2 API 路由

```python
# api/routers/onboarding.py

from fastapi import APIRouter, Depends
from typing import List, Optional
from pydantic import BaseModel

from application.commands.onboarding import (
    StartTourCommand, StartTourHandler,
    CompleteTourCommand, CompleteTourHandler,
    CompleteTaskCommand, CompleteTaskHandler,
    ClaimRewardCommand, ClaimRewardHandler,
)
from application.queries.onboarding import (
    GetAvailableToursQuery, GetAvailableToursHandler,
    GetChecklistProgressQuery, GetChecklistProgressHandler,
)
from dependencies import get_current_user

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


# ==================== Tours ====================

@router.get("/tours")
async def get_available_tours(
    user = Depends(get_current_user),
    handler: GetAvailableToursHandler = Depends()
):
    """获取用户可用的引导列表"""
    query = GetAvailableToursQuery(user_id=user["id"])
    return await handler.handle(query)


@router.get("/tours/{tour_key}")
async def get_tour(
    tour_key: str,
    user = Depends(get_current_user),
    handler = Depends()
):
    """获取单个引导配置"""
    pass


@router.get("/tours/{tour_key}/progress")
async def get_tour_progress(
    tour_key: str,
    user = Depends(get_current_user),
    handler = Depends()
):
    """获取引导进度"""
    pass


@router.post("/tours/{tour_key}/start")
async def start_tour(
    tour_key: str,
    user = Depends(get_current_user),
    handler: StartTourHandler = Depends()
):
    """开始引导"""
    command = StartTourCommand(user_id=user["id"], tour_key=tour_key)
    return await handler.handle(command)


@router.post("/tours/{tour_key}/step/{step_key}/complete")
async def complete_step(
    tour_key: str,
    step_key: str,
    user = Depends(get_current_user),
    handler = Depends()
):
    """完成引导步骤"""
    pass


@router.post("/tours/{tour_key}/complete")
async def complete_tour(
    tour_key: str,
    user = Depends(get_current_user),
    handler: CompleteTourHandler = Depends()
):
    """完成引导"""
    command = CompleteTourCommand(user_id=user["id"], tour_key=tour_key)
    return await handler.handle(command)


@router.post("/tours/{tour_key}/skip")
async def skip_tour(
    tour_key: str,
    user = Depends(get_current_user),
    handler = Depends()
):
    """跳过引导"""
    pass


# ==================== Checklist ====================

@router.get("/checklist")
async def get_checklist(
    user = Depends(get_current_user),
    handler: GetChecklistProgressHandler = Depends()
):
    """获取任务清单状态"""
    query = GetChecklistProgressQuery(user_id=user["id"])
    return await handler.handle(query)


@router.post("/checklist/tasks/{task_id}/check")
async def check_task(
    task_id: str,
    user = Depends(get_current_user),
    handler = Depends()
):
    """检查任务是否完成"""
    pass


@router.post("/checklist/tasks/{task_id}/claim")
async def claim_task_reward(
    task_id: str,
    user = Depends(get_current_user),
    handler: ClaimRewardHandler = Depends()
):
    """领取任务奖励"""
    command = ClaimRewardCommand(user_id=user["id"], task_id=task_id)
    return await handler.handle(command)


@router.post("/checklist/bonus/claim")
async def claim_bonus(
    user = Depends(get_current_user),
    handler = Depends()
):
    """领取完成奖励"""
    pass


@router.post("/checklist/collapse")
async def toggle_collapse(
    collapsed: bool,
    user = Depends(get_current_user),
    handler = Depends()
):
    """切换清单折叠状态"""
    pass


# ==================== Spotlight ====================

@router.post("/spotlight/{key}/dismiss")
async def dismiss_spotlight(
    key: str,
    user = Depends(get_current_user),
    handler = Depends()
):
    """关闭 Spotlight"""
    pass


@router.post("/spotlight/{key}/remind")
async def remind_spotlight(
    key: str,
    remind_hours: int = 24,
    user = Depends(get_current_user),
    handler = Depends()
):
    """稍后提醒"""
    pass


# ==================== Analytics ====================

@router.post("/analytics/event")
async def track_event(
    event_type: str,
    metadata: Optional[dict] = None,
    user = Depends(get_current_user),
    handler = Depends()
):
    """追踪引导事件"""
    pass
```

---

## 9. 前端实现

### 9.1 目录结构

```
@core/onboarding/
├── index.ts                        # 导出
├── types.ts                        # 类型定义 (<200 行)
├── context.tsx                     # OnboardingProvider (<300 行)
├── hooks.ts                        # Hooks (<150 行)
├── api.ts                          # API 服务 (<100 行)
│
├── components/
│   ├── index.ts
│   │
│   ├── tour/
│   │   ├── TourProvider.tsx       # Joyride 封装 (<200 行)
│   │   ├── TourTooltip.tsx        # 自定义 Tooltip (<150 行)
│   │   ├── TourModal.tsx          # Modal Tour (<200 行)
│   │   └── TourProgress.tsx       # 进度指示器 (<80 行)
│   │
│   ├── checklist/
│   │   ├── Checklist.tsx          # 主组件 (<200 行)
│   │   ├── ChecklistItem.tsx      # 单个任务 (<100 行)
│   │   ├── ChecklistProgress.tsx  # 进度条 (<80 行)
│   │   └── ChecklistBonus.tsx     # 奖励区域 (<80 行)
│   │
│   └── spotlight/
│       ├── Spotlight.tsx          # 基础组件 (<150 行)
│       ├── SpotlightTooltip.tsx   # 小气泡 (<80 行)
│       ├── SpotlightModal.tsx     # 弹窗式 (<120 行)
│       └── SpotlightUpgrade.tsx   # 升级提示 (<100 行)
│
└── utils/
    ├── triggers.ts                 # 触发条件判断 (<100 行)
    └── storage.ts                  # 本地存储 (<50 行)

@business/onboarding/
├── tours/
│   ├── index.ts
│   ├── welcomeTour.ts
│   └── editorTour.ts
├── checklists/
│   ├── index.ts
│   └── gettingStarted.ts
└── spotlights/
    └── index.ts
```

### 9.2 OnboardingProvider

```typescript
// @core/onboarding/context.tsx

"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from 'react';
import Joyride, { CallBackProps, STATUS, EVENTS } from 'react-joyride';
import { useAuth } from '@clerk/nextjs';
import { usePathname } from 'next/navigation';

import {
  TourConfig,
  TourProgress,
  ChecklistProgress,
  TourStatus,
} from './types';
import { onboardingApi } from './api';
import { TourTooltip } from './components/tour/TourTooltip';
import { TourModal } from './components/tour/TourModal';
import { shouldTrigger } from './utils/triggers';

// ==================== Context Type ====================

interface OnboardingContextType {
  // 状态
  isLoading: boolean;
  
  // Tour
  activeTour: TourConfig | null;
  tourProgress: TourProgress | null;
  startTour: (tourKey: string) => Promise<void>;
  skipTour: () => Promise<void>;
  
  // Checklist
  checklistProgress: ChecklistProgress | null;
  completeTask: (taskId: string) => Promise<void>;
  claimReward: (taskId: string) => Promise<void>;
  claimBonus: () => Promise<void>;
  toggleChecklist: () => void;
  
  // Spotlight
  dismissSpotlight: (key: string) => Promise<void>;
  shouldShowSpotlight: (key: string) => boolean;
  
  // 帮助菜单
  availableTours: TourConfig[];
  restartTour: (tourKey: string) => Promise<void>;
}

const OnboardingContext = createContext<OnboardingContextType | undefined>(undefined);

// ==================== Provider ====================

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const { userId, isSignedIn } = useAuth();
  const pathname = usePathname();
  
  // 状态
  const [isLoading, setIsLoading] = useState(true);
  const [availableTours, setAvailableTours] = useState<TourConfig[]>([]);
  const [activeTour, setActiveTour] = useState<TourConfig | null>(null);
  const [tourProgress, setTourProgress] = useState<TourProgress | null>(null);
  const [runTour, setRunTour] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [checklistProgress, setChecklistProgress] = useState<ChecklistProgress | null>(null);
  const [dismissedSpotlights, setDismissedSpotlights] = useState<Set<string>>(new Set());
  
  // ==================== 初始化 ====================
  
  useEffect(() => {
    if (!isSignedIn || !userId) {
      setIsLoading(false);
      return;
    }
    
    const init = async () => {
      setIsLoading(true);
      try {
        // 获取可用引导
        const { tours } = await onboardingApi.getAvailableTours();
        setAvailableTours(tours);
        
        // 检查自动触发的引导
        const autoTour = tours.find(t => 
          t.trigger.type === 'auto' && 
          shouldTrigger(t.trigger.conditions, { pathname, userId })
        );
        
        if (autoTour) {
          await startTourInternal(autoTour);
        }
        
        // 获取 Checklist
        const { progress } = await onboardingApi.getChecklistProgress();
        setChecklistProgress(progress);
        
        // 获取已关闭的 Spotlight
        const dismissed = await onboardingApi.getDismissedSpotlights();
        setDismissedSpotlights(new Set(dismissed));
        
      } catch (error) {
        console.error('Failed to init onboarding:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    init();
  }, [isSignedIn, userId]);
  
  // 页面变化时检查触发条件
  useEffect(() => {
    if (!isSignedIn || activeTour || isLoading) return;
    
    const pageTriggeredTour = availableTours.find(t =>
      t.trigger.type === 'auto' &&
      t.trigger.conditions.onPage?.some(p => pathname.startsWith(p)) &&
      shouldTrigger(t.trigger.conditions, { pathname, userId })
    );
    
    if (pageTriggeredTour) {
      startTourInternal(pageTriggeredTour);
    }
  }, [pathname, availableTours, isSignedIn, activeTour, isLoading]);
  
  // ==================== Tour 操作 ====================
  
  const startTourInternal = async (tour: TourConfig) => {
    setActiveTour(tour);
    setStepIndex(0);
    
    if (tour.tourType === 'guided') {
      setRunTour(true);
    }
    
    await onboardingApi.startTour(tour.key);
  };
  
  const startTour = useCallback(async (tourKey: string) => {
    const tour = availableTours.find(t => t.key === tourKey);
    if (tour) {
      await startTourInternal(tour);
    } else {
      // 从 API 获取
      const { tour: fetchedTour } = await onboardingApi.getTour(tourKey);
      await startTourInternal(fetchedTour);
    }
  }, [availableTours]);
  
  const skipTour = useCallback(async () => {
    if (!activeTour) return;
    
    await onboardingApi.skipTour(activeTour.key);
    setRunTour(false);
    setActiveTour(null);
    
    if (activeTour.onSkip?.redirect) {
      window.location.href = activeTour.onSkip.redirect;
    }
  }, [activeTour]);
  
  const completeTour = useCallback(async () => {
    if (!activeTour) return;
    
    await onboardingApi.completeTour(activeTour.key);
    setRunTour(false);
    
    if (activeTour.onComplete?.redirect) {
      window.location.href = activeTour.onComplete.redirect;
    }
    
    setActiveTour(null);
  }, [activeTour]);
  
  const restartTour = useCallback(async (tourKey: string) => {
    await onboardingApi.resetTour(tourKey);
    await startTour(tourKey);
  }, [startTour]);
  
  // Joyride 回调
  const handleJoyrideCallback = useCallback(async (data: CallBackProps) => {
    const { status, index, type } = data;
    
    if (status === STATUS.FINISHED) {
      await completeTour();
    } else if (status === STATUS.SKIPPED) {
      await skipTour();
    }
    
    if (type === EVENTS.STEP_AFTER) {
      setStepIndex(index + 1);
    }
  }, [completeTour, skipTour]);
  
  // ==================== Checklist 操作 ====================
  
  const refreshChecklist = useCallback(async () => {
    const { progress } = await onboardingApi.getChecklistProgress();
    setChecklistProgress(progress);
  }, []);
  
  const completeTask = useCallback(async (taskId: string) => {
    await onboardingApi.checkTask(taskId);
    await refreshChecklist();
  }, [refreshChecklist]);
  
  const claimReward = useCallback(async (taskId: string) => {
    await onboardingApi.claimTaskReward(taskId);
    await refreshChecklist();
  }, [refreshChecklist]);
  
  const claimBonus = useCallback(async () => {
    await onboardingApi.claimBonus();
    await refreshChecklist();
  }, [refreshChecklist]);
  
  const toggleChecklist = useCallback(() => {
    if (checklistProgress) {
      const newCollapsed = !checklistProgress.collapsed;
      setChecklistProgress({ ...checklistProgress, collapsed: newCollapsed });
      onboardingApi.toggleCollapse(newCollapsed);
    }
  }, [checklistProgress]);
  
  // ==================== Spotlight 操作 ====================
  
  const dismissSpotlight = useCallback(async (key: string) => {
    await onboardingApi.dismissSpotlight(key);
    setDismissedSpotlights(prev => new Set([...prev, key]));
  }, []);
  
  const shouldShowSpotlight = useCallback((key: string) => {
    return !dismissedSpotlights.has(key);
  }, [dismissedSpotlights]);
  
  // ==================== Context Value ====================
  
  const value = useMemo<OnboardingContextType>(() => ({
    isLoading,
    activeTour,
    tourProgress,
    startTour,
    skipTour,
    checklistProgress,
    completeTask,
    claimReward,
    claimBonus,
    toggleChecklist,
    dismissSpotlight,
    shouldShowSpotlight,
    availableTours,
    restartTour,
  }), [
    isLoading,
    activeTour,
    tourProgress,
    startTour,
    skipTour,
    checklistProgress,
    completeTask,
    claimReward,
    claimBonus,
    toggleChecklist,
    dismissSpotlight,
    shouldShowSpotlight,
    availableTours,
    restartTour,
  ]);
  
  return (
    <OnboardingContext.Provider value={value}>
      {children}
      
      {/* Modal Tour */}
      {activeTour && activeTour.tourType === 'modal' && (
        <TourModal
          tour={activeTour}
          stepIndex={stepIndex}
          onNext={() => setStepIndex(i => i + 1)}
          onBack={() => setStepIndex(i => i - 1)}
          onSkip={skipTour}
          onComplete={completeTour}
        />
      )}
      
      {/* Guided Tour (Joyride) */}
      {activeTour && activeTour.tourType === 'guided' && (
        <Joyride
          steps={activeTour.steps.map(s => ({
            target: s.target || 'body',
            content: s.content,
            title: s.title,
            placement: s.placement,
            disableBeacon: true,
          }))}
          run={runTour}
          stepIndex={stepIndex}
          continuous
          showProgress
          showSkipButton
          callback={handleJoyrideCallback}
          tooltipComponent={TourTooltip}
          styles={{
            options: {
              primaryColor: '#4F46E5',
              zIndex: 10000,
            },
          }}
          {...activeTour.options}
        />
      )}
    </OnboardingContext.Provider>
  );
}

// ==================== Hook ====================

export function useOnboarding() {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error('useOnboarding must be used within OnboardingProvider');
  }
  return context;
}
```

### 9.3 Checklist 组件

```typescript
// @core/onboarding/components/checklist/Checklist.tsx

"use client";

import React from 'react';
import { useOnboarding } from '../../context';
import { ChecklistItem } from './ChecklistItem';
import { ChecklistProgress } from './ChecklistProgress';
import { ChecklistBonus } from './ChecklistBonus';
import { cn } from '@core/utils';
import { ChevronUp, ChevronDown, Gift } from 'lucide-react';

export function Checklist() {
  const {
    checklistProgress,
    completeTask,
    claimReward,
    claimBonus,
    toggleChecklist,
  } = useOnboarding();
  
  if (!checklistProgress || checklistProgress.dismissed) {
    return null;
  }
  
  const { tasks, percentage, totalCreditsEarned, bonusAvailable, bonusClaimed, collapsed } = checklistProgress;
  const allComplete = percentage === 100;
  
  return (
    <div className={cn(
      "bg-white rounded-lg shadow-sm border border-gray-200",
      "transition-all duration-300"
    )}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={toggleChecklist}
      >
        <div className="flex items-center gap-3">
          <div className="text-2xl">🚀</div>
          <div>
            <h3 className="font-semibold text-gray-900">
              {allComplete ? '🎉 All Done!' : 'Getting Started'}
            </h3>
            <ChecklistProgress percentage={percentage} />
          </div>
        </div>
        
        <button className="text-gray-400 hover:text-gray-600">
          {collapsed ? <ChevronDown size={20} /> : <ChevronUp size={20} />}
        </button>
      </div>
      
      {/* Content */}
      {!collapsed && (
        <div className="px-4 pb-4 space-y-3">
          {!allComplete && (
            <p className="text-sm text-gray-500">
              Complete all tasks to earn bonus credits! 🎁
            </p>
          )}
          
          {/* Task List */}
          <div className="space-y-2">
            {tasks.map((task) => (
              <ChecklistItem
                key={task.taskId}
                task={task}
                onComplete={() => completeTask(task.taskId)}
                onClaim={() => claimReward(task.taskId)}
              />
            ))}
          </div>
          
          {/* Bonus Section */}
          <ChecklistBonus
            available={bonusAvailable}
            claimed={bonusClaimed}
            onClaim={claimBonus}
          />
          
          {/* Summary */}
          <div className="flex items-center justify-between pt-3 border-t text-sm">
            <span className="text-gray-500">You've earned:</span>
            <span className="font-semibold text-indigo-600">{totalCreditsEarned} 💎</span>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 10. 实施计划

### 10.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────┐
│                    实施计划                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: 基础设施 (2 天)                                        │
│  ├─ 数据库表创建                                                 │
│  ├─ 类型定义                                                    │
│  ├─ 后端 API 框架                                                │
│  ├─ OnboardingProvider 基础                                     │
│  └─ 测试环境配置                                                 │
│                                                                 │
│  Phase 2: Welcome Tour (2 天)                                   │
│  ├─ TourModal 组件                                              │
│  ├─ 欢迎引导步骤配置                                             │
│  ├─ 触发逻辑实现                                                 │
│  ├─ 完成/跳过追踪                                                │
│  └─ 动画效果 (Lottie)                                           │
│                                                                 │
│  Phase 3: Editor Tour (2 天)                                    │
│  ├─ Joyride 集成                                                │
│  ├─ 自定义 Tooltip 组件                                         │
│  ├─ 步骤配置                                                    │
│  ├─ 添加 data-tour 属性到编辑器组件                              │
│  └─ 触发逻辑                                                    │
│                                                                 │
│  Phase 4: Checklist (2 天)                                      │
│  ├─ Checklist 组件                                              │
│  ├─ ChecklistItem 组件                                          │
│  ├─ 任务检测逻辑                                                 │
│  ├─ 奖励发放逻辑                                                 │
│  └─ 进度持久化                                                  │
│                                                                 │
│  Phase 5: Spotlight + 优化 (1 天)                               │
│  ├─ Spotlight 组件系列                                          │
│  ├─ 触发规则实现                                                 │
│  ├─ 显示记录                                                    │
│  └─ 整体测试和优化                                               │
│                                                                 │
│  总计: 9 天                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 验收清单

| 功能 | 验收标准 | 测试方法 |
|------|----------|----------|
| **Welcome Tour** | 新用户登录后自动触发 | 创建新账户测试 |
| | 5 步引导完整展示 | 手动点击 |
| | 跳过功能正常 | 点击跳过 |
| | 完成后不再触发 | 刷新页面 |
| **Editor Tour** | 首次进入编辑器触发 | 导航到 /create |
| | 8 个步骤正确高亮 | 逐步点击 |
| | 步骤可前进后退 | 点击 Back/Next |
| | 完成后记录状态 | 刷新页面 |
| **Checklist** | Dashboard 显示清单 | 访问 Dashboard |
| | 任务自动检测完成 | 执行对应操作 |
| | 奖励正确发放 | 检查积分余额 |
| | 进度百分比正确 | 完成部分任务 |
| | 折叠/展开正常 | 点击切换 |
| **Spotlight** | 首次使用功能时触发 | 首次点击功能 |
| | 关闭后不再显示 | 刷新页面 |
| | 升级提示正确显示 | Free 用户点击 Pro 功能 |
| **帮助菜单** | 可重新触发引导 | 从帮助菜单启动 |
| **多语言** | 中英文正确显示 | 切换语言 |
| **分析** | 事件正确追踪 | 查看数据库/分析面板 |

### 10.3 依赖项

```json
{
  "dependencies": {
    "react-joyride": "^2.8.0",
    "lottie-react": "^2.4.0"
  }
}
```

---

**Onboarding 系统详细设计完成！**
