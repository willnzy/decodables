# 编辑器模块架构

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `decodables-fe/app/create/`, `domains/creation/`

---

## 一、模块概述

### 1.1 职责范围

编辑器模块是应用核心，负责：
- **Canvas 画布**: Fabric.js 图形编辑
- **媒体管理**: 图片、文字、形状处理
- **页面管理**: 8 页 Mini-book 结构
- **历史记录**: Undo/Redo 功能
- **项目保存**: 自动保存、导出

### 1.2 技术栈

| 技术 | 用途 |
|------|------|
| **Fabric.js 5.3.0** | Canvas 图形引擎 |
| **Zustand** | 状态管理 (Slice 架构) |
| **Web Worker** | 后台计算 |
| **IndexedDB** | 本地缓存 |

---

## 二、代码结构

### 2.1 前端结构 (核心)

```
app/create/
├── page.tsx                    # 编辑器页面
├── layout.tsx                  # 布局
├── _stores/                    # 状态管理
│   ├── useEditorStore.ts       # 主 Store
│   ├── types.ts                # 类型定义
│   └── slices/                 # Store 切片
│       ├── pageSlice.ts        # 页面状态
│       ├── projectSlice.ts     # 项目状态
│       ├── uiSlice.ts          # UI 状态
│       ├── canvasSlice.ts      # Canvas 状态
│       ├── historySlice.ts     # 历史状态
│       └── mobileSlice.ts      # 移动端状态
├── _components/                # UI 组件
│   ├── Canvas/                 # 画布组件
│   ├── Toolbar/                # 工具栏
│   ├── Panels/                 # 面板
│   ├── Properties/             # 属性面板
│   └── Modals/                 # 弹窗
├── _hooks/                     # Hooks
│   ├── canvas/                 # Canvas 操作
│   ├── editor/                 # 编辑器逻辑
│   ├── ai/                     # AI 功能
│   └── ui/                     # UI 控制
├── _services/                  # 服务层
└── _types/                     # 类型定义
```

### 2.2 后端结构

```
domains/creation/
├── __init__.py
├── aggregates/
│   └── project.py              # Project 聚合根
├── exceptions.py               # 领域异常
├── locked_elements.py          # 元素锁定
├── repository.py               # Repository 接口
├── service.py                  # 创作服务
├── thumbnail_service.py        # 缩略图服务
└── value_objects.py            # 值对象

api/user/
├── projects.py                 # 项目 CRUD API
└── export.py                   # 导出 API
```

---

## 三、状态管理

### 3.1 Store 架构 (V4)

```
┌─────────────────────────────────────────────────────────────┐
│                    useEditorStore                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐│
│  │ pageSlice │  │projectSlice│  │  uiSlice  │  │canvasSlice││
│  ├───────────┤  ├───────────┤  ├───────────┤  ├───────────┤│
│  │ pages[]   │  │ projectId │  │ panels    │  │ zoom      ││
│  │ currentIdx│  │ title     │  │ modals    │  │ grid      ││
│  │ pageData  │  │ topic     │  │ responsive│  │ selection ││
│  │           │  │ saveStatus│  │           │  │ tool      ││
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘│
│                                                             │
│  ┌───────────┐  ┌───────────┐                               │
│  │historySlice│ │mobileSlice│                               │
│  ├───────────┤  ├───────────┤                               │
│  │ past[]    │  │ bottomSheet│                              │
│  │ future[]  │  │ contextMenu│                              │
│  │ canUndo   │  │ gestures   │                              │
│  │ canRedo   │  │            │                              │
│  └───────────┘  └───────────┘                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Slice 职责

| Slice | 职责 |
|-------|------|
| **pageSlice** | 页面数据 (8 页结构)、当前页索引 |
| **projectSlice** | 项目元数据、保存状态 |
| **uiSlice** | 面板、弹窗、响应式断点 |
| **canvasSlice** | 缩放、网格、工具、选中对象 |
| **historySlice** | 撤销/重做栈 |
| **mobileSlice** | 移动端交互状态 |

### 3.3 状态持久化

```typescript
// 持久化到 localStorage
persist(
  (set, get, api) => ({ /* store */ }),
  {
    name: "editor-store",
    version: STORE_VERSION,
    storage: safeStorageAdapter,
    partialize: (state) => ({
      paperSize: state.paperSize,
      globalTopic: state.globalTopic,
      thumbnailSidebarVisible: state.thumbnailSidebarVisible,
    }),
    migrate: migrateStore,
  }
)
```

---

## 四、Canvas 架构

### 4.1 Fabric.js 集成

```typescript
// Canvas 初始化
const initCanvas = (canvasEl: HTMLCanvasElement) => {
  const canvas = new fabric.Canvas(canvasEl, {
    preserveObjectStacking: true,
    selection: true,
    renderOnAddRemove: false,  // 性能优化
  });
  
  // 注册自定义控件
  registerCustomControls(canvas);
  
  // 绑定事件
  bindCanvasEvents(canvas);
  
  return canvas;
};
```

### 4.2 对象模型

```typescript
// Canvas 对象类型
type CanvasObjectType = 
  | "image"       // 图片
  | "i-text"      // 可编辑文字
  | "textbox"     // 文本框
  | "path"        // 路径/手绘
  | "rect"        // 矩形
  | "circle"      // 圆形
  | "group"       // 组合
  | "activeSelection";  // 多选

