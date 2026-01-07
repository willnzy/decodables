# 素材分类系统设计方案

> **版本**: v1.0  
> **日期**: 2026-01-06  
> **目标**: 设计灵活、可扩展、易管理的素材分类系统

---

## 目录

1. [需求分析](#1-需求分析)
2. [分类体系设计](#2-分类体系设计)
3. [数据库设计](#3-数据库设计)
4. [后台管理系统](#4-后台管理系统)
5. [前端展示逻辑](#5-前端展示逻辑)
6. [API 设计](#6-api-设计)
7. [缓存策略](#7-缓存策略)
8. [扩展场景](#8-扩展场景)
9. [实施计划](#9-实施计划)

---

## 1. 需求分析

### 1.1 产品特性

```
┌─────────────────────────────────────────────────────────────────┐
│                    Make Decodables 产品特性                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  目标用户:                                                       │
│  • K-12 教师 (核心用户)                                          │
│  • 家长                                                          │
│  • 教育出版商                                                    │
│                                                                 │
│  核心场景:                                                       │
│  • 创建 8 页可折叠 mini-book                                    │
│  • 用于阅读教学 (phonics, decodables)                           │
│  • 需要大量教育相关素材                                          │
│                                                                 │
│  素材需求特点:                                                   │
│  • 教育主题为主 (学校、学习、字母、数字)                        │
│  • 儿童风格插画                                                  │
│  • 简单形状和图标                                                │
│  • 表格用于练习题                                                │
│  • 需要 PRO 和免费素材区分                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 分类系统需求

| 需求 | 说明 | 优先级 |
|------|------|--------|
| **多级分类** | 支持 2-3 级分类层次 | 🔴 P0 |
| **动态配置** | 后台可增删改分类，无需发版 | 🔴 P0 |
| **排序控制** | 可调整分类和素材显示顺序 | 🔴 P0 |
| **显示控制** | 可隐藏/显示特定分类 | 🔴 P0 |
| **权限控制** | Free/Pro 素材区分 | 🔴 P0 |
| **多语言** | 支持分类名称国际化 | 🟡 P1 |
| **标签系统** | 素材可打多个标签，支持搜索 | 🟡 P1 |
| **主题分组** | 按主题/节日等分组展示 | 🟢 P2 |
| **数据统计** | 统计各分类使用频率 | 🟢 P2 |

### 1.3 当前问题

```
┌─────────────────────────────────────────────────────────────────┐
│                    当前分类问题分析                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  问题 1: 维度混乱                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  当前结构:                                                │   │
│  │  └── 顶层: [System] [My Assets]  ← 来源维度              │   │
│  │      └── 内容: [Emoji][Sticker][Shape]... ← 类型维度     │   │
│  │                                                          │   │
│  │  问题: 两个维度混在同一层级，逻辑混乱                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  问题 2: 分类固定                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 分类写死在代码中                                       │   │
│  │  • 新增分类需要发版                                       │   │
│  │  • 无法快速响应业务需求                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  问题 3: 缺乏灵活性                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 无法调整分类顺序                                       │   │
│  │  • 无法隐藏某个分类                                       │   │
│  │  • 无法按时间/节日展示特定素材                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  问题 4: Emoji/Sticker 界限模糊                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 用户不清楚两者区别                                     │   │
│  │  • 搜索时需要分别搜索                                     │   │
│  │  • 实际上都是"图片类素材"                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 分类体系设计

### 2.1 分类维度分析

```
┌─────────────────────────────────────────────────────────────────┐
│                    分类维度分析                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  维度 1: 素材来源 (Source)                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • system    - 系统内置素材                               │   │
│  │  • user      - 用户上传素材                               │   │
│  │  • ai        - AI 生成素材                               │   │
│  │  • community - 社区共享素材                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  维度 2: 素材类型 (Type) - 决定渲染方式                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • text      - 文本元素 (Text, Heading, Caption)         │   │
│  │  • image     - 图片元素 (PNG, JPG, SVG图片)               │   │
│  │  • shape     - 形状元素 (矢量形状, 可编辑属性)              │   │
│  │  • table     - 表格元素                                   │   │
│  │  • line      - 线条元素                                   │   │
│  │  • group     - 组合元素 (多个元素的组合)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  维度 3: 内容分类 (Category) - 用户浏览维度                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  这是面向用户的分类，可动态配置                              │   │
│  │  例如: Faces, Animals, Nature, Education, Shapes...      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  维度 4: 权限等级 (Tier)                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • free      - 免费用户可用                               │   │
│  │  • starter   - starter初级用户可用       (修改)            │   │
│  │  • pro       - Pro 高级用户专属                           │   │
│  │  • ultra     - 未来的 特别计划专属                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  维度 5: 标签 (Tags) - 搜索和过滤                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  一个素材可以有多个标签                                     │   │
│  │  例如: ["cat", "animal", "pet", "cute", "education"]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 新分类体系

```
┌─────────────────────────────────────────────────────────────────┐
│                    新分类体系                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  顶层入口 (Tab):                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [📝 Text] [🖼️ Graphics] [🔷 Shapes] [📊 Tables] [📁 My] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  设计原则:                                                       │
│  • 按"用户意图"而非"技术类型"分类                               │
│  • 减少用户思考成本                                              │
│  • 每个 Tab 内部可动态配置子分类                                │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  📝 Text (文本)                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  用途: 添加文字到画布                                      │   │
│  │  type: text                                             │   │
│  │                                                         │   │
│  │  子分类 (后台配置):                                       │   │
│  │  ├── Headings     - Title, Heading, Subheading          │   │
│  │  ├── Body Text    - Body, Caption, Quote                │   │
│  │  ├── Lists        - Bullet List, Number List            │   │
│  │  └── Decorative   - Fancy Text, Word Art                │   │
│  │                                                         │   │
│  │  特殊功能: 数学符号、特殊字符插入                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🖼️ Graphics (图形素材)                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  用途: 添加视觉装饰元素                                    │   │
│  │  type: image                                            │   │
│  │                                                         │   │
│  │  子分类 (后台配置):                                        │   │
│  │  ├── 😀 Emoji          - 表情符号                         │   │
│  │  ├── ✨ Stickers        - 贴纸/插画                       │   │
│  │  │   ├── Animals                                        │   │
│  │  │   ├── Nature                                         │   │
│  │  │   ├── Objects                                        │   │
│  │  │   ├── Education                                      │   │
│  │  │   └── Decorations                                    │   │
│  │  ├── 🖼️ Illustrations   - 场景插画                        │   │
│  │  ├── 🎨 Backgrounds     - 背景图                         │   │
│  │  │   ├── Gradients                                      │   │
│  │  │   ├── Patterns                                        │   │
│  │  │   └── Solid Colors                                    │   │
│  │  └── 🖼️ Frames          - 相框/边框                       │   │
│  │                                                          │   │
│  │  合并逻辑: Emoji/Sticker/Image 都是"图形素材"               │   │
│  │  用户视角: "我要添加一个图片/装饰"                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🔷 Shapes (形状)                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  用途: 添加可编辑形状                                     │   │
│  │  type: shape, line                                       │   │
│  │                                                          │   │
│  │  子分类 (后台配置):                                       │   │
│  │  ├── Basic Shapes   - 矩形, 圆形, 三角形, 星形           │   │
│  │  ├── Arrows         - 各种箭头                           │   │
│  │  ├── Callouts       - 对话框, 标注框                     │   │
│  │  ├── Lines          - 直线, 曲线, 连接线                 │   │
│  │  └── Icons          - 简单图标 (SVG, 可变色)            │   │
│  │                                                          │   │
│  │  与 Graphics 区别: Shapes 支持属性编辑 (颜色/边框)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📊 Tables (表格)                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  用途: 添加表格                                           │   │
│  │  type: table                                             │   │
│  │                                                          │   │
│  │  子分类 (后台配置):                                       │   │
│  │  ├── Custom Table   - 自定义行列                         │   │
│  │  ├── Quick Presets  - 2×2, 3×3, 4×3 等                  │   │
│  │  └── Templates      - 课程表, 对比表, 清单表 (未来)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📁 My Assets (我的素材)                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  用途: 管理用户自己的素材                                 │   │
│  │  source: user, ai                                        │   │
│  │                                                          │   │
│  │  子分类:                                                  │   │
│  │  ├── Upload         - 上传新素材                         │   │
│  │  ├── AI Generate    - AI 生成                            │   │
│  │  ├── Smart Scan    - AI 扫描并生成        (修改)                     │   │
│  │  ├── Recent         - 最近上传                           │   │
│  │  └── Folders        - 用户文件夹
│  │                                                          │   │
│  │  特殊: 这个 Tab 按"来源"维度，与其他 Tab 不同            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 分类层级结构

```
┌─────────────────────────────────────────────────────────────────┐
│                    分类层级结构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 0: Root (隐藏)                                           │
│  │                                                              │
│  ├── Level 1: Tab (顶层入口，固定 5 个)                         │
│  │   │                                                          │
│  │   ├── text                                                  │
│  │   ├── graphics                                              │
│  │   ├── shapes                                                │
│  │   ├── tables                                                │
│  │   └── my-assets                                             │
│  │                                                              │
│  │   ├── Level 2: Category (一级分类，可配置)                  │
│  │   │   │                                                      │
│  │   │   ├── graphics/emoji                                    │
│  │   │   ├── graphics/stickers                                 │
│  │   │   ├── graphics/illustrations                            │
│  │   │   ├── graphics/backgrounds                              │
│  │   │   └── graphics/frames                                   │
│  │   │                                                          │
│  │   │   ├── Level 3: Sub-Category (二级分类，可配置)          │
│  │   │   │   │                                                  │
│  │   │   │   ├── graphics/stickers/animals                    │
│  │   │   │   ├── graphics/stickers/nature                     │
│  │   │   │   ├── graphics/stickers/education                  │
│  │   │   │   └── ...                                           │
│  │   │   │                                                      │
│  │   │   │   └── Level 4: Assets (素材)                        │
│  │   │   │                                                      │
│  │   │   └── 最多 3 级分类 (Tab → Category → Sub-Category)     │
│  │   │                                                          │
│  │   └── 建议: 大部分场景 2 级足够，避免过深                   │
│  │                                                              │
│  └── 结构灵活性:                                                │
│      • Level 1 (Tab): 固定，代码控制                           │
│      • Level 2-3 (Category): 动态，后台配置                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 教育产品推荐分类

```
┌─────────────────────────────────────────────────────────────────┐
│                    教育产品推荐分类                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🖼️ Graphics Tab 推荐子分类:                                     │
│                                                                 │
│  一级分类          二级分类                    说明             │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  😀 Emoji          Faces                      表情              │
│                    Animals                    动物              │
│                    Nature                     自然              │
│                    Food                       食物              │
│                    Objects                    物品              │
│                    Symbols                    符号              │
│                                                                 │
│  ✨ Stickers       Animals                    动物贴纸          │
│                    Nature                     自然贴纸          │
│                    People                     人物              │
│                    Education                  教育主题 ⭐       │
│                    ├── Alphabet              字母              │
│                    ├── Numbers               数字              │
│                    ├── School                学校              │
│                    └── Science               科学              │
│                    Holidays                   节日 ⭐          │
│                    ├── Halloween             万圣节            │
│                    ├── Christmas             圣诞节            │
│                    ├── Easter                复活节            │
│                    └── ...                                     │
│                    Decorations               装饰              │
│                                                                 │
│  🖼️ Illustrations  Scenes                     场景插画          │
│                    Characters                 角色              │
│                    Borders                    花边              │
│                                                                 │
│  🎨 Backgrounds    Gradients                  渐变              │
│                    Patterns                   图案              │
│                    ├── Dots                  圆点              │
│                    ├── Lines                 线条              │
│                    ├── Grid                  网格              │
│                    └── Stars                 星星              │
│                    Solid Colors              纯色              │
│                    Textures                   纹理              │
│                                                                 │
│  🖼️ Frames         Photo Frames               相框              │
│                    Text Frames                文字框            │
│                    Decorative Borders         装饰边框          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  🔷 Shapes Tab 推荐子分类:                                       │
│                                                                 │
│  Basic Shapes      Rectangle, Square, Circle, Ellipse          │
│                    Triangle, Pentagon, Hexagon                 │
│                    Star, Heart, Cross                          │
│                                                                 │
│  Arrows            Single Arrow, Double Arrow                  │
│                    Curved Arrow, Connector                     │
│                                                                 │
│  Callouts          Speech Bubble, Thought Bubble               │
│                    Banner, Label                               │
│                                                                 │
│  Lines             Straight, Curved, Zigzag                    │
│                    Dashed, Dotted                              │
│                                                                 │
│  Icons             Common Icons (checkmark, x, star)           │
│                    Education Icons (book, pencil, ruler)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 数据库设计

### 3.1 核心表结构

```sql
-- ============================================================
-- 分类表 (asset_categories)
-- 支持多级分类的树形结构
-- ============================================================

CREATE TABLE asset_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- 层级关系
  parent_id UUID REFERENCES asset_categories(id) ON DELETE CASCADE,
  path LTREE NOT NULL,                    -- 物化路径, 如 'graphics.stickers.animals'
  level INT NOT NULL DEFAULT 1,           -- 层级深度 (1-3)
  
  -- 基本信息
  slug VARCHAR(50) NOT NULL UNIQUE,       -- URL友好标识, 如 'animals'
  name VARCHAR(100) NOT NULL,             -- 显示名称
  name_i18n JSONB DEFAULT '{}',           -- 国际化名称 {"en": "Animals", "zh": "动物"}
  description TEXT,
  icon VARCHAR(50),                       -- 图标 (emoji 或 icon name)
  
  -- 关联的素材类型
  asset_type VARCHAR(20) NOT NULL,        -- text, image, shape, table, line
  
  -- 显示控制
  is_visible BOOLEAN DEFAULT true,
  is_featured BOOLEAN DEFAULT false,      -- 是否推荐/置顶
  display_order INT DEFAULT 0,            -- 排序权重
  
  -- 访问控制
  min_tier VARCHAR(20) DEFAULT 'free',    -- 最低访问等级: free, pro, exclusive
  
  -- 时间限定 (用于节日主题)
  visible_from TIMESTAMPTZ,               -- 开始显示时间
  visible_until TIMESTAMPTZ,              -- 结束显示时间
  
  -- 元数据
  metadata JSONB DEFAULT '{}',            -- 扩展字段
  
  -- 统计
  asset_count INT DEFAULT 0,              -- 素材数量 (缓存)
  usage_count INT DEFAULT 0,              -- 使用次数
  
  -- 时间戳
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- 索引
  CONSTRAINT valid_level CHECK (level BETWEEN 1 AND 3)
);

-- 物化路径索引 (高效查询子分类)
CREATE INDEX idx_categories_path ON asset_categories USING GIST (path);
CREATE INDEX idx_categories_parent ON asset_categories(parent_id);
CREATE INDEX idx_categories_visible ON asset_categories(is_visible, display_order);
CREATE INDEX idx_categories_type ON asset_categories(asset_type);

-- ============================================================
-- 素材表 (assets)
-- 存储所有类型的素材
-- ============================================================

CREATE TABLE assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- 分类关联
  category_id UUID NOT NULL REFERENCES asset_categories(id),
  
  -- 基本信息
  name VARCHAR(200) NOT NULL,
  name_i18n JSONB DEFAULT '{}',
  slug VARCHAR(100),                      -- URL友好标识
  
  -- 素材类型 (与分类保持一致)
  asset_type VARCHAR(20) NOT NULL,        -- text, image, shape, table, line
  
  -- 来源
  source VARCHAR(20) NOT NULL DEFAULT 'system',  -- system, user, ai, community
  source_user_id UUID REFERENCES auth.users(id), -- 如果是用户上传
  
  -- 文件信息
  file_url TEXT,                          -- 原始文件 URL
  thumbnail_url TEXT,                     -- 缩略图 URL
  file_size INT,                          -- 文件大小 (bytes)
  file_format VARCHAR(20),                -- png, jpg, svg, etc.
  
  -- 尺寸信息
  width INT,
  height INT,
  
  -- 素材内容 (根据类型不同)
  content JSONB NOT NULL DEFAULT '{}',    -- 具体内容数据
  /*
    text 类型:
    {
      "text": "Title",
      "fontSize": 48,
      "fontWeight": "bold",
      "fontFamily": "Inter"
    }
    
    shape 类型:
    {
      "shapeType": "rectangle",
      "svgPath": "M0 0 L100 0 L100 100 L0 100 Z",
      "defaultFill": "#6EE7B7",
      "defaultStroke": "#000000"
    }
    
    image 类型:
    {
      "altText": "A cute cat",
      "colors": ["#FF5733", "#33FF57"]  // 主色调，用于搜索
    }
  */
  
  -- 访问控制
  tier VARCHAR(20) DEFAULT 'free',        -- free, pro, exclusive
  
  -- 显示控制
  is_visible BOOLEAN DEFAULT true,
  is_featured BOOLEAN DEFAULT false,
  display_order INT DEFAULT 0,
  
  -- 搜索优化
  search_text TSVECTOR,                   -- 全文搜索向量
  
  -- 统计
  usage_count INT DEFAULT 0,
  
  -- 时间戳
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_assets_category ON assets(category_id);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_source ON assets(source);
CREATE INDEX idx_assets_tier ON assets(tier);
CREATE INDEX idx_assets_visible ON assets(is_visible, display_order);
CREATE INDEX idx_assets_search ON assets USING GIN(search_text);
CREATE INDEX idx_assets_featured ON assets(is_featured) WHERE is_featured = true;

-- ============================================================
-- 素材标签表 (asset_tags)
-- 支持多标签搜索
-- ============================================================

CREATE TABLE asset_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  name VARCHAR(50) NOT NULL,
  slug VARCHAR(50) NOT NULL UNIQUE,
  name_i18n JSONB DEFAULT '{}',
  
  -- 标签类型
  tag_type VARCHAR(20) DEFAULT 'general', -- general, color, style, theme, season
  
  -- 统计
  usage_count INT DEFAULT 0,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tags_type ON asset_tags(tag_type);
CREATE INDEX idx_tags_name ON asset_tags(name);

-- ============================================================
-- 素材-标签关联表 (asset_tag_relations)
-- ============================================================

CREATE TABLE asset_tag_relations (
  asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
  tag_id UUID REFERENCES asset_tags(id) ON DELETE CASCADE,
  
  PRIMARY KEY (asset_id, tag_id)
);

CREATE INDEX idx_tag_relations_asset ON asset_tag_relations(asset_id);
CREATE INDEX idx_tag_relations_tag ON asset_tag_relations(tag_id);

-- ============================================================
-- 用户最近使用记录 (user_recent_assets)
-- ============================================================

CREATE TABLE user_recent_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  
  used_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(user_id, asset_id)
);

CREATE INDEX idx_recent_user ON user_recent_assets(user_id, used_at DESC);

-- ============================================================
-- 用户收藏 (user_favorite_assets)
-- ============================================================

CREATE TABLE user_favorite_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(user_id, asset_id)
);

CREATE INDEX idx_favorites_user ON user_favorite_assets(user_id);

-- ============================================================
-- 用户上传素材 (user_assets)
-- 用户自己上传的素材，独立存储
-- ============================================================

CREATE TABLE user_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- 文件信息
  name VARCHAR(200) NOT NULL,
  file_url TEXT NOT NULL,
  thumbnail_url TEXT,
  file_size INT,
  file_format VARCHAR(20),
  width INT,
  height INT,
  
  -- 来源
  source VARCHAR(20) DEFAULT 'upload',    -- upload, ai
  
  -- 项目关联 (可选)
  project_id UUID,                        -- 如果只在特定项目中使用
  
  -- 访问范围
  scope VARCHAR(20) DEFAULT 'all',        -- all (所有项目), project (仅当前项目)
  
  -- 文件夹 (用户自定义整理)
  folder_path VARCHAR(500) DEFAULT '/',
  
  -- 元数据
  metadata JSONB DEFAULT '{}',
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_assets_user ON user_assets(user_id);
CREATE INDEX idx_user_assets_project ON user_assets(project_id);
CREATE INDEX idx_user_assets_folder ON user_assets(user_id, folder_path);
```

### 3.2 分类路径示例

```
┌─────────────────────────────────────────────────────────────────┐
│                    分类路径示例                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  使用 LTREE 类型存储物化路径:                                    │
│                                                                 │
│  路径                              含义                         │
│  ─────────────────────────────────────────────────────────────  │
│  graphics                         Graphics Tab 根节点           │
│  graphics.emoji                   Emoji 分类                    │
│  graphics.emoji.faces             Emoji > Faces                │
│  graphics.emoji.animals           Emoji > Animals              │
│  graphics.stickers                Stickers 分类                 │
│  graphics.stickers.animals        Stickers > Animals           │
│  graphics.stickers.education      Stickers > Education         │
│  graphics.backgrounds             Backgrounds 分类              │
│  graphics.backgrounds.gradients   Backgrounds > Gradients      │
│                                                                 │
│  shapes                           Shapes Tab 根节点             │
│  shapes.basic                     Basic Shapes                 │
│  shapes.arrows                    Arrows                       │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  查询示例:                                                       │
│                                                                 │
│  -- 获取 graphics 下所有分类                                    │
│  SELECT * FROM asset_categories                                 │
│  WHERE path <@ 'graphics';                                      │
│                                                                 │
│  -- 获取 stickers 的直接子分类                                  │
│  SELECT * FROM asset_categories                                 │
│  WHERE path ~ 'graphics.stickers.*{1}';                        │
│                                                                 │
│  -- 获取某分类及其所有子分类的素材数量                          │
│  SELECT SUM(asset_count) FROM asset_categories                  │
│  WHERE path <@ 'graphics.stickers';                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 素材内容结构

```typescript
// types/asset.ts

// 素材类型枚举
type AssetType = 'text' | 'image' | 'shape' | 'table' | 'line';

// 素材来源枚举
type AssetSource = 'system' | 'user' | 'ai' | 'community';

// 访问等级
type AssetTier = 'free' | 'pro' | 'exclusive';

// 基础素材接口
interface BaseAsset {
  id: string;
  categoryId: string;
  categoryPath: string;           // 冗余存储，方便查询
  
  name: string;
  nameI18n?: Record<string, string>;
  
  assetType: AssetType;
  source: AssetSource;
  tier: AssetTier;
  
  thumbnailUrl?: string;
  fileUrl?: string;
  
  isVisible: boolean;
  isFeatured: boolean;
  displayOrder: number;
  
  tags: string[];
  
  usageCount: number;
  createdAt: Date;
  updatedAt: Date;
}

// 文本素材
interface TextAsset extends BaseAsset {
  assetType: 'text';
  content: {
    text: string;
    fontSize: number;
    fontWeight: string;
    fontFamily: string;
    color?: string;
    align?: 'left' | 'center' | 'right';
  };
}

// 图片素材 (Emoji, Sticker, Illustration, Background, Frame)
interface ImageAsset extends BaseAsset {
  assetType: 'image';
  content: {
    altText?: string;
    colors?: string[];            // 主色调
    isAnimated?: boolean;         // 是否动图
    hasTransparency?: boolean;    // 是否有透明通道
  };
  width: number;
  height: number;
  fileFormat: 'png' | 'jpg' | 'gif' | 'svg' | 'webp';
}

// 形状素材
interface ShapeAsset extends BaseAsset {
  assetType: 'shape';
  content: {
    shapeType: 'rectangle' | 'ellipse' | 'triangle' | 'star' | 'polygon' | 'custom';
    svgPath?: string;             // SVG 路径 (custom 类型)
    points?: number;              // 多边形边数
    defaultFill: string;
    defaultStroke: string;
    defaultStrokeWidth: number;
    isEditable: boolean;          // 是否可编辑路径
  };
}

// 线条素材
interface LineAsset extends BaseAsset {
  assetType: 'line';
  content: {
    lineType: 'straight' | 'curved' | 'connector' | 'arrow';
    svgPath?: string;
    defaultStroke: string;
    defaultStrokeWidth: number;
    startMarker?: 'none' | 'arrow' | 'circle' | 'square';
    endMarker?: 'none' | 'arrow' | 'circle' | 'square';
  };
}

// 表格素材 (预设模板)
interface TableAsset extends BaseAsset {
  assetType: 'table';
  content: {
    rows: number;
    columns: number;
    hasHeader: boolean;
    defaultHeaderBg: string;
    defaultCellBg: string;
    defaultBorderColor: string;
    templateData?: string[][];    // 预填内容 (模板)
  };
}

// 联合类型
type Asset = TextAsset | ImageAsset | ShapeAsset | LineAsset | TableAsset;

// 分类接口
interface AssetCategory {
  id: string;
  parentId: string | null;
  path: string;
  level: number;
  
  slug: string;
  name: string;
  nameI18n?: Record<string, string>;
  description?: string;
  icon?: string;
  
  assetType: AssetType;
  
  isVisible: boolean;
  isFeatured: boolean;
  displayOrder: number;
  
  minTier: AssetTier;
  
  visibleFrom?: Date;
  visibleUntil?: Date;
  
  assetCount: number;
  
  children?: AssetCategory[];     // 子分类 (前端构建)
}
```

---

## 4. 后台管理系统

### 4.1 分类管理界面

```
┌─────────────────────────────────────────────────────────────────┐
│                    分类管理界面                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Asset Categories                        [+ Add Category] │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  Tab Filter: [All ▼]  [Graphics] [Shapes] [Tables]      │   │
│  │  Status: [All ▼]  [Visible] [Hidden]                    │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │                                                     │ │   │
│  │  │  📁 Graphics (Tab)                        [⚙️][👁]  │ │   │
│  │  │  │                                                  │ │   │
│  │  │  ├── 😀 Emoji                    152 items  [⚙️][↕] │ │   │
│  │  │  │   ├── Faces                   86 items   [⚙️][↕] │ │   │
│  │  │  │   ├── Animals                 42 items   [⚙️][↕] │ │   │
│  │  │  │   ├── Nature                  28 items   [⚙️][↕] │ │   │
│  │  │  │   └── + Add Sub-Category                         │ │   │
│  │  │  │                                                  │ │   │
│  │  │  ├── ✨ Stickers                 89 items   [⚙️][↕] │ │   │
│  │  │  │   ├── Animals                 24 items   [⚙️][↕] │ │   │
│  │  │  │   ├── Nature                  18 items   [⚙️][↕] │ │   │
│  │  │  │   ├── Education ⭐            32 items   [⚙️][↕] │ │   │
│  │  │  │   │   ├── Alphabet            26 items   [⚙️]    │ │   │
│  │  │  │   │   └── Numbers             6 items    [⚙️]    │ │   │
│  │  │  │   └── + Add Sub-Category                         │ │   │
│  │  │  │                                                  │ │   │
│  │  │  ├── 🖼️ Illustrations 🔒 Hidden   45 items  [⚙️][↕] │ │   │
│  │  │  │                                                  │ │   │
│  │  │  └── + Add Category                                 │ │   │
│  │  │                                                     │ │   │
│  │  │  📁 Shapes (Tab)                          [⚙️][👁]  │ │   │
│  │  │  │                                                  │ │   │
│  │  │  ├── Basic Shapes                32 items   [⚙️][↕] │ │   │
│  │  │  ├── Arrows                      12 items   [⚙️][↕] │ │   │
│  │  │  └── ...                                            │ │   │
│  │  │                                                     │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  图标说明:                                               │   │
│  │  ⚙️ 编辑   ↕ 拖拽排序   👁 显示/隐藏   ⭐ 置顶          │   │
│  │  🔒 隐藏状态   PRO Pro专属                              │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 分类编辑表单

```
┌─────────────────────────────────────────────────────────────────┐
│                    编辑分类: Stickers > Education                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Basic Information                                              │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Name (English) *                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Education                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Name (Chinese)                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  教育                                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Slug *                          Icon                           │
│  ┌────────────────────────┐      ┌────────────────────────┐    │
│  │  education              │      │  📚  [Select]         │    │
│  └────────────────────────┘      └────────────────────────┘    │
│                                                                 │
│  Parent Category                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Graphics > Stickers                               ▼    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Description                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Educational themed stickers including alphabet,        │   │
│  │  numbers, school supplies, and learning activities.     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Display Settings                                               │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Visibility    [● Visible  ○ Hidden]                           │
│                                                                 │
│  Featured      [✓] Show in featured section                    │
│                                                                 │
│  Display Order  ┌────────┐                                     │
│                 │  10    │  (Lower = Higher priority)          │
│                 └────────┘                                     │
│                                                                 │
│  Access Control                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Minimum Tier   [● Free  ○ Pro  ○ Exclusive]                   │
│                                                                 │
│  Time-Limited Display                                           │
│  [✓] Enable time-limited visibility                            │
│                                                                 │
│  Visible From   ┌─────────────┐  To  ┌─────────────┐          │
│                 │ 2026-10-01  │      │ 2026-10-31  │          │
│                 └─────────────┘      └─────────────┘          │
│  (For seasonal/holiday content)                                │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│                           [Cancel]  [Save Changes]              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 素材管理界面

```
┌─────────────────────────────────────────────────────────────────┐
│                    素材管理界面                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Assets                    [+ Upload] [+ Bulk Import]   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  Category: [Graphics > Stickers > Animals ▼]            │   │
│  │  Tier: [All ▼]  Status: [All ▼]  Search: [______]      │   │
│  │                                                          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │                                                          │   │
│  │  Showing 24 of 156 assets                    [Grid][List]│   │
│  │                                                          │   │
│  │  ┌────────┬────────┬────────┬────────┬────────┬────────┐│   │
│  │  │ [✓]    │ [✓]    │ [ ]    │ [ ]    │ [ ]    │ [ ]    ││   │
│  │  │ 🐱     │ 🐶     │ 🐰     │ 🐻     │ 🦊     │ 🐼     ││   │
│  │  │ Cat    │ Dog    │ Rabbit │ Bear   │ Fox    │ Panda  ││   │
│  │  │ Free   │ Free   │ PRO    │ PRO    │ Free   │ PRO    ││   │
│  │  │ [⚙️]   │ [⚙️]   │ [⚙️]   │ [⚙️]   │ [⚙️]   │ [⚙️]   ││   │
│  │  └────────┴────────┴────────┴────────┴────────┴────────┘│   │
│  │                                                          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │                                                          │   │
│  │  Bulk Actions (2 selected):                              │   │
│  │  [Move to Category ▼] [Change Tier ▼] [Delete]          │   │
│  │                                                          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │                                                          │   │
│  │  [← Previous]  Page 1 of 7  [Next →]                    │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 批量导入

```
┌─────────────────────────────────────────────────────────────────┐
│                    批量导入素材                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Upload Files                                           │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │       📁 Drop files here or click to upload             │   │
│  │                                                          │   │
│  │       Supported: PNG, JPG, SVG, GIF                     │   │
│  │       Max 100 files at once, 10MB per file              │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Uploaded: 24 files                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  cat.png ✓     dog.png ✓     rabbit.png ✓    bear.png ✓ │   │
│  │  fox.png ✓     panda.png ✓   lion.png ✓      tiger.png ✓│   │
│  │  ...                                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Step 2: Set Properties                                         │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Target Category *                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Graphics > Stickers > Animals                      ▼   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Default Tier        Default Tags                               │
│  ┌──────────────┐    ┌─────────────────────────────────────┐   │
│  │  Free    ▼   │    │  animal, sticker, cute              │   │
│  └──────────────┘    └─────────────────────────────────────┘   │
│                                                                 │
│  Naming Rule                                                    │
│  [● Use filename  ○ Custom pattern]                            │
│                                                                 │
│  Step 3: Preview & Confirm                                      │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Preview:                                                 │  │
│  │  🖼️ cat.png      → "Cat" in Animals (Free)               │  │
│  │  🖼️ dog.png      → "Dog" in Animals (Free)               │  │
│  │  🖼️ rabbit.png   → "Rabbit" in Animals (Free)            │  │
│  │  ...                                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│                           [Cancel]  [Import 24 Assets]          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.5 后台功能清单

| 功能模块 | 功能点 | 优先级 |
|----------|--------|--------|
| **分类管理** | 分类 CRUD | 🔴 P0 |
| | 拖拽排序 | 🔴 P0 |
| | 显示/隐藏控制 | 🔴 P0 |
| | 多语言名称 | 🟡 P1 |
| | 时间限定显示 | 🟢 P2 |
| **素材管理** | 素材 CRUD | 🔴 P0 |
| | 批量导入 | 🔴 P0 |
| | 批量移动/删除 | 🔴 P0 |
| | 标签管理 | 🟡 P1 |
| | 素材搜索 | 🔴 P0 |
| **权限控制** | Free/Pro 设置 | 🔴 P0 |
| | 批量更改权限 | 🟡 P1 |
| **数据统计** | 素材使用统计 | 🟢 P2 |
| | 分类使用统计 | 🟢 P2 |

---

## 5. 前端展示逻辑

### 5.1 数据获取策略

```typescript
// hooks/useMediaLibrary.ts

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { create } from 'zustand';

// ============================================================
// 状态管理
// ============================================================

interface MediaLibraryState {
  // UI 状态
  activeTab: 'text' | 'graphics' | 'shapes' | 'tables' | 'my-assets';
  activeCategory: string | null;
  activeSubCategory: string | null;
  searchQuery: string;
  
  // Actions
  setActiveTab: (tab: string) => void;
  setActiveCategory: (categoryId: string | null) => void;
  setActiveSubCategory: (categoryId: string | null) => void;
  setSearchQuery: (query: string) => void;
}

export const useMediaLibraryStore = create<MediaLibraryState>((set) => ({
  activeTab: 'graphics',
  activeCategory: null,
  activeSubCategory: null,
  searchQuery: '',
  
  setActiveTab: (tab) => set({ 
    activeTab: tab as any, 
    activeCategory: null, 
    activeSubCategory: null 
  }),
  setActiveCategory: (categoryId) => set({ 
    activeCategory: categoryId, 
    activeSubCategory: null 
  }),
  setActiveSubCategory: (categoryId) => set({ activeSubCategory: categoryId }),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));

// ============================================================
// 数据获取 Hooks
// ============================================================

/**
 * 获取分类树
 * 初次加载时获取，缓存较长时间
 */
export function useCategoryTree() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await fetch('/api/categories');
      return response.json();
    },
    staleTime: 1000 * 60 * 30,    // 30 分钟内不重新获取
    cacheTime: 1000 * 60 * 60,    // 缓存 1 小时
  });
}

/**
 * 获取特定分类的素材
 * 支持分页和懒加载
 */
export function useCategoryAssets(
  categoryPath: string | null,
  options: {
    page?: number;
    pageSize?: number;
    tier?: 'all' | 'free' | 'pro';
  } = {}
) {
  const { page = 1, pageSize = 50, tier = 'all' } = options;
  
  return useQuery({
    queryKey: ['assets', categoryPath, page, pageSize, tier],
    queryFn: async () => {
      const params = new URLSearchParams({
        path: categoryPath || '',
        page: page.toString(),
        pageSize: pageSize.toString(),
        ...(tier !== 'all' && { tier }),
      });
      
      const response = await fetch(`/api/assets?${params}`);
      return response.json();
    },
    enabled: !!categoryPath,
    staleTime: 1000 * 60 * 5,     // 5 分钟
    keepPreviousData: true,        // 分页时保留上一页数据
  });
}

/**
 * 搜索素材
 */
export function useAssetSearch(query: string, tab?: string) {
  return useQuery({
    queryKey: ['assets', 'search', query, tab],
    queryFn: async () => {
      const params = new URLSearchParams({
        q: query,
        ...(tab && { tab }),
        limit: '50',
      });
      
      const response = await fetch(`/api/assets/search?${params}`);
      return response.json();
    },
    enabled: query.length >= 2,
    staleTime: 1000 * 60 * 5,
  });
}

/**
 * 获取最近使用的素材
 */
export function useRecentAssets() {
  return useQuery({
    queryKey: ['assets', 'recent'],
    queryFn: async () => {
      const response = await fetch('/api/assets/recent');
      return response.json();
    },
    staleTime: 1000 * 60,         // 1 分钟
  });
}

/**
 * 获取用户收藏的素材
 */
export function useFavoriteAssets() {
  return useQuery({
    queryKey: ['assets', 'favorites'],
    queryFn: async () => {
      const response = await fetch('/api/assets/favorites');
      return response.json();
    },
  });
}

/**
 * 获取用户上传的素材
 */
export function useUserAssets(options: {
  scope?: 'all' | 'project';
  projectId?: string;
  folder?: string;
} = {}) {
  return useQuery({
    queryKey: ['user-assets', options],
    queryFn: async () => {
      const params = new URLSearchParams(options as any);
      const response = await fetch(`/api/user/assets?${params}`);
      return response.json();
    },
  });
}

// ============================================================
// Mutations
// ============================================================

/**
 * 记录素材使用
 */
export function useRecordAssetUsage() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (assetId: string) => {
      await fetch(`/api/assets/${assetId}/use`, { method: 'POST' });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['assets', 'recent']);
    },
  });
}

/**
 * 切换收藏状态
 */
export function useToggleFavorite() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (assetId: string) => {
      await fetch(`/api/assets/${assetId}/favorite`, { method: 'POST' });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['assets', 'favorites']);
    },
  });
}
```

### 5.2 前端分类树构建

```typescript
// utils/categoryTree.ts

