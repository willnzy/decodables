# 编辑器专用组件规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 CED-PageSelector, CED-ColorPicker, CED-Slider 等

---

## 概述

编辑器专用组件的设计规范。

---

## 组件列表

### PageSelector 页面选择器
- 页面缩略图列表
- 拖拽排序
- 添加/删除页面

### ColorPicker 颜色选择器
- 色板选择
- 自定义颜色
- 透明度控制
- 最近使用

### Slider 滑块
- 数值滑块
- 范围滑块
- 带输入框

### Toolbar 工具栏
- 水平工具栏
- 工具分组
- 快捷键提示

### PropertyPanel 属性面板
- 属性分组
- 折叠/展开
- 数值输入

### LayerPanel 图层面板
- 图层列表
- 拖拽排序
- 可见性控制
- 锁定控制

---

## 颜色选择器规范

```
预设色板: 20 种常用颜色
历史记录: 最近 8 种
格式: HEX / RGB / HSL
```

---

## 相关文档

- [编辑器功能规格](../../02-product/features/editor.md)
- [编辑器模块技术设计](../../04-engineering/modules/editor/)
