# Articles CMS 系统设计

> **状态**: ✅ 已实现
> **版本**: 2.1.0
> **最后更新**: 2026-01-16
> **关联计划**: Part D of Landing 页面优化计划

---

## 1. 概述

Articles CMS 系统用于管理网站的内容页面，包括：

| 分类 | 用途 | 前端路由 |
|------|------|----------|
| `manual` | 帮助文档、使用教程 | `/manual`, `/manual/[slug]` |
| `news` | 新闻公告、功能更新、活动通知 | `/news`, `/news/[slug]` |
| `changelog` | 更新日志、版本发布说明 | `/changelog` |
| `faq` | 常见问题 (Quick Answers) | `/manual` (FAQ 区块) |
| `troubleshooting` | 故障排除 (Common Issues) | `/manual` (Troubleshooting 区块) |

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
    category VARCHAR(50) NOT NULL CHECK (category IN ('manual', 'news', 'changelog', 'faq', 'troubleshooting')),
    tags JSONB DEFAULT '[]'::jsonb,        -- 标签数组
    cover_image VARCHAR(500),              -- 封面图 URL
    is_featured BOOLEAN DEFAULT false,     -- 是否精选 (v1.1.0 新增)
    is_published BOOLEAN DEFAULT false,    -- 发布状态
    published_at TIMESTAMPTZ,              -- 发布时间
    author_id UUID REFERENCES profiles(id), -- 作者 user_id
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
| `category` | VARCHAR(50) | ✅ | 分类: manual/news/changelog/faq/troubleshooting |
| `tags` | JSONB | - | 标签数组，如 `["images", "tutorial"]` |
| `cover_image` | VARCHAR(500) | - | 封面图 URL |
| `is_featured` | BOOLEAN | 自动 | 是否精选 (默认 false, v1.1.0 新增) |
| `is_published` | BOOLEAN | 自动 | 是否已发布 (默认 false) |
| `published_at` | TIMESTAMPTZ | - | 发布时间 (发布时自动设置) |
| `author_id` | UUID | - | 作者的 user_id |
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
    MANUAL = "manual"               # 帮助文档
    NEWS = "news"                   # 新闻公告
    CHANGELOG = "changelog"         # 更新日志
    FAQ = "faq"                     # 常见问题 (v2.0)
    TROUBLESHOOTING = "troubleshooting"  # 故障排除 (v2.0)

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

### 5.0 架构决策: Server-First (v2.0)

**核心原则**: 所有 SEO 关键内容在 Server Component 中获取数据，通过 props 传递给 Client Component。

```
┌─────────────────────────────────────────────────────────────┐
│  Server Component (page.tsx)                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  await articlesServerService.getFaqArticlesServer()   │  │
│  │  await articlesServerService.getArticleBySlugServer() │  │
│  └───────────────────────────────────────────────────────┘  │
│                         ↓ props                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Client Component (accordion, interactions)           │  │
│  │  - 接收 articles 数据作为 props                        │  │
│  │  - 只处理用户交互 (展开/折叠/搜索)                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**服务分工**:

| 服务 | 用途 | 使用场景 |
|------|------|----------|
| `articlesServerService.ts` | **PRIMARY** - 服务端数据获取 | Server Components, ISR 页面 |
| `articlesService.ts` | Types + 认证相关 API | Admin 页面, 需要认证的操作 |
| `useArticles.ts` hooks | Client-side 数据获取 | 动态交互场景 (搜索, 分页) |

**ISR 配置**:
- `revalidate = 3600` (1 小时缓存)
- `generateStaticParams()` 预渲染所有详情页

### 5.1 页面路由

```
app/
├── manual/
│   ├── page.tsx              # 帮助文档列表 + FAQ + Troubleshooting
│   └── [slug]/
│       └── page.tsx          # 文档详情
├── news/
│   ├── page.tsx              # 新闻列表
│   └── [slug]/
│       └── page.tsx          # 新闻详情
└── changelog/
    └── page.tsx              # 更新日志 (单页展示所有)
```

### 5.2 Server-Side 数据获取 (推荐)

```typescript
// services/articlesServerService.ts (v2.0)
// PRIMARY - 用于所有 SEO 关键页面

// 获取文章列表
export async function getArticlesServer(params: ListArticlesParams): Promise<ArticleListResponse | null>

// 获取单篇文章
export async function getArticleBySlugServer(slug: string): Promise<Article | null>

// 获取精选文章
export async function getFeaturedArticlesServer(category?: ArticleCategory, limit?: number): Promise<ArticleListItem[]>

// 获取相关文章
export async function getRelatedArticlesServer(slug: string, limit?: number): Promise<ArticleListItem[]>

// 分类快捷方法
export async function getManualArticlesServer(params?): Promise<ArticleListResponse | null>
export async function getNewsArticlesServer(params?): Promise<ArticleListResponse | null>
export async function getFaqArticlesServer(params?): Promise<ArticleListItem[]>           // v2.0 新增
export async function getTroubleshootingArticlesServer(params?): Promise<ArticleListItem[]> // v2.0 新增
export async function getChangelogArticlesServer(params?): Promise<ArticleListResponse | null>