interface CategoryNode {
  id: string;
  slug: string;
  name: string;
  icon?: string;
  path: string;
  level: number;
  assetCount: number;
  children: CategoryNode[];
  
  // 运行时属性
  isExpanded?: boolean;
  isActive?: boolean;
}

/**
 * 将扁平分类列表构建为树形结构
 */
export function buildCategoryTree(categories: AssetCategory[]): CategoryNode[] {
  const nodeMap = new Map<string, CategoryNode>();
  const roots: CategoryNode[] = [];
  
  // 第一遍：创建所有节点
  categories.forEach((cat) => {
    nodeMap.set(cat.id, {
      ...cat,
      children: [],
    });
  });
  
  // 第二遍：建立父子关系
  categories.forEach((cat) => {
    const node = nodeMap.get(cat.id)!;
    
    if (cat.parentId) {
      const parent = nodeMap.get(cat.parentId);
      if (parent) {
        parent.children.push(node);
      }
    } else {
      roots.push(node);
    }
  });
  
  // 排序
  const sortNodes = (nodes: CategoryNode[]) => {
    nodes.sort((a, b) => a.displayOrder - b.displayOrder);
    nodes.forEach((node) => {
      if (node.children.length > 0) {
        sortNodes(node.children);
      }
    });
  };
  
  sortNodes(roots);
  
  return roots;
}

