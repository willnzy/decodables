# 设计系统

> **说明**: 定义视觉规范，确保 UI 一致性

---

## 目录结构

```
03-design/
├── README.md          # 本文件
├── tokens.md          # 设计 Token（颜色/字体/间距）
├── components.md      # 组件规范
├── patterns.md        # 设计模式（响应式/布局）
└── brand.md           # 品牌规范
```

---

## 文档说明

| 文档 | 说明 | 来源 |
|------|------|------|
| `tokens.md` | 设计变量：颜色、字体、间距、阴影、圆角 | v2/02-standards/design-system.md |
| `components.md` | UI 组件规范：按钮、表单、卡片、模态框等 | v2/02-standards/design-system.md |
| `patterns.md` | 设计模式：响应式布局、导航模式、交互模式 | v2/02-standards/responsive-design-guide.md |
| `brand.md` | 品牌规范：Logo、色彩、语调 | 新建 |

---

## tokens.md 内容大纲

```markdown
## 颜色
- Primary: Emerald (#10B981)
- Secondary: Blue (#3B82F6)
- Accent: Violet (#7C3AED)
- Neutral: Gray scale
- Semantic: Success/Warning/Error/Info

## 字体
- Font Family: Inter
- Font Sizes: xs/sm/base/lg/xl/2xl/3xl
- Font Weights: normal/medium/semibold/bold

## 间距
- Spacing Scale: 0/1/2/3/4/5/6/8/10/12/16/20/24

## 阴影
- sm/md/lg/xl

## 圆角
- none/sm/md/lg/full
```

---

## components.md 内容大纲

```markdown
## 基础组件
- Button (variants: primary/secondary/ghost/destructive)
- Input / Textarea
- Select / Checkbox / Radio
- Badge / Tag

## 布局组件
- Card
- Dialog / Sheet
- Popover / Tooltip
- Tabs / Accordion

## 导航组件
- Navbar
- Sidebar
- BottomNavbar (移动端)
- Breadcrumb

## 反馈组件
- Toast
- Alert
- Skeleton
- Spinner
```

---

## patterns.md 内容大纲

```markdown
## 响应式设计
- 断点：sm(640)/md(768)/lg(1024)/xl(1280)
- Mobile-First 原则
- 触摸目标：最小 44px

## 布局模式
- 页面结构：Header/Main/Footer
- 侧边栏布局
- 卡片网格

## 交互模式
- 加载状态
- 空状态
- 错误状态
- 成功反馈
```

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `02-product/pages/` | 页面设计遵循设计系统 |
| `04-engineering/development/frontend.md` | 前端实现参考设计系统 |
