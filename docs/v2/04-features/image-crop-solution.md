# 图像裁切解决方案设计

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-06  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 图片裁剪交互不统一，影响编辑效率
- 目标与非目标: 目标是统一裁剪流程与约束；非目标是替代具体滤镜能力

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 图像裁切的技术方案与交互策略
- Fabric.js 方案评估与替代设计

## 影响范围

- 相关模块: 图像处理与编辑器
- 相关文档: `docs/v2/04-features/canvas-architecture.md`

## 证据与验证

- 关键证据来源：`decodables-fe/@core/`、`decodables-fe/app/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |

## 1. Fabric.js 裁切问题分析

### 1.1 Fabric.js 现有裁切方式

```
┌─────────────────────────────────────────────────────────────────┐
│                    Fabric.js 裁切方式对比                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  方式 1: clipPath (推荐但有限制)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  const rect = new fabric.Rect({                          │   │
│  │    width: 200, height: 200,                              │   │
│  │    left: 50, top: 50,                                    │   │
│  │    absolutePositioned: true                              │   │
│  │  });                                                      │   │
│  │  image.clipPath = rect;                                  │   │
│  │                                                          │   │
│  │  ❌ 问题:                                                 │   │
│  │  • 裁切区域跟随图像变换（旋转时异常）                      │   │
│  │  • 无交互式裁切 UI                                        │   │
│  │  • 导出时可能丢失裁切                                     │   │
│  │  • absolutePositioned 计算复杂                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  方式 2: 修改 image.width/height + cropX/cropY                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  image.set({                                              │   │
│  │    cropX: 50,    // 从左侧裁掉 50px                       │   │
│  │    cropY: 50,    // 从顶部裁掉 50px                       │   │
│  │    width: 200,   // 裁切后宽度                            │   │
│  │    height: 200   // 裁切后高度                            │   │
│  │  });                                                      │   │
│  │                                                          │   │
│  │  ✅ 优点: 真正的像素裁切，性能好                          │   │
│  │  ❌ 问题:                                                 │   │
│  │  • 只支持矩形裁切                                         │   │
│  │  • 无交互式 UI                                            │   │
│  │  • 需要手动计算坐标                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  方式 3: 离屏 Canvas 预处理                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  // 在离屏 canvas 上裁切                                  │   │
│  │  const offscreen = document.createElement('canvas');      │   │
│  │  offscreen.width = cropWidth;                             │   │
│  │  offscreen.height = cropHeight;                           │   │
│  │  const ctx = offscreen.getContext('2d');                  │   │
│  │  ctx.drawImage(img, -cropX, -cropY);                      │   │
│  │                                                          │   │
│  │  // 用裁切后的图像创建 Fabric 对象                        │   │
│  │  const croppedImage = new fabric.Image(offscreen);        │   │
│  │                                                          │   │
│  │  ✅ 优点: 完全控制，支持任意形状                          │   │
│  │  ❌ 问题: 不可逆，原图丢失                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Fabric.js 裁切的具体问题

| 问题 | 严重程度 | 描述 |
|------|----------|------|
| **无交互式裁切 UI** | 🔴 高 | 没有内置的拖拽裁切框 |
| **clipPath 变换问题** | 🔴 高 | 旋转/缩放图像时裁切区域异常 |
| **只支持矩形** | 🟡 中 | 原生 cropX/cropY 不支持圆形/自由形状 |
| **导出问题** | 🟡 中 | toDataURL 时裁切可能丢失 |
| **撤销困难** | 🟡 中 | 裁切后恢复原图需要额外处理 |
| **性能问题** | 🟢 低 | 复杂 clipPath 影响渲染性能 |

---

## 2. 解决方案对比

