# 导出服务

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/create/_hooks/editor/useEditorExport.ts`

---

## 概述

编辑器作品导出功能，支持多种格式和分辨率。

---

## 导出格式

| 格式 | 说明 | 限制 |
|------|------|------|
| PNG | 位图，支持透明 | 最大 8192×8192 |
| JPEG | 位图，较小文件 | 不支持透明 |
| PDF | 矢量/位图混合 | 单页/多页 |
| SVG | 矢量 | 仅矢量元素 |

---

## 分辨率选项

| 选项 | 倍数 | 适用场景 |
|------|------|----------|
| 标清 (SD) | 1x | 预览、社交分享 |
| 高清 (HD) | 2x | 打印、高分屏 |
| 超高清 (UHD) | 4x | 专业打印 (仅 t3) |

---

## 导出流程

### 前端流程

```typescript
const exportProject = async (format: ExportFormat, options: ExportOptions) => {
  // 1. 获取画布数据
  const canvasData = canvas.toJSON();
  
  // 2. 根据格式处理
  if (format === 'png' || format === 'jpeg') {
    return exportAsImage(canvas, format, options);
  } else if (format === 'pdf') {
    return exportAsPDF(canvas, options);
  } else if (format === 'svg') {
    return exportAsSVG(canvas);
  }
};
```

### PNG/JPEG 导出

```typescript
const exportAsImage = (canvas: fabric.Canvas, format: string, options: ExportOptions) => {
  const multiplier = options.resolution === 'hd' ? 2 : options.resolution === 'uhd' ? 4 : 1;
  
  const dataURL = canvas.toDataURL({
    format: format,
    quality: format === 'jpeg' ? 0.9 : undefined,
    multiplier: multiplier,
  });
  
  // 下载
  downloadFile(dataURL, `${projectName}.${format}`);
};
```

### PDF 导出

```typescript
const exportAsPDF = async (canvas: fabric.Canvas, options: ExportOptions) => {
  const pdf = new jsPDF({
    orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
    unit: 'px',
    format: [canvas.width, canvas.height],
  });
  
  // 遍历所有页面
  for (let i = 0; i < pages.length; i++) {
    if (i > 0) pdf.addPage();
    
    const pageCanvas = await renderPage(pages[i]);
    const imgData = pageCanvas.toDataURL('image/png');
    pdf.addImage(imgData, 'PNG', 0, 0);
  }
  
  pdf.save(`${projectName}.pdf`);
};
```

---

## 权限控制

| Tier | SD (1x) | HD (2x) | UHD (4x) | 水印 |
|------|---------|---------|----------|------|
| t1 | ✅ | ❌ | ❌ | 有 |
| t2 | ✅ | ✅ | ❌ | 无 |
| t3 | ✅ | ✅ | ✅ | 无 |

### 水印添加

```typescript
const addWatermark = (canvas: fabric.Canvas) => {
  const watermark = new fabric.Text('Make Decodables', {
    fontSize: 24,
    fill: 'rgba(0,0,0,0.3)',
    // 位置：右下角
    left: canvas.width - 150,
    top: canvas.height - 40,
  });
  canvas.add(watermark);
};
```

---

## 导出对话框

```
┌─────────────────────────────────────┐
│ 导出作品                            │
├─────────────────────────────────────┤
│ 格式                                │
│ [PNG ▼] [JPEG] [PDF] [SVG]          │
│                                     │
│ 分辨率                              │
│ ○ 标清 (1x) - 1080×1920            │
│ ● 高清 (2x) - 2160×3840            │
│ ○ 超高清 (4x) - 4320×7680 [Pro]    │
│                                     │
│ □ 包含背景                          │
│ □ 仅导出选中对象                    │
│                                     │
│ 页面范围 (PDF)                      │
│ ○ 全部页面                          │
│ ○ 当前页面                          │
│ ○ 自定义 [1-3, 5]                   │
│                                     │
│        [取消]  [导出]               │
└─────────────────────────────────────┘
```

---

## 后端导出 (可选)

对于大文件或复杂 PDF，可使用后端处理：

```
POST /api/projects/{id}/export
{
  "format": "pdf",
  "pages": [1, 2, 3],
  "resolution": "hd"
}

→ 返回下载链接
```

---

## 相关文档

- [架构设计](./architecture.md)
- [Tier 权益](../../../05-business/tier-system.md)
