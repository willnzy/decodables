# 字体系统

> **同步范围**: [frontend]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `tailwind.config.js`, 设计规范

---

## 一、概述

Make Decodables 使用 Inter 作为主要 UI 字体，支持多种字号和字重配置。

---

## 二、字体族

### 2.1 UI 字体

| 用途 | 字体 | Tailwind |
|------|------|----------|
| 主要字体 | Inter | `font-sans` |
| 代码字体 | JetBrains Mono | `font-mono` |

### 2.2 字体加载

```tsx
// app/layout.tsx
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
});
```

---

## 三、字号规范

### 3.1 标题字号

| 级别 | 字号 | 行高 | Tailwind | 用途 |
|------|------|------|----------|------|
| H1 | 36px | 40px | `text-4xl` | 页面标题 |
| H2 | 30px | 36px | `text-3xl` | 区块标题 |
| H3 | 24px | 32px | `text-2xl` | 卡片标题 |
| H4 | 20px | 28px | `text-xl` | 子标题 |
| H5 | 18px | 28px | `text-lg` | 小标题 |
| H6 | 16px | 24px | `text-base font-semibold` | 列表标题 |

### 3.2 正文字号

| 级别 | 字号 | 行高 | Tailwind | 用途 |
|------|------|------|----------|------|
| Body Large | 18px | 28px | `text-lg` | 引言、重要正文 |
| Body | 16px | 24px | `text-base` | 正文 (默认) |
| Body Small | 14px | 20px | `text-sm` | 辅助文字 |
| Caption | 12px | 16px | `text-xs` | 标签、时间戳 |

---

## 四、字重规范

| 名称 | 值 | Tailwind | 用途 |
|------|-----|----------|------|
| Regular | 400 | `font-normal` | 正文 |
| Medium | 500 | `font-medium` | 标签、按钮 |
| Semibold | 600 | `font-semibold` | 小标题 |
| Bold | 700 | `font-bold` | 大标题 |

---

## 五、行高规范

| 类型 | 比例 | Tailwind |
|------|------|----------|
| 紧凑 | 1.25 | `leading-tight` |
| 正常 | 1.5 | `leading-normal` |
| 宽松 | 1.75 | `leading-relaxed` |
| 松散 | 2 | `leading-loose` |

**推荐**:
- 标题: `leading-tight`
- 正文: `leading-normal` 或 `leading-relaxed`

---

## 六、字间距

| 类型 | 值 | Tailwind | 用途 |
|------|-----|----------|------|
| 紧凑 | -0.025em | `tracking-tight` | 大标题 |
| 正常 | 0 | `tracking-normal` | 正文 |
| 宽松 | 0.025em | `tracking-wide` | 小字标签 |
| 大写 | 0.05em | `tracking-wider` | 按钮文字 |

---

## 七、预设组合

### 7.1 标题组合

```tsx
// 页面标题
<h1 className="text-4xl font-bold tracking-tight text-gray-900">
  页面标题
</h1>

// 区块标题
<h2 className="text-2xl font-semibold text-gray-800">
  区块标题
</h2>

// 卡片标题
<h3 className="text-lg font-medium text-gray-700">
  卡片标题
</h3>
```

### 7.2 正文组合

```tsx
// 正文
<p className="text-base text-gray-600 leading-relaxed">
  正文内容
</p>

// 辅助文字
<p className="text-sm text-gray-500">
  辅助说明
</p>

// 标签
<span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
  标签
</span>
```

---

## 八、响应式字体

### 8.1 移动端适配

```tsx
// 响应式标题
<h1 className="text-2xl md:text-3xl lg:text-4xl font-bold">
  响应式标题
</h1>

// 响应式正文
<p className="text-sm md:text-base leading-relaxed">
  响应式正文
</p>
```

### 8.2 断点字号

| 断点 | H1 | Body |
|------|-----|------|
| Mobile (<640px) | 24px | 14px |
| Tablet (640-1024px) | 30px | 16px |
| Desktop (>1024px) | 36px | 16px |

---

## 九、代码参考

### 9.1 Tailwind 配置

```js
// tailwind.config.js
module.exports = {
  theme: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'monospace'],
    },
    fontSize: {
      xs: ['12px', { lineHeight: '16px' }],
      sm: ['14px', { lineHeight: '20px' }],
      base: ['16px', { lineHeight: '24px' }],
      lg: ['18px', { lineHeight: '28px' }],
      xl: ['20px', { lineHeight: '28px' }],
      '2xl': ['24px', { lineHeight: '32px' }],
      '3xl': ['30px', { lineHeight: '36px' }],
      '4xl': ['36px', { lineHeight: '40px' }],
    },
  },
};
```

### 9.2 全局样式

```css
/* globals.css */
body {
  @apply font-sans text-base text-gray-900 antialiased;
}

h1, h2, h3, h4, h5, h6 {
  @apply font-semibold tracking-tight;
}
```

---

**END OF DOCUMENT**
