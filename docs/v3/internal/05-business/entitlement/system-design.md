# 权益系统设计

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证 (来源: v2 文档 + 代码分析)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/identity/`, `domains/billing/`

---

## 一、概述

### 1.1 系统职责

| 能力 | 说明 | 负责模块 |
|------|------|---------|
| 用户权限管理 | Tier、试用期、配额、override | EntitlementService |
| 灰度发布 | 按比例放量 | FeatureFlagService |
| A/B 实验 | 多变体实验 | FeatureFlagService |
| 运营授权 | 指定用户越权 | EntitlementService |

### 1.2 架构原则

```
Entitlement 解决 "有没有资格" (用户 Tier、配额、试用期)
Feature Flag 解决 "是否已上线" (灰度、实验)
```

---

## 二、系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Entitlement System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │ EntitlementSvc   │    │ FeatureFlagSvc   │              │
│  │                  │    │                  │              │
│  │ - Tier 判断      │    │ - 灰度放量       │              │
│  │ - 试用期计算     │    │ - A/B 实验       │              │
│  │ - 配额检查       │    │ - Kill Switch    │              │
│  │ - Override      │    │                  │              │
│  └────────┬─────────┘    └────────┬─────────┘              │
│           │                       │                         │
│           └───────────┬───────────┘                         │
│                       ▼                                     │
│           ┌──────────────────────┐                         │
│           │     Merge Layer      │                         │
│           │                      │                         │
│           │ 优先级裁决:          │                         │
│           │ Kill Switch >        │                         │
│           │ Override >           │                         │
│           │ Tier/Trial >         │                         │
│           │ Feature Flag         │                         │
│           └──────────┬───────────┘                         │
│                      ▼                                     │
│           ┌──────────────────────┐                         │
│           │   API Response       │                         │
│           │                      │                         │
│           │ /api/v2/user/features│                         │
│           └──────────────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
1. 从 system_configs 读取 tier.features 与配额
2. 评估 Feature Flag (灰度/实验)
3. Merge 层合并结果
4. API 输出 /api/v2/user/features
```

---

## 三、合并层 (Merge Layer)

### 3.1 优先级

```
Kill Switch > Entitlement Override > Tier/Trial > Feature Flag Variant
```

### 3.2 返回结构

```python
class FeatureAccess:
    access: str  # "full" | "trial" | "locked"
    variant: str  # flag 评估结果
    reason: str  # 决策来源
    quota_remaining: Optional[int]  # 剩余配额
```

### 3.3 决策逻辑

```python
def evaluate_feature(user, feature_key):
    # 1. 检查 Kill Switch
    if is_kill_switch_on(feature_key):
        return FeatureAccess(access="locked", reason="kill_switch")
    
    # 2. 检查用户 Override
    if has_override(user.id, feature_key):
        override = get_override(user.id, feature_key)
        return FeatureAccess(access=override.access, reason="override")
    
    # 3. 检查 Tier 权限
    tier_access = check_tier_permission(user.tier, feature_key)
    if user.tier == "t1" and is_in_trial(user):
        tier_access = check_trial_permission(feature_key)
    
    # 4. 检查 Feature Flag
    flag_result = evaluate_feature_flag(user.id, feature_key)
    
    # 5. Merge
    return merge_results(tier_access, flag_result)
```

---

## 四、Entitlement Service

### 4.1 核心方法

```python
class EntitlementService:
    async def check_feature_access(
        self, user_id: UUID, feature_key: str
    ) -> FeatureAccess:
        """检查用户是否有权访问某功能"""
        
    async def check_quota(
        self, user_id: UUID, quota_key: str
    ) -> QuotaStatus:
        """检查用户配额"""
        
    async def is_in_trial(self, user_id: UUID) -> bool:
        """判断用户是否在试用期"""
        
    async def get_user_entitlements(
        self, user_id: UUID
    ) -> UserEntitlements:
        """获取用户完整权益"""
```

### 4.2 配额检查

```python
@dataclass
class QuotaStatus:
    key: str
    limit: int
    used: int
    remaining: int
    is_exceeded: bool

async def check_quota(user_id: UUID, quota_key: str) -> QuotaStatus:
    # 1. 获取用户 Tier
    user = await get_user(user_id)
    
    # 2. 获取 Tier 配额限制
    limit = await get_config(f"tier.{user.tier}.{quota_key}")
    
    # 3. 获取当前使用量
    used = await count_user_resource(user_id, quota_key)
    
    return QuotaStatus(
        key=quota_key,
        limit=limit,
        used=used,
        remaining=max(0, limit - used),
        is_exceeded=used >= limit
    )
```

---

## 五、Feature Flag Service

### 5.1 Flag 类型

| 类型 | 说明 | 用途 |
|------|------|------|
| Boolean | 开/关 | Kill Switch |
| Percentage | 按比例 | 灰度发布 |
| Segment | 按用户群 | 特定用户测试 |
| Experiment | A/B 测试 | 多变体实验 |

### 5.2 评估逻辑

```python
async def evaluate_flag(user_id: UUID, flag_key: str) -> FlagResult:
    flag = await get_flag(flag_key)
    
    if not flag.enabled:
        return FlagResult(enabled=False, variant="control")
    
    match flag.type:
        case "boolean":
            return FlagResult(enabled=flag.value, variant="default")
        
        case "percentage":
            hash_value = hash(f"{user_id}:{flag_key}") % 100
            enabled = hash_value < flag.percentage
            return FlagResult(enabled=enabled, variant="default")
        
        case "segment":
            enabled = user_id in flag.user_ids
            return FlagResult(enabled=enabled, variant="default")
        
        case "experiment":
            variant = assign_variant(user_id, flag)
            return FlagResult(enabled=True, variant=variant)
```

---

## 六、配置存储

### 6.1 system_configs 表结构

```sql
CREATE TABLE system_configs (
    id UUID PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(50),
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2 配置示例

```json
// tier.t2.features
{
  "ai_features": true,
  "smart_scan": false,
  "zip_export": false,
  "pdf_print": true,
  "pdf_download": true
}

// tier.t2.quota
{
  "max_projects": 10,
  "max_folders": 5,
  "max_custom_assets": 0
}
```

---

## 七、API 端点

### 7.1 获取用户权益

```
GET /api/v2/user/features
```

**Response:**

```json
{
  "tier": "t2",
  "is_trial": false,
  "trial_days_remaining": 0,
  "features": {
    "ai_features": { "access": "full", "reason": "tier" },
    "smart_scan": { "access": "locked", "reason": "tier" },
    "zip_export": { "access": "locked", "reason": "tier" }
  },
  "quota": {
    "max_projects": { "limit": 10, "used": 3, "remaining": 7 },
    "max_folders": { "limit": 5, "used": 2, "remaining": 3 }
  },
  "credits": {
    "monthly": 45,
    "permanent": 100,
    "total": 145
  }
}
```

---

## 八、相关文档

- [权限矩阵](./permission-matrix.md)
- [订阅生命周期](./billing-lifecycle.md)
- [Feature Flags 功能规格](../../02-product/features/feature-flags.md)
- [平台服务架构](../../04-engineering/modules/platform/architecture.md)

---

**END OF DOCUMENT**
