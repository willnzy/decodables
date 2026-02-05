# Editor 重设计：Media Library & Properties Panel

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

- 问题或机会: 编辑器媒体属性面板缺少统一规范
- 目标与非目标: 目标是统一媒体属性配置与交互；非目标是替代渲染实现

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- Media Library 与 Properties Panel 的 UI/UX 方案
- 交互规范与实施建议

## 影响范围

- 相关模块: 编辑器面板与交互
- 相关文档: `docs/v2/04-features/canvas-architecture.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/`、`decodables-fe/@core/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |

## 文档分工

**本文档重点**:
- ✅ Media Library 面板 (10 类分类、搜索、拖拽)
- ✅ Properties Panel (属性编辑、上下文感知)
- ✅ 面板 UI/UX 设计和交互规范
- ✅ 竞品分析和设计决策

**不涵盖内容** (请参考其他文档):
- ❌ Canvas 核心架构 → `docs/v2/04-features/canvas-architecture.md`
- ❌ 设计系统规范 → `docs/v2/02-standards/design-system.md`
- ❌ 素材分类后端 API → `docs/shared/asset-category-design.md`

---

## 目录

1. [竞品分析](#1-竞品分析)
2. [Media Library 重设计](#2-media-library-重设计)
3. [Properties Panel 重设计](#3-properties-panel-重设计)
4. [为未来功能预留](#4-为未来功能预留)
5. [三方库推荐](#5-三方库推荐)
6. [实施计划](#6-实施计划)

---

## 1. 竞品分析

### 1.1 主流设计软件对比

| 软件 | Media Library 特点 | Properties Panel 特点 | 优点 | 缺点 |
|------|-------------------|---------------------|------|------|
| **Canva** | 左侧面板，Tab 切换，搜索强大 | 右侧浮动，上下文感知 | 直观易用，分类清晰 | 功能较基础 |
| **Figma** | 左侧 Assets，拖拽添加 | 右侧固定，分组折叠 | 专业，键盘友好 | 学习曲线高 |
| **Adobe Express** | 左侧面板，推荐驱动 | 右侧面板，工具栏结合 | AI 推荐强 | 层级过深 |
| **Photopea** | 传统菜单 + 面板 | 多面板浮动 | 功能全面 | 界面复杂 |
| **Picsart** | 底部 Tab，全屏选择 | 底部工具栏 | 移动端友好 | 桌面端浪费空间 |

### 1.2 交互模式总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    主流交互模式                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  布局模式 (推荐: Canva 模式)                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  ┌────────┐  ┌──────────────────────┐  ┌────────┐     │    │
│  │  │        │  │                      │  │        │     │    │
│  │  │ Media  │  │       Canvas         │  │ Props  │     │    │
│  │  │ Library│  │                      │  │ Panel  │     │    │
│  │  │        │  │                      │  │        │     │    │
│  │  │ (左侧) │  │       (中间)          │  │ (右侧) │     │    │
│  │  │        │  │                      │  │        │     │    │
│  │  └────────┘  └──────────────────────┘  └────────┘     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Media Library 交互:                                             │
│  • Tab 切换分类 (不是折叠)                                       │
│  • 搜索置顶，全局可用                                            │
│  • 网格布局，hover 预览                                          │
│  • 拖拽或点击添加                                                │
│  • 懒加载 + 虚拟滚动                                             │
│                                                                 │
│  Properties Panel 交互:                                          │
│  • 上下文感知 (选中不同元素显示不同属性)                          │
│  • 分组折叠 (Position, Style, Effects)                          │
│  • 数值输入支持拖拽调整                                          │
│  • 快捷键提示                                                    │
│  • 实时预览                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Media Library 重设计

### 2.1 当前问题分析

| 问题 | 影响 | 优先级 |
|------|------|--------|
| 分类层级不清晰 | 用户找不到素材 | P0 |
| 没有搜索功能 | 效率低 | P0 |
| 无懒加载 | 性能差 | P1 |
| 无收藏/最近使用 | 重复劳动 | P1 |
| 扩展性差 | 无法新增分类 | P2 |

### 2.2 新分类体系 (10 类)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Media Library 新分类                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  一级分类 (Tab)           二级分类 (标签/筛选)                    │
│  ───────────────────────────────────────────────                │
│                                                                 │
│  1️⃣ AI Generate          • Image Generation                     │
│     (AI 生成)            • Story Generation                     │
│                          • Smart Scan (OCR)                     │
│                                                                 │
│  2️⃣ Templates            • Blank                                │
│     (模板)               • Phonics                              │
│                          • Sight Words                          │
│                          • Decodable Stories                    │
│                          • Seasonal                             │
│                                                                 │
│  3️⃣ Stickers             • Characters (人物)                    │
│     (贴纸)               • Animals (动物)                       │
│                          • Objects (物品)                       │
│                          • Nature (自然)                        │
│                          • Shapes (形状)                        │
│                          • Emojis (表情)                        │
│                          • Education (教育)                     │
│                                                                 │
│  4️⃣ Backgrounds          • Solid Colors                        │
│     (背景)               • Gradients                            │
│                          • Patterns                             │
│                          • Scenes                               │
│                          • Textures                             │
│                                                                 │
│  5️⃣ Text Styles          • Titles                               │
│     (文字样式)           • Body Text                            │
│                          • Labels                               │
│                          • Word Boxes                           │
│                                                                 │
│  6️⃣ Frames & Borders     • Photo Frames                        │
│     (边框)               • Text Borders                         │
│                          • Decorative                           │
│                                                                 │
│  7️⃣ Lines & Arrows       • Straight Lines                      │
│     (线条)               • Arrows                               │
│                          • Connectors                           │
│                          • Dividers                             │
│                                                                 │
│  8️⃣ Shapes               • Basic Shapes                        │
│     (形状)               • Callouts                             │
│                          • Badges                               │
│                          • Icons                                │
│                                                                 │
│  9️⃣ Uploads              • My Images                           │
│     (上传)               • My Projects                          │
│                          • Cloud Storage                        │
│                                                                 │
│  🔟 Recent & Favorites    • Recently Used                       │
│     (最近/收藏)          • Favorites                            │
│                          • Frequently Used                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 三层分类系统

```typescript
// 分类数据结构
interface MediaCategory {
  id: string;
  name: string;
  icon: string;
  order: number;
  
