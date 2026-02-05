# 权益配置

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

权益参数的配置管理，支持动态调整。

---

## 配置存储

权益配置存储在 `system_configs` 表:

```sql
-- 示例配置
INSERT INTO system_configs (key, value, category) VALUES
('tier.t2.monthly_credits', '100', 'entitlement'),
('tier.t3.monthly_credits', '200', 'entitlement'),
('tier.t1.project_limit', '3', 'entitlement'),
('tier.t2.project_limit', '10', 'entitlement'),
('tier.t3.project_limit', '-1', 'entitlement'),  -- -1 表示无限
('tier.t1.pages_per_project', '5', 'entitlement'),
('tier.t2.pages_per_project', '20', 'entitlement'),
('tier.t3.pages_per_project', '-1', 'entitlement');
```

---

## 配置 Key 命名

```
{category}.{tier}.{resource}

category: tier / credits / ai
tier: t1 / t2 / t3
resource: monthly_credits / project_limit / ...
```

---

## 后端获取

```python
from core.config import ConfigService

class EntitlementService:
    def __init__(self, config: ConfigService):
        self.config = config
    
    async def get_project_limit(self, tier: str) -> int:
        key = f"tier.{tier}.project_limit"
        value = await self.config.get(key, default='-1')
        return int(value) if value != '-1' else float('inf')
```

---

## 前端获取

```tsx
// 通过 API 获取
const { data: config } = useConfig();

// 或者静态配置 (需与后端同步)
const TIER_LIMITS = {
  t1: { projects: 3, pagesPerProject: 5 },
  t2: { projects: 10, pagesPerProject: 20 },
  t3: { projects: Infinity, pagesPerProject: Infinity },
};
```

---

## Admin 配置页

管理员可通过 Admin 页面调整:

```
Admin → 系统配置 → 权益配置
```

修改后实时生效 (无需重启)。

---

## 配置变更审计

```sql
-- 配置变更记录
CREATE TABLE config_audit_log (
  id UUID PRIMARY KEY,
  config_key TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  changed_by UUID REFERENCES users(id),
  changed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 相关文档

- [系统配置模块](../../04-engineering/modules/config/)
- [Admin 配置页](../../02-product/pages/admin/configs.md)
