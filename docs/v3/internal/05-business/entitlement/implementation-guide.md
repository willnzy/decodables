# 权益系统实现指南

> Implementation Guide - 权益系统开发实现参考

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]

---

## 一、概述

本文档为开发人员提供权益系统的实现指南，包括代码示例、最佳实践和常见模式。

---

## 二、核心组件

### 2.1 组件架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    权益系统组件架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ EntitlementChecker │    │ FeatureFlagService │                │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                              │
│           └──────────┬───────────┘                              │
│                      │                                          │
│              ┌───────▼───────┐                                  │
│              │ PolicyEvaluator │                                 │
│              └───────┬───────┘                                  │
│                      │                                          │
│      ┌───────────────┼───────────────┐                          │
│      │               │               │                          │
│ ┌────▼────┐   ┌──────▼──────┐  ┌─────▼─────┐                   │
│ │ TierRule │   │ QuotaChecker │  │ FlagEvaluator │               │
│ └─────────┘   └─────────────┘  └───────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心类定义

```python
# domains/entitlement/checker.py

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class EntitlementResult(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    QUOTA_EXCEEDED = "quota_exceeded"
    FEATURE_DISABLED = "feature_disabled"

@dataclass
class FeatureAccess:
    allowed: bool
    result: EntitlementResult
    rule: str
    feature: str
    message: Optional[str] = None
    quota_info: Optional[Dict[str, Any]] = None

@dataclass
class QuotaResult:
    allowed: bool
    reason: Optional[str] = None
    current: Optional[int] = None
    limit: Optional[int] = None
    retry_after: Optional[int] = None

class EntitlementChecker:
    """
    权益检查器 - 统一入口
    """
    
    def __init__(
        self,
        tier_service: TierService,
        feature_flag_service: FeatureFlagService,
        quota_service: QuotaService,
    ):
        self.tier_service = tier_service
        self.feature_flag_service = feature_flag_service
        self.quota_service = quota_service
    
    async def check_feature(
        self,
        user: User,
        feature_key: str,
        context: Optional[Dict] = None
    ) -> FeatureAccess:
        """
        检查用户是否可以使用某功能
        
        检查顺序:
        1. Kill Switch
        2. User Override
        3. Tier Permission
        4. Feature Flag
        5. Default
        """
        # 1. Kill Switch
        if await self.feature_flag_service.is_killed(feature_key):
            return FeatureAccess(
                allowed=False,
                result=EntitlementResult.FEATURE_DISABLED,
                rule='kill_switch',
                feature=feature_key,
                message='Feature is temporarily disabled'
            )
        
        # 2. User Override
        override = await self.tier_service.get_user_override(user.id, feature_key)
        if override is not None:
            return FeatureAccess(
                allowed=override,
                result=EntitlementResult.ALLOWED if override else EntitlementResult.DENIED,
                rule='user_override',
                feature=feature_key
            )
        
        # 3. Tier Permission
        tier_allowed = await self.tier_service.check_tier_permission(
            user.tier, feature_key
        )
        if tier_allowed is not None:
            return FeatureAccess(
                allowed=tier_allowed,
                result=EntitlementResult.ALLOWED if tier_allowed else EntitlementResult.DENIED,
                rule='tier_permission',
                feature=feature_key
            )
        
        # 4. Feature Flag
        flag_result = await self.feature_flag_service.evaluate(
            feature_key, user.id, context
        )
        if flag_result is not None:
            return FeatureAccess(
                allowed=flag_result,
                result=EntitlementResult.ALLOWED if flag_result else EntitlementResult.DENIED,
                rule='feature_flag',
                feature=feature_key
            )
        
        # 5. Default: allowed
        return FeatureAccess(
            allowed=True,
            result=EntitlementResult.ALLOWED,
            rule='default',
            feature=feature_key
        )
    
    async def check_quota(
        self,
        user: User,
        quota_type: str,
        amount: int = 1
    ) -> QuotaResult:
        """
        检查用户配额
        """
        return await self.quota_service.check(user, quota_type, amount)
```

