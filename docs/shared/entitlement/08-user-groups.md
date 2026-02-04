# 用户组批量授权

> 本文档详细说明 Make Decodables 用户组系统的设计与实现，支持对用户组进行批量权限管理。

**版本**: v1.2
**创建日期**: 2026-02-04
**来源**: 基于 01-permission-matrix.md 用户组授权定义
**更新**: 添加待实现清单
**实现状态**: 🔴 数据库层待实现

---

## 目录

1. [概述](#1-概述)
2. [数据库表设计](#2-数据库表设计)
3. [后端 Service 实现](#3-后端-service-实现)
4. [使用示例](#4-使用示例)
5. [相关文档](#5-相关文档)

---

## 1. 概述

用户组系统允许管理员将多个用户组织成一个组，并为整个组设置权限覆盖。这种批量授权方式适用于以下场景：

- **KOL 用户组**: 签约 KOL 用户享受 Pro 级别功能
- **Beta 测试组**: 参与内测的用户提前体验新功能
- **企业试用组**: 企业客户试用期间的特殊权限

**权限评估 7 层优先级** (完整版，参考 [06-priority-rules.md](./06-priority-rules.md)):

```
L0: Kill Switch       (最高，全局关闭)
L1: Feature Flag      (功能开关/灰度)
L2: User Override     (用户级覆盖)
L3: Group Override    (用户组覆盖) ← 本文档描述的层级
L4: Workspace Override(工作区覆盖)
L5: Tier Config       (Tier 基础配置)
L6: Fallback Default  (兜底默认值)
```

> **注意**: Group Override 在评估链中处于 L3 层级，优先于 Workspace 和 Tier Config，但低于 User Override。

---

## 2. 数据库表设计

### 2.1 用户组表 (user_groups)

```sql
-- =============================================
-- 用户组系统表
-- =============================================

-- 用户组表
CREATE TABLE user_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_key TEXT NOT NULL UNIQUE,          -- 唯一标识: 'kol', 'beta_testers', 'enterprise_pilot'
  group_name TEXT NOT NULL,                -- 显示名称: 'KOL 用户组', 'Beta 测试组'
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  created_by TEXT NOT NULL,                -- 创建人 (Admin user_id)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 用户组成员表 (user_group_members)

```sql
-- 用户组成员表
CREATE TABLE user_group_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  added_by UUID NOT NULL,                  -- 添加人 (Admin user_id)
  added_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,                  -- 成员过期时间 (可选)
  UNIQUE(group_id, user_id)
);
```

### 2.3 组级权限覆盖表 (group_feature_overrides)

```sql
-- 组级权限覆盖表
CREATE TABLE group_feature_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,
  override_value TEXT NOT NULL,            -- 'true' | 'false' | 'trial'
  reason TEXT,
  expires_at TIMESTAMPTZ,                  -- 权限过期时间 (可选)
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(group_id, feature_key)
);
```

### 2.4 审计日志表 (group_feature_override_logs)

```sql
-- 组级权限变更审计日志
CREATE TABLE group_feature_override_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  override_id UUID REFERENCES group_feature_overrides(id) ON DELETE SET NULL,
  group_id UUID NOT NULL,
  feature_key TEXT NOT NULL,
  action TEXT NOT NULL,                    -- 'created' | 'updated' | 'deleted' | 'expired'
  old_value TEXT,
  new_value TEXT,
  reason TEXT,
  changed_by TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.5 索引

```sql
-- 索引
CREATE INDEX idx_user_groups_key ON user_groups(group_key);
CREATE INDEX idx_user_group_members_user ON user_group_members(user_id);
CREATE INDEX idx_user_group_members_group ON user_group_members(group_id);
CREATE INDEX idx_user_group_members_expires ON user_group_members(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_group_feature_overrides_group ON group_feature_overrides(group_id);
CREATE INDEX idx_group_feature_overrides_expires ON group_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;
```

---

## 3. 后端 Service 实现

```python
# domains/entitlement/services/group_service.py

from typing import Optional, List
from datetime import datetime
from core.database import get_db

class GroupService:
    """用户组权限服务"""

    async def create_group(
        self,
        group_key: str,
        group_name: str,
        description: str,
        created_by: str
    ) -> dict:
        """创建用户组"""
        db = await get_db()
        result = await db.fetch_one("""
            INSERT INTO user_groups (group_key, group_name, description, created_by)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """, group_key, group_name, description, created_by)
        return dict(result)

    async def add_members(
        self,
        group_id: str,
        user_ids: List[str],
        added_by: str,
        expires_at: Optional[datetime] = None
    ) -> int:
        """批量添加成员"""
        db = await get_db()
        count = 0
        for user_id in user_ids:
            try:
                await db.execute("""
                    INSERT INTO user_group_members (group_id, user_id, added_by, expires_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (group_id, user_id) DO NOTHING
                """, group_id, user_id, added_by, expires_at)
                count += 1
            except Exception:
                pass
        return count

    async def set_group_feature(
        self,
        group_id: str,
        feature_key: str,
        override_value: str,
        reason: str,
        created_by: str,
        expires_at: Optional[datetime] = None
    ) -> dict:
        """设置组级权限"""
        db = await get_db()

        # 获取旧值
        old = await db.fetch_one("""
            SELECT override_value FROM group_feature_overrides
            WHERE group_id = $1 AND feature_key = $2
        """, group_id, feature_key)

        # Upsert
        result = await db.fetch_one("""
            INSERT INTO group_feature_overrides
            (group_id, feature_key, override_value, reason, expires_at, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (group_id, feature_key) DO UPDATE SET
                override_value = EXCLUDED.override_value,
                reason = EXCLUDED.reason,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            RETURNING *
        """, group_id, feature_key, override_value, reason, expires_at, created_by)

        # 记录审计日志
        await db.execute("""
            INSERT INTO group_feature_override_logs
            (override_id, group_id, feature_key, action, old_value, new_value, reason, changed_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, result['id'], group_id, feature_key,
            'updated' if old else 'created',
            old['override_value'] if old else None,
            override_value, reason, created_by)

        return dict(result)

    async def get_user_groups(self, user_id: str) -> List[str]:
        """获取用户所属的所有有效组 ID"""
        db = await get_db()
        rows = await db.fetch_all("""
            SELECT g.id FROM user_groups g
            JOIN user_group_members m ON g.id = m.group_id
            WHERE m.user_id = $1
              AND g.is_active = true
              AND (m.expires_at IS NULL OR m.expires_at > NOW())
        """, user_id)
        return [row['id'] for row in rows]

    async def get_group_override(
        self,
        group_ids: List[str],
        feature_key: str
    ) -> Optional[dict]:
        """获取组级权限覆盖 (优先返回第一个匹配的)"""
        if not group_ids:
            return None

        db = await get_db()
        result = await db.fetch_one("""
            SELECT * FROM group_feature_overrides
            WHERE group_id = ANY($1) AND feature_key = $2
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            LIMIT 1
        """, group_ids, feature_key)

        return dict(result) if result else None
```

---

## 4. 使用示例

### 4.1 为 KOL 用户组批量授权 AI 功能

```python
# 场景: 为 KOL 用户组批量授权 AI 功能

# 1. 创建 KOL 用户组
kol_group = await group_service.create_group(
    group_key='kol',
    group_name='KOL 用户组',
    description='签约 KOL 用户，享受 Pro 级别 AI 功能',
    created_by='admin_user_id'
)

# 2. 批量添加 KOL 用户
kol_user_ids = ['user_kol_001', 'user_kol_002', 'user_kol_003']
await group_service.add_members(
    group_id=kol_group['id'],
    user_ids=kol_user_ids,
    added_by='admin_user_id',
    expires_at=datetime(2026, 12, 31)  # 年底到期
)

# 3. 设置组级 AI 功能权限
await group_service.set_group_feature(
    group_id=kol_group['id'],
    feature_key='ai_features',
    override_value='true',
    reason='KOL 签约权益',
    created_by='admin_user_id'
)

await group_service.set_group_feature(
    group_id=kol_group['id'],
    feature_key='smart_scan',
    override_value='true',
    reason='KOL 签约权益',
    created_by='admin_user_id'
)

# 4. 评估时自动生效
# t1 KOL 用户访问 ai_features → allowed: true (Group Override)
# t1 普通用户访问 ai_features → allowed: false (Tier Config)
```

---

## 5. 相关文档

| 文档 | 说明 |
|------|------|
| [01-permission-matrix.md](./01-permission-matrix.md) | 权限矩阵总览 |
| [02-tier-config.md](./02-tier-config.md) | Tier 配置详解 |
| [03-system-design.md](./03-system-design.md) | 系统设计文档 |
| [04-feature-flag-engine.md](./04-feature-flag-engine.md) | Feature Flag 引擎 |
| [07-tier-inheritance.md](./07-tier-inheritance.md) | Tier 继承机制 |
| [README.md](./README.md) | 文档导航 |

---

---

## 6. 待实现清单

> ⚠️ **审计发现** (2026-02-04): 以下内容已设计但尚未在数据库/后端实现

### 6.1 数据库层 (🔴 P0)

| # | 待实现项 | 说明 | 优先级 |
|---|---------|------|--------|
| 1 | **创建 `user_groups` 表** | 用户组定义表 | 🟡 P1 |
| 2 | **创建 `user_group_members` 表** | 用户组成员关联表 | 🟡 P1 |
| 3 | **创建 `group_feature_overrides` 表** | 组级权限覆盖表 | 🟡 P1 |
| 4 | **创建 `group_feature_override_logs` 表** | 组级权限审计日志 | 🟢 P2 |
| 5 | **添加相关索引** | 参见 2.5 节索引设计 | 🟡 P1 |

### 6.2 后端逻辑层 (🟡 P1)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | `GroupService` 实现 | 参见第 3 节完整代码 |
| 2 | `UserGroupRepository` | 用户组 CRUD |
| 3 | 权限评估集成 | 在 7 级优先级链中集成 Group Override (L3) |

### 6.3 Admin API (🟡 P1)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | `POST /admin/groups` | 创建用户组 |
| 2 | `POST /admin/groups/{id}/members` | 批量添加成员 |
| 3 | `POST /admin/groups/{id}/features` | 设置组级权限 |
| 4 | `GET /admin/groups` | 查询所有用户组 |
| 5 | `GET /admin/groups/{id}/members` | 查询组成员 |

---

**文档版本历史**:

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.2 | 2026-02-04 | 添加待实现清单 |
| v1.1 | 2026-02-04 | 修正权限评估优先级为完整 7 层 |
| v1.0 | 2026-02-04 | 从 entitlement-permission-matrix.md 第 7.4 节提取 |