### 2.1 方案总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    裁切解决方案对比                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  方案 A: Cropper.js 集成 (⭐ 推荐)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  流程: 双击图像 → 打开裁切模态框 → 裁切 → 替换图像        │   │
│  │                                                          │   │
│  │  优点:                                                   │   │
│  │  ✅ 成熟稳定，功能完整                                    │   │
│  │  ✅ 支持旋转、翻转、缩放                                  │   │
│  │  ✅ 支持预设比例 (1:1, 4:3, 16:9)                         │   │
│  │  ✅ 响应式，移动端友好                                    │   │
│  │  ✅ 体积小 (~40KB)                                        │   │
│  │                                                          │   │
│  │  缺点:                                                   │   │
│  │  ❌ 需要单独的裁切界面（不是直接在画布上）                 │   │
│  │  ❌ 裁切后原图丢失（除非我们保存）                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  方案 B: react-image-crop 集成                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  流程: 类似 Cropper.js，但是 React 原生                   │   │
│  │                                                          │   │
│  │  优点:                                                   │   │
│  │  ✅ React 组件，集成简单                                  │   │
│  │  ✅ TypeScript 支持好                                     │   │
│  │  ✅ 体积更小 (~15KB)                                      │   │
│  │                                                          │   │
│  │  缺点:                                                   │   │
│  │  ❌ 功能比 Cropper.js 少                                  │   │
│  │  ❌ 不支持旋转                                            │   │
│  │  ❌ 不支持翻转                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  方案 C: 自定义画布内裁切工具                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  流程: 选中图像 → 点击裁切 → 画布上显示裁切框 → 拖拽调整  │   │
│  │                                                          │   │
│  │  优点:                                                   │   │
│  │  ✅ 无缝体验，不离开画布                                  │   │
│  │  ✅ 可支持非矩形裁切                                      │   │
│  │  ✅ 与现有工具系统集成                                    │   │
│  │                                                          │   │
│  │  缺点:                                                   │   │
│  │  ❌ 开发工作量大 (2-3 周)                                 │   │
│  │  ❌ 需要处理边界情况                                      │   │
│  │  ❌ 移动端适配复杂                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  方案 D: Konva.js 替换 (长期)                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Konva.js 有更好的裁切支持:                               │   │
│  │  • 内置 Transformer 支持裁切框                            │   │
│  │  • clip 函数更灵活                                        │   │
│  │  • 性能更好                                               │   │
│  │                                                          │   │
│  │  缺点:                                                   │   │
│  │  ❌ 需要重构整个画布系统                                  │   │
│  │  ❌ 迁移成本高                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  方案 E: 混合方案 (⭐⭐ 最佳实践)                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  短期: Cropper.js 模态框裁切（快速实现）                   │   │
│  │  中期: 自定义画布内简单裁切                               │   │
│  │  长期: 考虑 Konva.js 迁移                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 方案评分

| 方案 | 开发成本 | 用户体验 | 功能完整性 | 维护成本 | 推荐度 |
|------|----------|----------|------------|----------|--------|
| **A: Cropper.js** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| B: react-image-crop | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| C: 自定义工具 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| D: Konva 迁移 | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ (长期) |
| **E: 混合方案** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 3. 推荐方案：Cropper.js 集成