---

## 三、使用模式

### 3.1 功能门控 (Feature Gating)

```python
# 在 API 层使用

from fastapi import Depends, HTTPException

async def require_feature(
    feature_key: str,
    checker: EntitlementChecker = Depends(get_entitlement_checker),
    current_user: User = Depends(get_current_user)
):
    """依赖注入：要求特定功能权限"""
    access = await checker.check_feature(current_user, feature_key)
    
    if not access.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FEATURE_NOT_ALLOWED",
                "feature": feature_key,
                "rule": access.rule,
                "message": access.message or f"Access to {feature_key} is not allowed"
            }
        )
    
    return access

# 使用示例
@router.post("/generate")
async def generate_image(
    request: GenerateRequest,
    _feature: FeatureAccess = Depends(lambda: require_feature("ai_generation")),
    current_user: User = Depends(get_current_user)
):
    # 已验证有权限
    ...
```

### 3.2 配额检查 (Quota Check)

```python
# 在 Service 层使用

async def use_credits_for_generation(
    user: User,
    cost: int,
    checker: EntitlementChecker
) -> bool:
    """
    消费积分进行生成
    """
    # 1. 检查功能权限
    feature_access = await checker.check_feature(user, 'ai_generation')
    if not feature_access.allowed:
        raise FeatureNotAllowedError(feature_access.message)
    
    # 2. 检查积分配额
    quota_result = await checker.check_quota(user, 'credits', cost)
    if not quota_result.allowed:
        raise InsufficientCreditsError(
            required=cost,
            available=quota_result.current
        )
    
    # 3. 检查速率限制
    rate_result = await checker.check_quota(user, 'rate_limit_ai', 1)
    if not rate_result.allowed:
        raise RateLimitError(retry_after=rate_result.retry_after)
    
    # 4. 执行扣费
    await deduct_credits(user.id, cost, 'ai_generation')
    
    return True
```

### 3.3 前端权限检查

```typescript
// hooks/useEntitlement.ts

import { useQuery } from '@tanstack/react-query';

interface FeatureAccess {
  allowed: boolean;
  rule: string;
  feature: string;
  message?: string;
}

export function useFeatureAccess(featureKey: string): {
  allowed: boolean;
  loading: boolean;
  rule?: string;
} {
  const { data, isLoading } = useQuery({
    queryKey: ['feature-access', featureKey],
    queryFn: () => api.get<FeatureAccess>(`/api/v1/entitlement/check/${featureKey}`),
    staleTime: 5 * 60 * 1000, // 5 分钟缓存
  });
  
  return {
    allowed: data?.allowed ?? false,
    loading: isLoading,
    rule: data?.rule,
  };
}

// 使用示例
function AiGenerateButton() {
  const { allowed, loading } = useFeatureAccess('ai_generation');
  
  if (loading) return <Skeleton />;
  
  if (!allowed) {
    return (
      <Button disabled>
        <Lock className="mr-2 h-4 w-4" />
        升级解锁
      </Button>
    );
  }
  
  return <Button onClick={handleGenerate}>AI 生成</Button>;
}
```

### 3.4 条件渲染

```typescript
// components/FeatureGate.tsx

interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function FeatureGate({ feature, children, fallback }: FeatureGateProps) {
  const { allowed, loading } = useFeatureAccess(feature);
  
  if (loading) return null;
  
  if (!allowed) {
    return fallback ?? null;
  }
  
  return <>{children}</>;
}

// 使用示例
function EditorToolbar() {
  return (
    <Toolbar>
      <BasicTools />
      
      <FeatureGate 
        feature="custom_fonts" 
        fallback={<FontUpgradePrompt />}
      >
        <CustomFontPicker />
      </FeatureGate>
      
      <FeatureGate feature="export_pdf">
        <ExportPdfButton />
      </FeatureGate>
    </Toolbar>
  );
}
```

