# 文字与字体系统

> Text & Font Solution - 文字编辑、字体加载、艺术字效果

> **同步范围**: [frontend]
> **状态**: 🟢 已验证
> **最后更新**: 2026-02-05
> **数据来源**: `@core/components/editor/`, `@business/stores/editor/`

---

## 一、概述

文字与字体系统为编辑器提供文本编辑、字体选择、艺术字效果等能力，是教育类 Web 编辑器的核心功能。

---

## 二、设计原则

| 原则 | 说明 | 优先级 |
|------|------|--------|
| **零授权风险** | 仅使用开源免费商用字体 | 🔴 最高 |
| **性能优先** | 按需加载、智能预加载、本地缓存 | 🔴 最高 |
| **用户友好** | 分类清晰、预览直观、搜索便捷 | 🔴 高 |
| **可扩展** | 后台可配置、支持自定义字体 | 🟡 中 |

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       字体系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    字体来源层                            │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │   │
│  │  │ Google Fonts │ │  Fontsource  │ │  自定义字体   │    │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    字体存储层                            │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │           Cloudflare R2 / Vercel Blob            │   │   │
│  │  │  /fonts/{font-name}-{weight}.woff2               │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    客户端加载层                          │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │   │
│  │  │  关键字体     │ │  常用字体     │ │  按需字体     │    │   │
│  │  │  (首屏同步)   │ │  (空闲预载)   │ │  (用户触发)   │    │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    本地缓存层                            │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │   │
│  │  │ Memory Cache │ │ Service      │ │  IndexedDB   │    │   │
│  │  │ (FontFace)   │ │ Worker       │ │  (字体元数据) │    │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、字体来源与授权

### 4.1 推荐字体来源

| 来源 | 字体数量 | 授权类型 | 推荐度 |
|------|----------|----------|--------|
| **Google Fonts** | 1,500+ | OFL/Apache 2.0 | ⭐⭐⭐⭐⭐ |
| **Fontsource** | 1,500+ | 同 Google | ⭐⭐⭐⭐⭐ |
| **Bunny Fonts** | 1,400+ | 同 Google | ⭐⭐⭐⭐ |

### 4.2 授权合规

```
✅ OFL (SIL Open Font License)
- 免费商业使用 ✓
- 可修改和再分发 ✓
- 可嵌入软件/网站 ✓
- 需保留版权声明 ✓

✅ Apache 2.0 License
- 免费商业使用 ✓
- 可修改和再分发 ✓
```

---

## 五、字体分类

### 5.1 分类体系

| 分类 | 英文名 | 代表字体 | 使用场景 |
|------|--------|----------|----------|
| 无衬线 | Sans-serif | Inter, Roboto | 正文、标题 |
| 衬线体 | Serif | Playfair Display | 优雅标题 |
| 手写体 | Handwriting | Caveat, Pacifico | 装饰、签名 |
| 展示体 | Display | Lobster, Bangers | 海报、标题 |
| 等宽体 | Monospace | JetBrains Mono | 代码、数字 |
| 教育体 | Educational | Comic Neue | 教学材料 |

### 5.2 教育场景推荐

```typescript
// 针对 K-12 教育的字体推荐
const EDUCATIONAL_FONTS = [
  'Comic Neue',      // 手写风格，适合低年级
  'Nunito',          // 圆润友好
  'Lexend',          // 提高阅读效率
  'OpenDyslexic',    // 阅读障碍友好
];
```

---

## 六、字体加载策略

### 6.1 加载优先级

| 优先级 | 类型 | 加载时机 | 字体示例 |
|--------|------|----------|----------|
| P0 | 关键字体 | 首屏同步 | Inter (UI 字体) |
| P1 | 常用字体 | 空闲预加载 | Roboto, Open Sans |
| P2 | 按需字体 | 用户选择时 | 其他字体 |

### 6.2 加载实现

```typescript
// 字体加载服务
class FontLoader {
  private loadedFonts = new Set<string>();
  
  async loadFont(fontFamily: string, weight: number = 400): Promise<void> {
    const key = `${fontFamily}-${weight}`;
    
    if (this.loadedFonts.has(key)) return;
    
    const fontUrl = `/fonts/${fontFamily.toLowerCase()}-${weight}.woff2`;
    
    const font = new FontFace(fontFamily, `url(${fontUrl})`, {
      weight: String(weight),
      display: 'swap',
    });
    
    await font.load();
    document.fonts.add(font);
    this.loadedFonts.add(key);
  }
  
  async preloadFonts(fonts: string[]): Promise<void> {
    // 使用 requestIdleCallback 在空闲时预加载
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        fonts.forEach(font => this.loadFont(font));
      });
    }
  }
}
```

### 6.3 缓存策略

```typescript
// Service Worker 缓存配置
const FONT_CACHE_NAME = 'fonts-v1';
const FONT_TTL = 365 * 24 * 60 * 60 * 1000; // 1 年

// HTTP 缓存头
// Cache-Control: public, max-age=31536000, immutable
```

---

## 七、文字编辑功能

### 7.1 基础属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| fontFamily | string | 'Inter' | 字体 |
| fontSize | number | 24 | 字号 (px) |
| fontWeight | number | 400 | 字重 |
| fontStyle | string | 'normal' | 斜体 |
| fill | string | '#000000' | 文字颜色 |
| textAlign | string | 'left' | 对齐方式 |
| lineHeight | number | 1.2 | 行高 |
| charSpacing | number | 0 | 字间距 |

