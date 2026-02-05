# 布局组件规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/design/GRID-LAYOUT, CARD-COMPONENTS 等

---

## 概述

布局类组件的设计规范。

---

## 组件列表

### Container 容器
- 最大宽度限制
- 水平居中
- 响应式 padding

### Grid 网格
- 12 列网格
- 响应式列数
- 间距控制

### Card 卡片
- 基础卡片
- 可交互卡片
- 图片卡片

### Stack 堆叠
- 垂直堆叠
- 水平堆叠
- 间距控制

### Divider 分隔线
- 水平分隔
- 垂直分隔

---

## 网格系统

```
Desktop (lg): 4 列
Tablet (md): 3 列
Mobile (sm): 2 列
Mobile (xs): 1 列
```

---

## 卡片规范

| 属性 | 值 |
|------|-----|
| 圆角 | 8px (md) |
| 阴影 | shadow-sm |
| 内边距 | 16px |
| 悬停 | shadow-md + scale(1.02) |

---

## 相关文档

- [设计 Token](../tokens.md)
- [响应式模式](../patterns/responsive.md)
