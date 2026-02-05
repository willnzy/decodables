# 编辑器状态管理

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **对应代码**: `decodables-fe/app/create/_stores/`

---

## 概述

使用 Zustand 进行状态管理，采用 Slice 模式拆分不同职责的状态。

---

## Store 架构

```typescript
// useEditorStore.ts
import { create } from 'zustand';
import { canvasSlice, CanvasSlice } from './slices/canvasSlice';
import { historySlice, HistorySlice } from './slices/historySlice';
import { pageSlice, PageSlice } from './slices/pageSlice';
import { projectSlice, ProjectSlice } from './slices/projectSlice';
import { uiSlice, UISlice } from './slices/uiSlice';
import { mobileSlice, MobileSlice } from './slices/mobileSlice';

type EditorStore = CanvasSlice & HistorySlice & PageSlice & 
                   ProjectSlice & UISlice & MobileSlice;

export const useEditorStore = create<EditorStore>()((...a) => ({
  ...canvasSlice(...a),
  ...historySlice(...a),
  ...pageSlice(...a),
  ...projectSlice(...a),
  ...uiSlice(...a),
  ...mobileSlice(...a),
}));
```

---

## Slices 说明

### canvasSlice

```typescript
interface CanvasSlice {
  // 状态
  canvas: fabric.Canvas | null;
  selectedObjects: fabric.Object[];
  zoom: number;
  panOffset: { x: number; y: number };
  
  // 操作
  setCanvas: (canvas: fabric.Canvas) => void;
  setSelectedObjects: (objects: fabric.Object[]) => void;
  setZoom: (zoom: number) => void;
  setPanOffset: (offset: { x: number; y: number }) => void;
}
```

### historySlice

```typescript
interface HistorySlice {
  // 状态
  undoStack: CanvasState[];
  redoStack: CanvasState[];
  canUndo: boolean;
  canRedo: boolean;
  
  // 操作
  pushHistory: (state: CanvasState) => void;
  undo: () => void;
  redo: () => void;
  clearHistory: () => void;
}
```

### pageSlice

```typescript
interface PageSlice {
  // 状态
  pages: Page[];
  currentPageIndex: number;
  
  // 操作
  addPage: () => void;
  deletePage: (index: number) => void;
  duplicatePage: (index: number) => void;
  reorderPages: (from: number, to: number) => void;
  setCurrentPage: (index: number) => void;
}
```

### projectSlice

```typescript
interface ProjectSlice {
  // 状态
  projectId: string | null;
  projectName: string;
  isDirty: boolean;
  lastSavedAt: Date | null;
  
  // 操作
  setProjectId: (id: string) => void;
  setProjectName: (name: string) => void;
  markDirty: () => void;
  markClean: () => void;
}
```

### uiSlice

```typescript
interface UISlice {
  // 状态
  activeTool: ToolType;
  leftPanelTab: 'pages' | 'assets' | 'templates';
  showGrid: boolean;
  showRulers: boolean;
  leftPanelCollapsed: boolean;
  rightPanelCollapsed: boolean;
  
  // 操作
  setActiveTool: (tool: ToolType) => void;
  setLeftPanelTab: (tab: string) => void;
  toggleGrid: () => void;
  toggleRulers: () => void;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
}
```

### mobileSlice

```typescript
interface MobileSlice {
  // 状态
  isMobileView: boolean;
  activeSheet: 'none' | 'media' | 'properties' | 'tools';
  
  // 操作
  setMobileView: (isMobile: boolean) => void;
  openSheet: (sheet: string) => void;
  closeSheet: () => void;
}
```

---

## 使用示例

```tsx
// 组件中使用
const Tool = () => {
  // 选择性订阅，避免不必要的重渲染
  const activeTool = useEditorStore((s) => s.activeTool);
  const setActiveTool = useEditorStore((s) => s.setActiveTool);
  
  return (
    <button onClick={() => setActiveTool('brush')}>
      画笔
    </button>
  );
};
```

---

## 持久化

```typescript
// 部分状态持久化到 localStorage
import { persist } from 'zustand/middleware';

const uiSlice = persist(
  (set) => ({
    showGrid: true,
    showRulers: true,
    // ...
  }),
  {
    name: 'editor-ui-preferences',
    partialize: (state) => ({
      showGrid: state.showGrid,
      showRulers: state.showRulers,
    }),
  }
);
```

---

## 相关文档

- [架构设计](./architecture.md)
- [状态管理规范](../../development/state-management.md)
