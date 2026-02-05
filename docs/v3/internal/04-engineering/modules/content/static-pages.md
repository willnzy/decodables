# 静态页面 CMS 技术设计

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/static-pages-cms-design.md

---

## 概述

静态页面内容管理系统，支持 About Us、Contact Us、法律页面等。

---

## 页面类型

| 页面 | 路径 | 说明 |
|------|------|------|
| About Us | /about-us | 关于我们 |
| Contact Us | /contact-us | 联系我们 |
| Privacy Policy | /privacy-policy | 隐私政策 |
| Terms of Service | /terms-of-service | 服务条款 |
| Billing Policy | /billing-policy | 计费政策 |
| Marketplace Guidelines | /marketplace-guidelines | 市场规范 |

---

## 内容管理方式

### 方案: Markdown + Git

```
docs/v3/public/legal/
├── privacy-policy.md
├── terms-of-service.md
└── billing-policy.md
```

- 内容存储在 Git 仓库
- 部署时自动更新
- 支持版本历史

---

## 数据模型

```typescript
interface StaticPage {
  slug: string;        // URL 路径
  title: string;       // 页面标题
  content: string;     // Markdown 内容
  seo_title: string;
  seo_description: string;
  last_updated: Date;
}
```

---

## 前端渲染

```typescript
// 使用 MDX 渲染
import { MDXRemote } from 'next-mdx-remote';

export default function StaticPage({ content }) {
  return <MDXRemote source={content} />;
}
```

---

## 相关文档

- [法律文档 (public)](../../../../public/legal/)
- [用户端页面](../../../02-product/pages/user/)
