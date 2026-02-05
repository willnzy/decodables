# 内容 CMS 系统设计

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/articles.py`, `api/admin/static_pages.py`, `api/admin/asset_categories.py`

---

## 一、概述

### 1.1 核心能力

| 模块 | 说明 |
|------|------|
| Articles | 文章/博客/帮助中心 |
| Static Pages | 静态页面 (法律/公司) |
| Asset Categories | 素材分类树 |

---

## 二、Articles (文章系统)

### 2.1 API 端点

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/articles` | GET | 30/min | 文章列表 |
| `/api/v2/admin/articles/{id}` | GET | 30/min | 文章详情 |
| `/api/v2/admin/articles` | POST | 10/min | 创建文章 |
| `/api/v2/admin/articles/{id}` | PUT | 10/min | 更新文章 |
| `/api/v2/admin/articles/{id}` | DELETE | 10/min | 删除文章 |
| `/api/v2/admin/articles/{id}/publish` | POST | 10/min | 发布文章 |
| `/api/v2/admin/articles/{id}/unpublish` | POST | 10/min | 撤回文章 |

### 2.2 文章分类

```python
class ArticleCategory(str, Enum):
    MANUAL = "manual"            # 使用手册
    NEWS = "news"               # 新闻动态
    CHANGELOG = "changelog"     # 更新日志
    FAQ = "faq"                 # 常见问题
    TROUBLESHOOTING = "troubleshooting"  # 故障排除
```

### 2.3 数据结构

```python
class Article:
    id: UUID
    slug: str                    # URL 标识
    title: str
    summary: str                 # 摘要
    content: str                 # Markdown 内容
    
    # 分类与标签
    category: ArticleCategory
    tags: List[str]              # 最多 10 个
    
    # 状态
    is_published: bool
    published_at: Optional[datetime]
    
    # 展示
    cover_image: Optional[str]
    sort_order: int              # 排序权重 (越小越靠前)
    
    # SEO
    seo: ArticleSEO
    
    # 统计
    view_count: int
    
    # 时间
    created_at: datetime
    updated_at: datetime
    author_id: UUID

class ArticleSEO:
    meta_title: Optional[str]
    meta_description: Optional[str]
    og_image: Optional[str]
    canonical_url: Optional[str]
    noindex: bool = False
```

### 2.4 发布规则

```python
def validate_publish(article: Article) -> bool:
    """发布前校验"""
    errors = []
    
    if not article.title:
        errors.append("标题必填")
    if not article.slug:
        errors.append("slug 必填")
    if not article.content:
        errors.append("内容必填")
    
    if errors:
        raise ValidationError(errors)
    
    return True
```

### 2.5 URL 规则

```
news/changelog → /news/{slug}
其他分类 → /manual/{slug}
```

---

## 三、Static Pages (静态页面)

### 3.1 API 端点

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/static-pages` | GET | 30/min | 页面列表 |
| `/api/v2/admin/static-pages/{id}` | GET | 30/min | 页面详情 |
| `/api/v2/admin/static-pages` | POST | 10/min | 创建页面 |
| `/api/v2/admin/static-pages/{id}` | PUT | 10/min | 更新页面 |
| `/api/v2/admin/static-pages/{id}` | DELETE | 10/min | 删除页面 |
| `/api/v2/admin/static-pages/{id}/publish` | POST | 10/min | 发布页面 |
| `/api/v2/admin/static-pages/{id}/unpublish` | POST | 10/min | 撤回页面 |

### 3.2 页面类型

```python
class PageType(str, Enum):
    LEGAL = "legal"              # 法律文档 (隐私政策、服务条款)
    COMPANY = "company"          # 公司页面 (关于我们、联系方式)
    GUIDE = "guide"              # 指南
    OTHER = "other"              # 其他
```

### 3.3 数据结构

```python
class StaticPage:
    id: UUID
    slug: str                    # URL 标识
    title: str
    subtitle: Optional[str]
    content: str                 # Markdown 或 HTML
    
    # 类型
    page_type: PageType
    
    # 状态
    is_published: bool
    
    # 展示
    icon: Optional[str]          # 图标
    hero_gradient: Optional[str] # 顶部渐变色
    sort_order: int
    
    # SEO
    meta_title: Optional[str]
    meta_description: Optional[str]
    schema_data: Optional[dict]  # JSON-LD
    extra_data: Optional[dict]   # 扩展数据
    
    # 时间
    created_at: datetime
    updated_at: datetime