/**
 * 根据 Tab 获取对应的分类树
 */
export function getCategoriesForTab(
  tree: CategoryNode[], 
  tab: string
): CategoryNode[] {
  const tabNode = tree.find((node) => node.slug === tab);
  return tabNode?.children || [];
}

/**
 * 查找分类节点
 */
export function findCategoryNode(
  tree: CategoryNode[], 
  path: string
): CategoryNode | null {
  for (const node of tree) {
    if (node.path === path) {
      return node;
    }
    if (node.children.length > 0) {
      const found = findCategoryNode(node.children, path);
      if (found) return found;
    }
  }
  return null;
}

/**
 * 获取分类的面包屑路径
 */
export function getCategoryBreadcrumb(
  tree: CategoryNode[], 
  path: string
): CategoryNode[] {
  const parts = path.split('.');
  const breadcrumb: CategoryNode[] = [];
  
  let currentPath = '';
  let currentLevel = tree;
  
  for (const part of parts) {
    currentPath = currentPath ? `${currentPath}.${part}` : part;
    const node = currentLevel.find((n) => n.path === currentPath);
    
    if (node) {
      breadcrumb.push(node);
      currentLevel = node.children;
    }
  }
  
  return breadcrumb;
}
```

### 5.3 组件结构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Media Library 组件结构                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MediaLibrary/                                                  │
│  ├── MediaLibrary.tsx              # 主容器                     │
│  │   ├── MediaSearch.tsx           # 搜索框                     │
│  │   ├── MediaTabs.tsx             # 顶层 Tab                   │
│  │   ├── RecentSection.tsx         # 最近使用                   │
│  │   └── MediaContent.tsx          # 内容区域 (条件渲染)        │
│  │                                                              │
│  ├── tabs/                                                      │
│  │   ├── TextTab.tsx               # 文本 Tab                   │
│  │   │   └── TextPresetList.tsx    # 文本预设列表               │
│  │   │                                                          │
│  │   ├── GraphicsTab.tsx           # Graphics Tab               │
│  │   │   ├── CategoryPills.tsx     # 一级分类横向滚动           │
│  │   │   ├── SubCategoryList.tsx   # 二级分类折叠列表           │
│  │   │   └── AssetGrid.tsx         # 素材网格                   │
│  │   │                                                          │
│  │   ├── ShapesTab.tsx             # Shapes Tab                 │
│  │   │   ├── ShapeCategoryList.tsx                              │
│  │   │   └── ShapeGrid.tsx                                      │
│  │   │                                                          │
│  │   ├── TablesTab.tsx             # Tables Tab                 │
│  │   │   ├── TableCreator.tsx      # 自定义表格创建             │
│  │   │   └── TablePresets.tsx      # 预设模板                   │
│  │   │                                                          │
│  │   └── MyAssetsTab.tsx           # My Assets Tab              │
│  │       ├── UploadSection.tsx     # 上传区域                   │
│  │       ├── AIGenerateButton.tsx  # AI 生成入口                │
│  │       └── UserAssetGrid.tsx     # 用户素材列表               │
│  │                                                              │
│  ├── shared/                                                    │
│  │   ├── AssetCard.tsx             # 素材卡片                   │
│  │   ├── AssetGrid.tsx             # 虚拟滚动网格               │
│  │   ├── CategorySection.tsx       # 可折叠分类区块             │
│  │   ├── LoadingGrid.tsx           # 骨架屏                     │
│  │   ├── EmptyState.tsx            # 空状态                     │
│  │   └── ProBadge.tsx              # Pro 标记                   │
│  │                                                              │
│  └── hooks/                                                     │
│      ├── useMediaLibrary.ts        # 主状态 Hook                │
│      ├── useDragToCanvas.ts        # 拖拽到画布                 │
│      └── useAssetActions.ts        # 素材操作                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 Graphics Tab 详细实现

```tsx
// components/MediaLibrary/tabs/GraphicsTab.tsx

