# 图像裁切技术设计

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 main/image-crop-solution-design.md

---

## 概述

编辑器中图像裁切功能的技术设计。

---

## 功能

### 裁切模式
- 自由裁切
- 固定比例裁切 (1:1, 4:3, 16:9)
- 自定义比例

### 操作
- 拖拽裁切框
- 拖拽角点调整
- 数值输入精确裁切
- 重置/取消

---

## 技术方案

### Fabric.js 集成

```typescript
// 裁切遮罩
const clipPath = new fabric.Rect({
  left: x,
  top: y,
  width: cropWidth,
  height: cropHeight,
  absolutePositioned: true,
});

image.clipPath = clipPath;
```

### 裁切状态

```typescript
interface CropState {
  isActive: boolean;
  originalImage: fabric.Image;
  cropRect: { x: number; y: number; width: number; height: number };
  aspectRatio: number | null;
}
```

---

## UI 交互

1. 选中图片 → 工具栏显示"裁切"按钮
2. 点击裁切 → 进入裁切模式
3. 调整裁切框 → 实时预览
4. 确认/取消 → 应用或放弃

---

## 相关文档

- [编辑器架构](./architecture.md)
- [图片编辑功能](../../../02-product/features/editor.md)
