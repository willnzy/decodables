# 前端开发规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **对应代码**: `decodables-fe/`

---

## 概述

前端开发规范，基于 Next.js 16 + React 19 + TypeScript。

---

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Next.js | 16.1.1 | 框架 (App Router) |
| React | 19.2.3 | UI 库 |
| TypeScript | 5.9 | 类型系统 |
| Zustand | 5.0.9 | 状态管理 |
| Fabric.js | 5.3.0 | 画布引擎 |

---

## 目录结构

```
app/          → Next.js 页面
@core/        → 框架层（100% 复用）
@shared/      → 共享层（auth/analytics）
@business/    → 业务层（stores/services/hooks）
```

---

## 开发规范

### TypeScript 强制要求

- 所有新代码使用 `.tsx`/`.ts`
- 旧 `.js`/`.jsx` 文件修改时逐步迁移

### 响应式设计

- Mobile-First 实现
- CSS 优先（Tailwind 类名）
- 断点分界: md (768px)

### 状态管理

- 使用 Zustand 拆分式 Store
- 按功能域划分

---

## 详细规范

- [frontend/ 详细规范](./frontend/)
- [响应式设计指南](../../../../decodables-fe/docs/main/responsive-design-guide.md)
- [设计系统](../../../03-design/)