### 7.2 高级效果

```typescript
// Fabric.js 文字对象扩展
interface TextEffects {
  // 描边
  stroke?: string;
  strokeWidth?: number;
  
  // 阴影
  shadow?: {
    color: string;
    blur: number;
    offsetX: number;
    offsetY: number;
  };
  
  // 渐变填充
  gradientFill?: {
    type: 'linear' | 'radial';
    colors: string[];
    angle?: number;
  };
  
  // 轮廓
  outline?: {
    color: string;
    width: number;
  };
}
```

---

## 八、艺术字系统

### 8.1 预设样式

| 样式 | 描述 | 效果 |
|------|------|------|
| Shadow | 阴影文字 | 立体感 |
| Outline | 描边文字 | 醒目 |
| Gradient | 渐变文字 | 时尚 |
| 3D | 立体文字 | 海报 |
| Neon | 霓虹灯效果 | 夜店风 |
| Comic | 漫画风格 | 趣味 |

### 8.2 样式数据结构

```typescript
interface ArtTextStyle {
  id: string;
  name: string;
  thumbnail: string;
  properties: {
    fontFamily: string;
    fill: string | CanvasGradient;
    stroke?: string;
    strokeWidth?: number;
    shadow?: Shadow;
    // ... 其他属性
  };
}

// 预设样式库
const ART_TEXT_PRESETS: ArtTextStyle[] = [
  {
    id: 'shadow-blue',
    name: '蓝色阴影',
    thumbnail: '/presets/shadow-blue.png',
    properties: {
      fontFamily: 'Bangers',
      fill: '#3B82F6',
      shadow: {
        color: 'rgba(0,0,0,0.3)',
        blur: 10,
        offsetX: 4,
        offsetY: 4,
      },
    },
  },
  // ... 更多预设
];
```

---

## 九、文字模板 (Canva 风格)

### 9.1 模板类型

| 类型 | 描述 | 示例 |
|------|------|------|
| 标题组合 | 主标题 + 副标题 | "SALE" + "50% OFF" |
| 引用样式 | 引号 + 正文 + 作者 | 名言警句 |
| 列表样式 | 标题 + 列表项 | 清单模板 |
| 徽章样式 | 形状 + 文字 | 促销标签 |

### 9.2 模板数据结构

```typescript
interface TextTemplate {
  id: string;
  name: string;
  category: string;
  thumbnail: string;
  elements: Array<{
    type: 'text';
    content: string;
    position: { x: number; y: number };
    properties: TextProperties;
  }>;
}
```

---

## 十、Fabric.js 集成

### 10.1 文字对象创建

```typescript
import { IText, Textbox } from 'fabric';

// 创建可编辑文本
function createTextObject(text: string, options: Partial<TextProperties>) {
  return new Textbox(text, {
    fontFamily: options.fontFamily || 'Inter',
    fontSize: options.fontSize || 24,
    fill: options.fill || '#000000',
    left: options.left || 100,
    top: options.top || 100,
    width: options.width || 200,
    editable: true,
    // 启用换行
    splitByGrapheme: false,
  });
}
```

### 10.2 文字样式更新

```typescript
// Store action: 更新选中文字样式
function updateTextStyle(property: string, value: any) {
  const activeObject = canvas.getActiveObject();
  
  if (activeObject && activeObject.type === 'textbox') {
    activeObject.set(property, value);
    canvas.renderAll();
    
    // 同步到 Store
    updateObjectInStore(activeObject.id, { [property]: value });
  }
}
```

---

## 十一、多语言支持

### 11.1 支持的语言

| 语言 | 字体推荐 | 特殊处理 |
|------|----------|----------|
| 英文 | Inter, Roboto | 默认支持 |
| 简体中文 | Noto Sans SC | 需加载中文子集 |
| 繁体中文 | Noto Sans TC | 需加载中文子集 |
| 日文 | Noto Sans JP | 需加载日文子集 |
| 韩文 | Noto Sans KR | 需加载韩文子集 |

### 11.2 CJK 字体加载

```typescript
// 中日韩字体需要子集化处理
async function loadCJKFont(fontFamily: string, subset: string) {
  // 仅加载常用字符子集
  const subsetUrl = `/fonts/${fontFamily}-${subset}.woff2`;
  
  const font = new FontFace(fontFamily, `url(${subsetUrl})`, {
    unicodeRange: CJK_UNICODE_RANGES[subset],
  });
  
  await font.load();
  document.fonts.add(font);
}

const CJK_UNICODE_RANGES = {
  'sc-common': 'U+4E00-9FFF',  // 常用汉字
  'sc-ext': 'U+3400-4DBF',     // 扩展 A
};
```

---

## 十二、性能优化

### 12.1 字体文件优化

| 策略 | 效果 | 实现方式 |
|------|------|----------|
| WOFF2 格式 | 压缩率 30%+ | 格式转换 |
| 子集化 | 体积减少 80%+ | 仅保留常用字符 |
| 按需加载 | 减少首屏体积 | 延迟加载 |

### 12.2 渲染优化

```css
/* 字体显示策略 */
@font-face {
  font-family: 'CustomFont';
  src: url('/fonts/custom.woff2') format('woff2');
  font-display: swap; /* 避免 FOIT */
}
```

---

## 十三、相关文档

- [Editor 架构](../modules/editor/architecture.md)
- [Canvas 数据 Schema](../../05-business/canvas-data-schema.md)
- [设计系统](../../../external/03-design/design-system.md)
