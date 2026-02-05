# 导航组件规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 CED-Navbar, CED-BottomNavbar, CED-Sidebar 等

---

## 概述

导航类组件的设计规范。

---

## 组件列表

### TopNavbar 顶部导航
- Logo
- 主导航链接
- 用户菜单
- 响应式折叠

### BottomNavbar 底部导航 (Mobile)
- 固定底部
- 5 个主要入口
- 当前页高亮

### Sidebar 侧边栏
- 编辑器左侧面板
- 可折叠

### Tabs 标签页
- 基础标签
- 带图标标签
- 可滚动标签

### Breadcrumb 面包屑
- 路径导航
- 可点击返回

### DropdownMenu 下拉菜单
- 基础下拉
- 嵌套菜单
- 带图标菜单

---

## 响应式行为

| 组件 | Desktop | Mobile |
|------|---------|--------|
| TopNavbar | 完整显示 | 汉堡菜单 |
| BottomNavbar | 隐藏 | 显示 |
| Sidebar | 固定显示 | Sheet 弹出 |

---

## 相关文档

- [响应式模式](../patterns/responsive.md)
- [UI 导航设计](../../02-product/)
