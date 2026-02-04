# 多租户 / Workspace 权限

> 本文档描述 Workspace 级权限覆盖机制，支持 Team Plan 等多租户场景。

**版本**: v1.0
**创建日期**: 2026-02-04
**来源**: 基于 03-system-design.md Workspace 权限定义

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [01-permission-matrix.md](./01-permission-matrix.md) | 权限矩阵定义 |
| [03-system-design.md](./03-system-design.md) | 系统架构设计 |
| [04-feature-flag-engine.md](./04-feature-flag-engine.md) | Feature Flag 评估引擎 |
| [07-tier-inheritance.md](./07-tier-inheritance.md) | Tier 权限继承 |

---

## 1. 数据库表设计

### 1.1 Workspace 权限覆盖表

```sql
-- =============================================
-- Workspace 级权限系统表
-- =============================================

-- Workspace 权限覆盖表
CREATE TABLE workspace_feature_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,
  override_value TEXT NOT NULL,            -- 'true' | 'false' | 'trial'
  reason TEXT,                             -- 如 'Enterprise 试用', 'Team Plan 权益'
  expires_at TIMESTAMPTZ,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(workspace_id, feature_key)
);
```

### 1.2 审计日志表

```sql
-- Workspace 权限变更审计日志
CREATE TABLE workspace_feature_override_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  override_id UUID REFERENCES workspace_feature_overrides(id) ON DELETE SET NULL,
  workspace_id UUID NOT NULL,
  feature_key TEXT NOT NULL,
  action TEXT NOT NULL,                    -- 'created' | 'updated' | 'deleted' | 'expired'
  old_value TEXT,
  new_value TEXT,
  reason TEXT,
  changed_by TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 1.3 索引

```sql
-- 索引
CREATE INDEX idx_workspace_feature_overrides_workspace ON workspace_feature_overrides(workspace_id);
CREATE INDEX idx_workspace_feature_overrides_expires ON workspace_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;
```

---

## 2. Workspace 权限服务

```python
# domains/entitlement/services/workspace_override_service.py

from typing import Optional
from datetime import datetime
from core.database import get_db

class WorkspaceOverrideService:
    """Workspace 级权限覆盖服务"""

    async def set_workspace_feature(
        self,
        workspace_id: str,
        feature_key: str,
        override_value: str,
        reason: str,
        created_by: str,
        expires_at: Optional[datetime] = None
    ) -> dict:
        """设置 Workspace 级权限"""
        db = await get_db()

        # 获取旧值
        old = await db.fetch_one("""
            SELECT override_value FROM workspace_feature_overrides
            WHERE workspace_id = $1 AND feature_key = $2
        """, workspace_id, feature_key)

        # Upsert
        result = await db.fetch_one("""
            INSERT INTO workspace_feature_overrides
            (workspace_id, feature_key, override_value, reason, expires_at, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (workspace_id, feature_key) DO UPDATE SET
                override_value = EXCLUDED.override_value,
                reason = EXCLUDED.reason,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            RETURNING *
        """, workspace_id, feature_key, override_value, reason, expires_at, created_by)

        # 记录审计日志
        await db.execute("""
            INSERT INTO workspace_feature_override_logs
            (override_id, workspace_id, feature_key, action, old_value, new_value, reason, changed_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, result['id'], workspace_id, feature_key,
            'updated' if old else 'created',
            old['override_value'] if old else None,
            override_value, reason, created_by)

        return dict(result)

    async def get_workspace_override(
        self,
        workspace_id: str,
        feature_key: str
    ) -> Optional[dict]:
        """获取 Workspace 级权限覆盖"""
        db = await get_db()
        result = await db.fetch_one("""
            SELECT * FROM workspace_feature_overrides
            WHERE workspace_id = $1 AND feature_key = $2
              AND (expires_at IS NULL OR expires_at > NOW())
        """, workspace_id, feature_key)

        return dict(result) if result else None

    async def apply_team_plan(
        self,
        workspace_id: str,
        team_tier: str,  # 如 't3'
        reason: str,
        created_by: str,
        expires_at: Optional[datetime] = None
    ) -> int:
        """为 Workspace 应用 Team Plan 权限"""
        from lib.entitlement.inheritance import getTierFeaturesWithInheritance

        tier_features = getTierFeaturesWithInheritance(team_tier)
        count = 0

        for feature_key, value in tier_features.items():
            if value == True:
                await self.set_workspace_feature(
                    workspace_id=workspace_id,
                    feature_key=feature_key,
                    override_value='true',
                    reason=f"{reason} - {team_tier} 权益",
                    created_by=created_by,
                    expires_at=expires_at
                )
                count += 1

        return count
```

---

## 3. Team Plan 支持

### 3.1 权限继承逻辑

Workspace 级权限覆盖在评估链中的位置:

```
用户请求功能 X
      │
      ▼
┌─────────────────┐
│ L1: Kill Switch │ ── false ──▶ 返回 disabled
└────────┬────────┘
         │ true
         ▼
┌─────────────────┐
│ L2: Feature Flag│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ L3: User Override│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ L4: Group Override│
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ L5: Workspace Override │ ◀── 本文档描述的层级
└────────┬────────────┘
         │
         ▼
┌─────────────────┐
│ L6: Tier Config │
└─────────────────┘
```

### 3.2 Team Plan 权限流转

1. **Workspace Owner 购买 Team Plan**
   - 触发 `apply_team_plan()` 方法
   - 根据 Team Tier (如 t3) 获取对应权限列表
   - 为 Workspace 设置所有权限覆盖

2. **成员加入 Workspace**
   - 成员个人 Tier 可能是 t1 (Free)
   - 访问功能时，Workspace Override 优先于 Tier Config
   - 成员享受 Team Plan 权益

3. **成员离开 Workspace**
   - 评估时 workspaceId 为空或不同
   - 回退到 User Tier Config
   - 失去 Team Plan 权益

---

## 4. 使用示例

```python
# 场景: Workspace Owner 购买 Team Plan，成员获得权限

# 1. Owner 购买 Team Plan 后触发
workspace_id = 'workspace_abc123'

# 2. 为 Workspace 应用 t3 级别权限
count = await workspace_override_service.apply_team_plan(
    workspace_id=workspace_id,
    team_tier='t3',
    reason='Team Pro Plan 订阅',
    created_by='system',
    expires_at=datetime(2027, 2, 4)  # 订阅到期时间
)
print(f"已为 Workspace 设置 {count} 个权限")

# 3. 成员访问时的评估
# - 成员 user_a (t1) 访问 ai_features
# - 评估流程:
#   1. Kill Switch: 通过
#   2. Feature Flag: 无
#   3. User Override: 无
#   4. Group Override: 无
#   5. Workspace Override: ai_features = true
#   → allowed: true, source: 'workspace_override'

# 4. 成员离开 Workspace 后
# - 评估时 workspaceId 为空或不同
# - 回退到 User Tier Config (t1)
# → allowed: false (试用期过期)
```

---

## 5. 注意事项

### 5.1 过期处理

- `expires_at` 字段支持权限自动过期
- 查询时自动过滤已过期的覆盖
- 建议配合定时任务清理过期记录

### 5.2 审计追踪

- 所有变更记录在 `workspace_feature_override_logs` 表
- 支持追溯谁在什么时间做了什么修改
- 便于合规审计和问题排查

### 5.3 性能考虑

- `workspace_id` 索引确保快速查询
- 部分索引 `expires_at` 优化过期记录查询
- 建议对高频访问的 Workspace 权限做缓存
