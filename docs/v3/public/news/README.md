# 产品动态 (News)

> **输出到**: 网站 /news 页面 + SEO + 社媒
> **来源**: 产品更新 + internal/06-growth/content-strategy.md

---

## 目录结构

```
news/
├── README.md              # 本文件
│
├── releases/              # 版本发布
│   └── _template.md       # 发布文章模板
│
├── tutorials/             # 教程文章（SEO）
│   └── _template.md       # 教程模板
│
├── use-cases/             # 使用案例（SEO）
│   └── _template.md       # 案例模板
│
└── announcements/         # 公告
    └── _template.md       # 公告模板
```

---

## 内容类型

| 类型 | 目录 | 用途 | 频率 |
|------|------|------|------|
| **releases** | `releases/` | 版本发布公告 | 每次发版 |
| **tutorials** | `tutorials/` | 教程文章，SEO 内容 | 每周 1-2 篇 |
| **use-cases** | `use-cases/` | 用户案例，SEO 内容 | 每月 2-4 篇 |
| **announcements** | `announcements/` | 重要公告 | 按需 |

---

## 写作规范

### 使用 News 模板

参考 [news-template.md](../internal/10-governance/templates/news-template.md)

### 文件命名

```
YYYY-MM-DD-slug.md

示例：
2026-02-05-v2-5-release-ai-generation.md
2026-02-01-how-to-create-first-decodable.md
```

### 元数据规范

```yaml
---
title: 文章标题
slug: url-slug
type: release | tutorial | use-case | announcement
status: draft | review | published
publish_date: YYYY-MM-DD
author: Make Decodables Team
reading_time: N min
featured_image: /images/news/xxx.jpg

# SEO
seo_title: SEO 标题（60字符内）
seo_description: SEO 描述（160字符内）
seo_keywords: [keyword1, keyword2]

# 社媒
social_ready: true
---
```

---

## SEO 要求

### 关键词策略

| 类型 | 目标关键词 |
|------|------------|
| 核心词 | decodable, decodable maker, create decodable |
| 长尾词 | how to make decodable, free decodable generator |
| 教育词 | phonics resources, reading instruction |

### 内容要求

- 标题包含主要关键词
- 内容 ≥ 800 字（教程）或 ≥ 500 字（案例）
- 包含 2-3 个内部链接
- 图片有 alt 文本

---

## 社媒要求

每篇文章需包含：

| 平台 | 字数限制 | 要求 |
|------|----------|------|
| Twitter | 280 字符 | 简洁有力 + emoji + CTA |
| Facebook | 150-300 字 | 详细一点 + CTA |
| LinkedIn | 200-400 字 | 专业语调 |

---

## 发布流程

1. **草稿** - 使用模板创建文章
2. **SEO 检查** - 确认关键词、元数据
3. **社媒文案** - 准备各平台文案
4. **审核** - 内容校对
5. **发布** - 更新状态为 published
6. **同步** - 发布到网站、社媒

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| `internal/06-growth/content-strategy.md` | 内容策略指导 |
| `manual/` | 教程可链接到 Manual |