```

### 3.4 常见页面

| slug | 类型 | 说明 |
|------|------|------|
| `terms-of-service` | legal | 服务条款 |
| `privacy-policy` | legal | 隐私政策 |
| `about-us` | company | 关于我们 |
| `contact-us` | company | 联系我们 |

---

## 四、Asset Categories (素材分类)

### 4.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/asset-categories` | GET | 分类列表 |
| `/api/v2/admin/asset-categories/tree` | GET | 分类树 |
| `/api/v2/admin/asset-categories` | POST | 创建分类 |
| `/api/v2/admin/asset-categories/{slug}` | PATCH | 更新分类 |
| `/api/v2/admin/asset-categories/{slug}/move` | PUT | 移动分类 |
| `/api/v2/admin/asset-categories/{slug}` | DELETE | 删除分类 |
| `/api/v2/admin/asset-categories/{slug}/resources` | GET | 分类资源 |

### 4.2 数据结构

```python
class AssetCategory:
    id: UUID
    slug: str                    # 唯一标识
    name: str                    # 显示名称
    description: Optional[str]
    
    # 层级
    parent_id: Optional[UUID]
    path: str                    # ltree 路径
    level: int                   # 层级深度
    
    # 类型
    asset_type: str              # 素材类型
    min_tier: str                # 最低 Tier 要求
    
    # 展示
    is_visible: bool
    is_featured: bool
    display_order: int
    icon: Optional[str]
    thumbnail: Optional[str]
    
    # 统计
    resource_count: int
    
    created_at: datetime
    updated_at: datetime
```

### 4.3 树形结构

```python
class CategoryTree:
    """分类树节点"""
    category: AssetCategory
    children: List['CategoryTree']

# 返回示例
{
    "category": {"slug": "stickers", "name": "贴纸", ...},
    "children": [
        {
            "category": {"slug": "animals", "name": "动物", ...},
            "children": [
                {"category": {"slug": "cats", "name": "猫", ...}, "children": []},
                {"category": {"slug": "dogs", "name": "狗", ...}, "children": []}
            ]
        }
    ]
}
```

### 4.4 移动规则

```python
async def move_category(
    slug: str,
    new_parent_slug: Optional[str],
    new_order: int
):
    """
    移动分类
    
    规则:
    - 不能移动到自己的子节点下
    - 移动后更新所有子节点的 path
    - 更新同级节点的 display_order
    """
    category = await get_by_slug(slug)
    
    if new_parent_slug:
        new_parent = await get_by_slug(new_parent_slug)
        
        # 检查循环引用
        if new_parent.path.startswith(category.path):
            raise ValueError("不能移动到子节点下")
        
        new_path = f"{new_parent.path}.{slug}"
    else:
        new_path = slug
    
    # 更新路径
    await update_category_path(category.id, new_path)
    
    # 更新子节点路径
    await update_children_paths(category.id, category.path, new_path)
    
    # 更新排序
    await reorder_siblings(new_parent_slug, new_order)
```

### 4.5 删除规则

```python
async def delete_category(
    slug: str,
    cascade: bool = False
):
    """
    删除分类
    
    cascade=True: 级联删除子分类
    cascade=False: 有子分类时拒绝删除
    """
    category = await get_by_slug(slug)
    children = await get_children(category.id)
    
    if children and not cascade:
        raise ValueError("存在子分类，无法删除")
    
    if cascade:
        for child in children:
            await delete_category(child.slug, cascade=True)
    
    await delete_by_id(category.id)
```

---

## 五、前端交互

### 5.1 文章编辑器

```
┌─────────────────────────────────────────────────────┐
│  文章编辑                                           │
├─────────────────────────────────────────────────────┤
│  标题: [______________________________]             │
│  Slug: [______________________________]             │
│                                                     │
│  分类: [Manual ▼]  标签: [tag1] [tag2] [+添加]     │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │                                             │  │
│  │           Markdown 编辑器                   │  │
│  │                                             │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  [展开SEO设置]                                      │
│                                                     │
│       [保存草稿]    [预览]    [发布]               │
└─────────────────────────────────────────────────────┘
```

### 5.2 分类树管理

```
┌─────────────────────────────────────────────────────┐
│  素材分类                                           │
├─────────────────────────────────────────────────────┤
│  ▼ 贴纸 (stickers)                [编辑] [+子分类] │
│    ▼ 动物 (animals)                     [编辑]     │
│      ○ 猫 (cats)                        [编辑]     │
│      ○ 狗 (dogs)                        [编辑]     │
│    ▶ 人物 (characters)                  [编辑]     │
│  ▼ 背景 (backgrounds)                    [编辑]     │
│    ○ 纯色 (solid)                       [编辑]     │
│    ○ 渐变 (gradient)                    [编辑]     │
│                                                     │
│  支持拖拽排序和移动层级                             │
└─────────────────────────────────────────────────────┘
```

---

## 六、相关文档

- [Admin API 端点](../../api/admin-endpoints.md)
- [Marketplace 架构](../marketplace/architecture.md)
- [搜索模块](../search/architecture.md)

---

**END OF DOCUMENT**