import React, { useMemo } from 'react';
import { useMediaLibraryStore } from '../hooks/useMediaLibrary';
import { useCategoryTree, useCategoryAssets } from '../hooks/useMediaLibrary';
import { getCategoriesForTab } from '../utils/categoryTree';
import { CategoryPills } from './CategoryPills';
import { SubCategoryList } from './SubCategoryList';
import { AssetGrid } from '../shared/AssetGrid';
import { LoadingGrid } from '../shared/LoadingGrid';

export function GraphicsTab() {
  const { 
    activeCategory, 
    activeSubCategory,
    setActiveCategory,
    setActiveSubCategory,
  } = useMediaLibraryStore();
  
  // 获取分类树
  const { data: categoryTree, isLoading: categoriesLoading } = useCategoryTree();
  
  // 获取 Graphics Tab 下的一级分类
  const categories = useMemo(() => {
    if (!categoryTree) return [];
    return getCategoriesForTab(categoryTree, 'graphics');
  }, [categoryTree]);
  
  // 当前活跃的一级分类
  const activeCategory1 = useMemo(() => {
    return categories.find((c) => c.id === activeCategory);
  }, [categories, activeCategory]);
  
  // 获取素材
  const assetPath = activeSubCategory 
    ? activeCategory1?.children.find((c) => c.id === activeSubCategory)?.path
    : activeCategory1?.path;
    
  const { 
    data: assetsData, 
    isLoading: assetsLoading,
    fetchNextPage,
    hasNextPage,
  } = useCategoryAssets(assetPath || null);
  
  // 默认选中第一个分类
  React.useEffect(() => {
    if (!activeCategory && categories.length > 0) {
      setActiveCategory(categories[0].id);
    }
  }, [categories, activeCategory, setActiveCategory]);
  
  if (categoriesLoading) {
    return <LoadingGrid />;
  }
  
  return (
    <div className="flex flex-col h-full">
      {/* 一级分类 - 横向滚动 Pills */}
      <CategoryPills
        categories={categories}
        activeId={activeCategory}
        onChange={setActiveCategory}
      />
      
      {/* 二级分类 + 素材 */}
      {activeCategory1 && (
        <div className="flex-1 overflow-auto">
          {activeCategory1.children.length > 0 ? (
            // 有二级分类时，显示可折叠列表
            <SubCategoryList
              categories={activeCategory1.children}
              activeId={activeSubCategory}
              onChange={setActiveSubCategory}
              renderAssets={(category) => (
                <AssetGrid
                  assets={category.assets}
                  isLoading={assetsLoading}
                />
              )}
            />
          ) : (
            // 没有二级分类时，直接显示素材
            <AssetGrid
              assets={assetsData?.assets || []}
              isLoading={assetsLoading}
              hasMore={hasNextPage}
              onLoadMore={fetchNextPage}
            />
          )}
        </div>
      )}
    </div>
  );
}
```

```tsx
// components/MediaLibrary/tabs/CategoryPills.tsx

