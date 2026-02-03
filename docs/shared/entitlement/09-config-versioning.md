# 配置版本控制

> 权限系统配置的快照与回滚机制

**版本**: v1.0
**创建日期**: 2026-02-04
**来源**: entitlement-permission-matrix.md 第七章 7.5 节

---

## 目录

- [1. 数据库表设计](#1-数据库表设计)
- [2. 快照服务实现](#2-快照服务实现)
- [3. 使用示例](#3-使用示例)

---

## 1. 数据库表设计

### 1.1 配置快照表

```sql
-- =============================================
-- 配置版本控制系统表
-- =============================================

-- 配置快照表
CREATE TABLE config_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_key TEXT NOT NULL UNIQUE,       -- 唯一标识: 'pre_black_friday_2026'
  snapshot_name TEXT NOT NULL,             -- 显示名称: '黑五活动前快照'
  snapshot_type TEXT NOT NULL,             -- 类型: 'tier_configs' | 'feature_flags' | 'full'
  snapshot_data JSONB NOT NULL,            -- 完整配置数据
  description TEXT,
  is_current BOOLEAN DEFAULT false,        -- 是否为当前生效版本
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 1.2 配置回滚日志表

```sql
-- 配置回滚日志
CREATE TABLE config_rollback_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id UUID NOT NULL REFERENCES config_snapshots(id),
  rollback_type TEXT NOT NULL,             -- 'full' | 'partial'
  affected_keys TEXT[],                    -- 受影响的配置 key
  rollback_reason TEXT NOT NULL,
  rollback_by TEXT NOT NULL,
  rollback_at TIMESTAMPTZ DEFAULT NOW(),
  success BOOLEAN DEFAULT true,
  error_message TEXT
);
```

### 1.3 索引

```sql
-- 索引
CREATE INDEX idx_config_snapshots_type ON config_snapshots(snapshot_type);
CREATE INDEX idx_config_snapshots_created ON config_snapshots(created_at DESC);
CREATE INDEX idx_config_snapshots_current ON config_snapshots(is_current) WHERE is_current = true;
```

---

## 2. 快照服务实现

### 2.1 ConfigSnapshotService 类

```python
# domains/entitlement/services/snapshot_service.py

from typing import Optional, List
from datetime import datetime
import json
from core.database import get_db

class ConfigSnapshotService:
    """配置快照与回滚服务"""

    async def create_snapshot(
        self,
        snapshot_key: str,
        snapshot_name: str,
        snapshot_type: str,  # 'tier_configs' | 'feature_flags' | 'full'
        description: str,
        created_by: str
    ) -> dict:
        """创建配置快照"""
        db = await get_db()

        # 根据类型收集配置数据
        snapshot_data = {}

        if snapshot_type in ['tier_configs', 'full']:
            tier_configs = await db.fetch_all("""
                SELECT key, value, value_type FROM system_configs
                WHERE config_group = 'tier' AND is_active = true
            """)
            snapshot_data['tier_configs'] = [dict(r) for r in tier_configs]

        if snapshot_type in ['feature_flags', 'full']:
            feature_flags = await db.fetch_all("""
                SELECT * FROM feature_flags WHERE is_enabled = true
            """)
            snapshot_data['feature_flags'] = [dict(r) for r in feature_flags]

        if snapshot_type == 'full':
            # 包含全局开关
            global_configs = await db.fetch_all("""
                SELECT key, value, value_type FROM system_configs
                WHERE config_group = 'feature' AND is_active = true
            """)
            snapshot_data['global_configs'] = [dict(r) for r in global_configs]

            # 包含用户组权限
            group_overrides = await db.fetch_all("""
                SELECT * FROM group_feature_overrides
            """)
            snapshot_data['group_overrides'] = [dict(r) for r in group_overrides]

        # 保存快照
        result = await db.fetch_one("""
            INSERT INTO config_snapshots
            (snapshot_key, snapshot_name, snapshot_type, snapshot_data, description, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, snapshot_key, snapshot_name, snapshot_type,
            json.dumps(snapshot_data), description, created_by)

        return dict(result)
```

### 2.2 回滚方法

```python
    async def rollback_to_snapshot(
        self,
        snapshot_id: str,
        rollback_reason: str,
        rollback_by: str,
        partial_keys: Optional[List[str]] = None  # 部分回滚时指定 key
    ) -> dict:
        """回滚到指定快照"""
        db = await get_db()

        # 获取快照
        snapshot = await db.fetch_one("""
            SELECT * FROM config_snapshots WHERE id = $1
        """, snapshot_id)

        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        snapshot_data = json.loads(snapshot['snapshot_data'])
        affected_keys = []

        try:
            # 回滚 Tier 配置
            if 'tier_configs' in snapshot_data:
                for config in snapshot_data['tier_configs']:
                    if partial_keys and config['key'] not in partial_keys:
                        continue

                    await db.execute("""
                        UPDATE system_configs
                        SET value = $1, updated_at = NOW()
                        WHERE key = $2
                    """, config['value'], config['key'])
                    affected_keys.append(config['key'])

            # 回滚 Feature Flags
            if 'feature_flags' in snapshot_data:
                # 先禁用所有当前 flags
                await db.execute("""
                    UPDATE feature_flags SET is_enabled = false, updated_at = NOW()
                """)

                # 恢复快照中的 flags
                for flag in snapshot_data['feature_flags']:
                    if partial_keys and flag['flag_key'] not in partial_keys:
                        continue

                    await db.execute("""
                        INSERT INTO feature_flags (flag_key, flag_name, is_enabled, rollout_percentage, allowed_tiers)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (flag_key) DO UPDATE SET
                            is_enabled = EXCLUDED.is_enabled,
                            rollout_percentage = EXCLUDED.rollout_percentage,
                            allowed_tiers = EXCLUDED.allowed_tiers,
                            updated_at = NOW()
                    """, flag['flag_key'], flag['flag_name'], flag['is_enabled'],
                        flag['rollout_percentage'], flag['allowed_tiers'])
                    affected_keys.append(f"flag:{flag['flag_key']}")

            # 标记快照为当前生效
            await db.execute("""
                UPDATE config_snapshots SET is_current = false
            """)
            await db.execute("""
                UPDATE config_snapshots SET is_current = true WHERE id = $1
            """, snapshot_id)

            # 记录回滚日志
            log = await db.fetch_one("""
                INSERT INTO config_rollback_logs
                (snapshot_id, rollback_type, affected_keys, rollback_reason, rollback_by, success)
                VALUES ($1, $2, $3, $4, $5, true)
                RETURNING *
            """, snapshot_id, 'partial' if partial_keys else 'full',
                affected_keys, rollback_reason, rollback_by)

            return {
                'success': True,
                'affected_keys': affected_keys,
                'log_id': log['id']
            }

        except Exception as e:
            # 记录失败日志
            await db.execute("""
                INSERT INTO config_rollback_logs
                (snapshot_id, rollback_type, affected_keys, rollback_reason, rollback_by, success, error_message)
                VALUES ($1, $2, $3, $4, $5, false, $6)
            """, snapshot_id, 'partial' if partial_keys else 'full',
                affected_keys, rollback_reason, rollback_by, str(e))
            raise
```

### 2.3 列出快照方法

```python
    async def list_snapshots(
        self,
        snapshot_type: Optional[str] = None,
        limit: int = 20
    ) -> List[dict]:
        """列出快照"""
        db = await get_db()

        if snapshot_type:
            rows = await db.fetch_all("""
                SELECT id, snapshot_key, snapshot_name, snapshot_type,
                       description, is_current, created_by, created_at
                FROM config_snapshots
                WHERE snapshot_type = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, snapshot_type, limit)
        else:
            rows = await db.fetch_all("""
                SELECT id, snapshot_key, snapshot_name, snapshot_type,
                       description, is_current, created_by, created_at
                FROM config_snapshots
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)

        return [dict(r) for r in rows]
```

---

## 3. 使用示例

### 3.1 活动配置备份与回滚

```python
# 场景: 黑五活动前创建快照，活动后回滚

# 1. 活动前创建完整快照
snapshot = await snapshot_service.create_snapshot(
    snapshot_key='pre_black_friday_2026',
    snapshot_name='2026 黑五活动前快照',
    snapshot_type='full',
    description='黑五促销活动前的完整配置备份',
    created_by='admin_user_id'
)
print(f"快照创建成功: {snapshot['id']}")

# 2. 进行活动配置修改...
# (修改 Tier 权限、Feature Flags 等)

# 3. 活动结束后回滚
result = await snapshot_service.rollback_to_snapshot(
    snapshot_id=snapshot['id'],
    rollback_reason='黑五活动结束，恢复正常配置',
    rollback_by='admin_user_id'
)
print(f"回滚成功，影响 {len(result['affected_keys'])} 个配置项")
```

### 3.2 部分回滚

```python
# 4. 部分回滚 (只回滚特定配置)
result = await snapshot_service.rollback_to_snapshot(
    snapshot_id=snapshot['id'],
    rollback_reason='只恢复 t2 Tier 配置',
    rollback_by='admin_user_id',
    partial_keys=['tier.t2.features']  # 只回滚这个 key
)
```

---

## 相关文档

- [README.md](./README.md) - 权限系统文档索引
- [02-tier-config.md](./02-tier-config.md) - Tier 配置详解
- [04-feature-flag-engine.md](./04-feature-flag-engine.md) - Feature Flag 引擎
- [07-tier-inheritance.md](./07-tier-inheritance.md) - Tier 继承机制

---

**快照类型说明**:

| 类型 | 包含内容 |
|------|----------|
| `tier_configs` | Tier 相关的 system_configs |
| `feature_flags` | 所有启用的 Feature Flags |
| `full` | tier_configs + feature_flags + global_configs + group_overrides |