### 3.1 为什么选择 Cropper.js

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cropper.js 功能特性                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  核心功能:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ✅ 交互式裁切框 (可拖拽、可调整大小)                     │   │
│  │  ✅ 图像旋转 (90° 步进或自由旋转)                         │   │
│  │  ✅ 图像翻转 (水平/垂直)                                  │   │
│  │  ✅ 图像缩放 (滚轮或按钮)                                 │   │
│  │  ✅ 预设宽高比 (自由, 1:1, 4:3, 16:9, 自定义)             │   │
│  │  ✅ 圆形裁切预览                                          │   │
│  │  ✅ 响应式支持                                            │   │
│  │  ✅ 触摸屏支持                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  技术优势:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 体积: ~40KB (gzip 后 ~12KB)                           │   │
│  │  • 无依赖 (纯 JavaScript)                                │   │
│  │  • TypeScript 支持                                        │   │
│  │  • 活跃维护 (GitHub 12k+ stars)                          │   │
│  │  • 丰富的 API 和事件                                     │   │
│  │  • 支持 Canvas 输出                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  竞品对比:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Cropper.js      ⭐⭐⭐⭐⭐  功能最全，最成熟              │   │
│  │  react-cropper   ⭐⭐⭐⭐   Cropper.js 的 React 封装       │   │
│  │  react-image-crop ⭐⭐⭐    轻量但功能少                   │   │
│  │  react-easy-crop ⭐⭐⭐⭐   现代 UI，支持圆形              │   │
│  │  vue-cropper     ⭐⭐⭐⭐   Vue 专用                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    裁切流程架构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户操作流程:                                                   │
│                                                                 │
│  1. 选中图像                                                     │
│     │                                                           │
│     ▼                                                           │
│  2. 点击工具栏 [✂️ Crop] 按钮                                    │
│     │                                                           │
│     ▼                                                           │
│  3. ┌─────────────────────────────────────────────────────┐    │
│     │              Crop Modal                              │    │
│     │  ┌─────────────────────────────────────────────┐    │    │
│     │  │                                              │    │    │
│     │  │         ┌─────────────────────┐             │    │    │
│     │  │         │   ┌───────────┐     │             │    │    │
│     │  │         │   │  裁切框   │     │  ← 可拖拽   │    │    │
│     │  │         │   └───────────┘     │             │    │    │
│     │  │         │      图像预览       │             │    │    │
│     │  │         └─────────────────────┘             │    │    │
│     │  │                                              │    │    │
│     │  └─────────────────────────────────────────────┘    │    │
│     │                                                      │    │
│     │  Aspect Ratio: [Free ▼] [1:1] [4:3] [16:9]          │    │
│     │                                                      │    │
│     │  [↺ Rotate] [↔ Flip H] [↕ Flip V] [🔍 Zoom]         │    │
│     │                                                      │    │
│     │              [Cancel]  [Apply]                       │    │
│     └─────────────────────────────────────────────────────┘    │
│     │                                                           │
│     ▼                                                           │
│  4. 点击 Apply                                                   │
│     │                                                           │
│     ▼                                                           │
│  5. 裁切后的图像替换原图像                                        │
│     (保存原图到 element.originalImage 用于撤销)                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 实现代码

```typescript
// @core/canvas/tools/crop/CropTool.ts

import { Tool, ToolOptions, PointerEvent } from '../base/Tool';
import { ImageElement } from '../../elements/image/ImageElement';
import { CanvasEngine } from '../../core/CanvasEngine';

export class CropTool extends Tool {
  constructor(engine: CanvasEngine) {
    super('crop', engine, {});
  }
  
  protected getDefaultOptions(): ToolOptions {
    return { cursor: 'crosshair' };
  }
  
  onPointerDown(event: PointerEvent): void {
    // 点击图像时打开裁切模态框
    const element = this.engine.getElementAtPoint(event.point);
    
    if (element?.type === 'image') {
      this.openCropModal(element as ImageElement);
    }
  }
  
  onPointerMove(event: PointerEvent): void {}
  onPointerUp(event: PointerEvent): void {}
  
  private openCropModal(element: ImageElement): void {
    // 触发打开裁切模态框事件
    this.engine.emit('crop:open', { element });
  }
  
  getIcon(): string { return 'crop'; }
  getName(): string { return 'Crop'; }
  getShortcut(): string { return 'c'; }
}
```