// 自定义属性
interface CustomObjectProps {
  objectId: string;       // 唯一 ID
  locked: boolean;        // 锁定状态
  layerOrder: number;     // 图层顺序
  customType?: string;    // 自定义类型标记
}
```

### 4.3 事件系统

```typescript
// Canvas 事件处理
canvas.on({
  "selection:created": handleSelectionCreated,
  "selection:updated": handleSelectionUpdated,
  "selection:cleared": handleSelectionCleared,
  "object:modified": handleObjectModified,
  "object:added": handleObjectAdded,
  "object:removed": handleObjectRemoved,
  "mouse:down": handleMouseDown,
  "mouse:move": handleMouseMove,
  "mouse:up": handleMouseUp,
});
```

---

## 五、媒体管理

### 5.1 图片处理

```typescript
// useCanvasAddObjects hook
const addImage = async (url: string, options?: ImageOptions) => {
  // 1. 加载图片
  const img = await loadImage(url);
  
  // 2. 计算初始尺寸 (适应画布)
  const { width, height } = calculateFitSize(img, canvas);
  
  // 3. 创建 Fabric Image
  const fabricImage = new fabric.Image(img, {
    left: canvas.width / 2,
    top: canvas.height / 2,
    originX: "center",
    originY: "center",
    ...options,
  });
  
  // 4. 添加到画布
  canvas.add(fabricImage);
  canvas.setActiveObject(fabricImage);
  
  // 5. 记录历史
  pushHistory();
};
```

### 5.2 文字处理

```typescript
// 添加文字
const addText = (text: string, options?: TextOptions) => {
  const textbox = new fabric.Textbox(text, {
    left: 100,
    top: 100,
    width: 200,
    fontSize: 24,
    fontFamily: "Inter",
    fill: "#000000",
    ...options,
  });
  
  canvas.add(textbox);
  canvas.setActiveObject(textbox);
  pushHistory();
};

// 艺术字 (SVG 路径文字)
const addCurvedText = (text: string, pathType: PathType) => {
  const path = generateTextPath(text, pathType);
  // ...
};
```

### 5.3 形状处理

```typescript
// 预设形状
const SHAPES = {
  rectangle: fabric.Rect,
  circle: fabric.Circle,
  triangle: fabric.Triangle,
  star: createStarPath,
  arrow: createArrowPath,
};

const addShape = (type: ShapeType, options?: ShapeOptions) => {
  const ShapeClass = SHAPES[type];
  const shape = new ShapeClass({
    left: 100,
    top: 100,
    fill: "#4F46E5",
    stroke: "#312E81",
    strokeWidth: 2,
    ...options,
  });
  
  canvas.add(shape);
  pushHistory();
};
```

---

## 六、页面管理

### 6.1 Mini-book 结构

```typescript
// 8 页结构
interface ZinePage {
  pageNumber: number;     // 1-8
  pageType: PageType;     // cover, content, back
  canvasJson: CanvasJson; // Fabric.js JSON
  thumbnail?: string;     // 缩略图 URL
}

type PageType = 
  | "cover"        // 封面 (第 1 页)
  | "content"      // 内容页 (第 2-7 页)
  | "back";        // 封底 (第 8 页)
```

### 6.2 页面操作

```typescript
// pageSlice actions
const pageActions = {
  // 切换页面
  setCurrentPage: (index: number) => {
    // 1. 保存当前页 Canvas JSON
    saveCurrentPageCanvas();
    // 2. 切换索引
    set({ currentPageIndex: index });
    // 3. 加载目标页 Canvas
    loadPageCanvas(index);
  },
  
  // 复制页面
  copyPage: (sourceIndex: number, targetIndex: number) => {
    const sourceJson = get().pages[sourceIndex].canvasJson;
    // ...
  },
  
  // 清空页面
  clearPage: (index: number) => {
    // ...
  },
};
```

---

## 七、历史记录

### 7.1 Undo/Redo 实现

```typescript
// historySlice
interface HistoryState {
  past: HistoryEntry[];     // 撤销栈
  future: HistoryEntry[];   // 重做栈
  maxHistory: number;       // 最大历史数 (50)
}

interface HistoryEntry {
  canvasJson: CanvasJson;
  pageIndex: number;
  timestamp: number;
}

// 推入历史
const pushHistory = () => {
  const entry = createHistoryEntry();
  set((state) => ({
    past: [...state.past.slice(-maxHistory + 1), entry],
    future: [], // 清空重做栈
  }));
};

