# Theme System - 主题系统

> Daily Doodle 与主题展示系统设计

**验证状态**: 🟡 待验证  
**同步范围**: [fullstack]  
**代码来源**: `domains/themes/`, `api/user/themes.py`

---

## 一、概述

主题系统提供 Daily Doodle（每日涂鸦）和分类主题浏览功能，帮助用户发现灵感和创意模板。

---

## 二、核心概念

### 2.1 Daily Doodle

每日精选主题，提供创作灵感：

- **每日更新**: 每天更换一个主题
- **时区适配**: 根据用户时区显示当天主题
- **模板关联**: 每个主题关联多个模板

### 2.2 主题分类

```
主题分类结构:
├── 节日 (Holidays)
│   ├── 春节
│   ├── 圣诞节
│   └── ...
├── 季节 (Seasons)
│   ├── 春天
│   ├── 夏天
│   └── ...
├── 教育 (Education)
│   ├── 字母
│   ├── 数字
│   └── ...
└── 生活 (Life)
    ├── 动物
    ├── 食物
    └── ...
```

---

## 三、数据模型

### 3.1 Theme Entity

```python
class ThemeEntity:
    id: UUID
    name: str                    # 主题名称
    slug: str                    # URL 友好标识
    description: Optional[str]   # 描述
    category: str                # 分类
    cover_image_url: str         # 封面图
    is_active: bool              # 是否启用
    display_order: int           # 显示顺序
    scheduled_date: Optional[date]  # Daily Doodle 计划日期
    created_at: datetime
    updated_at: datetime
```

### 3.2 数据库 Schema

```sql
CREATE TABLE themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    cover_image_url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    scheduled_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 主题与模板关联
CREATE TABLE theme_templates (
    theme_id UUID REFERENCES themes(id),
    template_id UUID REFERENCES templates(id),
    display_order INTEGER DEFAULT 0,
    PRIMARY KEY (theme_id, template_id)
);

-- 索引
CREATE INDEX idx_themes_category ON themes(category);
CREATE INDEX idx_themes_scheduled ON themes(scheduled_date);
CREATE INDEX idx_themes_active ON themes(is_active) WHERE is_active = true;
```

---

## 四、核心流程

### 4.1 Daily Doodle 获取

```
┌─────────────────────────────────────────────────────────────────┐
│                   Daily Doodle 获取流程                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 获取用户时区                                                │
│     │                                                           │
│     ↓                                                           │
│  2. 计算用户当前日期                                            │
│     │                                                           │
│     ↓                                                           │
│  3. 查询 scheduled_date = 当前日期 的主题                       │
│     │                                                           │
│     ├── 有结果 → 返回该主题                                     │
│     │                                                           │
│     └── 无结果 → 返回随机活跃主题                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 主题列表展示

```python
async def get_themes_by_category(
    self,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[ThemeEntity], int]:
    """
    获取主题列表
    
    Args:
        category: 可选分类筛选
        offset: 分页偏移
        limit: 每页数量
    
    Returns:
        (主题列表, 总数)
    """
```

---

## 五、API 端点

### 5.1 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/themes/daily` | 获取 Daily Doodle |
| GET | `/api/v1/themes` | 获取主题列表 |
| GET | `/api/v1/themes/{slug}` | 获取主题详情 |
| GET | `/api/v1/themes/{slug}/templates` | 获取主题下的模板 |
| GET | `/api/v1/themes/categories` | 获取分类列表 |

### 5.2 响应示例

**Daily Doodle**:
```json
{
    "id": "uuid",
    "name": "春节",
    "slug": "chinese-new-year",
    "description": "庆祝中国传统新年",
    "category": "holidays",
    "cover_image_url": "https://...",
    "template_count": 12
}
```

**主题列表**:
```json
{
    "items": [
        {
            "id": "uuid",
            "name": "春节",
            "slug": "chinese-new-year",
            "category": "holidays",
            "cover_image_url": "https://...",
            "template_count": 12
        }
    ],
    "total": 50,
    "has_more": true
}
```

---

## 六、前端展示规则

### 6.1 Daily Doodle 展示

- **位置**: 首页顶部突出展示
- **刷新**: 每日自动切换
- **交互**: 点击进入主题详情页

### 6.2 主题网格

```
显示规则:
- 默认按 display_order 排序
- 每行 3-4 个主题卡片
- 懒加载分页
- 分类筛选
```

### 6.3 主题详情页

```
页面结构:
├── 主题封面大图
├── 主题名称和描述
├── 模板网格 (关联模板)
└── 相关主题推荐
```

---

## 七、Admin 管理

### 7.1 主题管理

| 操作 | 描述 |
|------|------|
| 创建主题 | 设置名称、分类、封面 |
| 编辑主题 | 修改信息、关联模板 |
| 排期 | 设置 Daily Doodle 日期 |
| 排序 | 调整显示顺序 |
| 停用 | 隐藏主题 |

### 7.2 批量操作

```python
# 批量排期 Daily Doodle
async def schedule_daily_doodles(
    self,
    schedules: List[dict]  # [{theme_id, date}, ...]
) -> int:
    """批量设置 Daily Doodle 排期"""
```

---

## 八、缓存策略

```python
CACHE_TTL = {
    'daily_doodle': 3600,      # 1 小时
    'theme_list': 1800,        # 30 分钟
    'theme_detail': 3600,      # 1 小时
    'categories': 86400,       # 24 小时
}
```

---

## 九、相关文档

- [内容 CMS](../admin/content-cms.md)
- [Marketplace 架构](../marketplace/architecture.md)