```typescript
// @core/canvas/components/CropModal.tsx

"use client";

import React, { useRef, useEffect, useState, useCallback } from 'react';
import Cropper from 'cropperjs';
import 'cropperjs/dist/cropper.css';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Slider } from '@/components/ui/slider';
import { 
  RotateCcw, 
  RotateCw, 
  FlipHorizontal, 
  FlipVertical,
  ZoomIn,
  ZoomOut,
  Square,
  RectangleHorizontal,
  Circle
} from 'lucide-react';

interface CropModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  imageUrl: string;
  onCrop: (croppedImageUrl: string, cropData: CropData) => void;
  initialAspectRatio?: number;
}

interface CropData {
  x: number;
  y: number;
  width: number;
  height: number;
  rotate: number;
  scaleX: number;
  scaleY: number;
}

const ASPECT_RATIOS = [
  { label: 'Free', value: NaN, icon: null },
  { label: '1:1', value: 1, icon: Square },
  { label: '4:3', value: 4/3, icon: RectangleHorizontal },
  { label: '16:9', value: 16/9, icon: RectangleHorizontal },
  { label: '3:2', value: 3/2, icon: RectangleHorizontal },
  { label: 'Circle', value: 1, icon: Circle, circular: true },
];

export function CropModal({ 
  open, 
  onOpenChange, 
  imageUrl, 
  onCrop,
  initialAspectRatio 
}: CropModalProps) {
  const imageRef = useRef<HTMLImageElement>(null);
  const cropperRef = useRef<Cropper | null>(null);
  const [aspectRatio, setAspectRatio] = useState<number>(initialAspectRatio || NaN);
  const [isCircular, setIsCircular] = useState(false);
  const [zoom, setZoom] = useState(1);
  
  // 初始化 Cropper
  useEffect(() => {
    if (!open || !imageRef.current) return;
    
    // 销毁旧实例
    if (cropperRef.current) {
      cropperRef.current.destroy();
    }
    
    // 创建新实例
    cropperRef.current = new Cropper(imageRef.current, {
      aspectRatio: aspectRatio,
      viewMode: 1,
      dragMode: 'move',
      autoCropArea: 0.8,
      restore: false,
      guides: true,
      center: true,
      highlight: true,
      cropBoxMovable: true,
      cropBoxResizable: true,
      toggleDragModeOnDblclick: false,
      initialAspectRatio: aspectRatio,
      ready() {
        // Cropper 准备就绪
      },
      zoom(e) {
        setZoom(e.detail.ratio);
      },
    });
    
    return () => {
      if (cropperRef.current) {
        cropperRef.current.destroy();
        cropperRef.current = null;
      }
    };
  }, [open, imageUrl]);
  
  // 更新宽高比
  useEffect(() => {
    if (cropperRef.current) {
      cropperRef.current.setAspectRatio(aspectRatio);
    }
  }, [aspectRatio]);
  
  // 旋转
  const handleRotate = useCallback((degree: number) => {
    cropperRef.current?.rotate(degree);
  }, []);
  
  // 翻转
  const handleFlip = useCallback((direction: 'horizontal' | 'vertical') => {
    if (!cropperRef.current) return;
    
    const data = cropperRef.current.getData();
    if (direction === 'horizontal') {
      cropperRef.current.scaleX(data.scaleX === 1 ? -1 : 1);
    } else {
      cropperRef.current.scaleY(data.scaleY === 1 ? -1 : 1);
    }
  }, []);
  
  // 缩放
  const handleZoom = useCallback((delta: number) => {
    cropperRef.current?.zoom(delta);
  }, []);
  
  // 重置
  const handleReset = useCallback(() => {
    cropperRef.current?.reset();
    setZoom(1);
  }, []);
  
  // 应用裁切
  const handleApply = useCallback(() => {
    if (!cropperRef.current) return;
    
    const cropData = cropperRef.current.getData(true); // rounded
    
    // 获取裁切后的 canvas
    const canvas = cropperRef.current.getCroppedCanvas({
      maxWidth: 4096,
      maxHeight: 4096,
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high',
    });
    
    // 如果是圆形裁切，应用圆形遮罩
    let finalCanvas = canvas;
    if (isCircular) {
      finalCanvas = applyCircularMask(canvas);
    }
    
    // 转换为 Data URL
    const croppedImageUrl = finalCanvas.toDataURL('image/png');
    
    onCrop(croppedImageUrl, {
      x: cropData.x,
      y: cropData.y,
      width: cropData.width,
      height: cropData.height,
      rotate: cropData.rotate,
      scaleX: cropData.scaleX,
      scaleY: cropData.scaleY,
    });
    
    onOpenChange(false);
  }, [onCrop, onOpenChange, isCircular]);
  
  // 圆形遮罩
  const applyCircularMask = (canvas: HTMLCanvasElement): HTMLCanvasElement => {
    const size = Math.min(canvas.width, canvas.height);
    const output = document.createElement('canvas');
    output.width = size;
    output.height = size;
    
    const ctx = output.getContext('2d')!;
    
    // 创建圆形裁切路径
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    ctx.closePath();
    ctx.clip();
    
    // 绘制图像
    const offsetX = (canvas.width - size) / 2;
    const offsetY = (canvas.height - size) / 2;
    ctx.drawImage(canvas, -offsetX, -offsetY);
    
    return output;
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Crop Image</DialogTitle>
        </DialogHeader>
        
        {/* 裁切区域 */}
        <div className="flex-1 min-h-0 bg-gray-100 rounded-lg overflow-hidden">
          <div className="w-full h-full flex items-center justify-center p-4">
            <img
              ref={imageRef}
              src={imageUrl}
              alt="Crop preview"
              className="max-w-full max-h-full"
              style={{ display: 'block' }}
            />
          </div>
        </div>
        
        {/* 工具栏 */}
        <div className="space-y-4 pt-4">
          {/* 宽高比选择 */}
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700">Aspect Ratio:</span>
            <ToggleGroup 
              type="single" 
              value={aspectRatio.toString()}
              onValueChange={(value) => {
                const ratio = ASPECT_RATIOS.find(r => r.value.toString() === value);
                if (ratio) {
                  setAspectRatio(ratio.value);
                  setIsCircular(ratio.circular || false);
                }
              }}
            >
              {ASPECT_RATIOS.map((ratio) => (
                <ToggleGroupItem 
                  key={ratio.label} 
                  value={ratio.value.toString()}
                  className="px-3"
                >
                  {ratio.icon && <ratio.icon className="w-4 h-4 mr-1" />}
                  {ratio.label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
          
          {/* 操作按钮 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {/* 旋转 */}
              <Button variant="outline" size="icon" onClick={() => handleRotate(-90)}>
                <RotateCcw className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={() => handleRotate(90)}>
                <RotateCw className="w-4 h-4" />
              </Button>
              
              <div className="w-px h-6 bg-gray-200 mx-2" />
              
              {/* 翻转 */}
              <Button variant="outline" size="icon" onClick={() => handleFlip('horizontal')}>
                <FlipHorizontal className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={() => handleFlip('vertical')}>
                <FlipVertical className="w-4 h-4" />
              </Button>
              
              <div className="w-px h-6 bg-gray-200 mx-2" />
              
              {/* 缩放 */}
              <Button variant="outline" size="icon" onClick={() => handleZoom(-0.1)}>
                <ZoomOut className="w-4 h-4" />
              </Button>
              <span className="text-sm text-gray-600 w-12 text-center">
                {Math.round(zoom * 100)}%
              </span>
              <Button variant="outline" size="icon" onClick={() => handleZoom(0.1)}>
                <ZoomIn className="w-4 h-4" />
              </Button>
              
              <div className="w-px h-6 bg-gray-200 mx-2" />
              
              {/* 重置 */}
              <Button variant="outline" size="sm" onClick={handleReset}>
                Reset
              </Button>
            </div>
            
            {/* 确认按钮 */}
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleApply}>
                Apply
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

```typescript
// @core/canvas/elements/image/ImageElement.ts (扩展)

