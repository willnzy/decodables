# Canvas 数据契约

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: 前端 Canvas 组件, 后端 projects 表

---

## 一、概述

### 1.1 设计目标

- 统一前后端 Canvas 数据结构
- 明确字段语义与类型约束
- 支持版本兼容与数据迁移

### 1.2 数据流

```
前端 Fabric.js Canvas
       ↓
Canvas JSON 序列化
       ↓
API 传输 (projects.canvas_data)
       ↓
PostgreSQL JSONB 存储
```

---

## 二、根结构

### 2.1 Project Canvas 根字段

```typescript
interface CanvasData {
  version: string;           // 数据版本，如 "1.0.0"
  pages: Page[];            // 页面数组 (固定 8 页)
  metadata: CanvasMetadata; // 元信息
}

interface CanvasMetadata {
  createdAt: string;        // ISO 8601 格式
  updatedAt: string;        // ISO 8601 格式
  editorVersion: string;    // 编辑器版本
  exportSettings?: ExportSettings;
}
```

### 2.2 Page 结构

```typescript
interface Page {
  id: string;               // UUID
  index: number;            // 页面序号 (0-7)
  type: PageType;           // 页面类型
  objects: CanvasObject[];  // 画布对象
  background?: Background;  // 背景设置
}

type PageType = 
  | 'front_cover'    // 封面
  | 'content'        // 内容页
  | 'back_cover';    // 封底
```

---

## 三、Canvas 对象

### 3.1 基础对象结构

```typescript
interface CanvasObject {
  // 通用字段
  id: string;              // 对象 UUID
  type: ObjectType;        // 对象类型
  left: number;            // X 坐标 (px)
  top: number;             // Y 坐标 (px)
  width: number;           // 宽度 (px)
  height: number;          // 高度 (px)
  scaleX: number;          // X 缩放 (默认 1)
  scaleY: number;          // Y 缩放 (默认 1)
  angle: number;           // 旋转角度 (度)
  opacity: number;         // 透明度 (0-1)
  visible: boolean;        // 是否可见
  selectable: boolean;     // 是否可选中
  locked: boolean;         // 是否锁定
  
  // 层级
  zIndex: number;          // 层级序号
}

type ObjectType = 
  | 'image'
  | 'text'
  | 'textbox'
  | 'shape'
  | 'group'
  | 'path'
  | 'line';
```

### 3.2 Image 对象

```typescript
interface ImageObject extends CanvasObject {
  type: 'image';
  src: string;             // 图片 URL
  assetId?: string;        // 关联素材 ID
  crossOrigin: string;     // CORS 设置
  
  // 裁切
  cropX?: number;
  cropY?: number;
  cropWidth?: number;
  cropHeight?: number;
  
  // 滤镜
  filters?: ImageFilter[];
}

interface ImageFilter {
  type: FilterType;
  value: number;
}

type FilterType = 
  | 'brightness'
  | 'contrast'
  | 'saturation'
  | 'blur';
```

### 3.3 Text 对象

```typescript
interface TextObject extends CanvasObject {
  type: 'text' | 'textbox';
  text: string;            // 文本内容
  fontFamily: string;      // 字体名称
  fontSize: number;        // 字号 (px)
  fontWeight: string;      // 字重
  fontStyle: string;       // 字形 (normal/italic)
  fill: string;            // 文字颜色
  stroke?: string;         // 描边颜色
  strokeWidth?: number;    // 描边宽度
  
  // 对齐
  textAlign: TextAlign;
  
  // 行距
  lineHeight: number;
  charSpacing: number;
  
  // 特效
  shadow?: TextShadow;
}

type TextAlign = 'left' | 'center' | 'right' | 'justify';

interface TextShadow {
  color: string;
  offsetX: number;
  offsetY: number;
  blur: number;
}
```

### 3.4 Shape 对象

```typescript
interface ShapeObject extends CanvasObject {
  type: 'shape';
  shapeType: ShapeType;
  fill: string;            // 填充色
  stroke: string;          // 边框色
  strokeWidth: number;     // 边框宽度
  
  // 圆角 (矩形)
  rx?: number;
  ry?: number;
}

type ShapeType = 
  | 'rect'
  | 'circle'
  | 'triangle'
  | 'ellipse'
  | 'polygon'
  | 'star';
```

---

## 四、背景配置

```typescript
interface Background {
  type: BackgroundType;
  color?: string;          // 纯色背景
  gradient?: Gradient;     // 渐变背景
  image?: BackgroundImage; // 图片背景
}

type BackgroundType = 'color' | 'gradient' | 'image';

interface Gradient {
  type: 'linear' | 'radial';
  colorStops: ColorStop[];
  angle?: number;          // 线性渐变角度
}

interface ColorStop {
  offset: number;          // 0-1
  color: string;
}

interface BackgroundImage {
  src: string;
  mode: 'fill' | 'fit' | 'tile';
  opacity: number;
}
```

