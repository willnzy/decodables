# 文章系统技术设计

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/articles-system-design.md

---

## 概述

文章/新闻系统的技术设计，支持产品公告、教程、案例等内容管理。

---

## 功能

### 内容管理
- 文章 CRUD
- 富文本编辑
- 图片上传
- SEO 设置

### 发布管理
- 草稿保存
- 定时发布
- 归档

### 分类管理
- 文章分类
- 标签系统

---

## 数据模型

```typescript
interface Article {
  id: string;
  slug: string;
  title: string;
  content: string; // Rich text
  excerpt: string;
  cover_image: string;
  category: string;
  tags: string[];
  status: 'draft' | 'published' | 'scheduled' | 'archived';
  published_at: Date;
  author_id: string;
  seo_title: string;
  seo_description: string;
  created_at: Date;
  updated_at: Date;
}
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/articles | 文章列表 |
| GET | /api/articles/:slug | 文章详情 |
| POST | /api/admin/articles | 创建文章 |
| PUT | /api/admin/articles/:id | 更新文章 |
| DELETE | /api/admin/articles/:id | 删除文章 |

---

## 相关文档

- [Admin 文章管理页面](../../../02-product/pages/admin/articles.md)
- [内容策略](../../../06-growth/acquisition/content-strategy.md)