export class ImageElement extends Element {
  // ... 现有代码 ...
  
  // 保存原始图像用于撤销
  private originalImageData: string | null = null;
  private cropHistory: CropData[] = [];
  
  /**
   * 应用裁切
   */
  async applyCrop(croppedImageUrl: string, cropData: CropData): Promise<void> {
    // 保存原始图像（如果是第一次裁切）
    if (!this.originalImageData) {
      this.originalImageData = await this.toDataURL();
    }
    
    // 记录裁切历史
    this.cropHistory.push(cropData);
    
    // 加载裁切后的图像
    await this.loadFromDataURL(croppedImageUrl);
    
    // 触发更新事件
    this.onCropApplied();
  }
  
  /**
   * 恢复原始图像
   */
  async restoreOriginal(): Promise<boolean> {
    if (!this.originalImageData) return false;
    
    await this.loadFromDataURL(this.originalImageData);
    this.cropHistory = [];
    
    return true;
  }
  
  /**
   * 撤销最后一次裁切
   */
  async undoLastCrop(): Promise<boolean> {
    if (this.cropHistory.length === 0) return false;
    
    // 如果只有一次裁切，恢复原图
    if (this.cropHistory.length === 1) {
      return this.restoreOriginal();
    }
    
    // 否则需要重新应用之前的裁切
    // 这需要更复杂的实现...
    return false;
  }
  
  /**
   * 是否有裁切历史
   */
  hasCropHistory(): boolean {
    return this.cropHistory.length > 0;
  }
  
