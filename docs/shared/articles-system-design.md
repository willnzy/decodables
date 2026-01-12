# Articles CMS 系统设计

> **状态**: ✅ 已实现
> **版本**: 1.2.0
> **最后更新**: 2026-01-13
> **关联计划**: Part D of Landing 页面优化计划

---

## 1. 概述

Articles CMS 系统用于管理网站的内容页面，包括：

| 分类 | 用途 | 前端路由 |
|------|------|----------|
| `manual` | 帮助文档、FAQ、使用教程 | `/manual`, `/manual/[slug]` |
| `news` | 新闻公告、功能更新、活动通知 | `/news`, `/news/[slug]` |
| `changelog` | 更新日志、版本发布说明 | `/changelog` |

**为什么不用 Config 系统?**

| 特征 | Config 系统 | Articles 系统 |
|------|------------|--------------|
| 数据量 | 有限 (几百条) | 无限增长 |
| 结构 | Key-Value | 完整文章 (标题、内容、分类) |
| 操作 | CRUD 单条 | 列表、搜索、分页、分类筛选 |
| 内容 | 短文本/JSON | 长富文本 (Markdown) |

---

## 2. 数据库设计

### 2.1 articles 表

```sql
-- 位置: migrations/v2/02_platform_services.sql
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(200) UNIQUE NOT NULL,     -- URL 友好标识
    title VARCHAR(500) NOT NULL,           -- 文章标题
    summary TEXT,                           -- 摘要 (用于列表展示)
    content TEXT NOT NULL,                  -- Markdown 内容
    category VARCHAR(50) NOT NULL CHECK (category IN ('manual', 'news', 'changelog')),
    tags JSONB DEFAULT '[]'::jsonb,        -- 标签数组
    cover_image VARCHAR(500),              -- 封面图 URL
    is_featured BOOLEAN DEFAULT false,     -- 是否精选 (v1.1.0 新增)
    is_published BOOLEAN DEFAULT false,    -- 发布状态
    published_at TIMESTAMPTZ,              -- 发布时间
    author_id TEXT REFERENCES profiles(id), -- 作者 (Clerk user_id)
    sort_order INTEGER DEFAULT 0,          -- 排序权重 (越小越靠前)
    view_count INTEGER DEFAULT 0,          -- 阅读量
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_articles_published ON articles(is_published, published_at DESC);
CREATE INDEX idx_articles_featured ON articles(is_featured, published_at DESC) WHERE is_featured = true;  -- v1.1.0 新增
CREATE INDEX idx_articles_slug ON articles(slug);
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | UUID | 自动 | 主键 |
| `slug` | VARCHAR(200) | ✅ | URL 友好标识，如 `how-to-add-images` |
| `title` | VARCHAR(500) | ✅ | 文章标题 |
| `summary` | TEXT | - | 摘要，用于列表卡片展示 |
| `content` | TEXT | ✅ | Markdown 格式的正文内容 |
| `category` | VARCHAR(50) | ✅ | 分类: manual/news/changelog |
| `tags` | JSONB | - | 标签数组，如 `["images", "tutorial"]` |
| `cover_image` | VARCHAR(500) | - | 封面图 URL |
| `is_featured` | BOOLEAN | 自动 | 是否精选 (默认 false, v1.1.0 新增) |
| `is_published` | BOOLEAN | 自动 | 是否已发布 (默认 false) |
| `published_at` | TIMESTAMPTZ | - | 发布时间 (发布时自动设置) |
| `author_id` | TEXT | - | 作者的 Clerk user_id |
| `sort_order` | INTEGER | 自动 | 排序权重 (默认 0) |
| `view_count` | INTEGER | 自动 | 阅读量 (默认 0) |

---

## 3. 后端架构

### 3.1 目录结构

```
decodables/
├── domains/articles/
│   ├── __init__.py           # 模块导出
│   ├── entities.py           # Article, ArticleSummary, ArticleCategory
│   ├── repository.py         # ArticleRepository 抽象接口
│   └── service.py            # ArticleService 业务逻辑
├── infrastructure/repositories/
│   └── article_repository.py # SupabaseArticleRepository 实现
└── api/
    ├── user/articles.py      # Public API (4 个端点)
    └── admin/articles.py     # Admin API (7 个端点)
```

### 3.2 实体定义

```python
# domains/articles/entities.py

class ArticleCategory(str, Enum):
    MANUAL = "manual"       # 帮助文档
    NEWS = "news"           # 新闻公告
    CHANGELOG = "changelog" # 更新日志