  // 子分类
  subcategories: {
    id: string;
    name: string;
    tags?: string[];
  }[];
  
  // 配置
  config: {
    searchable: boolean;
    allowUpload: boolean;
    showCount: boolean;
    lazyLoad: boolean;
    virtualScroll: boolean;
  };
  
  // 权限
  tier?: 'free' | 'starter' | 'pro';
}

// 分类配置
const MEDIA_CATEGORIES: MediaCategory[] = [
  {
    id: 'ai_generate',
    name: 'AI Generate',
    icon: 'sparkles',
    order: 1,
    subcategories: [
      { id: 'image_gen', name: 'Image Generation' },
      { id: 'story_gen', name: 'Story Generation' },
      { id: 'smart_scan', name: 'Smart Scan' },
    ],
    config: {
      searchable: false,
      allowUpload: false,
      showCount: false,
      lazyLoad: false,
      virtualScroll: false,
    },
  },
  {
    id: 'stickers',
    name: 'Stickers',
    icon: 'sticker',
    order: 3,
    subcategories: [
      { id: 'characters', name: 'Characters', tags: ['people', 'kids', 'adults'] },
      { id: 'animals', name: 'Animals', tags: ['pets', 'wild', 'farm', 'sea'] },
      { id: 'objects', name: 'Objects', tags: ['food', 'toys', 'tools'] },
      { id: 'nature', name: 'Nature', tags: ['plants', 'weather', 'seasons'] },
      { id: 'shapes', name: 'Shapes' },
      { id: 'emojis', name: 'Emojis' },
      { id: 'education', name: 'Education', tags: ['letters', 'numbers', 'school'] },
    ],
    config: {
      searchable: true,
      allowUpload: false,
      showCount: true,
      lazyLoad: true,
      virtualScroll: true,
    },
  },
  // ... 其他分类
];
```

### 2.4 UI 设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Media Library UI                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🔍 Search stickers, backgrounds...              [×]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ [✨AI] [📋Tmpl] [🎨Stick] [🖼️BG] [T] [🔲] [📁] [⭐]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Stickers                                    1,234 items│   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  [All] [Characters] [Animals] [Objects] [Nature] [▼]   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │   │
│  │  │     │ │     │ │     │ │     │ │     │ │     │      │   │
│  │  │ 🐕  │ │ 🐈  │ │ 🐘  │ │ 🦁  │ │ 🐰  │ │ 🐻  │      │   │
│  │  │     │ │     │ │     │ │     │ │     │ │     │      │   │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘      │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │   │
│  │  │     │ │     │ │     │ │     │ │     │ │     │      │   │
│  │  │ 🦊  │ │ 🐼  │ │ 🐨  │ │ 🐸  │ │ 🦋  │ │ 🐢  │      │   │
│  │  │     │ │     │ │     │ │     │ │     │ │     │      │   │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘      │   │
│  │                                                         │   │
│  │  [Load More...] or Virtual Scroll                       │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 交互规范

| 交互 | 行为 | 快捷键 |
|------|------|--------|
| 单击素材 | 添加到画布中心 | - |
| 拖拽素材 | 添加到指定位置 | - |
| 双击素材 | 添加并进入编辑模式 | - |
| 右键素材 | 上下文菜单 (添加/收藏/详情) | - |
| 搜索 | 全局搜索所有分类 | Ctrl+F |
| 切换分类 | Tab 切换 | 1-9 |
| 滚动 | 虚拟滚动，懒加载 | - |

---

## 3. Properties Panel 重设计

### 3.1 当前问题

| 问题 | 影响 | 优先级 |
|------|------|--------|
| 属性分组不清晰 | 找不到设置 | P0 |
| 缺少上下文感知 | 显示无关属性 | P0 |
| 数值调整不方便 | 效率低 | P1 |
| 缺少预设 | 重复操作 | P2 |

### 3.2 上下文感知属性面板

```typescript
// 不同元素类型显示不同属性
interface PropertyGroups {
  // 通用属性 (所有元素)
  common: ['position', 'size', 'rotation', 'opacity', 'lock'];
  