  /**
   * 是否可以恢复原图
   */
  canRestoreOriginal(): boolean {
    return this.originalImageData !== null;
  }
  
  // 序列化时包含裁切信息
  serialize(): object {
    return {
      ...super.serialize(),
      originalImageData: this.originalImageData,
      cropHistory: this.cropHistory,
    };
  }
  
  deserialize(data: any): void {
    super.deserialize(data);
    this.originalImageData = data.originalImageData || null;
    this.cropHistory = data.cropHistory || [];
  }
}
```

### 3.4 画布内快速裁切（简化版）

除了模态框裁切，还可以提供一个简化的画布内裁切：

```typescript
// @core/canvas/tools/crop/QuickCropTool.ts

/**
 * 快速裁切工具
 * 
 * 在画布上直接显示裁切框，用于简单的矩形裁切
 * 比模态框更快捷，但功能较少
 */

import { Tool, ToolOptions, PointerEvent } from '../base/Tool';
import { ImageElement } from '../../elements/image/ImageElement';
import { CanvasEngine } from '../../core/CanvasEngine';
import { fabric } from 'fabric';

interface CropState {
  element: ImageElement | null;
  cropRect: fabric.Rect | null;
  originalBounds: { left: number; top: number; width: number; height: number } | null;
  isActive: boolean;
}

export class QuickCropTool extends Tool {
  private state: CropState = {
    element: null,
    cropRect: null,
    originalBounds: null,
    isActive: false,
  };
  
  constructor(engine: CanvasEngine) {
    super('quick-crop', engine, {});
  }
  
  protected getDefaultOptions(): ToolOptions {
    return { cursor: 'crosshair' };
  }
  
  protected onActivate(): void {
    // 检查是否有选中的图像
    const selected = this.engine.getSelectedElements();
    if (selected.length === 1 && selected[0].type === 'image') {
      this.startCrop(selected[0] as ImageElement);
    } else {
      this.engine.showToast('Please select an image to crop');
      this.engine.setActiveTool('select');
    }
  }
  
  protected onDeactivate(): void {
    this.cancelCrop();
  }
  
  private startCrop(element: ImageElement): void {
    this.state.element = element;
    this.state.isActive = true;
    
    const fabricObj = this.engine.renderer.getFabricObject(element.id);
    if (!fabricObj) return;
    
    // 保存原始边界
    this.state.originalBounds = {
      left: fabricObj.left || 0,
      top: fabricObj.top || 0,
      width: (fabricObj.width || 0) * (fabricObj.scaleX || 1),
      height: (fabricObj.height || 0) * (fabricObj.scaleY || 1),
    };
    
    // 创建裁切框
    const bounds = this.state.originalBounds;
    this.state.cropRect = new fabric.Rect({
      left: bounds.left + bounds.width * 0.1,
      top: bounds.top + bounds.height * 0.1,
      width: bounds.width * 0.8,
      height: bounds.height * 0.8,
      fill: 'transparent',
      stroke: '#2196F3',
      strokeWidth: 2,
      strokeDashArray: [5, 5],
      cornerColor: '#2196F3',
      cornerSize: 10,
      transparentCorners: false,
      hasRotatingPoint: false,
      lockRotation: true,
    });
    
    // 添加到画布
    const canvas = this.engine.renderer.getNativeEngine();
    canvas.add(this.state.cropRect);
    canvas.setActiveObject(this.state.cropRect);
    canvas.renderAll();
    
    // 添加遮罩效果
    this.addDarkOverlay();
    
    // 显示确认按钮
    this.showCropControls();
  }
  
  private addDarkOverlay(): void {
    // 创建暗色遮罩，只露出裁切区域
    // 使用 4 个矩形围绕裁切框
  }
  
  private showCropControls(): void {
    // 显示 "Apply" 和 "Cancel" 按钮
    this.engine.emit('crop:showControls', {
      onApply: () => this.applyCrop(),
      onCancel: () => this.cancelCrop(),
    });
  }
  