@dataclass
class Article:
    id: UUID
    slug: str
    title: str
    content: str  # Markdown
    category: ArticleCategory
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    cover_image: Optional[str] = None
    is_featured: bool = False  # v1.1.0 新增
    is_published: bool = False
    published_at: Optional[datetime] = None
    author_id: Optional[str] = None
    sort_order: int = 0
    view_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class ArticleSummary:
    """轻量级文章表示，用于列表展示 (不含 content)"""
    id: UUID
    slug: str
    title: str
    summary: Optional[str]
    category: ArticleCategory
    tags: List[str]
    cover_image: Optional[str]
    is_featured: bool  # v1.1.0 新增
    is_published: bool
    published_at: Optional[datetime]
    view_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
```

### 3.3 Service 层方法

```python
# domains/articles/service.py

class ArticleService:
    # 公开 API (仅返回已发布文章)
    async def get_article(slug: str) -> Optional[Article]
    async def list_articles(category?, offset, limit) -> List[ArticleSummary]
    async def get_article_count(category?) -> int
    async def get_categories() -> List[dict]
    async def search_articles(query, category?, offset, limit) -> List[ArticleSummary]

    # 管理 API (含草稿)
    async def admin_get_article(article_id: UUID) -> Optional[Article]
    async def admin_list_articles(category?, include_drafts, offset, limit) -> List[ArticleSummary]
    async def admin_get_count(category?, published_only) -> int

    # 写操作
    async def create_article(...) -> Article
    async def update_article(article_id, ...) -> Optional[Article]
    async def publish_article(article_id) -> Optional[Article]
    async def unpublish_article(article_id) -> Optional[Article]
    async def delete_article(article_id) -> bool
```

---

## 4. API 端点

### 4.1 Public API (用户端)

| 方法 | 路径 | 说明 | 限流 |
|------|------|------|------|
| GET | `/api/v2/user/articles` | 列出已发布文章 | 60/min |
| GET | `/api/v2/user/articles/featured` | 获取精选文章 (v1.1.0) | 60/min |
| GET | `/api/v2/user/articles/categories` | 获取分类及文章数 | 60/min |
| GET | `/api/v2/user/articles/search` | 搜索文章 | 30/min |
| GET | `/api/v2/user/articles/{slug}` | 获取文章详情 | 60/min |
| GET | `/api/v2/user/articles/{slug}/related` | 获取相关文章 (v1.2.0) | 60/min |

#### GET `/articles`

列出已发布文章 (分页)。

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `category` | string | - | 筛选分类 (manual/news/changelog) |
| `offset` | int | 0 | 分页偏移 |
| `limit` | int | 20 | 每页数量 (max 100) |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "how-to-add-images",
      "title": "How to Add Images",
      "summary": "Learn how to upload images...",
      "category": "manual",
      "tags": ["images", "tutorial"],
      "cover_image": "https://...",
      "is_featured": false,
      "published_at": "2026-01-11T10:00:00Z",
      "view_count": 125
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20
}
```

#### GET `/articles/featured` (v1.1.0 新增)

