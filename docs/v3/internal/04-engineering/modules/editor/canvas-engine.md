# 画布引擎

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **对应代码**: `decodables-fe/app/create/_hooks/canvas/`

---

## 概述

基于 Fabric.js 5.3.0 封装的画布引擎，提供对象管理、渲染、事件处理等核心功能。

---

## 技术选型

| 选项 | 选择 | 理由 |
|------|------|------|
| 渲染库 | Fabric.js 5.3.0 | 成熟、功能全、社区活跃 |
| 渲染模式 | Canvas 2D | 兼容性好，满足需求 |

---

## 核心 Hooks

### useCanvasInit

```typescript
// 初始化 Fabric Canvas
const useCanvasInit = (containerRef: RefObject<HTMLDivElement>) => {
  const [canvas, setCanvas] = useState<fabric.Canvas | null>(null);
  
  useEffect(() => {
    const fabricCanvas = new fabric.Canvas('canvas', {
      selection: true,
      preserveObjectStacking: true,
      // ... 配置
    });
    setCanvas(fabricCanvas);
    
    return () => fabricCanvas.dispose();
  }, []);
  
  return canvas;
};
```

### useCanvasObjects

```typescript
// 对象 CRUD 操作
const useCanvasObjects = (canvas: fabric.Canvas) => {
  const addObject = (obj: fabric.Object) => { ... };
  const removeObject = (obj: fabric.Object) => { ... };
  const updateObject = (id: string, props: Partial<ObjectProps>) => { ... };
  const getObjectById = (id: string) => { ... };
  
  return { addObject, removeObject, updateObject, getObjectById };
};
```

### useCanvasEvents

```typescript
// 事件监听
const useCanvasEvents = (canvas: fabric.Canvas) => {
  useEffect(() => {
    canvas.on('selection:created', handleSelectionCreated);
    canvas.on('selection:updated', handleSelectionUpdated);
    canvas.on('object:modified', handleObjectModified);
    // ...
    
    return () => {
      canvas.off('selection:created');
      // ...
    };
  }, [canvas]);
};
```

---

## 对象序列化

### 自定义属性

```typescript
// 扩展 Fabric 对象属性
fabric.Object.prototype.toObject = (function(toObject) {
  return function(this: fabric.Object, propertiesToInclude?: string[]) {
    return fabric.util.object.extend(toObject.call(this, propertiesToInclude), {
      id: this.id,
      name: this.name,
      locked: this.locked,
      // 自定义属性
    });
  };
})(fabric.Object.prototype.toObject);
```

### 序列化格式

```json
{
  "version": "5.3.0",
  "objects": [
    {
      "type": "rect",
      "id": "obj_001",
      "left": 100,
      "top": 100,
      "width": 200,
      "height": 150,
      "fill": "#3B82F6",
      "name": "蓝色矩形",
      "locked": false
    }
  ],
  "background": "#FFFFFF"
}
```

---

## 性能优化

### 渲染优化

```typescript
// 批量操作时暂停渲染
canvas.renderOnAddRemove = false;
// ... 批量添加对象
canvas.renderOnAddRemove = true;
canvas.requestRenderAll();
```

### 对象缓存

```typescript
// 启用对象缓存
object.objectCaching = true;
object.statefullCache = true;
```

---

## 坐标系统

```
Canvas 坐标系:
(0,0) ────────────→ x
  │
  │
  │
  ↓
  y
```

- 原点在左上角
- x 向右增加
- y 向下增加

---

## 相关文档

- [架构设计](./architecture.md)
- [状态管理](./state-management.md)
- [画布区域页面设计](../../../02-product/pages/user/editor/canvas.md)
