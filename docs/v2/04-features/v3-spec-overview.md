# V3 Specification System Overview

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-17  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 规格变更与版本演进缺少统一摘要
- 目标与非目标: 目标是提供 v3 规格概览；非目标是替代详细设计文档

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- V3 规范的目标与覆盖范围
- CED/PED 文档结构与治理方式

## 影响范围

- 相关模块: 前端规范与组件体系
- 相关文档: `docs/v2/02-standards/frontend-development-guide.md`

## 证据与验证

- 关键证据来源：`decodables-fe/docs/tmp/refactor/v3/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |

## 1. What is V3 Specification?

V3 规范是 Make Decodables 前端组件和页面的现代化文档系统，为所有 UI 元素提供统一、完整的技术规范。

### 1.1 Core Objectives

1. **响应式优先**: 所有组件支持 Desktop/Tablet/Mobile 三断点
2. **TypeScript 强制**: 明确的接口定义
3. **系统集成**: 与 9 个核心系统规范交叉引用
4. **可执行性**: 每个规范包含详细重构计划

### 1.2 Coverage Summary

| 类型 | 文件数 | 覆盖率 |
|------|--------|--------|
| **CED (组件)** | 24 | 100% |
| **PED (页面)** | 11 (覆盖 25 原始页面) | 100% |
| **总计** | 35 | 100% |

---

## 2. Document Structure

### 2.1 CED (Component Engineering Document)

每个 CED 包含以下章节:

| 章节 | 内容 |
|------|------|
| **1. Overview** | 组件目标、用户价值、使用场景 |
| **2. Business Logic** | 核心流程、验证规则、边界情况 |
| **3. UX/UI Specs** | Desktop/Tablet/Mobile/Foldable 布局 |
| **4. Technical Architecture** | TypeScript 接口、状态管理、API 集成 |
| **5. Refactoring Plan** | 分步骤实施计划 |
| **6. Appendix** | 相关文档、变更日志 |

### 2.2 PED (Page Engineering Document)

每个 PED 包含以下章节:

| 章节 | 内容 |
|------|------|
| **1. Overview** | 页面目标、路由、权限控制 |
| **2. Business Logic** | 数据流、验证、状态管理 |
| **3. UX/UI Specs** | 响应式布局策略 |
| **4. Technical Architecture** | 目录结构、API 集成、性能优化 |
| **5. Refactoring Plan** | 分阶段实施计划 |
| **6. Appendix** | 相关 CED 引用 |

---

## 3. V3 Document Inventory

### 3.1 Components (24 files)

```
docs/tmp/refactor/v3/components/
├── UI Foundations
│   ├── CED-Dialog-v3.md
│   ├── CED-ConfirmDialog-v3.md
│   ├── CED-Toast-v3.md
│   ├── CED-Popover-v3.md
│   └── CED-DropdownMenu-v3.md
│
├── Navigation & Layout
│   ├── CED-Navbar-v3.md
│   ├── CED-Footer-v3.md
│   ├── CED-BottomNavbar-v3.md
│   ├── CED-MobileMenu-v3.md
│   ├── CED-Logo-v3.md
│   ├── CED-AnnouncementBar-v3.md
│   ├── CED-FloatingCTA-v3.md
│   ├── CED-SupportButton-v3.md
│   └── CED-NotificationPopover-v3.md
│
├── Feature Modals
│   ├── CED-CreateProjectModal-v3.md
│   ├── CED-PreviewModal-v3.md
│   ├── CED-PublishDialog-v3.md
│   ├── CED-SmartScanDialog-v3.md
│   ├── CED-UpgradeModal-v3.md
│   ├── CED-OutOfCreditsModal-v3.md
│   ├── CED-CreditsBreakdownDialog-v3.md
│   └── CED-ClerkBillingPage-v3.md
│
└── AI Modals
    ├── CED-AIDesignPagesModal-v3.md
    └── CED-AIImageModal-v3.md
```

### 3.2 Pages (11 files)

```
docs/tmp/refactor/v3/pages/
├── core/
│   ├── PED-Dashboard-v3.md
│   ├── PED-Editor-v3.md
│   └── PED-Marketplace-v3.md
│
├── admin/
│   └── PED-Admin-v3.md (covers 7 original admin pages)
│
├── user-flow/
│   ├── PED-Auth-v3.md (SignIn + SignUp)
│   ├── PED-Landing-v3.md
│   ├── PED-Notifications-v3.md
│   ├── PED-Profile-v3.md (Mobile-only)
│   ├── PED-Settings-v3.md
│   └── PED-TransactionHistory-v3.md
│
└── static/
    └── PED-StaticPages-v3.md (covers 9 static pages)
```

---

## 4. Responsive Breakpoints

所有 V3 文档遵循统一的响应式断点:

| Breakpoint | Width | Tailwind | 用途 |
|------------|-------|----------|------|
| **Mobile** | <768px | `default` | 手机 |
| **Tablet** | 768-1023px | `md:` | 平板 |
| **Desktop** | ≥1024px | `lg:` | 桌面 |

### 4.1 Foldable/Adaptive Support

| 模式 | 说明 |
|------|------|
| **Folded** | 折叠状态，使用 Mobile 布局 |
| **Unfolded** | 展开状态，使用 Tablet/Desktop 布局 |
| **Flex** | 半折叠状态，上下分屏 |

---

## 5. System Integration

V3 文档与以下 9 个系统规范交叉引用:

| # | System | Document | 影响范围 |
|---|--------|----------|----------|
| 1 | Feature Flags | `docs/shared/feature-flag-design.md` | 所有功能开关 |
| 2 | Onboarding | `docs/shared/onboarding-design.md` | Dashboard, Editor |
| 3 | Tier Permissions | `docs/shared/tier-permissions.md` | UpgradeModal, 所有受限功能 |
| 4 | Articles CMS | `docs/shared/articles-system-design.md` | Manual, News, Admin |
| 5 | Static Pages | `docs/shared/static-pages-cms-design.md` | Legal pages |
| 6 | Canvas Schema | `docs/shared/canvas-data-schema.md` | Editor |
| 7 | Asset Categories | `docs/shared/asset-category-design.md` | Editor, MediaLibrary |
| 8 | Theme System | `docs/shared/theme-system-design.md` | Dashboard, Admin |
| 9 | Analytics | `docs/shared/analytics-system-design.md` | All pages |

---

## 6. Code Refactoring Plan

基于 V3 规范，代码重构计划已生成:

| 维度 | 工作量 |
|------|--------|
| 组件重构 | 31.25h |
| 页面重构 | 58.50h |
| **总计** | **89.75h** |

详见: `docs/tmp/refactor/CODE-REFACTOR-PLAN.md`

---

## 7. Quality Checklist

每个 V3 文档必须满足:

- [ ] Desktop/Tablet/Mobile 三断点布局
- [ ] Foldable/Adaptive 支持
- [ ] TypeScript 接口定义
- [ ] 系统规范交叉引用
- [ ] 设计 Token 使用 (无硬编码颜色/尺寸)
- [ ] 重构计划

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/v2/02-standards/responsive-design-guide.md` | 响应式设计规范 |
| `docs/v2/02-standards/design-system.md` | 设计系统 |
| `docs/v2/02-standards/frontend-development-guide.md` | 前端开发规范 |
| `docs/tmp/refactor/CODE-REFACTOR-PLAN.md` | 代码重构计划 |

---

## 9. Change Log

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-17 | Initial documentation based on completed V3 modernization |

---

**END OF V3 OVERVIEW**
