# 收藏功能规格

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/favorites/`

---

## 一、概述

### 1.1 功能定位

收藏功能让用户保存喜欢的模板和素材，方便后续使用。

### 1.2 可收藏内容

| 内容 | 说明 |
|------|------|
| 模板 | 系统模板、社区模板 |
| 素材 | Marketplace 素材 |

---

## 二、功能范围

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 添加收藏 | P0 | ✅ |
| 取消收藏 | P0 | ✅ |
| 收藏列表 | P0 | ✅ |
| 收藏分组 | P2 | 🔜 |

---

## 三、添加收藏

### 3.1 交互方式

```
┌─────────────────────────────────────────────────────────────┐
│  模板卡片                                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                         ││
│  │               [Template Preview]                        ││
│  │                                                         ││
│  │                                          ♡ → ❤️        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Animal Alphabet                                            │
│  12 pages • Used 1.2k times                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 状态变化

| 状态 | 图标 | 说明 |
|------|------|------|
| 未收藏 | ♡ | 空心爱心 |
| 已收藏 | ❤️ | 实心爱心 |

---

## 四、收藏列表

### 4.1 入口位置

- Dashboard 侧边栏 "Favorites"
- Profile 页面 "My Favorites"

### 4.2 列表布局

```
┌────────────────────────────────────────────────────────────┐
│  ❤️ My Favorites                                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  [Templates (15)]  [Assets (32)]                           │
│                                                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │         │  │         │  │         │  │         │       │
│  │ Template│  │ Template│  │ Template│  │ Template│       │
│  │         │  │         │  │         │  │         │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│   Animal A-Z   Colors      Numbers     Shapes             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 五、数据模型

### 5.1 数据库表

```sql
CREATE TABLE favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    item_type VARCHAR(20) NOT NULL,  -- 'template' | 'asset'
    item_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, item_type, item_id)
);
```

### 5.2 索引

```sql
CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_item ON favorites(item_type, item_id);
```

---

## 六、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/favorites` | GET | 获取收藏列表 |
| `/favorites` | POST | 添加收藏 |
| `/favorites/{type}/{id}` | DELETE | 取消收藏 |
| `/favorites/check` | GET | 检查是否已收藏 |

### 6.1 请求示例

```json
// POST /favorites
{
  "item_type": "template",
  "item_id": "uuid"
}
```

### 6.2 响应示例

```json
// GET /favorites?type=template
{
  "items": [
    {
      "id": "favorite-uuid",
      "item_type": "template",
      "item_id": "template-uuid",
      "item": { "name": "Animal A-Z", "thumbnail": "..." },
      "created_at": "2026-02-01T10:00:00Z"
    }
  ],
  "total": 15
}
```

---

## 七、相关文档

- [Marketplace 功能规格](./marketplace.md)
- [模板功能规格](./templates.md)

---

**END OF DOCUMENT**