import React, { useRef } from 'react';
import { cn } from '@/lib/utils';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';

interface CategoryPillsProps {
  categories: CategoryNode[];
  activeId: string | null;
  onChange: (id: string) => void;
}

export function CategoryPills({ 
  categories, 
  activeId, 
  onChange 
}: CategoryPillsProps) {
  return (
    <ScrollArea className="w-full whitespace-nowrap border-b">
      <div className="flex gap-2 p-2">
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => onChange(category.id)}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full',
              'text-sm font-medium transition-colors',
              'whitespace-nowrap',
              activeId === category.id
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted hover:bg-muted/80 text-muted-foreground'
            )}
          >
            {category.icon && <span>{category.icon}</span>}
            <span>{category.name}</span>
            <span className="text-xs opacity-70">
              {category.assetCount}
            </span>
          </button>
        ))}
      </div>
      <ScrollBar orientation="horizontal" />
    </ScrollArea>
  );
}
```

```tsx
// components/MediaLibrary/tabs/SubCategoryList.tsx

import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface SubCategoryListProps {
  categories: CategoryNode[];
  activeId: string | null;
  onChange: (id: string | null) => void;
  renderAssets: (category: CategoryNode) => React.ReactNode;
}

export function SubCategoryList({
  categories,
  activeId,
  onChange,
  renderAssets,
}: SubCategoryListProps) {
  // 默认展开第一个
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    new Set(categories.length > 0 ? [categories[0].id] : [])
  );
  
  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };
  
  return (
    <div className="space-y-1 p-2">
      {categories.map((category) => {
        const isExpanded = expandedIds.has(category.id);
        
        return (
          <Collapsible
            key={category.id}
            open={isExpanded}
            onOpenChange={() => toggleExpanded(category.id)}
          >
            <CollapsibleTrigger className="w-full">
              <div className={cn(
                'flex items-center justify-between p-2 rounded-lg',
                'hover:bg-muted transition-colors',
                isExpanded && 'bg-muted'
              )}>
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  {category.icon && <span>{category.icon}</span>}
                  <span className="font-medium">{category.name}</span>
                </div>
                <span className="text-sm text-muted-foreground">
                  ({category.assetCount})
                </span>
              </div>
            </CollapsibleTrigger>
            
            <CollapsibleContent>
              <div className="pl-6 py-2">
                {renderAssets(category)}
              </div>
            </CollapsibleContent>
          </Collapsible>
        );
      })}
    </div>
  );
}
```

---

## 6. API 设计

### 6.1 API 端点

```
┌─────────────────────────────────────────────────────────────────┐
│                    API 端点设计                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  分类 API:                                                       │
│  ─────────────────────────────────────────────────────────────  │
│  GET    /api/categories                 获取分类树              │
│  GET    /api/categories/:id             获取分类详情            │
│  POST   /api/admin/categories           创建分类 (Admin)        │
│  PUT    /api/admin/categories/:id       更新分类 (Admin)        │
│  DELETE /api/admin/categories/:id       删除分类 (Admin)        │
│  PUT    /api/admin/categories/reorder   调整排序 (Admin)        │
│                                                                 │
│  素材 API:                                                       │
│  ─────────────────────────────────────────────────────────────  │
│  GET    /api/assets                     获取素材列表            │
│         ?path=graphics.stickers.animals                        │
│         &page=1&pageSize=50                                    │
│         &tier=free                                             │
│                                                                 │
│  GET    /api/assets/:id                 获取素材详情            │
│  GET    /api/assets/search              搜索素材                │
│         ?q=cat&tab=graphics&limit=50                           │
│                                                                 │
│  GET    /api/assets/recent              获取最近使用            │
│  GET    /api/assets/favorites           获取收藏                │
│                                                                 │
│  POST   /api/assets/:id/use             记录使用                │
│  POST   /api/assets/:id/favorite        切换收藏                │
│                                                                 │
│  POST   /api/admin/assets               创建素材 (Admin)        │
│  PUT    /api/admin/assets/:id           更新素材 (Admin)        │
│  DELETE /api/admin/assets/:id           删除素材 (Admin)        │
│  POST   /api/admin/assets/bulk-import   批量导入 (Admin)        │
│                                                                 │
│  用户素材 API:                                                   │
│  ─────────────────────────────────────────────────────────────  │
│  GET    /api/user/assets                获取用户素材            │
│         ?scope=all&folder=/                                    │
│                                                                 │
│  POST   /api/user/assets                上传素材                │
│  DELETE /api/user/assets/:id            删除素材                │
│  PUT    /api/user/assets/:id/move       移动到文件夹            │
│                                                                 │
│  标签 API:                                                       │
│  ─────────────────────────────────────────────────────────────  │
│  GET    /api/tags                       获取标签列表            │
│  GET    /api/tags/popular               获取热门标签            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 响应格式