// 用于 generateStaticParams
export async function getAllArticleSlugsServer(category?: ArticleCategory): Promise<string[]>
```

**使用示例 (Server Component)**:

```tsx
// app/manual/page.tsx
import {
  getManualArticlesServer,
  getFaqArticlesServer,
  getTroubleshootingArticlesServer
} from '@/services/articlesServerService';

export default async function ManualPage() {
  // 并行获取所有数据
  const [articles, faqArticles, troubleshootingArticles] = await Promise.all([
    getManualArticlesServer({ limit: 50 }),
    getFaqArticlesServer({ limit: 20 }),
    getTroubleshootingArticlesServer({ limit: 20 }),
  ]);

  return (
    <>
      <ArticleList articles={articles?.items ?? []} />
      <FAQSection articles={faqArticles} />           {/* 数据通过 props 传递 */}
      <TroubleshootingSection articles={troubleshootingArticles} />
    </>
  );
}
```

### 5.3 Client-Side Hooks (仅限交互场景)

```typescript
// hooks/useArticles.ts (v2.0)
// 仅用于需要客户端数据获取的场景

// ✅ 保留的 hooks (用于搜索、分页等动态交互)
export function useArticleList(params?)    // 带分页的文章列表
export function useArticle(slug)           // 单篇文章
export function useFeaturedArticles()      // 精选文章
export function useArticleSearch(query)    // 搜索
export function useChangelogArticles()     // 更新日志

// ❌ 已移除的 hooks (使用 Server-Side 替代)
// - useFaqArticles → getFaqArticlesServer()
// - useTroubleshootingArticles → getTroubleshootingArticlesServer()
// - useNewsArticles → getNewsArticlesServer()
// - useManualArticles → getManualArticlesServer()
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

### 6.0 实现状态 (Phase 8)

**已实现组件**:
```
components/admin/
├── ArticlesPanel.tsx          # 主面板组件 (478 行)
└── index.js                   # 导出文件 (已更新)

services/
└── adminService.ts            # 新增 Articles API 函数
    ├── adminListArticles()
    ├── adminGetArticle()
    ├── adminCreateArticle()
    ├── adminUpdateArticle()
    ├── adminDeleteArticle()
    ├── adminPublishArticle()
    └── adminUnpublishArticle()
```

**功能特性**:
- ✅ 文章列表 (分类筛选 + 搜索 + 分页)
- ✅ 创建/编辑文章 (Markdown 编辑器)
- ✅ 发布/取消发布
- ✅ 删除 (带确认对话框)
- ✅ 分类 Tab: All / Manual / FAQ / Troubleshooting / News / Changelog

**详细文档**: [PED-Articles.md](../../tmp/refactor/3-Pages/Admin/PED-Articles.md)

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
| 联系邮箱 | Config (`CONTACT_EMAIL`) | "info@foliaz.com" |
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
    url: `https://foliaz.com/${article.category}/${article.slug}`,
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
| Public API | ✅ 完成 | 6 个端点 |
| Admin API | ✅ 完成 | 7 个端点 |
| 前端 - Manual | ✅ 完成 | Server Component + ISR + FAQ/Troubleshooting 区块 |
| 前端 - News | ✅ 完成 | Server Component + ISR |
| 前端 - Changelog | 🔲 待开发 | changelog 页面 |
| Admin UI | ✅ 完成 | ArticlesPanel (Phase 8) |
| SEO 优化 | ✅ 完成 | Meta tags, Schema.org, ISR |

---

## 10. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-01-11 | 初始版本 |
| 1.1.0 | 2026-01-12 | 新增 `is_featured` 字段和索引；新增 `GET /articles/featured` API 端点；支持精选文章功能 (Manual/News Featured 区块) |
| 1.2.0 | 2026-01-13 | 新增 `GET /articles/{slug}/related` 端点；修正响应数据结构 (`articles` → `items`)；修复 DateTime 解析错误 (Supabase ISO 字符串处理) |
| **2.0.0** | **2026-01-15** | **Server-First 架构重构**；新增 `faq` 和 `troubleshooting` 分类；`articlesServerService.ts` 升级为 v2.0 (PRIMARY 数据源)；重构 FAQAccordion 为 Server/Client 组件；清理废弃 hooks (useFaqArticles, useTroubleshootingArticles 等) |
| **2.1.0** | **2026-01-16** | **Phase 8**: Admin Articles CMS 完成；新增 `ArticlesPanel.tsx` (478 行)；集成 Admin API (7 个端点)；支持 CRUD + 发布/取消发布 |

---

**文档版本**: 2.1.0
**最后更新**: 2026-01-16
**相关文档**:
- [user-api-review.md](user-api-review.md) - User API 完整参考
- [admin-api-review.md](admin-api-review.md) - Admin API 完整参考
- [pricing-system-design.md](pricing-system-design.md) - Config 系统扩展 (CMS-Lite)