获取精选文章列表。

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `category` | string | - | 筛选分类 (manual/news/changelog) |
| `limit` | int | 3 | 最大数量 (max 10) |

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "new-ai-feature",
      "title": "New Feature: AI Design Assistant",
      "summary": "Introducing our new AI-powered...",
      "category": "news",
      "tags": ["feature", "update"],
      "cover_image": "https://...",
      "is_featured": true,
      "published_at": "2026-01-12T10:00:00Z",
      "view_count": 250
    }
  ],
  "total": 3,
  "offset": 0,
  "limit": 4
}
```

#### GET `/articles/categories`

获取所有分类及已发布文章数。

**响应**:
```json
{
  "categories": [
    {
      "category": "manual",
      "display_name": "Help & Documentation",
      "count": 15
    },
    {
      "category": "news",
      "display_name": "News & Announcements",
      "count": 8
    },
    {
      "category": "changelog",
      "display_name": "Changelog",
      "count": 12
    }
  ]
}
```

#### GET `/articles/search`

搜索已发布文章 (标题、内容、摘要)。

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `q` | string | **必填** | 搜索关键词 (2-100 字符) |
| `category` | string | - | 筛选分类 |
| `offset` | int | 0 | 分页偏移 |
| `limit` | int | 20 | 每页数量 |

**响应**: 同 GET `/articles`

#### GET `/articles/{slug}`

获取单篇已发布文章详情。自动增加阅读量。

**响应**:
```json
{
  "id": "uuid",
  "slug": "how-to-add-images",
  "title": "How to Add Images",
  "content": "# How to Add Images\n\n...",
  "summary": "Learn how to upload images...",
  "category": "manual",
  "tags": ["images", "tutorial"],
  "cover_image": "https://...",
  "published_at": "2026-01-11T10:00:00Z",
  "view_count": 126,
  "created_at": "2026-01-10T08:00:00Z",
  "updated_at": "2026-01-11T10:00:00Z"
}
```

#### GET `/articles/{slug}/related` (v1.2.0 新增)

获取与指定文章相关的其他文章。返回同类别的已发布文章（排除当前文章）。

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 3 | 最大数量 (max 10) |

**响应**:
```json
[
  {
    "id": "uuid",
    "slug": "working-with-text",
    "title": "Working with Text in Your Project",
    "summary": "Learn how to add and format text...",
    "category": "manual",
    "tags": ["text", "tutorial"],
    "cover_image": "https://...",
    "published_at": "2026-01-10T10:00:00Z",
    "view_count": 98
  },
  {
    "id": "uuid",
    "slug": "advanced-editing-tips",
    "title": "Advanced Editing Tips",
    "summary": "Master advanced editing techniques...",
    "category": "manual",
    "tags": ["advanced", "tips"],
    "cover_image": "https://...",
    "published_at": "2026-01-09T10:00:00Z",
    "view_count": 156
  }
]
```

### 4.2 Admin API (管理端)

| 方法 | 路径 | 说明 | 限流 |
|------|------|------|------|
| GET | `/api/v2/admin/articles` | 列出所有文章 (含草稿) | 30/min |
| GET | `/api/v2/admin/articles/{id}` | 获取文章 (by ID) | 30/min |
| POST | `/api/v2/admin/articles` | 创建文章 | 10/min |
| PUT | `/api/v2/admin/articles/{id}` | 更新文章 | 10/min |
| DELETE | `/api/v2/admin/articles/{id}` | 删除文章 | 10/min |
| POST | `/api/v2/admin/articles/{id}/publish` | 发布文章 | 10/min |
| POST | `/api/v2/admin/articles/{id}/unpublish` | 取消发布 | 10/min |

#### POST `/articles` (创建)

**请求体**:
```json
{
  "title": "How to Add Images",
  "content": "# How to Add Images\n\n...",
  "category": "manual",
  "slug": "how-to-add-images",  // 可选，自动生成
  "summary": "Learn how to upload images",
  "tags": ["images", "tutorial"],
  "cover_image": "https://...",
  "is_published": false,  // 默认草稿
  "sort_order": 0
}
```

**响应**:
```json
{
  "success": true,
  "message": "Article created successfully",
  "article": { ... }
}
```

#### PUT `/articles/{id}` (更新)

**请求体** (所有字段可选):
```json
{
  "title": "Updated Title",
  "content": "...",
  "summary": "...",
  "tags": ["updated", "tags"]
}
```

#### POST `/articles/{id}/publish`

发布文章，自动设置 `is_published=true` 和 `published_at=now()`。

#### POST `/articles/{id}/unpublish`

取消发布 (设为草稿)，清除 `published_at`。

---

## 5. 前端集成

### 5.1 页面路由

```
app/
├── manual/
│   ├── page.tsx              # 帮助文档列表
│   └── [slug]/
│       └── page.tsx          # 文档详情
├── news/
│   ├── page.tsx              # 新闻列表
│   └── [slug]/
│       └── page.tsx          # 新闻详情
└── changelog/
    └── page.tsx              # 更新日志 (单页展示所有)
```

### 5.2 API 调用示例

```typescript
// hooks/useArticles.ts

// 获取文章列表
export async function fetchArticles(category?: string, offset = 0, limit = 20) {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (category) params.set('category', category);

  const res = await fetch(`/api/v2/user/articles?${params}`);
  return res.json();
}

// 获取单篇文章
export async function fetchArticle(slug: string) {
  const res = await fetch(`/api/v2/user/articles/${slug}`);
  if (!res.ok) throw new Error('Article not found');
  return res.json();
}

// 获取分类
export async function fetchCategories() {
  const res = await fetch('/api/v2/user/articles/categories');
  return res.json();
}

// 搜索
export async function searchArticles(query: string, category?: string) {
  const params = new URLSearchParams({ q: query });
  if (category) params.set('category', category);

  const res = await fetch(`/api/v2/user/articles/search?${params}`);
  return res.json();
}
```

### 5.3 Markdown 渲染

使用 `react-markdown` + `remark-gfm`:

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function ArticleContent({ content }: { content: string }) {
  return (
    <article className="prose prose-slate max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-3xl font-bold mb-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-2xl font-semibold mt-8 mb-4">{children}</h2>,
          p: ({ children }) => <p className="mb-4 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-6 mb-4">{children}</ul>,
          code: ({ children }) => <code className="bg-slate-100 px-1.5 py-0.5 rounded">{children}</code>,
        }}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
```

---

## 6. Admin 界面设计

### 6.1 文章列表