// 撤销
const undo = () => {
  const { past, future } = get();
  if (past.length === 0) return;
  
  const current = createHistoryEntry();
  const previous = past[past.length - 1];
  
  set({
    past: past.slice(0, -1),
    future: [current, ...future],
  });
  
  applyHistoryEntry(previous);
};
```

### 7.2 快捷键

```typescript
// useHotkeys hook
useHotkeys([
  { keys: ["mod+z"], action: undo },
  { keys: ["mod+shift+z", "mod+y"], action: redo },
  { keys: ["mod+c"], action: copy },
  { keys: ["mod+v"], action: paste },
  { keys: ["mod+x"], action: cut },
  { keys: ["Delete", "Backspace"], action: deleteSelected },
  { keys: ["mod+a"], action: selectAll },
  { keys: ["mod+d"], action: duplicate },
  { keys: ["mod+g"], action: group },
  { keys: ["mod+shift+g"], action: ungroup },
]);
```

---

## 八、项目保存

### 8.1 保存流程

```
┌────────────────────────────────────────────────────────────┐
│                    Save Flow                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. 触发保存 (手动 / 自动保存)                              │
│           │                                                │
│           ▼                                                │
│  2. 收集数据                                               │
│     - 所有页面 Canvas JSON                                  │
│     - 项目元数据 (title, topic)                            │
│           │                                                │
│           ▼                                                │
│  3. 生成缩略图                                             │
│     - 每页生成 200x200 预览图                               │
│           │                                                │
│           ▼                                                │
│  4. 调用后端 API                                           │
│     PUT /projects/{id}                                     │
│           │                                                │
│           ▼                                                │
│  5. 更新保存状态                                           │
│     saveStatus: "saved"                                    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 8.2 自动保存

```typescript
// useAutoSave hook
const useAutoSave = () => {
  const { isDirty, saveProject } = useEditorStore();
  
  useEffect(() => {
    if (!isDirty) return;
    
    const timer = setTimeout(() => {
      saveProject();
    }, AUTO_SAVE_DELAY); // 3000ms
    
    return () => clearTimeout(timer);
  }, [isDirty]);
};
```

### 8.3 乐观更新

```typescript
// useOptimisticSave hook
const saveWithOptimistic = async () => {
  // 1. 立即更新 UI (乐观)
  set({ saveStatus: "saving" });
  
  try {
    // 2. 调用 API
    await saveProjectAPI(projectData);
    set({ saveStatus: "saved" });
  } catch (error) {
    // 3. 失败回滚
    set({ saveStatus: "error" });
    showToast("保存失败，请重试");
  }
};
```

---

## 九、后端 Entity

### 9.1 Project 聚合根

```python
@dataclass
class Project:
    """项目聚合根"""
    id: UUID
    user_id: UUID
    workspace_id: UUID
    
    # 元数据
    title: str
    topic: Optional[str]
    paper_size: str  # Letter, A4, etc.
    
    # 内容
    pages: List[ProjectPage]
    thumbnail_url: Optional[str]
    
    # 状态
    is_deleted: bool = False
    
    # 时间
    created_at: datetime
    updated_at: datetime
```

### 9.2 ProjectPage

```python
@dataclass
class ProjectPage:
    """项目页面"""
    page_number: int
    page_type: str  # cover, content, back
    canvas_json: dict
    thumbnail_url: Optional[str]
```

---

## 十、API 端点

### 10.1 项目 CRUD

| 端点 | 方法 | 说明 |
|------|------|------|
| `/projects` | GET | 项目列表 |
| `/projects` | POST | 创建项目 |
| `/projects/{id}` | GET | 获取项目 |
| `/projects/{id}` | PUT | 更新项目 |
| `/projects/{id}` | DELETE | 删除项目 |

### 10.2 导出

| 端点 | 方法 | 说明 |
|------|------|------|
| `/export/image` | POST | 导出图片 (PNG/JPG) |
| `/export/pdf` | POST | 导出 PDF |

---

## 十一、性能优化

### 11.1 Canvas 优化

```typescript
// 1. 批量渲染
canvas.renderOnAddRemove = false;
// 添加多个对象后手动渲染
canvas.requestRenderAll();

// 2. 对象缓存
object.objectCaching = true;

// 3. 离屏 Canvas
const offscreenCanvas = document.createElement("canvas");
```

### 11.2 状态优化

```typescript
// 1. 选择性订阅
const zoom = useEditorStore(useShallow((s) => s.zoom));

// 2. 计算属性缓存
const canUndo = useEditorStore((s) => s.past.length > 0);

// 3. 批量更新
set((state) => ({
  ...state,
  prop1: value1,
  prop2: value2,
}));
```

### 11.3 Web Worker

```typescript
// 后台计算 (不阻塞 UI)
const worker = new Worker("/_workers/canvasWorker.ts");

worker.postMessage({ type: "generateThumbnail", data });
worker.onmessage = (e) => {
  const { thumbnail } = e.data;
  // 更新缩略图
};
```

---

## 十二、相关文档

- [Canvas 架构设计](../../../docs/[重构后]Canvas-Architecture-Design.md)
- [媒体属性设计](../../../docs/[重构后]Editor-Media-Properties-Redesign.md)
- [文字字体方案](../../../docs/[重构后]Text-Font-Solution-Design.md)
- [API 参考 - 项目](../../03-api/projects.md)

---

**END OF DOCUMENT**
