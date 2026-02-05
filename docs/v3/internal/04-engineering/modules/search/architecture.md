# 搜索模块架构

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/user/search.py`, `domains/marketplace/`

---

## 一、模块概述

### 1.1 职责

搜索模块负责提供全站搜索能力，支持项目、模板和素材的搜索。

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 关键词搜索 | 按关键词匹配内容 |
| 模糊匹配 | 容错搜索 |
| 分类筛选 | 按类型/分类过滤 |
| 排序 | 相关度/时间/热度 |

---

## 二、系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Search Module                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Frontend                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │  │
│  │  │ Search   │  │ Results  │  │ Filters  │           │  │
│  │  │ Input    │  │ List     │  │ Panel    │           │  │
│  │  └──────────┘  └──────────┘  └──────────┘           │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                       API                             │  │
│  │  /search  /search/projects  /search/templates        │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  Search Service                       │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │  │
│  │  │ Query    │  │ Filter   │  │ Sort     │           │  │
│  │  │ Parser   │  │ Builder  │  │ Builder  │           │  │
│  │  └──────────┘  └──────────┘  └──────────┘           │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL                         │  │
│  │  pg_trgm (模糊匹配) + GIN 索引 (全文搜索)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、搜索范围

### 3.1 可搜索内容

| 内容类型 | 搜索字段 | 权重 |
|----------|----------|------|
| 项目 | name | 高 |
| 模板 | name, description, tags | 高/中/低 |
| 素材 | name, tags | 高/低 |

### 3.2 搜索结果

```python
@dataclass
class SearchResults:
    query: str
    total: int
    projects: SearchResultSection
    templates: SearchResultSection
    assets: SearchResultSection

@dataclass
class SearchResultSection:
    items: List[Any]
    total: int
```

---

## 四、搜索实现

### 4.1 PostgreSQL 扩展

```sql
-- 启用 pg_trgm 扩展 (模糊匹配)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 启用全文搜索
CREATE EXTENSION IF NOT EXISTS unaccent;
```

### 4.2 索引设计

```sql
-- 模板名称模糊搜索索引
CREATE INDEX idx_templates_name_trgm 
ON templates USING GIN (name gin_trgm_ops);

-- 模板标签搜索索引
CREATE INDEX idx_templates_tags 
ON templates USING GIN (tags);

-- 素材名称模糊搜索索引
CREATE INDEX idx_assets_name_trgm 
ON assets USING GIN (name gin_trgm_ops);

-- 素材标签搜索索引
CREATE INDEX idx_assets_tags 
ON assets USING GIN (tags);
```

### 4.3 搜索查询

```sql
-- 模糊匹配搜索
SELECT * FROM templates
WHERE name % $1  -- 相似度匹配
   OR $1 = ANY(tags)  -- 标签匹配
ORDER BY 
    CASE 
        WHEN name ILIKE $1 || '%' THEN 1  -- 前缀匹配优先
        WHEN name ILIKE '%' || $1 || '%' THEN 2  -- 包含匹配
        ELSE 3
    END,
    similarity(name, $1) DESC  -- 相似度排序
LIMIT $2 OFFSET $3;
```

---

## 五、服务层

### 5.1 搜索服务

```python
class SearchService:
    async def search_all(
        self, 
        query: str, 
        user_id: UUID,
        limit: int = 10
    ) -> SearchResults:
        """全局搜索"""
        projects = await self.search_projects(query, user_id, limit)
        templates = await self.search_templates(query, limit)
        assets = await self.search_assets(query, limit)
        
        return SearchResults(
            query=query,
            total=projects.total + templates.total + assets.total,
            projects=projects,
            templates=templates,
            assets=assets
        )
    
    async def search_templates(
        self,
        query: str,
        category: Optional[str] = None,
        sort: str = "relevance",
        limit: int = 20,
        offset: int = 0
    ) -> SearchResultSection:
        """搜索模板"""
        # 构建查询
        sql = """
            SELECT *, similarity(name, $1) as score
            FROM templates
            WHERE name % $1 OR $1 = ANY(tags)
        """
        
        if category:
            sql += f" AND category = '{category}'"
        
        if sort == "relevance":
            sql += " ORDER BY score DESC"
        elif sort == "newest":
            sql += " ORDER BY created_at DESC"
        elif sort == "popular":
            sql += " ORDER BY usage_count DESC"
        
        sql += f" LIMIT {limit} OFFSET {offset}"
        
        return await self.execute_search(sql, query)
```

### 5.2 查询解析

```python
class QueryParser:
    def parse(self, query: str) -> ParsedQuery:
        """解析搜索查询"""
        # 移除特殊字符
        clean_query = re.sub(r'[^\w\s]', '', query)
        
        # 分词
        terms = clean_query.lower().split()
        
        # 识别过滤器 (如 category:animals)
        filters = {}
        search_terms = []
        for term in terms:
            if ':' in term:
                key, value = term.split(':', 1)
                filters[key] = value
            else:
                search_terms.append(term)
        
        return ParsedQuery(
            terms=search_terms,
            filters=filters,
            original=query
        )
```

---

## 六、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/search` | GET | 全局搜索 |
| `/search/projects` | GET | 搜索项目 |
| `/search/templates` | GET | 搜索模板 |
| `/search/assets` | GET | 搜索素材 |
| `/search/suggestions` | GET | 搜索建议 |

### 6.1 请求参数

| 参数 | 类型 | 说明 |
|------|------|------|
| q | string | 搜索关键词 |
| type | string | 类型筛选 |
| category | string | 分类筛选 |
| sort | string | 排序方式 |
| limit | int | 每页数量 |
| offset | int | 偏移量 |

### 6.2 响应示例

```json
// GET /search?q=animal
{
  "query": "animal",
  "total": 156,
  "projects": {
    "items": [
      {"id": "...", "name": "My Animal Book", "thumbnail": "..."}
    ],
    "total": 3
  },
  "templates": {
    "items": [
      {"id": "...", "name": "Animal Alphabet", "thumbnail": "..."}
    ],
    "total": 45
  },
  "assets": {
    "items": [
      {"id": "...", "name": "Dog", "thumbnail": "..."}
    ],
    "total": 108
  }
}
```

---

## 七、搜索建议

### 7.1 实现方式

```python
async def get_suggestions(self, query: str, limit: int = 5) -> List[str]:
    """获取搜索建议"""
    # 从热门搜索词中匹配
    popular = await self.get_popular_searches(query, limit=3)
    
    # 从标签中匹配
    tags = await self.get_matching_tags(query, limit=3)
    
    # 合并去重
    suggestions = list(dict.fromkeys(popular + tags))[:limit]
    
    return suggestions
```

### 7.2 热门搜索

```sql
-- 记录搜索历史
CREATE TABLE search_history (
    id UUID PRIMARY KEY,
    query VARCHAR(200) NOT NULL,
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 热门搜索统计
SELECT query, COUNT(*) as count
FROM search_history
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY query
ORDER BY count DESC
LIMIT 10;
```

---

## 八、性能优化

### 8.1 缓存策略

| 缓存 | TTL | 说明 |
|------|-----|------|
| 热门搜索 | 1h | Redis 缓存 |
| 搜索建议 | 5min | 内存缓存 |
| 模板列表 | 10min | Redis 缓存 |

### 8.2 查询优化

- 使用 GIN 索引加速模糊搜索
- 限制返回字段减少数据传输
- 分页查询避免全表扫描

---

## 九、相关文档

- [搜索功能规格](../../02-product/features/search.md)
- [Marketplace 模块架构](../marketplace/architecture.md)

---

**END OF DOCUMENT**