  // 文本属性
  text: ['font', 'fontSize', 'fontWeight', 'color', 'alignment', 'lineHeight', 'letterSpacing', 'textEffects'];
  
  // 图片属性
  image: ['filters', 'crop', 'flip', 'borderRadius', 'shadow', 'border'];
  
  // 形状属性
  shape: ['fill', 'stroke', 'strokeWidth', 'cornerRadius', 'shadow'];
  
  // 贴纸属性
  sticker: ['colorOverlay', 'flip', 'shadow'];
  
  // 背景属性
  background: ['fill', 'image', 'pattern', 'gradient'];
}

// 根据选中元素动态显示
function getPropertiesForElement(element: CanvasElement): PropertyGroup[] {
  const groups: PropertyGroup[] = [
    { id: 'transform', name: 'Transform', properties: PropertyGroups.common },
  ];
  
  switch (element.type) {
    case 'text':
      groups.push(
        { id: 'typography', name: 'Typography', properties: PropertyGroups.text },
        { id: 'effects', name: 'Effects', properties: ['shadow', 'outline'] }
      );
      break;
    case 'image':
      groups.push(
        { id: 'image', name: 'Image', properties: PropertyGroups.image },
        { id: 'effects', name: 'Effects', properties: ['shadow', 'border'] }
      );
      break;
    // ... 其他类型
  }
  
  return groups;
}
```

### 3.3 UI 设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Properties Panel UI                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  没有选中元素时:                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Properties                                              │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │           📝 Select an element                          │   │
│  │              to edit its properties                     │   │
│  │                                                          │   │
│  │  ─────────────────────────────────────                  │   │
│  │                                                          │   │
│  │  Page Settings                                    [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  Background:  [🎨 Color Picker]                 │   │   │
│  │  │  Size:        [Letter ▼]                        │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  选中文本元素时:                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Properties                               Text Element   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  Transform                                        [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  X: [120] px    Y: [80] px                      │   │   │
│  │  │  W: [200] px    H: [50] px    🔗                │   │   │
│  │  │  Rotation: [0°]  ─────○─────                    │   │   │
│  │  │  Opacity: [100%] ───────────○                   │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Typography                                       [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  Font:    [Comic Sans ▼]                        │   │   │
│  │  │  Size:    [24] px    Weight: [Bold ▼]          │   │   │
│  │  │  Color:   [██████] #333333                     │   │   │
│  │  │  Align:   [≡] [≡] [≡] [≡]                      │   │   │
│  │  │  Line H:  [1.5]      Letter: [0] px            │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Effects                                          [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  Shadow:   [✓]  Color: [██] Blur: [4]          │   │   │
│  │  │  Outline:  [ ]                                  │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Actions                                                │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  [🗑️ Delete] [📋 Duplicate] [🔒 Lock] [📦 Group]│   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  选中图片元素时:                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Properties                              Image Element   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  Transform                                        [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  (同上)                                          │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Image                                            [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  [✂️ Crop] [↔️ Flip H] [↕️ Flip V] [🔄 Reset]   │   │   │
│  │  │  Corner:  [0] px   ─────○─────                  │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Filters                                          [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  Brightness: [100%] ─────○─────                 │   │   │
│  │  │  Contrast:   [100%] ─────○─────                 │   │   │
│  │  │  Saturation: [100%] ─────○─────                 │   │   │
│  │  │  Blur:       [0] px ○─────────                  │   │   │
│  │  │                                                 │   │   │
│  │  │  Presets: [Original] [Vivid] [B&W] [Sepia]     │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Effects                                          [▼]   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  Shadow: [✓]  X:[2] Y:[2] Blur:[8] Color:[██]  │   │   │
│  │  │  Border: [ ]                                    │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 数值输入增强

```typescript
// 拖拽调整数值
interface NumberInputProps {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  onChange: (value: number) => void;
}

