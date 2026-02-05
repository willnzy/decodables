# 用户手册

> **输出到**: 网站 /manual 页面
> **来源**: internal/02-product/features/ + internal/05-business/

---

## 目录结构

```
manual/
├── README.md              # 本文件
│
├── getting-started/       # 快速入门
│   ├── what-is-decodables.md    # 产品介绍
│   ├── create-account.md        # 创建账号
│   ├── first-project.md         # 创建第一个项目
│   └── interface-overview.md    # 界面概览
│
├── editor/                # 编辑器使用
│   ├── canvas-basics.md         # 画布基础
│   ├── add-elements.md          # 添加元素
│   ├── text-editing.md          # 文字编辑
│   ├── image-editing.md         # 图片编辑
│   ├── drawing-tools.md         # 绘图工具
│   ├── ai-features.md           # AI 功能
│   ├── import-export.md         # 导入导出
│   └── keyboard-shortcuts.md    # 快捷键
│
├── dashboard/             # Dashboard 使用
│   ├── manage-projects.md       # 管理项目
│   ├── folders.md               # 文件夹
│   └── workspace.md             # 工作空间
│
├── marketplace/           # Marketplace 使用
│   ├── browse-templates.md      # 浏览模板
│   ├── purchase.md              # 购买
│   └── sell-your-work.md        # 出售作品
│
├── billing/               # 账单与订阅
│   ├── plans-pricing.md         # 套餐与定价
│   ├── manage-subscription.md   # 管理订阅
│   ├── credits.md               # 积分说明
│   └── invoices.md              # 发票
│
└── account/               # 账号管理
    ├── profile-settings.md      # 个人设置
    ├── security.md              # 安全设置
    └── notifications.md         # 通知设置
```

---

## 写作原则

### 面向用户

- 使用用户语言，避免技术术语
- 聚焦"如何做"，不解释"为什么这样设计"
- 提供清晰的操作步骤
- 配合截图说明

### 内容结构

每个文档应包含：

1. **简介** - 这个功能是什么
2. **操作步骤** - 如何使用（带截图）
3. **常见问题** - 链接到 FAQ
4. **相关内容** - 链接到其他 Manual

### 示例格式

```markdown
# 创建第一个项目

## 简介
在 Make Decodables 中，项目是你创作内容的容器...

## 操作步骤

### 1. 进入 Dashboard
登录后，你会看到 Dashboard 页面...

![Dashboard 截图](./images/dashboard.png)

### 2. 点击「新建项目」
在右上角找到「新建项目」按钮...

### 3. 选择模板或空白画布
你可以选择：
- **空白画布** - 从零开始创作
- **模板** - 使用预设模板快速开始

## 常见问题
- [如何删除项目？](/faq/editor#delete-project)
- [项目有数量限制吗？](/faq/billing#project-limit)

## 相关内容
- [画布基础](/manual/editor/canvas-basics)
- [添加元素](/manual/editor/add-elements)
```

---

## 内容转化来源

| Manual 文档 | 来源 |
|-------------|------|
| getting-started/ | 产品概述 + 用户流程 |
| editor/ | internal/02-product/features/editor.md |
| dashboard/ | internal/02-product/features/dashboard.md |
| marketplace/ | internal/02-product/features/marketplace.md |
| billing/ | internal/05-business/ |
| account/ | internal/02-product/features/auth.md |

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `faq/` | Manual 深度内容，FAQ 解答疑问 |
| `ai-knowledge-base/` | Manual 内容提取为 AI 知识 |