---

## 四、缓存策略

### 4.1 后端缓存

```python
# core/cache.py

from functools import wraps
import redis.asyncio as redis

class EntitlementCache:
    """权益缓存"""
    
    TTL = {
        'tier_permission': 3600,      # 1 小时
        'user_override': 300,         # 5 分钟
        'feature_flag': 300,          # 5 分钟
        'kill_switch': 60,            # 1 分钟 (需要快速生效)
        'quota_usage': 60,            # 1 分钟
    }
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get_tier_permission(
        self, tier: str, feature: str
    ) -> Optional[bool]:
        key = f"entitlement:tier:{tier}:{feature}"
        value = await self.redis.get(key)
        if value is not None:
            return value == b'1'
        return None
    
    async def set_tier_permission(
        self, tier: str, feature: str, allowed: bool
    ):
        key = f"entitlement:tier:{tier}:{feature}"
        await self.redis.setex(
            key,
            self.TTL['tier_permission'],
            '1' if allowed else '0'
        )
    
    async def invalidate_user(self, user_id: str):
        """用户权益变更时清除缓存"""
        pattern = f"entitlement:user:{user_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

### 4.2 前端缓存

```typescript
// lib/entitlement-cache.ts

const CACHE_KEY = 'entitlement_cache';
const CACHE_TTL = 5 * 60 * 1000; // 5 分钟

interface CacheEntry {
  allowed: boolean;
  rule: string;
  timestamp: number;
}

class EntitlementCache {
  private cache: Map<string, CacheEntry> = new Map();
  
  get(feature: string): boolean | null {
    const entry = this.cache.get(feature);
    
    if (!entry) return null;
    
    if (Date.now() - entry.timestamp > CACHE_TTL) {
      this.cache.delete(feature);
      return null;
    }
    
    return entry.allowed;
  }
  
  set(feature: string, allowed: boolean, rule: string) {
    this.cache.set(feature, {
      allowed,
      rule,
      timestamp: Date.now(),
    });
  }
  
  invalidate() {
    this.cache.clear();
  }
}

export const entitlementCache = new EntitlementCache();
```

---

## 五、事件处理

### 5.1 Tier 变更事件

```python
# domains/entitlement/events.py

from domains.events import EventBus

class TierChangedEvent:
    user_id: str
    old_tier: str
    new_tier: str
    reason: str  # upgrade/downgrade/admin

async def handle_tier_changed(event: TierChangedEvent):
    """处理 Tier 变更事件"""
    # 1. 清除缓存
    await entitlement_cache.invalidate_user(event.user_id)
    
    # 2. 更新配额
    await quota_service.recalculate_quotas(event.user_id, event.new_tier)
    
    # 3. 发送通知
    await notification_service.send_tier_changed(
        event.user_id,
        event.old_tier,
        event.new_tier
    )
    
    # 4. 记录审计日志
    await audit_service.log(
        user_id=event.user_id,
        action='tier_changed',
        details={
            'old_tier': event.old_tier,
            'new_tier': event.new_tier,
            'reason': event.reason
        }
    )

# 注册事件处理器
EventBus.subscribe(TierChangedEvent, handle_tier_changed)
```

### 5.2 Feature Flag 变更

```python
async def handle_feature_flag_changed(flag_key: str):
    """处理 Feature Flag 变更"""
    # 清除相关缓存
    pattern = f"entitlement:flag:{flag_key}:*"
    await redis_client.delete_pattern(pattern)
    
    # 广播到所有实例
    await pubsub.publish('feature_flag_changed', flag_key)
```

---

## 六、错误处理

### 6.1 异常类定义

```python
# domains/entitlement/exceptions.py

class EntitlementError(Exception):
    """权益相关异常基类"""
    code: str = "ENTITLEMENT_ERROR"