// 交互方式:
// 1. 直接输入数字
// 2. 上下箭头微调 (+/- step)
// 3. 拖拽 label 调整 (Figma 风格)
// 4. Shift + 拖拽 = 10x 步进
// 5. Alt + 拖拽 = 0.1x 步进
```

---

## 4. 为未来功能预留

### 4.1 扩展性设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    未来功能扩展预留                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Media Library 扩展:                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  当前:                                                    │
│  │  [✨AI] [📋Tmpl] [🎨Stick] [🖼️BG] [T] [🔲] [📁] [⭐]    │   │
│  │                                                          │
│  │  未来可新增 Tab:                                          │
│  │  [🖌️ Draw]    - 画笔/手绘工具                            │
│  │  [📊 Charts]  - 图表组件                                 │
│  │  [🎬 Video]   - 视频/GIF (Pro)                           │
│  │  [🔊 Audio]   - 音频 (Pro)                               │
│  │  [📝 Tables]  - 表格组件                                 │
│  │  [🧩 Widgets] - 交互组件                                 │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Properties Panel 扩展:                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  未来可新增属性组:                                        │
│  │                                                          │
│  │  • Draw Properties (画笔属性)                            │
│  │    - Brush Type, Size, Opacity, Smoothing               │
│  │                                                          │
│  │  • Animation Properties (动画属性)                       │
│  │    - Entry, Exit, Duration, Delay                       │
│  │                                                          │
│  │  • Interaction Properties (交互属性)                     │
│  │    - Click Action, Hover Effect                         │
│  │                                                          │
│  │  • Layer Properties (图层属性)                           │
│  │    - Blend Mode, Layer Effects                          │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 画笔功能预留

```typescript
// 画笔工具配置
interface BrushTool {
  id: string;
  name: string;
  icon: string;
  
