# 模板功能规格

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/templates/`, `api/user/templates.py`

---

## 一、概述

### 1.1 功能定位

模板功能帮助用户快速创建高质量的教育内容，提供专业设计的起点。

### 1.2 模板类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **Phonics** | 自然拼读教学 | CVC Words, Blends |
| **Sight Words** | 高频词学习 | Dolch Words, Fry Words |
| **Decodable Stories** | 可解码故事 | Short Vowels Story |
| **Blank** | 空白模板 | 8-page Mini-book |

---

## 二、功能范围

### 2.1 功能清单

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 模板浏览 | P0 | ✅ |
| 模板预览 | P0 | ✅ |
| 模板使用 | P0 | ✅ |
| 模板搜索 | P1 | ✅ |
| 模板收藏 | P1 | ✅ |
| 保存为模板 | P2 | 🔜 |

### 2.2 非目标

- 用户模板市场 (V2)
- 模板付费销售 (V2)
- 团队模板共享 (V3)

---

## 三、用户故事

### 3.1 模板浏览

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| TPL-01 | 作为教师，我想浏览 Phonics 模板 | 按分类筛选显示相关模板 |
| TPL-02 | 作为教师，我想看模板预览 | 显示所有页面缩略图 |

### 3.2 模板使用

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| TPL-03 | 作为教师，我想使用模板创建项目 | 点击使用 → 创建新项目 |
| TPL-04 | 作为教师，我想在现有项目应用模板 | 模板内容覆盖当前页面 |

### 3.3 模板管理

| ID | 用户故事 | 验收标准 |
|----|----------|----------|
| TPL-05 | 作为教师，我想收藏常用模板 | 可添加/移除收藏 |
| TPL-06 | 作为教师，我想保存自己的模板 | 可将项目保存为个人模板 |

---

## 四、功能详情

### 4.1 模板分类

```
┌────────────────────────────────────────────────────────────┐
│                    Template Categories                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📚 Phonics Templates                                      │
│  ├── CVC Words (cat, dog, sun...)                          │
│  ├── CVCe Words (cake, bike, cone...)                      │
│  ├── Consonant Blends (bl, cr, st...)                      │
│  ├── Digraphs (ch, sh, th, wh)                             │
│  └── R-Controlled Vowels (ar, er, ir, or, ur)              │
│                                                            │
│  👁️ Sight Words Templates                                  │
│  ├── Pre-Primer (the, and, a...)                           │
│  ├── Primer (he, she, was...)                              │
│  ├── First Grade (after, again, an...)                     │
│  └── Second Grade (always, around, because...)             │
│                                                            │
│  📖 Decodable Stories                                      │
│  ├── Short Vowel Stories                                   │
│  ├── Long Vowel Stories                                    │
│  └── Blend Stories                                         │
│                                                            │
│  📄 Blank Templates                                        │
│  ├── 8-Page Mini-book                                      │
│  ├── Letter Size                                           │
│  └── A4 Size                                               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.2 模板浏览页面

```
┌────────────────────────────────────────────────────────────┐
│                      Templates                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  [Search templates...]                    [Filter ▼]       │
│                                                            │
│  Categories: [All] [Phonics] [Sight Words] [Stories]       │
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │             │  │             │  │             │        │
│  │  [Preview]  │  │  [Preview]  │  │  [Preview]  │        │
│  │             │  │             │  │             │        │
│  │ CVC Words   │  │ CVCe Words  │  │ Blends      │        │
│  │ 8 pages     │  │ 8 pages     │  │ 8 pages     │        │
│  │ ♥ 234       │  │ ♥ 189       │  │ ♥ 156       │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │             │  │             │  │             │        │
│  │  [Preview]  │  │  [Preview]  │  │  [Preview]  │        │
│  │             │  │             │  │             │        │
│  │ Sight Words │  │ Short Story │  │ Blank       │        │
│  │ 8 pages     │  │ 8 pages     │  │ 8 pages     │        │
│  │ ♥ 312       │  │ ♥ 98        │  │ ♥ 567       │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.3 模板预览弹窗

```
┌────────────────────────────────────────────────────────────┐
│  CVC Words Template                              [×]       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌────────────────────────────────────┐                   │
│  │                                    │                   │
│  │        [Large Preview Image]       │                   │
│  │                                    │                   │
│  └────────────────────────────────────┘                   │
│                                                            │
│  Page 1 of 8                      [<] [1] [2] ... [8] [>]  │
│                                                            │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │  1   │ │  2   │ │  3   │ │  4   │ │  5   │ │ ...  │   │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │
│                                                            │
│  Description:                                              │
│  A fun mini-book for teaching CVC words (consonant-vowel- │
│  consonant). Perfect for K-1 students learning to decode. │
│                                                            │
│  [♡ Add to Favorites]                [Use This Template]  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.4 使用模板