```typescript
// 分类树响应
interface CategoriesResponse {
  success: boolean;
  data: {
    categories: AssetCategory[];
    updatedAt: string;            // 用于缓存判断
  };
}

// 素材列表响应
interface AssetsResponse {
  success: boolean;
  data: {
    assets: Asset[];
    pagination: {
      page: number;
      pageSize: number;
      total: number;
      totalPages: number;
      hasMore: boolean;
    };
    category: {
      id: string;
      path: string;
      name: string;
    };
  };
}

// 搜索响应
interface SearchResponse {
  success: boolean;
  data: {
    results: Array<{
      category: string;
      categoryName: string;
      assets: Asset[];
      total: number;
    }>;
    query: string;
    totalResults: number;
  };
}
```

---

## 7. 缓存策略

### 7.1 多级缓存

```
┌─────────────────────────────────────────────────────────────────┐
│                    多级缓存策略                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 1: 浏览器内存缓存 (React Query)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  分类树:    staleTime: 30min, cacheTime: 60min          │   │
│  │  素材列表:  staleTime: 5min,  cacheTime: 30min          │   │
│  │  搜索结果:  staleTime: 5min,  cacheTime: 15min          │   │
│  │  最近使用:  staleTime: 1min,  cacheTime: 10min          │   │
│  │                                                          │   │
│  │  优点: 速度最快，零延迟                                  │   │
│  │  缺点: 页面刷新后失效                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Level 2: 浏览器持久缓存 (IndexedDB)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  存储内容:                                                │   │
│  │  • 分类树 (带版本号)                                      │   │
│  │  • 常用分类的素材 (前 2 页)                              │   │
│  │  • 最近使用记录                                           │   │
│  │  • 收藏记录                                               │   │
│  │                                                          │   │
│  │  更新策略:                                                │   │
│  │  • 启动时检查版本，有更新则刷新                          │   │
│  │  • 后台静默更新                                           │   │
│  │                                                          │   │
│  │  优点: 持久化，离线可用                                  │   │
│  │  缺点: 需要同步机制                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Level 3: CDN 缓存                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 素材图片: CDN 缓存 (1 年)                             │   │
│  │  • API 响应: Edge 缓存 (5 分钟)                          │   │
│  │                                                          │   │
│  │  使用 Cloudflare/Vercel Edge                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Level 4: 服务端缓存 (Redis)                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 分类树: TTL 1 小时                                    │   │
│  │  • 热门素材: TTL 30 分钟                                 │   │
│  │  • 搜索结果: TTL 5 分钟                                  │   │
│  │                                                          │   │
│  │  缓存失效:                                                │   │
│  │  • 后台更新分类/素材时主动失效                           │   │
│  │  • 使用 cache tags 批量失效                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 缓存实现

```typescript
// lib/cache/assetCache.ts

