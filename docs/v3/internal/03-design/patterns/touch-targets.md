# 触摸目标规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/interaction/TOUCH-TARGETS

---

## 概述

移动端触摸目标的设计规范。

---

## 最小尺寸

| 元素 | 最小尺寸 | 推荐尺寸 |
|------|----------|----------|
| 按钮 | 44 × 44 px | 48 × 48 px |
| 图标按钮 | 44 × 44 px | 48 × 48 px |
| 链接 | 44px 高度 | - |
| 列表项 | 44px 高度 | 48-56px |

---

## 间距要求

```
触摸目标之间最小间距: 8px
```

避免误触的关键是保持足够间距。

---

## 实现方式

### 扩展触摸区域

```css
/* 小图标但大触摸区 */
.icon-button {
  width: 24px;
  height: 24px;
  padding: 12px; /* 总尺寸 48px */
  margin: -12px;
}
```

### 点击反馈

```css
/* 移动端点击反馈 */
.touchable {
  -webkit-tap-highlight-color: transparent;
}

.touchable:active {
  transform: scale(0.95);
  opacity: 0.8;
}
```

---

## Safe Area

### 底部安全区

```css
/* 底部导航适配 */
.bottom-nav {
  padding-bottom: env(safe-area-inset-bottom);
}
```

### 刘海屏适配

```css
/* 顶部适配 */
.header {
  padding-top: env(safe-area-inset-top);
}
```

---

## 相关文档

- [响应式模式](./responsive.md)
- [交互模式](./interaction.md)
