# Feature Flag 技术实现

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/platform/`, `experiments` 表

---

## 一、概述

Feature Flag 系统的技术实现细节，包括数据结构、评估引擎、API 和前端集成。

> **业务规则**: 评估优先级规则见 [权益策略规则](../../../05-business/entitlement/policy-rules.md)

---

## 二、Flag 类型

### 2.1 Boolean Flag

最简单的开关类型，只有开/关两种状态。

```python
FLAG_AI_PAGE_GENERATION = FeatureFlag(
    key="ai_page_generation",
    type="boolean",
    enabled=True,
    default_value=False,
    description="Enable AI page generation"
)
```

### 2.2 Percentage Flag

按用户 ID 的 hash 值决定是否启用。

```python
FLAG_NEW_EDITOR = FeatureFlag(
    key="new_editor",
    type="percentage",
    enabled=True,
    percentage=30,  # 30% 用户启用
    description="New editor experience"
)
```

### 2.3 Segment Flag

仅对特定用户群启用。

```python
FLAG_BETA_FEATURES = FeatureFlag(
    key="beta_features",
    type="segment",
    enabled=True,
    user_ids=["user_1", "user_2", "user_3"],
    description="Beta tester features"
)
```

### 2.4 Experiment Flag

A/B 实验，支持多变体。

```python
FLAG_PRICING_EXPERIMENT = FeatureFlag(
    key="pricing_experiment",
    type="experiment",
    enabled=True,
    variants=[
        {"name": "control", "weight": 50},
        {"name": "variant_a", "weight": 25},
        {"name": "variant_b", "weight": 25}
    ],
    description="Pricing page A/B test"
)
```

---

## 三、评估引擎

### 3.1 核心逻辑

```python
class FeatureFlagEngine:
    async def evaluate(
        self,
        flag_key: str,
        user_id: Optional[UUID] = None,
        context: Optional[dict] = None
    ) -> FlagResult:
        """
        评估 Feature Flag
        
        返回:
            FlagResult:
                enabled: bool - 是否启用
                variant: str - 变体名称
                reason: str - 决策原因
        """
        flag = await self.get_flag(flag_key)
        
        if not flag:
            return FlagResult(
                enabled=False,
                variant="control",
                reason="flag_not_found"
            )
        
        # 1. Kill Switch
        if flag.kill_switch:
            return FlagResult(
                enabled=False,
                variant="control",
                reason="kill_switch"
            )
        
        # 2. Flag 未启用
        if not flag.enabled:
            return FlagResult(
                enabled=False,
                variant="control",
                reason="flag_disabled"
            )
        
        # 3. 用户 Override
        if user_id:
            override = await self.get_user_override(user_id, flag_key)
            if override:
                return FlagResult(
                    enabled=override.enabled,
                    variant=override.variant,
                    reason="user_override"
                )
        
        # 4. 按类型评估
        match flag.type:
            case "boolean":
                return self._evaluate_boolean(flag)
            case "percentage":
                return self._evaluate_percentage(flag, user_id)
            case "segment":
                return self._evaluate_segment(flag, user_id)
            case "experiment":
                return self._evaluate_experiment(flag, user_id)
        
        return FlagResult(
            enabled=False,
            variant="control",
            reason="unknown_type"
        )
```

### 3.2 百分比评估

```python
def _evaluate_percentage(
    self,
    flag: FeatureFlag,
    user_id: Optional[UUID]
) -> FlagResult:
    """基于 user_id hash 的百分比评估"""
    if not user_id:
        return FlagResult(
            enabled=False,
            variant="control",
            reason="no_user_id"
        )
    
    # 使用 MD5 确保一致性
    hash_input = f"{user_id}:{flag.key}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    bucket = hash_value % 100
    
    enabled = bucket < flag.percentage
    
    return FlagResult(
        enabled=enabled,
        variant="treatment" if enabled else "control",
        reason="percentage_rollout"
    )
```

### 3.3 实验评估

```python
def _evaluate_experiment(
    self,
    flag: FeatureFlag,
    user_id: Optional[UUID]
) -> FlagResult:
    """A/B 实验变体分配"""
    if not user_id:
        return FlagResult(
            enabled=True,
            variant="control",
            reason="no_user_id_default_control"
        )
    
    # 计算用户桶
    hash_input = f"{user_id}:{flag.key}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    bucket = hash_value % 100
    
    # 按权重分配变体
    cumulative = 0
    for variant in flag.variants:
        cumulative += variant["weight"]
        if bucket < cumulative:
            return FlagResult(
                enabled=True,
                variant=variant["name"],
                reason="experiment_assignment"
            )
    
    # 默认 control
    return FlagResult(
        enabled=True,
        variant="control",
        reason="experiment_default"
    )
