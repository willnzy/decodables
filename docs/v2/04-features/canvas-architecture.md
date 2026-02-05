# Canvas 画布架构设计 - 可扩展架构

**状态**: active  
**版本**: 1.1.0  
**版本日期**: 2026-01-11  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 画布架构复杂，需要统一分层与数据流说明
- 目标与非目标: 目标是明确画布架构与核心数据流；非目标是替代具体实现细节

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- Canvas 架构与工具系统设计
- 渲染引擎选型与性能优化策略

## 影响范围

- 相关模块: Canvas 引擎与编辑器
- 相关文档: `docs/v2/03-business/canvas-data-schema.md`

## 证据与验证

- 关键证据来源：`decodables-fe/@core/`、`decodables-fe/app/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.1.0 | 结构对齐与信息补齐 | Docs Working Group |

## 快速导航

| 我想要... | 跳转到 |
|-----------|--------|
| 了解架构概况 | [3. 架构设计](#3-架构设计) |
| 实现新工具 | [6. 工具系统设计](#6-工具系统设计) |
| 添加手绘功能 | [7. 手绘与画笔系统](#7-手绘与画笔系统) |
| 支持矢量图 | [8. 矢量图支持](#8-矢量图支持) |
| 实现撤销/重做 | [9. 历史记录系统](#9-历史记录系统) |
| 性能优化 | [10. 性能优化](#10-性能优化) |

---

## 文档分工

**本文档重点**:
- ✅ Canvas 核心架构 (Tool Manager、Element System、History System)
- ✅ 渲染引擎选型与集成 (Fabric.js、Paper.js)
- ✅ 手绘、矢量、导出功能的技术实现
- ✅ 性能优化策略

**不涵盖内容** (请参考其他文档):
- ❌ UI 面板设计 → `docs/v2/04-features/editor-media-properties.md`
- ❌ 设计系统规范 → `docs/v2/02-standards/design-system.md`
- ❌ Canvas 数据持久化格式 → `docs/shared/canvas-data-schema.md`

---

## 目录

1. [需求分析](#1-需求分析)
2. [技术选型](#2-技术选型)
3. [架构设计](#3-架构设计)
4. [核心抽象层](#4-核心抽象层)
5. [渲染引擎设计](#5-渲染引擎设计)
6. [工具系统设计](#6-工具系统设计)
7. [手绘与画笔系统](#7-手绘与画笔系统)
8. [矢量图支持](#8-矢量图支持)
9. [历史记录系统](#9-历史记录系统)
10. [性能优化](#10-性能优化)
11. [实施路线图](#11-实施路线图)

---

## 1. 需求分析

### 1.1 当前功能

```
┌─────────────────────────────────────────────────────────────────┐
│                    当前画布功能                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ 已支持                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 图片元素 (位图)                                        │   │
│  │  • 文本元素                                               │   │
│  │  • 基础形状 (矩形、圆形)                                   │   │
│  │  • 贴纸 (PNG/SVG)                                         │   │
│  │  • 拖拽、缩放、旋转                                        │   │
│  │  • 图层管理                                               │   │
│  │  • 撤销/重做                                              │   │
│  │  • 导出 PDF                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 未来功能需求

```
┌─────────────────────────────────────────────────────────────────┐
│                    未来功能需求                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🎯 Phase 1: 手绘与画笔                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 铅笔工具 (Pencil)                                      │   │
│  │  • 钢笔工具 (Pen) - 平滑曲线                               │   │
│  │  • 马克笔 (Marker)                                        │   │
│  │  • 荧光笔 (Highlighter)                                   │   │
│  │  • 橡皮擦 (Eraser)                                        │   │
│  │  • 画笔大小、颜色、透明度                                  │   │
│  │  • 压感支持 (Stylus)                                      │   │
│  │  • 路径平滑算法                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🎯 Phase 2: 矢量图形                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 贝塞尔曲线编辑                                         │   │
│  │  • 路径节点操作 (添加/删除/移动)                           │   │
│  │  • 布尔运算 (合并/相交/差集)                               │   │
│  │  • SVG 导入/导出                                          │   │
│  │  • 矢量形状库                                             │   │
│  │  • 路径描边与填充                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🎯 Phase 3: 高级功能                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 蒙版 (Masking)                                         │   │
│  │  • 混合模式 (Blend Modes)                                 │   │
│  │  • 图层效果 (阴影、模糊、发光)                             │   │
│  │  • 渐变填充                                               │   │
│  │  • 图案填充                                               │   │
│  │  • 智能参考线                                             │   │
│  │  • 网格与对齐                                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 技术挑战

| 挑战 | 描述 | 影响 |
|------|------|------|
| **渲染性能** | 手绘路径可能有数千个点 | 需要优化渲染和简化算法 |
| **平滑度** | 手绘线条需要自然流畅 | 需要路径平滑算法 |
| **精确性** | 矢量编辑需要亚像素精度 | 需要高精度数学计算 |
| **撤销性能** | 手绘产生大量历史记录 | 需要优化历史记录策略 |
| **导出兼容** | SVG/PDF 需要正确输出矢量 | 需要完整的路径序列化 |
| **移动端** | 触摸屏手势与画笔冲突 | 需要智能模式切换 |

---

## 2. 技术选型

### 2.1 渲染引擎对比

```
┌─────────────────────────────────────────────────────────────────┐
│                    渲染引擎对比                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Fabric.js (当前)                                         │   │
│  │  ─────────────────                                        │   │
│  │  ✅ 优点:                                                 │   │
│  │  • 成熟稳定，文档完善                                      │   │
│  │  • 对象模型完整                                           │   │
│  │  • SVG 支持良好                                           │   │
│  │  • 社区活跃                                               │   │
│  │                                                          │   │
│  │  ❌ 缺点:                                                 │   │
│  │  • 性能一般 (Canvas 2D)                                   │   │
│  │  • 手绘支持有限                                           │   │
│  │  • 路径编辑功能基础                                        │   │
│  │  • 体积较大 (~300KB)                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Konva.js                                                 │   │
│  │  ─────────────────                                        │   │
│  │  ✅ 优点:                                                 │   │
│  │  • 性能优秀                                               │   │
│  │  • React 集成好 (react-konva)                             │   │
│  │  • 分层渲染                                               │   │
│  │  • 体积小 (~150KB)                                        │   │
│  │                                                          │   │
│  │  ❌ 缺点:                                                 │   │
│  │  • 矢量编辑功能需自己实现                                  │   │
│  │  • SVG 支持有限                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Paper.js                                                 │   │
│  │  ─────────────────                                        │   │
│  │  ✅ 优点:                                                 │   │
│  │  • 矢量路径操作强大                                        │   │
│  │  • 布尔运算完整                                           │   │
│  │  • 贝塞尔曲线支持好                                        │   │
│  │  • SVG 导入导出完善                                        │   │
│  │                                                          │   │
│  │  ❌ 缺点:                                                 │   │
│  │  • 社区较小                                               │   │
│  │  • 文档偏学术                                             │   │
│  │  • 非 React 生态                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PixiJS                                                   │   │
│  │  ─────────────────                                        │   │
│  │  ✅ 优点:                                                 │   │
│  │  • 性能最强 (WebGL)                                       │   │
│  │  • 滤镜效果丰富                                           │   │
│  │  • 大规模元素无压力                                        │   │
│  │                                                          │   │
│  │  ❌ 缺点:                                                 │   │
│  │  • 主要面向游戏                                           │   │
│  │  • 矢量支持弱                                             │   │
│  │  • SVG 需额外处理                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 手绘库对比

