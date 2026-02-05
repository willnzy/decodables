# 编辑器性能优化

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **对应代码**: `decodables-fe/app/create/`

---

## 概述

编辑器性能优化策略，确保流畅的编辑体验。

---

## 性能目标

| 指标 | 目标值 |
|------|--------|
| 首次加载 | < 3s |
| 画布渲染 FPS | ≥ 30fps |
| 对象拖动延迟 | < 16ms |
| 自动保存 | < 1s |

---

## 画布优化

### 对象缓存

```typescript
// 启用对象缓存
object.objectCaching = true;

// 对于静态对象，使用更激进的缓存
staticObject.statefullCache = true;
```

### 批量渲染

```typescript
// 批量添加对象时暂停渲染
canvas.renderOnAddRemove = false;

objects.forEach(obj => canvas.add(obj));

// 完成后统一渲染
canvas.renderOnAddRemove = true;
canvas.requestRenderAll();
```

### 视口裁剪

```typescript
// 只渲染视口内的对象
canvas.skipOffscreen = true;
```

---

## 图片优化

### 懒加载

```typescript
// 使用 IntersectionObserver 懒加载图片
const loadImageWhenVisible = (imageObject: fabric.Image) => {
  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      imageObject.setSrc(imageObject._originalSrc);
      observer.disconnect();
    }
  });
  
  observer.observe(canvas.getElement());
};
```

### 缩略图

```typescript
// 素材面板使用缩略图
const thumbnailUrl = getResizedUrl(originalUrl, { width: 200 });
```

### 图片压缩

- 上传时压缩 > 2MB 的图片
- 使用 WebP 格式 (支持时)

---

## 事件优化

### 节流

```typescript
// 拖动事件节流
const handleObjectMoving = throttle((e: fabric.IEvent) => {
  updateProperties(e.target);
}, 16); // 60fps

canvas.on('object:moving', handleObjectMoving);
```

### 防抖

```typescript
// 属性面板输入防抖
const handlePropertyChange = debounce((value: number) => {
  selectedObject.set('width', value);
  canvas.renderAll();
}, 100);
```

---

## 状态优化

### 选择性订阅

```typescript
// 只订阅需要的状态
const zoom = useEditorStore((s) => s.zoom);

// 而不是
const { zoom, pan, ... } = useEditorStore();
```

### 状态分片

Store 按功能拆分为多个 Slice，减少不必要的更新。

---

## 历史记录优化

### 增量记录

```typescript
// 只记录变化的部分
interface HistoryEntry {
  type: 'add' | 'remove' | 'modify';
  objectId: string;
  changes: Partial<ObjectProps>;
  previousValues: Partial<ObjectProps>;
}
```

### 历史压缩

```typescript
// 合并短时间内的连续操作
const compressHistory = (entries: HistoryEntry[]) => {
  // 合并同一对象在 500ms 内的多次修改
};
```

---

## 加载优化

### 代码分割

```typescript
// 按需加载 AI 功能
const AIModal = dynamic(() => import('./_components/AIModal'), {
  loading: () => <Spinner />,
});
```

### 预加载

```typescript
// 预加载常用资源
useEffect(() => {
  // 预加载默认字体
  preloadFonts(['Roboto', 'Open Sans']);
  
  // 预加载常用图标
  preloadIcons(commonIcons);
}, []);
```

---

## Web Worker

### 复杂计算

```typescript
// 将复杂计算移到 Worker
const worker = new Worker('/workers/canvas-worker.ts');

// 发送计算任务
worker.postMessage({ type: 'pathSimplify', path: complexPath });

// 接收结果
worker.onmessage = (e) => {
  const simplifiedPath = e.data.result;
  // 使用结果
};
```

### Worker 任务

- 路径简化
- 图片滤镜
- PDF 生成
- 大量对象序列化

---

## 内存管理

### 及时释放

```typescript
// 离开页面时释放资源
useEffect(() => {
  return () => {
    canvas.dispose();
    worker.terminate();
  };
}, []);
```

### 图片引用

```typescript
// 使用 URL.revokeObjectURL 释放 Blob URL
const blobUrl = URL.createObjectURL(file);
// 使用完毕后
URL.revokeObjectURL(blobUrl);
```

---

## 性能监控

### 指标收集

```typescript
const trackPerformance = () => {
  const metrics = {
    fps: calculateFPS(),
    memory: performance.memory?.usedJSHeapSize,
    objectCount: canvas.getObjects().length,
  };
  
  // 上报到分析系统
  analytics.track('editor_performance', metrics);
};
```

---

## 相关文档

- [架构设计](./architecture.md)
- [性能优化指南](../../development/)