```

---

## 四、数据结构

### 4.1 Feature Flag 表

```sql
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,  -- boolean, percentage, segment, experiment
    enabled BOOLEAN DEFAULT true,
    kill_switch BOOLEAN DEFAULT false,
    percentage INTEGER,
    user_ids UUID[],
    variants JSONB,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 用户 Override 表

```sql
CREATE TABLE feature_flag_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    flag_key VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL,
    variant VARCHAR(50),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, flag_key)
);
```

### 4.3 实验分配记录表

```sql
CREATE TABLE experiment_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    experiment_key VARCHAR(100) NOT NULL,
    variant VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, experiment_key)
);
```

---

## 五、API 端点

### 5.1 用户端点

```python
# 获取用户的 Flag 状态
GET /api/v2/user/features/{key}
Response: {
    "enabled": true,
    "variant": "treatment",
    "reason": "percentage_rollout"
}

# 批量获取 Flags
POST /api/v2/user/features/batch
Body: { "keys": ["flag_a", "flag_b"] }
Response: {
    "flags": {
        "flag_a": { "enabled": true, "variant": "control" },
        "flag_b": { "enabled": false, "variant": "control" }
    }
}
```

### 5.2 Admin 端点

```python
# 获取所有 Flags
GET /api/v2/admin/feature-flags

# 创建 Flag
POST /api/v2/admin/feature-flags
Body: {
    "key": "new_feature",
    "type": "percentage",
    "percentage": 10,
    "description": "New feature rollout"
}

# 切换 Flag 状态
POST /api/v2/admin/feature-flags/{key}/toggle

# 设置用户 Override
POST /api/v2/admin/feature-flags/{key}/override
Body: {
    "user_id": "...",
    "enabled": true,
    "variant": "treatment"
}
```

---

## 六、前端集成

### 6.1 React Hook

```typescript
// hooks/useFeatureFlag.ts

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useFeatureFlag(key: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['feature-flag', key],
    queryFn: () => api.get(`/user/features/${key}`),
    staleTime: 5 * 60 * 1000, // 5 分钟缓存
  });

  return {
    enabled: data?.enabled ?? false,
    variant: data?.variant ?? 'control',
    isLoading,
    error,
  };
}

// 使用
function NewFeatureComponent() {
  const { enabled, variant } = useFeatureFlag('new_editor');
  
  if (!enabled) {
    return <OldEditor />;
  }
  
  return variant === 'variant_a' ? <NewEditorA /> : <NewEditorB />;
}
```

### 6.2 Context Provider

```typescript
// contexts/FeatureFlagContext.tsx

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface FeatureFlags {
  [key: string]: {
    enabled: boolean;
    variant: string;
  };
}

const FeatureFlagContext = createContext<FeatureFlags>({});

export function FeatureFlagProvider({ children }) {
  const [flags, setFlags] = useState<FeatureFlags>({});

  useEffect(() => {
    api.post('/user/features/batch', {
      keys: ['new_editor', 'ai_features', 'pricing_v2']
    }).then(res => setFlags(res.data.flags));
  }, []);

  return (
    <FeatureFlagContext.Provider value={flags}>
      {children}
    </FeatureFlagContext.Provider>
  );
}

export function useFeatureFlags() {
  return useContext(FeatureFlagContext);
}
```

---

## 七、最佳实践

### 7.1 命名规范

```python
# 功能开关
"feature_{name}"           # feature_new_editor
"feature_{name}_enabled"   # feature_ai_enabled

# 实验
"experiment_{name}"        # experiment_pricing_v2
"ab_{name}"               # ab_signup_flow

# Kill Switch
"kill_{name}"             # kill_ai_generation
```

### 7.2 生命周期

```
1. 创建 Flag (percentage: 0%)
2. 内部测试 (segment: beta_testers)
3. 小规模灰度 (percentage: 5%)
4. 逐步放量 (10% → 25% → 50% → 100%)
5. 全量发布 (type: boolean, enabled: true)
6. 清理代码，删除 Flag
```

### 7.3 监控与告警

```python
# 记录 Flag 评估
async def evaluate_with_logging(flag_key: str, user_id: UUID):
    result = await engine.evaluate(flag_key, user_id)
    
    # 记录评估结果
    await log_flag_evaluation(
        flag_key=flag_key,
        user_id=user_id,
        enabled=result.enabled,
        variant=result.variant,
        reason=result.reason
    )
    
    return result
```

---

## 八、相关文档

- [权益策略规则](../../../05-business/entitlement/policy-rules.md)
- [Feature Flags 功能规格](../../../02-product/features/feature-flags.md)

---

**END OF DOCUMENT**