**创建新项目**:
```
点击 "Use This Template"
  → 创建项目副本
  → 打开编辑器
  → 用户可自由修改
```

**应用到现有项目** (编辑器内):
```
从 Media Library 选择模板
  → 确认覆盖提示
  → 应用到当前页面
```

---

## 五、模板数据结构

### 5.1 Template Entity

```typescript
interface Template {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  subcategory: string;
  
  // 内容
  pages: TemplatePage[];
  thumbnail_url: string;
  preview_urls: string[];
  
  // 元数据
  page_count: number;
  paper_size: "Letter" | "A4";
  
  // 统计
  use_count: number;
  favorite_count: number;
  
  // 权限
  tier_required: "t1" | "t2" | "t3";
  is_premium: boolean;
  
  // 时间
  created_at: string;
  updated_at: string;
}

interface TemplatePage {
  page_number: number;
  canvas_json: object;
  thumbnail_url: string;
}

type TemplateCategory = 
  | "phonics"
  | "sight_words"
  | "decodable_stories"
  | "blank";
```

---

## 六、Tier 权限

### 6.1 模板访问权限

| Tier | 可用模板 |
|------|----------|
| t1 (Free) | Blank + 部分 Phonics |
| t2 (Starter) | 全部模板 |
| t3 (Pro) | 全部模板 + 保存个人模板 |

### 6.2 Premium 标记

```
┌─────────────┐
│  [PREMIUM]  │  ← 高级模板标记
│  [Preview]  │
│             │
│ Pro Story   │
│ 8 pages     │
└─────────────┘
```

---

## 七、UI/交互

### 7.1 页面列表

| 页面 | 路径 | 说明 |
|------|------|------|
| 模板库 | `/templates` | 浏览所有模板 |
| 模板详情 | `/templates/[id]` | 模板预览页 |
| 我的模板 | `/dashboard/templates` | 个人保存的模板 |

### 7.2 入口位置

| 入口 | 位置 |
|------|------|
| 导航菜单 | 顶部导航 "Templates" |
| Dashboard | "Create from Template" 按钮 |
| 编辑器 | Media Library > Templates Tab |

### 7.3 筛选与排序

**筛选选项**:
| 筛选 | 选项 |
|------|------|
| 分类 | Phonics / Sight Words / Stories / Blank |
| Tier | Free / Premium |
| 纸张 | Letter / A4 |

**排序选项**:
| 排序 | 说明 |
|------|------|
| Popular | 按使用量 |
| Newest | 按创建时间 |
| Favorites | 按收藏量 |

---

## 八、API 端点

### 8.1 模板列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/templates` | GET | 获取模板列表 |

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| category | string | 分类筛选 |
| limit | int | 每页数量 |
| offset | int | 偏移量 |
| sort | string | 排序方式 |

### 8.2 模板详情

| 端点 | 方法 | 说明 |
|------|------|------|
| `/templates/{id}` | GET | 获取模板详情 |

### 8.3 使用模板

| 端点 | 方法 | 说明 |
|------|------|------|
| `/templates/{id}/use` | POST | 从模板创建项目 |

### 8.4 收藏管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/templates/{id}/favorite` | POST | 添加收藏 |
| `/templates/{id}/favorite` | DELETE | 取消收藏 |
| `/templates/favorites` | GET | 获取收藏列表 |

---

## 九、验收标准

### 9.1 功能验收

| 功能 | 验收标准 |
|------|----------|
| 模板浏览 | 能按分类筛选和排序 |
| 模板预览 | 能查看所有页面预览 |
| 模板使用 | 能从模板创建新项目 |
| 模板收藏 | 能添加和取消收藏 |

### 9.2 权限验收

| 项目 | 验收标准 |
|------|----------|
| Free 用户 | 只能使用免费模板 |
| Premium 标记 | 高级模板显示标记 |
| 升级提示 | 点击高级模板显示升级提示 |

---

## 十、相关文档

- [编辑器功能规格](./editor.md)
- [Tier 系统](../../05-business/tier-system/overview.md)
- [素材分类系统](../../docs/shared/asset-category-design.md)

---

**END OF DOCUMENT**
