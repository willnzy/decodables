# 权限继承冲突解决

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [06-priority-rules.md](./06-priority-rules.md) | 7 层优先级规则 |
| [07-tier-inheritance.md](./07-tier-inheritance.md) | Tier 继承链 |

---

## 一、冲突场景

### 1.1 常见冲突类型

| 场景 | 冲突描述 |
|------|----------|
| Override 与 Tier | 用户 Override 与 Tier 基础配置不一致 |
| Group 与 Group | 用户属于多个 Group，权限配置不同 |
| Workspace 与 User | Workspace 级配置与用户级配置冲突 |
| 继承链冲突 | 高级 Tier 继承低级 Tier 时的权限覆盖 |

### 1.2 冲突示例

```
场景: 用户属于 "Beta Testers" 和 "Enterprise Clients" 两个组

Beta Testers:
  ai_features: enabled

Enterprise Clients:
  ai_features: disabled (企业合规要求)

问题: 该用户的 ai_features 应该是什么？
```

---

## 二、解决策略

### 2.1 策略类型

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **Permissive** | 多个权限中取最宽松的 | 功能开放类 |
| **Restrictive** | 多个权限中取最严格的 | 安全合规类 |
| **Priority** | 按预设优先级决定 | 有明确层级的场景 |
| **Explicit** | 必须显式配置，否则拒绝 | 高风险操作 |

### 2.2 默认策略

```
系统默认: Restrictive (安全优先)

可按功能覆盖:
- ai_features: Permissive
- payment_operations: Restrictive
- data_export: Restrictive
- beta_features: Permissive
```

---

## 三、优先级规则

### 3.1 7 层优先级

```
L0: Kill Switch       (最高，全局关闭)
L1: Feature Flag      (功能开关)
L2: User Override     (用户级覆盖)
L3: Group Override    (用户组覆盖)
L4: Workspace Override(工作区覆盖)
L5: Tier Config       (Tier 基础配置)
L6: Fallback Default  (兜底默认值)
```

### 3.2 评估流程

```python
async def evaluate_permission(user_id: str, feature: str) -> PermissionResult:
    # L0: Kill Switch
    if await is_kill_switch_enabled(feature):
        return PermissionResult(allowed=False, reason="kill_switch")

    # L1: Feature Flag
    flag = await get_feature_flag(feature)
    if not flag.enabled:
        return PermissionResult(allowed=False, reason="feature_disabled")

    # L2: User Override
    user_override = await get_user_override(user_id, feature)
    if user_override is not None:
        return PermissionResult(allowed=user_override, reason="user_override")

    # L3: Group Override (处理多 Group 冲突)
    groups = await get_user_groups(user_id)
    group_permissions = await get_group_permissions(groups, feature)
    if group_permissions:
        resolved = resolve_group_conflict(group_permissions, feature)
        return PermissionResult(allowed=resolved, reason="group_override")

    # L4: Workspace Override
    workspace = await get_user_workspace(user_id)
    ws_override = await get_workspace_override(workspace, feature)
    if ws_override is not None:
        return PermissionResult(allowed=ws_override, reason="workspace_override")

    # L5: Tier Config
    tier = await get_user_tier(user_id)
    tier_permission = await get_tier_permission(tier, feature)
    if tier_permission is not None:
        return PermissionResult(allowed=tier_permission, reason="tier_config")

    # L6: Fallback
    return PermissionResult(allowed=FALLBACK_DEFAULTS.get(feature, False), reason="fallback")
```

---

## 四、多 Group 冲突解决

### 4.1 解决算法

```python
def resolve_group_conflict(
    group_permissions: List[GroupPermission],
    feature: str
) -> bool:
    strategy = FEATURE_CONFLICT_STRATEGIES.get(feature, "restrictive")

    if strategy == "permissive":
        # 任一允许则允许
        return any(p.allowed for p in group_permissions)

    elif strategy == "restrictive":
        # 全部允许才允许
        return all(p.allowed for p in group_permissions)

    elif strategy == "priority":
        # 按 Group 优先级排序，取最高优先级的值
        sorted_perms = sorted(group_permissions, key=lambda p: p.group_priority)
        return sorted_perms[0].allowed

    elif strategy == "explicit":
        # 必须所有 Group 显式配置且一致
        if not all(p.is_explicit for p in group_permissions):
            return False
        values = set(p.allowed for p in group_permissions)
        if len(values) != 1:
            return False  # 不一致时拒绝
        return values.pop()

    return False
```

### 4.2 配置示例

```json
{
  "feature_conflict_strategies": {
    "ai_features": "permissive",
    "smart_scan": "permissive",
    "pdf_export": "restrictive",
    "zip_export": "restrictive",
    "publish_paid": "restrictive",
    "recover_deleted": "restrictive"
  }
}
```

---

## 五、继承链冲突

### 5.1 Tier 继承规则

```
TIER_INHERITANCE = {
    "t1": [],           # 无继承
    "t2": ["t1"],       # 继承 t1
    "t3": ["t2"],       # 继承 t2 (间接继承 t1)
    "t4": ["t3"]        # 继承 t3 (间接继承 t2, t1)
}
```

### 5.2 继承冲突处理

```
原则: 高级 Tier 显式配置 > 继承的配置

示例:
t2 配置: ai_features = true
t3 未配置 ai_features

结果: t3 用户的 ai_features = true (继承自 t2)

示例 2:
t2 配置: max_projects = 10
t3 配置: max_projects = unlimited

结果: t3 用户的 max_projects = unlimited (显式配置覆盖继承)
```

---

## 六、调试与排查

### 6.1 权限调试接口

```python
# 获取权限评估详情
GET /api/v1/debug/permissions/{feature}
Response: {
    "feature": "ai_features",
    "result": true,
    "evaluation_path": [
        {"level": "L0_kill_switch", "checked": true, "result": null},
        {"level": "L1_feature_flag", "checked": true, "result": null},
        {"level": "L2_user_override", "checked": true, "result": null},
        {"level": "L3_group_override", "checked": true, "result": true, "groups": ["beta_testers"]},
        {"level": "decision", "reason": "group_override", "value": true}
    ]
}
```

### 6.2 冲突日志

```python
# 记录冲突解决过程
{
    "event": "permission_conflict_resolved",
    "user_id": "user_xxx",
    "feature": "ai_features",
    "conflict_type": "multi_group",
    "groups": ["beta_testers", "enterprise_clients"],
    "group_values": [true, false],
    "strategy": "permissive",
    "resolved_value": true,
    "timestamp": "2026-02-04T10:00:00Z"
}
```

---

## 七、最佳实践

### 7.1 配置建议

| 建议 | 说明 |
|------|------|
| 避免多 Group 重叠 | 设计 Group 时避免用户属于多个配置冲突的 Group |
| 使用显式配置 | 关键功能使用显式配置而非依赖继承 |
| 定期审计 | 定期检查是否有意外的权限冲突 |
| 记录决策 | 记录冲突解决的原因，便于排查 |

### 7.2 常见问题

| 问题 | 解决方案 |
|------|----------|
| 用户反馈权限不符预期 | 使用调试接口查看评估路径 |
| 批量权限异常 | 检查 Group 配置是否有冲突 |
| 继承权限丢失 | 检查高级 Tier 是否显式覆盖 |

---

**END OF DOCUMENT**