  // 画笔属性
  properties: {
    size: { min: 1, max: 100, default: 10 };
    opacity: { min: 0, max: 100, default: 100 };
    hardness: { min: 0, max: 100, default: 80 };
    smoothing: { min: 0, max: 100, default: 50 };
  };
  
  // 画笔类型
  type: 'pen' | 'pencil' | 'marker' | 'highlighter' | 'eraser';
  
  // 压感支持
  pressureSensitive: boolean;
}

// 画笔 Tab 内容
const BRUSH_TOOLS: BrushTool[] = [
  { id: 'pen', name: 'Pen', type: 'pen', ... },
  { id: 'pencil', name: 'Pencil', type: 'pencil', ... },
  { id: 'marker', name: 'Marker', type: 'marker', ... },
  { id: 'highlighter', name: 'Highlighter', type: 'highlighter', ... },
  { id: 'eraser', name: 'Eraser', type: 'eraser', ... },
];
```

### 4.3 插件系统预留

```typescript
// 未来插件系统接口
interface MediaPlugin {
  id: string;
  name: string;
  icon: string;
  
  // Tab 配置
  tab: {
    order: number;
    label: string;
  };
  
  // 内容渲染
  render: () => React.ReactNode;
  
  // 属性面板
  properties?: PropertyGroup[];
  
  // 权限
  tier?: 'free' | 'starter' | 'pro';
}

// 注册插件
function registerMediaPlugin(plugin: MediaPlugin): void;
```

---

## 5. 三方库推荐

### 5.1 Canvas 引擎对比

| 库 | 优点 | 缺点 | 适合场景 | 推荐度 |
|-----|------|------|----------|--------|
| **Fabric.js** (当前) | 功能全面、文档好、社区大 | 体积大、性能一般 | 通用编辑器 | ⭐⭐⭐⭐ |
| **Konva.js** | 性能好、React 友好 | 功能略少 | 高性能需求 | ⭐⭐⭐⭐⭐ |
| **PixiJS** | 性能最好、WebGL | 2D 文档少、学习曲线 | 游戏/动画 | ⭐⭐⭐ |
| **Paper.js** | 矢量强、路径操作 | 社区小 | 矢量绑图 | ⭐⭐⭐ |
| **Excalidraw** | 手绘风格、开源 | 功能单一 | 白板/手绘 | ⭐⭐⭐ |

**建议**: 
- 短期：继续使用 **Fabric.js 5.3**，它功能最全面
- 长期：考虑迁移到 **Konva.js** 以获得更好性能
- 如果要加画笔功能：可以集成 **perfect-freehand** 库

### 5.2 UI 组件库推荐

| 用途 | 推荐库 | 说明 |
|------|--------|------|
| **虚拟滚动** | `@tanstack/react-virtual` | 最佳性能，用于素材列表 |
| **拖拽** | `@dnd-kit/core` | 现代 API，用于素材拖入画布 |
| **颜色选择器** | `react-colorful` | 轻量 (2KB)，功能完整 |
| **滑块** | `@radix-ui/react-slider` | 无障碍，配合 shadcn |
| **数值输入** | 自定义 + `use-gesture` | Figma 风格拖拽调整 |
| **快捷键** | `react-hotkeys-hook` | 简单好用 |
| **右键菜单** | `@radix-ui/react-context-menu` | 配合 shadcn |
| **搜索** | `cmdk` 或 `fuse.js` | 模糊搜索 |
| **图片懒加载** | `react-lazy-load-image-component` | 简单好用 |
| **手势操作** | `@use-gesture/react` | 拖拽、缩放、旋转 |

### 5.3 性能优化库

| 用途 | 推荐库 | 说明 |
|------|--------|------|
| **图片压缩** | `browser-image-compression` | 客户端压缩 |
| **图片裁剪** | `react-image-crop` | 简单易用 |
| **图片滤镜** | `WebGL Filters` 或 Fabric 内置 | GPU 加速 |
| **撤销重做** | `zustand` + `immer` | 状态快照 |
| **历史记录** | 自定义 或 `use-undo` | 简单场景 |

### 5.4 画笔功能相关

| 用途 | 推荐库 | 说明 |
|------|--------|------|
| **手绘平滑** | `perfect-freehand` | 最佳手绘效果 |
| **压感支持** | `Pointer Events API` | 原生支持 |
| **矢量路径** | `Paper.js` 或 `svg-path-commander` | 路径操作 |
| **白板功能** | `tldraw` | 完整白板解决方案 |

### 5.5 具体推荐组合

```typescript
// 推荐的技术栈组合

