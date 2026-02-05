# 响应式设计模式

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/responsive/

---

## 概述

响应式设计的核心模式和规范。

---

## 断点系统

| 断点 | 宽度 | 设备 |
|------|------|------|
| xs | < 640px | 手机竖屏 |
| sm | ≥ 640px | 手机横屏 |
| **md** | **≥ 768px** | **平板/桌面分界** |
| lg | ≥ 1024px | 桌面 |
| xl | ≥ 1280px | 大屏桌面 |

---

## Mobile-First 原则

```css
/* 默认样式 = 移动端 */
.element {
  padding: 16px;
  flex-direction: column;
}

/* 桌面端增强 */
@media (min-width: 768px) {
  .element {
    padding: 24px;
    flex-direction: row;
  }
}
```

---

## 布局适配

### 页面布局

| 布局 | Mobile | Desktop |
|------|--------|---------|
| 导航 | 底部导航 | 顶部导航 |
| 侧边栏 | Sheet 弹出 | 固定显示 |
| 网格 | 1-2 列 | 3-4 列 |

### 组件适配

| 组件 | Mobile | Desktop |
|------|--------|---------|
| Dialog | 全屏 Sheet | 居中弹窗 |
| Menu | 底部 Sheet | Dropdown |
| Table | 卡片列表 | 表格 |

---

## 设备检测

```typescript
// 使用 CSS 媒体查询优先
// JS 检测仅用于功能差异

const isMobile = window.matchMedia('(max-width: 767px)').matches;
```

---

## 相关文档

- [响应式设计指南](../../../../decodables-fe/docs/main/responsive-design-guide.md)
- [布局组件](../components/layout.md)