```
┌─────────────────────────────────────────────────────────────────┐
│ Articles                                         [+ New Article]│
├─────────────────────────────────────────────────────────────────┤
│ Category: [All ▼]  Status: [All ▼]  Search: [____________]     │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📄 How to add images to your project                        │ │
│ │ manual  |  ✅ Published  |  Views: 125  |  Updated: Jan 10  │ │
│ │                                        [Edit] [Unpublish]   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📰 New Feature: AI Design Pages                             │ │
│ │ news  |  📝 Draft  |  Views: 0  |  Updated: Jan 09          │ │
│ │                                        [Edit] [Publish]     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 文章编辑器

```
┌─────────────────────────────────────────────────────────────────┐
│ Edit Article                                    [Save] [Preview]│
├─────────────────────────────────────────────────────────────────┤
│ Title: [How to add images to your project                    ] │
│ Slug:  [how-to-add-images              ] (auto-generated)      │
│ Category: [manual ▼]     Tags: [images] [editor] [+ Add]       │
│ Summary: [Learn how to upload and manage images in editor    ] │
├─────────────────────────────────────────────────────────────────┤
│ Content (Markdown):                    [Bold] [Italic] [Link]  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ # How to Add Images                                         │ │
│ │                                                             │ │
│ │ You can add images to your project in several ways:        │ │
│ │                                                             │ │
│ │ ## Method 1: Upload from Computer                          │ │
│ │ 1. Click the "Add Image" button in the toolbar             │ │
│ │ 2. Select a file from your computer                        │ │
│ │ 3. Wait for the upload to complete                         │ │
│ │                                                             │ │
│ │ ## Method 2: Use AI Generation                             │ │
│ │ ...                                                         │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ Status: [□ Published]   Sort Order: [0]                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 与 Config 系统的配合

Articles 系统处理**长内容** (文章、文档)，而 Config 系统处理**短配置** (页面文案、联系方式)。

| 内容类型 | 使用系统 | 示例 |
|----------|----------|------|
| 帮助文档 | Articles (`manual`) | "How to Add Images" |
| 新闻公告 | Articles (`news`) | "New Feature: AI Design" |
| 更新日志 | Articles (`changelog`) | "v2.0.0 Release Notes" |
| Landing 页面标题 | Config (`LANDING_HERO_TITLE`) | "Create Beautiful 8-Page Zines" |
| 联系邮箱 | Config (`CONTACT_EMAIL`) | "info@makedecodables.com" |
| 价格信息 | Config (`PRICING_*`) | 功能列表、价格档位 |

---

## 8. SEO 优化 (可选)

### 8.1 动态 Meta Tags

```tsx
// app/manual/[slug]/page.tsx
export async function generateMetadata({ params }) {
  const article = await fetchArticle(params.slug);
  return {
    title: `${article.title} | Make Decodables`,
    description: article.summary,
    openGraph: {
      title: article.title,
      description: article.summary,
      images: article.cover_image ? [article.cover_image] : [],
    },
  };
}
```

### 8.2 Sitemap 生成

```tsx
// app/sitemap.ts
export default async function sitemap() {
  const articles = await fetchAllArticles();
  return articles.map(article => ({
    url: `https://makedecodables.com/${article.category}/${article.slug}`,
    lastModified: article.updated_at,
  }));
}
```

---

## 9. 实施状态

| 阶段 | 状态 | 内容 |
|------|------|------|
| 数据库 | ✅ 完成 | articles 表 + 索引 |
| Domain 层 | ✅ 完成 | entities, repository, service |
| Infrastructure | ✅ 完成 | SupabaseArticleRepository |
| Public API | ✅ 完成 | 4 个端点 |
| Admin API | ✅ 完成 | 7 个端点 |
| 前端页面 | 🔲 待开发 | manual, news, changelog |
| Admin UI | 🔲 待开发 | ArticlesManagementPanel |
| SEO 优化 | 🔲 可选 | Meta tags, sitemap |

---

## 10. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-01-11 | 初始版本 |
| 1.1.0 | 2026-01-12 | 新增 `is_featured` 字段和索引；新增 `GET /articles/featured` API 端点；支持精选文章功能 (Manual/News Featured 区块) |
| **1.2.0** | **2026-01-13** | **新增 `GET /articles/{slug}/related` 端点**；修正响应数据结构 (`articles` → `items`)；修复 DateTime 解析错误 (Supabase ISO 字符串处理) |

---

**文档版本**: 1.2.0
**最后更新**: 2026-01-13
**相关文档**:
- [user-api-review.md](user-api-review.md) - User API 完整参考
- [admin-api-review.md](admin-api-review.md) - Admin API 完整参考
- [pricing-system-design.md](pricing-system-design.md) - Config 系统扩展 (CMS-Lite)