---

## 五、数据库存储

### 5.1 projects 表

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Canvas 数据 (JSONB)
    canvas_data JSONB NOT NULL DEFAULT '{}',
    
    -- 缩略图
    thumbnail_url VARCHAR(500),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'draft',
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- JSONB 索引
CREATE INDEX idx_projects_canvas_version 
ON projects ((canvas_data->>'version'));
```

### 5.2 完整示例

```json
{
  "version": "1.0.0",
  "pages": [
    {
      "id": "page-1",
      "index": 0,
      "type": "front_cover",
      "background": {
        "type": "color",
        "color": "#ffffff"
      },
      "objects": [
        {
          "id": "obj-1",
          "type": "image",
          "left": 100,
          "top": 100,
          "width": 200,
          "height": 200,
          "scaleX": 1,
          "scaleY": 1,
          "angle": 0,
          "opacity": 1,
          "visible": true,
          "selectable": true,
          "locked": false,
          "zIndex": 0,
          "src": "https://...",
          "assetId": "asset-uuid",
          "crossOrigin": "anonymous"
        },
        {
          "id": "obj-2",
          "type": "textbox",
          "left": 150,
          "top": 350,
          "width": 300,
          "height": 50,
          "scaleX": 1,
          "scaleY": 1,
          "angle": 0,
          "opacity": 1,
          "visible": true,
          "selectable": true,
          "locked": false,
          "zIndex": 1,
          "text": "My Story Book",
          "fontFamily": "Inter",
          "fontSize": 32,
          "fontWeight": "bold",
          "fontStyle": "normal",
          "fill": "#333333",
          "textAlign": "center",
          "lineHeight": 1.2,
          "charSpacing": 0
        }
      ]
    }
  ],
  "metadata": {
    "createdAt": "2026-02-05T10:00:00Z",
    "updatedAt": "2026-02-05T12:30:00Z",
    "editorVersion": "2.0.0"
  }
}
```

---

## 六、版本兼容

### 6.1 版本策略

| 版本 | 变更类型 | 说明 |
|------|----------|------|
| 1.0.x | 补丁 | 仅修复 bug，完全兼容 |
| 1.x.0 | 次版本 | 新增字段，向后兼容 |
| x.0.0 | 主版本 | 结构变更，需迁移 |

### 6.2 迁移逻辑

```typescript
function migrateCanvasData(data: any): CanvasData {
  const version = data.version || '0.0.0';
  
  if (semver.lt(version, '1.0.0')) {
    // v0 -> v1 迁移
    data = migrateV0ToV1(data);
  }
  
  // 设置默认值
  return applyDefaults(data);
}

function applyDefaults(data: CanvasData): CanvasData {
  data.pages = data.pages.map(page => ({
    ...page,
    objects: page.objects.map(obj => ({
      scaleX: 1,
      scaleY: 1,
      angle: 0,
      opacity: 1,
      visible: true,
      selectable: true,
      locked: false,
      ...obj
    }))
  }));
  
  return data;
}
```

---

## 七、校验规则

### 7.1 必填字段

| 层级 | 必填字段 |
|------|----------|
| Root | version, pages, metadata |
| Page | id, index, type, objects |
| Object | id, type, left, top, width, height |

### 7.2 类型约束

```typescript
// Zod 校验示例
const CanvasObjectSchema = z.object({
  id: z.string().uuid(),
  type: z.enum(['image', 'text', 'textbox', 'shape', 'group', 'path', 'line']),
  left: z.number(),
  top: z.number(),
  width: z.number().positive(),
  height: z.number().positive(),
  scaleX: z.number().positive().default(1),
  scaleY: z.number().positive().default(1),
  angle: z.number().min(0).max(360).default(0),
  opacity: z.number().min(0).max(1).default(1),
  visible: z.boolean().default(true),
  selectable: z.boolean().default(true),
  locked: z.boolean().default(false),
  zIndex: z.number().int().min(0).default(0),
});
```

---

## 八、性能优化

### 8.1 数据压缩

- 存储时压缩 JSONB (PostgreSQL 自动)
- 传输时可选 gzip 压缩
- 大图片使用 CDN URL 而非 base64

### 8.2 增量更新

```typescript
// 仅更新变更的对象
PATCH /api/v2/user/projects/{id}/objects
Body: {
  "operations": [
    { "op": "update", "id": "obj-1", "data": { "left": 120 } },
    { "op": "delete", "id": "obj-2" },
    { "op": "add", "data": { ... } }
  ]
}
```

---

## 九、相关文档

- [编辑器架构](../04-engineering/modules/editor/architecture.md)
- [项目管理](../04-engineering/modules/dashboard/architecture.md)
- [素材系统](../02-product/features/assets.md)

---

**END OF DOCUMENT**
