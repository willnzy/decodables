# AI 功能集成

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/create/_hooks/ai/`

---

## 概述

编辑器中的 AI 功能集成，包括 AI 生图、AI 生页面、OCR 识别。

---

## AI 功能列表

| 功能 | 积分消耗 | 提供商 |
|------|----------|--------|
| AI 生图 | 5 | FAL.ai |
| AI 生页面 | 5 | FAL.ai + OpenAI |
| OCR 识别 | 10 | OpenAI Vision |

---

## AI 生图

### 流程

```
用户输入描述 → 调用 FAL.ai → 返回图片 → 添加到画布
```

### API 调用

```typescript
const generateImage = async (prompt: string) => {
  // 1. 检查积分
  const hasCredits = await checkCredits(5);
  if (!hasCredits) {
    showUpgradeDialog();
    return;
  }
  
  // 2. 调用 API
  const result = await api.post('/api/ai/generate-image', {
    prompt,
    size: '1024x1024',
  });
  
  // 3. 添加到画布
  fabric.Image.fromURL(result.imageUrl, (img) => {
    canvas.add(img);
    canvas.centerObject(img);
  });
  
  // 4. 扣除积分
  await deductCredits(5);
};
```

### 生成参数

```typescript
interface GenerateImageParams {
  prompt: string;
  negativePrompt?: string;
  size: '512x512' | '1024x1024' | '1024x768' | '768x1024';
  style?: 'realistic' | 'cartoon' | 'anime' | 'painting';
}
```

---

## AI 生页面

### 流程

```
用户输入描述 → AI 分析 → 生成布局 → 生成元素 → 渲染到画布
```

### 生成策略

1. **分析 Prompt**: 使用 GPT 分析用户意图
2. **生成布局**: 确定元素位置和大小
3. **生成内容**: 文字用 GPT 生成，图片用 FAL.ai
4. **渲染**: 将生成的元素添加到画布

### 布局模板

```typescript
interface PageLayout {
  elements: {
    type: 'text' | 'image' | 'shape';
    position: { x: number; y: number };
    size: { width: number; height: number };
    content?: string;
    style?: object;
  }[];
}
```

---

## OCR 识别

### 流程

```
选择图片 → 发送到 OpenAI Vision → 返回文字 → 添加文字对象
```

### 实现

```typescript
const recognizeText = async (imageObject: fabric.Image) => {
  // 1. 获取图片 base64
  const dataUrl = imageObject.toDataURL();
  
  // 2. 调用 OCR API
  const result = await api.post('/api/ai/ocr', {
    image: dataUrl,
  });
  
  // 3. 创建文字对象
  const textbox = new fabric.Textbox(result.text, {
    left: imageObject.left,
    top: imageObject.top + imageObject.height + 20,
    width: imageObject.width,
  });
  
  canvas.add(textbox);
};
```

---

## 积分检查

### 前端检查

```typescript
const useAICreditsCheck = () => {
  const { credits } = useUserStore();
  
  const checkCredits = (required: number) => {
    if (credits < required) {
      return {
        canUse: false,
        shortage: required - credits,
      };
    }
    return { canUse: true };
  };
  
  return { checkCredits };
};
```

### 积分不足提示

```
┌─────────────────────────────────────┐
│ 积分不足                            │
├─────────────────────────────────────┤
│ AI 生图需要 5 积分                  │
│ 当前积分: 3                         │
│                                     │
│ [取消]  [充值积分]                  │
└─────────────────────────────────────┘
```

---

## 生成历史

### 存储

```typescript
interface AIGenerationRecord {
  id: string;
  type: 'image' | 'page' | 'ocr';
  prompt: string;
  result: string;  // URL 或文本
  createdAt: Date;
}
```

### UI 显示

在 Media 面板的"AI 生成"Tab 显示历史记录，方便重复使用。

---

## 错误处理

| 错误 | 处理 |
|------|------|
| 积分不足 | 显示充值引导 |
| 生成失败 | 重试按钮 + 不扣积分 |
| 超时 | 提示稍后重试 |
| 内容违规 | 提示修改 Prompt |

---

## 相关文档

- [AI 模块架构](../ai/)
- [积分系统](../../../05-business/credits-system/)
