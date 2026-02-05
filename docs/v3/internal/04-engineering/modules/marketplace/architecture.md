# Marketplace 模块架构

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/marketplace/`, `app/(protected)/marketplace/`

---

## 一、模块概述

### 1.1 职责

Marketplace 模块负责素材和模板的浏览、搜索和管理。

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 素材浏览 | 按分类浏览素材 |
| 模板浏览 | 浏览系统模板 |
| 搜索 | 关键词搜索 |
| 收藏 | 收藏喜欢的内容 |
| 下载/使用 | 添加到项目 |

---

## 二、系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                   Marketplace Module                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Frontend                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │  │
│  │  │ Browse   │  │ Search   │  │ Favorites│           │  │
│  │  │ Page     │  │ Results  │  │ Page     │           │  │
│  │  └──────────┘  └──────────┘  └──────────┘           │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                      API                              │  │
│  │  /assets  /templates  /categories  /favorites        │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Domain                             │  │
│  │  AssetService  TemplateService  FavoriteService      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、后端架构

### 3.1 目录结构

```
domains/marketplace/
├── entities.py          # Asset, Template, Category 实体
├── repository.py        # 数据访问接口
├── service.py           # 业务逻辑服务
└── search_service.py    # 搜索服务

api/user/
├── assets.py            # 素材 API
├── templates.py         # 模板 API
└── categories.py        # 分类 API
```

### 3.2 核心实体

**Asset 实体**:

```python
@dataclass
class Asset:
    id: UUID
    name: str
    category_id: UUID
    thumbnail_url: str
    file_url: str
    file_type: str  # 'image' | 'svg' | 'audio'
    tags: List[str]
    tier_required: str  # 't1' | 't2' | 't3'
    usage_count: int
    created_at: datetime
```

**Category 实体**:

```python
@dataclass
class Category:
    id: UUID
    name: str
    slug: str
    parent_id: Optional[UUID]
    icon: str
    sort_order: int
```

### 3.3 服务层

```python
class MarketplaceService:
    # 素材
    async def list_assets(self, category_id, offset, limit) -> List[Asset]
    async def search_assets(self, query, filters) -> List[Asset]
    async def get_asset(self, asset_id) -> Asset
    
    # 模板
    async def list_templates(self, category_id, offset, limit) -> List[Template]
    async def get_template(self, template_id) -> Template
    
    # 分类
    async def list_categories(self) -> List[Category]
```

---

## 四、前端架构

### 4.1 目录结构

```
app/(protected)/marketplace/
├── page.tsx               # 主页面
├── assets/
│   ├── page.tsx           # 素材列表
│   └── [category]/page.tsx
├── templates/
│   ├── page.tsx           # 模板列表
│   └── [id]/page.tsx      # 模板详情
└── _components/
    ├── AssetGrid.tsx      # 素材网格
    ├── TemplateCard.tsx   # 模板卡片
    └── CategoryNav.tsx    # 分类导航
```

### 4.2 状态管理

```typescript
// stores/marketplace/marketplaceStore.ts
interface MarketplaceState {
  assets: Asset[];
  templates: Template[];
  categories: Category[];
  currentCategory: string | null;
  searchQuery: string;
  loading: boolean;
  
  // Actions
  fetchAssets: (categoryId?: string) => Promise<void>;
  searchAssets: (query: string) => Promise<void>;
  fetchTemplates: () => Promise<void>;
}
```

---

## 五、分类系统

### 5.1 素材分类 (10 类)

| ID | 名称 | 图标 |
|----|------|------|
| 1 | Characters | 👤 |
| 2 | Animals | 🐾 |
| 3 | Objects | 📦 |
| 4 | Backgrounds | 🖼️ |
| 5 | Shapes | ⬛ |
| 6 | Icons | 🔣 |
| 7 | Decorations | ✨ |
| 8 | Text Effects | 🔤 |
| 9 | Frames | 🖼️ |
| 10 | Audio | 🔊 |

### 5.2 模板分类

| 分类 | 说明 |
|------|------|
| Alphabet | 字母学习 |
| Numbers | 数字学习 |
| Colors | 颜色学习 |
| Shapes | 形状学习 |
| Animals | 动物主题 |
| Seasons | 季节主题 |

---

## 六、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/assets` | GET | 素材列表 |
| `/assets/{id}` | GET | 素材详情 |
| `/assets/search` | GET | 搜索素材 |
| `/templates` | GET | 模板列表 |
| `/templates/{id}` | GET | 模板详情 |
| `/categories` | GET | 分类列表 |

---

## 七、数据库设计

### 7.1 表结构

```sql
-- 素材表
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category_id UUID REFERENCES categories(id),
    thumbnail_url TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    tags TEXT[],
    tier_required VARCHAR(10) DEFAULT 't1',
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 分类表
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    parent_id UUID REFERENCES categories(id),
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0
);

-- 模板表
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_url TEXT NOT NULL,
    category VARCHAR(50),
    page_count INTEGER DEFAULT 8,
    data JSONB NOT NULL,
    tier_required VARCHAR(10) DEFAULT 't1',
    usage_count INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 7.2 索引

```sql
-- 素材搜索索引
CREATE INDEX idx_assets_category ON assets(category_id);
CREATE INDEX idx_assets_tags ON assets USING GIN(tags);
CREATE INDEX idx_assets_name_trgm ON assets USING GIN(name gin_trgm_ops);

-- 模板索引
CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_featured ON templates(is_featured) WHERE is_featured = TRUE;
```

---

## 八、搜索实现

### 8.1 全文搜索

```sql
-- 使用 pg_trgm 进行模糊匹配
SELECT * FROM assets
WHERE name % $1  -- 相似度匹配
   OR $1 = ANY(tags)  -- 标签匹配
ORDER BY similarity(name, $1) DESC
LIMIT 20;
```

### 8.2 搜索建议

```python
async def get_search_suggestions(query: str) -> List[str]:
    # 返回匹配的标签和名称
    return await repo.find_matching_terms(query, limit=5)
```

---

## 九、相关文档

- [Marketplace 功能规格](../../02-product/features/marketplace.md)
- [收藏功能规格](../../02-product/features/favorites.md)

---

**END OF DOCUMENT**