// 1. Canvas 引擎
import { Canvas } from 'fabric';  // 或 Konva

// 2. 虚拟滚动 (Media Library)
import { useVirtualizer } from '@tanstack/react-virtual';

// 3. 拖拽
import { DndContext, useDraggable, useDroppable } from '@dnd-kit/core';

// 4. 颜色选择
import { HexColorPicker, HexColorInput } from 'react-colorful';

// 5. 手势 (数值拖拽调整)
import { useDrag } from '@use-gesture/react';

// 6. 快捷键
import { useHotkeys } from 'react-hotkeys-hook';

// 7. 搜索
import Fuse from 'fuse.js';

// 8. 手绘 (未来)
import getStroke from 'perfect-freehand';
```

---

## 6. 实施计划

### 6.1 阶段划分

```
Phase 1: Media Library 重构 (5 天)
├─ 新分类数据结构
├─ Tab 切换组件
├─ 虚拟滚动集成
├─ 搜索功能
└─ 收藏/最近使用

Phase 2: Properties Panel 重构 (4 天)
├─ 上下文感知逻辑
├─ 分组折叠组件
├─ 数值拖拽输入
├─ 滑块组件优化
└─ 颜色选择器

Phase 3: 交互优化 (3 天)
├─ 拖拽添加素材
├─ 快捷键系统
├─ 右键菜单
└─ Tooltip 优化

Phase 4: 性能优化 (2 天)
├─ 图片懒加载
├─ 缓存策略
└─ 渲染优化

总计: ~14 天 (约 3 周)
```

### 6.2 检查清单

| 功能 | 验收标准 |
|------|----------|
| 分类切换 | Tab 切换流畅 |
| 虚拟滚动 | 1000+ 素材无卡顿 |
| 搜索 | 实时响应 <100ms |
| 拖拽添加 | 流畅无延迟 |
| 属性面板 | 上下文切换 <50ms |
| 数值调整 | 拖拽实时预览 |
| 收藏功能 | 状态持久化 |

---

## 7. 迁移策略

### 7.1 渐进式迁移

```
Week 1: 
├─ 新建 MediaLibrary v2 组件
├─ 保留旧组件，新旧并存
└─ Feature Flag 控制切换

Week 2:
├─ 新建 PropertiesPanel v2 组件
├─ 迁移 Text 属性
└─ 迁移 Image 属性

Week 3:
├─ 迁移剩余属性
├─ 全量切换到 v2
└─ 下线旧组件
```

### 7.2 数据迁移

```typescript
// 素材分类数据迁移
// 旧: 6 个分类
// 新: 10 个分类

const CATEGORY_MIGRATION_MAP = {
  'backgrounds': 'backgrounds',
  'stickers': 'stickers',
  'text': 'text_styles',
  'shapes': 'shapes',
  'uploads': 'uploads',
  'templates': 'templates',
  // 新增
  'ai_generate': 'ai_generate',
  'frames': 'frames',
  'lines': 'lines',
  'favorites': 'favorites',
};
```

---

**Editor 重设计方案完成！**
