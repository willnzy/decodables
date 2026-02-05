# 按钮组件

> **同步范围**: [frontend]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `components/ui/button.tsx`, Radix UI

---

## 一、概述

按钮是最常用的交互组件，基于 Radix UI 和 Tailwind CSS 实现。

---

## 二、按钮变体

### 2.1 变体列表

| 变体 | 用途 | 样式 |
|------|------|------|
| **default** | 主要操作 | 深色背景，白色文字 |
| **secondary** | 次要操作 | 浅色背景，深色文字 |
| **outline** | 轮廓按钮 | 透明背景，边框 |
| **ghost** | 幽灵按钮 | 透明背景，无边框 |
| **link** | 链接样式 | 无背景，下划线 |
| **destructive** | 危险操作 | 红色背景 |

### 2.2 视觉示例

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  [████ Default ████]  [ Secondary ]  [ Outline ]            │
│                                                             │
│  [ Ghost ]  [ Link ]  [████ Destructive ████]               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、按钮尺寸

| 尺寸 | 高度 | 内边距 | 字号 | Tailwind |
|------|------|--------|------|----------|
| sm | 32px | px-3 | 14px | `size="sm"` |
| default | 40px | px-4 | 14px | `size="default"` |
| lg | 48px | px-6 | 16px | `size="lg"` |
| icon | 40px | p-2 | - | `size="icon"` |

---

## 四、按钮状态

### 4.1 状态列表

| 状态 | 说明 | 样式变化 |
|------|------|----------|
| Default | 默认状态 | 基础样式 |
| Hover | 悬停状态 | 背景变深 |
| Active | 激活状态 | 背景更深 |
| Focus | 聚焦状态 | 显示焦点环 |
| Disabled | 禁用状态 | 降低透明度 |
| Loading | 加载状态 | 显示加载指示器 |

### 4.2 状态样式

```tsx
// Default 变体状态
const defaultStyles = {
  default: "bg-primary-600 text-white",
  hover: "hover:bg-primary-700",
  active: "active:bg-primary-800",
  focus: "focus-visible:ring-2 focus-visible:ring-primary-500",
  disabled: "disabled:opacity-50 disabled:cursor-not-allowed",
};
```

---

## 五、使用示例

### 5.1 基础用法

```tsx
import { Button } from "@/components/ui/button";

// 主按钮
<Button>Click me</Button>

// 次要按钮
<Button variant="secondary">Secondary</Button>

// 轮廓按钮
<Button variant="outline">Outline</Button>

// 危险按钮
<Button variant="destructive">Delete</Button>
```

### 5.2 尺寸变化

```tsx
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>
```

### 5.3 图标按钮

```tsx
import { Plus, Settings } from "lucide-react";

// 图标按钮
<Button size="icon">
  <Settings className="h-4 w-4" />
</Button>

// 图标 + 文字
<Button>
  <Plus className="h-4 w-4 mr-2" />
  Add New
</Button>
```

### 5.4 加载状态

```tsx
import { Loader2 } from "lucide-react";

<Button disabled>
  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
  Loading...
</Button>
```

### 5.5 链接按钮

```tsx
import Link from "next/link";

<Button asChild>
  <Link href="/dashboard">Go to Dashboard</Link>
</Button>
```

---

## 六、代码实现

### 6.1 Button 组件

```tsx
// components/ui/button.tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary-600 text-white hover:bg-primary-700",
        secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200",
        outline: "border border-gray-200 bg-white hover:bg-gray-100",
        ghost: "hover:bg-gray-100 hover:text-gray-900",
        link: "text-primary-600 underline-offset-4 hover:underline",
        destructive: "bg-red-500 text-white hover:bg-red-600",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-sm",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

---

## 七、使用指南

### 7.1 变体选择

| 场景 | 推荐变体 |
|------|----------|
| 主要操作 (保存、提交) | `default` |
| 次要操作 (取消) | `secondary` 或 `outline` |
| 工具栏按钮 | `ghost` |
| 导航链接 | `link` |
| 危险操作 (删除) | `destructive` |

### 7.2 尺寸选择

| 场景 | 推荐尺寸 |
|------|----------|
| 主要 CTA | `lg` |
| 表单提交 | `default` |
| 表格操作 | `sm` |
| 纯图标 | `icon` |

### 7.3 可访问性

- 始终提供可理解的按钮文字
- 图标按钮需要 `aria-label`
- 禁用状态要有视觉反馈
- 聚焦状态要有焦点环

```tsx
// 图标按钮可访问性
<Button size="icon" aria-label="Settings">
  <Settings className="h-4 w-4" />
</Button>
```

---

## 八、相关文档

- [颜色系统](../tokens/colors.md)
- [字体系统](../tokens/typography.md)

---

**END OF DOCUMENT**