class FeatureNotAllowedError(EntitlementError):
    code = "FEATURE_NOT_ALLOWED"
    
    def __init__(self, feature: str, rule: str, message: str = None):
        self.feature = feature
        self.rule = rule
        super().__init__(message or f"Access to {feature} is not allowed")

class InsufficientCreditsError(EntitlementError):
    code = "INSUFFICIENT_CREDITS"
    
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient credits: need {required}, have {available}")

class QuotaExceededError(EntitlementError):
    code = "QUOTA_EXCEEDED"
    
    def __init__(self, quota_type: str, limit: int):
        self.quota_type = quota_type
        self.limit = limit
        super().__init__(f"Quota exceeded for {quota_type}: limit is {limit}")

class RateLimitError(EntitlementError):
    code = "RATE_LIMITED"
    
    def __init__(self, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s")
```

### 6.2 API 异常处理

```python
# api/exception_handlers.py

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(EntitlementError)
async def entitlement_exception_handler(request: Request, exc: EntitlementError):
    status_code = {
        'FEATURE_NOT_ALLOWED': 403,
        'INSUFFICIENT_CREDITS': 402,
        'QUOTA_EXCEEDED': 429,
        'RATE_LIMITED': 429,
    }.get(exc.code, 400)
    
    return JSONResponse(
        status_code=status_code,
        content={
            'error': exc.code,
            'message': str(exc),
            'details': getattr(exc, '__dict__', {})
        },
        headers={
            'Retry-After': str(exc.retry_after)
        } if hasattr(exc, 'retry_after') and exc.retry_after else {}
    )
```

---

## 七、测试模式

### 7.1 单元测试

```python
# tests/unit/test_entitlement.py

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def checker():
    return EntitlementChecker(
        tier_service=MagicMock(),
        feature_flag_service=MagicMock(),
        quota_service=MagicMock(),
    )

@pytest.mark.asyncio
async def test_feature_allowed_by_tier(checker):
    # Arrange
    user = User(id='user_1', tier='t2')
    checker.tier_service.check_tier_permission = AsyncMock(return_value=True)
    
    # Act
    result = await checker.check_feature(user, 'export_pdf')
    
    # Assert
    assert result.allowed is True
    assert result.rule == 'tier_permission'

@pytest.mark.asyncio
async def test_feature_blocked_by_kill_switch(checker):
    # Arrange
    user = User(id='user_1', tier='t3')
    checker.feature_flag_service.is_killed = AsyncMock(return_value=True)
    
    # Act
    result = await checker.check_feature(user, 'experimental_feature')
    
    # Assert
    assert result.allowed is False
    assert result.rule == 'kill_switch'
```

### 7.2 集成测试

```python
# tests/integration/test_entitlement_flow.py

@pytest.mark.asyncio
async def test_complete_entitlement_flow(test_client, test_db):
    """完整权益流程测试"""
    # 1. 创建 t1 用户
    user = await create_test_user(tier='t1')
    
    # 2. 验证 t1 无法使用 export_pdf
    response = await test_client.post(
        '/api/v1/projects/123/export',
        json={'format': 'pdf'},
        headers={'Authorization': f'Bearer {user.token}'}
    )
    assert response.status_code == 403
    assert response.json()['error'] == 'FEATURE_NOT_ALLOWED'
    
    # 3. 升级到 t2
    await upgrade_user(user.id, 't2')
    
    # 4. 验证 t2 可以使用 export_pdf
    response = await test_client.post(
        '/api/v1/projects/123/export',
        json={'format': 'pdf'},
        headers={'Authorization': f'Bearer {user.token}'}
    )
    assert response.status_code == 200
```

---

## 八、相关文档

- [权益系统设计](./system-design.md)
- [权益策略规则](./policy-rules.md)
- [Feature Flag 引擎](../../02-standards/feature-flag-engine.md)
- [测试指南](../../02-standards/testing-guide.md)
