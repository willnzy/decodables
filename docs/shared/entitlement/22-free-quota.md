# 免费额度/体验次数

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [01-permission-matrix.md](./01-permission-matrix.md) | 权限矩阵 |
| [15-credits-lifecycle.md](./15-credits-lifecycle.md) | 积分生命周期 |

---

## 一、免费额度类型

### 1.1 注册赠送

| 赠送项 | 数量 | 类型 | 有效期 |
|--------|------|------|--------|
| 永久积分 | 100 | permanent | 永久 |

### 1.2 试用期权限

t1 用户在 7 天试用期内可体验:

| 功能 | 试用期内 | 试用期后 |
|------|----------|----------|
| AI 生图 | ✅ 可用 | ❌ 锁定 |
| AI 生 Page | ✅ 可用 | ❌ 锁定 |
| Smart Scan | ✅ 可用 | ❌ 锁定 |
| 剪贴板粘贴 | ✅ 可用 | ❌ 锁定 |
| ZIP 导出 | ✅ 可用 | ❌ 锁定 |
| 自定义素材上传 | ✅ 10 个 | ❌ 锁定 |

---

## 二、体验次数设计

### 2.1 功能体验次数

对于非订阅用户，提供有限次免费体验:

| 功能 | 免费次数 | 重置周期 | 适用用户 |
|------|----------|----------|----------|
| AI 生图 | 3 次 | 不重置 | t1 试用期后 |
| AI 生 Page | 2 次 | 不重置 | t1 试用期后 |
| Smart Scan | 2 次 | 不重置 | t1 试用期后 |
| PDF 导出 | 5 次 | 月重置 | t1 |

### 2.2 体验次数消耗

```
用户使用 AI 生图:
1. 检查是否订阅用户 → 是 → 扣积分
2. 检查是否有免费次数 → 是 → 消耗免费次数
3. 都没有 → 弹出升级提示
```

---

## 三、额度管理

### 3.1 额度查询

```python
async def get_free_quota(user_id: str, feature: str) -> dict:
    quota = await db.get_user_quota(user_id, feature)
    return {
        "feature": feature,
        "total": quota.total,
        "used": quota.used,
        "remaining": quota.total - quota.used,
        "resets_at": quota.resets_at
    }
```

### 3.2 额度消耗

```python
async def consume_free_quota(user_id: str, feature: str) -> bool:
    quota = await get_free_quota(user_id, feature)

    if quota["remaining"] <= 0:
        return False

    await db.increment_quota_used(user_id, feature)
    return True
```

---

## 四、重置规则

### 4.1 重置类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| 不重置 | 用完即止，永不恢复 | AI 功能体验 |
| 日重置 | 每日 UTC 00:00 重置 | 高频功能 |
| 月重置 | 每月 1 日重置 | PDF 导出等 |

### 4.2 重置逻辑

```python
async def reset_quotas():
    # 月重置
    await db.execute("""
        UPDATE user_quotas
        SET used = 0, resets_at = date_trunc('month', NOW()) + INTERVAL '1 month'
        WHERE reset_type = 'monthly'
        AND resets_at <= NOW()
    """)

    # 日重置
    await db.execute("""
        UPDATE user_quotas
        SET used = 0, resets_at = date_trunc('day', NOW()) + INTERVAL '1 day'
        WHERE reset_type = 'daily'
        AND resets_at <= NOW()
    """)
```

---

## 五、数据结构

### 5.1 用户额度表

```sql
CREATE TABLE IF NOT EXISTS user_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    feature VARCHAR(50) NOT NULL, -- ai_generate, smart_scan, pdf_export
    total INT NOT NULL DEFAULT 0,
    used INT NOT NULL DEFAULT 0,
    reset_type VARCHAR(20), -- null, daily, monthly
    resets_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, feature)
);

-- 索引
CREATE INDEX idx_user_quotas_user ON user_quotas(user_id);
CREATE INDEX idx_user_quotas_reset ON user_quotas(reset_type, resets_at);
```

### 5.2 初始化额度

```sql
-- 用户注册时初始化免费额度
INSERT INTO user_quotas (user_id, feature, total, used, reset_type, resets_at)
VALUES
    ($1, 'ai_generate', 3, 0, NULL, NULL),
    ($1, 'ai_page', 2, 0, NULL, NULL),
    ($1, 'smart_scan', 2, 0, NULL, NULL),
    ($1, 'pdf_export', 5, 0, 'monthly', date_trunc('month', NOW()) + INTERVAL '1 month');
```

---

## 六、用户界面

### 6.1 额度显示

```
AI 功能入口:
┌─────────────────────────────────┐
│ AI 生成图片                      │
│                                 │
│ 免费次数: 2/3 剩余               │
│ [生成图片]                       │
│                                 │
│ 💡 升级 Pro 享无限 AI 功能       │
└─────────────────────────────────┘
```

### 6.2 额度用尽提示

```
┌─────────────────────────────────┐
│ 免费次数已用完                   │
│                                 │
│ 您已使用完 AI 生图的免费次数     │
│                                 │
│ 升级 Pro Plan 可享受:           │
│ ✅ 无限 AI 生图                  │
│ ✅ 每月 200 积分                 │
│ ✅ 更多高级功能                  │
│                                 │
│ [立即升级]  [稍后再说]           │
└─────────────────────────────────┘
```

---

## 七、API 接口

```python
# 查询功能额度
GET /api/v1/quotas/{feature}
Response: {
    "feature": "ai_generate",
    "total": 3,
    "used": 1,
    "remaining": 2,
    "resets_at": null
}

# 查询所有额度
GET /api/v1/quotas
Response: {
    "quotas": [
        {"feature": "ai_generate", "total": 3, "used": 1, "remaining": 2},
        {"feature": "pdf_export", "total": 5, "used": 2, "remaining": 3, "resets_at": "2026-03-01"}
    ]
}
```

---

## 八、与积分的关系

| 场景 | 优先级 | 说明 |
|------|--------|------|
| 订阅用户 | 积分 | 直接扣积分 |
| 非订阅用户有额度 | 免费额度 | 先用免费额度 |
| 非订阅用户无额度 | 拒绝 | 提示升级 |

```
使用 AI 功能:
if user.tier in ['t2', 't3']:
    consume_credits()
else:
    if has_free_quota():
        consume_free_quota()
    else:
        show_upgrade_modal()
```

---

**END OF DOCUMENT**