  private async applyCrop(): Promise<void> {
    if (!this.state.element || !this.state.cropRect || !this.state.originalBounds) {
      return;
    }
    
    const cropRect = this.state.cropRect;
    const bounds = this.state.originalBounds;
    
    // 计算裁切区域相对于图像的位置
    const cropX = (cropRect.left! - bounds.left) / bounds.width;
    const cropY = (cropRect.top! - bounds.top) / bounds.height;
    const cropWidth = cropRect.width! / bounds.width;
    const cropHeight = cropRect.height! / bounds.height;
    
    // 获取原始图像
    const imageUrl = await this.state.element.toDataURL();
    
    // 执行裁切
    const croppedUrl = await this.cropImage(imageUrl, {
      x: cropX,
      y: cropY,
      width: cropWidth,
      height: cropHeight,
    });
    
    // 应用裁切
    await this.state.element.applyCrop(croppedUrl, {
      x: cropX,
      y: cropY,
      width: cropWidth,
      height: cropHeight,
      rotate: 0,
      scaleX: 1,
      scaleY: 1,
    });
    
    // 更新位置
    this.state.element.setTransform({
      x: cropRect.left!,
      y: cropRect.top!,
    });
    
    // 清理并记录历史
    this.cleanup();
    this.engine.history.commit();
    this.engine.setActiveTool('select');
  }
  
  private async cropImage(
    imageUrl: string, 
    crop: { x: number; y: number; width: number; height: number }
  ): Promise<string> {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d')!;
        
        const sx = crop.x * img.width;
        const sy = crop.y * img.height;
        const sw = crop.width * img.width;
        const sh = crop.height * img.height;
        
        canvas.width = sw;
        canvas.height = sh;
        
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
        
        resolve(canvas.toDataURL('image/png'));
      };
      img.src = imageUrl;
    });
  }
  
  private cancelCrop(): void {
    this.cleanup();
    this.engine.setActiveTool('select');
  }
  
  private cleanup(): void {
    if (this.state.cropRect) {
      const canvas = this.engine.renderer.getNativeEngine();
      canvas.remove(this.state.cropRect);
      canvas.renderAll();
    }
    
    this.state = {
      element: null,
      cropRect: null,
      originalBounds: null,
      isActive: false,
    };
    
    this.engine.emit('crop:hideControls');
  }
  
  onPointerDown(event: PointerEvent): void {}
  onPointerMove(event: PointerEvent): void {}
  onPointerUp(event: PointerEvent): void {}
  
  getIcon(): string { return 'crop'; }
  getName(): string { return 'Quick Crop'; }
  getShortcut(): string { return 'c'; }
}
```

---

## 4. 其他裁切库对比

### 4.1 详细对比表

```
┌─────────────────────────────────────────────────────────────────┐
│                    裁切库详细对比                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Cropper.js                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GitHub: 12.8k ⭐  │  体积: 40KB  │  维护: 活跃           │   │
│  │                                                          │   │
│  │  ✅ 功能完整 (裁切/旋转/翻转/缩放)                        │   │
│  │  ✅ 多种裁切模式                                          │   │
│  │  ✅ 支持预设宽高比                                        │   │
│  │  ✅ 触摸屏支持                                            │   │
│  │  ✅ 丰富的 API 和事件                                     │   │
│  │  ✅ 无依赖                                                │   │
│  │  ❌ 非 React 原生                                         │   │
│  │  ❌ UI 需要自定义                                         │   │
│  │                                                          │   │
│  │  npm: cropperjs                                           │   │
│  │  React: react-cropper                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  react-image-crop                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GitHub: 3.7k ⭐  │  体积: 15KB  │  维护: 活跃            │   │
│  │                                                          │   │
│  │  ✅ React 原生组件                                        │   │
│  │  ✅ TypeScript 完整支持                                   │   │
│  │  ✅ 体积小                                                │   │
│  │  ✅ 简单易用                                              │   │
│  │  ❌ 不支持旋转                                            │   │
│  │  ❌ 不支持翻转                                            │   │
│  │  ❌ 不支持缩放图像                                        │   │
│  │  ❌ 功能较基础                                            │   │
│  │                                                          │   │
│  │  npm: react-image-crop                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  react-easy-crop                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GitHub: 2.1k ⭐  │  体积: 20KB  │  维护: 活跃            │   │
│  │                                                          │   │
│  │  ✅ 现代 UI 设计                                          │   │
│  │  ✅ 支持圆形裁切                                          │   │
│  │  ✅ 支持旋转                                              │   │
│  │  ✅ 支持缩放                                              │   │
│  │  ✅ 触摸友好                                              │   │
│  │  ✅ TypeScript 支持                                       │   │
│  │  ❌ 依赖 tslib                                            │   │
│  │  ❌ 自定义能力有限                                        │   │
│  │                                                          │   │
│  │  npm: react-easy-crop                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  react-avatar-editor                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GitHub: 2.3k ⭐  │  体积: 25KB  │  维护: 较少            │   │
│  │                                                          │   │
│  │  ✅ 专为头像设计                                          │   │
│  │  ✅ 圆形/方形裁切                                         │   │
│  │  ✅ 拖拽定位                                              │   │
│  │  ❌ 不适合通用裁切                                        │   │
│  │  ❌ 功能有限                                              │   │
│  │                                                          │   │
│  │  npm: react-avatar-editor                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 推荐选择