import { openDB, IDBPDatabase } from 'idb';

const DB_NAME = 'makedecodables-assets';
const DB_VERSION = 1;

interface CacheDB {
  categories: {
    key: 'tree';
    value: {
      data: AssetCategory[];
      version: string;
      cachedAt: number;
    };
  };
  assets: {
    key: string;  // categoryPath
    value: {
      data: Asset[];
      total: number;
      cachedAt: number;
    };
  };
  recent: {
    key: 'list';
    value: {
      assetIds: string[];
      updatedAt: number;
    };
  };
}

let dbPromise: Promise<IDBPDatabase<CacheDB>> | null = null;

function getDB() {
  if (!dbPromise) {
    dbPromise = openDB<CacheDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        db.createObjectStore('categories');
        db.createObjectStore('assets');
        db.createObjectStore('recent');
      },
    });
  }
  return dbPromise;
}

export const assetCache = {
  // 分类树缓存
  async getCategoryTree(): Promise<AssetCategory[] | null> {
    const db = await getDB();
    const cached = await db.get('categories', 'tree');
    
    if (!cached) return null;
    
    // 检查缓存是否过期 (1 小时)
    const isExpired = Date.now() - cached.cachedAt > 60 * 60 * 1000;
    if (isExpired) return null;
    
    return cached.data;
  },
  
  async setCategoryTree(data: AssetCategory[], version: string) {
    const db = await getDB();
    await db.put('categories', {
      data,
      version,
      cachedAt: Date.now(),
    }, 'tree');
  },
  
  // 素材缓存
  async getAssets(categoryPath: string): Promise<{ data: Asset[]; total: number } | null> {
    const db = await getDB();
    const cached = await db.get('assets', categoryPath);
    
    if (!cached) return null;
    
    // 检查缓存是否过期 (30 分钟)
    const isExpired = Date.now() - cached.cachedAt > 30 * 60 * 1000;
    if (isExpired) return null;
    
    return { data: cached.data, total: cached.total };
  },
  
  async setAssets(categoryPath: string, data: Asset[], total: number) {
    const db = await getDB();
    await db.put('assets', {
      data,
      total,
      cachedAt: Date.now(),
    }, categoryPath);
  },
  
  // 最近使用
  async getRecent(): Promise<string[]> {
    const db = await getDB();
    const cached = await db.get('recent', 'list');
    return cached?.assetIds || [];
  },
  
  async addRecent(assetId: string) {
    const db = await getDB();
    const current = await this.getRecent();
    
    // 去重，最多保留 20 个
    const updated = [assetId, ...current.filter((id) => id !== assetId)].slice(0, 20);
    
    await db.put('recent', {
      assetIds: updated,
      updatedAt: Date.now(),
    }, 'list');
  },
  
  // 清除缓存
  async clear() {
    const db = await getDB();
    await db.clear('categories');
    await db.clear('assets');
  },
};
```

---

## 8. 扩展场景

### 8.1 节日主题

```
┌─────────────────────────────────────────────────────────────────┐
│                    节日主题素材                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  场景: 万圣节期间自动显示万圣节素材                              │
│                                                                 │
│  实现方式:                                                       │
│  1. 创建节日分类，设置 visible_from 和 visible_until            │
│  2. API 查询时自动过滤时间范围                                  │
│  3. 前端在首页显示 "Holiday Picks" 区块                        │
│                                                                 │
│  数据库配置示例:                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  {                                                       │   │
│  │    "slug": "halloween",                                  │   │
│  │    "name": "Halloween",                                  │   │
│  │    "path": "graphics.stickers.holidays.halloween",       │   │
│  │    "is_featured": true,                                  │   │
│  │    "visible_from": "2026-10-01T00:00:00Z",              │   │
│  │    "visible_until": "2026-11-01T00:00:00Z"              │   │
│  │  }                                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  前端展示:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🎃 Halloween Picks                         [See all →]  │   │
│  │  ┌────────┬────────┬────────┬────────┐                  │   │
│  │  │ 🎃     │ 👻     │ 🦇     │ 🕷️     │                  │   │
│  │  └────────┴────────┴────────┴────────┘                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 社区素材 (未来)