| 库 | 特点 | 效果 | 体积 | 推荐场景 |
|-----|------|------|------|----------|
| **[perfect-freehand](https://github.com/steveruizok/perfect-freehand)** | 最自然的手绘效果 | ⭐⭐⭐⭐⭐ | 5KB | 手绘涂鸦 |
| **[Rough.js](https://roughjs.com/)** | 手绘风格矢量 | ⭐⭐⭐⭐ | 20KB | 草图风格 |
| **[Pressure.js](https://github.com/stuyam/pressure)** | 压感检测 | - | 3KB | 配合其他库 |
| **[Simplify.js](https://mourner.github.io/simplify-js/)** | 路径简化 (Ramer-Douglas-Peucker) | - | 2KB | 性能优化 |

### 2.3 技术能力依赖汇总

| 功能需求 | 核心库 | 辅助库 | npm 包名 |
|---------|--------|--------|----------|
| **Canvas 渲染** | Fabric.js 5.3.0 | - | `fabric` |
| **撤销/重做** | 自定义 Command Pattern | fabric-history (可选) | `fabric-history` |
| **手绘笔触** | perfect-freehand | Pressure.js | `perfect-freehand`, `pressure` |
| **路径简化** | Simplify.js | - | `simplify-js` |
| **矢量编辑** | Paper.js | - | `paper` |
| **布尔运算** | Paper.js | - | `paper` |
| **SVG 处理** | Fabric.js + Paper.js | - | - |
| **PDF 导出** | 后端处理 | - | - |

### 2.4 推荐方案

```
┌─────────────────────────────────────────────────────────────────┐
│                    推荐技术方案                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  方案: 抽象层 + 多引擎混合                                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                  ┌─────────────────┐                     │   │
│  │                  │  Canvas Core    │  ← 抽象层            │   │
│  │                  │   (我们的代码)   │                     │   │
│  │                  └────────┬────────┘                     │   │
│  │                           │                              │   │
│  │          ┌────────────────┼────────────────┐             │   │
│  │          │                │                │             │   │
│  │          ▼                ▼                ▼             │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │   │
│  │  │  Fabric.js   │ │ perfect-     │ │  Paper.js    │     │   │
│  │  │  (主渲染)    │ │ freehand     │ │  (矢量操作)  │     │   │
│  │  │              │ │ (手绘)       │ │              │     │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘     │   │
│  │                                                          │   │
│  │  渲染职责:        手绘职责:         矢量职责:              │   │
│  │  • 图片/文本     • 路径生成        • 贝塞尔编辑            │   │
│  │  • 基础形状      • 平滑算法        • 布尔运算              │   │
│  │  • 变换操作      • 压感处理        • 路径操作              │   │
│  │  • 导出         • 笔刷效果        • SVG 处理              │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  优势:                                                          │
│  • 保持现有 Fabric.js 投资                                      │
│  • 各取所长，最佳效果                                            │
│  • 可独立升级各模块                                              │
│  • 抽象层隔离，未来可替换                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 架构设计

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    画布架构全景                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      UI Layer                            │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ Toolbar │ │ Canvas  │ │ Media   │ │ Props   │       │   │
│  │  │         │ │ View    │ │ Library │ │ Panel   │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Canvas Core                           │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │                 Tool Manager                     │    │   │
│  │  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐      │    │   │
│  │  │  │Select │ │ Draw  │ │ Shape │ │ Text  │ ...  │    │   │
│  │  │  └───────┘ └───────┘ └───────┘ └───────┘      │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │               Element System                     │    │   │
│  │  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐      │    │   │
│  │  │  │ Image │ │ Text  │ │ Path  │ │ Shape │ ...  │    │   │
│  │  │  └───────┘ └───────┘ └───────┘ └───────┘      │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │               History System                     │    │   │
│  │  │  Command Pattern + Diff-based Snapshots          │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │                Event System                      │    │   │
│  │  │  Pointer / Keyboard / Touch / Stylus             │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Render Engine Layer                     │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │   Fabric.js  │  │ Freehand     │  │  Paper.js    │  │   │
│  │  │   Renderer   │  │ Renderer     │  │  Renderer    │  │   │
│  │  │              │  │              │  │              │  │   │
│  │  │ • Objects    │  │ • Strokes    │  │ • Paths      │  │   │
│  │  │ • Selection  │  │ • Pressure   │  │ • Boolean    │  │   │
│  │  │ • Transform  │  │ • Smoothing  │  │ • Bezier     │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  │                                                          │   │
│  │         ┌────────────────────────────────────┐          │   │
│  │         │         Unified Canvas             │          │   │
│  │         │     (Multiple Layers Composited)   │          │   │
│  │         └────────────────────────────────────┘          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Export System                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │   │
│  │  │   PDF    │  │   PNG    │  │   SVG    │  │  JSON   │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 目录结构

```
@core/canvas/
├── index.ts                        # 公开 API
├── types.ts                        # 类型定义
│
├── core/
│   ├── CanvasEngine.ts            # 画布引擎主类 (<300 行)
│   ├── CanvasState.ts             # 状态管理 (<200 行)
│   ├── CanvasEvents.ts            # 事件系统 (<200 行)
│   └── CanvasConfig.ts            # 配置 (<100 行)
│
├── elements/
│   ├── base/
│   │   ├── Element.ts             # 元素基类 (<200 行)
│   │   ├── ElementFactory.ts      # 元素工厂 (<150 行)
│   │   └── ElementRegistry.ts     # 元素注册 (<100 行)
│   │
│   ├── image/
│   │   └── ImageElement.ts        # 图片元素 (<200 行)
│   │
│   ├── text/
│   │   └── TextElement.ts         # 文本元素 (<250 行)
│   │
│   ├── shape/
│   │   ├── ShapeElement.ts        # 形状基类 (<150 行)
│   │   ├── RectElement.ts         # 矩形 (<100 行)
│   │   ├── CircleElement.ts       # 圆形 (<100 行)
│   │   └── PolygonElement.ts      # 多边形 (<150 行)
│   │
│   ├── path/
│   │   ├── PathElement.ts         # 路径元素 (<250 行)
│   │   ├── PathUtils.ts           # 路径工具 (<200 行)
│   │   └── BezierUtils.ts         # 贝塞尔工具 (<200 行)
│   │
│   └── freehand/
│       ├── FreehandElement.ts     # 手绘元素 (<200 行)
│       └── StrokeRenderer.ts      # 笔触渲染 (<150 行)
│
├── tools/
│   ├── base/
│   │   ├── Tool.ts                # 工具基类 (<150 行)
│   │   ├── ToolManager.ts         # 工具管理器 (<200 行)
│   │   └── ToolRegistry.ts        # 工具注册 (<100 行)
│   │
│   ├── select/
│   │   └── SelectTool.ts          # 选择工具 (<250 行)
│   │
│   ├── draw/
│   │   ├── PencilTool.ts          # 铅笔 (<200 行)
│   │   ├── PenTool.ts             # 钢笔 (<250 行)
│   │   ├── MarkerTool.ts          # 马克笔 (<150 行)
│   │   ├── HighlighterTool.ts     # 荧光笔 (<150 行)
│   │   └── EraserTool.ts          # 橡皮擦 (<200 行)
│   │
│   ├── shape/
│   │   ├── RectTool.ts            # 矩形工具 (<150 行)
│   │   ├── CircleTool.ts          # 圆形工具 (<150 行)
│   │   └── LineTool.ts            # 直线工具 (<150 行)
│   │
│   ├── path/
│   │   ├── PathTool.ts            # 路径工具 (<250 行)
│   │   └── PathEditTool.ts        # 路径编辑 (<300 行)
│
│   │
│   └── text/
│       └── TextTool.ts            # 文本工具 (<200 行)
│
├── renderers/
│   ├── base/
│   │   ├── Renderer.ts            # 渲染器接口 (<100 行)
│   │   └── RenderManager.ts       # 渲染管理器 (<200 行)
│   │
│   ├── fabric/
│   │   ├── FabricRenderer.ts      # Fabric 渲染器 (<300 行)
│   │   └── FabricAdapter.ts       # 适配器 (<200 行)
│   │
│   ├── freehand/
│   │   ├── FreehandRenderer.ts    # 手绘渲染器 (<250 行)
│   │   └── StrokeGenerator.ts     # 笔触生成 (<200 行)
│   │
│   └── vector/
│       ├── VectorRenderer.ts      # 矢量渲染器 (<250 行)
│       └── PaperAdapter.ts        # Paper.js 适配 (<200 行)
│
├── history/
│   ├── HistoryManager.ts          # 历史管理器 (<250 行)
│   ├── Command.ts                 # 命令基类 (<100 行)
│   └── commands/
│       ├── AddElementCommand.ts   # 添加元素 (<80 行)
│       ├── RemoveElementCommand.ts # 删除元素 (<80 行)
│       ├── TransformCommand.ts    # 变换命令 (<100 行)
│       ├── StyleCommand.ts        # 样式命令 (<100 行)
│       └── DrawCommand.ts         # 绘制命令 (<150 行)
│
├── export/
│   ├── Exporter.ts                # 导出器接口 (<80 行)
│   ├── PDFExporter.ts             # PDF 导出 (<200 行)
│   ├── PNGExporter.ts             # PNG 导出 (<150 行)
│   ├── SVGExporter.ts             # SVG 导出 (<200 行)
│   └── JSONExporter.ts            # JSON 导出 (<150 行)
│
├── input/
│   ├── InputManager.ts            # 输入管理器 (<250 行)
│   ├── PointerHandler.ts          # 指针处理 (<200 行)
│   ├── KeyboardHandler.ts         # 键盘处理 (<150 行)
│   ├── GestureHandler.ts          # 手势处理 (<200 行)
│   └── StylusHandler.ts           # 触控笔处理 (<150 行)
│
└── utils/
    ├── math.ts                    # 数学工具 (<200 行)
    ├── geometry.ts                # 几何工具 (<200 行)
    ├── color.ts                   # 颜色工具 (<100 行)
    └── simplify.ts                # 路径简化 (<100 行)
```

---

## 4. 核心抽象层

### 4.1 元素基类

```typescript
// @core/canvas/elements/base/Element.ts

import { nanoid } from 'nanoid';

// ==================== 类型定义 ====================

export interface Point {
  x: number;
  y: number;
}

export interface Bounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Transform {
  x: number;
  y: number;
  scaleX: number;
  scaleY: number;
  rotation: number;  // 角度
  skewX: number;
  skewY: number;
}

export interface ElementStyle {
  fill?: string | null;
  stroke?: string | null;
  strokeWidth?: number;
  opacity?: number;
  shadow?: {
    color: string;
    blur: number;
    offsetX: number;
    offsetY: number;
  } | null;
}

export type ElementType = 
  | 'image' 
  | 'text' 
  | 'rect' 
  | 'circle' 
  | 'polygon'
  | 'path' 
  | 'freehand'
  | 'group';

// ==================== 元素基类 ====================

export abstract class Element {
  readonly id: string;
  readonly type: ElementType;
  
  // 变换
  protected _transform: Transform = {
    x: 0,
    y: 0,
    scaleX: 1,
    scaleY: 1,
    rotation: 0,
    skewX: 0,
    skewY: 0,
  };
  
  // 样式
  protected _style: ElementStyle = {
    fill: null,
    stroke: '#000000',
    strokeWidth: 1,
    opacity: 1,
    shadow: null,
  };
  
  // 状态
  protected _visible: boolean = true;
  protected _locked: boolean = false;
  protected _selectable: boolean = true;
  
  // 元数据
  protected _name: string = '';
  protected _layerIndex: number = 0;
  
  constructor(type: ElementType, id?: string) {
    this.id = id || nanoid();
    this.type = type;
  }
  
  // ==================== 变换 ====================
  
  get transform(): Readonly<Transform> {
    return { ...this._transform };
  }
  
  setTransform(transform: Partial<Transform>): void {
    this._transform = { ...this._transform, ...transform };
    this.onTransformChange();
  }
  
  moveTo(x: number, y: number): void {
    this._transform.x = x;
    this._transform.y = y;
    this.onTransformChange();
  }
  
  moveBy(dx: number, dy: number): void {
    this._transform.x += dx;
    this._transform.y += dy;
    this.onTransformChange();
  }
  
  scaleTo(scaleX: number, scaleY: number): void {
    this._transform.scaleX = scaleX;
    this._transform.scaleY = scaleY;
    this.onTransformChange();
  }
  
  rotateTo(angle: number): void {
    this._transform.rotation = angle;
    this.onTransformChange();
  }
  
  rotateBy(angle: number): void {
    this._transform.rotation += angle;
    this.onTransformChange();
  }
  
  // ==================== 样式 ====================
  
  get style(): Readonly<ElementStyle> {
    return { ...this._style };
  }
  
  setStyle(style: Partial<ElementStyle>): void {
    this._style = { ...this._style, ...style };
    this.onStyleChange();
  }
  
  // ==================== 状态 ====================
  
  get visible(): boolean { return this._visible; }
  set visible(value: boolean) { 
    this._visible = value;
    this.onVisibilityChange();
  }
  
  get locked(): boolean { return this._locked; }
  set locked(value: boolean) { 
    this._locked = value;
  }
  
  get selectable(): boolean { return this._selectable && !this._locked; }
  
  // ==================== 抽象方法 ====================
  
  /**
   * 获取边界框
   */
  abstract getBounds(): Bounds;
  
  /**
   * 点击测试
   */
  abstract containsPoint(point: Point): boolean;
  
  /**
   * 序列化
   */
  abstract serialize(): object;
  
  /**
   * 反序列化
   */
  abstract deserialize(data: object): void;
  
  /**
   * 克隆
   */
  abstract clone(): Element;
  
  // ==================== 生命周期钩子 ====================
  
  protected onTransformChange(): void {}
  protected onStyleChange(): void {}
  protected onVisibilityChange(): void {}
  
  // ==================== 渲染适配 ====================
  
  /**
   * 转换为 Fabric.js 对象
   */
  abstract toFabricObject(): fabric.Object;
  
  /**
   * 从 Fabric.js 对象同步状态
   */
  abstract syncFromFabricObject(obj: fabric.Object): void;
  
  /**
   * 转换为 SVG
   */
  abstract toSVG(): string;
}
```

### 4.2 工具基类

```typescript
// @core/canvas/tools/base/Tool.ts

import { Element, Point } from '../../elements/base/Element';
import { CanvasEngine } from '../../core/CanvasEngine';

// ==================== 类型定义 ====================

export interface ToolOptions {
  // 通用选项
  cursor?: string;
  
  // 画笔选项
  size?: number;
  color?: string;
  opacity?: number;
  
  // 其他选项
  [key: string]: any;
}

export interface PointerEvent {
  point: Point;
  pressure: number;      // 0-1, 压感
  tiltX: number;         // 触控笔倾斜
  tiltY: number;
  pointerType: 'mouse' | 'pen' | 'touch';
  button: number;        // 0=左键, 1=中键, 2=右键
  shiftKey: boolean;
  ctrlKey: boolean;
  altKey: boolean;
  metaKey: boolean;
}

export type ToolType = 
  | 'select'
  | 'pencil'
  | 'pen'
  | 'marker'
  | 'highlighter'
  | 'eraser'
  | 'rect'
  | 'circle'
  | 'line'
  | 'path'
  | 'path-edit'
  | 'text';

// ==================== 工具基类 ====================

export abstract class Tool {
  readonly type: ToolType;
  protected engine: CanvasEngine;
  protected options: ToolOptions;
  protected isActive: boolean = false;
  
  constructor(type: ToolType, engine: CanvasEngine, options: ToolOptions = {}) {
    this.type = type;
    this.engine = engine;
    this.options = { ...this.getDefaultOptions(), ...options };
  }
  
  // ==================== 生命周期 ====================
  
  /**
   * 工具激活时调用
   */
  activate(): void {
    this.isActive = true;
    this.engine.setCursor(this.options.cursor || 'default');
    this.onActivate();
  }
  
  /**
   * 工具停用时调用
   */
  deactivate(): void {
    this.isActive = false;
    this.onDeactivate();
  }
  
  // ==================== 事件处理 ====================
  
  /**
   * 指针按下
   */
  abstract onPointerDown(event: PointerEvent): void;
  
  /**
   * 指针移动
   */
  abstract onPointerMove(event: PointerEvent): void;
  
  /**
   * 指针抬起
   */
  abstract onPointerUp(event: PointerEvent): void;
  
  /**
   * 双击
   */
  onDoubleClick(event: PointerEvent): void {}
  
  /**
   * 键盘事件
   */
  onKeyDown(event: KeyboardEvent): void {}
  onKeyUp(event: KeyboardEvent): void {}
  
  // ==================== 选项 ====================
  
  getOptions(): ToolOptions {
    return { ...this.options };
  }
  
  setOptions(options: Partial<ToolOptions>): void {
    this.options = { ...this.options, ...options };
    this.onOptionsChange();
  }
  
  protected abstract getDefaultOptions(): ToolOptions;
  
  // ==================== 钩子 ====================
  
  protected onActivate(): void {}
  protected onDeactivate(): void {}
  protected onOptionsChange(): void {}
  
  // ==================== 辅助方法 ====================

  
  /**
   * 获取光标样式
   */
  getCursor(): string {
    return this.options.cursor || 'default';
  }
  
  /**
   * 获取工具图标
   */
  abstract getIcon(): string;
  
  /**
   * 获取工具名称
   */
  abstract getName(): string;
  
  /**
   * 获取快捷键
   */
  abstract getShortcut(): string;
}
```

### 4.3 渲染器接口

```typescript
// @core/canvas/renderers/base/Renderer.ts

import { Element } from '../../elements/base/Element';

export interface RenderContext {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  scale: number;
  offset: { x: number; y: number };
}

export interface RenderOptions {
  quality: 'low' | 'medium' | 'high';
  showBounds: boolean;
  showGrid: boolean;
}

/**
 * 渲染器接口
 * 
 * 不同的渲染引擎实现此接口，实现统一的渲染 API
 */
export interface IRenderer {
  /**
   * 初始化渲染器
   */
  initialize(container: HTMLElement, width: number, height: number): void;
  
  /**
   * 销毁渲染器
   */
  destroy(): void;
  
  /**
   * 调整大小
   */
  resize(width: number, height: number): void;
  
  /**
   * 添加元素
   */
  addElement(element: Element): void;
  
  /**
   * 移除元素
   */
  removeElement(element: Element): void;
  
  /**
   * 更新元素
   */
  updateElement(element: Element): void;
  
  /**
   * 清空画布
   */
  clear(): void;
  
  /**
   * 渲染
   */
  render(): void;
  
  /**
   * 导出为图片
   */
  toDataURL(format: 'png' | 'jpeg', quality?: number): string;
  
  /**
   * 导出为 SVG
   */
  toSVG(): string;
  
  /**
   * 获取原生画布对象
   */
  getNativeCanvas(): HTMLCanvasElement;
  
  /**
   * 获取原生引擎对象 (Fabric.Canvas, Konva.Stage 等)
   */
  getNativeEngine(): any;
}
```

---

## 5. 渲染引擎设计

### 5.1 多层渲染架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    多层渲染架构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Container                             │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  Layer 4: UI Layer (guides, selection)          │    │   │
│  │  │  ┌─────────────────────────────────────────┐    │    │   │
│  │  │  │  选择框, 参考线, 标尺                    │    │    │   │
│  │  │  └─────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                           ↑                              │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  Layer 3: Drawing Layer (active drawing)        │    │   │
│  │  │  ┌─────────────────────────────────────────┐    │    │   │
│  │  │  │  当前绘制中的路径 (实时渲染)             │    │    │   │
│  │  │  └─────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                           ↑                              │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  Layer 2: Content Layer (elements)              │    │   │
│  │  │  ┌─────────────────────────────────────────┐    │    │   │
│  │  │  │  图片, 文本, 形状, 完成的路径            │    │    │   │
│  │  │  └─────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                           ↑                              │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  Layer 1: Background Layer                      │    │   │
│  │  │  ┌─────────────────────────────────────────┐    │    │   │
│  │  │  │  背景颜色/图片/图案                      │    │    │   │
│  │  │  └─────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  优势:                                                          │
│  • 手绘时只需重绘 Drawing Layer，不影响其他层                    │
│  • UI 层独立更新，不触发内容重绘                                 │
│  • 可针对不同层使用不同渲染策略                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Fabric.js 渲染器

```typescript
// @core/canvas/renderers/fabric/FabricRenderer.ts

import { fabric } from 'fabric';
import { IRenderer, RenderContext } from '../base/Renderer';
import { Element } from '../../elements/base/Element';

export class FabricRenderer implements IRenderer {
  private canvas: fabric.Canvas | null = null;
  private container: HTMLElement | null = null;
  private elements: Map<string, fabric.Object> = new Map();
  
  // ==================== 初始化 ====================
  
  initialize(container: HTMLElement, width: number, height: number): void {
    this.container = container;
    
    // 创建 canvas 元素
    const canvasEl = document.createElement('canvas');
    canvasEl.id = 'fabric-canvas';
    container.appendChild(canvasEl);
    
    // 初始化 Fabric.js
    this.canvas = new fabric.Canvas(canvasEl, {
      width,
      height,
      backgroundColor: '#ffffff',
      selection: true,
      preserveObjectStacking: true,
      enableRetinaScaling: true,
      stopContextMenu: true,
      fireRightClick: true,
    });
    
    this.setupEvents();
  }
  
  destroy(): void {
    if (this.canvas) {
      this.canvas.dispose();
      this.canvas = null;
    }
    if (this.container) {
      this.container.innerHTML = '';
    }
    this.elements.clear();
  }
  
  resize(width: number, height: number): void {
    if (!this.canvas) return;
    this.canvas.setWidth(width);
    this.canvas.setHeight(height);
    this.canvas.renderAll();
  }
  
  // ==================== 元素操作 ====================
  
  addElement(element: Element): void {
    if (!this.canvas) return;
    
    const fabricObj = element.toFabricObject();
    fabricObj.set('data', { elementId: element.id });
    
    this.canvas.add(fabricObj);
    this.elements.set(element.id, fabricObj);
  }
  
  removeElement(element: Element): void {
    if (!this.canvas) return;
    
    const fabricObj = this.elements.get(element.id);
    if (fabricObj) {
      this.canvas.remove(fabricObj);
      this.elements.delete(element.id);
    }
  }
  
  updateElement(element: Element): void {
    if (!this.canvas) return;
    
    const fabricObj = this.elements.get(element.id);
    if (fabricObj) {
      // 同步元素状态到 Fabric 对象
      const transform = element.transform;
      const style = element.style;
      
      fabricObj.set({
        left: transform.x,
        top: transform.y,
        scaleX: transform.scaleX,
        scaleY: transform.scaleY,
        angle: transform.rotation,
        opacity: style.opacity,
        fill: style.fill,
        stroke: style.stroke,
        strokeWidth: style.strokeWidth,
      });
      
      fabricObj.setCoords();
    }
    
    this.canvas.renderAll();
  }
  
  // ==================== 渲染 ====================
  
  clear(): void {
    if (!this.canvas) return;
    this.canvas.clear();
    this.elements.clear();
  }
  
  render(): void {
    if (!this.canvas) return;
    this.canvas.renderAll();
  }
  
  // ==================== 导出 ====================
  
  toDataURL(format: 'png' | 'jpeg', quality = 1): string {
    if (!this.canvas) return '';
    return this.canvas.toDataURL({
      format,
      quality,
      multiplier: 2, // 2x 分辨率
    });
  }
  
  toSVG(): string {
    if (!this.canvas) return '';
    return this.canvas.toSVG();
  }
  
  // ==================== 访问器 ====================
  
  getNativeCanvas(): HTMLCanvasElement {
    return this.canvas?.getElement() as HTMLCanvasElement;
  }
  
  getNativeEngine(): fabric.Canvas {
    return this.canvas!;
  }
  
  // ==================== 私有方法 ====================
  
  private setupEvents(): void {
    if (!this.canvas) return;
    
    // 对象选择
    this.canvas.on('selection:created', (e) => {
      this.onSelectionChange(e.selected);
    });
    
    this.canvas.on('selection:updated', (e) => {
      this.onSelectionChange(e.selected);
    });
    
    this.canvas.on('selection:cleared', () => {
      this.onSelectionChange([]);
    });
    
    // 对象修改
    this.canvas.on('object:modified', (e) => {
      if (e.target) {
        this.onObjectModified(e.target);
      }
    });
  }
  
  private onSelectionChange(objects: fabric.Object[] | undefined): void {
    // 通知状态管理器
  }
  
  private onObjectModified(obj: fabric.Object): void {
    // 同步到元素状态
    const elementId = (obj as any).data?.elementId;
    if (elementId) {
      // 触发元素更新事件
    }
  }
}
```

---

## 6. 工具系统设计

### 6.1 工具管理器

```typescript
// @core/canvas/tools/base/ToolManager.ts

import { Tool, ToolType, PointerEvent } from './Tool';
import { CanvasEngine } from '../../core/CanvasEngine';

export class ToolManager {
  private tools: Map<ToolType, Tool> = new Map();
  private activeTool: Tool | null = null;
  private engine: CanvasEngine;
  
  constructor(engine: CanvasEngine) {
    this.engine = engine;
  }
  
  // ==================== 工具注册 ====================
  
  register(tool: Tool): void {
    this.tools.set(tool.type, tool);
  }
  
  unregister(type: ToolType): void {
    if (this.activeTool?.type === type) {
      this.activeTool.deactivate();
      this.activeTool = null;
    }
    this.tools.delete(type);
  }
  
  // ==================== 工具切换 ====================
  
  setActiveTool(type: ToolType): Tool | null {
    const tool = this.tools.get(type);
    if (!tool) {
      console.warn(`Tool not found: ${type}`);
      return null;
    }
    
    // 停用当前工具
    if (this.activeTool) {
      this.activeTool.deactivate();
    }
    
    // 激活新工具
    this.activeTool = tool;
    tool.activate();

    
    // 触发工具切换事件
    this.engine.emit('tool:change', { tool: type });
    
    return tool;
  }
  
  getActiveTool(): Tool | null {
    return this.activeTool;
  }
  
  getTool(type: ToolType): Tool | null {
    return this.tools.get(type) || null;
  }
  
  getAllTools(): Tool[] {
    return Array.from(this.tools.values());
  }
  
  // ==================== 事件分发 ====================
  
  handlePointerDown(event: PointerEvent): void {
    this.activeTool?.onPointerDown(event);
  }
  
  handlePointerMove(event: PointerEvent): void {
    this.activeTool?.onPointerMove(event);
  }
  
  handlePointerUp(event: PointerEvent): void {
    this.activeTool?.onPointerUp(event);
  }
  
  handleDoubleClick(event: PointerEvent): void {
    this.activeTool?.onDoubleClick(event);
  }
  
  handleKeyDown(event: KeyboardEvent): void {
    // 检查快捷键切换工具
    const tool = this.findToolByShortcut(event.key);
    if (tool && !event.ctrlKey && !event.metaKey) {
      this.setActiveTool(tool.type);
      return;
    }
    
    this.activeTool?.onKeyDown(event);
  }
  
  handleKeyUp(event: KeyboardEvent): void {
    this.activeTool?.onKeyUp(event);
  }
  
  // ==================== 辅助方法 ====================
  
  private findToolByShortcut(key: string): Tool | null {
    for (const tool of this.tools.values()) {
      if (tool.getShortcut().toLowerCase() === key.toLowerCase()) {
        return tool;
      }
    }
    return null;
  }
}
```

### 6.2 选择工具

```typescript
// @core/canvas/tools/select/SelectTool.ts

import { Tool, ToolType, ToolOptions, PointerEvent } from '../base/Tool';
import { Element, Point } from '../../elements/base/Element';
import { CanvasEngine } from '../../core/CanvasEngine';

interface SelectionState {
  isDragging: boolean;
  isResizing: boolean;
  isRotating: boolean;
  startPoint: Point;
  lastPoint: Point;
  selectedElements: Element[];
  handle: string | null;  // 'tl', 'tr', 'bl', 'br', 'rotate', etc.
}

export class SelectTool extends Tool {
  private state: SelectionState = {
    isDragging: false,
    isResizing: false,
    isRotating: false,
    startPoint: { x: 0, y: 0 },
    lastPoint: { x: 0, y: 0 },
    selectedElements: [],
    handle: null,
  };
  
  constructor(engine: CanvasEngine, options: ToolOptions = {}) {
    super('select', engine, options);
  }
  
  // ==================== 默认选项 ====================
  
  protected getDefaultOptions(): ToolOptions {
    return {
      cursor: 'default',
    };
  }
  
  // ==================== 事件处理 ====================
  
  onPointerDown(event: PointerEvent): void {
    const { point } = event;
    this.state.startPoint = point;
    this.state.lastPoint = point;
    
    // 检查是否点击在控制手柄上
    const handle = this.getHandleAtPoint(point);
    if (handle) {
      this.state.handle = handle;
      if (handle === 'rotate') {
        this.state.isRotating = true;
      } else {
        this.state.isResizing = true;
      }
      return;
    }
    
    // 检查是否点击在元素上
    const element = this.engine.getElementAtPoint(point);
    
    if (element) {
      // Shift 键多选
      if (event.shiftKey) {
        this.engine.toggleSelection(element);
      } else if (!this.engine.isSelected(element)) {
        this.engine.setSelection([element]);
      }
      
      this.state.isDragging = true;
      this.state.selectedElements = this.engine.getSelectedElements();
    } else {
      // 点击空白区域，清除选择或开始框选
      if (!event.shiftKey) {
        this.engine.clearSelection();
      }
      this.startMarquee(point);
    }
  }
  
  onPointerMove(event: PointerEvent): void {
    const { point } = event;
    const dx = point.x - this.state.lastPoint.x;
    const dy = point.y - this.state.lastPoint.y;
    
    if (this.state.isDragging) {
      // 移动选中的元素
      for (const element of this.state.selectedElements) {
        element.moveBy(dx, dy);
      }
      this.engine.render();
    } else if (this.state.isResizing) {
      // 缩放选中的元素
      this.handleResize(point);
    } else if (this.state.isRotating) {
      // 旋转选中的元素
      this.handleRotate(point);
    } else {
      // 更新光标
      this.updateCursor(point);
    }
    
    this.state.lastPoint = point;
  }
  
  onPointerUp(event: PointerEvent): void {
    if (this.state.isDragging || this.state.isResizing || this.state.isRotating) {
      // 记录历史
      this.engine.history.commit();
    }
    
    this.resetState();
  }
  
  onDoubleClick(event: PointerEvent): void {
    const element = this.engine.getElementAtPoint(event.point);
    
    if (element?.type === 'text') {
      // 进入文本编辑模式
      this.engine.enterTextEditMode(element);
    } else if (element?.type === 'path' || element?.type === 'freehand') {
      // 进入路径编辑模式
      this.engine.setActiveTool('path-edit');
    }
  }
  
  onKeyDown(event: KeyboardEvent): void {
    const selected = this.engine.getSelectedElements();
    if (selected.length === 0) return;
    
    switch (event.key) {
      case 'Delete':
      case 'Backspace':
        this.engine.deleteElements(selected);
        break;
        
      case 'ArrowUp':
        this.moveSelection(0, event.shiftKey ? -10 : -1);
        break;
      case 'ArrowDown':
        this.moveSelection(0, event.shiftKey ? 10 : 1);
        break;
      case 'ArrowLeft':
        this.moveSelection(event.shiftKey ? -10 : -1, 0);
        break;
      case 'ArrowRight':
        this.moveSelection(event.shiftKey ? 10 : 1, 0);
        break;
        
      case 'd':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault();
          this.engine.duplicateElements(selected);
        }
        break;
    }
  }
  
  // ==================== 辅助方法 ====================
  
  private resetState(): void {
    this.state = {
      isDragging: false,
      isResizing: false,
      isRotating: false,
      startPoint: { x: 0, y: 0 },
      lastPoint: { x: 0, y: 0 },
      selectedElements: [],
      handle: null,
    };
  }
  
  private getHandleAtPoint(point: Point): string | null {
    // 检测控制点
    // 返回 'tl', 'tr', 'bl', 'br', 'tm', 'bm', 'lm', 'rm', 'rotate' 或 null
    return null;
  }
  
  private handleResize(point: Point): void {
    // 实现缩放逻辑
  }
  
  private handleRotate(point: Point): void {
    // 实现旋转逻辑
  }
  
  private updateCursor(point: Point): void {
    const handle = this.getHandleAtPoint(point);
    if (handle) {
      // 设置对应的光标
      const cursors: Record<string, string> = {
        'tl': 'nwse-resize',
        'tr': 'nesw-resize',
        'bl': 'nesw-resize',
        'br': 'nwse-resize',
        'tm': 'ns-resize',
        'bm': 'ns-resize',
        'lm': 'ew-resize',
        'rm': 'ew-resize',
        'rotate': 'crosshair',
      };
      this.engine.setCursor(cursors[handle] || 'default');
    } else {
      const element = this.engine.getElementAtPoint(point);
      this.engine.setCursor(element ? 'move' : 'default');
    }
  }
  
  private startMarquee(point: Point): void {
    // 开始框选
  }
  
  private moveSelection(dx: number, dy: number): void {
    for (const element of this.engine.getSelectedElements()) {
      element.moveBy(dx, dy);
    }
    this.engine.render();
    this.engine.history.commit();
  }
  
  // ==================== 元数据 ====================
  
  getIcon(): string {
    return 'cursor';
  }
  
  getName(): string {
    return 'Select';
  }
  
  getShortcut(): string {
    return 'v';
  }
}
```

---

## 7. 手绘与画笔系统

### 7.1 核心原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    手绘系统原理                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入阶段:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Pointer Events → Input Points                          │   │
│  │                                                          │
│  │  每个输入点包含:                                          │
│  │  • x, y 坐标                                             │
│  │  • pressure (压感, 0-1)                                  │
│  │  • tiltX, tiltY (倾斜角度)                               │
│  │  • timestamp (时间戳)                                    │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  平滑阶段:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Smoothing Algorithm                                     │
│  │                                                          │
│  │  • 移动平均 (Moving Average)                             │
│  │  • 贝塞尔拟合 (Bezier Fitting)                           │
│  │  • Catmull-Rom 样条                                      │
│  │                                                          │
│  │  输出: 平滑的点序列                                       │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  笔触生成阶段:                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  perfect-freehand                                        │
│  │                                                          │
│  │  输入: 点序列 [{x, y, pressure}, ...]                    │
│  │  输出: 轮廓点序列 (多边形)                                │
│  │                                                          │
│  │  特性:                                                   │
│  │  • 根据压感变化笔画粗细                                   │
│  │  • 自然的起笔和收笔效果                                   │
│  │  • 笔画中间自然的粗细变化                                 │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  渲染阶段:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Canvas Rendering                                        │
│  │                                                          │
│  │  • 实时渲染: 边画边显示                                   │
│  │  • 最终渲染: 简化路径后渲染                               │
│  │                                                          │
│  │  优化:                                                   │
│  │  • 分层渲染 (Drawing Layer)                              │
│  │  • 路径简化 (Simplify.js)                                │
│  │  • 增量渲染 (只重绘新增部分)                              │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 铅笔工具实现

```typescript
// @core/canvas/tools/draw/PencilTool.ts

import { Tool, ToolType, ToolOptions, PointerEvent } from '../base/Tool';
import { Point } from '../../elements/base/Element';
import { FreehandElement } from '../../elements/freehand/FreehandElement';
import { CanvasEngine } from '../../core/CanvasEngine';
import getStroke from 'perfect-freehand';

interface StrokePoint {
  x: number;
  y: number;
  pressure: number;
}

export class PencilTool extends Tool {
  private isDrawing: boolean = false;
  private points: StrokePoint[] = [];
  private currentElement: FreehandElement | null = null;
  private drawingCanvas: HTMLCanvasElement | null = null;
  private drawingCtx: CanvasRenderingContext2D | null = null;
  
  constructor(engine: CanvasEngine, options: ToolOptions = {}) {
    super('pencil', engine, options);
  }
  
  // ==================== 默认选项 ====================
  
  protected getDefaultOptions(): ToolOptions {
    return {
      cursor: 'crosshair',
      size: 4,
      color: '#000000',
      opacity: 1,
      thinning: 0.5,        // 压感影响程度
      smoothing: 0.5,       // 平滑程度
      streamline: 0.5,      // 线条流畅度
      simulatePressure: true, // 模拟压感 (鼠标)
    };
  }
  
  // ==================== 生命周期 ====================
  
  protected onActivate(): void {
    this.setupDrawingLayer();
  }
  
  protected onDeactivate(): void {
    this.cleanupDrawingLayer();
  }
  
  // ==================== 事件处理 ====================
  
  onPointerDown(event: PointerEvent): void {
    this.isDrawing = true;
    this.points = [];
    
    // 创建新的手绘元素
    this.currentElement = new FreehandElement();
    this.currentElement.setStyle({
      stroke: this.options.color,
      strokeWidth: this.options.size,
      opacity: this.options.opacity,
    });
    
    // 记录第一个点
    this.addPoint(event);
    
    // 开始实时渲染
    this.renderStroke();
  }
  
  onPointerMove(event: PointerEvent): void {
    if (!this.isDrawing) return;
    
    // 添加新点
    this.addPoint(event);
    
    // 实时渲染
    this.renderStroke();
  }
  
  onPointerUp(event: PointerEvent): void {
    if (!this.isDrawing) return;
    
    this.isDrawing = false;
    
    // 添加最后一个点
    this.addPoint(event);
    
    // 完成绘制
    this.finishStroke();
  }
  
  // ==================== 核心绘制逻辑 ====================
  
  private addPoint(event: PointerEvent): void {
    const pressure = this.options.simulatePressure && event.pointerType === 'mouse'
      ? this.simulatePressure(event.point)
      : event.pressure;
    
    this.points.push({
      x: event.point.x,
      y: event.point.y,
      pressure,
    });
  }
  
  private simulatePressure(point: Point): number {
    // 基于速度模拟压感
    if (this.points.length < 2) return 0.5;
    
    const lastPoint = this.points[this.points.length - 1];
    const dx = point.x - lastPoint.x;
    const dy = point.y - lastPoint.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // 速度越快，压感越小
    const pressure = Math.max(0.1, Math.min(1, 1 - distance / 50));
    return pressure;
  }
  
  private renderStroke(): void {
    if (!this.drawingCtx || this.points.length < 2) return;
    
    // 使用 perfect-freehand 生成笔触轮廓
    const outlinePoints = getStroke(this.points, {
      size: this.options.size,
      thinning: this.options.thinning,
      smoothing: this.options.smoothing,
      streamline: this.options.streamline,
      simulatePressure: false, // 我们已经处理过了
    });
    
    // 清空绘制层
    this.drawingCtx.clearRect(
      0, 0,
      this.drawingCanvas!.width,
      this.drawingCanvas!.height
    );
    
    // 绘制笔触
    this.drawingCtx.fillStyle = this.options.color;
    this.drawingCtx.globalAlpha = this.options.opacity;
    
    this.drawingCtx.beginPath();
    
    if (outlinePoints.length > 0) {
      this.drawingCtx.moveTo(outlinePoints[0][0], outlinePoints[0][1]);
      
      for (let i = 1; i < outlinePoints.length; i++) {
        this.drawingCtx.lineTo(outlinePoints[i][0], outlinePoints[i][1]);
      }
      
      this.drawingCtx.closePath();
      this.drawingCtx.fill();
    }
  }
  
  private finishStroke(): void {
    if (!this.currentElement || this.points.length < 2) {
      this.currentElement = null;
      this.clearDrawingLayer();
      return;
    }
    
    // 简化路径点
    const simplifiedPoints = this.simplifyPoints(this.points);
    
    // 设置元素数据
    this.currentElement.setPoints(simplifiedPoints);
    this.currentElement.setStrokeOptions({
      size: this.options.size,
      thinning: this.options.thinning,
      smoothing: this.options.smoothing,
      streamline: this.options.streamline,
    });
    
    // 添加到画布
    this.engine.addElement(this.currentElement);
    this.engine.history.commit();
    
    // 清理
    this.currentElement = null;
    this.points = [];
    this.clearDrawingLayer();
  }
  
  private simplifyPoints(points: StrokePoint[]): StrokePoint[] {
    // 使用 Douglas-Peucker 算法简化路径
    // 保留压感信息
    if (points.length < 10) return points;
    
    // 简化阈值
    const tolerance = 1.0;
    
    // 实现简化算法...
    return points; // 简化版，实际需要实现算法
  }
  
  // ==================== 绘制层管理 ====================
  
  private setupDrawingLayer(): void {
    const mainCanvas = this.engine.renderer.getNativeCanvas();
    
    this.drawingCanvas = document.createElement('canvas');
    this.drawingCanvas.width = mainCanvas.width;
    this.drawingCanvas.height = mainCanvas.height;
    this.drawingCanvas.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: none;
    `;
    
    mainCanvas.parentElement?.appendChild(this.drawingCanvas);
    this.drawingCtx = this.drawingCanvas.getContext('2d');
  }
  
  private clearDrawingLayer(): void {
    if (this.drawingCtx && this.drawingCanvas) {
      this.drawingCtx.clearRect(0, 0, this.drawingCanvas.width, this.drawingCanvas.height);
    }
  }
  
  private cleanupDrawingLayer(): void {
    if (this.drawingCanvas) {
      this.drawingCanvas.remove();
      this.drawingCanvas = null;
      this.drawingCtx = null;
    }
  }
  
  // ==================== 元数据 ====================
  
  getIcon(): string {
    return 'pencil';
  }
  
  getName(): string {
    return 'Pencil';
  }
  
  getShortcut(): string {
    return 'p';
  }
}
```

### 7.3 手绘元素

```typescript
// @core/canvas/elements/freehand/FreehandElement.ts

import { fabric } from 'fabric';
import { Element, ElementType, Bounds, Point } from '../base/Element';
import getStroke from 'perfect-freehand';

interface StrokePoint {
  x: number;
  y: number;
  pressure: number;
}

interface StrokeOptions {
  size: number;
  thinning: number;
  smoothing: number;
  streamline: number;
}

export class FreehandElement extends Element {
  private points: StrokePoint[] = [];
  private strokeOptions: StrokeOptions = {
    size: 4,
    thinning: 0.5,
    smoothing: 0.5,
    streamline: 0.5,
  };
  
  // 缓存
  private cachedOutline: [number, number][] | null = null;
  private cachedPath: string | null = null;
  
  constructor(id?: string) {
    super('freehand', id);
  }
  
  // ==================== 数据设置 ====================
  
  setPoints(points: StrokePoint[]): void {
    this.points = points;
    this.invalidateCache();
  }
  
  setStrokeOptions(options: Partial<StrokeOptions>): void {
    this.strokeOptions = { ...this.strokeOptions, ...options };
    this.invalidateCache();
  }
  
  // ==================== 轮廓计算 ====================
  
  private getOutline(): [number, number][] {
    if (this.cachedOutline) return this.cachedOutline;
    
    this.cachedOutline = getStroke(this.points, {
      size: this.strokeOptions.size,
      thinning: this.strokeOptions.thinning,
      smoothing: this.strokeOptions.smoothing,
      streamline: this.strokeOptions.streamline,
      simulatePressure: false,
    });
    
    return this.cachedOutline;
  }
  
  private getPathData(): string {
    if (this.cachedPath) return this.cachedPath;
    
    const outline = this.getOutline();
    if (outline.length === 0) return '';
    
    // 转换为 SVG 路径
    const d = outline.reduce(
      (acc, [x, y], i, arr) => {
        if (i === 0) return `M ${x},${y}`;
        
        // 使用贝塞尔曲线平滑
        const [px, py] = arr[i - 1];
        const cx = (px + x) / 2;
        const cy = (py + y) / 2;
        
        return `${acc} Q ${px},${py} ${cx},${cy}`;
      },
      ''
    );
    
    this.cachedPath = d + ' Z';
    return this.cachedPath;
  }
  
  private invalidateCache(): void {
    this.cachedOutline = null;
    this.cachedPath = null;
  }
  
  // ==================== Element 实现 ====================
  
  getBounds(): Bounds {
    if (this.points.length === 0) {
      return { x: 0, y: 0, width: 0, height: 0 };
    }
    
    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;
    
    for (const point of this.points) {
      minX = Math.min(minX, point.x);
      minY = Math.min(minY, point.y);
      maxX = Math.max(maxX, point.x);
      maxY = Math.max(maxY, point.y);
    }
    
    // 考虑笔画宽度
    const padding = this.strokeOptions.size / 2;
    
    return {
      x: minX - padding,
      y: minY - padding,
      width: maxX - minX + padding * 2,
      height: maxY - minY + padding * 2,
    };
  }
  
  containsPoint(point: Point): boolean {
    // 简化实现: 检查是否在边界框内
    const bounds = this.getBounds();
    return (
      point.x >= bounds.x &&
      point.x <= bounds.x + bounds.width &&
      point.y >= bounds.y &&
      point.y <= bounds.y + bounds.height
    );
  }
  
  serialize(): object {
    return {
      id: this.id,
      type: this.type,
      points: this.points,
      strokeOptions: this.strokeOptions,
      transform: this._transform,
      style: this._style,
    };
  }
  
  deserialize(data: any): void {
    this.points = data.points || [];
    this.strokeOptions = data.strokeOptions || this.strokeOptions;
    this._transform = data.transform || this._transform;
    this._style = data.style || this._style;
    this.invalidateCache();
  }
  
  clone(): FreehandElement {
    const cloned = new FreehandElement();
    cloned.points = [...this.points];
    cloned.strokeOptions = { ...this.strokeOptions };
    cloned._transform = { ...this._transform };
    cloned._style = { ...this._style };
    return cloned;
  }
  
  // ==================== Fabric.js 适配 ====================
  
  toFabricObject(): fabric.Object {
    const pathData = this.getPathData();
    
    const path = new fabric.Path(pathData, {
      fill: this._style.stroke, // 手绘用填充而非描边

      fill: this._style.stroke, // 手绘用填充而非描边
      stroke: null,
      opacity: this._style.opacity,
      left: this._transform.x,
      top: this._transform.y,
      scaleX: this._transform.scaleX,
      scaleY: this._transform.scaleY,
      angle: this._transform.rotation,
      selectable: this._selectable,
      evented: !this._locked,
    });
    
    return path;
  }
  
  syncFromFabricObject(obj: fabric.Object): void {
    this._transform.x = obj.left || 0;
    this._transform.y = obj.top || 0;
    this._transform.scaleX = obj.scaleX || 1;
    this._transform.scaleY = obj.scaleY || 1;
    this._transform.rotation = obj.angle || 0;
  }
  
  toSVG(): string {
    const pathData = this.getPathData();
    const transform = this._transform;
    
    return `
      <path
        d="${pathData}"
        fill="${this._style.stroke}"
        opacity="${this._style.opacity}"
        transform="translate(${transform.x}, ${transform.y}) 
                   rotate(${transform.rotation}) 
                   scale(${transform.scaleX}, ${transform.scaleY})"
      />
    `;
  }
}
```

### 7.4 画笔类型对比

```
┌─────────────────────────────────────────────────────────────────┐
│                    画笔类型对比                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Pencil (铅笔)                                           │   │
│  │  ─────────────                                           │   │
│  │  特点: 压感影响线条粗细，自然的手绘效果                    │   │
│  │  参数: size=4, thinning=0.5, smoothing=0.5               │   │
│  │  效果: ～～～～～                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Pen (钢笔)                                              │   │
│  │  ─────────────                                           │   │
│  │  特点: 均匀线条，高平滑度，适合签名                       │   │
│  │  参数: size=3, thinning=0, smoothing=0.8                 │   │
│  │  效果: ─────────                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Marker (马克笔)                                         │   │
│  │  ─────────────                                           │   │
│  │  特点: 宽扁笔触，略有透明，可叠加                         │   │
│  │  参数: size=20, thinning=0.2, opacity=0.6                │   │
│  │  效果: ████████                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Highlighter (荧光笔)                                    │   │
│  │  ─────────────                                           │   │
│  │  特点: 高透明度，亮色，混合模式                           │   │
│  │  参数: size=30, opacity=0.3, blendMode=multiply          │   │
│  │  效果: ░░░░░░░░ (半透明覆盖)                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Eraser (橡皮擦)                                         │   │
│  │  ─────────────                                           │   │
│  │  特点: 擦除已有内容，可调节大小                           │   │
│  │  实现: composite operation = destination-out              │   │
│  │  效果: (清除区域)                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. 矢量图支持

### 8.1 路径元素

```typescript
// @core/canvas/elements/path/PathElement.ts

import { fabric } from 'fabric';
import { Element, ElementType, Bounds, Point } from '../base/Element';

// ==================== 类型定义 ====================

export interface PathPoint {
  x: number;
  y: number;
  handleIn?: Point;   // 入方向控制点
  handleOut?: Point;  // 出方向控制点
  type: 'corner' | 'smooth' | 'symmetric';
}

export interface PathSegment {
  type: 'M' | 'L' | 'C' | 'Q' | 'Z';
  points: number[];
}

// ==================== 路径元素 ====================

export class PathElement extends Element {
  private nodes: PathPoint[] = [];
  private closed: boolean = false;
  
  // 缓存
  private cachedPathData: string | null = null;
  
  constructor(id?: string) {
    super('path', id);
  }
  
  // ==================== 节点操作 ====================
  
  addNode(point: PathPoint): void {
    this.nodes.push(point);
    this.invalidateCache();
  }
  
  insertNode(index: number, point: PathPoint): void {
    this.nodes.splice(index, 0, point);
    this.invalidateCache();
  }
  
  removeNode(index: number): void {
    this.nodes.splice(index, 1);
    this.invalidateCache();
  }
  
  updateNode(index: number, point: Partial<PathPoint>): void {
    this.nodes[index] = { ...this.nodes[index], ...point };
    this.invalidateCache();
  }
  
  getNodes(): ReadonlyArray<PathPoint> {
    return this.nodes;
  }
  
  setClosed(closed: boolean): void {
    this.closed = closed;
    this.invalidateCache();
  }
  
  // ==================== 路径数据 ====================
  
  getPathData(): string {
    if (this.cachedPathData) return this.cachedPathData;
    
    if (this.nodes.length === 0) return '';
    
    let d = '';
    
    for (let i = 0; i < this.nodes.length; i++) {
      const node = this.nodes[i];
      const prevNode = i > 0 ? this.nodes[i - 1] : null;
      
      if (i === 0) {
        d += `M ${node.x},${node.y}`;
      } else {
        // 使用贝塞尔曲线连接
        const cp1 = prevNode!.handleOut || prevNode!;
        const cp2 = node.handleIn || node;
        
        if (node.handleIn || prevNode!.handleOut) {
          d += ` C ${cp1.x},${cp1.y} ${cp2.x},${cp2.y} ${node.x},${node.y}`;
        } else {
          d += ` L ${node.x},${node.y}`;
        }
      }
    }
    
    if (this.closed && this.nodes.length > 2) {
      // 闭合路径
      const firstNode = this.nodes[0];
      const lastNode = this.nodes[this.nodes.length - 1];
      
      if (lastNode.handleOut || firstNode.handleIn) {
        const cp1 = lastNode.handleOut || lastNode;
        const cp2 = firstNode.handleIn || firstNode;
        d += ` C ${cp1.x},${cp1.y} ${cp2.x},${cp2.y} ${firstNode.x},${firstNode.y}`;
      }
      
      d += ' Z';
    }
    
    this.cachedPathData = d;
    return d;
  }
  
  setPathData(d: string): void {
    // 解析 SVG 路径数据为节点
    this.nodes = this.parsePathData(d);
    this.invalidateCache();
  }
  
  private parsePathData(d: string): PathPoint[] {
    // 解析 SVG 路径字符串
    // 这是一个简化实现，完整实现需要处理所有 SVG 路径命令
    const nodes: PathPoint[] = [];
    
    // 使用正则表达式解析...
    
    return nodes;
  }
  
  private invalidateCache(): void {
    this.cachedPathData = null;
  }
  
  // ==================== 布尔运算 ====================
  
  /**
   * 与另一个路径合并
   */
  union(other: PathElement): PathElement {
    // 使用 Paper.js 进行布尔运算
    // 需要 Paper.js 适配器
    return this;
  }
  
  /**
   * 与另一个路径相交
   */
  intersect(other: PathElement): PathElement {
    return this;
  }
  
  /**
   * 减去另一个路径
   */
  subtract(other: PathElement): PathElement {
    return this;
  }
  
  /**
   * 异或运算
   */
  exclude(other: PathElement): PathElement {
    return this;
  }
  
  // ==================== Element 实现 ====================
  
  getBounds(): Bounds {
    if (this.nodes.length === 0) {
      return { x: 0, y: 0, width: 0, height: 0 };
    }
    
    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;
    
    for (const node of this.nodes) {
      minX = Math.min(minX, node.x);
      minY = Math.min(minY, node.y);
      maxX = Math.max(maxX, node.x);
      maxY = Math.max(maxY, node.y);
      
      // 也考虑控制点
      if (node.handleIn) {
        minX = Math.min(minX, node.handleIn.x);
        minY = Math.min(minY, node.handleIn.y);
        maxX = Math.max(maxX, node.handleIn.x);
        maxY = Math.max(maxY, node.handleIn.y);
      }
      if (node.handleOut) {
        minX = Math.min(minX, node.handleOut.x);
        minY = Math.min(minY, node.handleOut.y);
        maxX = Math.max(maxX, node.handleOut.x);
        maxY = Math.max(maxY, node.handleOut.y);
      }
    }
    
    return {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
    };
  }
  
  containsPoint(point: Point): boolean {
    // 使用射线法检测点是否在闭合路径内
    if (!this.closed) return false;
    
    // 简化实现...
    return false;
  }
  
  serialize(): object {
    return {
      id: this.id,
      type: this.type,
      nodes: this.nodes,
      closed: this.closed,
      transform: this._transform,
      style: this._style,
    };
  }
  
  deserialize(data: any): void {
    this.nodes = data.nodes || [];
    this.closed = data.closed || false;
    this._transform = data.transform || this._transform;
    this._style = data.style || this._style;
    this.invalidateCache();
  }
  
  clone(): PathElement {
    const cloned = new PathElement();
    cloned.nodes = this.nodes.map(n => ({ ...n }));
    cloned.closed = this.closed;
    cloned._transform = { ...this._transform };
    cloned._style = { ...this._style };
    return cloned;
  }
  
  toFabricObject(): fabric.Object {
    const pathData = this.getPathData();
    
    return new fabric.Path(pathData, {
      fill: this._style.fill,
      stroke: this._style.stroke,
      strokeWidth: this._style.strokeWidth,
      opacity: this._style.opacity,
      left: this._transform.x,
      top: this._transform.y,
      scaleX: this._transform.scaleX,
      scaleY: this._transform.scaleY,
      angle: this._transform.rotation,
    });
  }
  
  syncFromFabricObject(obj: fabric.Object): void {
    this._transform.x = obj.left || 0;
    this._transform.y = obj.top || 0;
    this._transform.scaleX = obj.scaleX || 1;
    this._transform.scaleY = obj.scaleY || 1;
    this._transform.rotation = obj.angle || 0;
  }
  
  toSVG(): string {
    const pathData = this.getPathData();
    
    return `
      <path
        d="${pathData}"
        fill="${this._style.fill || 'none'}"
        stroke="${this._style.stroke || 'none'}"
        stroke-width="${this._style.strokeWidth}"
        opacity="${this._style.opacity}"
      />
    `;
  }
}
```

### 8.2 路径编辑工具

```typescript
// @core/canvas/tools/path/PathEditTool.ts

import { Tool, ToolType, ToolOptions, PointerEvent } from '../base/Tool';
import { PathElement, PathPoint } from '../../elements/path/PathElement';
import { Point } from '../../elements/base/Element';
import { CanvasEngine } from '../../core/CanvasEngine';

interface EditState {
  selectedNodeIndex: number | null;
  selectedHandle: 'in' | 'out' | null;
  isDragging: boolean;
  dragStart: Point;
}

export class PathEditTool extends Tool {
  private targetPath: PathElement | null = null;
  private state: EditState = {
    selectedNodeIndex: null,
    selectedHandle: null,
    isDragging: false,
    dragStart: { x: 0, y: 0 },
  };
  
  constructor(engine: CanvasEngine, options: ToolOptions = {}) {
    super('path-edit', engine, options);
  }
  
  protected getDefaultOptions(): ToolOptions {
    return {
      cursor: 'default',
      nodeRadius: 6,
      handleRadius: 4,
      handleLineWidth: 1,
    };
  }
  
  // ==================== 生命周期 ====================
  
  protected onActivate(): void {
    // 获取当前选中的路径
    const selected = this.engine.getSelectedElements();
    if (selected.length === 1 && selected[0].type === 'path') {
      this.targetPath = selected[0] as PathElement;
      this.renderEditUI();
    }
  }
  
  protected onDeactivate(): void {
    this.clearEditUI();
    this.targetPath = null;
  }
  
  // ==================== 事件处理 ====================
  
  onPointerDown(event: PointerEvent): void {
    if (!this.targetPath) return;
    
    const { point } = event;
    
    // 检查是否点击了节点
    const nodeIndex = this.getNodeAtPoint(point);
    if (nodeIndex !== null) {
      this.state.selectedNodeIndex = nodeIndex;
      this.state.selectedHandle = null;
      this.state.isDragging = true;
      this.state.dragStart = point;
      return;
    }
    
    // 检查是否点击了控制柄
    const handleResult = this.getHandleAtPoint(point);
    if (handleResult) {
      this.state.selectedNodeIndex = handleResult.nodeIndex;
      this.state.selectedHandle = handleResult.handle;
      this.state.isDragging = true;
      this.state.dragStart = point;
      return;
    }
    
    // 检查是否点击了路径线段 (添加新节点)
    if (event.altKey) {
      const insertResult = this.getInsertPoint(point);
      if (insertResult) {
        this.insertNode(insertResult.index, insertResult.point);
        this.state.selectedNodeIndex = insertResult.index;
        this.state.isDragging = true;
        this.state.dragStart = point;
        return;
      }
    }
    
    // 点击空白处，退出路径编辑
    this.engine.setActiveTool('select');
  }
  
  onPointerMove(event: PointerEvent): void {
    if (!this.state.isDragging || !this.targetPath) return;
    
    const { point } = event;
    const dx = point.x - this.state.dragStart.x;
    const dy = point.y - this.state.dragStart.y;
    
    if (this.state.selectedHandle) {
      // 移动控制柄
      this.moveHandle(
        this.state.selectedNodeIndex!,
        this.state.selectedHandle,
        point
      );
    } else if (this.state.selectedNodeIndex !== null) {
      // 移动节点
      this.moveNode(this.state.selectedNodeIndex, point);
    }
    
    this.state.dragStart = point;
    this.renderEditUI();
  }
  
  onPointerUp(event: PointerEvent): void {
    if (this.state.isDragging) {
      this.engine.history.commit();
    }
    
    this.state.isDragging = false;
  }
  
  onKeyDown(event: KeyboardEvent): void {
    if (!this.targetPath) return;
    
    switch (event.key) {
      case 'Delete':
      case 'Backspace':
        if (this.state.selectedNodeIndex !== null) {
          this.deleteNode(this.state.selectedNodeIndex);
        }
        break;
        
      case 'Escape':
        this.engine.setActiveTool('select');
        break;
    }
  }
  
  // ==================== 节点操作 ====================
  
  private moveNode(index: number, point: Point): void {
    if (!this.targetPath) return;
    
    const nodes = this.targetPath.getNodes();
    const node = nodes[index];
    
    // 计算偏移
    const dx = point.x - node.x;
    const dy = point.y - node.y;
    
    // 更新节点和控制柄
    const update: Partial<PathPoint> = {
      x: point.x,
      y: point.y,
    };
    
    if (node.handleIn) {
      update.handleIn = {
        x: node.handleIn.x + dx,
        y: node.handleIn.y + dy,
      };
    }
    
    if (node.handleOut) {
      update.handleOut = {
        x: node.handleOut.x + dx,
        y: node.handleOut.y + dy,
      };
    }
    
    this.targetPath.updateNode(index, update);
    this.engine.updateElement(this.targetPath);
  }
  
  private moveHandle(index: number, handle: 'in' | 'out', point: Point): void {
    if (!this.targetPath) return;
    
    const nodes = this.targetPath.getNodes();
    const node = nodes[index];
    
    const update: Partial<PathPoint> = {};
    
    if (handle === 'in') {
      update.handleIn = { x: point.x, y: point.y };
      
      // 如果是对称类型，同时移动对面的控制柄
      if (node.type === 'symmetric' && node.handleOut) {
        const dx = point.x - node.x;
        const dy = point.y - node.y;
        update.handleOut = { x: node.x - dx, y: node.y - dy };
      }
    } else {
      update.handleOut = { x: point.x, y: point.y };
      
      if (node.type === 'symmetric' && node.handleIn) {
        const dx = point.x - node.x;
        const dy = point.y - node.y;
        update.handleIn = { x: node.x - dx, y: node.y - dy };
      }
    }
    
    this.targetPath.updateNode(index, update);
    this.engine.updateElement(this.targetPath);
  }
  
  private insertNode(index: number, point: Point): void {
    if (!this.targetPath) return;
    
    const newNode: PathPoint = {
      x: point.x,
      y: point.y,
      type: 'smooth',
    };
    
    this.targetPath.insertNode(index, newNode);
    this.engine.updateElement(this.targetPath);
  }
  
  private deleteNode(index: number): void {
    if (!this.targetPath) return;
    
    const nodes = this.targetPath.getNodes();
    if (nodes.length <= 2) {
      // 删除整个路径
      this.engine.deleteElements([this.targetPath]);
      this.engine.setActiveTool('select');
    } else {
      this.targetPath.removeNode(index);
      this.state.selectedNodeIndex = null;
      this.engine.updateElement(this.targetPath);
      this.renderEditUI();
    }
  }
  
  // ==================== 检测方法 ====================
  
  private getNodeAtPoint(point: Point): number | null {
    if (!this.targetPath) return null;
    
    const nodes = this.targetPath.getNodes();
    const radius = this.options.nodeRadius!;
    
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const dx = point.x - node.x;
      const dy = point.y - node.y;
      
      if (dx * dx + dy * dy <= radius * radius) {
        return i;
      }
    }
    
    return null;
  }
  
  private getHandleAtPoint(point: Point): { nodeIndex: number; handle: 'in' | 'out' } | null {
    if (!this.targetPath) return null;
    
    const nodes = this.targetPath.getNodes();
    const radius = this.options.handleRadius!;
    
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      
      if (node.handleIn) {
        const dx = point.x - node.handleIn.x;
        const dy = point.y - node.handleIn.y;
        if (dx * dx + dy * dy <= radius * radius) {
          return { nodeIndex: i, handle: 'in' };
        }
      }
      
      if (node.handleOut) {
        const dx = point.x - node.handleOut.x;
        const dy = point.y - node.handleOut.y;
        if (dx * dx + dy * dy <= radius * radius) {
          return { nodeIndex: i, handle: 'out' };
        }
      }
    }
    
    return null;
  }
  
  private getInsertPoint(point: Point): { index: number; point: Point } | null {
    // 检测点击是否在路径线段附近
    // 返回插入位置和精确的插入点
    return null;
  }
  
  // ==================== UI 渲染 ====================
  
  private renderEditUI(): void {
    // 渲染节点和控制柄
    // 使用 UI Layer
  }
  
  private clearEditUI(): void {
    // 清除编辑 UI
  }
  
  // ==================== 元数据 ====================
  
  getIcon(): string {
    return 'pen-tool';
  }
  
  getName(): string {
    return 'Edit Path';
  }
  
  getShortcut(): string {
    return 'a';
  }
}
```

---

## 9. 历史记录系统

### 9.0 开源库选型

| 库名 | GitHub | 特点 | Fabric.js 兼容性 | 推荐度 |
|------|--------|------|------------------|--------|
| [fabric-history](https://github.com/alimozdemir/fabric-history) | ⭐ 200+ | 简单易用，canvas.undo()/redo() | ⚠️ v6.0 不兼容，v5.x 可用 | ⭐⭐⭐ |
| [fabricjs-history](https://github.com/KID-1912/fabricjs-history) | ⭐ 50+ | 支持 history:change 事件 | ✅ 较新 | ⭐⭐⭐ |
| 自定义 Command Pattern | - | 完全控制，可扩展性强 | ✅ | ⭐⭐⭐⭐⭐ |

**fabric-history 使用示例** (Fabric.js 5.x):
```javascript
import 'fabric-history';
import { fabric } from 'fabric';

const canvas = new fabric.Canvas('canvas');
// 自动扩展 canvas 实例
canvas.undo();  // 撤销
canvas.redo();  // 重做
canvas.clearHistory();  // 清空历史

// 排除特定对象
obj.excludeFromExport = true;  // 该对象的操作不记录历史
```

**推荐方案**: 对于生产环境，建议使用自定义 Command Pattern 实现，提供更好的控制和可扩展性。

> 参考资料:
> - [Fabric.js History Operations](https://alimozdemir.com/posts/fabric-js-history-operations-undo-redo-and-useful-tips)
> - [Fabric.js 6.0 Undo/Redo Issue #10011](https://github.com/fabricjs/fabric.js/issues/10011)

### 9.1 命令模式实现

```typescript
// @core/canvas/history/HistoryManager.ts

import { Element } from '../elements/base/Element';
import { Command } from './Command';

interface HistoryState {
  commands: Command[];
  pointer: number;  // 当前位置
  maxSize: number;  // 最大历史记录数
}

export class HistoryManager {
  private state: HistoryState = {
    commands: [],
    pointer: -1,
    maxSize: 50,
  };
  
  private pendingChanges: Command[] = [];
  private batchMode: boolean = false;
  
  // ==================== 记录操作 ====================
  
  /**
   * 执行命令并记录
   */
  execute(command: Command): void {
    command.execute();
    
    if (this.batchMode) {
      this.pendingChanges.push(command);
    } else {
      this.pushCommand(command);
    }
  }
  
  /**
   * 开始批量操作
   */
  startBatch(): void {
    this.batchMode = true;
    this.pendingChanges = [];
  }
  
  /**
   * 提交批量操作
   */
  commit(): void {
    if (!this.batchMode) return;
    
    this.batchMode = false;
    
    if (this.pendingChanges.length === 0) return;
    
    if (this.pendingChanges.length === 1) {
      this.pushCommand(this.pendingChanges[0]);
    } else {
      // 创建批量命令
      const batchCommand = new BatchCommand(this.pendingChanges);
      this.pushCommand(batchCommand);
    }
    
    this.pendingChanges = [];
  }
  
  /**
   * 取消批量操作
   */
  cancel(): void {
    if (!this.batchMode) return;
    
    // 撤销所有待处理的更改
    for (let i = this.pendingChanges.length - 1; i >= 0; i--) {
      this.pendingChanges[i].undo();
    }
    
    this.batchMode = false;
    this.pendingChanges = [];
  }
  
  // ==================== 撤销/重做 ====================
  
  undo(): boolean {
    if (!this.canUndo()) return false;
    
    const command = this.state.commands[this.state.pointer];
    command.undo();
    this.state.pointer--;
    
    return true;
  }
  
  redo(): boolean {
    if (!this.canRedo()) return false;
    
    this.state.pointer++;
    const command = this.state.commands[this.state.pointer];
    command.execute();
    
    return true;
  }
  
  canUndo(): boolean {
    return this.state.pointer >= 0;
  }
  
  canRedo(): boolean {
    return this.state.pointer < this.state.commands.length - 1;
  }
  
  // ==================== 辅助方法 ====================
  
  private pushCommand(command: Command): void {
    // 清除当前位置之后的命令 (分支历史)
    this.state.commands = this.state.commands.slice(0, this.state.pointer + 1);
    
    // 添加新命令
    this.state.commands.push(command);
    this.state.pointer++;
    
    // 限制历史记录大小
    if (this.state.commands.length > this.state.maxSize) {
      this.state.commands.shift();
      this.state.pointer--;
    }
  }
  
  clear(): void {
    this.state.commands = [];
    this.state.pointer = -1;
  }
  
  getUndoDescription(): string | null {
    if (!this.canUndo()) return null;
    return this.state.commands[this.state.pointer].description;
  }
  
  getRedoDescription(): string | null {
    if (!this.canRedo()) return null;
    return this.state.commands[this.state.pointer + 1].description;
  }
}

// ==================== 命令基类 ====================

export abstract class Command {
  abstract readonly description: string;
  abstract execute(): void;
  abstract undo(): void;
}

// ==================== 批量命令 ====================

class BatchCommand extends Command {
  private commands: Command[];
  readonly description: string;
  
  constructor(commands: Command[]) {
    super();
    this.commands = commands;
    this.description = commands[0]?.description || 'Multiple changes';
  }
  
  execute(): void {
    for (const command of this.commands) {
      command.execute();
    }
  }
  
  undo(): void {
    for (let i = this.commands.length - 1; i >= 0; i--) {
      this.commands[i].undo();
    }
  }
}
```

### 9.2 具体命令

```typescript
// @core/canvas/history/commands/TransformCommand.ts

import { Command } from '../Command';
import { Element, Transform } from '../../elements/base/Element';

export class TransformCommand extends Command {
  readonly description = 'Transform';
  
  private element: Element;
  private oldTransform: Transform;
  private newTransform: Transform;
  
  constructor(element: Element, oldTransform: Transform, newTransform: Transform) {
    super();
    this.element = element;
    this.oldTransform = { ...oldTransform };
    this.newTransform = { ...newTransform };
  }
  
  execute(): void {
    this.element.setTransform(this.newTransform);
  }
  
  undo(): void {
    this.element.setTransform(this.oldTransform);
  }
}

// @core/canvas/history/commands/DrawCommand.ts

import { Command } from '../Command';
import { FreehandElement } from '../../elements/freehand/FreehandElement';
import { CanvasEngine } from '../../core/CanvasEngine';

export class DrawCommand extends Command {
  readonly description = 'Draw';
  
  private engine: CanvasEngine;
  private element: FreehandElement;
  
  constructor(engine: CanvasEngine, element: FreehandElement) {
    super();
    this.engine = engine;
    this.element = element;
  }
  
  execute(): void {
    this.engine.addElementInternal(this.element);
  }
  
  undo(): void {
    this.engine.removeElementInternal(this.element);
  }
}
```

---

## 10. 性能优化

### 10.1 优化策略

```
┌─────────────────────────────────────────────────────────────────┐
│                    性能优化策略                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 分层渲染 (Layer-based Rendering)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 背景层: 静态，很少重绘                                  │
│  │  • 内容层: 元素变化时重绘                                  │
│  │  • 绘制层: 高频重绘，最小化区域                            │
│  │  • UI层: 仅覆盖层，不影响内容                              │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  2. 增量渲染 (Incremental Rendering)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 手绘时只渲染新增的笔画段                                │
│  │  • 使用 dirty rectangles 只重绘变化区域                    │
│  │  • 大批量元素使用虚拟化                                    │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  3. 路径简化 (Path Simplification)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 绘制完成后简化路径点                                    │
│  │  • Douglas-Peucker 算法                                   │
│  │  • 保留压感信息的智能简化                                  │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  4. 离屏渲染 (Offscreen Rendering)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 复杂元素预渲染到离屏 canvas                             │
│  │  • 缓存渲染结果                                           │
│  │  • 缩放时使用缓存快速预览                                  │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  5. 请求动画帧 (RAF Batching)                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 批量处理多个更新请求                                    │
│  │  • 避免强制同步布局                                        │
│  │  • 使用 requestAnimationFrame 调度渲染                    │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  6. 内存优化 (Memory Optimization)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 大图片使用 ImageBitmap                                 │
│  │  • 历史记录使用差异存储                                    │
│  │  • 超出视口的元素延迟渲染                                  │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 性能指标

| 场景 | 目标 FPS | 最大延迟 |
|------|----------|----------|
| 手绘 | 60 FPS | 16ms |
| 拖拽 | 60 FPS | 16ms |
| 缩放 | 30 FPS | 33ms |
| 选择 | 60 FPS | 16ms |
| 导出 | - | 3s (8页) |

---

## 11. 实施路线图

### 11.1 阶段规划

```
┌─────────────────────────────────────────────────────────────────┐
│                    实施路线图                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: 架构重构 (2 周)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Week 1:                                                  │
│  │  • 设计核心抽象层 (Element, Tool, Renderer)              │
│  │  • 重构现有代码到新架构                                   │
│  │  • 保持现有功能正常                                       │
│  │                                                          │
│  │  Week 2:                                                  │
│  │  • 实现 ToolManager                                       │
│  │  • 实现 HistoryManager                                    │
│  │  • 实现 FabricRenderer 适配器                             │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 2: 手绘功能 (2 周)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Week 3:                                                  │
│  │  • 集成 perfect-freehand                                  │
│  │  • 实现 PencilTool                                        │
│  │  • 实现 FreehandElement                                   │
│  │  • 分层渲染架构                                           │
│  │                                                          │
│  │  Week 4:                                                  │
│  │  • 实现 MarkerTool, HighlighterTool                      │
│  │  • 实现 EraserTool                                        │
│  │  • 压感支持                                               │
│  │  • 性能优化                                               │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 3: 矢量功能 (2 周)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Week 5:                                                  │
│  │  • 实现 PathElement                                       │
│  │  • 实现 PenTool (钢笔)                                    │
│  │  • 贝塞尔曲线渲染                                         │
│  │                                                          │
│  │  Week 6:                                                  │
│  │  • 实现 PathEditTool                                      │
│  │  • 节点编辑 UI                                            │
│  │  • SVG 导入导出                                           │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 4: 高级功能 (2 周)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Week 7:                                                  │
│  │  • 布尔运算 (Paper.js 集成)                               │
│  │  • 渐变填充                                               │
│  │  • 图案填充                                               │
│  │                                                          │
│  │  Week 8:                                                  │
│  │  • 智能参考线                                             │
│  │  • 对齐功能                                               │
│  │  • 完善和测试                                             │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  总计: 8 周                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 依赖项

```json
{
  "dependencies": {
    "fabric": "^5.3.0",
    "perfect-freehand": "^1.2.0",
    "simplify-js": "^1.2.4",
    "paper": "^0.12.17"
  },
  "devDependencies": {
    "@types/fabric": "^5.3.0"
  }
}
```

### 11.3 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 性能问题 | 手绘卡顿 | 分层渲染 + 增量更新 |
| 库冲突 | 多引擎协调 | 抽象层隔离 |
| 移动端兼容 | 触摸手势 | 智能模式切换 |
| 历史记录膨胀 | 内存占用 | 差异存储 + 限制条数 |
| 导出一致性 | SVG/PDF 差异 | 统一路径序列化 |

---

**画布架构设计完成！**

这个架构支持：
- ✅ 当前所有功能
- ✅ 手绘与画笔 (Phase 2)
- ✅ 矢量图编辑 (Phase 3)
- ✅ 高级功能预留 (Phase 4)
- ✅ 未来扩展 (插件系统)
