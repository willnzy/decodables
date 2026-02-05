# 产品规格

> **说明**: 定义产品做什么，功能边界和页面设计

---

## 目录结构

```
02-product/
├── README.md              # 本文件
├── features/              # 功能规格
│   ├── README.md          # 功能清单与优先级
│   ├── editor.md          # 编辑器功能
│   ├── dashboard.md       # Dashboard
│   ├── marketplace.md     # Marketplace
│   ├── billing.md         # 计费
│   ├── auth.md            # 认证
│   └── admin.md           # Admin 后台
│
└── pages/                 # 页面设计
    ├── user/              # 用户端页面
    └── admin/             # 管理端页面
```

---

## features/ 功能规格

| 文档 | 说明 | 来源 |
|------|------|------|
| `editor.md` | 编辑器功能：画布、元素、AI、导入导出 | v2/04-features/canvas-architecture.md |
| `dashboard.md` | Dashboard：项目管理、文件夹、工作空间 | v2/04-features/user-capabilities/workspace-system-design.md |
| `marketplace.md` | 模板市场：浏览、购买、出售 | v2/04-features/user-capabilities/marketplace-system-design.md |
| `billing.md` | 计费：订阅、积分、支付 | v2/04-features/user-capabilities/billing-system-design.md |
| `auth.md` | 认证：注册、登录、OAuth | v2/01-architecture/self-hosted-auth-design.md |
| `admin.md` | Admin：用户管理、内容管理、配置 | v2/04-features/admin-capabilities/ |

---

## pages/ 页面设计

### user/ 用户端页面

| 页面 | 说明 |
|------|------|
| landing.md | 首页 |
| sign-in.md | 登录页 |
| sign-up.md | 注册页 |
| dashboard.md | Dashboard 页 |
| editor.md | 编辑器页 |
| marketplace.md | 市场页 |
| profile.md | 个人中心 |
| settings.md | 设置页 |
| billing.md | 订阅管理 |

### admin/ 管理端页面

| 页面 | 说明 |
|------|------|
| overview.md | 概览 |
| users.md | 用户管理 |
| content.md | 内容管理 |
| config.md | 系统配置 |
| analytics.md | 数据分析 |

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `03-design/` | 功能规格的视觉实现 |
| `04-engineering/modules/` | 功能规格的技术实现 |
| `05-business/` | 功能背后的业务规则 |
| `public/manual/` | 功能规格转化为用户手册 |
