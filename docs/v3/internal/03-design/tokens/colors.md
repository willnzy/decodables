# 颜色系统

> **同步范围**: [frontend]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `tailwind.config.js`, 设计规范

---

## 一、概述

Make Decodables 使用基于 Tailwind CSS 的颜色系统，支持浅色和深色模式。

---

## 二、品牌色

### 2.1 主色 (Primary)

| 名称 | Hex | Tailwind | 用途 |
|------|-----|----------|------|
| Primary-50 | `#EEF2FF` | `primary-50` | 浅背景 |
| Primary-100 | `#E0E7FF` | `primary-100` | Hover 背景 |
| Primary-500 | `#6366F1` | `primary-500` | 主色调 |
| Primary-600 | `#4F46E5` | `primary-600` | 按钮 |
| Primary-700 | `#4338CA` | `primary-700` | 按钮 Hover |

### 2.2 强调色 (Accent)

| 名称 | Hex | Tailwind | 用途 |
|------|-----|----------|------|
| Violet | `#7C3AED` | `violet-500` | Pro Tier |
| Blue | `#3B82F6` | `blue-500` | Starter Tier |
| Emerald | `#10B981` | `emerald-500` | Free Tier |

---

## 三、语义色

### 3.1 状态色

| 语义 | Hex | Tailwind | 用途 |
|------|-----|----------|------|
| Success | `#22C55E` | `green-500` | 成功提示 |
| Warning | `#F59E0B` | `amber-500` | 警告提示 |
| Error | `#EF4444` | `red-500` | 错误提示 |
| Info | `#3B82F6` | `blue-500` | 信息提示 |

### 3.2 交互色

| 状态 | 说明 | 示例 |
|------|------|------|
| Default | 默认状态 | `bg-primary-600` |
| Hover | 悬停状态 | `hover:bg-primary-700` |
| Active | 激活状态 | `active:bg-primary-800` |
| Disabled | 禁用状态 | `bg-gray-300 cursor-not-allowed` |

---

## 四、中性色

### 4.1 灰度

| 名称 | Hex | Tailwind | 用途 |
|------|-----|----------|------|
| Gray-50 | `#F9FAFB` | `gray-50` | 页面背景 |
| Gray-100 | `#F3F4F6` | `gray-100` | 卡片背景 |
| Gray-200 | `#E5E7EB` | `gray-200` | 边框 |
| Gray-300 | `#D1D5DB` | `gray-300` | 禁用元素 |
| Gray-400 | `#9CA3AF` | `gray-400` | 占位文字 |
| Gray-500 | `#6B7280` | `gray-500` | 次要文字 |
| Gray-600 | `#4B5563` | `gray-600` | 正文文字 |
| Gray-700 | `#374151` | `gray-700` | 标题文字 |
| Gray-800 | `#1F2937` | `gray-800` | 强调文字 |
| Gray-900 | `#111827` | `gray-900` | 最深文字 |

---

## 五、Tier 主题色

| Tier | 颜色 | Tailwind | 用途 |
|------|------|----------|------|
| t1 (Free) | Emerald `#10B981` | `emerald-500` | 徽章、标签 |
| t2 (Starter) | Blue `#3B82F6` | `blue-500` | 徽章、标签 |
| t3 (Pro) | Violet `#7C3AED` | `violet-500` | 徽章、标签 |

```tsx
// Tier 颜色映射
const tierColors = {
  t1: "bg-emerald-100 text-emerald-700",
  t2: "bg-blue-100 text-blue-700",
  t3: "bg-violet-100 text-violet-700",
};
```

---

## 六、深色模式

### 6.1 背景色

| 用途 | 浅色 | 深色 |
|------|------|------|
| 页面背景 | `gray-50` | `gray-900` |
| 卡片背景 | `white` | `gray-800` |
| 输入框 | `white` | `gray-700` |

### 6.2 文字色

| 用途 | 浅色 | 深色 |
|------|------|------|
| 主要文字 | `gray-900` | `gray-100` |
| 次要文字 | `gray-500` | `gray-400` |
| 占位文字 | `gray-400` | `gray-500` |

### 6.3 使用方式

```tsx
// Tailwind 深色模式类名
<div className="bg-white dark:bg-gray-800">
  <p className="text-gray-900 dark:text-gray-100">
    内容
  </p>
</div>
```

---

## 七、代码参考

### 7.1 CSS 变量

```css
:root {
  --color-primary: #4F46E5;
  --color-primary-hover: #4338CA;
  --color-success: #22C55E;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
}

.dark {
  --color-primary: #818CF8;
  --color-primary-hover: #6366F1;
}
```

### 7.2 Tailwind 配置

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#EEF2FF',
          500: '#6366F1',
          600: '#4F46E5',
          700: '#4338CA',
        },
      },
    },
  },
};
```

---

## 八、使用指南

### 8.1 背景色选择

| 场景 | 推荐 |
|------|------|
| 页面背景 | `bg-gray-50` |
| 卡片 | `bg-white` |
| 输入框 | `bg-white border-gray-200` |
| 高亮区域 | `bg-primary-50` |

### 8.2 文字色选择

| 场景 | 推荐 |
|------|------|
| 标题 | `text-gray-900` |
| 正文 | `text-gray-600` |
| 次要信息 | `text-gray-500` |
| 链接 | `text-primary-600` |
| 错误提示 | `text-red-500` |

---

**END OF DOCUMENT**