```
┌─────────────────────────────────────────────────────────────────┐
│                    社区素材 (未来扩展)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  场景: 用户可以分享自己的素材给社区                              │
│                                                                 │
│  数据模型扩展:                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  assets 表新增字段:                                       │   │
│  │  • source: 'community'                                   │   │
│  │  • author_id: UUID                                       │   │
│  │  • is_approved: boolean                                  │   │
│  │  • likes_count: int                                      │   │
│  │  • downloads_count: int                                  │   │
│  │                                                          │   │
│  │  新增表:                                                  │   │
│  │  • community_submissions (提交审核)                      │   │
│  │  • community_likes (点赞)                                │   │
│  │  • community_reports (举报)                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  前端展示:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  新增 Tab: [Community]                                   │   │
│  │                                                          │   │
│  │  子分类:                                                  │   │
│  │  • Popular (热门)                                        │   │
│  │  • New (最新)                                            │   │
│  │  • Following (关注的创作者)                              │   │
│  │                                                          │   │
│  │  素材卡片显示:                                            │   │
│  │  • 作者头像和名称                                        │   │
│  │  • 点赞数                                                │   │
│  │  • 下载数                                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 AI 生成素材

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI 生成素材扩展                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  当前: AI 生成的图片存入 user_assets                            │
│                                                                 │
│  未来扩展:                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. AI 生成的热门素材可被提升为系统素材                   │   │
│  │     • 管理员审核后迁移到 assets 表                        │   │
│  │     • source: 'ai'                                       │   │
│  │                                                          │   │
│  │  2. AI 生成提示词模板                                     │   │
│  │     • 预设常用提示词 (教育场景)                          │   │
│  │     • 用户可保存自己的提示词                             │   │
│  │                                                          │   │
│  │  3. AI 素材风格一致性                                     │   │
│  │     • 提供风格预设 (卡通、写实、扁平)                    │   │
│  │     • 保持项目内风格统一                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. 实施计划

### 9.1 阶段规划

```
┌─────────────────────────────────────────────────────────────────┐
│                    实施计划                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: 数据库重构 (1 周)                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 创建新表结构                                           │   │
│  │  • 数据迁移脚本                                           │   │
│  │  • 迁移现有分类和素材数据                                 │   │
│  │  • 测试数据完整性                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 2: 后台管理 (1.5 周)                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 分类管理 CRUD                                          │   │
│  │  • 分类排序 (拖拽)                                        │   │
│  │  • 素材管理 CRUD                                          │   │
│  │  • 批量导入功能                                           │   │
│  │  • 权限控制 (Free/Pro)                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 3: API 开发 (1 周)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 分类 API                                               │   │
│  │  • 素材 API (列表、搜索)                                  │   │
│  │  • 用户素材 API                                           │   │
│  │  • 缓存层实现                                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 4: 前端重构 (2 周)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Week 1:                                                  │   │
│  │  • 新 Tab 结构实现                                        │   │
│  │  • 分类数据获取和缓存                                     │   │
│  │  • Graphics Tab 完整实现                                  │   │
│  │                                                          │   │
│  │  Week 2:                                                  │   │
│  │  • 其他 Tab 实现                                          │   │
│  │  • 搜索功能                                               │   │
│  │  • 最近使用 / 收藏                                        │   │
│  │  • 性能优化                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Phase 5: 测试和优化 (0.5 周)                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 功能测试                                               │   │
│  │  • 性能测试                                               │   │
│  │  • 数据验证                                               │   │
│  │  • Bug 修复                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  总计: 6 周                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 迁移策略

```
┌─────────────────────────────────────────────────────────────────┐
│                    数据迁移策略                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 并行运行                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 新表和旧表并行存在                                     │   │
│  │  • 迁移期间新数据同时写入两边                             │   │
│  │  • 前端通过 Feature Flag 切换数据源                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  2. 灰度发布                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 先对内部用户开放新系统                                 │   │
│  │  • 逐步增加比例 (10% → 50% → 100%)                       │   │
│  │  • 监控错误和性能                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  3. 回滚方案                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 保留旧表至少 1 个月                                    │   │
│  │  • Feature Flag 可快速回滚                                │   │
│  │  • 数据同步脚本随时可用                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 总结

### 核心设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| **Tab 数量** | 5 个 (Text/Graphics/Shapes/Tables/My) | 覆盖所有场景，不过多 |
| **分类层级** | 最多 3 级 | 平衡灵活性和复杂度 |
| **分类存储** | LTREE 物化路径 | 高效查询子树 |
| **前后端分离** | 后台配置 + API + 前端渲染 | 灵活、可扩展 |
| **缓存策略** | 4 级缓存 | 性能最优 |

### 关键优势

1. **灵活可配置**: 后台可随时调整分类，无需发版
2. **高性能**: 多级缓存 + 虚拟滚动
3. **可扩展**: 预留节日主题、社区素材、AI 素材扩展
4. **用户友好**: 按用户意图分类，搜索 + 最近使用

### 后台管理要点

1. **分类管理**: 树形展示、拖拽排序、显示控制
2. **素材管理**: 批量导入、批量操作、标签管理
3. **权限控制**: Free/Pro 灵活设置
4. **数据统计**: 使用频率、热门素材

---

**素材分类系统设计完成！**
