# 无障碍设计规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/accessibility/

---

## 概述

无障碍设计 (A11y) 规范，确保产品对所有用户可用。

---

## WCAG 2.1 合规

目标: **AA 级别**

### 核心原则

1. **可感知** - 信息可被感知
2. **可操作** - 界面可操作
3. **可理解** - 内容可理解
4. **健壮性** - 兼容辅助技术

---

## 颜色对比度

| 元素 | 最小对比度 |
|------|----------|
| 正文文本 | 4.5:1 |
| 大号文本 (18px+) | 3:1 |
| UI 组件 | 3:1 |

### 检查工具

- Chrome DevTools
- axe DevTools
- Contrast Checker

---

## 键盘导航

### 焦点管理

```css
/* 可见焦点环 */
:focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}

/* 隐藏鼠标焦点 */
:focus:not(:focus-visible) {
  outline: none;
}
```

### Tab 顺序

- 逻辑顺序 (从上到下，从左到右)
- 跳过装饰元素
- 模态框内焦点陷阱

---

## 屏幕阅读器

### ARIA 标签

```html
<!-- 按钮描述 -->
<button aria-label="关闭对话框">×</button>

<!-- 区域标识 -->
<nav aria-label="主导航">...</nav>

<!-- 实时区域 -->
<div role="alert" aria-live="polite">操作成功</div>
```

### 语义化 HTML

- 使用正确的标题层级 (h1-h6)
- 使用 `<button>` 而非 `<div onclick>`
- 使用 `<main>`, `<nav>`, `<aside>` 等语义标签

---

## 相关文档

- [设计 Token - 颜色](../tokens/colors.md)
- [WCAG 2.1 指南](https://www.w3.org/WAI/WCAG21/quickref/)