| 场景 | 推荐库 | 理由 |
|------|--------|------|
| **功能完整** | Cropper.js / react-cropper | 功能最全，支持旋转翻转 |
| **轻量简单** | react-image-crop | 体积最小，够用即可 |
| **现代 UI** | react-easy-crop | UI 美观，支持圆形 |
| **头像裁切** | react-avatar-editor | 专为头像设计 |

---

## 5. 实施计划

### 5.1 阶段规划

```
┌─────────────────────────────────────────────────────────────────┐
│                    裁切功能实施计划                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: Cropper.js 模态框 (3 天)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Day 1:                                                   │   │
│  │  • 安装 cropperjs / react-cropper                         │   │
│  │  • 创建 CropModal 组件                                    │   │
│  │  • 基础裁切功能                                           │   │
│  │                                                          │   │
│  │  Day 2:                                                   │   │
│  │  • 宽高比选择                                             │   │
│  │  • 旋转/翻转功能                                          │   │
│  │  • 缩放功能                                               │   │
│  │  • 圆形裁切                                               │   │
│  │                                                          │   │
│  │  Day 3:                                                   │   │
│  │  • 与 ImageElement 集成                                   │   │
│  │  • 裁切历史/撤销                                          │   │
│  │  • 测试和优化                                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 2: 快速裁切工具 (2 天) - 可选                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • QuickCropTool 实现                                     │   │
│  │  • 画布内裁切框                                           │   │
│  │  • 遮罩效果                                               │   │
│  │  • 确认/取消 UI                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 3: 高级功能 (2 天) - 可选                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 自由形状裁切（多边形）                                 │   │
│  │  • 智能裁切（人脸检测）                                   │   │
│  │  • 批量裁切                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  总计: 3-7 天                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 依赖安装

```bash
# 方案 A: Cropper.js (推荐)
npm install cropperjs react-cropper

# 方案 B: react-easy-crop
npm install react-easy-crop

# 方案 C: react-image-crop
npm install react-image-crop
```

---

## 6. 总结与建议

### 最终推荐

```
┌─────────────────────────────────────────────────────────────────┐
│                    推荐方案                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⭐ 短期 (1周内): react-cropper (Cropper.js React 封装)          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 功能完整，满足 90% 需求                                │   │
│  │  • 开发快速 (3 天)                                        │   │
│  │  • 成熟稳定                                               │   │
│  │  • 模态框方式，不影响现有画布逻辑                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🔄 中期 (可选): 画布内快速裁切                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 提升用户体验                                           │   │
│  │  • 适合简单矩形裁切                                       │   │
│  │  • 与模态框互补                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🚀 长期: 考虑 Konva.js 迁移                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 更好的裁切原生支持                                     │   │
│  │  • 更好的性能                                             │   │
│  │  • 更灵活的变换系统                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 关键决策点

| 问题 | 建议 |
|------|------|
| **使用模态框还是画布内裁切？** | 先做模态框（更快），后续可加画布内 |
| **需要旋转/翻转功能吗？** | 需要 → Cropper.js；不需要 → react-image-crop |
| **需要圆形裁切吗？** | 教育产品可能需要（头像等） |
| **保留原图吗？** | 建议保留，支持撤销/恢复 |

---

**裁切解决方案设计完成！**
